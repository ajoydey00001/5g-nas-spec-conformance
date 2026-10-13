# NAS symbol alignment (T1.4, PLAN.md §3.1)

Confirmed 2026-10-13 from the 5GBaseChecker modified core (Open5GS 2.4.9), clone `642443b7`:
dispatcher `src/amf/testsocket.c`, senders `src/amf/nas-path.c`, builders `src/amf/gmm-build.c`,
encoders `src/amf/nas-security.c`.

Header types (TS 24.501 §9.3.1): 0 plain, 1 integrity, 2 integrity + ciphered,
3 integrity + new context, 4 integrity + ciphered + new context.

"No MAC" below means the message is encoded by `nas_5gs_security_encode_null_security()`: the header
type field is kept, but integrity protection and ciphering are both switched off (no valid MAC, not
ciphered).

| Code symbol | Paper symbol (Table 9) | What the core sends (from code) | Status |
|---|---|---|---|
| `enable_s1` | enable_reg | Not a core message: the learner (`srsueSUL`) starts the UE, which sends Registration Request | confirmed |
| `id_request_plain_text` | identity_req_plain | Identity Request, plain encode (`ogs_nas_5gs_plain_encode`), header 0 | confirmed |
| `auth_request_plain_text` | auth_req_plain | Authentication Request, plain encode, header 0, fresh AV from AUSF | confirmed |
| `nas_sm_cmd` | nas_sm_cmd_int | Security Mode Command, header 3, negotiated NIA/NEA; buffer stored for replay | confirmed |
| `nas_sm_cmd_protected` | nas_sm_cmd_header2_protected | Security Mode Command, header 2 (integrity + ciphered) | confirmed |
| `nas_sm_cmd_replay` | nas_sm_cmd_replay | Re-sends the stored `nas_sm_cmd` buffer unchanged (same COUNT/MAC); `null_action` if none stored | confirmed |
| `nas_sm_cmd_ns` | nas_sm_cmd_NIA0_int | Security Mode Command selecting NIA0/NEA0, header 3, encoded with MAC (`nas_5gs_security_encode`) | confirmed |
| `nas_sm_cmd_ns_plain_text` | nas_sm_cmd_NIA0_plain | Same SMC selecting NIA0/NEA0, header 3, **no MAC** | confirmed |
| `registration_accept_protected` | reg_accept_protected | Registration Accept, header 2; sent via NGAP DownlinkNASTransport (`*_dlnas`); `null_action` before SMC | confirmed |
| `registration_accept_plain_text` | reg_accept_plain | Registration Accept, header 0 | confirmed |
| `registration_accept_h4_plain_text` | reg_accept_header4_plain | Registration Accept, header field 4 but **no MAC, not ciphered** | confirmed |
| `config_update_cmd_protected` | conf_update_cmd_protected | Configuration Update Command (NITZ), header 2; buffer stored for replay | confirmed |
| `config_update_cmd_plain_text` | conf_update_cmd_plain | Configuration Update Command (NITZ), header 0 | confirmed |
| `config_update_cmd_replay` | conf_update_cmd_replay | Re-sends the stored protected Configuration Update Command | confirmed |
| `deregistration_req_protected` | dereg_req_protected | Network-initiated Deregistration Request, header 2 | confirmed |
| `deregistration_req_plain_text` | dereg_req_plain | Network-initiated Deregistration Request, header 0, no MAC | confirmed |

## Notes for the spec FSM (T1.5)

- Several symbols answer `null_action` from the **core side** when a precondition fails (no K_AMF, no NAS
  keys, nothing stored for replay). For example, `nas_sm_cmd` before authentication never reaches the UE.
  So `null_action` in a learned FSM can mean "the UE ignored it" **or** "the core did not send it". The
  spec FSM has to model the same preconditions, or these edges will show up as false Case 2 deviations
  (PLAN.md §7, "symbol mismatch").
- Preconditions found in `testsocket.c`:
  - `nas_sm_cmd`, `nas_sm_cmd_ns`: need K_AMF (i.e. after a successful authentication)
  - `nas_sm_cmd_protected`, `config_update_cmd_protected`, `config_update_cmd_replay`: need K_NASint and K_NASenc
  - `nas_sm_cmd_replay`: needs a stored SMC and K_NASint
  - `registration_accept_protected`: needs K_gNB (after SMC)
- The **learner** adds its own preconditions on top (`UESUL.context_check()`), also answered with `null_action`
  without sending anything:
  - every symbol except `enable_s1` needs a live radio link (`radio_check()`)
  - `nas_sm_cmd_protected`, `registration_accept_protected`, `config_update_cmd_protected` need an earlier
    `auth_request_plain_text` in the same query
  - `nas_sm_cmd_replay` needs an earlier `nas_sm_cmd`; `config_update_cmd_replay` needs an earlier
    `config_update_cmd_protected`
  - once `nas_sm_complete` was seen more than once and `auth_response` at least twice, everything returns
    `null_action` (srsueSUL also has a `>= 1` / `>= 2` variant of this cut-off)
- If more than one Registration Request is seen in one query (`regis_count > 1`), every later symbol returns
  `null_action` until `RACH_Reset`.
- "plain_text" in a symbol name does not always mean header type 0: `registration_accept_h4_plain_text`
  keeps header type 4 and only drops the MAC and ciphering.
