#!/bin/bash
# Sequential cold experiments with a common wallclock budget. Run on host.
set -euo pipefail
LAB=${T1_LAB_ROOT:-$HOME/thrust1-lab}
REPO=${T1_REPO_DIR:-$HOME/5g-nas-spec-conformance}
exec 9>"$LAB/research/queue.lock"
flock -n 9 || { echo 'Another queue is active'; exit 1; }
if docker exec t1-learn pgrep -f org.example.uelearner.Learner >/dev/null 2>&1; then
  echo 'An existing learner is active; refusing interference'; exit 1
fi
[ -f "$LAB/learnrun/AUTO_RESUME_OFF" ] || { echo 'Pause old auto-resume before running'; exit 1; }
docker exec t1-learn test -f /work/research/build/research-learner.jar
for arm in 01_wp 02_spec 03_shipped 04_both; do
  run="$LAB/research/runs/$arm"
  if [ -f "$run/outcome.json" ]; then
    python3 -I -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))["status"] != "wp_suite_complete")' "$run/outcome.json" || { echo "Previous arm incomplete; prepare a fresh run ID"; exit 1; }
    continue
  fi
  if [ -f "$LAB/research/STOP" ]; then echo 'Queue paused by STOP marker'; exit 0; fi
  limit=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["wallclock_limit_seconds"])' "$run/run.json")
  echo "Starting $arm $(date -Is)"
  docker exec -w "/work/research/runs/$arm" t1-learn ./container_init.sh > "$run/logs/init.log" 2>&1
  started=$(date +%s)
  set +e
  docker exec -w "/work/research/runs/$arm" t1-learn timeout --signal=TERM --kill-after=30 "$limit" java -Xmx1536m -cp /work/research/build/research-learner.jar org.example.uelearner.Learner fgue.properties > "$run/logs/console.log" 2>&1
  code=$?
  set -e
  elapsed=$(( $(date +%s) - started ))
  docker exec -w "/work/research/runs/$arm" t1-learn bash -c './kill_uecontroller.sh; ./kill_gnb.sh; ./kill_core.sh' >/dev/null 2>&1 || true
  python3 "$REPO/thrust1/research/summarize_run.py" "$run" "$code" "$elapsed"
  echo "Finished $arm exit=$code $(date -Is)"
  # A fault is not a usable arm comparison. Stop for diagnosis; timeouts are recorded too.
  [ "$code" = 0 ] || { echo 'Queue stopped: arm incomplete; inspect outcome.json'; exit 1; }
done
python3 "$REPO/thrust1/research/summarize_run.py" --compare "$LAB/research/runs" "$REPO/thrust1/results/D4_live.json"
