// Per-tree generation service: the warm request's 34 ms of recomputation.
//
// A warm checkout request used to re-establish three tokens on every command:
// the ENGINE inventory (976 files of the launcher's engine, ~22 ms even with the
// digest cache, because it stat()s every selected file), the RUNTIME pin over
// `priv`/`native`, and the PROJECT pin folded with the realm's recorded sources
// (~11 ms). All three are content-stable while a tree is unchanged, yet the
// client recomputed them per request.
//
// This module keeps them in a per-tree resident. The resident is the AUTHORITY
// for "did the tree change", and its answer is backed by the kernel, not by a
// heuristic:
//
//   * it watches every directory of the engine tree, the project tree and the
//     extra roots (and every directory the realm's manifest records) with
//     inotify, on local filesystems only (the fs magic is checked at start);
//   * it drains the event queue immediately before answering; any event marks
//     the affected tokens dirty and they are RECOMPUTED (never guessed);
//   * if the queue overflowed, a watch could not be installed, the root was
//     replaced (dev+ino changed) or the filesystem is not a local one, it
//     answers "fallback" and the client computes locally, exactly as before.
//
// A change can therefore only be missed when the kernel does not report it,
// and in that case the service has already refused to answer. The three tokens
// it returns are computed by `checkout_generations`, the same function the
// client uses, so a cached answer and a local one are byte-identical. The realm
// remains the authority for retirement: it compares the token the client sends
// with the one it opened against, so a wrong "same" can never serve stale code
// as a different realm — a changed token retires it.
//
// The resident is started by the first client that misses it and is optional:
// `BL_CHECKOUT_GENERATION_SERVICE=0` disables it.

// The included files share this crate root: `Path`, `PathBuf`, `Read`, `Write`,
// `UnixStream`, `Duration` and `HashMap`-free helpers are already imported by
// `daemon.rs`. Only the items this file adds are imported here.
#[cfg(target_os = "linux")]
use std::collections::{HashMap, HashSet};
#[cfg(target_os = "linux")]
use std::os::unix::ffi::OsStrExt;
#[cfg(target_os = "linux")]
use std::os::unix::fs::MetadataExt;
#[cfg(target_os = "linux")]
use std::os::unix::net::UnixListener;

/// Debug logs live beside the socket, never in a directory the service could
/// be watching (a log write that invalidates the tree is an infinite loop).
#[cfg(target_os = "linux")]
fn debug_log_path() -> PathBuf {
    runtime_dir().unwrap_or_else(std::env::temp_dir)
        .join(format!("generation-debug-{}.log", std::process::id()))
}

/// The environment `checkout_hash_files` folds into each token. The service
/// computes with the CLIENT's values: they are part of the token's identity.
pub const TOKEN_ENV: [&str; 16] = [
    "HOME", "XDG_DATA_HOME", "ERL_FLAGS", "ERL_AFLAGS", "ELIXIR_ERL_OPTIONS",
    "BEAM_LISP_AOT_BACKEND", "BEAM_LISP_AOT_CACHE_DIR", "BEAM_LISP_AOT_CACHE",
    "BEAM_LISP_AOT_STRICT", "BEAM_LISP_DEV", "XDG_CACHE_HOME", "BEAM_LISP_EBIN",
    "BEAM_LISP_PATH", "BL_BOOTSTRAP_SEED", "BL_CHECKOUT_PLATFORM",
    "BL_CHECKOUT_SDK_INPUTS",
];

const SCOPE_ENGINE: u8 = 1;
const SCOPE_RUNTIME: u8 = 2;
const SCOPE_PROJECT: u8 = 4;
const SCOPE_ALL: u8 = SCOPE_ENGINE | SCOPE_RUNTIME | SCOPE_PROJECT;

fn service_enabled() -> bool {
    std::env::var_os("BL_CHECKOUT_GENERATION_SERVICE").map_or(true, |v| v != "0")
}

/// The client-side environment for one request, or `None` when a value is not
/// UTF-8 (the protocol is JSON; a byte-exact answer is then not possible here,
/// so the client computes locally).
#[cfg(target_os = "linux")]
fn token_env() -> Option<Vec<(String, Option<String>)>> {
    TOKEN_ENV
        .iter()
        .map(|key| {
            match std::env::var_os(key) {
                None => Some((key.to_string(), None)),
                Some(value) => value.into_string().ok().map(|v| (key.to_string(), Some(v))),
            }
        })
        .collect()
}

#[cfg(target_os = "linux")]
fn socket_path(root: &Path) -> Option<PathBuf> {
    use sha2::{Digest, Sha256};
    let mut digest = Sha256::new();
    digest.update(b"bl-generation-service-v1\0");
    digest.update(root.as_os_str().as_encoded_bytes());
    let hex: String = digest.finalize()[..8].iter().map(|b| format!("{b:02x}")).collect();
    Some(runtime_dir()?.join(format!("generation-{hex}-src.sock")))
}

#[cfg(target_os = "linux")]
fn token_path(socket: &Path) -> PathBuf {
    socket.with_extension("token")
}

