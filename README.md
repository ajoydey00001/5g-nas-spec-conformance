# 5G NAS spec-conformance — Thrust 1 work (Ajoy Dey)

Work prepared for Dr. Imtiaz Karim (SysNetS Lab, UT Dallas).

**Thrust 1 idea:** extract a *specification* reference FSM for the 5G NAS UE from TS 24.501 (every transition
tied to a clause ID and a verbatim quote), then compare learned UE FSMs against the spec instead of only against
each other. Device-vs-device differential testing (5GBaseChecker's DevScan) cannot see a deviation that all
devices share; the spec reference can.

## Main results so far (details: [`thrust1/results/T1_RESULTS_v1.md`](thrust1/results/T1_RESULTS_v1.md))

- Spec FSM: 6 states × 16 NAS inputs = 96 cells from TS 24.501 v17.8.0; **89/89 quotes verified verbatim**.
- Against the two learned UE FSMs shipped with 5GBaseChecker: **23 deviation classes**,
  of which **6 are invisible to differential testing** (both devices answer identically, both wrong):
  plain Identity/Authentication Request after security (I3, I4), replayed SMC (I6), null-integrity SMC (I10).
- **All 23 confirmed** independently by the authors' DevLyzer (45 LTL properties).
- Two spec-model repairs (R1, R2) found by feeding device/property evidence back to the spec text, plus a
  candidate spec gap (5.5.1.2.4 vs 5.5.1.3.4).
- srsUE learning run (Table 4 configuration) in progress; early queries already show I3, I4, I6/I7, I10, I19,
  I20, matching the paper's Table 8 ground truth. Final model and report v2 will be added when it finishes.

## Next: Thrust 2 and Thrust 3 (planned)

The plan is the one in the PhD proposal (`proposal/Ajoy_Dey_PhD_Proposal.tex`). Thrust 1 already produces
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
- DevLyzer confirmation of all 23, i.e. step 3 already done for these noncompliance candidates
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
| `ocudu/` | Earlier work: OCUDU gNB + Open5GS + srsUE over ZMQ, end-to-end ping, LaTeX report + PDF |
| `screenshots/` | Screenshots of the runs |
| `proposal/` | PhD proposal (LaTeX) and Thrust 1 output slide |

## Not included (third-party / large)

- 5GBaseChecker (USENIX Security '24): https://github.com/SyNSec-den/5GBaseChecker
- 3GPP TS 24.501 v17.8.0: https://www.3gpp.org/ftp/Specs/archive/24_series/24.501/24501-h80.zip
  (regenerate the clause index with `thrust1/extract/spec_clauses.py`)
- SPEC5G dataset, srsRAN, OCUDU source trees, Docker images.
