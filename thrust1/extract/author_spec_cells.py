"""Spec FSM v1 for the 16 NAS inputs, as extracted from TS 24.501 v17.8.0 (T1.5, PLAN.md §3.2).

Extractor: Claude (Opus 5.5) inside a Claude Code session, 2026-10-13, reading only the clause texts
printed by extract/dump_clauses.py from ts24501_v17.8.0_clauses.jsonl (no API key available, so one sample
per cell and no ensemble vote; see T1_PROGRESS.md). Running this file writes spec_cells_v1.json.

Each cell answers: "a compliant UE in STATE receives INPUT (the exact message the 5GBaseChecker core
builds, symbols/alignment.md) — what does it send, and which state is it in afterwards?"
The test harness (core/learner preconditions, cut-offs) is NOT modelled here; build_spec_fsm.py adds it.

kind:
  SPEC            the quoted clause states the behaviour directly ("shall")
  INFERRED        follows from the quoted clause(s) but not stated for exactly this case (note says why)
  UNDERSPECIFIED  the spec does not say what the UE does; output = most conservative reading,
                  also_allowed = other readings. These are (c) candidates in the four-case classifier.
  NO_CONNECTION   UE has no NAS signalling connection, nothing can be received
also_allowed: further outputs a compliant UE may send ("may" behaviour / two compliant readings).
"""
import json
import sys

STATES = {
    'S0': 'Before enable_s1: UE powered on in 5GMM-DEREGISTERED, no NAS signalling connection.',
    'S1': '5GMM-REGISTERED-INITIATED: REGISTRATION REQUEST sent for initial registration; no 5G NAS '
          'security context; not authenticated on this connection.',
    'S2': '5GMM-REGISTERED-INITIATED: 5G AKA completed (new KAMF in a partial native 5G NAS security '
          'context); secure exchange of NAS messages NOT yet established (no SECURITY MODE COMMAND accepted).',
    'S3': '5GMM-REGISTERED-INITIATED: SECURITY MODE COMMAND accepted, secure exchange of NAS messages '
          'established; REGISTRATION ACCEPT not yet received.',
    'S4': '5GMM-REGISTERED: REGISTRATION ACCEPT processed (REGISTRATION COMPLETE sent); secure exchange '
          'of NAS messages established.',
    'S5': '5GMM-DEREGISTERED after a network-initiated de-registration completed; NAS signalling '
          'connection released.',
}

Q = {  # clause_id, verbatim quote
    'list':     ('4.4.4.2', 'Except the messages listed below, no NAS signalling messages shall be processed by the receiving 5GMM entity in the UE or forwarded to the 5GSM entity, unless the network has established secure exchange of 5GS NAS messages for the NAS signalling connection'),
    'list_id':  ('4.4.4.2', 'IDENTITY REQUEST (if requested identification parameter is SUCI);'),
    'list_auth': ('4.4.4.2', 'AUTHENTICATION REQUEST;'),
    'plain_after': ('4.4.4.2', 'If any NAS signalling message is received as not integrity protected even though the secure exchange of NAS messages has been established by the network, then the NAS shall discard this message.'),
    'mac_fail': ('4.4.4.2', 'If NAS signalling messages, having not successfully passed the integrity check, are received, then the NAS in the UE shall discard that message.'),
    'id_resp':  ('5.4.3.3', 'if timer T3519 is not running, generate a fresh SUCI as specified in 3GPP TS 33.501 [24], send an IDENTITY RESPONSE message with the SUCI'),
    'auth_resp': ('5.4.1.3.3', 'the UE shall process the 5G authentication challenge data and respond with an AUTHENTICATION RESPONSE message to the network.'),
    'smc_check': ('5.4.2.3', 'This is done by performing the integrity check of the message'),
    'smc_ok':   ('5.4.2.3', 'If the SECURITY MODE COMMAND message can be accepted, the UE shall send a SECURITY MODE COMPLETE message integrity protected with the selected 5GS integrity algorithm'),
    'smc_rej':  ('5.4.2.5', 'If the security mode command cannot be accepted, the UE shall send a SECURITY MODE REJECT message.'),
    'ia0':      ('5.4.2.3', 'The UE shall accept a SECURITY MODE COMMAND message indicating the "null integrity protection algorithm" 5G-IA0 as the selected 5G NAS integrity algorithm only if the message is received when'),
    'smc_unciph': ('5.4.2.2', 'The AMF shall send the SECURITY MODE COMMAND message unciphered'),
    'smc_change': ('5.4.2.2', 'The AMF may initiate a SECURITY MODE COMMAND in order to change the 5G security algorithms for a current 5G NAS security context already in use.'),
    'replay':   ('4.4.3.2', 'for a given 5G NAS security context, a given NAS COUNT value shall be accepted at most one time and only if message integrity verifies correctly.'),
    'reg_acc':  ('5.5.1.2.4', 'Upon receipt of the REGISTRATION ACCEPT message, the UE shall reset the registration attempt counter, enter state 5GMM-REGISTERED and set the 5GS update status to 5U1 UPDATED.'),
    'guti_amf': ('5.5.1.2.4', 'If a 5G-GUTI or the SOR transparent container IE is included in the REGISTRATION ACCEPT message, the AMF shall start timer T3550 and enter state 5GMM-COMMON-PROCEDURE-INITIATED'),
    'cu_ack':   ('5.4.4.3', 'If "acknowledgement requested" is indicated in the Acknowledgement bit of the Configuration update indication IE in the CONFIGURATION UPDATE COMMAND message, the UE shall send a CONFIGURATION UPDATE COMPLETE message.'),
    'cu_nitz':  ('5.4.4.2', 'Acknowledgement shall be requested for all parameters except when only NITZ is included.'),
    'dereg':    ('5.5.2.3.2', 'The UE shall send a DEREGISTRATION ACCEPT message to the network and enter the state 5GMM-DEREGISTERED for 3GPP access.'),
    'dereg_collision': ('5.5.1.2.7', 'If the UE receives a DEREGISTRATION REQUEST message from the network in state 5GMM-REGISTERED-INITIATED the de-registration procedure shall be aborted and the initial registration procedure shall be progressed.'),
    'not_compat': ('7.4', 'If the UE receives a message not compatible with the protocol state, the UE shall return a status message (5GMM STATUS or 5GSM STATUS depending on the EPD) with cause #98 "message type not compatible with protocol state".'),
    'reg_init': ('5.5.1.2.2', 'The UE in state 5GMM-DEREGISTERED shall initiate the registration procedure for initial registration by sending a REGISTRATION REQUEST message to the AMF,'),
}

