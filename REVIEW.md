# Independent review guide (for a second model, e.g. Claude Fable 5, or a human reviewer)

The goal is an independent check of the Thrust 1 results by a reviewer who did not build them. The reviewer
reruns the analysis, checks the claims against the spec text and the code, and writes down what holds and
what doesn't.

## 1. Set up (the reviewer's own machine and Claude account)

Needs: Linux or macOS, `git`, `curl`, Python 3.8+ (standard library only). No 5G stack, no Docker, no GPU.

```bash
git clone https://github.com/ajoydey00001/5g-nas-spec-conformance.git
cd 5g-nas-spec-conformance
bash reproduce.sh          # ~1 min; downloads TS 24.501 v17.8.0 and the two 5GBaseChecker FSMs
```
Expected end of output:
```
quotes: 89 checked, 0 not found verbatim
summary: Case 2 INVISIBLE to diff: 6, Case 2 visible: 8, Case 3 visible: 9
   classes match committed results: True (23 vs 23)
```

### Option A: Claude Code with Fable (recommended, because the reviewer can run code)

```bash
curl -fsSL https://claude.ai/install.sh | bash     # install Claude Code
cd 5g-nas-spec-conformance
claude                                             # log in with the reviewer's own account
```
Inside Claude Code, type `/model` and choose **Fable**. Then paste the prompt from section 2.

### Option B: claude.ai in the browser (reading only, no code execution)

Start a new chat, select the **Fable** model, attach the repository with **+ → Add from GitHub** (the repo
is public), and paste the prompt from section 2. In this mode the reviewer cannot run `reproduce.sh`. Paste
its output into the chat as well.

## 2. Review prompt (paste as-is)

```text
You are an independent, skeptical reviewer for a security research artifact. Read README.md,
thrust1/PLAN.md (sections 0 and 3), thrust1/results/T1_RESULTS_v1.md, thrust1/spec_fsm/REPAIRS.md and the
code in thrust1/extract, thrust1/compare and thrust1/symbols. Run `bash reproduce.sh` and read repro/.

Claim under review: a specification-derived reference FSM (TS 24.501 v17.8.0, every cell with clause ID and
verbatim quote) finds deviations in learned 5G UE FSMs that device-vs-device differential testing
(5GBaseChecker DevScan) cannot see; on FSM_A/FSM_B, 6 of 23 deviation classes are invisible to DevScan.

Check and report, each with a verdict (holds / partly / does not hold) and evidence (file:line, command
output, or spec clause text):
1. Reproducibility: does reproduce.sh give the stated numbers?
2. Spec fidelity: pick at least 15 cells from thrust1/spec_fsm/spec_cells_v1.json (all 6 Case-2-invisible
   ones, plus random SPEC, INFERRED and UNDERSPECIFIED ones). Read the cited clause in repro/clauses.jsonl.
   Does the quoted text really imply the cell's output and next state? Did the extractor miss an exception
   (e.g. the 4.4.4.2 list of messages that may be processed without integrity protection)?
3. Comparator logic (thrust1/compare/spec_vs_devices.py): are "first-point deviation", the Case 1-4
   classification and "visible_to_diff" defined and computed correctly? Can the "may_block" harness model
   hide real deviations or create false ones? Construct a counterexample if you can.
4. Blind-spot claim: confirm independently, from the FSMs, that FSM_A and FSM_B give identical outputs along
   each invisible witness (so pairwise comparison cannot flag them).
5. Ground truth: compare `fsm_tools.py issues` output with 5GBaseChecker Table 8 / DevLyzer verdicts
   (thrust1/lab/devlyzer). Any disagreement?
6. Overclaiming: list every sentence in README.md, T1_RESULTS_v1.md and thrust1/report/thrust1_report.tex
   that says more than the evidence supports, and suggest a correct rewording.
7. Novelty: relative to 5GBaseChecker (USENIX Sec '24), DIKEUE, 5GReasoner, CellularLint and the
   PSMBench/LLM-extraction line of work, what is actually new here and what is not?
8. Data analysis: from repro/T1.6_spec_vs_AB.json, tabulate deviations by spec state, input, cell kind
   (SPEC / INFERRED) and case. What fraction of findings rests on INFERRED cells or on only one device?
9. Threats to validity the authors did not list, ranked by impact.

Write the result to REVIEW_FABLE.md: a summary verdict, a severity-ranked findings table
(critical / major / minor), the data-analysis tables from item 8, and concrete next steps. Do not modify
any other file. Do not soften findings.
```

## 3. Bringing the review back

The reviewer sends back `REVIEW_FABLE.md`. To add it to the repo:
```bash
cp REVIEW_FABLE.md ~/5g-nas-spec-conformance/thrust1/results/
cd ~/5g-nas-spec-conformance && git add -A && git commit -m "Add independent Fable review" && git push
```
Fixes made in response are logged in `thrust1/T1_PROGRESS.md`, each one pointing to the review item it
answers.

## Notes

- `reproduce.sh` covers the offline analysis (spec FSM, comparator, issue probes). The srsUE learning run
  needs the full Docker stack (`thrust1/env/`, `thrust1/lab/`) and about a day of compute, so it is not part
  of the quick check. Its logs and checkpoints are in `thrust1/lab/srsue_checkpoint/`.
- The spec FSM was extracted by Claude Opus 5.5 in one pass. A review by a different model is exactly the
  independence check this work still lacks.
