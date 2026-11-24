//! A single command's checked engine bytes. The format and policy are the
//! existing scripts/sdk-inputs protocol; Python remains its independent verifier
//! during immutable source capture. A capture's evidence is never reused by a
//! later command. A file's content DIGEST may be: see `DigestCache`, which keys a
//! digest by the file's complete stat stamp and refuses any stamp that was not
//! already in the past when the file was read.
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File, Metadata, OpenOptions};
use std::io::{self, Read};
use std::path::{Path, PathBuf};

fn invalid(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.into())
}

#[cfg(target_os = "linux")]
#[derive(Clone, Debug, PartialEq, Eq)]
struct Stamp {
    device: u64, inode: u64, size: u64, mode: u32,
    mtime: (i64, i64), ctime: (i64, i64),
}

#[cfg(target_os = "linux")]
impl Stamp {
    fn file(meta: &Metadata) -> Self {
        use std::os::unix::fs::MetadataExt;
        Self { device: meta.dev(), inode: meta.ino(), size: meta.size(), mode: meta.mode(),
            mtime: (meta.mtime(), meta.mtime_nsec()), ctime: (meta.ctime(), meta.ctime_nsec()) }
    }
    fn newest(&self) -> (i64, i64) { self.mtime.max(self.ctime) }
    fn directory(meta: &Metadata) -> Self {
        let mut value = Self::file(meta);
        value.size = 0;
        value.mode &= libc::S_IFMT;
        value
    }
}

struct Policy {
    roots: Vec<String>, excluded: Vec<String>, reserved: Vec<String>, targets: Vec<String>,
    entries: u64, file_bytes: u64, total_bytes: u64, depth: u64,
}

impl Policy {
    fn read(root: &Path) -> io::Result<Self> {
        let path = root.join("nix/engine-inputs.json");
        let mut bytes = Vec::new();
        #[cfg(target_os = "linux")]
        let input = {
            use std::os::unix::fs::OpenOptionsExt;
            OpenOptions::new().read(true).custom_flags(libc::O_NOFOLLOW).open(path)?
        };
        #[cfg(not(target_os = "linux"))]
        let input = File::open(path)?;
        input.take(65537).read_to_end(&mut bytes)?;
        if bytes.len() > 65536 { return Err(invalid("engine-input policy exceeds capacity")); }
        let value: serde_json::Value = serde_json::from_slice(&bytes).map_err(|e| invalid(e.to_string()))?;
        let object = value.as_object().ok_or_else(|| invalid("invalid engine-input policy"))?;
        let keys: BTreeSet<_> = object.keys().map(String::as_str).collect();
        if keys != BTreeSet::from(["version", "roots", "excluded", "reserved", "targetRoots", "limits"])
            || value["version"] != 1 {
            return Err(invalid("unsupported engine-input policy"));
        }
        let paths = |key: &str, reserved: bool| -> io::Result<Vec<String>> {
            let rows = value[key].as_array().ok_or_else(|| invalid("malformed engine-input paths"))?;
            if !reserved && rows.is_empty() { return Err(invalid("empty engine-input paths")); }
            rows.iter().map(|row| {
                let name = row.as_str().ok_or_else(|| invalid("invalid engine-input path"))?;
                if (reserved && (name.is_empty() || name.contains('/')))
                    || (!reserved && name.split('/').any(|part| ["", ".", ".."].contains(&part))) {
                    return Err(invalid("engine-input paths must be relative"));
                }
                Ok(name.to_owned())
            }).collect()
        };
        let limits = value["limits"].as_object().ok_or_else(|| invalid("invalid engine-input limits"))?;
        if limits.keys().map(String::as_str).collect::<BTreeSet<_>>()
            != BTreeSet::from(["entries", "fileBytes", "totalBytes", "depth"]) {
            return Err(invalid("invalid engine-input limits"));
        }
        let limit = |name: &str| limits[name].as_u64().filter(|n| *n > 0)
            .ok_or_else(|| invalid("invalid engine-input limit"));
        Ok(Self { roots: paths("roots", false)?, excluded: paths("excluded", false)?,
            reserved: paths("reserved", true)?, targets: paths("targetRoots", false)?,
            entries: limit("entries")?, file_bytes: limit("fileBytes")?,
            total_bytes: limit("totalBytes")?, depth: limit("depth")? })
    }
}

