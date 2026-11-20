# Gambit vs Chez substrate comparison

Runs the qualified native compiler Scheme (`research/native-seed/out/cutover-core-build-v3/prelude.scm`)
on Chez Scheme 10.4.1 without changing BL sources, and compares it with the Gambit image and warm BEAM.
Results and interpretation: `research/checked-tiles/journal/06-chez-substrate-and-user-path.bl.org`;
evidence: `research/checked-tiles/evidence/substrate-ab.json`.

| File | Role |
| --- | --- |
| `translate.ss` | Gambit-dialect `prelude.scm` → Chez forms + extracted C (`#!optional`, `##` globals, `c-lambda`) |
| `gambit-forms.ss` | Form rewrite shared by the translator and the runtime `eval` shim |
| `chez-shim.ss` | Gambit tables, exception catcher, error objects, string/vector moves |
| `observer.scm` | Portable timing observer (same steps as `speed/attrib/native-attrib.scm.in`, timing mode) |
| `run-gambit.sh`, `run-chez.sh` | Run the observer on one engine (`run-chez.sh` modes: interpret, compile2, compile3) |
| `compare.py` | Counterbalanced Gambit / Chez / BEAM comparison with a byte-identity gate |
| `gambit-build-time.py` | Times the qualified Gambit unit recipe (gsc -c, clang) |
| `user-path.sh` | Times what a user waits for with the installed `bl` |

```sh
work run --memory 3G --timeout 2400 -- python3 research/substrate-ab/compare.py \
  --image research/native-seed/out/cutover-core-build-v3 --work /tmp/ab-work --out /tmp/ab-compare
```

`run-chez.sh` reuses `prelude-O<level>.so` in the work directory when present; delete it after
changing `chez-shim.ss` or the translator. Not yet established on Chez: actor corpus, source corpus,
self-emission fixpoint.
