set -u
BL=$1; O=/tmp/f1-othman/out/${2:-vm2}; mkdir -p $O
export BL_SDK_REUSE_CURRENT=1
cd /tmp/f1-othman/proj
echo "LOAD-BEFORE $(uptime)"
$BL run one.bl; $BL run one.bl
$BL run load_all.bl 2>&1 | tail -1
U9_OUT=$O/wall-deep.txt $BL run start_wall_deep.bl 2>&1 | tail -1
for i in $(seq 20); do $BL run one.bl >/dev/null 2>&1; done
U9_OUT=$O/wall-deep.txt $BL run stop_wall.bl >/dev/null 2>&1
head -60 $O/wall-deep.txt | tr -s ' \n' ' ' | sed 's/ \([0-9]* calls\)/\n\1/g' | cut -c1-200
echo; echo "LOAD-AFTER $(uptime)"
$BL realm stop
