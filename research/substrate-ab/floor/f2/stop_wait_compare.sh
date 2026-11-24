set -u
M=/home/othman/code/undefine/beam-lisp--execution-protocol/bin/bl
WT=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/lane-dupstart
uptime
cd $WT; ./bin/bl realm stop >/dev/null 2>&1
for mode in old new; do
  pend=0
  for k in $(seq 8); do
    (cd $WT && ./bin/bl run /tmp/stopwait-othman/x.bl >/dev/null 2>&1)
    if [ $mode = old ]; then (cd $WT && ./bin/bl realm stop 2>&1 | tail -1)
    else (cd /tmp/stopwait-othman/proj && BL_SDK_REUSE_CURRENT=1 $M run stop_new.bl -- $WT 2>&1 | grep -E 'STOP-RESULT|stopped|retired' | tr '\n' ' '; echo); fi
    out=$(cd $WT && ./bin/bl run /tmp/stopwait-othman/x.bl 2>&1)
    case "$out" in *"retirement pending"*) pend=$((pend+1)); echo "  cycle $k: next run reached the stopping VM";; esac
  done
  echo "== $mode: $pend of 8 runs after stop reached the stopping VM"
done
cd $WT; ./bin/bl realm stop 2>&1 | tail -1
cd /tmp/stopwait-othman/proj && BL_SDK_REUSE_CURRENT=1 $M realm stop 2>&1 | tail -1
