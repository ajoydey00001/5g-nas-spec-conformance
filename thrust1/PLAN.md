# Implementation plan: Thrust 1 → 2 → 3 (5G NAS only)

Last verified: 2026-10-12, against the repos and papers listed in §10.
Proposal: `proposal/Ajoy_Dey_PhD_Proposal.tex`. Scope: 5G NAS (TS 24.501) only; no 4G.

---

## 0. What "my idea works" will look like

Everything below runs on one Linux laptop with a **simulated radio** (no phone, no USRP).

| # | What it shows | Evidence |
|---|---|---|
| D1 | I can run the pipeline the lab builds on | Reproduce 5GBaseChecker's srsUE and OAI UE results (Table 4 FSM sizes, Table 8 issue sets) with its released code and 45 properties |
| D2 | Differential testing has a blind spot | srsUE-vs-OAI UE comparison (DevScan) cannot show the issues both UEs share |
| D3 | A spec reference closes it | Spec FSM (LLM, TS 24.501 v17.8.0) vs each UE flags those shared issues as **Case 2** |
| D4 | The loop pays for itself | Spec transitions used as potential counterexamples cut equivalence queries, most of all for a first device with no other device's counterexamples |

### 0.1 Ground truth for the two open-source UEs

From 5GBaseChecker [USENIX Sec '24] Table 2 (issues) and Table 8 (which device has which issue).

| Issue | Behavior | Flaw type | Layer | OAI UE 2023.w33 | srsUE release_22_10 | srsUE-vs-OAI diff can see it? | Expected label |
|---|---|---|---|---|---|---|---|
| I3 | accepts identity_req_plain after NAS security activation | M3, M4 | NAS | yes | yes | **no (shared)** | (d) |
| I4 | accepts auth_req_plain after NAS security activation | M3, M4 | NAS | yes | yes | **no (shared)** | (d) |
| I6 | accepts nas_sm_cmd_replay right after nas_sm_cmd_int | M6 | NAS | yes | – | yes | (d) |
| I7 | accepts nas_sm_cmd_replay after registration complete | M6 | NAS | – | yes | yes | (d) |
| I9 | plain-header NAS (reg_accept_plain, conf_update_cmd_plain) bypass integrity check | S | NAS | – | yes | yes | (d) |
| I10 | accepts nas_sm_cmd_NIA0_plain | I | NAS | yes | yes | **no (shared)** | (d) |
| I11 | accepts rrc_sm_cmd_NIA0_plain | I | RRC | yes | yes | no (shared) | out of NAS scope |
| I17 | does not accept reg_accept_protected inside DL NAS Transport | U1 | NAS | yes | – | yes | (c) candidate |
| I19 | accepts nas_sm_cmd_header2_protected | U1 | NAS | yes | yes | **no (shared)** | (c) candidate |
| I20 | replies conf_update_comp when acknowledgment indicator absent | U2 | NAS | – | yes | yes | (c) candidate |

- Shared NAS issues **I3, I4, I10, I19** are the demo. With only these two UEs, device-vs-device comparison sees identical behavior and reports nothing for them. 5GBaseChecker exposed them only because some commercial phones behaved correctly.
- Expected-label rule: 5GBaseChecker's flaw types M*, S and I are noncompliance (d). U1 and U2 are its "underspecified specification" class, so they are (c) candidates. Confirm each one by reading the clause.
- Pin these exact UE versions. Newer versions may have fixed the issues.

### 0.2 Reference numbers to reproduce (5GBaseChecker Table 4)

| UE | MQ | EQ | Time (min) | States | Transitions |
|---|---|---|---|---|---|
| srsUE | 710 | 3,732 | 2,221 | 6 | 20 |
| OAI UE | 687 | 3,602 | 2,145 | 6 | 16 |

- These two were learned **after** 17 phones, reusing their counterexamples (collaborative learning). To match the table, load `CEStore/configured_CEs/CE_reverse_feeding/All_CEs`.
- From scratch costs far more. The first device (Motorola Edge+) took 25,239 EQ and 17,615 min.
- Equivalence queries dominate (about 5× membership queries for both UEs). That is exactly what Thrust 1's guided equivalence queries target.
- Their machine: Ubuntu 20.04, AMD Ryzen 9 7950X3D, 64 GB RAM.

---

## 1. What exists vs what I write

### 1.1 Reuse

| Component | Gives you | Notes |
|---|---|---|
| **5GBaseChecker** (AGPL-3.0) | **StateSynth:** modified Open5GS core, modified OAI gNB, modified srsRAN_4G gNB; StateLearner on LearnLib (TTT + Wp-method); Trace2Model; fsm_comparator. **DevScan:** extends BLEDiff's checker; `dot2smv.py`, nuXmv. **DevLyzer:** `attack_trace_checker` with **45 LTL properties**, `all_inputs.txt` (29 symbols), `all_outputs.txt` (15 symbols). Also per-device learner configs, `CEStore` with configured CEs, 2 sample FSMs, 8 sample deviations. | Ubuntu 20.04, JDK 11, maven, Python 2.7 + 3, MongoDB 4.4, NuSMV 2.6.0. `start_ue.sh` launches srsUE. AGPL: publishing a modified version means releasing it under AGPL. |
| **PSMBench** `Zilinlin/RFC_PSM_Benchmark` (Apache-2.0) | `state_machine_format.json` schema; per-section prompts plus a combination prompt (`prompt_generation.py`); `eval_fsm_sim.py` (fuzzy semantic matching of states and transitions, precision/recall/F1) | Data is RFC-only. Reuse the method and evaluator, not the data. |
| **SPEC5G** `Imtiazkarimik23/SPEC5G` | 134M-word cellular spec corpus | Check whether it contains TS 24.501, and which version. |
| **Hermes** `SyNSec-den/hermes-spec-to-fsm` (Apache-2.0) | Annotated 5G NAS data; synthesizer outputs `transitions.txt`, `ir-out.xml`, `smv-out.smv` | FSM outputs are not shipped; you must run it (CoreNLP server; tested on Ubuntu 22.04 with a GPU). Candidate reference FSM. |
| **CellularLint** `CellularLint/cellularlint-codes` (CC0-1.0) | NLI models and code for inconsistency detection | The list of 157 inconsistencies is not visible in the repo. Optional (c) confirmer. |
| **nuXmv 2.2.0** | Model checker | Linux x86_64 and macOS arm64; non-commercial/academic use only. |
| **OAI RF simulator** | `--rfsim` for gNB and `nr-uesoftmodem`, no SDR needed | Built automatically with the OAI gNB/UE; `./build_oai ... -w SIMU` rebuilds it. |
| **srsRAN_4G ≥ 22.04** | 5G SA srsUE + srsENB-based gNB over ZMQ with Open5GS (app note) | The srsENB 5G prototype is deprecated upstream, but it is what 5GBaseChecker modified. |
| **TS 24.501 v17.8.0** | `24501-h80.zip` from the 3GPP archive | The same version 5GBaseChecker built its alphabet from (with TS 38.331 v17.6.0). |

**Reference only:**
- DIKEUE: 4G, with two sample FSMs.
- Proteus: 4G LTE and BLE only.
- SpecGPT (Zhang et al., arXiv 2510.14348): 5G NAS LLM extraction with ensembles; no code found.

**Not public** (ask the authors through Dr. Karim only if needed):
- all 19 learned FSMs;
- the full 2,044 deviations;
- the 36 hand-analyzed deviations.

### 1.2 What I write (the contribution, as small modules)

```
implementation/
  symbols/   alignment table + NAS projection of learned FSMs
  extract/   clause index, constrained LLM extraction, .dot writer, confidence records
  compare/   spec-vs-device runner (wraps DevScan) + four-case classifier
  guide/     spec transitions -> potential counterexamples (CEStore input)
  repair/    re-read clause, repair or annotate, tie-break rule
  triage/    Thrust 2 agent + tool confirmers (wraps DevLyzer)
  trust/     Thrust 3 benchmark + metrics
```

---

## 2. Environment

- **Env A, reproduction (Linux laptop):** Ubuntu 20.04, the artifact's tested OS.
  - If the laptop runs 24.04 (as in `ocudu_setup/`), use a 20.04 VM or container. ZMQ and rfsim are pure software, so no USB passthrough is needed.
  - Containers need SCTP for Open5GS: load the module on the host (`modprobe sctp`) and use host networking. *(to verify)*
- **Env B, warm-up:** your `ocudu_setup/OCUDU_SETUP_PLAN.md` (OCUDU gNB + Open5GS + srsUE over ZMQ). Good for 5G SA bring-up and Wireshark.
  - **Not used for reproduction:** 5GBaseChecker's learner adapter lives inside its own modified Open5GS and gNB.
- **Mac:** LLM extraction, analysis, nuXmv (arm64 build exists).
- **Pre-flight:** `nproc`, `free -h` (16 GB minimum, 32 GB better; they used 64 GB), `df -h`.
- **Long runs:** one UE took about 37 h on their desktop. Use `resume=true` and `cache=true` in `fgue.properties`, and run inside `tmux`.

---

## 3. Thrust 1: implementation-grounded spec model

| Step | Goal | Done when | Est. |
|---|---|---|---|
| T1.0 | Warm-up: 5G SA registration with srsUE over ZMQ; capture NAS in Wireshark | pcap shows Registration Request/Accept and Security Mode Command | 1 wk |
| T1.1 | Offline reproduction: DevScan on `FSM_A.dot`/`FSM_B.dot` → `deviant-queries.json`; DevLyzer with the 45 properties | Output matches the README (8 sample traces analyzed) | 1–2 d |
| T1.2 | Learn **srsUE first** (start_ue.sh path exists), then **OAI UE** (rfsim) | FSM ≈ 6 states / 20 transitions (srsUE), ≈ 6 / 16 (OAI); DevLyzer flags the Table 8 NAS issues | 2–4 wk |
| T1.3 | Differential baseline: DevScan srsUE vs OAI UE → DevLyzer | List of issues it can see; expected to **miss I3, I4, I10, I19** | 2 d |
| T1.4 | Symbol alignment table (§3.1) + NAS projection | Every NAS symbol mapped to message, header type, clause; confirmed from adapter code | 1 wk |
| T1.5 | Spec FSM extraction (§3.2) | Spec `.dot` over the NAS alphabet; property check and audit done | 2–3 wk |
| T1.6 | Spec vs each UE + four cases (§3.3) | **Shared issues appear as Case 2: demo D3** | 1–2 wk |
| T1.7 | Guided learning + repair loop (§3.4) | Query savings and repair numbers: **first paper** | 3–4 wk |

**T1.2 risks:**
- The README doesn't document simulated-radio configs for the learner; `start_ue.sh` launches srsUE only.
- Read `modified_cellular_stack/conf/` and the learner scripts. For OAI, build `5GBaseChecker_OAI_gnb` with rfsim and write your own `nr-uesoftmodem --rfsim` launcher.
- If stuck for more than a week, ask the authors (Kai Tu, Syed Rafiul Hussain, Penn State).

### 3.1 Symbol alignment (T1.4)

The code names differ from the paper's Table 9 names; a confirmed mapping is needed first. Confirm the "likely" rows from the modified Open5GS code, where each symbol's message is built.

| Code symbol (`all_inputs.txt`) | Paper symbol (Table 9) | Status |
|---|---|---|
| enable_s1 | enable_reg (trigger registration) | likely |
| id_request_plain_text | identity_req_plain | likely |
| auth_request_plain_text | auth_req_plain | likely |
| nas_sm_cmd | nas_sm_cmd_int | likely |
| nas_sm_cmd_protected | nas_sm_cmd_header2_protected | likely |
| nas_sm_cmd_replay | nas_sm_cmd_replay | same |
| nas_sm_cmd_ns | nas_sm_cmd_NIA0_int | likely |
| nas_sm_cmd_ns_plain_text | nas_sm_cmd_NIA0_plain | likely |
| registration_accept_protected / _plain_text / _h4_plain_text | reg_accept_protected / _plain / _header4_plain | likely |
| config_update_cmd_protected / _plain_text / _replay | conf_update_cmd_protected / _plain / _replay | likely |
| deregistration_req_protected / _plain_text | dereg_req_protected / _plain | likely |

- **NAS projection:** keep the 16 NAS inputs above and 9 NAS outputs:
  - registration_request, id_response, auth_response;
  - nas_sm_complete, nas_sm_reject, registration_complete;
  - deregistration_accept, config_update_complete, null_action.
- Dropping the RRC edges from a learned FSM keeps its exact behavior on NAS-only input sequences.
- **Security header types** used in the alphabet: 0 (plain), 2 (integrity + ciphered), 3 (integrity, new context), 4 (integrity + ciphered, new context).

### 3.2 Spec FSM extraction (T1.5)

1. **Corpus:** TS 24.501 v17.8.0, split into clauses with their IDs. Use SPEC5G only if it holds this version.
2. **Clauses to retrieve** (check numbering in v17.8.0):
   - 4.4 NAS security (4.4.3.2 replay, 4.4.4 integrity checking);
   - 5.1.3 5GMM states;
   - 5.4.1 authentication (5G-AKA), 5.4.2 security mode control, 5.4.3 identification, 5.4.4 generic UE configuration update;
   - 5.5.1 registration, 5.5.2 de-registration.
3. **Prompting:** PSMBench pipeline (per-section prompts, then a combination prompt), but with a **closed vocabulary**:
   - inputs and outputs only from §3.1;
   - states = 5GMM state × NAS-security-context-active flag.
4. **Output:** a complete Mealy machine over the NAS alphabet.
   - Every (state, input) gets output + next state + `{clause_id, quoted_text, support: 0, contradiction: 0}`.
   - If the spec is silent, mark it `UNSPECIFIED` instead of guessing. These are compared separately and become (b)/(c) candidates.
5. **Ensemble:** k samples or models per (state, input); majority vote. Disagreement lowers confidence.
6. **Writer:** emit `.dot` in 5GBaseChecker's format (`s0..sN`, edge label `input / output`), so DevScan and `dot2smv.py` work unchanged.
7. **Checks:**
   - nuXmv against the NAS-relevant subset of the 45 properties;
   - PSMBench `eval_fsm_sim.py` F1 against a reference (decision R2);
   - a hand audit of about 30 transitions.

### 3.3 Spec vs device and the four cases (T1.6)

- Run DevScan on (spec, srsUE) and (spec, OAI UE). Each deviation is an input sequence plus the two output sequences.
- For each deviation, run its input on every learned UE FSM. k = number of UEs whose output matches the spec FSM. This sets support = k and contradiction = n − k.

| Case | k | Devices among themselves | Likely labels |
|---|---|---|---|
| 1 | k = n | agree with spec | none (not sent to Thrust 2) |
| 2 | k = 0 | agree with each other | (a), (d), (b) |
| 3 | 0 < k < n | split | (d), (b), (c) |
| 4 | k = 0 | disagree with each other | (c), (b) |

- Run DevLyzer on the spec-vs-device deviations with the 45 properties.
- **Done when:** I3, I4, I10, I19 appear as Case 2 and DevLyzer attributes them to the right properties. Report recall over the 9 NAS issues (13 issue–UE pairs: 6 for OAI UE, 7 for srsUE), against the T1.3 baseline.
- Expect many Case 2 hits from extraction errors at first. They feed §3.4. With n = 2, consensus is weak; that is fine for the demo, and more devices come later.

### 3.4 Guided learning and the repair loop (T1.7)

1. **Guided equivalence queries, with no learner code change.**
   - 5GBaseChecker already consumes potential counterexamples (PCEs) before the Wp-method (Algorithm 2, lines 11–16).
   - Generate PCEs from the spec FSM: for each spec transition (s, a), take the access sequence to s, append a, and order the PCEs by confidence.
   - Write them in the `CEStore` format. Copy the format from `CEStore/configured_CEs/` examples and `fsm_comparator/CEextract.py` output. *(format to verify)*
2. **Experiments per UE, cold start:**
   - (a) Wp only;
   - (b) spec PCEs + Wp;
   - (c) their `All_CEs` + Wp;
   - (d) both.
   - Measure MQ, EQ and time. Check that the final FSMs are equivalent (DevScan reports 0 deviations between runs). Budget: about 1.5 days per run, so about 12 days of compute for 4 configs × 2 UEs.
3. **Repair:**
   - Transitions with support 0 and contradiction n go back to the LLM with the quoted clause, which repairs or annotates them.
   - **Tie-break:** consensus can lower confidence but never deletes a transition; the clause, confirmed by nuXmv or replay, decides.
4. **Stop rule** (not in the proposal yet): stop when a round finds no new counterexample and changes no spec transition; at most 3 repair rounds per transition.
5. **Metrics before and after repair:**
   - number of Case 2 false positives;
   - property satisfaction;
   - F1 against the reference.

---

## 4. Thrust 2: agentic triage

| Step | What | Reuse |
|---|---|---|
| T2.1 | Discrepancy record: `{input_seq, spec_out, device_out, device, transition_id, case, k}` | output of T1.6 |
| T2.2 | Tools: `retrieve(query)` (T1.5 index); `replay(seq, device)` (offline on learned FSM, online via learner membership query); `confidence(transition_id)` | learner MQ path |
| T2.3 | Agent proposes a label plus a checkable claim. LTL in **DevLyzer syntax** (`G`, `F`, `X`, `input = sym`, `output = sym`) for (a)/(d); input sequence + repeat count for (b); clause pair for (c) | `ltl_properties.txt` as syntax examples |
| T2.4 | Confirmers: (a)/(d) DevLyzer `attack_trace_checker` (nuXmv per-trace model); (b) ≥10 online replays + spec-allowed check; (c) LLM judge or CellularLint NLI over the clause pair | DevLyzer, CellularLint |
| T2.5 | Independence: a second model re-derives each property; compare by verdict on all deviating traces and against the 45 released properties | nuXmv |
| T2.6 | Evaluation (§4.1) | |
| T2.7 | Exploit synthesis: simulation only, srsUE/OAI. A new issue is reported to the srsRAN / OAI maintainers. COTS over the air only later in a lab: shield box, programmable SIM (sysmoISIM-SJA2), approvals | |

### 4.1 Ground truth for Thrust 2

- **Property recovery:** hide the 45 properties; count how many agent properties are verdict-equivalent to an expert property on all deviating traces.
- **Issue labels:** the 9 NAS issues in §0.1 (13 issue–UE pairs), with expected labels; plus the audited (a) cases from T1.6; plus the (b) cases from replay flakiness.
- **Effort:** analyst time per deviation vs about 2 min (5GBaseChecker: 36 deviations analyzed by hand → 45 properties).
- **Proposal fix 1:** their 36 hand-analyzed deviations are **not public**. Evaluate on regenerated deviations (T1.3, T1.6) with the 45 public properties and Tables 2/8 as truth. Update the Thrust 2 metrics sentence in the .tex accordingly.
- **Proposal fix 2:** the .tex also lists DIKEUE's 17 issues as Thrust 2 ground truth. Those are 4G; with a 5G-only scope, drop them or move them to future work.

---

## 5. Thrust 3: trust in the triage agent

| Step | What |
|---|---|
| T3.1 | Freeze the benchmark: confirmed cases `{input_seq, outputs, clause_text, truth_label, confirming_tool}` |
| T3.2 | Two modes: agent with evidence tools; LLM alone with the record |
| T3.3 | Models: GPT-4o, DeepSeek-V3, Qwen3 (local, for reproducibility) |
| T3.4 | Metrics: per-label accuracy and macro-F1; verbalized confidence → ECE (10 bins) and Brier; counterfactual pairs (swap vendor/device name, Rel-16 ↔ Rel-17) → label-flip rate with 95% bootstrap CI |
| T3.5 | Size it at about 6 months (review note); the benchmark comes free from Thrust 2 |

---

## 6. Milestones

| M | Week | Deliverable |
|---|---|---|
| M0 | 1 | Env A + warm-up pcap |
| M1 | 2 | DevScan/DevLyzer sample reproduction |
| M2 | 3–6 | srsUE and OAI UE FSMs; Table 4/8 NAS rows reproduced (**D1**) |
| M3 | 6–8 | Symbol table + spec FSM v1 + property check |
| M4 | 8–10 | Differential baseline vs spec reference: **D2 + D3, the demo for Dr. Karim** |
| M5 | 10–14 | Guided learning + repair numbers (**D4**, first paper) |
| M6 | months 4–8 | Thrust 2 |
| M7 | months 8–10 | Thrust 3 |

These are estimates; T1.2 compute time is the biggest unknown.

---

## 7. False positives: sources and defenses

| Source | Symptom | Defense |
|---|---|---|
| Symbol mismatch | Almost everything deviates | §3.1 table confirmed from code before the first full run |
| LLM extraction error | Many Case 2 hits on one transition | Re-read clause, label (a), repair loop |
| Learning noise | Deviation vanishes on replay | ≥10 replays, label (b) |
| "may" behavior in spec | UEs split, both valid | Spec-allowed check, label (b) |
| Spec silent | No clause supports either side | `UNSPECIFIED` bucket, (c) candidate |

Rule of thumb: hundreds of Case 2 hits mean check the symbols before the devices.

---

## 8. Decisions for you

| ID | Decision | Options | My recommendation |
|---|---|---|---|
| R1 | NAS scope | Proposal's 4 procedures vs 5GBaseChecker's 6 (adds configuration update, de-registration) | **6**: the symbols already exist, and I9/I20 need configuration update. Update the scope sentence in the .tex. |
| R2 | Reference FSM for F1 | Hermes 5G NAS output (run synthesizer, map symbols); hand-built for SMC + registration; property-only (45) | Hand-built small reference + property check first; Hermes later |
| R3 | Laptop OS | Native 20.04 vs 20.04 VM/container on 24.04 | Whatever the laptop already runs; VM if 24.04 |
| R4 | LLM access | API (GPT-4o, DeepSeek) vs local (Qwen3) | Local for development, API for final numbers |
| R5 | Ask authors for full FSMs/deviations | Through Dr. Karim | Only if T1.2 stalls |

---

## 9. Verification log

**Checked against sources (2026-10-12):**
- [x] 5GBaseChecker tested srsUE and OAI UE over a software-simulated radio (paper §9.1). This confirms the .tex claim "exactly as 5GBaseChecker did".
- [x] Learner = StateLearner on LearnLib TTT + Wp-method (paper §8; `fgue.properties`: `ttt`, `wpmethod`). Matches the .tex.
- [x] Modified Open5GS core plus OAI and srsRAN gNBs (paper §8; repo `modified_cellular_stack`).
- [x] 45 LTL properties, 29 input and 15 output symbols, 2 sample FSMs, 8 sample deviations are public (raw repo files).
- [x] The 19 learned FSMs, 2,044 deviations and 36 analyzed deviations are not public (repo FSM folders hold only FSM_A/FSM_B).
- [x] Table 4 and Table 8 numbers for srsUE and OAI UE (paper text).
- [x] PSMBench repo, license, evaluator (fuzzy semantic matching); Hermes outputs not shipped; CellularLint repo; nuXmv license and platforms; OAI rfsim needs no SDR; srsRAN_4G ≥ 22.04 has 5G SA srsUE + ZMQ + Open5GS; `24501-h80.zip` exists.

**Still to verify (do these first, in this order):**
1. "likely" rows in §3.1 (adapter code)
2. `CEStore` counterexample file format
3. simulated-radio configs for the learner, especially OAI UE
4. TS 24.501 v17.8.0 clause numbers in §3.2
5. whether SPEC5G contains TS 24.501 v17.8.0
6. which of the 45 properties are NAS-only
7. SCTP inside a container/VM

---

## 10. Sources

- 5GBaseChecker code: https://github.com/SyNSec-den/5GBaseChecker
- 5GBaseChecker paper: https://www.usenix.org/system/files/usenixsecurity24-tu.pdf
- 5GBaseChecker artifact appendix: https://usenix.org/system/files/usenixsecurity24-appendix-tu.pdf
- DIKEUE: https://github.com/SyNSec-den/DIKEUE
- Proteus: https://github.com/SyNSec-den/Proteus
- Hermes: https://github.com/SyNSec-den/hermes-spec-to-fsm
- PSMBench: https://github.com/Zilinlin/RFC_PSM_Benchmark
- SPEC5G: https://github.com/Imtiazkarimik23/SPEC5G
- CellularLint: https://github.com/CellularLint/cellularlint-codes
- SpecGPT paper: https://arxiv.org/abs/2510.14348
- nuXmv: https://nuxmv.fbk.eu/download.html
- OAI RF simulator: https://github.com/OPENAIRINTERFACE/openairinterface5g/blob/develop/radio/rfsimulator/README.md
- srsRAN 4G 5G SA end-to-end (ZMQ + Open5GS): https://docs.srsran.com/projects/4g/en/next/app_notes/source/5g_sa_E2E/source/index.html
- TS 24.501 archive: https://www.3gpp.org/ftp/Specs/archive/24_series/24.501/