NULL = 'null_action'


def cell(output, nxt, kind, *quotes, also=(), note=''):
    return {'output': output, 'next': nxt, 'kind': kind, 'also_allowed': list(also),
            'evidence': [{'clause_id': Q[q][0], 'quote': Q[q][1]} for q in quotes], 'note': note}


def no_conn(s):
    return cell(NULL, s, 'NO_CONNECTION', note='no NAS signalling connection')


def build():
    C = {}
    pre_sec = ('S1', 'S2')        # secure exchange not established
    post_sec = ('S3', 'S4')       # secure exchange established
    for s in STATES:
        C[s] = {}
        # enable_s1 = power-cycle + registration (the learner restarts core, gNB and UE): always a fresh S1
        C[s]['enable_s1'] = cell('registration_request', 'S1', 'SPEC', 'reg_init',
                                 note='the learner restarts the whole stack, so the UE always starts deregistered')
        if s in ('S0', 'S5'):
            for a in INPUTS[1:]:
                C[s][a] = no_conn(s)
            continue
        pre = s in pre_sec
        nxt_auth = 'S2' if pre else s

        # --- plain messages allowed only before security (4.4.4.2 a, b) ---
        if pre:
            C[s]['id_request_plain_text'] = cell('id_response', s, 'SPEC', 'list_id', 'id_resp',
                                                 note='core requests SUCI (gmm_build_identity_request)')
            C[s]['auth_request_plain_text'] = cell('auth_response', 'S2', 'SPEC', 'list_auth', 'auth_resp',
                                                   note='core sends a fresh AV each time, so no SQN/RAND reuse')
        else:
            C[s]['id_request_plain_text'] = cell(NULL, s, 'SPEC', 'plain_after', note='I3')
            C[s]['auth_request_plain_text'] = cell(NULL, s, 'SPEC', 'plain_after', note='I4')

        # --- security mode command family ---
        if s == 'S1':
            for a in ('nas_sm_cmd', 'nas_sm_cmd_protected', 'nas_sm_cmd_ns', 'nas_sm_cmd_ns_plain_text'):
                C[s][a] = cell('nas_sm_reject', s, 'INFERRED', 'smc_check', 'smc_rej', also=[NULL],
                               note='no KAMF yet, so the integrity check cannot pass')
        else:
            if s == 'S2':
                C[s]['nas_sm_cmd'] = cell('nas_sm_complete', 'S3', 'SPEC', 'smc_check', 'smc_ok')
            else:
                C[s]['nas_sm_cmd'] = cell('nas_sm_complete', s, 'INFERRED', 'smc_change', 'smc_ok',
                                          note='fresh SMC (new COUNT) on an active context: algorithm change')
            C[s]['nas_sm_cmd_protected'] = cell(
                NULL, s, 'UNDERSPECIFIED', 'smc_unciph', 'smc_check',
                also=['nas_sm_reject', 'nas_sm_complete'],
                note='I19 (paper U1): the AMF must send SMC unciphered with header type 3; the UE-side handling '
                     'of a ciphered header-type-2 SMC is not specified')
            C[s]['nas_sm_cmd_ns'] = cell('nas_sm_reject', s, 'SPEC', 'ia0', 'smc_rej', also=[NULL],
                                         note='5G-IA0 only for emergency / W-AGF; DevLyzer props 10/11 allow reject or ignore')
            C[s]['nas_sm_cmd_ns_plain_text'] = cell('nas_sm_reject', s, 'SPEC', 'ia0', 'smc_rej', also=[NULL],
                                                    note='I10: 5G-IA0 and no valid MAC')
        C[s]['nas_sm_cmd_replay'] = cell(NULL, s, 'SPEC', 'replay',
                                         note='I6 (right after SMC) / I7 (after registration)')

        # --- registration accept family ---
        if pre:
            for a in ('registration_accept_protected', 'registration_accept_h4_plain_text', 'registration_accept_plain_text'):
                C[s][a] = cell(NULL, s, 'SPEC', 'list', note='not in the 4.4.4.2 list of messages processed before security')
        else:
            if s == 'S4':
                # repair R2 (2026-10-13): v1 draft answered registration_complete again; a REGISTRATION ACCEPT
                # with no registration pending is not compatible with 5GMM-REGISTERED -> 5GMM STATUS #98,
                # which is outside the learner's output alphabet (observed as null_action)
                C[s]['registration_accept_protected'] = cell(
                    NULL, s, 'INFERRED', 'not_compat',
                    note='repair R2: 5GMM STATUS #98 is not in the output alphabet, observed as null_action')
            else:
                C[s]['registration_accept_protected'] = cell(
                    'registration_complete', 'S4', 'INFERRED', 'reg_acc', 'guti_amf',
                    note='open5gs includes a new 5G-GUTI; the explicit UE rule "return a REGISTRATION COMPLETE ... to '
                         'acknowledge the received 5G-GUTI" exists only in 5.5.1.3.4 (mobility registration), not in 5.5.1.2.4')
            C[s]['registration_accept_h4_plain_text'] = cell(NULL, s, 'SPEC', 'mac_fail',
                                                             note='header type 4 but no valid MAC')
            C[s]['registration_accept_plain_text'] = cell(NULL, s, 'SPEC', 'plain_after', note='I9 (reg_accept_plain)')

        # --- configuration update family ---
        if pre:
            for a in ('config_update_cmd_protected', 'config_update_cmd_plain_text', 'config_update_cmd_replay'):
                C[s][a] = cell(NULL, s, 'SPEC', 'list', note='not in the 4.4.4.2 list of messages processed before security')
        else:
            C[s]['config_update_cmd_protected'] = cell(
                NULL, s, 'UNDERSPECIFIED', 'cu_nitz', 'cu_ack', also=['config_update_complete'],
                note='I20 (paper U2): core sends NITZ only, no acknowledgement requested; the UE is told when to '
                     'send COMPLETE but not forbidden to send it otherwise')
            C[s]['config_update_cmd_plain_text'] = cell(NULL, s, 'SPEC', 'plain_after', note='I9 (conf_update_cmd_plain)')
            C[s]['config_update_cmd_replay'] = cell(NULL, s, 'SPEC', 'replay')

        # --- network-initiated de-registration ---
        if pre:
            for a in ('deregistration_req_protected', 'deregistration_req_plain_text'):
                C[s][a] = cell(NULL, s, 'SPEC', 'list', note='not in the 4.4.4.2 list of messages processed before security')
        else:
            if s == 'S3':
                # repair R1 (2026-10-13): v1 draft said deregistration_accept; DevLyzer property 1 disagreed and
                # the collision rule in 5.5.1.2.7 confirms the UE must ignore it while REGISTERED-INITIATED
                C[s]['deregistration_req_protected'] = cell(NULL, s, 'SPEC', 'dereg_collision',
                                                            note='repair R1: collision with initial registration')
            else:
                C[s]['deregistration_req_protected'] = cell('deregistration_accept', 'S5', 'SPEC', 'dereg',
                                                            note='core: re-registration not required, 3GPP access')
            C[s]['deregistration_req_plain_text'] = cell(NULL, s, 'SPEC', 'plain_after')
    return C