fn beneath(parent: &[u8], child: &[u8]) -> bool {
    child == parent || (child.starts_with(parent) && child.get(parent.len()) == Some(&b'/'))
}

// Match Python's filesystem surrogateescape and JSON ensure_ascii, including
// non-UTF8 Unix names. Sort by Unicode code points as Python does, not OS bytes.
fn points(mut bytes: &[u8]) -> Vec<u32> {
    let mut result = Vec::new();
    while !bytes.is_empty() {
        match std::str::from_utf8(bytes) {
            Ok(text) => { result.extend(text.chars().map(u32::from)); break; }
            Err(error) => {
                let valid = error.valid_up_to();
                result.extend(std::str::from_utf8(&bytes[..valid]).unwrap().chars().map(u32::from));
                let count = error.error_len().unwrap_or(bytes.len() - valid);
                result.extend(bytes[valid..valid + count].iter().map(|byte| 0xdc00 + u32::from(*byte)));
                bytes = &bytes[valid + count..];
            }
        }
    }
    result
}

fn json_name(name: &[u32]) -> String {
    use std::fmt::Write;
    let mut out = String::from("\"");
    for &point in name {
        match point {
            0x22 => out.push_str("\\\""), 0x5c => out.push_str("\\\\"),
            8 => out.push_str("\\b"), 9 => out.push_str("\\t"), 10 => out.push_str("\\n"),
            12 => out.push_str("\\f"), 13 => out.push_str("\\r"),
            0x20..=0x7e => out.push(char::from_u32(point).unwrap()),
            0..=0xffff => { write!(out, "\\u{point:04x}").unwrap(); }
            _ => {
                let high = 0xd800 + ((point - 0x10000) >> 10);
                let low = 0xdc00 + ((point - 0x10000) & 0x3ff);
                write!(out, "\\u{high:04x}\\u{low:04x}").unwrap();
            }
        }
    }
    out.push('"');
    out
}


// ── content digests across commands ─────────────────────────────────────────
//
// Every checkout command used to read and SHA-256 the whole engine tree (about a
// thousand files, 67 MB): 0.34 s of CPU before the warm VM saw the request. The
// cache keeps, per physical path, the digest with the complete stat stamp it was
// read under (device, inode, size, mode, mtime and ctime in nanoseconds). A later
// command reuses the digest only for an identical stamp.
//
// The racy case is a write in the same clock tick as the read: the stamp would
// not change. A digest is therefore recorded only when the file's newest
// timestamp was at least RACY_SECONDS older than the moment its read began; any
// later write moves mtime and ctime past that moment, and ctime cannot be set
// from user space. A clock stepped backwards is the residual risk, as for git's
// index; BL_CHECKOUT_DIGEST_CACHE=0 disables reuse.
//
// M4: one cache file per checkout root (`checkout-digests-v2/<root>.bin`), and
// saving never stats a row. The v1 cache was one file for every tree a user
// ever ran: 63,000 rows and 12 MB on this host (every worktree and scratch copy
// in /tmp), loaded by every client that computed locally, and every save
// pruned it with one `exists()` per row. Warm that was 117-326 ms of a local
// inventory; with the dentries evicted (a host deep in swap) it was measured at
// 15.5 s in M1 and 112 s here. A row now survives a save when this process used
// it (a hit or a fresh read) or while the file stays under its bound; past the
// bound only used rows are kept. A stale row is harmless: a lookup needs the
// complete stamp to match.
#[cfg(target_os = "linux")]
mod digest_cache {
    use super::Stamp;
    use std::collections::HashMap;
    use std::io::{Read, Write};
    use std::path::{Path, PathBuf};
    use std::sync::Mutex;

