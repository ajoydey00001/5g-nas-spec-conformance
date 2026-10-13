# Thrust 1 demonstration — ready for teacher review

This is the review milestone agreed on 2026-10-14. The broader research plan is
deferred until feedback; it is not claimed complete.

## What was demonstrated

A specification-backed reference can expose shared behavior that pairwise
comparison of learned device models cannot flag on the same witness.

| Evidence | Result |
|---|---|
| TS 24.501 v17.8.0 reference | 6 states × 16 inputs = 96 cells |
| Textual provenance | 89 evidence quotes match after normalization; 30 no-connection cells have no quotes |
| A/B/srsUE comparison | 23 deviation classes under the current reference |
| Shared witness blind spot | Six complete output sequences agree across all three models but violate the reference |
| srsUE hypothesis 5 | Six states / 21 non-self-loop transitions; expected Table 8 issue recall 7/7 |
| DevLyzer | 23 attack records, seven overlapping benign records, zero unresolved |

## Limits to disclose

- srsUE is a budget-limited hypothesis, not proven converged. The upstream learner
  exited after 30 EQ calls before its normal final writer. The file name
  `srsue_learnedModel.dot` is retained for script compatibility.
- Findings are model/reference discrepancies and property-level corroboration;
  they are not new validated exploits. Some violations arise in witness prefixes.
- Five of the six invisible cells are SPEC; one is INFERRED. Sensitivity testing
  retains six after opening R2 or fixing optional SMC state handling, and retains
  five when inferred-cell judgments are disabled.
- The clause review covers 30 selected cells and is aware of the original model.
  It is not blind ensemble extraction or a human reference evaluation.
- Supplemental D4 uses fixed FSM oracles, not live UEs. All 12 learned outputs
  exactly match their targets; SPEC guidance reduces EQ calls by 5.65–12.47%
  versus Wp alone, while shipped guidance performs better.
- Live D4 was stopped for this review milestone. Partial logs are preserved;
  no live efficiency result or OAI reproduction is claimed.

## What to give the teacher

1. The repository and `thrust1/report/thrust1_report.tex` (compile in Overleaf).
2. `T1_RESULTS_v2.md` for the main experiment.
3. `T1_AUDIT.md` for unresolved issues and the full-plan completion gap.
4. `T1_SEMANTIC_REVIEW.json`, `sensitivity/summary.json`, and `D4_OFFLINE.md`
   as supplementary evidence, keeping their stated limits.

## Verification

Run `bash reproduce.sh`, `bash check_thrust1.sh`, and
`python3 -m unittest discover -s thrust1/tests -v`.
PASS means saved-artifact consistency, not full research completion.

## Questions for feedback

- Is the reference-based blind-spot demonstration sufficient for the next milestone?
- Which reference interpretations should receive independent/manual validation first?
- Should OAI reproduction and live D4 be the next experiments?
