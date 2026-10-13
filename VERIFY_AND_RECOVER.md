# Verify the finalized Thrust 1 demonstration

Run `bash reproduce.sh` once to populate the ignored `repro/` directory, then
`bash check_thrust1.sh`. The second command checks saved artifact consistency,
model provenance, issue probes, and witness agreement. It does not rerun DevLyzer
or establish semantic correctness, convergence, or completion of the original plan.

The finalized result is srsUE hypothesis 5: 6 states / 21 non-self-loop transitions,
Table 8 recall 7/7, 23 three-device classes, six invisible classes. DevLyzer has
23 attack records, seven overlapping benign records, and zero unresolved.
The learner exits at its 30-equivalence-call budget. Auto-resume is paused;
resuming unchanged replays cached answers and exits again.

See [the audit](thrust1/results/T1_AUDIT.md) for the remaining research requirements.
The full Thrust 1 plan is not complete even when every artifact check passes.

Recovery for a separate future run is documented in RUNBOOK.md. Preserve
`thrust1/results/srsue_learnedModel.dot`, its provenance, and the checkpoint DB
before changing the learner or starting another experiment.
