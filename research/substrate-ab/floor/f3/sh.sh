med(){ sort -n | awk '{a[NR]=$1} END{print a[int((NR+1)/2)], "min", a[1], "max", a[NR]}'; }
us(){ echo "$1: $(for i in $(seq 1 31); do a=${EPOCHREALTIME/./}; "${@:2}" >/dev/null 2>&1; b=${EPOCHREALTIME/./}; echo $((b-a)); done | med) us"; }
ls -la /bin/sh; readlink -f /bin/sh; echo "LANG=$LANG LC_ALL=${LC_ALL:-} LOCALE_ARCHIVE=${LOCALE_ARCHIVE:-}"
us true /bin/true
us sh-true /bin/sh -c true
us env-C-sh env LC_ALL=C /bin/sh -c true
us env-true /usr/bin/env true
us bash-posix /bin/sh --posix -c true
D=$(nix shell nixpkgs#dash --command which dash); us dash $D -c true
us env-i-sh env -i /bin/sh -c true
