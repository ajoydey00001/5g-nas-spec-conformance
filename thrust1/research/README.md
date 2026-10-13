# Thrust 1 research experiments

The original demonstration and SQLite checkpoint are preserved. These tools
advance the remaining research requirements; they do not mark the plan complete.
Thrust 2/3 and paid model APIs are not used. Compile the report in Overleaf.

## Completed in this session

- Built an isolated Java 11 research learner from the pinned fat JAR and source.
  `learner.patch` removes the hard-coded 30-call exit. `EQCount=0` disables the
  query cap; a positive cap now throws and results in a nonzero exit.
  The early “Learning complete” message is replaced because it only meant that
  a chosen output symbol was present. Genuine finite Wp completion has a marker.
  Original source and JAR are untouched. Build hashes are in learner_build.json.
- Generated 53 SPEC-only candidate input words. Their output placeholders are
  ignored by upstream `loadCE`; candidates are tested against actual observations.
- Corrected canonical shipped CE count: **30 records**, 29 newline characters.
- Reviewed 30 selected cells here; see results/T1_SEMANTIC_REVIEW.json.
  This is a review aware of the existing model, not a blind extraction ensemble.
- Ran four assumption variants; see results/sensitivity/summary.json.
- Ran actual LearnLib TTT/Wp on A, B and the preserved srsUE hypothesis using all
  four arms: results/D4_offline.json. Each learned model was checked for exact
  equivalence to its oracle by a product-machine BFS. These are fixed-model
  experiments, not live UE query or runtime results.

## Live srsUE experiment

Four cold arms: Wp-only, SPEC-only PCEs + Wp, shipped PCEs + Wp, both + Wp.
All use the original 29-symbol alphabet, lookahead 1, no prior persistent
cache/database, and an equal 48-hour wallclock limit. The script records
incomplete runs honestly and stops the queue on an error or timeout.
Failure does not authorize a like-for-like savings claim.

Prepared under `~/thrust1-lab/research/runs/`. Each arm includes config, CE hash,
source-spec hash, separate output directory, and measured outcome. The old
`learnrun` checkpoint is not copied or overwritten. MongoDB/core/radio resources
are shared, so only one live arm runs at a time.

The queue was managed by `t1-research-queue.service` and was stopped at the
user's request to finalize the one-day teacher-review milestone. A STOP marker
is present. The first arm has status stopped_for_teacher_review; there is no
completed live D4 result. Do not resume that partial arm as a cold start.
Check without changing anything:

```bash
systemctl --user status t1-research-queue.service
cat ~/thrust1-lab/research/queue.log
tail -20 ~/thrust1-lab/research/runs/01_wp/logs/console.log
```

To prevent the next arm starting, create `~/thrust1-lab/research/STOP`.
The current arm continues. A process crash or reboot does not automatically
resume these cold runs; keep partial output, diagnose, and prepare a new run ID.
Do not relaunch an already partially executed arm and call it a cold start.

`run_queue.sh` invokes summarize_run.py and, when all arms finish, compares full
models and writes `thrust1/results/D4_live.json`. Finite Wp-suite completion is
conditional on the assumed state bound/lookahead; it is not a proof of behavior
outside that bound. Log query counts exclude majority-vote wire-level retries;
report them as membership/equivalence oracle calls, alongside elapsed time.

## Reproduce tools

```bash
python3 -I thrust1/research/spec_pces.py thrust1/spec_fsm/spec_cells_v1.json /tmp/spec-pces
python3 -I thrust1/research/sensitivity.py
python3 -I thrust1/research/review_cells.py
python3 thrust1/research/offline_d4.py
python3 -m unittest discover -s thrust1/tests -v
```

build_learner.py runs inside a Java 11 container with the pinned original source
and fat JAR. prepare_runs.py runs on the host and refuses to overwrite existing
runs. Keep the generated JAR in the lab, not Git.

## Remaining requirements

OAI source is present but its gNB/nrUE simulator binaries are not built. It needs
resource-limited build, subscriber/config alignment, a successful smoke test,
then its learning/differential/D4 runs. No OAI results or scope revision are claimed.
Do not compile heavy radio code concurrently with the measured live baseline.
Independent blind extraction/reference evaluation still remains; the present
session can review clauses without an API key but cannot fabricate independent
samples or a human reference. Complete the live arms and evaluate their measured
outcomes before updating any full-plan completion claim.
