# Thrust 1 results v2 — spec reference vs differential testing (2026-10-14)

Devices: FSM_A, FSM_B and srsUE hypothesis 5. The srsUE artifact is a
**budget-limited hypothesis, not a converged learned model**. It is stored as
`srsue_learnedModel.dot` for script compatibility; provenance is in
`srsue_model_provenance.json`.

| Metric | Paper srsUE | This experiment |
|---|---|---|
| States / non-self-loop transitions | 6 / 20 | 6 / 21 |
| Expected Table 8 NAS issues recovered | 7 | 7/7 |
| I6 | not listed for srsUE | present |
| Three-device deviation classes | — | 23 |
| Invisible / visible Case 2 / Case 3 | — | 6 / 8 / 9 |
| DevLyzer attack / benign / unresolved witness records | — | 23 / 7 / 0 |

Attack and benign records overlap: seven witnesses also have a nonviolating
device-output group. These counts are not an exclusive partition.

The learner exits after 30 equivalence-query calls in CE reverse feeding mode,
before its normal final-model writer. Cached resumes reproduce the same model
and exit again. The archived hypothesis-5 copies have identical SHA-256 hashes.
The checkpoint contains 1,484 saved answers; this is not a directly comparable
paper MQ/EQ count. Both I9 probes pass but I9 counts once in recall.
The six invisible witnesses have identical complete output sequences across all
three models. DevLyzer corroborates witness-level property violations; it does
not independently prove each spec interpretation or exploit impact.

Spec model: `spec_fsm/spec_cells_v1.json` — 6 states × 16 NAS inputs = 96 cells, extracted from TS 24.501 v17.8.0
(53 SPEC, 8 INFERRED, 5 UNDERSPECIFIED, 30 NO_CONNECTION), protocol evidence is attached where applicable; the 30 NO_CONNECTION cells have no quotes;
**89/89 quotes verified verbatim** against the spec text. Extractor: Claude in a Claude Code session, one sample
per cell (no API key; see limitations).

## D2 — the blind spot of device-vs-device differential testing

DevScan on FSM_A vs FSM_B (authors' tool, T1.1) reports **8 deviations**; every one ends at
`nas_sm_cmd_ns` (SMC with NIA0). **None ends at** a plain Identity Request, a plain Authentication Request,
a replayed SMC, or a header-type-2 SMC after security — because FSM_A and FSM_B behave the same there.

## D3 — the spec reference closes it

`compare/spec_vs_devices.py` (first-point deviations, harness preconditions modelled as uncertain):
23 deviation classes; **6 Case 2 classes are invisible to differential testing** (identical device outputs along
the whole witness):

| Spec cell | Spec (clause) | FSM_A | FSM_B | Issue | DevLyzer property violated |
|---|---|---|---|---|---|
| id_request_plain_text after SMC (S3) | discard (4.4.4.2) | id_response | id_response | I3 | 4 (both) |
| auth_request_plain_text after SMC (S3) | discard (4.4.4.2) | auth_response | auth_response | I4 | 6 (both) |
| nas_sm_cmd_replay after SMC (S3) | discard (4.4.3.2) | nas_sm_complete | nas_sm_complete | I6 | 8, 9 (both) |
| nas_sm_cmd_ns_plain_text (S2, S3) | SECURITY MODE REJECT (5.4.2.3, 5.4.2.5) | nas_sm_complete | nas_sm_complete | I10 | 12, 13 (both) |
| nas_sm_cmd_ns_plain_text before auth (S1) | reject (inferred) | nas_sm_complete | nas_sm_complete | I10 variant | 12, 13 (both) |

(c) candidates — spec silent (UNDERSPECIFIED cells), device behaviour reported, not judged:

| Cell | FSM_A | FSM_B | Issue (paper class) |
|---|---|---|---|
| nas_sm_cmd_protected (header type 2 SMC) after SMC | nas_sm_complete | nas_sm_complete | I19 (U1) — shared, so also invisible to diff |
| config_update_cmd_protected, NITZ only, no ack requested | null_action | config_update_complete | I20 (U2) |

Independent confirmation: all 23 deviation classes, fed to the authors' DevLyzer in its own
`deviant-queries.json` format, are classified as property violations (0 unresolved). The spec model was not
built from these properties, and the properties were not written for our spec model.

## The loop: device/property evidence repairs the spec model (`spec_fsm/REPAIRS.md`)

| Repair | Draft cell | Evidence | Re-read clause | Result |
|---|---|---|---|---|
| R1 | S3 × protected DEREGISTRATION REQUEST → accept | DevLyzer property 1 | 5.5.1.2.7 collision rule | ignore while REGISTERED-INITIATED |
| R2 | S4 × second REGISTRATION ACCEPT → REGISTRATION COMPLETE | devices ignore it | 7.4 (not compatible with protocol state → 5GMM STATUS #98) | null_action |

Also found while extracting: v17.8.0 states the UE's "acknowledge the received 5G-GUTI with REGISTRATION COMPLETE"
rule only for mobility/periodic registration (5.5.1.3.4), not for initial registration (5.5.1.2.4), although the
AMF waits for REGISTRATION COMPLETE in both (T3550). Candidate (c) spec gap.

Also found: DevLyzer property 1 is imprecise (its "never registration_complete" only looks forward, so a UE that
registered, re-keyed and is then deregistered counts as unregistered). The 45 properties are strong evidence,
not ground truth.

## Limitations (say these out loud)

- FSM_A/FSM_B device identities are not published; their ground truth is DevLyzer's verdict, not Table 8.
  Table 8 comparison applies to srsUE (7/7 here); OAI UE was not run.
- One extraction sample per cell, by the same model that wrote the comparator; no ensemble, no API run yet.
  A scripted re-extraction (Gemini free tier / DeepSeek / Claude API) is needed before a paper.
- Harness preconditions are modelled as "may block": where the core or learner might suppress a message,
  null_action is always accepted, so a device that wrongly stays silent in exactly those situations is not
  flagged. Deviations where a device answers when it should not (I3, I4, I6/I7, I10) are unaffected.
- FSM_A does not complete registration; the three-device S4 analysis includes FSM_B and srsUE.
- Quote matching establishes textual provenance, not semantic correctness.
- Independent spec extraction/audit and guided-learning D4 cost experiments remain outstanding.
- The srsUE result is budget-limited and uses NEA0; convergence and NEA2 behavior are not established.