    const MAGIC: &[u8; 16] = b"bl-digests-v2\0\0\0";
    const RACY_SECONDS: i64 = 2;
    /// Rows a load accepts and a save writes for one root (a checkout has
    /// about 5,000 engine, library and project files).
    const MAX_ENTRIES: usize = 30_000;

    struct Row { stamp: Stamp, digest: [u8; 32], used: bool }
    struct Cache { path: Option<PathBuf>, rows: HashMap<Vec<u8>, Row>, dirty: bool }

    static CACHE: Mutex<Option<Cache>> = Mutex::new(None);
    static ROOT: Mutex<Option<PathBuf>> = Mutex::new(None);

    fn enabled() -> bool { std::env::var_os("BL_CHECKOUT_DIGEST_CACHE").is_none_or(|v| v != "0") }

    /// Name the checkout whose cache file this process uses. Only the first
    /// binding before the cache loads counts; later ones are ignored, since the
    /// rows are keyed by physical path and are valid for any root.
    pub fn bind_root(root: &Path) {
        if let Ok(mut bound) = ROOT.lock() {
            if bound.is_none() { *bound = Some(root.to_path_buf()); }
        }
    }

    fn location() -> Option<PathBuf> {
        let base = std::env::var_os("XDG_CACHE_HOME").filter(|v| !v.is_empty()).map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".cache")))?;
        let root = ROOT.lock().ok().and_then(|r| r.clone())
            .or_else(|| std::env::var_os("BL_CHECKOUT_ROOT").map(PathBuf::from));
        let name = match root {
            Some(root) => {
                use sha2::{Digest, Sha256};
                let digest = Sha256::digest(root.as_os_str().as_encoded_bytes());
                digest[..12].iter().map(|b| format!("{b:02x}")).collect::<String>()
            }
            None => "default".to_string(),
        };
        Some(base.join("beam-lisp/checkout-digests-v2").join(format!("{name}.bin")))
    }

    fn take_i64(bytes: &[u8], at: &mut usize) -> Option<i64> {
        let v = i64::from_le_bytes(bytes.get(*at..*at + 8)?.try_into().ok()?); *at += 8; Some(v)
    }

    fn load(path: &Path) -> HashMap<Vec<u8>, Row> {
        let mut rows = HashMap::new();
        let mut bytes = Vec::new();
        if std::fs::File::open(path).and_then(|f| f.take(64 << 20).read_to_end(&mut bytes)).is_err()
            || bytes.len() < 16 || &bytes[..16] != MAGIC { return rows; }
        let mut at = 16;
        while at < bytes.len() && rows.len() < MAX_ENTRIES {
            let Some(row) = (|| {
                let len = take_i64(&bytes, &mut at)? as usize;
                let name = bytes.get(at..at.checked_add(len)?)?.to_vec(); at += len;
                let device = take_i64(&bytes, &mut at)? as u64; let inode = take_i64(&bytes, &mut at)? as u64;
                let size = take_i64(&bytes, &mut at)? as u64; let mode = take_i64(&bytes, &mut at)? as u32;
                let mtime = (take_i64(&bytes, &mut at)?, take_i64(&bytes, &mut at)?);
                let ctime = (take_i64(&bytes, &mut at)?, take_i64(&bytes, &mut at)?);
                let digest: [u8; 32] = bytes.get(at..at + 32)?.try_into().ok()?; at += 32;
                Some((name, Row { stamp: Stamp { device, inode, size, mode, mtime, ctime }, digest, used: false }))
            })() else { return HashMap::new() };
            rows.insert(row.0, row.1);
        }
        rows
    }

    fn with<T>(f: impl FnOnce(&mut Cache) -> T) -> Option<T> {
        if !enabled() { return None; }
        let mut guard = CACHE.lock().ok()?;
        let cache = guard.get_or_insert_with(|| {
            let path = location();
            let rows = path.as_deref().map(load).unwrap_or_default();
            Cache { path, rows, dirty: false }
        });
        Some(f(cache))
    }

    pub fn lookup(path: &Path, stamp: &Stamp) -> Option<[u8; 32]> {
        with(|c| {
            let row = c.rows.get_mut(path.as_os_str().as_encoded_bytes())?;
            if row.stamp != *stamp { return None; }
            row.used = true;
            Some(row.digest)
        }).flatten()
    }

    /// The wall clock as (seconds, nanoseconds), taken before a read begins.
    pub fn now() -> (i64, i64) {
        let d = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
        (d.as_secs() as i64, d.subsec_nanos() as i64)
    }

    pub fn record(path: &Path, stamp: &Stamp, digest: [u8; 32], read_began: (i64, i64)) {
        if (stamp.newest().0 + RACY_SECONDS, stamp.newest().1) >= read_began { return; }
        with(|c| {
            let key = path.as_os_str().as_encoded_bytes().to_vec();
            if c.rows.len() < MAX_ENTRIES || c.rows.contains_key(&key) {
                c.rows.insert(key, Row { stamp: stamp.clone(), digest, used: true });
                c.dirty = true;
            }
        });
    }

    /// Persist new digests. No row is stat()ed: past the bound, only rows this
    /// process used are kept. Best effort: a cache that cannot be written only
    /// costs the next command its reads.
    pub fn save() {
        let _ = with(|c| -> std::io::Result<()> {
            let Some(path) = c.path.clone() else { return Ok(()) };
            if !c.dirty { return Ok(()); }
            if c.rows.len() >= MAX_ENTRIES * 9 / 10 { c.rows.retain(|_, row| row.used); }
            let mut out = Vec::with_capacity(16 + c.rows.len() * 140);
            out.extend_from_slice(MAGIC);
            for (name, row) in &c.rows {
                let s = &row.stamp;
                out.extend_from_slice(&(name.len() as i64).to_le_bytes());
                out.extend_from_slice(name);
                for v in [s.device as i64, s.inode as i64, s.size as i64, s.mode as i64, s.mtime.0, s.mtime.1, s.ctime.0, s.ctime.1] {
                    out.extend_from_slice(&v.to_le_bytes());
                }
                out.extend_from_slice(&row.digest);
            }
            let dir = path.parent().unwrap_or(Path::new("."));
            std::fs::create_dir_all(dir)?;
            let tmp = dir.join(format!(".checkout-digests-{}.tmp", std::process::id()));
            {
                use std::os::unix::fs::OpenOptionsExt;
                let mut f = std::fs::OpenOptions::new().write(true).create(true).truncate(true).mode(0o600).open(&tmp)?;
                f.write_all(&out)?;
            }
            std::fs::rename(&tmp, &path)?;
            c.dirty = false;
            Ok(())
        });
    }

    #[cfg(test)]
    pub fn location_for_tests() -> Option<PathBuf> { with(|c| c.path.clone()).flatten() }
}

