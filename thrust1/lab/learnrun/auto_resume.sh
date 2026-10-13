#!/bin/bash
# Run by cron every 15 min (and at boot). Restarts the srsUE learning run from the checkpoint when it has
# crashed or stalled, so the laptop can be left alone for days.
#   install:   (crontab -l 2>/dev/null; echo "*/15 * * * * bash $HOME/thrust1-lab/learnrun/auto_resume.sh"; echo "@reboot sleep 120; bash $HOME/thrust1-lab/learnrun/auto_resume.sh") | crontab -
#   pause:     touch ~/thrust1-lab/learnrun/AUTO_RESUME_OFF      (do this before stopping the learner on purpose)
#   remove:    crontab -r
#   its log:   ~/thrust1-lab/learnrun/logs/auto_resume.log
L=~/thrust1-lab/learnrun
LOG=$L/logs/auto_resume.log
D=$L/logs/srsue.log
MAX=6                                   # give up after this many automatic restarts (then a human must look)
log() { echo "$(date '+%F %H:%M') $*" >> $LOG; }

[ -f $L/AUTO_RESUME_OFF ] && exit 0
[ -f $D/learnedModel.dot ] && exit 0    # finished: nothing to do
n=$(grep -c RESTART $LOG 2>/dev/null); n=${n:-0}
[ "$n" -ge $MAX ] && exit 0

if docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then
  # running: is it stuck? newest change to any query log
  last=$(stat -c %Y $D/learning_queries.log $D/equivalence_queries.log $L/my_database.sqlite 2>/dev/null | sort -n | tail -1)
  age=$(( ($(date +%s) - ${last:-0}) / 60 ))
  [ $age -lt 90 ] && exit 0
  log "RESTART #$((n+1)): no new query for $age min -> killing the learner"
  docker exec t1-learn pkill -f uelearner.Learner; sleep 20
else
  log "RESTART #$((n+1)): learner not running"
fi
bash $L/resume_after_reboot.sh >> $LOG 2>&1