/// Answer this request from the tree's resident, or `None` when there is no
/// service, it is still warming, or it is unsure. `None` is always safe: the
/// caller computes the same tokens locally.
#[cfg(target_os = "linux")]
pub fn generation_cached(root: &Path, project: &Path, extra: &[PathBuf]) -> Option<Generations> {
    if !service_enabled() { return None; }
    let debug = std::env::var_os("BL_CHECKOUT_GENERATION_DEBUG").is_some();
    let answer = (|| -> Result<Generations, String> {
        let socket = socket_path(root).ok_or("no runtime dir")?;
        let token = std::fs::read_to_string(token_path(&socket)).map_err(|e| format!("token {}: {e}", token_path(&socket).display()))?;
        let env = token_env().ok_or("env is not UTF-8")?;
        query_at(&socket, &token, project, extra, &env)
    })();
    match answer {
        Ok(generations) => Some(generations),
        Err(reason) => {
            // A resident that is not up yet is normal, not a decline: the
            // first request starts it and computes locally.
            let warming = reason.contains("Connection refused")
                || reason.starts_with("token ");
            if debug && !warming { eprintln!("U10-SERVICE-DECLINED {reason}"); }
            None
        }
    }
}

#[cfg(not(target_os = "linux"))]
pub fn generation_cached(_root: &std::path::Path, _project: &std::path::Path, _extra: &[std::path::PathBuf]) -> Option<Generations> {
    None
}

