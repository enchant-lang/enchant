//! The checkout platform, selected without a shell on the warm path (F1).
//!
//! `scripts/prepare-checkout-platform` defines the platform's inputs and is the
//! only writer of `.bl/platform-stat.v1`: the platform fingerprint, then one
//! stat line per input entry (`%y %m %p %l %D %i %s %T@ %C@`, directories
//! included), recorded only when no entry changed within its racy window. This
//! module re-stats exactly that recorded listing. When every entry still
//! carries its recorded stamp, the recorded fingerprint names the platform
//! (`.bl/platforms/<fingerprint>`) and the script is not run. Any difference,
//! an unparsable line, or `BL_CHECKOUT_DIGEST_CACHE=0` is a miss: the caller
//! runs the script, which re-lists and re-hashes as it always has.
//!
//! An edit to a listed file moves its ctime (not settable from user space); an
//! added, removed or renamed entry moves its directory's mtime and ctime. So a
//! hit is exactly the script's own cache hit, without the fork, `find` and bash.
use std::path::{Path, PathBuf};

pub const STAT_CACHE: &str = ".bl/platform-stat.v1";
/// The platform whose client `bin/bl` execs without running the script.
/// Written only by a client naming its own platform (see `checkout.rs`).
pub const POINTER: &str = ".bl/checkout-platform";

/// The recorded fingerprint, when the recorded listing still matches the tree.
#[cfg(unix)]
pub fn settled_fingerprint(root: &Path) -> Option<String> {
    if std::env::var_os("BL_CHECKOUT_DIGEST_CACHE").is_some_and(|v| v == "0") {
        return None;
    }
    let recorded = std::fs::read(root.join(STAT_CACHE)).ok()?;
    settled_in(root, std::str::from_utf8(&recorded).ok()?)
}

#[cfg(unix)]
fn settled_in(root: &Path, recorded: &str) -> Option<String> {
    let listing = recorded.strip_suffix('\n')?;
    let (fingerprint, lines) = listing.split_once('\n')?;
    if fingerprint.len() != 64 || !fingerprint.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
        return None;
    }
    let mut entries = 0usize;
    for line in lines.split('\n') {
        if !entry_unchanged(root, line)? {
            return None;
        }
        entries += 1;
    }
    (entries > 0).then(|| fingerprint.to_string())
}

/// `Some(true)` when the entry's current stat equals its line, `Some(false)`
/// when it differs or is gone, `None` when the line cannot be read unambiguously.
#[cfg(unix)]
fn entry_unchanged(root: &Path, line: &str) -> Option<bool> {
    use std::os::unix::fs::{FileTypeExt, MetadataExt};
    // Path and link target may hold spaces; the five stamps never do.
    let mut right = line.rsplitn(6, ' ');
    let ctime = parse_time(right.next()?)?;
    let mtime = parse_time(right.next()?)?;
    let size: u64 = right.next()?.parse().ok()?;
    let inode: u64 = right.next()?.parse().ok()?;
    let device: u64 = right.next()?.parse().ok()?;
    let mut left = right.next()?.splitn(3, ' ');
    let kind = left.next()?;
    let mode = u32::from_str_radix(left.next()?, 8).ok()?;
    let rest = left.next()?;
    let (path, link) = if kind == "l" {
        let (path, link) = rest.split_once(' ')?;
        if path.is_empty() || link.is_empty() || link.contains(' ') { return None; }
        (path, Some(link))
    } else {
        (rest.strip_suffix(' ')?, None)
    };
    if path.is_empty() || path.starts_with('/') || path.split('/').any(|part| part == "..") {
        return None;
    }
    let full = root.join(path);
    let Ok(meta) = std::fs::symlink_metadata(&full) else { return Some(false) };
    let file_type = meta.file_type();
    let now_kind = if file_type.is_file() { "f" } else if file_type.is_dir() { "d" }
        else if file_type.is_symlink() { "l" } else if file_type.is_fifo() { "p" }
        else if file_type.is_socket() { "s" } else if file_type.is_block_device() { "b" }
        else if file_type.is_char_device() { "c" } else { return None };
    if now_kind != kind || meta.mode() & 0o7777 != mode || meta.dev() != device
        || meta.ino() != inode || meta.size() != size
        || (meta.mtime(), meta.mtime_nsec()) != mtime || (meta.ctime(), meta.ctime_nsec()) != ctime {
        return Some(false);
    }
    if let Some(link) = link {
        let Ok(target) = std::fs::read_link(&full) else { return Some(false) };
        if target.as_os_str().as_encoded_bytes() != link.as_bytes() { return Some(false); }
    }
    Some(true)
}

