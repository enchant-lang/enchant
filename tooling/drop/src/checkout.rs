// Checkout entry for the same native transport used by installed drops.
// Kept in this binary so framing, ownership and unknown-outcome rules stay shared.
fn checkout_root() -> Option<PathBuf> {
    std::env::var_os("BL_CHECKOUT_ROOT").map(PathBuf::from)
}

// This supplies filesystem prerequisites only. It grants no Source invocation
// authority and uses the same publication custody as the bootstrap builder.
fn checkout_prerequisites(args: &[String]) -> Result<(), String> {
    if args.len() != 2 { return Err("usage: --checkout-prerequisites ROOT PLATFORM".into()); }
    let root = std::fs::canonicalize(&args[0]).map_err(|e| e.to_string())?;
    if !root.join("priv/bootstrap/seed/manifest.term").is_file() {
        return Err("checkout bootstrap manifest is required".into());
    }
    let platform = std::fs::canonicalize(&args[1]).map_err(|e| e.to_string())?;
    if !platform.to_str().is_some_and(nix_artifact::store_object) {
        return Err("checkout platform must be an immutable store object".into());
    }
    let descriptor: serde_json::Value = serde_json::from_slice(
        &std::fs::read(platform.join("platform.json")).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if descriptor["version"] != 1 || descriptor["kind"] != "checkout-platform"
        || descriptor["target"] != "x86_64-linux" {
        return Err("unsupported checkout platform".into());
    }
    let bundle = std::fs::canonicalize(platform.join("native-products")).map_err(|e| e.to_string())?;
    if !bundle.to_str().is_some_and(nix_artifact::store_object) {
        return Err("native set must be an immutable store object".into());
    }
    let manifest: serde_json::Value = serde_json::from_slice(
        &std::fs::read(bundle.join("artifacts.json")).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if manifest["version"] != 1 || manifest["kind"] != "native-set"
        || manifest["target"] != "x86_64-linux" { return Err("unsupported native set".into()); }
    let products = manifest["products"].as_object().ok_or("native set omits products")?;
    if products.is_empty() || products.len() > 128 || !products.contains_key("lazy_memo") {
        return Err("native set omits mandatory products or exceeds capacity".into());
    }
    let mut selections = Vec::new();
    for (name, row) in products {
        let output = row["output"].as_str().ok_or("native set omits product output")?;
        let request = serde_json::json!({"version": 1, "crate": name,
            "abi": format!("beam-lisp-native-{name}-v1"), "target": "x86_64-linux",
            "source": row["source"]});
        let library = nix_artifact::verify(Path::new(output), &request)?;
        selections.push((library, root.join("priv/native").join(format!("{name}.so"))));
    }
    // Validate the whole set before publishing anything. All selection occurs
    // before BEAM boot can freeze native-host physical-library identities.
    for (library, destination) in selections {
        if std::fs::read_link(&destination).is_ok_and(|selected| selected == library) { continue; }
        std::fs::create_dir_all(destination.parent().unwrap()).map_err(|e| e.to_string())?;
        publish_native_reference(&library, &destination)?;
    }
    Ok(())
}

/// The three tokens one checkout request carries. `engine` is the fingerprint
/// the SDK selection is keyed by (`BL_CHECKOUT_SDK_INPUTS`); `runtime` pins the
/// running image (`BL_CHECKOUT_GENERATION`); `project` pins a realm to the
/// sources it resolved (`BL_CHECKOUT_SOURCE_GENERATION`).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Generations {
    pub engine: String,
    pub runtime: String,
    pub project: String,
}

/// Compute the three tokens EXACTLY as the checkout client always has: one
/// engine inventory, the runtime inventory over `priv`/`native`, and the
/// project inventory folded with the realm's manifest. `generation.rs`'s
/// service calls this same function, so a cached answer and a locally computed
/// one are byte-identical.
fn checkout_generations(
    root: &Path,
    project: &Path,
    extra_sources: &[PathBuf],
) -> std::io::Result<Generations> {
    let evidence = engine_inputs::Snapshot::capture(root)?;
    let runtime = checkout_runtime_generation(root, Some(&evidence))?;
    let project_token = checkout_project_generation(root, project, extra_sources, Some(&evidence))?;
    evidence.verify()?;
    engine_inputs::save_digest_cache();
    Ok(Generations { engine: evidence.fingerprint.clone(), runtime, project: project_token })
}

/// `BL_CHECKOUT_PHASE_TIMES=1` prints one `U10-PHASE name microseconds` line per
/// phase to stderr. Off by default: a command's stderr is the command's.
struct PhaseTimer { start: std::time::Instant, last: std::time::Instant, on: bool }
impl PhaseTimer {
    fn new() -> Self {
        let now = std::time::Instant::now();
        Self { start: now, last: now, on: std::env::var_os("BL_CHECKOUT_PHASE_TIMES").is_some_and(|v| v == "1") }
    }
    fn mark(&mut self, name: &str) {
        let now = std::time::Instant::now();
        if self.on {
            eprintln!("U10-PHASE {} {}", name, now.duration_since(self.last).as_micros());
        }
        self.last = now;
    }
    fn total(&self) {
        if self.on {
            eprintln!("U10-PHASE total {}", self.start.elapsed().as_micros());
        }
    }
}

fn checkout_main(args: &[String]) -> ! {
    let mut timer = PhaseTimer::new();
    let root = args
        .first()
        .and_then(|s| std::fs::canonicalize(s).ok())
        .filter(|p| p.join("priv/bootstrap/seed/manifest.term").is_file())
        .unwrap_or_else(|| fail("--checkout requires a beam-lisp checkout"));
    if args.get(1).map(String::as_str) != Some("--") {
        fail("usage: drop-launcher --checkout ROOT -- ARGV...");
    }
    timer.mark("root");
    // `bin/bl`'s one-exec path passes the root as it was invoked; the
    // environment names the canonical one, as `bin/bl` always exported it.
    std::env::set_var("BL_CHECKOUT_ROOT", &root);
    #[cfg(unix)]
    select_checkout_platform(&root);
    timer.mark("platform");
    let argv = &args[2..];
    let cwd = std::env::current_dir().unwrap_or_else(|e| fail(&e.to_string()));
    let project = root_override(argv)
        .or_else(|| project_dir(&cwd))
        .unwrap_or_else(|| cwd.clone());
    let project = std::fs::canonicalize(project).unwrap_or_else(|e| fail(&e.to_string()));
    let extra_sources = checkout_extra_sources(&project, &request_cwd(&cwd, argv), argv);
    timer.mark("project+extra");
    // The per-tree generation service answers engine/runtime/project from a
    // kernel-observed tree (see `generation.rs`). It is an optimization with a
    // safe failure mode: when it is absent, still warming, or unsure it says
    // nothing, and this process computes the same three tokens itself.
    let generations = generation_cached(&root, &project, &extra_sources);
    timer.mark("service");
    let generations = match generations {
        Some(g) => g,
        None => {
            generation_ensure(&root);
            let g = checkout_generations(&root, &project, &extra_sources)
                .unwrap_or_else(|e| fail(&format!("checkout inventory: {e}")));
            timer.mark("local");
            g
        }
    };
    std::env::set_var("BL_CHECKOUT_SDK_INPUTS", &generations.engine);
    std::env::set_var("BL_CHECKOUT_ROOT", &root);
    std::env::set_var("BL_CHECKOUT_GENERATION", generations.runtime);
    std::env::set_var("BL_CHECKOUT_SOURCE_GENERATION", generations.project);
    timer.total();
    exec_payload(&root, "src", argv)
}

/// Set by a client that selected the platform for the client it execs, so that
/// one may name itself in `.bl/checkout-platform`. Never reaches the VM.
const PLATFORM_SELECTED: &str = "BL_CHECKOUT_PLATFORM_SELECTED";

/// F1: `bin/bl` execs the client `.bl/checkout-platform` names with no
/// `BL_CHECKOUT_PLATFORM`. This client then selects the platform itself, the
/// way `bin/bl` did: the script's recorded stat listing, re-stated here, or
/// else the script. When the selected platform's client is another binary it
/// execs that one, with the platform set, exactly as `bin/bl` would have. A
/// preset `BL_CHECKOUT_PLATFORM` (build sandboxes, the cold re-entry through
/// `bin/bl`, `bin/bl` without a pointer yet, or a selecting client) is used as
/// given; `BL_CHECKOUT_PLATFORM_SELECTED` equal to it says it was selected for
/// this tree, so its own client may record itself as the pointer. Only a
/// client of this protocol ever writes the pointer, and only naming itself, so
/// `bin/bl` never execs an older client without a platform.
#[cfg(unix)]
fn select_checkout_platform(root: &Path) {
    use std::os::unix::process::CommandExt;
    let selected = std::env::var_os(PLATFORM_SELECTED);
    std::env::remove_var(PLATFORM_SELECTED);
    if let Some(preset) = std::env::var_os("BL_CHECKOUT_PLATFORM").filter(|v| !v.is_empty()) {
        if selected.is_some_and(|s| s == preset) && runs_client_of(Path::new(&preset)) {
            checkout_platform::record_pointer(root, Path::new(&preset));
        }
        return;
    }
    let platform = checkout_platform::settled_fingerprint(root)
        .and_then(|fingerprint| checkout_platform::retained(root, &fingerprint))
        .unwrap_or_else(|| prepare_checkout_platform(root));
    let text = platform.to_str().unwrap_or("");
    if !nix_artifact::store_object(text) {
        eprintln!("bl: checkout platform must be an immutable Nix product");
        std::process::exit(69);
    }
    let client = platform.join("bin/drop-launcher");
    if !platform.join("platform.json").is_file() || !is_executable(&client) {
        eprintln!("bl: checkout platform is incomplete");
        std::process::exit(69);
    }
    let natives = std::fs::canonicalize(platform.join("native-products"))
        .unwrap_or_else(|_| platform.join("native-products"));
    let mut path = std::ffi::OsString::from(format!("{text}/bin:"));
    path.push(std::env::var_os("PATH").unwrap_or_default());
    std::env::set_var("BL_CHECKOUT_PLATFORM", &platform);
    std::env::set_var("BL_ARTIFACT_PLATFORM", platform.join("artifact-platform"));
    std::env::set_var("BL_PREPARED_NATIVES", natives);
    std::env::set_var("BL_BIN", &client);
    std::env::set_var("PATH", path);
    if runs_client_of(&platform) {
        checkout_platform::record_pointer(root, &platform);
        return;
    }
    let error = Command::new(&client)
        .args(std::env::args_os().skip(1))
        .env(PLATFORM_SELECTED, &platform)
        .exec();
    fail(&format!("cannot run {}: {error}", client.display()));
}

/// Whether this process is the platform's own client binary.
#[cfg(unix)]
fn runs_client_of(platform: &Path) -> bool {
    let mine = std::env::current_exe().ok().and_then(|exe| std::fs::canonicalize(exe).ok());
    mine.is_some() && mine == std::fs::canonicalize(platform.join("bin/drop-launcher")).ok()
}

#[cfg(unix)]
fn is_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    std::fs::metadata(path).is_ok_and(|m| m.is_file() && m.permissions().mode() & 0o111 != 0)
}