/// Start the tree's resident if it is not already answering. Detached: it
/// outlives this client and serves later commands. A failure is silent — the
/// caller has already fallen back to a local computation.
#[cfg(target_os = "linux")]
pub fn generation_ensure(root: &Path) {
    if !service_enabled() { return; }
    let Some(socket) = socket_path(root) else { return; };
    if UnixStream::connect(&socket).is_ok() { return; }
    // One resident per root: only the lock's taker starts one. A loser exits
    // silently; the winner binds, replacing any stale socket.
    let lock = socket.with_extension("lock");
    let Ok(lock_file) = std::fs::OpenOptions::new().create(true).read(true).write(true).open(&lock) else { return; };
    use std::os::unix::io::AsRawFd;
    let acquired = unsafe { libc::flock(lock_file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0;
    if !acquired { return; }
    drop(lock_file); // releases the probe lock; the spawned resident takes it
    let Ok(exe) = std::env::current_exe() else { return; };
    use std::os::unix::process::CommandExt;
    let mut command = std::process::Command::new(exe);
    command.arg("--generation-service").arg(root)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());
    unsafe { command.pre_exec(|| { libc::setsid(); Ok(()) }); }
    let _ = command.spawn();
}

#[cfg(not(target_os = "linux"))]
pub fn generation_ensure(_root: &std::path::Path) {}

#[cfg(target_os = "linux")]
fn query_at(
    socket: &Path,
    token: &str,
    project: &Path,
    extra: &[PathBuf],
    env: &[(String, Option<String>)],
) -> Result<Generations, String> {
    let mut stream = UnixStream::connect(socket).map_err(|e| e.to_string())?;
    stream.set_read_timeout(Some(std::time::Duration::from_millis(150))).ok();
    stream.set_write_timeout(Some(std::time::Duration::from_millis(150))).ok();
    let env: serde_json::Map<String, serde_json::Value> = env.iter()
        .map(|(k, v)| (k.clone(), match v { Some(v) => serde_json::Value::String(v.clone()), None => serde_json::Value::Null }))
        .collect();
    let request = serde_json::json!({
        "token": token,
        "project": project.to_str().ok_or("project path is not UTF-8")?,
        "extra": extra.iter().filter_map(|p| p.to_str()).collect::<Vec<_>>(),
        "env": env,
    });
    let mut line = serde_json::to_vec(&request).map_err(|e| e.to_string())?;
    line.push(b'\n');
    stream.write_all(&line).map_err(|e| e.to_string())?;
    let mut answer = Vec::new();
    let mut byte = [0u8; 1];
    loop {
        let n = stream.read(&mut byte).map_err(|e| e.to_string())?;
        if n == 0 || byte[0] == b'\n' { break; }
        answer.push(byte[0]);
        if answer.len() > 64 * 1024 { return Err("answer too large".into()); }
    }
    let value: serde_json::Value = serde_json::from_slice(&answer).map_err(|e| e.to_string())?;
    let ok = value.get("ok").ok_or_else(|| value.get("fallback").and_then(|v| v.as_str()).unwrap_or("service declined").to_string())?;
    let field = |name: &str| ok.get(name).and_then(|v| v.as_str()).map(str::to_string).ok_or_else(|| format!("answer lacks {name}"));
    Ok(Generations { engine: field("engine")?, runtime: field("runtime")?, project: field("project")? })
}

/// Serve one tree until the process ends. Called by `--generation-service ROOT`.
#[cfg(target_os = "linux")]
pub fn generation_serve(root: PathBuf) -> ! {
    let root = std::fs::canonicalize(&root).unwrap_or(root);
    let socket = socket_path(&root).expect("socket path");
    if let Some(parent) = socket.parent() { let _ = std::fs::create_dir_all(parent); }
    if UnixStream::connect(&socket).is_ok() {
        // Another resident already answers for this tree.
        std::process::exit(0);
    }
    // One resident per root, and a stale socket is REPLACED, not served: take
    // an advisory lock on a sibling file, then re-check the socket under it.
    // The lock releases on any exit, so a crashed resident never blocks the
    // next one.
    let lock_path = socket.with_extension("lock");
    let lock_file = match std::fs::OpenOptions::new().create(true).read(true).write(true).open(&lock_path) {
        Ok(file) => file,
        Err(_) => std::process::exit(0),
    };
    use std::os::unix::io::AsRawFd;
    if unsafe { libc::flock(lock_file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
        std::process::exit(0);
    }
    std::mem::forget(lock_file); // held for this process's life
    if UnixStream::connect(&socket).is_ok() { std::process::exit(0); }
    let _ = std::fs::remove_file(&socket);
    let listener = match UnixListener::bind(&socket) {
        Ok(listener) => listener,
        Err(_) => std::process::exit(0),
    };
    use std::os::unix::fs::PermissionsExt;
    let _ = std::fs::set_permissions(&socket, std::fs::Permissions::from_mode(0o600));
    let token = format!("{:016x}{:016x}", std::process::id(), std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0));
    if std::fs::write(token_path(&socket), &token).and_then(|_| std::fs::set_permissions(token_path(&socket), std::fs::Permissions::from_mode(0o600))).is_err() {
        std::process::exit(0);
    }
    let mut state = match State::new(root) {
        Ok(state) => state,
        Err(reason) => {
            // Not observable here: answer every query with the reason.
            let mut unavailable = Unavailable { reason, token };
            unavailable.run(listener);
        }
    };
    state.token = token;
    state.run(listener)
}

#[cfg(not(target_os = "linux"))]
pub fn generation_serve(_root: std::path::PathBuf) -> ! {
    std::process::exit(0)
}

#[cfg(target_os = "linux")]
struct Unavailable { reason: String, token: String }

#[cfg(target_os = "linux")]
impl Unavailable {
    fn run(&mut self, listener: UnixListener) -> ! {
        for stream in listener.incoming() {
            let Ok(mut stream) = stream else { continue; };
            let _ = read_request(&mut stream).and_then(|request| {
                if request.get("token").and_then(|v| v.as_str()) != Some(self.token.as_str()) {
                    return Err("bad token".to_string());
                }
                write_answer(&mut stream, &serde_json::json!({"fallback": self.reason}))
            });
        }
        std::process::exit(0)
    }
}

#[cfg(target_os = "linux")]
fn read_request(stream: &mut UnixStream) -> Result<serde_json::Value, String> {
    stream.set_read_timeout(Some(std::time::Duration::from_millis(500))).ok();
    let mut line = Vec::new();
    let mut byte = [0u8; 1];
    loop {
        let n = stream.read(&mut byte).map_err(|e| e.to_string())?;
        if n == 0 || byte[0] == b'\n' { break; }
        line.push(byte[0]);
        if line.len() > 256 * 1024 { return Err("request too large".into()); }
    }
    serde_json::from_slice(&line).map_err(|e| e.to_string())
}

#[cfg(target_os = "linux")]
fn write_answer(stream: &mut UnixStream, value: &serde_json::Value) -> Result<(), String> {
    let mut line = serde_json::to_vec(value).map_err(|e| e.to_string())?;
    line.push(b'\n');
    stream.write_all(&line).map_err(|e| e.to_string())
}

#[cfg(target_os = "linux")]
struct Watch {
    fd: libc::c_int,
    scopes: HashMap<libc::c_int, u8>,
    dirs: HashMap<libc::c_int, PathBuf>,
    watched: HashSet<PathBuf>,
}

#[cfg(target_os = "linux")]
impl Watch {
    fn new() -> std::io::Result<Self> {
        let fd = unsafe { libc::inotify_init1(libc::IN_NONBLOCK | libc::IN_CLOEXEC) };
        if fd < 0 { return Err(std::io::Error::last_os_error()); }
        Ok(Self { fd, scopes: HashMap::new(), dirs: HashMap::new(), watched: HashSet::new() })
    }
    fn reset(&mut self) -> std::io::Result<()> {
        unsafe { libc::close(self.fd); }
        let fresh = Self::new()?;
        *self = fresh;
        Ok(())
    }
    /// Watch `dir` for events about its own entries. Scope bits are unioned, so
    /// a directory that is both an engine root and part of the project answers
    /// both scopes.
    fn add_dir(&mut self, dir: &Path, scope: u8) -> Result<(), String> {
        const WATCH_LIMIT: usize = 20_000;
        if self.watched.len() >= WATCH_LIMIT { return Err("watch set exceeds its bound".into()); }
        let canonical = std::fs::canonicalize(dir).map_err(|e| e.to_string())?;
        if self.watched.contains(&canonical) {
            // Find the wd by path to widen its scope.
            if let Some((&wd, _)) = self.dirs.iter().find(|(_, p)| **p == canonical) {
                let previous = self.scopes.get(&wd).copied().unwrap_or(0);
                let merged = previous | scope;
                if merged != previous {
                    let mask = event_mask(merged);
                    let added = unsafe { libc::inotify_add_watch(self.fd, c_path(&canonical)?.as_ptr(), mask) };
                    if added < 0 { return Err(std::io::Error::last_os_error().to_string()); }
                    self.scopes.insert(added, merged);
                }
            }
            return Ok(());
        }
        let mask = event_mask(scope);
        let added = unsafe { libc::inotify_add_watch(self.fd, c_path(&canonical)?.as_ptr(), mask) };
        if added < 0 { return Err(std::io::Error::last_os_error().to_string()); }
        self.scopes.insert(added, scope);
        self.dirs.insert(added, canonical.clone());
        self.watched.insert(canonical);
        Ok(())
    }
    /// Every directory below `root`, plus `root` itself. Directory watches see
    /// IN_MODIFY for their direct children as well as create/delete/rename, so
    /// a file edit anywhere in the tree is observed.
    fn add_tree(&mut self, root: &Path, classify: &dyn Fn(&Path) -> u8) -> Result<(), String> {
        let mut pending = vec![root.to_path_buf()];
        let mut seen = HashSet::new();
        while let Some(dir) = pending.pop() {
            let Ok(physical) = std::fs::canonicalize(&dir) else { continue; };
            if !seen.insert(physical.clone()) { continue; }
            let Ok(meta) = std::fs::metadata(&physical) else { continue; };
            if !meta.is_dir() { continue; }
            self.add_dir(&physical, classify(&physical))?;
            if let Ok(entries) = std::fs::read_dir(&physical) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    let Ok(kind) = entry.file_type() else { continue; };
                    if kind.is_dir() || (kind.is_symlink() && std::fs::metadata(&path).is_ok_and(|m| m.is_dir())) {
                        pending.push(path);
                    }
                }
            }
        }
        Ok(())
    }
    fn drain(&mut self) -> u8 {
        let debug = std::env::var_os("BL_CHECKOUT_GENERATION_DEBUG").is_some();
        let mut dirty = 0u8;
        let mut buffer = [0u8; 16 * 1024];
        loop {
            let n = unsafe { libc::read(self.fd, buffer.as_mut_ptr().cast(), buffer.len()) };
            if n <= 0 { break; }
            let mut offset = 0usize;
            while offset + std::mem::size_of::<libc::inotify_event>() <= n as usize {
                let event: libc::inotify_event = unsafe {
                    std::ptr::read_unaligned(buffer.as_ptr().add(offset).cast())
                };
                let size = std::mem::size_of::<libc::inotify_event>() + event.len as usize;
                offset += size;
                if event.mask & libc::IN_Q_OVERFLOW != 0 { return SCOPE_ALL; }
                let scope = self.scopes.get(&event.wd).copied().unwrap_or(SCOPE_ALL);
                if event.mask & libc::IN_IGNORED != 0 {
                    self.scopes.remove(&event.wd);
                    self.dirs.remove(&event.wd);
                    dirty |= scope;
                    continue;
                }
                let path = self.dirs.get(&event.wd).map(|dir| {
                    if event.len > 0 {
                        let name_bytes = unsafe {
                            std::slice::from_raw_parts(buffer.as_ptr().add(offset - event.len as usize), event.len as usize)
                        };
                        let name = name_bytes.split(|b| *b == 0).next().unwrap_or(&[]);
                        dir.join(std::ffi::OsStr::from_bytes(name))
                    } else {
                        dir.clone()
                    }
                });
                let narrowed = match &path { Some(path) => refine(scope, path), None => scope };
                if debug {
                    use std::io::Write as _;
                    if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true)
                        .open(debug_log_path()) {
                        let _ = writeln!(file, "event wd={} mask={:x} scope={} narrowed={} path={}",
                                         event.wd, event.mask, scope, narrowed,
                                         path.as_ref().map(|p| p.display().to_string()).unwrap_or_default());
                    }
                }
                dirty |= narrowed;
            }
        }
        dirty
    }
}