/// GNU find's `%T@`: seconds, a point, then the fraction (10 digits today);
/// the first nine are nanoseconds.
fn parse_time(text: &str) -> Option<(i64, i64)> {
    let (seconds, fraction) = text.split_once('.')?;
    if fraction.is_empty() || !fraction.bytes().all(|b| b.is_ascii_digit()) { return None; }
    let seconds: i64 = seconds.parse().ok()?;
    let mut nanos = 0i64;
    for position in 0..9 {
        let digit = fraction.as_bytes().get(position).map_or(0, |b| i64::from(b - b'0'));
        nanos = nanos * 10 + digit;
    }
    Some((seconds, nanos))
}

/// The platform the recorded fingerprint names, if it is still retained.
pub fn retained(root: &Path, fingerprint: &str) -> Option<PathBuf> {
    let retained = root.join(".bl/platforms").join(fingerprint);
    retained.join("platform.json").is_file().then(|| std::fs::canonicalize(retained).ok()).flatten()
}

/// Point `.bl/checkout-platform` at `platform`, unless it already does.
#[cfg(unix)]
pub fn record_pointer(root: &Path, platform: &Path) {
    let pointer = root.join(POINTER);
    if std::fs::read_link(&pointer).is_ok_and(|current| current == platform) {
        return;
    }
    let staged = root.join(format!("{POINTER}.{}", std::process::id()));
    let _ = std::fs::remove_file(&staged);
    if std::os::unix::fs::symlink(platform, &staged).is_ok() && std::fs::rename(&staged, &pointer).is_err() {
        let _ = std::fs::remove_file(&staged);
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::process::Command;

    struct Tree(PathBuf);
    impl Drop for Tree {
        fn drop(&mut self) { let _ = std::fs::remove_dir_all(&self.0); }
    }

    /// A tree with the script's input set, listed by the real script's own
    /// `find` expression (so the parser is pinned to what the script writes).
    fn tree(name: &str) -> Tree {
        let root = std::env::temp_dir().join(format!("checkout-platform-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        for dir in ["nix/artifact", "tooling/drop/src", "tooling/drop/target", "native/lazy_memo", "scripts", "test/scripts"] {
            std::fs::create_dir_all(root.join(dir)).unwrap();
        }
        for file in ["flake.lock", "flake.nix", "scripts/sdk-inputs", "test/scripts/test_engine_snapshot.py",
                     "nix/a.nix", "nix/ci-check.nix", "nix/with space.nix", "tooling/drop/src/x.rs",
                     "tooling/drop/target/ignored", "native/lazy_memo/lib.rs"] {
            std::fs::write(root.join(file), file).unwrap();
        }
        let script = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../scripts/prepare-checkout-platform");
        std::fs::copy(script, root.join("scripts/prepare-checkout-platform")).unwrap();
        std::os::unix::fs::symlink("a.nix", root.join("nix/link.nix")).unwrap();
        Tree(root)
    }

    /// The script's listing, taken with the script's own expression.
    fn listing(root: &Path) -> String {
        let script = std::fs::read_to_string(root.join("scripts/prepare-checkout-platform")).unwrap();
        let start = script.find("ci_recipes=(").unwrap();
        let end = script.find("stat_listing=$(\n").unwrap();
        let find = &script[script.find("  find \"${inputs[@]}\"").unwrap()..];
        let find = &find[..find.find("\n)\n").unwrap()];
        let program = format!("set -euo pipefail\nroot=\"$1\"\ncd \"$root\"\n{}\nfind_listing=$(\n{find}\n)\nprintf '%s\\n' \"$find_listing\"",
                              &script[start..end]);
        let out = Command::new("bash").arg("-c").arg(program).arg("bash").arg(root).output().unwrap();
        assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
        String::from_utf8(out.stdout).unwrap()
    }

    fn recorded(root: &Path) -> String {
        format!("{}\n{}", "ab".repeat(32), listing(root))
    }

    #[test]
    fn an_unchanged_listing_names_its_fingerprint() {
        let t = tree("hit");
        let text = recorded(&t.0);
        assert!(text.contains("nix/with space.nix"), "{text}");
        assert!(text.lines().any(|l| l.starts_with("d ")), "directories carry stamps: {text}");
        assert!(text.lines().any(|l| l.starts_with("l ") && l.contains(" a.nix ")), "{text}");
        assert!(!text.contains("ci-check.nix") && !text.contains("target"), "{text}");
        assert_eq!(Some("ab".repeat(32)), settled_in(&t.0, &text));
    }

    #[test]
    fn any_change_under_the_inputs_is_a_miss() {
        let t = tree("miss");
        let edits: [(&str, &dyn Fn(&Path)); 6] = [
            ("content, same size", &|r| std::fs::write(r.join("nix/a.nix"), "NIX/A.NIX").unwrap()),
            ("chmod", &|r| { use std::os::unix::fs::PermissionsExt;
                std::fs::set_permissions(r.join("tooling/drop/src/x.rs"), std::fs::Permissions::from_mode(0o600)).unwrap() }),
            ("added file", &|r| std::fs::write(r.join("tooling/drop/src/new.rs"), "").unwrap()),
            ("removed file", &|r| std::fs::remove_file(r.join("native/lazy_memo/lib.rs")).unwrap()),
            ("retargeted link", &|r| { std::fs::remove_file(r.join("nix/link.nix")).unwrap();
                std::os::unix::fs::symlink("ci-check.nix", r.join("nix/link.nix")).unwrap() }),
            ("selector edited", &|r| { let p = r.join("scripts/prepare-checkout-platform");
                let s = std::fs::read_to_string(&p).unwrap(); std::fs::write(p, s + "\n").unwrap() }),
        ];
        for (what, edit) in edits {
            let text = recorded(&t.0);
            assert!(settled_in(&t.0, &text).is_some(), "{what}: before");
            // Coarse kernel timestamps: let a tick pass so a stamp can move.
            std::thread::sleep(std::time::Duration::from_millis(20));
            edit(&t.0);
            assert_eq!(None, settled_in(&t.0, &text), "{what}");
        }
    }

    #[test]
    fn a_pruned_entry_and_an_unreadable_line_behave() {
        let t = tree("pruned");
        let text = recorded(&t.0);
        // Writes inside a pruned directory, or to a CI recipe, are not inputs.
        std::fs::write(t.0.join("tooling/drop/target/ignored"), "rebuilt").unwrap();
        std::fs::write(t.0.join("nix/ci-check.nix"), "changed CI recipe").unwrap();
        assert_eq!(Some("ab".repeat(32)), settled_in(&t.0, &text));
        for bad in ["", "not-a-fingerprint\nf 644 x  1 2 3 4.0 5.0\n",
                    &text.replace(" nix/a.nix ", " ../a.nix "), &format!("{}\nf 644 nix/a.nix\n", "ab".repeat(32))] {
            assert_eq!(None, settled_in(&t.0, bad), "{bad:?}");
        }
    }

    #[test]
    fn find_fractions_read_as_nanoseconds() {
        assert_eq!(Some((1792664275, 788936185)), parse_time("1792664275.7889361850"));
        assert_eq!(Some((5, 100000000)), parse_time("5.1"));
        assert_eq!(None, parse_time("5"));
        assert_eq!(None, parse_time("5.x"));
    }

    #[test]
    fn the_pointer_is_replaced_atomically_and_only_when_it_differs() {
        let t = tree("pointer");
        let (a, b) = (t.0.join("pa"), t.0.join("pb"));
        std::fs::create_dir_all(t.0.join(".bl")).unwrap();
        record_pointer(&t.0, &a);
        assert_eq!(a, std::fs::read_link(t.0.join(POINTER)).unwrap());
        record_pointer(&t.0, &b);
        assert_eq!(b, std::fs::read_link(t.0.join(POINTER)).unwrap());
        let staged: Vec<_> = std::fs::read_dir(t.0.join(".bl")).unwrap()
            .filter_map(|e| e.ok()).map(|e| e.file_name()).collect();
        assert_eq!(1, staged.len(), "{staged:?}");
    }
}
