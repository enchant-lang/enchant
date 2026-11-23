set -u
BL=$1; O=/tmp/f1-othman/out/${2:-vm}; mkdir -p $O
export BL_SDK_REUSE_CURRENT=1
cd /tmp/f1-othman/proj
echo "LOAD-BEFORE $(uptime)"
$BL run one.bl
$BL run load_all.bl 2>&1 | tail -1
U9_OUT=$O/wall-min.txt $BL run start_wall_min.bl 2>&1 | tail -1
for i in $(seq 20); do $BL run one.bl >/dev/null 2>&1; done
U9_OUT=$O/wall-min.txt $BL run stop_wall.bl >/dev/null 2>&1
cat $O/wall-min.txt | cut -c1-200
U9_OUT=$O/wall-full.txt $BL run start_wall2.bl 2>&1 | tail -1
for i in $(seq 20); do $BL run one.bl >/dev/null 2>&1; done
U9_OUT=$O/wall-full.txt $BL run stop_wall.bl >/dev/null 2>&1
head -40 $O/wall-full.txt | cut -c1-200
$BL run start_procs.bl 2>&1 | tail -1
for i in $(seq 20); do $BL run one.bl >/dev/null 2>&1; done
U9_OUT=$O/procs.txt $BL run stop_procs.bl >/dev/null 2>&1
sort $O/procs.txt | uniq -c | sort -rn | head -30 | cut -c1-200
echo "LOAD-AFTER $(uptime)"
