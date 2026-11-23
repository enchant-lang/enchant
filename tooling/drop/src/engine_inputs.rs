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
#[cfg(target_os = "linux")]
mod digest_cache {
    use super::Stamp;
    use std::collections::HashMap;
    use std::io::{Read, Write};
    use std::path::{Path, PathBuf};
    use std::sync::Mutex;

    const MAGIC: &[u8; 16] = b"bl-digests-v1\0\0\0";
    const RACY_SECONDS: i64 = 2;
    const MAX_ENTRIES: usize = 200_000;

    struct Cache { path: Option<PathBuf>, rows: HashMap<Vec<u8>, (Stamp, [u8; 32])>, dirty: bool }

    static CACHE: Mutex<Option<Cache>> = Mutex::new(None);

    fn enabled() -> bool { std::env::var_os("BL_CHECKOUT_DIGEST_CACHE").is_none_or(|v| v != "0") }

    fn location() -> Option<PathBuf> {
        let base = std::env::var_os("XDG_CACHE_HOME").filter(|v| !v.is_empty()).map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".cache")))?;
        Some(base.join("beam-lisp/checkout-digests-v1.bin"))
    }

    fn take_i64(bytes: &[u8], at: &mut usize) -> Option<i64> {
        let v = i64::from_le_bytes(bytes.get(*at..*at + 8)?.try_into().ok()?); *at += 8; Some(v)
    }

    fn load(path: &Path) -> HashMap<Vec<u8>, (Stamp, [u8; 32])> {
        let mut rows = HashMap::new();
        let mut bytes = Vec::new();
        if std::fs::File::open(path).and_then(|mut f| f.read_to_end(&mut bytes)).is_err()
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
                Some((name, (Stamp { device, inode, size, mode, mtime, ctime }, digest)))
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
        with(|c| c.rows.get(path.as_os_str().as_encoded_bytes())
            .filter(|(seen, _)| seen == stamp).map(|(_, d)| *d)).flatten()
    }

    /// The wall clock as (seconds, nanoseconds), taken before a read begins.
    pub fn now() -> (i64, i64) {
        let d = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default();
        (d.as_secs() as i64, d.subsec_nanos() as i64)
    }

    pub fn record(path: &Path, stamp: &Stamp, digest: [u8; 32], read_began: (i64, i64)) {
        if (stamp.newest().0 + RACY_SECONDS, stamp.newest().1) >= read_began { return; }
        with(|c| {
            if c.rows.len() < MAX_ENTRIES {
                c.rows.insert(path.as_os_str().as_encoded_bytes().to_vec(), (stamp.clone(), digest));
                c.dirty = true;
            }
        });
    }

    /// Persist new digests, dropping rows whose file is gone. Best effort: a
    /// cache that cannot be written only costs the next command its reads.
    pub fn save() {
        let _ = with(|c| -> std::io::Result<()> {
            let Some(path) = c.path.clone() else { return Ok(()) };
            if !c.dirty { return Ok(()); }
            c.rows.retain(|name, _| { use std::os::unix::ffi::OsStrExt; Path::new(std::ffi::OsStr::from_bytes(name)).exists() });
            let mut out = Vec::with_capacity(16 + c.rows.len() * 140);
            out.extend_from_slice(MAGIC);
            for (name, (s, digest)) in &c.rows {
                for v in [name.len() as i64] { out.extend_from_slice(&v.to_le_bytes()); }
                out.extend_from_slice(name);
                for v in [s.device as i64, s.inode as i64, s.size as i64, s.mode as i64, s.mtime.0, s.mtime.1, s.ctime.0, s.ctime.1] {
                    out.extend_from_slice(&v.to_le_bytes());
                }
                out.extend_from_slice(digest);
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
}

#[cfg(target_os = "linux")]
pub use digest_cache::save as save_digest_cache;

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
        let mut capture = Capture { policy, reload: crate::dev_reload::Policy::read(&root), entries: 0, bytes: 0, seen: BTreeSet::new(),
            rows: Vec::new(), snapshot: Self { fingerprint: String::new(), base_fingerprint: String::new(), files: BTreeMap::new(), directories: Vec::new(), policy: (policy_path, policy_stamp) } };
        capture.walk(&root, &[], 0)?;
        if capture.policy.roots.iter().any(|path| !capture.seen.contains(path.as_bytes())) {
            return Err(invalid("required engine-input root is missing"));
        }
        capture.rows.sort_by(|a, b| a.0.cmp(&b.0));
        let digest = |prefix: &[u8], base: bool| {
            let mut hash = Sha256::new();
            hash.update(prefix);
            hash.update(b"[");
            for (index, (_, row, _)) in capture.rows.iter().filter(|row| !(base && row.2)).enumerate() {
                if index != 0 { hash.update(b","); }
                hash.update(row.as_bytes());
            }
            hash.update(b"]");
            format!("{:x}", hash.finalize())
        };
        capture.snapshot.fingerprint = digest(b"beam-lisp-engine-inputs-v1\0", false);
        // `scripts/sdk-inputs --base` computes the same bytes.
        capture.snapshot.base_fingerprint = if capture.rows.iter().any(|row| row.2) {
            digest(b"beam-lisp-engine-inputs-base-v1\0", true)
        } else {
            capture.snapshot.fingerprint.clone()
        };
        capture.snapshot.verify()?;
        Ok(capture.snapshot)
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
                let hex = digest.iter().map(|byte| format!("{byte:02x}")).collect::<String>();
                let executable = info.mode() & 0o100 != 0;
                let held = held(true);
                self.rows.push((key, format!("[{encoded},\"regular\",{executable},\"{hex}\"]"), held));
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
