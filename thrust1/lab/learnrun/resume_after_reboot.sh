#!/bin/bash
# Resume the srsUE learning run after the laptop was switched off or rebooted.
#   bash ~/thrust1-lab/learnrun/resume_after_reboot.sh
# Saved answers live in my_database.sqlite. On start the learner moves table queryNew_srsue into
# query_srsue and answers those queries from it, so only unanswered queries run on core/gNB/UE again.
set -e
L=~/thrust1-lab/learnrun
R=~/5g-nas-spec-conformance
CK=$R/thrust1/lab/srsue_checkpoint

if docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then
  echo "The learner is already running. Nothing to do."; exit 0
fi

echo "[1/6] Starting the container"
if docker inspect t1-learn >/dev/null 2>&1; then
  docker start t1-learn >/dev/null
else
  docker run -d --init --name t1-learn --privileged --memory=6g --memory-swap=7g --cpus=5 \
    -v ~/thrust1-lab:/work -w /work/learnrun t1-enva sleep infinity >/dev/null
fi

echo "[2/6] Starting MongoDB and adding the test subscriber"
docker exec t1-learn bash -c 'pkill mongod; sleep 2; rm -rf /tmp/mongo'
docker exec t1-learn /work/learnrun/container_init.sh

echo "[3/6] Stopping leftover core / gNB / UE processes"
for k in kill_uecontroller kill_gnb kill_core; do docker exec t1-learn /work/learnrun/$k.sh >/dev/null 2>&1 || true; done

echo "[4/6] Checking the checkpoint database"
n() { python3 -I -c "
import sqlite3
c = sqlite3.connect('file:$1?mode=ro', uri=True)
print(sum(c.execute('select count(*) from ' + t).fetchone()[0] for t in ('query_srsue', 'queryNew_srsue')))" 2>/dev/null || echo 0; }
LOCAL=$(n $L/my_database.sqlite); SAVED=$(n $CK/my_database.sqlite)
echo "    saved answers: laptop copy $LOCAL, GitHub copy $SAVED"
if [ "$LOCAL" -lt "$SAVED" ]; then
  echo "    laptop copy is missing or older -> restoring the GitHub checkpoint copy"
  [ -f $L/my_database.sqlite ] && mv $L/my_database.sqlite $L/my_database.sqlite.broken.$(date +%s)
  cp $CK/my_database.sqlite $L/my_database.sqlite
fi

echo "[5/6] Keeping the old logs (the learner starts new log files)"
TS=$(date +%Y%m%d_%H%M)
[ -d $L/logs/srsue.log ] && mv $L/logs/srsue.log $L/logs/srsue.log.before_resume_$TS
[ -f $L/logs/learner_console.log ] && mv $L/logs/learner_console.log $L/logs/learner_console.before_resume_$TS.log
echo "resumed $(date)" >> $L/logs/run_table4_time.txt

echo "[6/6] Starting the learner (sleep blocked) and the 30-min GitHub checkpoints"
nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --who=thrust1 --why="5GBaseChecker srsUE learning run" \
  bash -c "docker exec t1-learn /work/learnrun/start_learner.sh; echo \"EXIT=\$? \$(date)\" >> $L/logs/run_table4_time.txt" \
  > $L/logs/resume_$TS.out 2>&1 &
sleep 60
nohup $L/checkpoint.sh > $L/logs/checkpoint_$TS.out 2>&1 &

sleep 5
if docker exec t1-learn pgrep -f uelearner.Learner >/dev/null; then
  echo
  echo "Resumed. The learner is running. Watch it with:"
  echo "  tail -f $L/logs/learner_console.log | grep -E 'Found in previous log|Not found|Starting round'"
  echo "'Found in previous log' = answered from the checkpoint; 'Not found' = live again from there on."
else
  echo "The learner did not start. Check $L/logs/learner_console.log and $L/logs/resume_$TS.out"
fi
