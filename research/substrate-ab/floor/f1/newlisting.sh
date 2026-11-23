# Writes a settled new-format listing of $1's platform inputs, with fingerprint $2, to $3,
# using the worktree script's own find expression.
set -euo pipefail
root=$1; fp=$2; out=$3; WT=/home/othman/code/undefine/beam-lisp--execution-protocol/.claude/worktrees/lane-warm-floor
cd "$root"
script=$WT/scripts/prepare-checkout-platform
eval "$(sed -n '/^ci_recipes=(/,/^stat_cache=/p' $script | grep -v '^stat_cache=')"
listing=$(find "${inputs[@]}" \( "${skipped[@]}" \) -prune -o -printf '%y %m %p %l %D %i %s %T@ %C@\n')
printf '%s\n%s\n' "$fp" "$listing" > "$out"