/// The script's own answer: it re-lists, re-hashes on a miss, records a
/// settled listing and realizes the platform. Its stderr is the user's.
#[cfg(unix)]
fn prepare_checkout_platform(root: &Path) -> PathBuf {
    let script = root.join("scripts/prepare-checkout-platform");
    let output = Command::new(&script)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::inherit())
        .output()
        .unwrap_or_else(|e| fail(&format!("cannot run {}: {e}", script.display())));
    if !output.status.success() {
        std::process::exit(output.status.code().unwrap_or(1));
    }
    let printed = String::from_utf8_lossy(&output.stdout);
    let printed = printed.trim_end_matches('\n');
    std::fs::canonicalize(printed).unwrap_or_else(|_| PathBuf::from(printed))
}

fn invocation_tree(cwd: &Path, argv: &[String]) -> Option<PathBuf> {
    root_override(argv)
        .and_then(canonical_or)
        .or_else(|| project_dir(cwd))
        .or_else(|| resolve_root(cwd))
}

fn checkout_transport(argv: &[String], tree: Option<&str>, config: Option<&str>) -> Transport {
    // Provisioning changes this runtime. Managed build/self-build requests
    // prepare immutable products on the build station and can reuse this client.
    if verb_of(argv)
        .as_deref()
        .is_some_and(|v| ["seed", "deps"].contains(&v))
    {
        return Transport::Cold;
    }
    declared_transport(argv, tree, config).unwrap_or(Transport::Require)
}

// Lifecycle control remains authenticated but can stop the previous source
// generation. It never sends a business request or retries one after send.
#[cfg(unix)]
fn stop_checkout_daemon(root: &Path) -> bool {
    let build = hello_build();
    let mut stream = match hello_generation(root, &build, false, None) {
        Hello::Ready(stream, generation) => {
            if generation.as_deref()
                == std::env::var("BL_CHECKOUT_GENERATION")
                    .ok()
                    .as_deref()
                    .map(str::as_bytes)
            {
                return true; // A concurrent client already replaced the outdated VM.
            }
            stream
        }
        Hello::No => return true,
        _ => return false,
    };
    let mut e = Enc::new();
    e.tuple_header(5);
    e.atom("bl");
    e.small_int(1);
    e.atom("control");
    e.binary(&request_id());
    e.atom("stop");
    if send_frame(&mut stream, &e.finish()).is_err() {
        return false;
    }
    loop {
        match recv_frame(&mut stream)
            .ok()
            .and_then(|bytes| decode(&bytes))
        {
            Some(Term::Tuple(t)) if t.len() == 5 && t[2].as_atom() == Some("exit") => break,
            Some(_) => continue,
            None => break,
        }
    }
    for _ in 0..250 {
        match hello_generation(root, &build, false, None) {
            Hello::No => return true,
            Hello::Ready(_, generation)
                if generation.as_deref()
                    == std::env::var("BL_CHECKOUT_GENERATION")
                        .ok()
                        .as_deref()
                        .map(str::as_bytes) =>
            {
                return true
            }
            _ => {}
        }
        std::thread::sleep(Duration::from_millis(20));
    }
    false
}

fn checkout_memory_bound(command: Command) -> Command {
    #[cfg(target_os = "linux")]
    {
        let runtime = PathBuf::from(format!("/run/user/{}", unsafe { libc_getuid() }));
        if runtime.join("systemd/private").exists() {
            return checkout_scope(command);
        }
    }
    command
}

fn checkout_scope(command: Command) -> Command {
    let mut bounded = Command::new("systemd-run");
    bounded.arg(format!(
        "--unit=bl-checkout-{}-{}",
        std::process::id(),
        now_secs()
    ));
    bounded.args([
        "--user",
        "--scope",
        "--quiet",
        "--collect",
        "--property=MemoryMax=4G",
        "--property=MemorySwapMax=512M",
        "--",
    ]);
    // systemd-run resolves its bus using XDG_RUNTIME_DIR. Restore the caller's
    // original runtime directory only in the executed CLI (including test sockets).
    bounded.args(["env", "-u", "XDG_RUNTIME_DIR"]);
    if let Some(value) = std::env::var_os("XDG_RUNTIME_DIR") {
        let mut assignment = std::ffi::OsString::from("XDG_RUNTIME_DIR=");
        assignment.push(value);
        bounded.arg(assignment);
    }
    bounded.arg(command.get_program()).args(command.get_args());
    for (key, value) in command.get_envs() {
        if let Some(value) = value {
            bounded.env(key, value);
        } else {
            bounded.env_remove(key);
        }
    }
    bounded.env(
        "XDG_RUNTIME_DIR",
        format!("/run/user/{}", unsafe { libc_getuid() }),
    );
    if let Some(dir) = command.get_current_dir() {
        bounded.current_dir(dir);
    }
    bounded
}