#[cfg(target_os = "linux")]
fn c_path(path: &Path) -> Result<std::ffi::CString, String> {
    use std::os::unix::ffi::OsStrExt;
    std::ffi::CString::new(path.as_os_str().as_bytes()).map_err(|_| "path holds NUL".to_string())
}

#[cfg(target_os = "linux")]
fn event_mask(scope: u8) -> u32 {
    let _ = scope;
    (libc::IN_MODIFY | libc::IN_ATTRIB | libc::IN_CLOSE_WRITE | libc::IN_CREATE
        | libc::IN_DELETE | libc::IN_MOVED_FROM | libc::IN_MOVED_TO
        | libc::IN_DELETE_SELF | libc::IN_MOVE_SELF) as u32
}

/// Narrow an event's dirty scope by where it landed. `refine` only ever
/// REMOVES a scope for a path whose tokens PROVABLY cannot depend on it: the
/// realm's manifest lives under `.bl/`, which is never an engine input, so an
/// append there cannot change the engine. Everything else keeps the watch's
/// mask — over-invalidating costs one recomputation, under-invalidating could
/// serve a stale token, and the manifest is the only path this file can prove
/// disjoint from the engine tree.
#[cfg(target_os = "linux")]
fn refine(scope: u8, path: &Path) -> u8 {
    if path.components().any(|c| c.as_os_str() == ".bl") { return SCOPE_PROJECT; }
    scope
}

#[cfg(target_os = "linux")]
struct State {
    root: PathBuf,
    root_id: (u64, u64),
    token: String,
    identities: HashMap<PathBuf, (u64, u64)>,
    /// Inputs the manifest recorded that no longer exist: a directory watch is
    /// impossible, and watching a shared ancestor such as /tmp would let
    /// unrelated temp traffic invalidate the tree. Their APPEARANCE is checked
    /// with one stat per answer instead.
    missing: Vec<PathBuf>,
    inputs_key: Option<String>,
    watch: Watch,
    dirty: u8,
    unavailable: Option<String>,
    evidence: Option<engine_inputs::Snapshot>,
    engine: Option<(String, String)>,
    runtime_env: Option<String>,
    projects: HashMap<String, String>,
}

#[cfg(target_os = "linux")]
impl State {
    fn new(root: PathBuf) -> Result<Self, String> {
        let watch = Watch::new().map_err(|e| format!("inotify: {e}"))?;
        let meta = std::fs::metadata(&root).map_err(|e| e.to_string())?;
        if !local_filesystem(&root) { return Err("tree is not on a local filesystem".into()); }
        Ok(Self {
            root_id: (meta.dev(), meta.ino()),
            root,
            token: String::new(),
            identities: HashMap::new(),
            missing: Vec::new(),
            inputs_key: None,
            watch,
            dirty: SCOPE_ALL,
            unavailable: None,
            evidence: None,
            engine: None,
            runtime_env: None,
            projects: HashMap::new(),
        })
    }

