//! Which engine files a checkout VM reloads in place (U15).
//!
//! `nix/dev-reload.json` names the library trees (`priv/lib`, `priv/std`) whose
//! `.bl` sources a warm checkout VM compiles over its SDK instead of preparing a
//! new SDK. A file there is still an engine input: it is in the engine
//! fingerprint, so `scripts/prepare-checkout-sdk` builds it in. What changes is
//! which token it moves on a request:
//!
//! * a RELOADABLE file moves the PROJECT token (the realm retires, the VM
//!   compiles the file over the SDK; `priv/std/bl/dev-overlay.bl`);
//! * every other engine file moves the RUNTIME token, as before (the VM is
//!   replaced and the cold path selects or prepares an SDK).
//!
//! `compiler` lists the sources that feed the compiler key
//! (`nix/producer-sources.nix`): never reloadable. `restart` lists the code
//! that serves the request itself (the VM substrate, the daemon and the
//! overlay): an edit replaces the VM. `BL_CHECKOUT_DEV_OVERLAY=0` turns the
//! whole policy off. A missing or malformed policy reloads nothing.
use std::path::Path;

pub struct Policy {
    roots: Vec<String>,
    extensions: Vec<String>,
    held: Vec<String>,
}

fn beneath(parent: &str, child: &str) -> bool {
    child == parent || (child.starts_with(parent) && child.as_bytes().get(parent.len()) == Some(&b'/'))
}

pub fn disabled() -> bool {
    std::env::var_os("BL_CHECKOUT_DEV_OVERLAY").is_some_and(|v| v == "0")
}

impl Policy {
    pub fn read(root: &Path) -> Option<Self> {
        if disabled() { return None; }
        let bytes = std::fs::read(root.join("nix/dev-reload.json")).ok()?;
        if bytes.len() > 65536 { return None; }
        let value: serde_json::Value = serde_json::from_slice(&bytes).ok()?;
        if value["version"] != 1 { return None; }
        let list = |key: &str| -> Option<Vec<String>> {
            value[key].as_array()?.iter().map(|v| v.as_str().map(str::to_owned)).collect()
        };
        let roots = list("roots")?;
        let extensions = list("extensions")?;
        let mut held = list("compiler")?;
        held.extend(list("restart")?);
        let relative = |p: &String| !p.is_empty() && !p.starts_with('/') && !p.split('/').any(|c| c.is_empty() || c == "." || c == "..");
        if roots.is_empty() || extensions.is_empty() || !roots.iter().all(relative) || !held.iter().all(relative) {
            return None;
        }
        Some(Self { roots, extensions, held })
    }

    /// A root-relative regular file the VM reloads in place.
    pub fn reloadable(&self, relative: &str) -> bool {
        self.roots.iter().any(|root| beneath(root, relative) && root != relative)
            && self.extensions.iter().any(|ext| relative.ends_with(ext.as_str()))
            && !self.held.iter().any(|held| beneath(held, relative))
    }

    /// A directory row the base fingerprint leaves out: one inside a reload
    /// root. Its files that are NOT reloadable keep their own rows.
    pub fn reload_directory(&self, relative: &str) -> bool {
        self.roots.iter().any(|root| beneath(root, relative) && root != relative)
    }