#[cfg(target_os = "linux")]
pub use digest_cache::save as save_digest_cache;
#[cfg(target_os = "linux")]
pub use digest_cache::bind_root as bind_digest_cache_root;
#[cfg(not(target_os = "linux"))]
pub fn bind_digest_cache_root(_: &Path) {}

/// The digest a later command would reuse for `path` as it stands now.
#[cfg(all(test, target_os = "linux"))]
pub fn reusable_digest(path: &Path) -> Option<[u8; 32]> {
    digest_cache::lookup(path, &Stamp::file(&fs::symlink_metadata(path).ok()?))
}
#[cfg(not(target_os = "linux"))]
pub fn save_digest_cache() {}

/// The SHA-256 of a file the snapshot does not cover, read at most once while its
/// stamp stays the same (see `digest_cache`). The stamp is checked around the read.
#[cfg(target_os = "linux")]
pub fn file_digest(path: &Path) -> io::Result<[u8; 32]> {
    let mut input = File::open(path)?;
    let stamp = Stamp::file(&input.metadata()?);
    if let Some(digest) = digest_cache::lookup(path, &stamp) { return Ok(digest); }
    let began = digest_cache::now();
    let mut content = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let count = input.read(&mut buffer)?;
        if count == 0 { break; }
        content.update(&buffer[..count]);
    }
    let digest: [u8; 32] = content.finalize().into();
    if stamp == Stamp::file(&input.metadata()?) { digest_cache::record(path, &stamp, digest, began); }
    Ok(digest)
}

