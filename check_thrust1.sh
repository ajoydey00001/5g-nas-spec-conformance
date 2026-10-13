#!/bin/bash
# Is Thrust 1 complete and correct? Prints PASS / FAIL / WAIT for each check.   bash check_thrust1.sh
cd "$(dirname "$0")"
T=thrust1; RES=$T/results; L=~/thrust1-lab/learnrun
ok=0; bad=0
pass() { echo "PASS  $*"; ok=$((ok+1)); }
fail() { echo "FAIL  $*"; bad=$((bad+1)); }
wait_() { echo "WAIT  $*"; bad=$((bad+1)); }

echo "== A. offline analysis reproduces (spec FSM, 89 quotes, 23 classes on FSM_A/FSM_B)"
out=$(bash reproduce.sh 2>&1)
echo "$out" | grep -q "classes match committed results: True" && pass "reproduce.sh: classes match the committed results" \
  || fail "reproduce.sh: classes differ or it crashed (run: bash reproduce.sh)"
echo "$out" | grep -qi "identical to the committed" && pass "spec cells regenerate identically (quotes verified)" \
  || fail "spec cells differ from the committed ones"

echo "== B. srsUE learning run"
if [ -f $RES/srsue_learnedModel.dot ]; then
  pass "final srsUE model saved: $(python3 -I $T/symbols/fsm_tools.py stats $RES/srsue_learnedModel.dot | cut -d: -f2)  (paper: 6 states, 20 transitions)"
elif docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then
  wait_ "learner still running ($(ls $L/logs/srsue.log 2>/dev/null | grep -c 'hypothesis_[0-9]*\.dot$') hypotheses so far) - run finish_thrust1.sh when it ends"
else
  fail "no final model and the learner is not running: bash ~/thrust1-lab/learnrun/resume_after_reboot.sh, or finish_thrust1.sh to use the last hypothesis"
fi

echo "== C. srsUE vs paper (Table 8) and spec vs devices"
I=$RES/srsue_issues.txt; [ -f $I ] || I=$RES/srsue_issues_dry.txt
if [ -f $I ]; then
  r=$(grep -cE '^(I3|I4|I7|I10|I19|I20) +PRESENT' $I); grep -qE '^I9[ab] +PRESENT' $I && r=$((r+1))
  [ $r -ge 6 ] && pass "Table 8 recall $r/7 ($(basename $I))" || fail "Table 8 recall only $r/7 ($(basename $I)) - check symbols (PLAN.md §7)"
else wait_ "no srsUE issue file yet (finish_thrust1.sh)"; fi
S=$RES/T1.6_summary_ABsrs.txt; [ -f $S ] || S=$RES/T1.6_summary_ABsrs_dry.txt
if [ -f $S ]; then
  inv=$(grep -o 'INVISIBLE to diff: [0-9]*' $S | grep -o '[0-9]*$')
  [ "${inv:-0}" -gt 0 ] && pass "Case 2 classes invisible to differential testing: $inv ($(basename $S)) <- the novelty claim" \
    || fail "no invisible Case 2 class in $(basename $S)"
else wait_ "no spec-vs-devices summary with srsUE yet (finish_thrust1.sh)"; fi
U=$(ls $T/lab/devlyzer_srs/deviant-queries_unresolved.json $T/lab/devlyzer_srs_dry/deviant-queries_unresolved.json 2>/dev/null | head -1)
if [ -n "$U" ]; then
  u=$(python3 -I -c "import json,sys;print(len(json.load(open(sys.argv[1]))['traces']))" $U)
  [ "$u" = 0 ] && pass "DevLyzer: 0 unresolved ($U)" || fail "DevLyzer: $u unresolved traces ($U)"
else wait_ "no DevLyzer result with srsUE yet"; fi

echo "== D. write-up and backup"
[ -f $RES/T1_RESULTS_v2.md ] && pass "results v2 written" || wait_ "results/T1_RESULTS_v2.md not written yet (NEXT_STEPS A4)"
grep -q "srsUE learning run in progress" $T/report/thrust1_report.tex && wait_ "report still says srsUE in progress (NEXT_STEPS A4)" || pass "report updated"
git fetch -q 2>/dev/null
[ -z "$(git status --porcelain)" ] && [ "$(git rev-parse HEAD)" = "$(git rev-parse @{u} 2>/dev/null)" ] \
  && pass "everything committed and pushed to GitHub" || wait_ "uncommitted or unpushed changes: git add -A && git commit -m ... && git push"

echo; echo "$ok passed, $bad not yet / failed. Thrust 1 is complete when every line is PASS."
