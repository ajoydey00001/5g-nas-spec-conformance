#!/bin/bash
# "What is the update?" in one command: health, progress, speed, model size, finish estimate, what to do.
#   bash ~/thrust1-lab/learnrun/update.sh
L=~/thrust1-lab/learnrun
D=$L/logs/srsue.log
R=~/5g-nas-spec-conformance

echo "================ srsUE learning run: update $(date '+%F %H:%M') ================"
bash $L/status.sh 2>/dev/null | head -11

python3 -I - $D/learning_queries.log $D/equivalence_queries.log <<'EOF'
import sys, re, datetime as dt
ts = []
for p in sys.argv[1:]:
    try:
        for line in open(p, errors='replace'):
            m = re.match(r'(\w{3} \d+, \d{4} \d+:\d+:\d+ [AP]M)', line)
            if m:
                ts.append(dt.datetime.strptime(m.group(1), '%b %d, %Y %I:%M:%S %p') + dt.timedelta(hours=6))
    except OSError:
        pass
if not ts:
    print('speed           no queries logged yet'); sys.exit()
ts.sort()
now = dt.datetime.now()
last3h = [t for t in ts if t > now - dt.timedelta(hours=3)]
print('speed           %d queries in the last 3 h  (~%d per hour)' % (len(last3h), len(last3h) / 3))
idle = (now - ts[-1]).total_seconds() / 60
print('last query      %s local  (%d min ago)%s' % (ts[-1].strftime('%H:%M'), idle,
      '   <- over 90 min: auto_resume.sh will restart it' if idle > 90 else ''))
EOF

H=$(ls $D/hypothesis_*.dot 2>/dev/null | sort -V | tail -1)
[ -n "$H" ] && echo "newest model    $(basename $H): $(python3 -I $R/thrust1/symbols/fsm_tools.py stats $H | cut -d: -f2)   (paper Table 4: 6 states, 20 transitions)"
echo "auto-resume     $([ -f $L/AUTO_RESUME_OFF ] && echo PAUSED || echo on), restarts so far: $(grep -c RESTART $L/logs/auto_resume.log 2>/dev/null || echo 0)"

echo "------------------------------------------------------------------------------------"
if [ -f $D/learnedModel.dot ]; then
  echo "FINISHED: learnedModel.dot exists. Now run:"
  echo "   cd ~/5g-nas-spec-conformance && git pull && bash finish_thrust1.sh && bash check_thrust1.sh"
elif docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then
  echo "RUNNING normally. Expected finish: 2026-10-14 (about midday; later if another round starts)."
  echo "Nothing to do. Keep the charger plugged in."
else
  echo "LEARNER NOT RUNNING and no learnedModel.dot."
  echo "   auto-resume restarts it within 15 min, or by hand: bash ~/thrust1-lab/learnrun/resume_after_reboot.sh"
  echo "   (if you stopped it on purpose: cd ~/5g-nas-spec-conformance && bash finish_thrust1.sh)"
fi