#[cfg(not(target_os = "linux"))]
pub fn file_digest(path: &Path) -> io::Result<[u8; 32]> {
    let mut input = File::open(path)?;
    let mut content = Sha256::new();
    io::copy(&mut input, &mut content)?;
    Ok(content.finalize().into())
}

/// `file_digest` for a caller that already has the file's metadata: on a cache
/// hit a regular file costs one stat instead of an open plus a stat. `meta`
/// must describe `path` itself (a `symlink_metadata` result), not a symlink's
/// target.
#[cfg(target_os = "linux")]
pub fn file_digest_stamped(path: &Path, meta: &Metadata) -> io::Result<[u8; 32]> {
    if let Some(digest) = digest_cache::lookup(path, &Stamp::file(meta)) { return Ok(digest); }
    file_digest(path)
}

#[cfg(not(target_os = "linux"))]
pub fn file_digest_stamped(path: &Path, _meta: &Metadata) -> io::Result<[u8; 32]> {
    file_digest(path)
}

#[cfg(target_os = "linux")]
pub struct Snapshot {
    pub fingerprint: String,
    /// The fingerprint without the files a checkout VM reloads in place
    /// (`dev_reload`). Equal to `fingerprint` when nothing is reloadable. It keys
    /// the VM; `fingerprint` still selects and builds the SDK.
    pub base_fingerprint: String,
    files: BTreeMap<PathBuf, (Stamp, [u8; 32])>,
    directories: Vec<(PathBuf, Stamp)>,
    policy: (PathBuf, Stamp),
    /// The sorted fingerprint rows and what `refresh_reloadable` needs to
    /// re-derive them for a few files: the canonical root, the per-file and
    /// total byte limits, and the bytes counted.
    root: PathBuf,
    rows: Vec<(Vec<u32>, String, bool)>,
    file_bytes: u64,
    total_bytes: u64,
    bytes: u64,
}

#[cfg(target_os = "linux")]
fn fingerprints(rows: &[(Vec<u32>, String, bool)]) -> (String, String) {
    let digest = |prefix: &[u8], base: bool| {
        let mut hash = Sha256::new();
        hash.update(prefix);
        hash.update(b"[");
        for (index, (_, row, _)) in rows.iter().filter(|row| !(base && row.2)).enumerate() {
            if index != 0 { hash.update(b","); }
            hash.update(row.as_bytes());
        }
        hash.update(b"]");
        format!("{:x}", hash.finalize())
    };
    let full = digest(b"beam-lisp-engine-inputs-v1\0", false);
    // `scripts/sdk-inputs --base` computes the same bytes.
    let base = if rows.iter().any(|row| row.2) {
        digest(b"beam-lisp-engine-inputs-base-v1\0", true)
    } else {
        full.clone()
    };
    (full, base)
}

#[cfg(target_os = "linux")]
fn file_row(encoded: &str, executable: bool, digest: &[u8; 32]) -> String {
    let hex = digest.iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    format!("[{encoded},\"regular\",{executable},\"{hex}\"]")
}