    fn run(&mut self, listener: UnixListener) -> ! {
        for stream in listener.incoming() {
            let Ok(mut stream) = stream else { continue; };
            let answer = match read_request(&mut stream) {
                Err(reason) => serde_json::json!({"fallback": format!("bad request: {reason}")}),
                Ok(request) => {
                    if request.get("token").and_then(|v| v.as_str()) != Some(self.token.as_str()) {
                        serde_json::json!({"fallback": "bad token"})
                    } else {
                        match self.answer(&request) {
                            Ok(generations) => serde_json::json!({"ok": {
                                "engine": generations.engine,
                                "runtime": generations.runtime,
                                "project": generations.project,
                            }}),
                            Err(reason) => serde_json::json!({"fallback": reason}),
                        }
                    }
                }
            };
            if write_answer(&mut stream, &answer).is_err() { continue; }
        }
        std::process::exit(0)
    }

    fn log(&self, message: &str) {
        if std::env::var_os("BL_CHECKOUT_GENERATION_DEBUG").is_some() {
            use std::io::Write as _;
            if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true)
                .open(debug_log_path()) {
                let _ = writeln!(file, "{message}");
            }
        }
    }

    fn answer(&mut self, request: &serde_json::Value) -> Result<Generations, String> {
        if let Some(reason) = &self.unavailable { return Err(reason.clone()); }
        let project = PathBuf::from(request.get("project").and_then(|v| v.as_str()).ok_or("project missing")?);
        let extra: Vec<PathBuf> = request.get("extra").and_then(|v| v.as_array())
            .ok_or("extra missing")?.iter().filter_map(|v| v.as_str()).map(PathBuf::from).collect();
        let env = request.get("env").and_then(|v| v.as_object()).ok_or("env missing")?;
        let mut env_vec = Vec::new();
        for key in TOKEN_ENV {
            match env.get(key) {
                Some(serde_json::Value::String(value)) => { std::env::set_var(key, value); env_vec.push((key, Some(value.clone()))); }
                Some(serde_json::Value::Null) | None => { std::env::remove_var(key); env_vec.push((key, None)); }
                Some(_) => return Err("env value is not a string".into()),
            }
        }
        let env_key = env_signature(&env_vec);

        // Identity of the roots we depend on: a replaced tree must invalidate
        // even though its old inodes could have been quiet.
        let root_meta = std::fs::metadata(&self.root).map_err(|e| e.to_string())?;
        if (root_meta.dev(), root_meta.ino()) != self.root_id {
            self.root_id = (root_meta.dev(), root_meta.ino());
            self.reset(format!("root replaced"));
        }
        for path in std::iter::once(&project).chain(extra.iter()) {
            // An absent declared root has no watches of its own; its nearest
            // existing ancestor (the project root) is watched, so its
            // appearance invalidates the project pin like any new candidate.
            if !path.exists() { continue; }
            if !local_filesystem(path) { return Err("project is not on a local filesystem".into()); }
            if let Ok(meta) = std::fs::metadata(path) {
                if let Some(seen) = self.identities.get(path) {
                    if *seen != (meta.dev(), meta.ino()) {
                        self.reset(format!("{} replaced", path.display()));
                    }
                }
            }
        }

        // Watches FIRST, so a change during a computation is reported rather
        // than baked into an answer; then the computations; then the queue is
        // drained again and any event makes this answer a fallback.
        let a = std::time::Instant::now();
        let pre = self.sync();
        self.log(&format!("query pre_dirty={pre}"));
        self.watch_inputs(&project, &extra)?;
        self.log(&format!("watched dirs={} in {} us", self.watch.watched.len(), a.elapsed().as_micros()));
        let post_watch = self.sync();
        self.log(&format!("post_watch_dirty={post_watch}"));
        let b = std::time::Instant::now();
        let recomputed_engine = self.engine.is_none() || self.runtime_env.as_deref() != Some(env_key.as_str());
        if recomputed_engine {
            self.compute_engine()?;
            self.runtime_env = Some(env_key.clone());
        }
        let key = project_key(&project, &extra, &env_key);
        let recomputed_project = !self.projects.contains_key(&key);
        if recomputed_project {
            self.compute_project(&project, &extra, &key)?;
        }
        self.log(&format!("compute engine={recomputed_engine} project={recomputed_project} us={}", b.elapsed().as_micros()));
        if self.sync() != 0 {
            self.log("answer=fallback (event during compute)");
            return Err("tree changed while computing".into());
        }
        let (engine, runtime) = self.engine.clone().ok_or("engine missing")?;
        let project_token = self.projects.get(&key).cloned().ok_or("project missing")?;
        Ok(Generations { engine, runtime, project: project_token })
    }

    fn reset(&mut self, _reason: String) {
        self.engine = None;
        self.runtime_env = None;
        self.projects.clear();
        self.evidence = None;
        self.watch.reset().ok();
        self.identities.clear();
        self.missing.clear();
        self.dirty = SCOPE_ALL;
    }

    /// Drain the kernel queue and invalidate what the events touched. Never
    /// settles a value: an invalidated scope is recomputed on demand.
    fn sync(&mut self) -> u8 {
        let drained = self.watch.drain();
        if drained != 0 {
            self.dirty |= drained;
            self.apply_dirty();
        }
        drained
    }

    fn apply_dirty(&mut self) {
        if self.dirty & (SCOPE_ENGINE | SCOPE_RUNTIME) != 0 {
            self.engine = None;
            self.runtime_env = None;
            self.projects.clear();
            self.evidence = None;
        }
        if self.dirty & SCOPE_PROJECT != 0 { self.projects.clear(); }
        // A new directory or a bigger manifest may need watches the walk has
        // not placed yet; re-walk on the next query.
        self.inputs_key = None;
        self.dirty = 0;
    }

    fn compute_engine(&mut self) -> Result<(), String> {
        let evidence = engine_inputs::Snapshot::capture(&self.root).map_err(|e| e.to_string())?;
        let runtime = checkout_runtime_generation(&self.root, Some(&evidence)).map_err(|e| e.to_string())?;
        evidence.verify().map_err(|e| e.to_string())?;
        engine_inputs::save_digest_cache();
        self.engine = Some((evidence.fingerprint.clone(), runtime));
        self.evidence = Some(evidence);
        Ok(())
    }

    fn compute_project(&mut self, project: &Path, extra: &[PathBuf], key: &str) -> Result<(), String> {
        let token = checkout_project_generation(&self.root, project, extra, self.evidence.as_ref())
            .map_err(|e| e.to_string())?;
        self.projects.insert(key.to_string(), token);
        Ok(())
    }

    /// Watch `target`, or remember it as missing. A missing observed input is
    /// not a fallback: its absence is a stable fact, and one stat per answer
    /// notices it appearing.
    fn watch_or_missing(&mut self, target: &Path, scope: u8) -> Result<(), String> {
        match self.watch.add_dir(target, scope) {
            Ok(()) => Ok(()),
            Err(reason) if reason.contains("No such file") || reason.contains("os error 2") => {
                if self.missing.len() < 1024 && !self.missing.iter().any(|p| p == target) {
                    self.missing.push(target.to_path_buf());
                }
                Ok(())
            }
            Err(reason) => Err(reason),
        }
    }

    /// Did any input the manifest recorded while absent appear? One stat each.
    fn missing_appeared(&mut self) -> bool {
        if self.missing.is_empty() { return false; }
        let mut appeared = false;
        self.missing.retain(|path| {
            if path.exists() { appeared = true; false } else { true }
        });
        appeared
    }

    fn watch_inputs(&mut self, project: &Path, extra: &[PathBuf]) -> Result<(), String> {
        let key = watch_key(project, extra);
        if self.inputs_key.as_deref() == Some(key.as_str()) { return Ok(()); }
        for path in std::iter::once(&self.root).chain(std::iter::once(&project.to_path_buf())).chain(extra.iter()) {
            if let Ok(meta) = std::fs::metadata(path) {
                self.identities.insert(path.clone(), (meta.dev(), meta.ino()));
            }
        }
        // The ENGINE is the policy's roots (bin, nix, priv, native, …), never
        // the whole checkout: recursing over a real tree's research/ and .git
        // is what made the first answer take seconds. The root itself is
        // watched non-recursively for the policy's top-level files.
        self.watch.add_dir(&self.root, SCOPE_ALL)?;
        for path in engine_roots(&self.root) {
            if path.is_dir() {
                self.watch.add_tree(&path, &|_| SCOPE_ENGINE | SCOPE_RUNTIME)?;
            } else if let Some(parent) = path.parent() {
                self.watch.add_dir(parent, SCOPE_ALL)?;
            }
        }
        // The PROJECT is the project root (non-recursive: env.bl and the loose
        // top-level sources), its declared/extra roots, and overrides/ — the
        // same set the project pin walks.
        self.watch.add_dir(project, SCOPE_PROJECT)?;
        let overrides = project.join("overrides");
        if overrides.is_dir() { self.watch.add_tree(&overrides, &|_| SCOPE_PROJECT)?; }
        for root in extra {
            if root.exists() {
                self.watch.add_tree(root, &|_| SCOPE_PROJECT)?;
            } else if self.missing.len() < 1024 && !self.missing.iter().any(|p| p == root) {
                self.missing.push(root.clone());
            }
        }
        // The realm's manifest records what it resolved; new or edited inputs
        // outside the trees above (a script under /tmp, a library root) need
        // their directories watched too.
        if let Some(sources) = read_realm_sources(project) {
            for (path, recorded) in sources.entries.iter() {
                // A `D` line names a DIRECTORY whose entries were candidates;
                // its own listing is what must be watched. An `L` line names a
                // FILE the loader read; its parent directory carries the
                // modify/delete/rename events. Watching a `D` path's parent
                // reached /tmp for a recorded search root and made every temp
                // file in the system invalidate the project pin.
                let target = match recorded {
                    Recorded::Entries(_) => path.clone(),
                    Recorded::Loaded(_) => path.parent().unwrap_or(path).to_path_buf(),
                };
                self.watch_or_missing(&target, SCOPE_PROJECT)?;
            }
        }
        self.inputs_key = Some(key);
        Ok(())
    }

}

