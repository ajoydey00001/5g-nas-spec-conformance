#!/bin/bash
# Finish Thrust 1 after the srsUE learning run: RUNBOOK.md §3.1-3.5 in one command.
#   bash finish_thrust1.sh          # after the learner has exited: stops the 5G stack, analyses learnedModel.dot
#   bash finish_thrust1.sh --dry    # while it still runs: analyses the newest hypothesis_N.dot, stops nothing
# Everything goes to thrust1/results/ (srsue_*, T1.6_*_ABsrs.*) and thrust1/lab/devlyzer_srs/.
# Then write the text by hand (NEXT_STEPS.md, part A, steps 4-6) and push.
set -e
cd "$(dirname "$0")"
R=$PWD; T=$R/thrust1; RES=$T/results
LOGS=~/thrust1-lab/learnrun/logs/srsue.log
DRY=0; [ "$1" = "--dry" ] && DRY=1

echo "== 1. is the learner finished?"
if docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; then
  if [ $DRY = 0 ]; then echo "The learner is still running. Wait, or use: bash finish_thrust1.sh --dry"; exit 1; fi
  echo "   still running (dry run: nothing is stopped)"
else
  tail -3 ~/thrust1-lab/learnrun/logs/run_table4_time.txt 2>/dev/null || true
  if [ $DRY = 0 ] && docker inspect t1-learn >/dev/null 2>&1; then
    echo "   stopping the 5G stack and the container"
    docker exec t1-learn bash -c 'cd /work/learnrun; ./kill_uecontroller.sh; ./kill_gnb.sh; ./kill_core.sh' >/dev/null 2>&1 || true
    docker stop t1-learn >/dev/null || true
  fi
fi

echo "== 2. which model?"
if [ -f $LOGS/learnedModel.dot ]; then M=$LOGS/learnedModel.dot
else M=$(ls $LOGS/hypothesis_*.dot 2>/dev/null | sort -V | tail -1)
     [ -z "$M" ] && { echo "No model found in $LOGS"; exit 1; }
     echo "   no learnedModel.dot -> using the last hypothesis (say so in the report)"
fi
echo "   model: $M"
SUF=""; [ $DRY = 1 ] && SUF="_dry"
cp $M $RES/srsue_learnedModel$SUF.dot
cp ~/thrust1-lab/learnrun/logs/run_table4_time.txt $RES/srsue_run_times$SUF.txt 2>/dev/null || true
MD=$RES/srsue_learnedModel$SUF.dot

echo "== 3. Table 4 (size: paper says 6 states, 20 transitions) and Table 8 (issues)"
python3 -I $T/symbols/fsm_tools.py stats $MD | tee $RES/srsue_stats$SUF.txt
python3 -I $T/symbols/fsm_tools.py issues $MD | tee $RES/srsue_issues$SUF.txt
python3 -I $T/symbols/fsm_tools.py nas $MD $RES/srsue_nas$SUF.dot >/dev/null
python3 -I - $RES/srsue_issues$SUF.txt <<'EOF'
import sys, re
txt = open(sys.argv[1]).read()
truth = ['I3', 'I4', 'I7', 'I9a', 'I9b', 'I10', 'I19', 'I20']   # Table 8 srsUE row (I9 = our probes I9a/I9b)
got = {i for i in truth if re.search(r'\b%s\b.*PRESENT' % i, txt)}
i9 = ('I9a' in got) or ('I9b' in got)
hits = len(got & {'I3', 'I4', 'I7', 'I10', 'I19', 'I20'}) + i9
print('   Table 8 recall for srsUE: %d/7   present: %s' % (hits, ' '.join(sorted(got))))
print('   I6 present (Table 8 lists it only for OAI UE):', bool(re.search(r'\bI6\b.*PRESENT', txt)))
EOF

echo "== 4. spec vs devices: FSM_A, FSM_B and srsUE"
[ -f repro/dl/FSM_A.dot ] && [ -f repro/dl/FSM_B.dot ] || bash reproduce.sh >/dev/null
python3 -I $T/compare/spec_vs_devices.py $T/spec_fsm/spec_cells_v1.json $RES/T1.6_spec_vs_ABsrs$SUF.json \
  A=repro/dl/FSM_A.dot B=repro/dl/FSM_B.dot srsue=$MD > $RES/T1.6_summary_ABsrs$SUF.txt
grep -A3 -i '^summary' $RES/T1.6_summary_ABsrs$SUF.txt || tail -5 $RES/T1.6_summary_ABsrs$SUF.txt

echo "== 5. DevLyzer (the authors' 45 LTL properties)"
D=$T/lab/devlyzer_srs$SUF; mkdir -p $D
SRC=~/thrust1-lab/5GBaseChecker/DevLyzer
if [ -d $SRC ] && docker image inspect t1-offline >/dev/null 2>&1; then
  W=$(mktemp -d); cp -r $SRC/main.py $SRC/attack_trace_checker $W/
  python3 -I $T/compare/to_devlyzer.py $RES/T1.6_spec_vs_ABsrs$SUF.json $W/deviant-queries.json
  docker run --rm --cpus=2 -u $(id -u):$(id -g) -v $W:/work -w /work t1-offline python3 main.py >/dev/null 2>&1 || true
  cp $W/deviant-queries*.json $D/; rm -rf $W
  for f in attack benign unresolved; do
    printf '   %-10s %s\n' $f "$(python3 -I -c "import json,sys;print(len(json.load(open(sys.argv[1]))['traces']))" $D/deviant-queries_$f.json 2>/dev/null || echo '?')"
  done
else
  echo "   skipped: needs ~/thrust1-lab/5GBaseChecker/DevLyzer and docker image t1-offline (RUNBOOK P7)"
fi

echo
echo "Done. New files:"; ls -1 $RES | grep -E "srsue|ABsrs" | sed 's/^/   thrust1\/results\//'
[ $DRY = 1 ] && echo "(dry run: files end in _dry; delete them or keep them as the interim result)"
echo "Next: NEXT_STEPS.md part A, step 4 (write T1_RESULTS_v2.md and the report), then git add/commit/push."
