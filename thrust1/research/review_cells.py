"""Materialize this session's clause-based review; not a blind extraction ensemble."""
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]

# Findings written by the reviewing model after inspecting full indexed clauses
# and the upstream core source. No device consensus is used as normative truth.
SELECTION=[
('S1','nas_sm_cmd_ns_plain_text','inferred','No KAMF permits no successful ordinary integrity check. Reject is inferred from 5.4.2.5; silence may be a harness observation, not an equivalent protocol action.'),
('S2','nas_sm_cmd_ns_plain_text','supported_with_scope','5.4.2.3 excludes 5G-IA0 outside emergency and W-AGF cases. The experiment is ordinary 3GPP registration.'),
('S3','nas_sm_cmd_ns_plain_text','supported_with_scope','Null-integrity acceptance requires exceptions absent from the stated experiment; rejection/ignore projection is conservative.'),
('S3','id_request_plain_text','supported','4.4.4.2 requires discarding unprotected messages after security establishment. The SUCI exception concerns pre-security processing.'),
('S3','auth_request_plain_text','supported','4.4.4.2 requires discarding unprotected messages once secure exchange is established.'),
('S3','nas_sm_cmd_replay','supported_with_scope','4.4.3.2 permits a COUNT only once in the same context. Requires captured identical protected message and non-IA0 integrity.'),
('S3','registration_accept_plain_text','supported','4.4.4.2 post-security plain-message discard applies.'),
('S3','config_update_cmd_plain_text','supported','4.4.4.2 post-security plain-message discard applies.'),
('S3','deregistration_req_plain_text','supported','4.4.4.2 post-security plain-message discard applies.'),
('S4','id_request_plain_text','supported','The post-security discard rule continues in registered state.'),
('S4','auth_request_plain_text','supported','The post-security discard rule continues in registered state.'),
('S4','registration_accept_plain_text','supported','Plain-message discard applies irrespective of whether repeated Registration Accept is state-compatible.'),
('S4','config_update_cmd_plain_text','supported','The post-security discard rule continues in registered state.'),
('S4','deregistration_req_plain_text','supported','The post-security discard rule continues in registered state.'),
('S4','nas_sm_cmd_replay','supported_with_scope','Same COUNT cannot be accepted twice in one context; rekeying/COUNT changes must be distinguished.'),
('S3','config_update_cmd_replay','supported_with_scope','The replay assertion needs a previously sent buffered command, not simply the symbolic input name.'),
('S4','config_update_cmd_replay','supported_with_scope','The replay assertion needs a previously sent buffered command in the same context.'),
('S1','registration_accept_protected','supported_with_scope','Registration Accept is absent from the pre-security processing list. This assumes the input does not itself establish NAS security.'),
('S2','registration_accept_protected','supported_with_scope','Authentication alone has not established secure exchange; pre-security processing restriction applies.'),
('S1','config_update_cmd_plain_text','supported','Configuration Update is absent from the 4.4.4.2 pre-security processing exception list.'),
('S2','config_update_cmd_protected','supported_with_scope','Authentication alone does not permit processing of Configuration Update before security establishment.'),
('S2','id_request_plain_text','supported_with_scope','Pre-security SUCI request is permitted. 5.4.3.3 sends a fresh SUCI or stored SUCI depending on T3519; both project to id_response.'),
('S1','auth_request_plain_text','supported_with_scope','A fresh valid ordinary AKA challenge requires a response. Invalid RAND/AUTN or synchronization failures are outside the symbolic assumption.'),
('S2','nas_sm_cmd','supported_with_scope','A valid, capability-matching SMC accepted under 5.4.2.3 activates security and returns COMPLETE; validity must be verified in the actual sender.'),
('S3','deregistration_req_protected','supported_with_scope','5.5.1.2.7 collision aborts deregistration only when access types match; note 2 is relevant. Core and model assume 3GPP access.'),
('S2','nas_sm_cmd_protected','needs_state_repair','If the allowed alternative COMPLETE is observed, security should become active. A single next=S2 for all optional outputs loses that state change. Conditional transition support and sensitivity experiment added; baseline preserved.'),
('S3','config_update_cmd_protected','underspecified','5.4.4.3 says when an acknowledgement is required, not that every other response is prohibited. NITZ-only/no-ack assumptions depend on the builder.'),
('S4','config_update_cmd_protected','underspecified','Same conditional acknowledgement rule; this is an ambiguity candidate, not proved exploitable noncompliance.'),
('S3','registration_accept_protected','inferred','5.5.1.2.4 enters REGISTERED, but GUTI-only acknowledgement text is explicit in 5.5.1.3.4. AMF timer behavior is not alone a UE obligation; optional IEs may separately require COMPLETE.'),
('S4','registration_accept_protected','unresolved','7.4 requires STATUS only if this message is state-incompatible. The quote does not itself prove repeated Registration Accept incompatibility; retransmission context must be audited. R2-open sensitivity removes this class.'),
]

def main():
    doc=json.loads((ROOT/'thrust1/spec_fsm/spec_cells_v1.json').read_text())
    rows=[]
    for state,inp,verdict,reason in SELECTION:
        cell=doc['cells'][state][inp]
        rows.append({'state':state,'input':inp,'verdict':verdict,'reason':reason,'current_cell':cell})
    out=ROOT/'thrust1/results/T1_SEMANTIC_REVIEW.json'
    out.write_text(json.dumps({'reviewer':'Codex, current session, 2026-10-14','method':'Clause-based second-model review with access to the existing model. Not blind extraction, not a human independent reference, and not an extraction-accuracy score.','scope':'30 selected protocol cells including all six invisible ones. Other cells and state/harness assumptions still require review.','records':rows},indent=2)+'\n')
    print(out)

if __name__=='__main__':main()