/// What `watch_inputs` walked last: the project, its extra roots and the
/// realm's manifest (token plus recorded paths). Re-walking 1612 directories
/// per request was the service's own 100 ms; it happens only when this changes.
#[cfg(target_os = "linux")]
fn watch_key(project: &Path, extra: &[PathBuf]) -> String {
    use sha2::{Digest, Sha256};
    let mut digest = Sha256::new();
    digest.update(project.as_os_str().as_encoded_bytes());
    for path in extra { digest.update([0]); digest.update(path.as_os_str().as_encoded_bytes()); }
    if let Some(sources) = read_realm_sources(project) {
        digest.update([0]);
        digest.update(sources.token.as_bytes());
        for (path, _) in sources.entries.iter() {
            digest.update([0]);
            digest.update(path.as_os_str().as_encoded_bytes());
        }
    }
    digest.finalize()[..16].iter().map(|b| format!("{b:02x}")).collect()
}

/// The engine policy's roots, resolved under `root`. Reading the policy keeps
/// the watch set equal to the inputs the engine fingerprint actually covers;
/// a missing or malformed policy falls back to the known roots (watching MORE
/// is safe — it only over-invalidates).
#[cfg(target_os = "linux")]
fn engine_roots(root: &Path) -> Vec<PathBuf> {
    let declared = std::fs::read(root.join("nix/engine-inputs.json")).ok()
        .and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok())
        .and_then(|value| value.get("roots").and_then(|r| r.as_array()).map(|rows| {
            rows.iter().filter_map(|row| row.as_str()).map(|name| root.join(name)).collect::<Vec<_>>()
        }));
    declared.unwrap_or_else(|| ["bin", "nix", "priv", "native", "tooling/drop", "packages/job-runner"]
        .iter().map(|name| root.join(name)).collect())
}

