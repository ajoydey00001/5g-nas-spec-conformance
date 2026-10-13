# Spec FSM repair log (Thrust 1 loop: evidence → re-read clause → repair or annotate)

| ID | Cell | Draft | Evidence that disagreed | Clause re-read | Repaired to |
|---|---|---|---|---|---|
| R1 | S3 × deregistration_req_protected | deregistration_accept → S5 (5.5.2.3.2) | DevLyzer property 1 (expert property from 5GBaseChecker): before registration completes, a protected DEREGISTRATION REQUEST must be ignored | 5.5.1.2.7: "If the UE receives a DEREGISTRATION REQUEST message from the network in state 5GMM-REGISTERED-INITIATED the de-registration procedure shall be aborted and the initial registration procedure shall be progressed." | null_action, stay S3 |
| R2 | S4 × registration_accept_protected | registration_complete (inferred from 5.5.1.2.4) | Both sample devices (FSM_A path excluded, FSM_B) ignore a second REGISTRATION ACCEPT once registered (Case 2 in T1.6 v1) | 7.4: "If the UE receives a message not compatible with the protocol state, the UE shall return a status message ... with cause #98" — 5GMM STATUS is outside the learner's output alphabet | null_action (observed form of 5GMM STATUS) |
