#!/bin/bash
# Read-only status: live learning and preserved demonstration are distinct.
L=${T1_LAB_DIR:-$HOME/thrust1-lab/learnrun}
R=${T1_REPO_DIR:-$HOME/5g-nas-spec-conformance}
D=$L/logs/srsue.log
printf '================ Thrust 1 status: %s ================\n' "$(date '+%F %H:%M')"
if docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then
  RUNNING=1; echo 'learner         RUNNING'
else
  RUNNING=0; echo 'learner         NOT RUNNING'
fi
if [ -f "$L/AUTO_RESUME_OFF" ]; then
  echo 'auto-resume     PAUSED'
else
  echo 'auto-resume     enabled (restart limits may apply)'
fi
if [ -d "$D" ]; then
  echo "live logs       $D"
else
  echo 'live logs       absent; earlier logs may be archived'
fi
python3 -I - "$R" <<'PY'
import json, pathlib, subprocess, sys
r = pathlib.Path(sys.argv[1]); results = r/'thrust1/results'
provenance = results/'srsue_model_provenance.json'
if provenance.exists():
    d = json.loads(provenance.read_text())
    print('saved model     %s: %s states / %s non-self-loop transitions' % (d['status'], d['states'], d['non_self_loop_transitions']))
    print('convergence     %s (recorded provenance)' % ('established' if d.get('converged') else 'NOT established'))
    print('stop reason     '+d['stop_reason'])
else:
    print('saved model     no finalized provenance record')
comparison = results/'T1.6_spec_vs_ABsrs.json'
if comparison.exists():
    classes = json.loads(comparison.read_text())['classes']
    invisible = sum(c['case']==2 and not c['visible_to_diff'] for c in classes)
    print('saved analysis  %d classes / %d invisible witnesses (run check_thrust1.sh to validate)' % (len(classes), invisible))
print('review milestone finalized demonstration; broader experiments deferred until teacher feedback')
print('research plan   INCOMPLETE: independent semantic/extraction validation, OAI reproduction or scope revision, and D4 experiments remain')
print('audit           '+str(results/'T1_AUDIT.md'))
status = subprocess.run(['git','-C',str(r),'status','--porcelain'], capture_output=True,text=True)
head = subprocess.run(['git','-C',str(r),'rev-parse','HEAD'],capture_output=True,text=True)
upstream = subprocess.run(['git','-C',str(r),'rev-parse','@{u}'],capture_output=True,text=True)
if status.returncode == 0:
    print('working tree    '+('has uncommitted changes' if status.stdout else 'clean'))
if head.returncode == upstream.returncode == 0:
    print('backup          '+('matches locally known upstream' if head.stdout == upstream.stdout else 'differs from locally known upstream')+' (no remote fetch performed)')
PY
if [ "$RUNNING" = 1 ]; then
  echo 'Next: monitor the live run; no completion time is inferred from query counts.'
elif [ -f "$R/thrust1/results/srsue_model_provenance.json" ]; then
  echo 'The demonstration model is preserved. Run: bash ~/5g-nas-spec-conformance/check_thrust1.sh'
  echo 'Do not resume the unchanged budget-limited run; cached replay reaches the same exit limit.'
elif [ -f "$L/AUTO_RESUME_OFF" ]; then
  echo 'Automatic restart is paused. Inspect logs and archived hypotheses before deciding to resume.'
else
  echo 'Inspect learner logs and model artifacts before restarting; process exit alone does not establish convergence.'
fi