#[cfg(target_os = "linux")]
impl Snapshot {
    pub fn capture(root: &Path) -> io::Result<Self> {
        let root = fs::canonicalize(root)?;
        if root.parent().is_none() || !root.is_dir() { return Err(invalid("invalid engine-input root")); }
        let policy_path = root.join("nix/engine-inputs.json");
        let policy_info = fs::symlink_metadata(&policy_path)?;
        if !policy_info.is_file() { return Err(invalid("engine-input policy must be a regular file")); }
        let policy_stamp = Stamp::file(&policy_info);
        let policy = Policy::read(&root)?;
        let (file_bytes, total_bytes) = (policy.file_bytes, policy.total_bytes);
        let mut capture = Capture { policy, reload: crate::dev_reload::Policy::read(&root), entries: 0, bytes: 0, seen: BTreeSet::new(),
            rows: Vec::new(), snapshot: Self { fingerprint: String::new(), base_fingerprint: String::new(), files: BTreeMap::new(), directories: Vec::new(), policy: (policy_path, policy_stamp),
                root: root.clone(), rows: Vec::new(), file_bytes, total_bytes, bytes: 0 } };
        capture.walk(&root, &[], 0)?;
        if capture.policy.roots.iter().any(|path| !capture.seen.contains(path.as_bytes())) {
            return Err(invalid("required engine-input root is missing"));
        }
        capture.rows.sort_by(|a, b| a.0.cmp(&b.0));
        let (full, base) = fingerprints(&capture.rows);
        capture.snapshot.fingerprint = full;
        capture.snapshot.base_fingerprint = base;
        capture.snapshot.rows = std::mem::take(&mut capture.rows);
        capture.snapshot.bytes = capture.bytes;
        capture.snapshot.verify()?;
        Ok(capture.snapshot)
    }

    /// M4: re-derive this snapshot after edits to `paths`, each a file it
    /// already holds as a RELOADABLE row (`dev_reload`), by reading only those
    /// files. The result is what a fresh `capture` would compute when nothing
    /// else changed; the caller (the generation service) knows that from the
    /// kernel's events and asks only then. `Ok(false)` (nothing changed here)
    /// means a path is not such a row, the policy moved, or a limit was hit:
    /// the caller captures the whole tree instead. The base fingerprint, and
    /// so the runtime token, cannot change this way; that is checked too.
    pub fn refresh_reloadable(&mut self, paths: &[PathBuf]) -> io::Result<bool> {
        use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
        let Some(reload) = crate::dev_reload::Policy::read(&self.root) else { return Ok(false) };
        if Stamp::file(&fs::symlink_metadata(&self.policy.0)?) != self.policy.1 { return Ok(false); }
        let mut rows = self.rows.clone();
        let mut files = Vec::new();
        let mut bytes = self.bytes;
        for path in paths {
            if !self.files.contains_key(path) {
                // A file that came and went (an editor's or `sed -i`'s
                // temporary, renamed over the source): neither this snapshot
                // nor a fresh capture holds it. Anything else is a new input.
                match fs::symlink_metadata(path) {
                    Err(error) if error.kind() == io::ErrorKind::NotFound => continue,
                    _ => return Ok(false),
                }
            }
            let Some(name) = path.strip_prefix(&self.root).ok().and_then(Path::to_str) else { return Ok(false) };
            if !reload.reloadable(name) { return Ok(false); }
            let key = points(name.as_bytes());
            let Ok(index) = rows.binary_search_by(|row| row.0.cmp(&key)) else { return Ok(false) };
            if !rows[index].2 { return Ok(false); }
            let info = fs::symlink_metadata(path)?;
            if !info.is_file() || info.len() > self.file_bytes { return Ok(false); }
            let mut input = OpenOptions::new().read(true).custom_flags(libc::O_NOFOLLOW).open(path)?;
            let stamp = Stamp::file(&input.metadata()?);
            if stamp != Stamp::file(&info) { return Ok(false); }
            let digest = match digest_cache::lookup(path, &stamp) {
                Some(digest) => digest,
                None => {
                    let began = digest_cache::now();
                    let mut hash = Sha256::new();
                    let mut buffer = [0u8; 65536];
                    let mut count = 0u64;
                    loop {
                        let read = input.read(&mut buffer)?;
                        if read == 0 { break; }
                        count += read as u64;
                        if count > self.file_bytes { return Ok(false); }
                        hash.update(&buffer[..read]);
                    }
                    if stamp != Stamp::file(&input.metadata()?) || stamp != Stamp::file(&fs::symlink_metadata(path)?) || count != info.len() {
                        return Ok(false);
                    }
                    let digest: [u8; 32] = hash.finalize().into();
                    digest_cache::record(path, &stamp, digest, began);
                    digest
                }
            };
            let old = self.files[path].0.size;
            bytes = bytes - old.min(bytes) + info.len();
            if bytes > self.total_bytes { return Ok(false); }
            rows[index].1 = file_row(&json_name(&key), info.mode() & 0o100 != 0, &digest);
            files.push((path.clone(), stamp, digest));
        }
        let (full, base) = fingerprints(&rows);
        if base != self.base_fingerprint { return Ok(false); }
        for (path, stamp, digest) in files {
            // An in-place write leaves its directory's stamp; refresh it anyway
            // so `verify` describes the tree this snapshot now stands for.
            if let Some(parent) = path.parent() {
                if let Some(entry) = self.directories.iter_mut().find(|(dir, _)| dir == parent) {
                    entry.1 = Stamp::directory(&fs::symlink_metadata(parent)?);
                }
            }
            self.files.insert(path, (stamp, digest));
        }
        self.rows = rows;
        self.bytes = bytes;
        self.fingerprint = full;
        Ok(true)
    }