    /// The reload roots themselves, root-relative.
    pub fn roots(&self) -> &[String] { &self.roots }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn repository() -> std::path::PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
    }

    #[test]
    fn the_checked_in_policy_reloads_library_sources_only() {
        let policy = Policy::read(&repository()).expect("nix/dev-reload.json");
        assert!(policy.reloadable("priv/lib/split/wire.bl"));
        assert!(policy.reloadable("priv/std/test.bl"));
        assert!(policy.reloadable("priv/std/reload/runtime.bl"));
        assert!(policy.reloadable("priv/lib/code/notes.bl.md"));
        for held in ["priv/std/multi.bl", "priv/std/vm/native.bl", "priv/std/vm/session.bl",
                     "priv/std/bl/daemon.bl", "priv/std/bl/env.bl.md", "priv/host/env.bl",
                     "priv/boot/core.bl", "priv/lib/js/runtime.mjs", "priv/lib", "nix/dev-reload.json"] {
            assert!(!policy.reloadable(held), "{held} must stay an engine (runtime) input");
        }
        assert!(policy.reload_directory("priv/lib/split"));
        assert!(!policy.reload_directory("priv/lib"));
    }

    /// Every `priv/std` or `priv/lib` file the compiler is built from
    /// (`nix/producer-sources.nix`, the `compiler` set) is held back.
    #[test]
    fn compiler_inputs_are_never_reloadable() {
        let policy = Policy::read(&repository()).unwrap();
        let nix = std::fs::read_to_string(repository().join("nix/producer-sources.nix")).unwrap();
        let compiler = nix.split("compiler = source [").nth(1).unwrap().split("];").next().unwrap();
        let mut seen = 0;
        for word in compiler.split_whitespace() {
            let name = word.trim_matches('"');
            if name.starts_with("priv/std") || name.starts_with("priv/lib") {
                seen += 1;
                assert!(!policy.reloadable(name), "{name} feeds the compiler key");
                let listed = std::fs::read_to_string(repository().join("nix/dev-reload.json")).unwrap();
                assert!(listed.contains(&format!("\"{name}\"")), "{name} is named in dev-reload.json's compiler list");
            }
        }
        assert!(seen >= 7, "the compiler set still names its std inputs ({seen})");
    }

    /// `scripts/sdk-inputs --base` (the cold SDK selection) and the client's
    /// `base_fingerprint` (the VM key) are the same bytes.
    #[cfg(target_os = "linux")]
    #[test]
    fn the_base_fingerprint_agrees_with_sdk_inputs() {
        let root = std::env::temp_dir().join(format!("dev-reload-base-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        for dir in ["priv/lib/split", "priv/std/vm", "nix"] {
            std::fs::create_dir_all(root.join(dir)).unwrap();
        }
        std::fs::write(root.join("nix/engine-inputs.json"), r#"{"version":1,"roots":["priv","nix"],
            "excluded":["priv/generated"],"reserved":[".git"],"targetRoots":["priv"],
            "limits":{"entries":100,"fileBytes":65536,"totalBytes":131072,"depth":10}}"#).unwrap();
        std::fs::copy(repository().join("nix/dev-reload.json"), root.join("nix/dev-reload.json")).unwrap();
        for (name, text) in [("priv/lib/split/wire.bl", "w"), ("priv/lib/split/c.mjs", "c"),
                             ("priv/std/multi.bl", "m"), ("priv/std/vm/session.bl", "s"), ("priv/std/t.bl", "t")] {
            std::fs::write(root.join(name), text).unwrap();
        }
        let snapshot = crate::engine_inputs::Snapshot::capture(&root).unwrap();
        let python = |base: bool| {
            let mut command = std::process::Command::new("python3");
            command.arg(repository().join("scripts/sdk-inputs")).arg("--root").arg(&root);
            if base { command.arg("--base"); }
            String::from_utf8(command.output().unwrap().stdout).unwrap().trim().to_owned()
        };
        assert_eq!(python(false), snapshot.fingerprint);
        assert_eq!(python(true), snapshot.base_fingerprint);
        assert_ne!(snapshot.base_fingerprint, snapshot.fingerprint);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn malformed_or_disabled_policies_reload_nothing() {
        let root = std::env::temp_dir().join(format!("dev-reload-policy-{}", std::process::id()));
        std::fs::create_dir_all(root.join("nix")).unwrap();
        std::fs::write(root.join("nix/dev-reload.json"), r#"{"version":1,"roots":["../x"],"extensions":[".bl"],"compiler":[],"restart":[]}"#).unwrap();
        assert!(Policy::read(&root).is_none());
        std::fs::write(root.join("nix/dev-reload.json"), r#"{"version":2,"roots":["priv/lib"],"extensions":[".bl"],"compiler":[],"restart":[]}"#).unwrap();
        assert!(Policy::read(&root).is_none());
        std::fs::remove_dir_all(root).unwrap();
    }
}
