#!/bin/bash
# Every 30 min while the learner runs: snapshot its resume state into the share repo, commit and push.
# The learner's checkpoint is my_database.sqlite (table queryNew_srsue = every answered membership query);
# on restart with resume_learning=true it answers those from the DB instead of re-running the stack.
L=~/thrust1-lab/learnrun
R=~/5g-nas-spec-conformance
D=$R/thrust1/lab/srsue_checkpoint
mkdir -p $D
while true; do
  python3 -I -c "
import sqlite3, sys
src = sqlite3.connect('file:$L/my_database.sqlite?mode=ro', uri=True)
dst = sqlite3.connect('$D/my_database.sqlite')
src.backup(dst); dst.close()
print(sum(src.execute('select count(*) from ' + t).fetchone()[0] for t in ('query_srsue', 'queryNew_srsue')))" > $D/n_queries.txt
  cp $L/resume.log $L/fgue.properties $D/
  rsync -a $L/logs/srsue.log/ $D/srsue.log/ --exclude '*.lck'
  cp $L/logs/learner_console.log $L/logs/run_table4_time.txt $D/ 2>/dev/null
  cd $R
  git add thrust1/lab/srsue_checkpoint
  if ! git diff --cached --quiet; then
    git commit -q -m "srsUE learning checkpoint: $(cat $D/n_queries.txt) queries ($(date '+%F %H:%M'))" && git push -q 2>&1 | tail -1
    echo "$(date '+%H:%M') pushed checkpoint, $(cat $D/n_queries.txt) queries"
  fi
  docker exec t1-learn pgrep -f uelearner.Learner > /dev/null || { echo "learner finished $(date)"; break; }
  sleep 1800
done
