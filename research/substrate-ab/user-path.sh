#!/usr/bin/env bash
# Times what a user waits for with the installed `bl`: --cold, first persistent
# VM, warm hello, an unchanged two-namespace project with an imported macro,
# a body edit and a macro-provider edit. Usage: user-path.sh SCRATCH_DIR
# Note: the first plain `bl run` starts the persistent VM; stop it afterwards
# only if you started it (`bl realm stop`).
set -uo pipefail
d=${1:?scratch dir}; mkdir -p "$d" && cd "$d"
printf '(println "hello")\n' > hello.bl
printf '(+ 1 2)\n' > one.bl
cat > util.bl <<'BL'
(ns util)
(defmacro twice [x] `(do ~x ~x))
(defn square [x] (* x x))
(defn sum-squares [xs] (reduce + 0 (map square xs)))
BL
cat > app.bl <<'BL'
(ns app (:require [util :refer [square sum-squares twice]]))
(defn fib [n] (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))
(defn main [] (twice (println (sum-squares (range 10)) (fib 20))))
(main)
BL
t() { local s=$(date +%s%N); "$@" > last.out 2>&1; echo "$1 $(( ($(date +%s%N)-s)/1000000 )) ms rc=$? :: ${*:2}"; }
t bl --cold run hello.bl
t bl run hello.bl
for i in 1 2 3; do t bl run hello.bl; done
for i in 1 2 3; do t bl --version; done
for i in 1 2 3 4; do t bl run one.bl; done
for i in 1 2 3 4 5 6 7; do t bl run app.bl; done
sed -i 's/(fib 20)/(fib 21)/' app.bl; for i in 1 2 3; do t bl run app.bl; done
sed -i 's/(\* x x)/(* x x 1)/' util.bl; for i in 1 2; do t bl run app.bl; done