#[cfg(test)]
fn checkout_generation(root: &Path, project: &Path) -> std::io::Result<String> {
    Ok(format!(
        "{}:{}",
        checkout_runtime_generation(root, None)?,
        checkout_project_generation(
            root,
            project,
            &checkout_extra_sources(project, project, &[]), None
        )?
    ))
}

/// The roots env.bl / .env.local.bl declare with `:paths`, `:path` and `:run`,
/// and whether any file declared `:paths` at all. Without `:paths` the realm's
/// only project root is the working tree itself (loader.bl `ambient_dirs`:
/// the cwd, then `BEAM_LISP_PATH`; `cli.bl` `with-project` adds `:paths` and
/// the tree's `overrides/`).
fn declared_roots(project: &Path) -> (Vec<PathBuf>, bool) {
    let mut roots = Vec::new();
    let mut paths_declared = false;
    for file in ["env.bl", ".env.local.bl"] {
        if let Ok(text) = std::fs::read_to_string(project.join(file)) {
            let tokens = literal_tokens(&text);
            for (i, (depth, key)) in tokens.iter().enumerate() {
                let Some((_, next)) = tokens.get(i + 1) else {
                    continue;
                };
                if key == ":paths" && next == "[" {
                    // Only the PROJECT's own `:paths` are search roots. A nested
                    // `:build {:paths […]}` describes where build sources live
                    // (this tree's `priv/…`), which the runtime pin already
                    // covers; walking it here inventoried the whole engine twice.
                    if *depth != 1 { continue; }
                    paths_declared = true;
                    for (d, value) in &tokens[i + 2..] {
                        if d <= depth {
                            break;
                        }
                        if let Some(value) =
                            value.strip_prefix('"').and_then(|v| v.strip_suffix('"'))
                        {
                            roots.push(project.join(value));
                        }
                    }
                } else if [":path", ":run"].contains(&key.as_str()) {
                    if let Some(value) = next.strip_prefix('"').and_then(|v| v.strip_suffix('"')) {
                        roots.push(project.join(value));
                    }
                }
            }
        }
    }
    (roots, paths_declared)
}

fn checkout_extra_sources(project: &Path, cwd: &Path, argv: &[String]) -> Vec<PathBuf> {
    let (mut roots, _) = declared_roots(project);
    // The realm also searches the request's cwd. At the project root that is
    // covered by the shallow top-level inventory; a deeper cwd is a root of its own.
    if cwd != project {
        roots.push(cwd.to_path_buf());
    }
    for path in collect_env_paths() {
        roots.push(cwd.join(path));
    }
    let mut i = 0;
    while i < argv.len() && argv[i] != "--" {
        if ["-p", "--path", "--code-path"].contains(&argv[i].as_str()) {
            if let Some(path) = argv.get(i + 1) {
                roots.push(cwd.join(path));
            }
            i += 1;
        }
        i += 1;
    }
    roots
}

/// A file under `root` the VM reloads in place (`dev_reload`, U15).
fn checkout_reloadable(root: &Path, policy: &dev_reload::Policy, path: &Path) -> bool {
    path.strip_prefix(root).ok().and_then(Path::to_str).is_some_and(|name| policy.reloadable(name))
}

/// The reloadable library sources of the engine tree: they key the realm (the
/// project token), not the VM (U15).
fn checkout_reloadable_sources(root: &Path, files: &mut Vec<PathBuf>) -> std::io::Result<()> {
    if let Some(policy) = dev_reload::Policy::read(root) {
        for name in policy.roots() {
            let mut found = Vec::new();
            checkout_sources(&root.join(name), &mut found)?;
            files.extend(found.into_iter().filter(|path| checkout_reloadable(root, &policy, path)));
        }
    }
    Ok(())
}

fn checkout_runtime_generation(root: &Path, evidence: Option<&engine_inputs::Snapshot>) -> std::io::Result<String> {
    let mut files = Vec::new();
    checkout_sources(&root.join("priv"), &mut files)?;
    // A reloadable library source moves the project token instead (U15): the
    // VM compiles it over its SDK and keeps running.
    if let Some(policy) = dev_reload::Policy::read(root) {
        files.retain(|path| !checkout_reloadable(root, &policy, path));
    }
    checkout_sources(&root.join("native"), &mut files)?;
    for name in [
        "bin/bl",
        "bin/bl-stage-hosts",
        "env.bl",
        "priv/bootstrap/seed/manifest.term",
        "priv/codegen.sources",
        ".cargo/config.toml",
        ".cargo/config",
        "rust-toolchain.toml",
        "rust-toolchain",
    ] {
        if root.join(name).is_file() {
            files.push(root.join(name));
        }
    }
    if let Some(ebin) = std::env::var_os("BEAM_LISP_EBIN") {
        checkout_sources(&PathBuf::from(ebin), &mut files)?;
    }
    // This token keys the VM. It folds the engine fingerprint THIS checkout
    // captured, so an edit to any engine input (also outside priv/native, e.g.
    // nix/ or tooling/drop) retires the VM, and a caller-exported
    // `BL_CHECKOUT_SDK_INPUTS` can neither select nor key one (U13). Without
    // evidence (tests only) the pin is captured here, or empty when the root
    // declares no engine inputs.
    // The pin leaves the reloadable sources out too (`base_fingerprint`).
    let engine_pin = match evidence {
        Some(snapshot) => snapshot.base_fingerprint.clone(),
        None => engine_inputs::Snapshot::capture(root).map(|s| s.base_fingerprint).unwrap_or_default(),
    };
    checkout_hash_files(root, files, evidence, &engine_pin)
}

fn checkout_project_generation(
    root: &Path,
    project: &Path,
    extra_sources: &[PathBuf],
    evidence: Option<&engine_inputs::Snapshot>,
) -> std::io::Result<String> {
    let mut files = Vec::new();
    let sources = read_realm_sources(project);
    if sources.is_some() {
        // The realm recorded what it resolved (see `read_realm_sources`), so
        // the walk is not needed: inventory the project's own files, its
        // declared roots (`extra_sources`), `overrides/` and the loose
        // sources at the top of the tree; the manifest adds the rest.
        for name in ["env.bl", ".env.local.bl"] {
            if project.join(name).is_file() {
                files.push(project.join(name));
            }
        }
        checkout_top_level(project, &mut files)?;
        checkout_sources(&project.join("overrides"), &mut files)?;
    } else {
        // No usable manifest (first request, or unreadable): the working tree
        // is the root, and every file in it counts.
        checkout_sources(project, &mut files)?;
    }
    // The runtime pin already covers these trees. In an engine checkout,
    // avoid reading its SDK and native binaries again for the project pin.
    // Explicit extra paths below retain their own complete inventory.
    let sdk = root.join("priv");
    let native = root.join("native");
    files.retain(|path| !path.starts_with(&sdk) && !path.starts_with(&native));
    // Except the engine's reloadable library sources: those retire the realm
    // and are compiled over the SDK by the VM (U15).
    checkout_reloadable_sources(root, &mut files)?;
    for path in extra_sources {
        checkout_sources(path, &mut files)?;
    }
    // The project pin excludes the engine: the runtime pin already moves on
    // an engine edit, and a caller's engine pin must not reach either token.
    let base = checkout_hash_files(root, files, evidence, "")?;
    match sources {
        None => Ok(base),
        Some(sources) => Ok(fold_realm_sources(root, &base, &sources)),
    }
}

/// One recorded observation. `Loaded` is a file the loader read, with that
/// digest of its bytes. `Entries` is a DIRECTORY whose entries were candidates
/// that did not exist: its digest is over the entry names, so listing it once
/// verifies every absent candidate under it.
#[derive(Clone)]
enum Recorded {
    Loaded([u8; 32]),
    Entries([u8; 32]),
}