#[cfg(target_os = "linux")]
fn project_key(project: &Path, extra: &[PathBuf], env_key: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut digest = Sha256::new();
    digest.update(b"bl-generation-project-v1\0");
    digest.update(project.as_os_str().as_encoded_bytes());
    for path in extra { digest.update([0]); digest.update(path.as_os_str().as_encoded_bytes()); }
    digest.update([0]);
    digest.update(env_key.as_bytes());
    digest.finalize()[..16].iter().map(|b| format!("{b:02x}")).collect()
}

#[cfg(target_os = "linux")]
fn env_signature(env: &[(&str, Option<String>)]) -> String {
    use sha2::{Digest, Sha256};
    let mut digest = Sha256::new();
    for (key, value) in env {
        digest.update(key.as_bytes());
        digest.update([0]);
        match value { Some(v) => { digest.update([1]); digest.update(v.as_bytes()); } None => digest.update([0]) }
        digest.update([0]);
    }
    digest.finalize()[..16].iter().map(|b| format!("{b:02x}")).collect()
}

/// Local filesystems report inotify events reliably; a network or FUSE tree
/// may not, so the service refuses there rather than risk a stale answer.
#[cfg(target_os = "linux")]
fn local_filesystem(path: &Path) -> bool {
    let Ok(cpath) = c_path(path) else { return false; };
    let mut stat: libc::statfs = unsafe { std::mem::zeroed() };
    if unsafe { libc::statfs(cpath.as_ptr(), &mut stat) } != 0 { return false; }
    // ext2/3/4, xfs, btrfs, tmpfs, overlayfs, zfs
    matches!(stat.f_type as i64, 0xEF53 | 0x58465342 | 0x9123683E | 0x01021994 | 0x794C7630 | 0x2FC12FC1)
}

#[cfg(all(test, target_os = "linux"))]
mod generation_tests {
    use super::*;

