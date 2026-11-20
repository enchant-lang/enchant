#!/usr/bin/env bash
# Usage: profile-chez.sh WORK_DIR IN_DIR OUT_DIR [REPS] — sample the reader job on Chez.
# WORK_DIR must already hold host.so and prelude-O2.so (run-chez.sh compile2 builds them).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); export AB_HERE=$here
work=$1; in=$2; out=$3; reps=${4:-6}; mkdir -p "$out"
cat > "$out/profile.ss" <<SCM
(load-shared-object "$work/host.so")
(load "$here/chez-shim.ss")
(load "$work/prelude-O2.so")
(load "$here/chez-profile.ss")
(define ab-source "$in/reader.bl")
(define ab-bundle "$in/eval-prepared.scm")
(define ab-out "$out")
(define ab-reps $reps)
(define (ab-now) (let ((t (current-time 'time-monotonic))) (+ (* 1000. (time-second t)) (/ (time-nanosecond t) 1e6))))
(define ab-catch with-exception-catcher)
(define ab-report display-exception)
(let ((old (exit-handler)))
  (exit-handler (lambda args (ab-profile-stop! "$out/profile.txt") (apply old args))))
(ab-profile-start!)
(load "$here/observer.scm")
SCM
scheme -q "$out/profile.ss"