    // A command may reuse only the digest of this exact captured pathname.
    // External paths and generated/non-selected files are read independently.
    pub fn digest(&self, path: &Path) -> Option<&[u8; 32]> {
        self.files.get(path).map(|(_, digest)| digest)
    }

    pub fn verify(&self) -> io::Result<()> {
        if Stamp::file(&fs::symlink_metadata(&self.policy.0)?) != self.policy.1 {
            return Err(invalid("engine-input policy changed during capture"));
        }
        for (path, (stamp, _)) in &self.files {
            if Stamp::file(&fs::symlink_metadata(path)?) != *stamp {
                return Err(invalid("engine input changed after capture"));
            }
        }
        for (path, stamp) in &self.directories {
            if Stamp::directory(&fs::symlink_metadata(path)?) != *stamp {
                return Err(invalid("engine input directory changed after capture"));
            }
        }
        Ok(())
    }
}

#[cfg(target_os = "linux")]
struct Capture {
    policy: Policy, reload: Option<crate::dev_reload::Policy>, entries: u64, bytes: u64, seen: BTreeSet<Vec<u8>>,
    rows: Vec<(Vec<u32>, String, bool)>, snapshot: Snapshot,
}

#[cfg(target_os = "linux")]
impl Capture {
    fn walk(&mut self, directory: &Path, relative: &[u8], depth: u64) -> io::Result<()> {
        use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
        if depth > self.policy.depth { return Err(invalid("engine-input depth limit exceeded")); }
        let before = fs::symlink_metadata(directory)?;
        if !before.is_dir() { return Err(invalid("engine input directory changed type")); }
        let mut children = Vec::new();
        for entry in fs::read_dir(directory)? {
            self.entries += 1;
            if self.entries > self.policy.entries { return Err(invalid("engine-input entry limit exceeded")); }
            children.push(entry?);
        }
        children.sort_by_key(|entry| points(entry.file_name().as_encoded_bytes()));
        for entry in children {
            let name = entry.file_name();
            let name = name.as_encoded_bytes();
            let mut path = relative.to_vec();
            if !path.is_empty() { path.push(b'/'); }
            path.extend_from_slice(name);
            if self.policy.reserved.iter().any(|value| value.as_bytes() == name)
                || (name == b"target" && self.policy.targets.iter().any(|value| beneath(value.as_bytes(), &path)))
                || self.policy.excluded.iter().any(|value| beneath(value.as_bytes(), &path)) { continue; }
            if !self.policy.roots.iter().any(|value| beneath(value.as_bytes(), &path) || beneath(&path, value.as_bytes())) { continue; }
            let physical = entry.path();
            let info = fs::symlink_metadata(&physical)?;
            self.seen.insert(path.clone());
            let key = points(&path);
            let encoded = json_name(&key);
            // Reloadable rows stay in `fingerprint` and leave `base_fingerprint`.
            let relative = std::str::from_utf8(&path).ok();
            let held = |file: bool| match (&self.reload, relative) {
                (Some(reload), Some(name)) => if file { reload.reloadable(name) } else { reload.reload_directory(name) },
                _ => false,
            };
            if info.is_dir() {
                let held = held(false);
                self.rows.push((key, format!("[{encoded},\"directory\"]"), held));
                self.walk(&physical, &path, depth + 1)?;
            } else if info.is_file() {
                if info.len() > self.policy.file_bytes { return Err(invalid("engine-input file size limit exceeded")); }
                let mut input = OpenOptions::new().read(true).custom_flags(libc::O_NOFOLLOW).open(&physical)?;
                let stamp = Stamp::file(&input.metadata()?);
                if stamp != Stamp::file(&info) { return Err(invalid("engine input changed during open")); }
                let digest: [u8; 32] = if let Some(digest) = digest_cache::lookup(&physical, &stamp) {
                    self.bytes += info.len();
                    if self.bytes > self.policy.total_bytes { return Err(invalid("engine-input byte limit exceeded")); }
                    digest
                } else {
                    let began = digest_cache::now();
                    let mut hash = Sha256::new();
                    let mut buffer = [0u8; 65536];
                    let mut count = 0u64;
                    loop {
                        let read = input.read(&mut buffer)?;
                        if read == 0 { break; }
                        count += read as u64;
                        self.bytes += read as u64;
                        if count > self.policy.file_bytes || self.bytes > self.policy.total_bytes { return Err(invalid("engine-input byte limit exceeded")); }
                        hash.update(&buffer[..read]);
                    }
                    if stamp != Stamp::file(&input.metadata()?) || stamp != Stamp::file(&fs::symlink_metadata(&physical)?) || count != info.len() {
                        return Err(invalid("engine input changed while hashing"));
                    }
                    let digest: [u8; 32] = hash.finalize().into();
                    digest_cache::record(&physical, &stamp, digest, began);
                    digest
                };
                let executable = info.mode() & 0o100 != 0;
                let held = held(true);
                self.rows.push((key, file_row(&encoded, executable, &digest), held));
                self.snapshot.files.insert(physical, (stamp, digest));
            } else { return Err(invalid("selected engine input must be a regular file or directory")); }
        }
        let stamp = Stamp::directory(&before);
        if stamp != Stamp::directory(&fs::symlink_metadata(directory)?) {
            return Err(invalid("engine input directory changed while hashing"));
        }
        self.snapshot.directories.push((directory.to_owned(), stamp));
        Ok(())
    }
}

#[cfg(not(target_os = "linux"))]
pub struct Snapshot { pub fingerprint: String, pub base_fingerprint: String }

#[cfg(not(target_os = "linux"))]
impl Snapshot {
    pub fn capture(_: &Path) -> io::Result<Self> { Err(invalid("checkout engine capture requires Linux")) }
    pub fn digest(&self, _: &Path) -> Option<&[u8; 32]> { None }
    pub fn verify(&self) -> io::Result<()> { Ok(()) }
}
