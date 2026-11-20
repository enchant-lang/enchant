#!/usr/bin/env bash
# Usage: run-chez.sh MODE WORK_DIR IN_DIR OUT_DIR REPS
#   MODE interpret | compile2 | compile3 — how prelude.ss becomes executable.
# WORK_DIR holds translate.ss output (prelude.ss, host.c). Times the reader job on Chez.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); export AB_HERE=$here; mode=$1; work=$2; in=$3; out=$4; reps=${5:-8}
mkdir -p "$out"
# Gambit c-lambda exposes static C functions; Chez needs exported symbols.
[ -f "$work/host.so" ] || { sed -E "s/^static (.*bl_text_[a-z]+\()/\1/" "$work/host.c" > "$work/host-export.c"; gcc -O2 -shared -fPIC -o "$work/host.so" "$work/host-export.c" -ldl; }
case $mode in
  interpret) load="(parameterize ((current-eval interpret)) (load \"$work/prelude.ss\"))" ;;
  compile2|compile3)
    level=${mode#compile}; so="$work/prelude-O$level.so"
    if [ ! -f "$so" ]; then
      scheme -q <<SCM
(optimize-level $level) (load-shared-object "$work/host.so") (load "$here/chez-shim.ss")
(define t0 (current-time 'time-monotonic))
(compile-file "$work/prelude.ss" "$so")
(let ((d (time-difference (current-time 'time-monotonic) t0)))
  (printf "AB_CHEZ_COMPILE_S ~a\n" (+ (time-second d) (/ (time-nanosecond d) 1e9))))
SCM
    fi
    load="(load \"$so\")" ;;
esac
cat > "$out/run.ss" <<SCM
(load-shared-object "$work/host.so")
(load "$here/chez-shim.ss")
$load
(define ab-source "$in/reader.bl")
(define ab-bundle "$in/eval-prepared.scm")
(define ab-out "$out")
(define ab-reps $reps)
(define (ab-now) (let ((t (current-time 'time-monotonic))) (+ (* 1000. (time-second t)) (/ (time-nanosecond t) 1e6))))
(define ab-catch with-exception-catcher)
(define ab-report display-exception)
(load "$here/observer.scm")
SCM
/usr/bin/env time -f "AB_PROCESS wall %e user %U sys %S maxrss_kb %M" scheme -q "$out/run.ss"