/// What the warm realm wrote down about its own resolution, in
/// `<project>/.bl/realm-sources.v1` (`source_record_candidate` in `priv/host/loader.bl`).
/// One entry per path, the first record wins.
struct RealmSources {
    /// The header's token, new each time the manifest file is created.
    token: String,
    entries: std::collections::BTreeMap<PathBuf, Recorded>,
}

const REALM_SOURCES: &str = ".bl/realm-sources.v1";

/// The manifest of `project` (canonical), or `None` when it is missing, from
/// another root, torn (no final newline), or holds anything unparseable or an
/// `X` (unrecordable) line. `None` always means: do the full walk.
fn read_realm_sources(project: &Path) -> Option<RealmSources> {
    let text = std::fs::read_to_string(project.join(REALM_SOURCES)).ok()?;
    if !text.ends_with('\n') {
        return None;
    }
    let mut lines = text.lines();
    let header = lines.next()?.strip_prefix("bl-realm-sources 2\t")?;
    let (root, token) = header.split_once('\t')?;
    if token.is_empty() || token.contains('\t') {
        return None;
    }
    if std::fs::canonicalize(root).ok()?.as_path() != project {
        return None;
    }
    let mut entries = std::collections::BTreeMap::new();
    for line in lines {
        let mut parts = line.splitn(3, '\t');
        let (path, recorded) = match (parts.next()?, parts.next(), parts.next()) {
            ("L", Some(hex), Some(path)) => (path, Recorded::Loaded(parse_digest(hex)?)),
            ("D", Some(hex), Some(path)) => (path, Recorded::Entries(parse_digest(hex)?)),
            _ => return None,
        };
        if !Path::new(path).is_absolute() {
            return None;
        }
        entries.entry(PathBuf::from(path)).or_insert(recorded);
    }
    Some(RealmSources { token: token.to_string(), entries })
}

/// The digest of a directory's entries, in sorted name order: each name, NUL,
/// then one byte for what it is (`f` regular file, `d` directory, `o` other —
/// all following symlinks). A name changing TYPE changes the digest too.
/// `source_listing_digest` in `priv/host/loader.bl` writes the same bytes.
/// `None` when the directory cannot be listed.
fn directory_entries_digest(dir: &Path) -> Option<[u8; 32]> {
    use sha2::{Digest, Sha256};
    let mut entries: Vec<(Vec<u8>, u8)> = std::fs::read_dir(dir)
        .ok()?
        .filter_map(|entry| entry.ok())
        .map(|entry| {
            let kind = match std::fs::metadata(entry.path()) {
                Ok(meta) if meta.is_file() => b'f',
                Ok(meta) if meta.is_dir() => b'd',
                _ => b'o',
            };
            (entry.file_name().as_encoded_bytes().to_vec(), kind)
        })
        .collect();
    entries.sort();
    let mut hash = Sha256::new();
    for (name, kind) in entries {
        hash.update(&name);
        hash.update([0, kind]);
    }
    Some(hash.finalize().into())
}

fn parse_digest(hex: &str) -> Option<[u8; 32]> {
    if hex.len() != 64 || !hex.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
        return None;
    }
    let mut out = [0u8; 32];
    for (i, byte) in out.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&hex[2 * i..2 * i + 2], 16).ok()?;
    }
    Some(out)
}

/// Fold the manifest into the project generation. A path contributes only when
/// it differs from what the realm recorded: a file edited or deleted since it
/// was read, or a candidate that did not exist and now does. Recording a new
/// file therefore never changes the generation; changing one the realm used,
/// or creating one it looked for, always does.
fn fold_realm_sources(root: &Path, base: &str, sources: &RealmSources) -> String {
    use sha2::{Digest, Sha256};
    let mut hash = Sha256::new();
    hash.update(b"checkout-realm-sources-v2\0");
    hash.update(base.as_bytes());
    hash.update(sources.token.as_bytes());
    hash.update([0]);
    // the runtime pin already covers the image's own trees
    let sdk = root.join("priv");
    let native = root.join("native");
    for (path, recorded) in &sources.entries {
        if path.starts_with(&sdk) || path.starts_with(&native) {
            continue;
        }
        // A directory record covers every absent candidate directly under it,
        // so one listing stands for the batch. A loaded file is a file edit or
        // deletion only if its bytes (or its existence) now differ.
        let current = match recorded {
            Recorded::Entries(recorded) => {
                let current = directory_entries_digest(path);
                if current == Some(*recorded) {
                    continue;
                }
                current
            }
            Recorded::Loaded(recorded) => {
                let current = match std::fs::metadata(path) {
                    Ok(meta) if meta.is_file() => {
                        Some(engine_inputs::file_digest(path).unwrap_or([0xff; 32]))
                    }
                    Ok(_) => Some([0xfe; 32]),
                    Err(_) => None,
                };
                if current == Some(*recorded) {
                    continue;
                }
                current
            }
        };
        let name = path.as_os_str().as_encoded_bytes();
        hash.update((name.len() as u64).to_be_bytes());
        hash.update(name);
        match current {
            Some(digest) => {
                hash.update([1]);
                hash.update(digest);
            }
            None => hash.update([0]),
        }
    }
    format!("{:x}", hash.finalize())
}

/// `engine_pin` is folded in the `BL_CHECKOUT_SDK_INPUTS` slot, where the
/// client's environment value used to be read; the environment is never read
/// for it.
fn checkout_hash_files(root: &Path, mut files: Vec<PathBuf>, evidence: Option<&engine_inputs::Snapshot>, engine_pin: &str) -> std::io::Result<String> {
    use sha2::{Digest, Sha256};
    files.sort();
    files.dedup();
    let mut hash = Sha256::new();
    hash.update(b"checkout-generation-v2\0");
    hash.update(root.as_os_str().as_encoded_bytes());
    for key in [
        "HOME",
        "XDG_DATA_HOME",
        "ERL_FLAGS",
        "ERL_AFLAGS",
        "ELIXIR_ERL_OPTIONS",
        "BEAM_LISP_AOT_BACKEND",
        "BEAM_LISP_AOT_CACHE_DIR",
        "BEAM_LISP_AOT_CACHE",
        "BEAM_LISP_AOT_STRICT",
        "BEAM_LISP_DEV",
        "XDG_CACHE_HOME",
        "BEAM_LISP_EBIN",
        "BEAM_LISP_PATH",
        "BL_BOOTSTRAP_SEED",
        "BL_CHECKOUT_PLATFORM",
    ] {
        hash.update(key.as_bytes());
        hash.update([0]);
        hash.update(std::env::var_os(key).unwrap_or_default().as_encoded_bytes());
        hash.update([0]);
    }
    // Same position and bytes as when the slot was read from the
    // environment, so a runtime token matches one computed before U10.
    hash.update(b"BL_CHECKOUT_SDK_INPUTS");
    hash.update([0]);
    hash.update(engine_pin.as_bytes());
    hash.update([0]);
    let mut parents = std::collections::HashMap::<PathBuf, PathBuf>::new();
    for path in files {
        // One stat for the file: the same metadata decides its digest (the
        // cache is keyed by the full stamp) and whether it is a symlink. Only a
        // regular file can reuse the path stat for a digest lookup.
        let meta = std::fs::symlink_metadata(&path)?;
        let is_symlink = meta.file_type().is_symlink();
        let digest = if let Some(digest) = evidence.and_then(|snapshot| snapshot.digest(&path)) {
            *digest
        } else if is_symlink {
            engine_inputs::file_digest(&path)?
        } else {
            engine_inputs::file_digest_stamped(&path, &meta)?
        };
        // Canonicalize each directory once; a file needs its own resolution
        // only when it is itself a symlink.
        let canonical = match (path.parent(), path.file_name()) {
            (Some(parent), Some(name)) if !is_symlink => {
                if !parents.contains_key(parent) {
                    parents.insert(parent.to_path_buf(), std::fs::canonicalize(parent)?);
                }
                parents[parent].join(name)
            }
            _ => std::fs::canonicalize(&path)?,
        };
        let physical = canonical.as_os_str().as_encoded_bytes();
        hash.update((physical.len() as u64).to_be_bytes());
        hash.update(physical);
        let name = path.as_os_str().as_encoded_bytes();
        hash.update((name.len() as u64).to_be_bytes());
        hash.update(name);
        hash.update(digest);
    }
    Ok(format!("{:x}", hash.finalize()))
}

