#!/bin/bash
# "What is the update?" in one command: health, progress, speed, model size, finish estimate, what to do.
#   bash ~/thrust1-lab/learnrun/update.sh
L=~/thrust1-lab/learnrun
D=$L/logs/srsue.log
R=~/5g-nas-spec-conformance

echo "================ srsUE learning run: update $(date '+%F %H:%M') ================"
bash $L/status.sh 2>/dev/null | head -13

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
python3 -I - "$D" "$R" "$(cat $D/learning_queries.log $D/equivalence_queries.log 2>/dev/null | grep -c '^INFO: \[')" <<'EOF2'
import sys, os
D, R, q = sys.argv[1], sys.argv[2], int(sys.argv[3] or 0)
res = R + '/thrust1/results/'
EST_TOTAL = 1100   # estimated total queries for the srsUE run (from the speed so far); the real end is learnedModel.dot
finished = os.path.exists(D + '/learnedModel.dot') or os.path.exists(res + 'srsue_learnedModel.dot')
learn = 1.0 if finished else min(q / EST_TOTAL, 0.97)
def ex(f): return os.path.exists(res + f)
report = R + '/thrust1/report/thrust1_report.tex'
report_done = os.path.exists(report) and 'srsUE learning run in progress' not in open(report).read()
steps = [  # (weight, done fraction, name)
    (10, 1, 'T1.0  environment, 5GBaseChecker build, symbol alignment'),
    (10, 1, 'T1.1  OCUDU / srsUE 5G stack working end to end'),
    (20, 1, 'T1.5  spec FSM v1 from TS 24.501 (89 verbatim quotes)'),
    (15, 1, 'T1.6  spec vs FSM_A/FSM_B: 23 classes, 6 invisible to diff'),
    (5,  1, '      DevLyzer check on FSM_A/FSM_B (23/23 attack)'),
    (25, learn, 'T1.2  srsUE learning run (Table 4)%s' % ('' if finished else '   ~%d/%d queries, estimate' % (q, EST_TOTAL))),
    (5,  1 if ex('srsue_learnedModel.dot') else 0, '      srsUE analysis: finish_thrust1.sh (Table 8, spec vs 3 devices, DevLyzer)'),
    (7,  (ex('T1_RESULTS_v2.md') + report_done) / 2, '      write-up: T1_RESULTS_v2.md + report v2'),
    (3,  0, '      final check_thrust1.sh all PASS + git push'),
]
total = sum(w * f for w, f, _ in steps)
bar = '#' * int(total / 5) + '.' * (20 - int(total / 5))
print('THRUST 1 COMPLETION  [%s] %d%%' % (bar, total))
for w, f, n in steps:
    print('   %-4s %3d%% of %2d   %s' % ('done' if f >= 1 else ('...' if f > 0 else 'todo'), f * 100, w, n))
EOF2

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