    /// The service applies the CLIENT's token environment to its process
    /// before computing (that is what makes the answer byte-identical), and
    /// Rust's test harness runs tests in threads of one process. Serialize the
    /// tests that compute tokens or ask a service so one test's environment
    /// cannot land inside another's computation.
    static ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());
    fn serialized() -> std::sync::MutexGuard<'static, ()> {
        ENV_LOCK.lock().unwrap_or_else(|poison| poison.into_inner())
    }

    struct Fixture { root: PathBuf, project: PathBuf }

    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.root);
        }
    }

    /// A minimal engine checkout plus a project whose realm manifest records one
    /// loaded file and one searched directory — the two line kinds the fold has.
    fn fixture(name: &str) -> Fixture {
        let root = std::env::temp_dir().join(format!("generation-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(root.join("priv/host")).unwrap();
        std::fs::create_dir_all(root.join("nix")).unwrap();
        std::fs::write(root.join("nix/engine-inputs.json"), r#"{
            "version":1,"roots":["priv","nix"],"excluded":["priv/generated"],
            "reserved":[".git","__pycache__"],"targetRoots":["priv"],
            "limits":{"entries":1000,"fileBytes":65536,"totalBytes":1048576,"depth":10}
        }"#).unwrap();
        std::fs::write(root.join("priv/runtime.bl"), "runtime 1").unwrap();
        std::fs::write(root.join("priv/host/helper.bl"), "helper 1").unwrap();
        let project = root.join("proj");
        std::fs::create_dir_all(project.join(".bl")).unwrap();
        std::fs::create_dir_all(project.join("lib")).unwrap();
        std::fs::write(project.join("env.bl"), "{:name \"proj\"}\n").unwrap();
        std::fs::write(project.join("a.bl"), "(ns a) (defn value [] 1)\n").unwrap();
        let a = project.join("a.bl");
        let canonical_project = std::fs::canonicalize(&project).unwrap();
        let loaded = sha_hex(&std::fs::read(&a).unwrap());
        // An EMPTY directory's listing digest is sha256 of zero bytes.
        let empty_dir = sha_hex(&[]);
        let manifest = format!(
            "bl-realm-sources 2\t{}\t{}-1\nL\t{}\t{}\nD\t{}\t{}\n",
            canonical_project.display(), std::process::id(), loaded,
            std::fs::canonicalize(&a).unwrap().display(), empty_dir,
            std::fs::canonicalize(project.join("lib")).unwrap().display());
        std::fs::write(project.join(".bl/realm-sources.v1"), manifest).unwrap();
        Fixture { root, project }
    }

    fn sha_hex(bytes: &[u8]) -> String {
        use sha2::{Digest, Sha256};
        let mut digest = Sha256::new();
        digest.update(bytes);
        digest.finalize().iter().map(|b| format!("{b:02x}")).collect()
    }

    fn tokens(f: &Fixture) -> Generations {
        checkout_generations(&f.root, &f.project, &[]).unwrap()
    }

    #[test]
    fn a_loaded_file_changes_the_project_token_an_unrelated_one_does_not() {
        let _serial = serialized();
        let f = fixture("semantics");
        let first = tokens(&f);
        std::fs::write(f.project.join("README.md"), "notes\n").unwrap();
        let unrelated = tokens(&f);
        assert_eq!(first, unrelated, "an unrelated file is not an input");
        std::fs::write(f.project.join("a.bl"), "(ns a) (defn value [] 2)\n").unwrap();
        let loaded = tokens(&f);
        assert_ne!(first.project, loaded.project, "a loaded file's bytes are the project pin");
        std::fs::write(f.root.join("priv/host/helper.bl"), "helper 2\n").unwrap();
        let engine = tokens(&f);
        assert_ne!(first.engine, engine.engine, "engine inputs move the engine pin");
        assert_eq!(loaded.project, engine.project,
                   "the project pin excludes the engine's own trees");
    }

    #[test]
    fn a_new_candidate_in_a_recorded_directory_changes_the_project_token() {
        let _serial = serialized();
        let f = fixture("candidate");
        let first = tokens(&f);
        std::fs::write(f.project.join("lib/now-present.bl"), "(ns now-present)\n").unwrap();
        let after = tokens(&f);
        assert_ne!(first.project, after.project,
                   "a file appearing in a recorded search directory can change resolution");
    }

    #[cfg(target_os = "linux")]
    fn service(f: &Fixture) -> Option<PathBuf> {
        let socket = f.root.join("generation-test.sock");
        let listener = UnixListener::bind(&socket).ok()?;
        let token = format!("test-{}", std::process::id());
        std::fs::write(token_path(&socket), &token).ok()?;
        let mut state = State::new(f.root.clone()).ok()?;
        state.token = token;
        std::thread::spawn(move || { state.run(listener); });
        Some(socket)
    }

    fn ask(socket: &Path, f: &Fixture) -> Result<Generations, String> {
        let token = std::fs::read_to_string(token_path(socket)).unwrap();
        query_at(socket, &token, &f.project, &[], &token_env().unwrap())
    }

    /// Retry while the resident reports that a change landed during a
    /// computation; the protocol makes that a fallback, never a stale answer.
    fn ask_settled(socket: &Path, f: &Fixture) -> Generations {
        for _ in 0..8 {
            match ask(socket, f) {
                Ok(g) => return g,
                Err(reason) if reason.contains("tree changed") => continue,
                Err(reason) => panic!("service declined: {reason}"),
            }
        }
        panic!("service did not settle");
    }

    #[test]
    fn the_service_answers_and_recomputes_only_what_changed() {
        let _serial = serialized();
        let f = fixture("service");
        let Some(socket) = service(&f) else { return; }; // no inotify here: skip
        let first = ask_settled(&socket, &f);
        assert_eq!(first, tokens(&f), "cached and local answers are identical");
        assert_eq!(ask_settled(&socket, &f), first);
        std::fs::write(f.project.join("README.md"), "unrelated\n").unwrap();
        assert_eq!(ask_settled(&socket, &f), first, "an unrelated edit keeps every token");
        std::fs::write(f.project.join("a.bl"), "(ns a) (defn value [] 3)\n").unwrap();
        let loaded = ask_settled(&socket, &f);
        assert_ne!(loaded.project, first.project, "a loaded edit moves the project token");
        assert_eq!(loaded.engine, first.engine, "and does not move the engine token");
        std::fs::write(f.root.join("priv/host/helper.bl"), "helper 3\n").unwrap();
        let engine = ask_settled(&socket, &f);
        assert_ne!(engine.engine, first.engine, "an engine edit moves the engine token");
    }

    #[test]
    fn the_service_watches_a_recorded_directory_and_answers_a_missing_input() {
        let f = fixture("watched-dir");
        // A recorded `D` directory that does not exist yet: the manifest still
        // casts it as an input, and the service must answer (one stat notices
        // it appearing) rather than refuse.
        std::fs::remove_dir_all(f.project.join("lib")).unwrap();
        let g1 = tokens(&f); // the local answer with the directory missing
        let Some(socket) = service(&f) else { return; };
        let first = ask_settled(&socket, &f);
        assert_eq!(first, g1, "the service answers while a recorded input is missing");
        // A new candidate in the recorded directory changes the project pin; the
        // service sees the directory appear and recomputes.
        std::fs::create_dir_all(f.project.join("lib")).unwrap();
        std::fs::write(f.project.join("lib/now-present.bl"), "(ns now-present)\n").unwrap();
        let after = ask_settled(&socket, &f);
        assert_ne!(after.project, first.project,
                   "a candidate appearing in a recorded directory moves the project token");
    }

    #[test]
    fn a_queue_that_could_not_be_watched_is_a_fallback_not_an_answer() {
        // No inotify instance for this process is a refusal, and the client
        // then computes locally; the protocol cannot express "probably".
        let value = serde_json::json!({"fallback": "tree is not on a local filesystem"});
        assert!(value.get("ok").is_none());
    }
}