/// The loose source files directly in `dir`, without descending.
fn checkout_top_level(dir: &Path, files: &mut Vec<PathBuf>) -> std::io::Result<()> {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return Ok(());
    };
    for entry in entries {
        let entry = entry?;
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if (name.ends_with(".bl") || name.ends_with(".bl.md") || name.ends_with(".bl.org"))
            && std::fs::metadata(entry.path()).is_ok_and(|m| m.is_file())
        {
            files.push(entry.path());
        }
    }
    Ok(())
}

fn checkout_sources(dir: &Path, files: &mut Vec<PathBuf>) -> std::io::Result<()> {
    if !dir.exists() {
        return Ok(());
    }
    if dir.is_file() {
        files.push(dir.to_path_buf());
        return Ok(());
    }
    // One canonicalization per root. Below it a real directory's physical
    // path is its parent's plus its name; only a symlinked directory needs
    // resolving again, to catch cycles.
    let physical = std::fs::canonicalize(dir)?;
    checkout_sources_walk(dir, &physical, files, &mut std::collections::BTreeSet::new())
}

fn checkout_sources_walk(
    dir: &Path,
    physical: &Path,
    files: &mut Vec<PathBuf>,
    visited: &mut std::collections::BTreeSet<PathBuf>,
) -> std::io::Result<()> {
    if !visited.insert(physical.to_path_buf()) {
        return Ok(());
    }
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name();
        let name = name.to_string_lossy();
        let kind = entry.file_type()?;
        if kind.is_dir() || (kind.is_symlink() && path.is_dir()) {
            if (!name.starts_with('.') || name == ".cargo")
                && !(name == "build" && dir.file_name().is_none_or(|n| n != "priv"))
                && !["_build", "target", "deps", "node_modules", "tmp"].contains(&name.as_ref())
            {
                let below = if kind.is_symlink() {
                    std::fs::canonicalize(&path)?
                } else {
                    physical.join(entry.file_name())
                };
                checkout_sources_walk(&path, &below, files, visited)?;
            }
        } else if (kind.is_file() || (kind.is_symlink() && path.is_file()))
            && (name.ends_with(".bl")
                || name.ends_with(".bl.md")
                || name.ends_with(".bl.org")
                || name.ends_with(".rs")
                || name.ends_with(".so")
                || name.ends_with(".beam")
                || name.ends_with(".app")
                || name == "Cargo.toml"
                || name == "Cargo.lock"
                || name == "sdk-code.term"
                || name == "precompiled.term"
                || name == "rust-toolchain.toml"
                || name == "rust-toolchain"
                || (dir.file_name().is_some_and(|n| n == ".cargo")
                    && ["config", "config.toml"].contains(&name.as_ref()))
                || (dir.file_name().is_some_and(|n| n == "native")
                    && dir
                        .parent()
                        .and_then(Path::file_name)
                        .is_some_and(|n| n == "priv")))
        {
            files.push(path);
        }
    }
    Ok(())
}

#[cfg(test)]
mod checkout_tests {
    use super::*;

