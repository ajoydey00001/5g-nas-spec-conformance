# 5G NAS spec-conformance — Thrust 1 work (Ajoy Dey)

Work prepared for Dr. Imtiaz Karim (SysNetS Lab, UT Dallas).

**Thrust 1 idea:** extract a *specification* reference FSM for the 5G NAS UE from TS 24.501 (protocol cells
carry clause evidence; 30 no-connection cells encode a harness abstraction), then compare learned UE FSMs against the spec instead of only against
each other. Device-vs-device differential testing (5GBaseChecker's DevScan) cannot see a deviation that all
devices share; the spec reference can.

## Main results so far (details: [`thrust1/results/T1_RESULTS_v1.md`](thrust1/results/T1_RESULTS_v1.md))

- Spec FSM: 6 states × 16 NAS inputs = 96 cells from TS 24.501 v17.8.0; **89/89 evidence quotes matched after whitespace/punctuation normalization**.
- Against the two learned UE FSMs shipped with 5GBaseChecker: **23 deviation classes**,
  of which **6 are invisible to differential testing** (both devices answer identically, both wrong):
  plain Identity/Authentication Request after security (I3, I4), replayed SMC (I6), null-integrity SMC (I10).
- DevLyzer finds property violations on all 23 witness records. This corroborates traces;
  it does not confirm every final-cell interpretation independently.
- Two spec-model repairs (R1, R2) found by feeding device/property evidence back to the spec text, plus a
  candidate spec gap (5.5.1.2.4 vs 5.5.1.3.4).
- Finalized srsUE hypothesis 5: **6 states / 21 transitions**, Table 8 recall **7/7**, plus I6.
  Adding it preserves **23 classes and six invisible classes**; DevLyzer checks all 23 witness records.
  This is a **budget-limited hypothesis**, not a converged model. See
  [`results v2`](thrust1/results/T1_RESULTS_v2.md) and the updated report.

## Teacher-review milestone

The demonstration is finalized for teacher review. See
[`TEACHER_REVIEW.md`](thrust1/results/TEACHER_REVIEW.md) for results, limitations,
and the review package. Broader research experiments are deferred until feedback.

## Completion status

The proof-of-concept artifacts are finalized. **The full Thrust 1 plan is not complete:**
independent semantic validation, extraction ensembles/reference evaluation, and D4 guided-learning
experiments remain outstanding; OAI UE was not reproduced. The srsUE hypothesis is budget-limited.
See [`Thrust 1 audit`](thrust1/results/T1_AUDIT.md) for verified findings and completion criteria.
All PASS from `check_thrust1.sh` means artifact consistency, not research completion.

## If something breaks

**Progress of the srsUE run:** `bash ~/thrust1-lab/learnrun/update.sh` (copy in `thrust1/lab/learnrun/`).

**Is Thrust 1 correct, and what if the run crashes: [`VERIFY_AND_RECOVER.md`](VERIFY_AND_RECOVER.md).**

**What to do next, with every command: [`NEXT_STEPS.md`](NEXT_STEPS.md)** (finish Thrust 1 with `finish_thrust1.sh`, then Thrust 2 and 3 with `thrust2/triage.py` and `thrust3/score.py`).

[`RUNBOOK.md`](RUNBOOK.md) covers every problem met so far (symptom, cause, fix), a one-screen health check
(`bash ~/thrust1-lab/learnrun/status.sh`), and the exact steps to finish the analysis when the srsUE run ends.

## Reproduce and review

`bash reproduce.sh` reruns the whole offline analysis in about a minute (Python standard library only).
[`REVIEW.md`](REVIEW.md) is a guide for an independent review by a second model (e.g. Claude Fable) or a person.

## Next: Thrust 2 and Thrust 3 (planned)

The plan comes from the PhD proposal (`proposal/Ajoy_Dey_PhD_Proposal.tex`). Step-by-step tasks, a worked
example and "done when" criteria are in [`thrust1/PLAN.md`](thrust1/PLAN.md) §4–§5. Thrust 1 already produces
the inputs both thrusts need.

### Thrust 2: an agent that triages discrepancies and builds exploits

For every deviation between the spec FSM and a learned FSM, an LLM agent does the step that 5GBaseChecker
leaves to a human expert.

1. **Collect evidence.** The agent gets the deviating input word and both output sequences. It can call
   three tools:
   - clause retrieval over the same TS 24.501 clause index (`thrust1/extract/spec_clauses.py`)
   - how every other learned device behaves on the same word (`thrust1/compare/spec_vs_devices.py`)
   - the spec cell's evidence record: clause ID, verbatim quote, kind
2. **Propose a label.** The agent picks one of four labels:
   - (a) a model-extraction error
   - (b) a benign learning artefact or allowed nondeterminism
   - (c) a specification ambiguity
   - (d) an implementation noncompliance that may be exploitable

   It states the claim in a form a tool can check: an LTL property for (a) and (d), a replay script for (b),
   and a pair of conflicting clauses for (c).
3. **Confirm with a tool.** A label is final only when a tool confirms it:
   - (a) and (d): nuXmv on a per-trace model, as DevLyzer does
   - (b): repeated replay
   - (c): a CellularLint-style inconsistency report

   A second model re-derives each property, so the LLM's errors are caught.
4. **Build the exploit.** For confirmed (d) cases, the agent turns the deviating trace into an attack
   sequence, replays it against the UE and records the impact. Findings then go through responsible
   disclosure.

**Metrics.** Triage precision and recall per label, measured against the ground truth that already exists:
- 5GBaseChecker's 45 properties and 36 hand-analysed deviations
- DIKEUE's 17 issues
- Table 8

After that: the number of new confirmed cases, and analyst time per deviation.

**Already in place from Thrust 1:**
- 23 deviation classes with witnesses
- DevLyzer witness-level checks for all 23; proposed final-cell claims still require targeted confirmation
- (c) candidates I19 and I20
- the R1 and R2 repairs: two (a) model-extraction errors, found when device and property evidence sent the
  spec model back to the clause text

### Thrust 3: how far the triage agent can be trusted

The confirmed Thrust 2 discrepancies become a public labelled benchmark. Several LLMs are measured on it
(GPT-4o, DeepSeek-V3, Qwen3):
- **Accuracy** per label
- **Calibration:** expected calibration error and Brier score
- **Bias:** swap vendor names or 3GPP release numbers while the ground truth stays fixed, and count how often
  the label flips

The aim is to know how much of the agent's verdict can be trusted before an analyst acts on it.

## Layout

| Path | What |
|---|---|
| `thrust1/report/thrust1_report.tex` | LaTeX technical report (compile in Overleaf) |
| `thrust1/PLAN.md`, `thrust1/T1_PROGRESS.md` | Implementation plan and full step-by-step log |
| `thrust1/extract/` | TS 24.501 clause indexer, spec-cell extraction, spec FSM builder, SPEC5G mapping |
| `thrust1/spec_fsm/` | Spec FSM (cells JSON, PSMBench JSON, .dot) and `REPAIRS.md` |
| `thrust1/compare/spec_vs_devices.py` | Spec-vs-device comparator (first-point deviations, four-case classification) |
| `thrust1/symbols/` | Symbol alignment with the 5GBaseChecker core, FSM tools (stats, NAS projection, NuSMV) |
| `thrust1/results/` | Result tables and JSON |
| `thrust1/env/` | Dockerfiles and run scripts for the 5GBaseChecker stack |
| `thrust1/lab/` | Learning-run scripts, configs and logs (srsUE), DevLyzer inputs, build logs |
| `thrust1/lab/srsue_checkpoint/RESUME.md` | **How to resume the srsUE learning run after the laptop was off** |
| `ocudu/` | Earlier work: OCUDU gNB + Open5GS + srsUE over ZMQ, end-to-end ping, LaTeX report + PDF |
| `screenshots/` | Screenshots of the runs |
| `proposal/` | PhD proposal (LaTeX) and Thrust 1 output slide |

## Not included (third-party / large)

- 5GBaseChecker (USENIX Security '24): https://github.com/SyNSec-den/5GBaseChecker
- 3GPP TS 24.501 v17.8.0: https://www.3gpp.org/ftp/Specs/archive/24_series/24.501/24501-h80.zip
  (regenerate the clause index with `thrust1/extract/spec_clauses.py`)
- SPEC5G dataset, srsRAN, OCUDU source trees, Docker images.

Research continuation (2026-10-14): [research tools](thrust1/research/README.md),
30-cell clause review, assumption sensitivity, and supplemental fixed-model D4
measurements are available. Live srsUE D4 was started and stopped for teacher review; partial logs are
preserved and no live savings are claimed. The original plan remains incomplete. Thrust 2/3 are not being run.
