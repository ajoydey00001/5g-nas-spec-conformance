#!/bin/bash
# One-screen health check of the srsUE learning run.   bash ~/thrust1-lab/learnrun/status.sh
L=~/thrust1-lab/learnrun
Q=$L/logs/srsue.log/learning_queries.log
echo "time            $(date '+%F %H:%M')"
echo "charger         $(cat /sys/class/power_supply/A*/online 2>/dev/null | sed 's/1/plugged in/;s/0/ON BATTERY/')"
if docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then echo "learner         RUNNING"; else echo "learner         NOT RUNNING"; fi
echo "queries         $(grep -c '^INFO: \[' $Q 2>/dev/null)   (last finished: $(grep -h '^Oct' $Q 2>/dev/null | tail -1 | cut -c1-24) UTC = +6h local)"
echo "round           $(grep 'Starting round' $L/logs/srsue.log/learner.log 2>/dev/null | tail -1 | sed 's/INFO: //')"
echo "hypotheses      $(ls $L/logs/srsue.log 2>/dev/null | grep -E 'hypothesis_[0-9]+\.dot$|learnedModel\.dot' | tr '\n' ' ')"
echo "/dev/shm        $(docker exec t1-learn df -h /dev/shm 2>/dev/null | tail -1 | awk '{print $5" used"}')"
echo "core running    $(docker exec t1-learn pgrep -c -f open5gs-amfd 2>/dev/null || echo 0)"
echo "sleep blocker   $(systemd-inhibit --list 2>/dev/null | grep -c thrust1) active"
echo "github backup   $(pgrep -f checkpoint.sh >/dev/null && echo running || echo NOT running), last: $(git -C ~/5g-nas-spec-conformance log -1 --format='%s' 2>/dev/null)"
echo "run times:"; sed 's/^/                /' $L/logs/run_table4_time.txt 2>/dev/null
echo "last console lines:"; tail -200 $L/logs/learner_console.log 2>/dev/null | grep -av '^\s*at ' | tail -4 | cut -c1-140 | sed 's/^/                /'
