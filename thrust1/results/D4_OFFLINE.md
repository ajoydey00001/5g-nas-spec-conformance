# Supplemental D4: fixed-model experiment — 2026-10-14

Actual LearnLib TTT/Wp (lookahead 1, 29 inputs), with fresh oracle counters.
Each result is exactly equivalent to the target FSM. This does not replace live UE experiments.

| Target | Arm | MQ calls | EQ calls | EQ reduction vs Wp |
|---|---|---:|---:|---:|
| A | 01_wp | 687 | 18328 | 0.00% |
| A | 02_spec | 687 | 17292 | 5.65% |
| A | 03_shipped | 687 | 15697 | 14.36% |
| A | 04_both | 687 | 15750 | 14.07% |
| B | 01_wp | 734 | 20415 | 0.00% |
| B | 02_spec | 709 | 17869 | 12.47% |
| B | 03_shipped | 710 | 16143 | 20.93% |
| B | 04_both | 709 | 16196 | 20.67% |
| srsue_h5 | 01_wp | 733 | 20312 | 0.00% |
| srsue_h5 | 02_spec | 708 | 17805 | 12.34% |
| srsue_h5 | 03_shipped | 709 | 16081 | 20.83% |
| srsue_h5 | 04_both | 708 | 16134 | 20.57% |

SPEC-only guidance reduces EQ calls on these fixed targets. Shipped guidance
performs better, and combining both costs extra EQ calls relative to shipped
alone. This is not evidence that the proposed method outperforms collaborative
learning. Runtime seconds are Java model-oracle CPU measurements, not radio
learning time. No ground-truth UE behavior beyond the saved target is measured.