    #[cfg(target_os = "linux")]
    fn engine_fixture(name: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!("checkout-engine-{name}-{}", std::process::id()));
        std::fs::create_dir_all(root.join("priv/generated")).unwrap();
        std::fs::create_dir_all(root.join("nix")).unwrap();
        std::fs::write(root.join("nix/engine-inputs.json"), r#"{
            "version":1,"roots":["priv","nix"],"excluded":["priv/generated"],
            "reserved":[".git","__pycache__"],"targetRoots":["priv"],
            "limits":{"entries":100,"fileBytes":65536,"totalBytes":131072,"depth":10}
        }"#).unwrap();
        std::fs::write(root.join("priv/runtime.bl"), "runtime 1").unwrap();
        root
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn checked_engine_bytes_preserve_runtime_and_explicit_project_pins() {
        let root = engine_fixture("pins");
        let snapshot = engine_inputs::Snapshot::capture(&root).unwrap();
        assert_eq!(checkout_runtime_generation(&root, None).unwrap(),
                   checkout_runtime_generation(&root, Some(&snapshot)).unwrap());
        assert_eq!(checkout_project_generation(&root, &root, &[root.join("priv")], None).unwrap(),
                   checkout_project_generation(&root, &root, &[root.join("priv")], Some(&snapshot)).unwrap());
        snapshot.verify().unwrap();
        std::fs::write(root.join("priv/runtime.bl"), "runtime 2").unwrap();
        assert!(snapshot.verify().is_err(), "a captured YES cannot survive a source edit");
        assert_ne!(snapshot.fingerprint, engine_inputs::Snapshot::capture(&root).unwrap().fingerprint);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn digests_are_reused_only_for_settled_unchanged_stamps() {
        use std::os::unix::fs::MetadataExt;
        let root = engine_fixture("digest-cache");
        let runtime = root.join("priv/runtime.bl");
        let project = root.join("project");
        std::fs::create_dir_all(&project).unwrap();
        let external = project.join("external.bl");
        std::fs::write(&external, "external 1").unwrap();
        // a file changed within the racy window is read again, never reused
        let fresh = engine_inputs::Snapshot::capture(&root).unwrap();
        let fresh_project = checkout_project_generation(&root, &project, &[], Some(&fresh)).unwrap();
        assert!(engine_inputs::reusable_digest(&runtime).is_none());
        assert!(engine_inputs::reusable_digest(&external).is_none());
        std::thread::sleep(std::time::Duration::from_millis(2300));
        let first = engine_inputs::Snapshot::capture(&root).unwrap();
        let first_project = checkout_project_generation(&root, &project, &[], Some(&first)).unwrap();
        assert_eq!(first.fingerprint, fresh.fingerprint);
        assert_eq!(first_project, fresh_project);
        assert!(engine_inputs::reusable_digest(&runtime).is_some());
        assert!(engine_inputs::reusable_digest(&external).is_some());
        // reuse answers exactly what a full read answers
        let second = engine_inputs::Snapshot::capture(&root).unwrap();
        assert_eq!(second.fingerprint, first.fingerprint);
        assert_eq!(checkout_project_generation(&root, &project, &[], Some(&second)).unwrap(), first_project);
        // same length, mtime put back: ctime still moves, so the edit is read
        for path in [&runtime, &external] {
            let mtime = std::fs::metadata(path).unwrap().modified().unwrap();
            let before = std::fs::metadata(path).unwrap().size();
            let text = std::fs::read_to_string(path).unwrap().replace('1', "9");
            std::fs::write(path, text).unwrap();
            std::fs::File::options().write(true).open(path).unwrap().set_modified(mtime).unwrap();
            assert_eq!(std::fs::metadata(path).unwrap().size(), before);
            assert!(engine_inputs::reusable_digest(path).is_none());
        }
        assert_ne!(engine_inputs::Snapshot::capture(&root).unwrap().fingerprint, first.fingerprint);
        let edited = engine_inputs::Snapshot::capture(&root).unwrap();
        assert_ne!(checkout_project_generation(&root, &project, &[], Some(&edited)).unwrap(), first_project);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn generated_and_external_bytes_still_have_independent_live_checks() {
        let root = engine_fixture("generated");
        let generated = root.join("priv/generated/code.beam");
        std::fs::write(&generated, "generation 1").unwrap();
        let snapshot = engine_inputs::Snapshot::capture(&root).unwrap();
        assert!(snapshot.digest(&generated).is_none());
        let before = checkout_runtime_generation(&root, Some(&snapshot)).unwrap();
        std::fs::write(&generated, "generation 2").unwrap();
        snapshot.verify().unwrap();
        assert_ne!(before, checkout_runtime_generation(&root, Some(&snapshot)).unwrap());
        let project = root.join("project");
        std::fs::create_dir_all(&project).unwrap();
        let external = project.join("external.bl");
        std::fs::write(&external, "external 1").unwrap();
        let before = checkout_project_generation(&root, &project, &[], Some(&snapshot)).unwrap();
        std::fs::write(&external, "external 2").unwrap();
        assert_ne!(before, checkout_project_generation(&root, &project, &[], Some(&snapshot)).unwrap());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn engine_snapshot_refuses_symlinks_and_changed_policy_or_directory_membership() {
        let root = engine_fixture("invalidation");
        let snapshot = engine_inputs::Snapshot::capture(&root).unwrap();
        std::fs::create_dir(root.join("priv/new-empty-directory")).unwrap();
        assert!(snapshot.verify().is_err());
        let snapshot = engine_inputs::Snapshot::capture(&root).unwrap();
        std::fs::write(root.join("nix/engine-inputs.json"), "{}").unwrap();
        assert!(snapshot.verify().is_err());
        std::fs::remove_dir_all(&root).unwrap();
        let root = engine_fixture("symlink");
        std::os::unix::fs::symlink("runtime.bl", root.join("priv/link.bl")).unwrap();
        assert!(engine_inputs::Snapshot::capture(&root).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn declared_hidden_and_external_source_paths_are_inventoried() {
        let root = std::env::temp_dir().join(format!("checkout-paths-{}", std::process::id()));
        let project = root.join("project");
        std::fs::create_dir_all(project.join(".local/lib")).unwrap();
        std::fs::create_dir_all(root.join("shared")).unwrap();
        std::fs::write(root.join("shared/value.bl"), "(ns shared.value)").unwrap();
        std::fs::write(project.join("env.bl"), r#"{:paths [".local/lib"] :uses {"shared" {:path "../shared"}} :tasks {:go {:run "../task.bl"}}}"#).unwrap();
        let roots = checkout_extra_sources(&project, &project, &[]);
        assert!(roots.contains(&project.join(".local/lib")));
        assert!(roots.contains(&project.join("../shared")));
        assert!(roots.contains(&project.join("../task.bl")));
        let before = checkout_generation(&root, &project).unwrap();
        std::fs::write(project.join(".local/lib/example.bl"), "(ns example)").unwrap();
        assert_ne!(before, checkout_generation(&root, &project).unwrap());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn project_edits_change_the_realm_input_but_preserve_the_runtime_pin() {
        let root =
            std::env::temp_dir().join(format!("checkout-runtime-pin-{}", std::process::id()));
        let project = root.join("project");
        std::fs::create_dir_all(root.join("priv")).unwrap();
        std::fs::create_dir_all(&project).unwrap();
        std::fs::write(root.join("priv/runtime.bl"), "runtime 1").unwrap();
        std::fs::write(project.join("value.bl"), "value 1").unwrap();
        let runtime = checkout_runtime_generation(&root, None).unwrap();
        let sources = checkout_project_generation(&root, &project, &[], None).unwrap();
        std::fs::write(project.join("value.bl"), "value 2").unwrap();
        assert_eq!(runtime, checkout_runtime_generation(&root, None).unwrap());
        assert_ne!(
            sources,
            checkout_project_generation(&root, &project, &[], None).unwrap()
        );
        let engine_sources = checkout_project_generation(&root, &root, &[], None).unwrap();
        std::fs::write(root.join("priv/runtime.bl"), "runtime 2").unwrap();
        assert_ne!(runtime, checkout_runtime_generation(&root, None).unwrap());
        assert_eq!(
            engine_sources,
            checkout_project_generation(&root, &root, &[], None).unwrap()
        );
        let configured = checkout_runtime_generation(&root, None).unwrap();
        std::fs::write(root.join("env.bl"), "{:deps []}").unwrap();
        assert_ne!(configured, checkout_runtime_generation(&root, None).unwrap());
        std::fs::remove_dir_all(root).unwrap();
    }

    /// U15: a reloadable library source keeps the VM (runtime token) and the
    /// SDK selection's base, retires the realm (project token) and still moves
    /// the full engine fingerprint, so a real SDK preparation builds it in. A
    /// compiler input, a request-serving source and a non-source asset under
    /// the same trees keep replacing the VM.
    #[cfg(target_os = "linux")]
    #[test]
    fn library_edits_retire_the_realm_and_keep_the_vm() {
        let root = engine_fixture("dev-reload");
        let project = root.join("project");
        for dir in ["priv/lib/split", "priv/std/vm", "priv/host", "nix"] {
            std::fs::create_dir_all(root.join(dir)).unwrap();
        }
        std::fs::create_dir_all(&project).unwrap();
        std::fs::write(root.join("nix/dev-reload.json"), r#"{"version":1,"roots":["priv/lib","priv/std"],
            "extensions":[".bl",".bl.md"],"compiler":["priv/std/multi.bl"],"restart":["priv/std/vm"]}"#).unwrap();
        for (name, text) in [("priv/lib/split/wire.bl", "wire 1"), ("priv/std/test.bl", "test 1"),
                             ("priv/std/multi.bl", "multi 1"), ("priv/std/vm/session.bl", "session 1"),
                             ("priv/lib/split/codec.mjs", "codec 1"), ("priv/host/env.bl", "env 1")] {
            std::fs::write(root.join(name), text).unwrap();
        }
        let tokens = || {
            let snapshot = engine_inputs::Snapshot::capture(&root).unwrap();
            (snapshot.fingerprint.clone(), snapshot.base_fingerprint.clone(),
             checkout_runtime_generation(&root, Some(&snapshot)).unwrap(),
             checkout_project_generation(&root, &project, &[], Some(&snapshot)).unwrap())
        };
        let first = tokens();
        assert_ne!(first.0, first.1, "a reloadable source is left out of the base");
        for (name, edited) in [("priv/lib/split/wire.bl", "wire 2"), ("priv/std/test.bl", "test 2")] {
            let before = tokens();
            std::fs::write(root.join(name), edited).unwrap();
            let after = tokens();
            assert_ne!(after.0, before.0, "{name}: the SDK fingerprint still covers it");
            assert_eq!(after.1, before.1, "{name}: the base (VM key) does not");
            assert_eq!(after.2, before.2, "{name}: the VM keeps running");
            assert_ne!(after.3, before.3, "{name}: the realm retires");
        }
        // A new reloadable file is a realm change too, not a VM change.
        let before = tokens();
        std::fs::write(root.join("priv/lib/split/new.bl"), "new").unwrap();
        let after = tokens();
        assert_eq!((after.1.clone(), after.2.clone()), (before.1.clone(), before.2.clone()));
        assert_ne!(after.3, before.3);
        for (name, edited) in [("priv/std/multi.bl", "multi 2"), ("priv/std/vm/session.bl", "session 2"),
                               ("priv/lib/split/codec.mjs", "codec 2"), ("priv/host/env.bl", "env 2")] {
            let before = tokens();
            std::fs::write(root.join(name), edited).unwrap();
            let after = tokens();
            assert_ne!(after.1, before.1, "{name}: moves the base");
            assert_ne!(after.2, before.2, "{name}: replaces the VM");
        }
        // Without a policy every engine edit replaces the VM, as before U15.
        std::fs::remove_file(root.join("nix/dev-reload.json")).unwrap();
        let off = tokens();
        assert_eq!(off.1, off.0, "no base without a policy");
        std::fs::write(root.join("priv/lib/split/wire.bl"), "wire 3").unwrap();
        assert_ne!(tokens().2, off.2);
        std::fs::remove_dir_all(root).unwrap();
    }

    fn declared_project(name: &str) -> (PathBuf, PathBuf) {
        let root = std::env::temp_dir().join(format!("checkout-declared-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(root.join("priv")).unwrap();
        std::fs::create_dir_all(root.join("examples/deep")).unwrap();
        std::fs::create_dir_all(root.join("overrides")).unwrap();
        std::fs::write(root.join("priv/runtime.bl"), "runtime").unwrap();
        std::fs::write(root.join("env.bl"), r#"{:name "t" :paths ["examples"]}"#).unwrap();
        std::fs::write(root.join("examples/deep/app.bl"), "app 1").unwrap();
        std::fs::write(root.join("overrides/shim.bl"), "shim 1").unwrap();
        std::fs::write(root.join("top.bl"), "top 1").unwrap();
        std::fs::create_dir_all(root.join("test/bl")).unwrap();
        std::fs::write(root.join("test/bl/seed_support.bl"), "seed 1").unwrap();
        // the realm loaded the helper from its cwd root and looked for it first
        // in a directory where it was not
        write_manifest(&root, &[
            loaded(&root, "test/bl/seed_support.bl"),
            absent(&root, "test/bl/seed_support.clj"),
        ]);
        let project = std::fs::canonicalize(&root).unwrap();
        (root, project)
    }

    fn hex(bytes: &[u8]) -> String {
        bytes.iter().map(|b| format!("{b:02x}")).collect()
    }

    fn digest_hex(bytes: &[u8]) -> String {
        use sha2::{Digest, Sha256};
        hex(&Sha256::digest(bytes))
    }

    /// Write a manifest the way the realm does: header, then entries.
    fn write_manifest(root: &Path, entries: &[String]) {
        write_manifest_with(root, "epoch-1", entries)
    }

    fn write_manifest_with(root: &Path, token: &str, entries: &[String]) {
        let project = std::fs::canonicalize(root).unwrap();
        std::fs::create_dir_all(project.join(".bl")).unwrap();
        let mut text = format!("bl-realm-sources 2\t{}\t{}\n", project.display(), token);
        // the realm records each path once
        let mut seen = std::collections::BTreeSet::new();
        for line in entries {
            let path = line.rsplit_once('\t').map(|(_, path)| path).unwrap_or(line);
            if seen.insert(path.to_string()) {
                text.push_str(line);
                text.push('\n');
            }
        }
        std::fs::write(project.join(REALM_SOURCES), text).unwrap();
    }

    fn loaded(root: &Path, relative: &str) -> String {
        let path = std::fs::canonicalize(root).unwrap().join(relative);
        format!("L\t{}\t{}", digest_hex(&std::fs::read(&path).unwrap()), path.display())
    }

    /// The manifest line for a candidate that missed: the parent of its highest
    /// missing ancestor, with that directory's entry digest.
    fn absent(root: &Path, relative: &str) -> String {
        let project = std::fs::canonicalize(root).unwrap();
        // the realm has created its `.bl` before it records anything
        std::fs::create_dir_all(project.join(".bl")).unwrap();
        let parent = project.join(relative).parent().unwrap().to_path_buf();
        let digest = directory_entries_digest(&parent).unwrap();
        format!("D\t{}\t{}", hex(&digest), parent.display())
    }

    fn generation(root: &Path) -> String {
        let project = std::fs::canonicalize(root).unwrap();
        checkout_generation(&project, &project).unwrap()
    }

    #[test]
    fn editing_a_declared_root_file_changes_the_project_generation() {
        let (root, _) = declared_project("edit");
        let before = generation(&root);
        for (file, text) in [
            ("examples/deep/app.bl", "app 2"),
            ("overrides/shim.bl", "shim 2"),
            ("top.bl", "top 2"),
            ("env.bl", r#"{:name "t" :paths ["examples" "extra"]}"#),
        ] {
            let was = generation(&root);
            std::fs::write(root.join(file), text).unwrap();
            assert_ne!(was, generation(&root), "{file} is a realm input");
        }
        assert_ne!(before, generation(&root));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn junk_outside_the_declared_roots_does_not_change_the_project_generation() {
        let (root, _) = declared_project("junk");
        let before = generation(&root);
        for i in 0..1000 {
            let dir = root.join(format!("scratch/out/d{i}/nested"));
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(dir.join("junk.bl"), format!("junk {i}")).unwrap();
        }
        assert_eq!(before, generation(&root));
        std::fs::write(root.join("scratch/out/d7/nested/junk.bl"), "changed").unwrap();
        assert_eq!(before, generation(&root));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_file_the_realm_loaded_outside_the_declared_roots_pins_the_generation() {
        let (root, _) = declared_project("manifest-file");
        let before = generation(&root);
        std::fs::write(root.join("test/bl/seed_support.bl"), "seed 2").unwrap();
        let edited = generation(&root);
        assert_ne!(before, edited, "an edit to a manifest-listed file is a realm input");
        std::fs::write(root.join("test/bl/seed_support.bl"), "seed 1").unwrap();
        assert_eq!(before, generation(&root), "restored bytes restore the generation");
        std::fs::remove_file(root.join("test/bl/seed_support.bl")).unwrap();
        assert_ne!(before, generation(&root), "a deleted file is a change");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_candidate_the_realm_found_absent_changes_the_generation_when_it_appears() {
        let (root, _) = declared_project("manifest-absent");
        let before = generation(&root);
        std::fs::write(root.join("test/bl/seed_support.clj"), "shadow").unwrap();
        let appeared = generation(&root);
        assert_ne!(before, appeared, "a name appearing in a searched directory");
        // The realm recorded the directory only; it reads the file on its next
        // resolution and then records its BYTES (`L`). Until then a content edit
        // of a file it never loaded cannot change what it resolves.
        std::fs::write(root.join("test/bl/seed_support.clj"), "shadow 2").unwrap();
        assert_eq!(appeared, generation(&root));
        // ...and once the realm has read it, its bytes pin the generation.
        write_manifest(&root, &[
            loaded(&root, "test/bl/seed_support.bl"),
            absent(&root, "test/bl/seed_support.clj"),
            loaded(&root, "test/bl/seed_support.clj"),
        ]);
        let read = generation(&root);
        std::fs::write(root.join("test/bl/seed_support.clj"), "shadow 3").unwrap();
        assert_ne!(read, generation(&root), "a read file's bytes are a realm input");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_manifest_restarted_under_a_live_realm_is_a_new_generation() {
        let (root, _) = declared_project("manifest-epoch");
        let entries = [loaded(&root, "test/bl/seed_support.bl")];
        write_manifest_with(&root, "epoch-1", &entries);
        let first = generation(&root);
        assert_eq!(first, generation(&root));
        write_manifest_with(&root, "epoch-2", &entries);
        assert_ne!(first, generation(&root), "the token is part of the generation");
        // a header without a token is not a manifest
        let project = std::fs::canonicalize(&root).unwrap();
        std::fs::write(project.join(REALM_SOURCES), format!("bl-realm-sources 2\t{}\n", project.display())).unwrap();
        assert!(read_realm_sources(&project).is_none());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn an_absent_directory_that_appears_changes_the_generation() {
        let (root, _) = declared_project("manifest-dir");
        write_manifest(&root, &[
            loaded(&root, "test/bl/seed_support.bl"),
            absent(&root, "missing-dir"),
        ]);
        let before = generation(&root);
        std::fs::create_dir_all(root.join("missing-dir/inner")).unwrap();
        assert_ne!(before, generation(&root));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_name_changing_type_changes_the_directory_digest() {
        let dir = std::env::temp_dir().join(format!("checkout-listing-type-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join("x.bl")).unwrap();
        let as_directory = directory_entries_digest(&dir).unwrap();
        std::fs::remove_dir(dir.join("x.bl")).unwrap();
        std::fs::write(dir.join("x.bl"), "now a file").unwrap();
        // the name is the same; only its type changed, and that is a realm input
        assert_ne!(as_directory, directory_entries_digest(&dir).unwrap());
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn one_directory_record_covers_a_batch_of_absent_candidates() {
        let (root, _) = declared_project("manifest-batch");
        write_manifest(&root, &[
            loaded(&root, "test/bl/seed_support.bl"),
            absent(&root, "test/bl/first.clj"),
            absent(&root, "test/bl/second.org"),
            absent(&root, "test/bl/third.bl.md"),
        ]);
        // the three misses are one line: the directory, not each absent name
        let text = std::fs::read_to_string(root.join(REALM_SOURCES)).unwrap();
        assert_eq!(3, text.lines().count(), "{text}");
        let before = generation(&root);
        // any entry appearing in that directory is a change (conservative)
        std::fs::write(root.join("test/bl/appeared.bl"), "x").unwrap();
        assert_ne!(before, generation(&root));
        // and the directory's listing coming back restores it
        std::fs::remove_file(root.join("test/bl/appeared.bl")).unwrap();
        assert_eq!(before, generation(&root));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_manifest_from_the_old_grammar_falls_back_to_the_walk() {
        let (root, project) = declared_project("manifest-v1");
        let text = format!(
            "bl-realm-sources 1\t{}\tepoch\nA\t{}/test/bl/seed_support.clj\n",
            project.display(),
            project.display()
        );
        std::fs::write(project.join(REALM_SOURCES), text).unwrap();
        assert!(read_realm_sources(&project).is_none(), "v1 is not this client's manifest");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn recording_more_does_not_change_the_generation_and_bad_manifests_fall_back_to_the_walk() {
        let (root, project) = declared_project("manifest-shape");
        let before = generation(&root);
        std::fs::create_dir_all(root.join("lib")).unwrap();
        std::fs::write(root.join("lib/x.bl"), "x").unwrap();
        write_manifest(&root, &[
            loaded(&root, "test/bl/seed_support.bl"),
            absent(&root, "test/bl/seed_support.clj"),
            loaded(&root, "lib/x.bl"),
            absent(&root, "lib/y.bl"),
        ]);
        assert_eq!(before, generation(&root), "unchanged entries add nothing");
        let manifest = project.join(REALM_SOURCES);
        let good = std::fs::read_to_string(&manifest).unwrap();
        // every unusable manifest means: walk everything. A junk file then counts.
        std::fs::create_dir_all(root.join("scratch")).unwrap();
        for bad in [
            format!("{good}X\\t\\n"),
            good.trim_end().to_string(),
            good.replacen(&project.display().to_string(), "/elsewhere", 1),
            format!("{good}L\\tnothex\\t/x\\n"),
            format!("{good}D\\t{}\\trelative.bl\\n", "0".repeat(64)),
        ] {
            std::fs::write(&manifest, &bad).unwrap();
            std::fs::write(root.join("scratch/junk.bl"), "1").unwrap();
            let one = generation(&root);
            std::fs::write(root.join("scratch/junk.bl"), "2").unwrap();
            assert_ne!(one, generation(&root), "walk for: {bad:?}");
        }
        std::fs::remove_file(&manifest).unwrap();
        std::fs::write(root.join("scratch/junk.bl"), "3").unwrap();
        let one = generation(&root);
        std::fs::write(root.join("scratch/junk.bl"), "4").unwrap();
        assert_ne!(one, generation(&root), "no manifest, full walk");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn symlinked_declared_roots_and_cycles_are_followed_once() {
        let (root, _) = declared_project("link");
        let outside = std::env::temp_dir().join(format!("checkout-linked-{}", std::process::id()));
        std::fs::create_dir_all(&outside).unwrap();
        std::fs::write(outside.join("lib.bl"), "lib 1").unwrap();
        std::os::unix::fs::symlink(&outside, root.join("examples/linked")).unwrap();
        std::os::unix::fs::symlink(root.join("examples"), root.join("examples/deep/loop")).unwrap();
        let before = generation(&root);
        std::fs::write(outside.join("lib.bl"), "lib 2").unwrap();
        assert_ne!(before, generation(&root), "a symlinked root's files are inventoried");
        std::fs::remove_dir_all(root).unwrap();
        std::fs::remove_dir_all(outside).unwrap();
    }

    #[test]
    fn memory_scope_preserves_argv_environment_and_directory() {
        let mut command = Command::new("/checkout with spaces/bin/bl");
        command
            .args(["realm", "start", "--root", "/project with spaces"])
            .env("BL_CHECKOUT_COLD", "/checkout with spaces")
            .env_remove("UNSET_TEST_ENV")
            .current_dir("/tmp");
        let bounded = checkout_scope(command);
        let args = bounded
            .get_args()
            .map(|a| a.to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        assert!(args.contains(&"--property=MemoryMax=4G".to_string()));
        assert_eq!(
            &args[args.len() - 5..],
            [
                "/checkout with spaces/bin/bl",
                "realm",
                "start",
                "--root",
                "/project with spaces"
            ]
        );
        assert!(bounded.get_envs().any(|(k, v)| k == "BL_CHECKOUT_COLD"
            && v == Some(std::ffi::OsStr::new("/checkout with spaces"))));
        assert!(bounded
            .get_envs()
            .any(|(k, v)| k == "UNSET_TEST_ENV" && v.is_none()));
        assert_eq!(bounded.get_current_dir(), Some(Path::new("/tmp")));
    }

    #[test]
    fn subdirectories_use_the_project_endpoint() {
        let root = std::env::temp_dir().join(format!("checkout-tree-{}", std::process::id()));
        std::fs::create_dir_all(root.join("nested")).unwrap();
        std::fs::write(root.join("env.bl"), "{}").unwrap();
        assert_eq!(
            invocation_tree(&root.join("nested"), &[]),
            Some(root.clone())
        );
        let argv = vec![
            "--root".to_string(),
            root.join("nested").to_string_lossy().into_owned(),
        ];
        assert_eq!(invocation_tree(&root, &argv), Some(root.join("nested")));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn checkout_defaults_to_one_persistent_owner_and_honors_cold_policy() {
        assert_eq!(checkout_transport(&[], None, None), Transport::Require);
        let args = |words: &[&str]| words.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert_eq!(
            checkout_transport(&args(&["--cold", "eval", "1"]), None, None),
            Transport::Cold
        );
        assert_eq!(
            checkout_transport(&[], Some(":warm \"attach\""), None),
            Transport::Attach
        );
        for verb in ["build", "self-build"] {
            assert_eq!(checkout_transport(&args(&[verb]), None, None), Transport::Require);
            assert_eq!(checkout_transport(&args(&["--cold", verb]), None, None), Transport::Cold);
            assert_eq!(checkout_transport(&args(&[verb]), Some(":warm \"off\""), None), Transport::Cold);
        }
        for verb in ["seed", "deps"] {
            assert_eq!(
                checkout_transport(&args(&["--warm", verb]), None, None),
                Transport::Cold
            );
        }
    }

    #[test]
    fn generation_tracks_content_additions_deletions_and_checkout_identity() {
        let root = std::env::temp_dir().join(format!("checkout-generation-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        for dir in ["priv/bootstrap/seed", "native", "bin", "project"] {
            std::fs::create_dir_all(root.join(dir)).unwrap();
        }
        for file in [
            "bin/bl",
            "bin/bl-stage-hosts",
            "priv/bootstrap/seed/manifest.term",
            "priv/codegen.sources",
        ] {
            std::fs::write(root.join(file), "fixture").unwrap();
        }
        let project = root.join("project");
        let key = || checkout_generation(&root, &project).unwrap();
        let first = key();
        let source = project.join("a.bl");
        std::fs::write(&source, "(def a 1)").unwrap();
        let added = key();
        assert_ne!(first, added);
        std::fs::write(&source, "(def a 2)").unwrap();
        assert_ne!(added, key());
        std::fs::remove_file(source).unwrap();
        assert_eq!(first, key());
        std::fs::create_dir(project.join("build")).unwrap();
        std::fs::write(project.join("build/generated.bl"), "ignored").unwrap();
        assert_eq!(first, key());
        std::fs::write(
            root.join("priv/bootstrap/seed/manifest.term"),
            "different floor",
        )
        .unwrap();
        assert_ne!(first, key());
        std::fs::remove_dir_all(root).unwrap();
    }
}