INPUTS = ('enable_s1 id_request_plain_text auth_request_plain_text nas_sm_cmd nas_sm_cmd_protected '
          'nas_sm_cmd_replay nas_sm_cmd_ns nas_sm_cmd_ns_plain_text registration_accept_protected '
          'registration_accept_h4_plain_text registration_accept_plain_text config_update_cmd_protected '
          'config_update_cmd_plain_text config_update_cmd_replay deregistration_req_protected '
          'deregistration_req_plain_text').split()

if __name__ == '__main__':
    cells = build()
    assert all(set(cells[s]) == set(INPUTS) for s in STATES), 'every (state, input) cell must be filled'
    doc = {'spec': 'TS 24.501 v17.8.0', 'extractor': 'Claude Opus 5.5 (Claude Code session), 1 sample per cell',
           'date': '2026-10-13', 'initial_state': 'S0', 'states': STATES, 'inputs': INPUTS, 'cells': cells}
    json.dump(doc, open(sys.argv[1], 'w'), indent=1)
    kinds = {}
    for s in cells:
        for a in cells[s]:
            kinds[cells[s][a]['kind']] = kinds.get(cells[s][a]['kind'], 0) + 1
    print('%d cells -> %s  %s' % (sum(kinds.values()), sys.argv[1], kinds))
