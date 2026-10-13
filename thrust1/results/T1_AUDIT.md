# Thrust 1 consistency audit — 2026-10-14

## Verdict

The saved proof-of-concept results reproduce. **The original Thrust 1 research
plan is not complete**, and an all-PASS artifact check does not assure scientific
correctness or completion. Earlier statements that Thrust 1 was complete should
be read as finalization of this demonstration only.

## Verified results

- `bash reproduce.sh`: 1,181 clauses, 96 cells, 89 normalized evidence quotes
  found, exact two-device comparison reproduced: 23 classes, six invisible.
- `bash check_thrust1.sh`: preserved model hash, exact three-device comparison,
  7/7 issue probes, six witnesses with identical complete outputs on all three
  models, saved DevLyzer category counts, and explicit budget provenance.
- The preserved model has 29 input symbols and 174 total edges; earlier
  31-symbol setup descriptions are stale. Its security and registration
  prefixes return Registration Request, Authentication Response, SMC Complete,
  and Registration Complete as appropriate.
- srsUE hypothesis 5 has six states / 21 non-self-loop transitions; paper
  comparison is six / 20. It is not a converged final model.
- Three-device classes: 20 SPEC and three INFERRED; 15 classes have three
  prefix-conforming devices, eight have two (FSM_A is excluded after its
  registration failure). No prefix-conforming device reaches a different
  named spec state in these 23 saved witnesses under the current simulator.
- DevLyzer: 23 attack records, seven benign records, zero unresolved. All
  seven benign IDs also occur in the attack set; categories are not exclusive.

## Findings and disposition

| Severity | Finding | Evidence / disposition |
|---|---|---|
| Major | Completion criteria were narrowed without eliminating contradictory prose | PLAN.md D1 requires UE reproduction and D4 measures guided-learning savings; these are not established. README, PLAN, NEXT_STEPS and VERIFY_AND_RECOVER now distinguish artifact finalization from research completion. |
| Major | DevLyzer trace violations were described as confirmation of every final-cell class | Class 23, S4 × protected Registration Accept, has property 11 on B/srsUE, concerning the preceding null-integrity SMC rejection. That property does not validate the final-cell R2 inference. Report/results now qualify corroboration. Targeted cell confirmation remains open. |
| Major | “Independent” confirmation overstated independence | R1 used property evidence and R2 used device observations to repair the reference. The expert properties are external, but the final reference incorporates those observations. Claims corrected. |
| Major | Budget-limited hypothesis could be mistaken for completed learning | LogOracle.java calls System.exit(0) after 30 equivalence-query calls in CE-feeding mode. Learner.java writes learnedModel.dot only through another termination path. Provenance explicitly says converged=false. No source change or convergence experiment was performed in this audit. |
| Major | Spec/harness abstractions still require semantic validation | Null output can denote suppressed delivery, ignored input, unsupported STATUS output, or timeout. The builder uses strict blocked() while the comparator uses permissive may_block(). Generated DOT is an illustrative strict product, not the comparator's oracle. Treating accepted header-type-2 SMC as UNDERSPECIFIED permits nas_sm_complete but retains the same spec state, including S2; the next-state semantics need audit. No speculative semantic repair was made. |
| Moderate | Every Case 2 was described as invisible | Eight Case 2 classes are visible along their prefixes. Only the six with visible_to_diff=false and identical entire output sequences establish the claimed witness blind spot. Report corrected. |
| Moderate | Quote checking printed failures but returned success; reproduce.sh also tolerated mismatches | Builder now rejects missing/mismatched evidence before writing output; reproduction now exits on regenerated-cell or full-result mismatch and enables pipefail. Regression tests cover invalid and missing evidence. |
| Moderate | Recall probes alone cannot establish reachability or absence generally | fsm_tools.py checks final outputs of selected words without validating their prefixes. For hypothesis 5 the canonical security/registration prefixes return expected outputs. For FSM_A, post-registration probes should not imply the registered situation was reached. General probe reporting remains limited. |
| Moderate | Fresh-checkout prerequisites were implicit | repro/ is ignored. Run reproduce.sh before check_thrust1.sh; cached-input checks do not independently authenticate downloads. DevLyzer checks in the completion script inspect saved output rather than rerunning the checker. |
| Minor | Evidence was called “verbatim” without stating normalization | check_quotes normalizes whitespace and selected punctuation. It verifies normalized substring presence, not exact bytes or entailment. Thirty NO_CONNECTION cells have no quotes; 89 is the number of evidence records, not transitions. |
| Minor | Report artifact path and exact-reproduction claims were stale | Report points to thrust1/ and retains observed 6/21 vs paper 6/20. Historical v1 results and progress entries remain historical, not current status. |

## What is needed to complete the original plan

1. Audit protocol and harness semantics against the full clauses and actual
   delivered message contents, including optional-output next states, R2,
   COUNT/replay, security changes, and NAS connection release.
2. Perform the independent/reference validation specified in PLAN.md §3.2:
   repeated extraction/ensemble agreement, reference evaluation, a transition
   audit, and suitable property checks. This audit is a consistency review,
   not a second extraction or independent human validation.
3. Complete or explicitly revise D1's OAI UE reproduction requirement. FSM_A/B
   identities are unpublished and cannot substitute for named OAI reproduction.
4. Establish convergence if claiming a final learned model; otherwise retain
   the explicitly bounded experimental scope and account for 6/21 vs 6/20,
   NEA0 use, and different query budgets.
5. Run D4 guided-learning experiments with controlled baselines, MQ/EQ/time
   measurement and final-model equivalence. Manual R1/R2 repairs demonstrate
   feedback, not reduced learning cost or an automated repair loop.
6. Compile/review the updated report PDF; no LaTeX compiler is installed here.

Safe claim now: “We finalized a reproducible specification-reference
proof of concept: 23 model-derived deviation classes and six witnesses whose
outputs agree across three UE models but disagree with the current reference.
The srsUE model is budget-limited; full semantic validation and guided-learning
experiments remain future work.”
