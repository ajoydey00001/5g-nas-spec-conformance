# Thrust 1 progress log

Workspace for runs: `~/thrust1-lab/` (5GBaseChecker clone `642443b7`, logs in `~/thrust1-lab/logs/`).
Container for offline tools: `implementation/env/Dockerfile.offline` → image `t1-offline`
(Ubuntu 20.04, Python 2.7.18 + 3.8, pydot, graphviz, NuSMV 2.6.0).

## T1.0 Warm-up — DONE (2026-10-13)
- Done on the OCUDU testbed (OCUDU gNB + Open5GS v2.7.6 + srsUE over ZMQ), not the 5GBaseChecker stack.
- `~/ocudu-lab/report/runtime/ue_nas.pcap` (11 NAS PDUs): Registration Request (0x41), Authentication
  Request/Response (0x56/0x57), Security Mode Command/Complete (0x5d/0x5e), Registration Accept/Complete
  (0x42/0x43), UL/DL NAS Transport (0x67/0x68), Configuration Update Command/Complete (0x54/0x55).
- Security header types seen: 0 (plain), 3 (SMC), 4 (SMC complete), 2 (all later messages).
- Lesson: Open5GS AMF with 3 TACs breaks srsUE (TAI list length 19 ≠ 7). Use a single TAC.

## T1.1 Offline reproduction — DONE (2026-10-13)
- DevScan (`Autorun.py` + `AutoAnalysis.py`) on FSM_A/FSM_B: 5 s, **8 deviant traces, identical set to the
  shipped `DevLyzer/deviant-queries.json`**.
- DevLyzer (`main.py`, 45 properties): **8/8 analyzed, 0 unresolved** (8 attack, 0 benign), 2 s
  (README says ~20 min on their machine).
- `ViolatingPropertiesIdx` is 1-based (trace 1: FSM_B answers nas_sm_cmd_ns_plain_text with nas_sm_complete
  → props 12, 13; nas_sm_cmd_ns with nas_sm_reject → 11).

## Verification items (PLAN.md §9)
- [x] 6. NAS-only properties: **21 of 45** mention no RRC symbol: 1–15, 29–32, 43, 44.
  Props 26, 27, 33, 34 mix NAS and RRC conditions.
- [x] 1. Symbol table: all 16 NAS symbols confirmed from the modified core → `symbols/alignment.md`
  (incl. core-side preconditions that turn symbols into `null_action`; important for T1.5).
- [x] 2. CEStore format: one counterexample per line, `INFO: [in1 in2 ... / out1 out2 ...]`;
  `CE_reverse_feeding/All_CEs` has 29 lines. Learner reads the **file** `./CEStore/input`.
- [ ] 3. simulated-radio configs: srs gNB `enb.conf` uses `device_name = uhd`; a ZMQ `device_args` line is
  present but commented out → switch to zmq for T1.2.
- [x] 4. TS 24.501 v17.8.0 clause numbers: all 11 in PLAN.md §3.2 exist with the expected titles
  (4.4, 4.4.3.2 Replay protection, 4.4.4, 5.1.3, 5.4.1–5.4.4, 5.5.1, 5.5.2). Corpus:
  `~/thrust1-lab/spec/ts24501_v17.8.0_clauses.jsonl` (1,181 clauses) from `extract/spec_clauses.py`.
  Download needs a browser User-Agent (3GPP returns 403 to curl's default).
  Size of the 8 clause trees: ~132k words (~185k tokens); 5.5.1 registration alone is 72k words → T1.5 must
  retrieve per subclause, not prompt with whole procedures.
- [x] 5. SPEC5G (repo moved to `SysNetS/SPEC5G`): the corpus is a Google Drive zip (`Gold_5G_v4.0.zip`,
  134M words, sentence-level, crawled for the AACL 2023 paper). The GitHub repo has only code. It is a
  sentence corpus without clause IDs, so it cannot give the `{clause_id, quoted_text}` records T1.5 needs.
  **Decision: use the official 3GPP v17.8.0 clause corpus above; SPEC5G stays optional** (e.g. as a
  retrieval-quality comparison). Proposal wording updated 2026-10-13 (Thrust 1 step 1 and Thrust 2 step 1).
  Mapping SPEC5G → clause IDs is feasible: SPEC5G crawled the 3GPP `ftp/Specs/2022-09` snapshot with
  `textract`; TS 24.501 v17.8.0 was released 2022-09-23 (v17.7.0 2022-06-24, v17.9.0 2023-01-06), so the snapshot
  very likely holds v17.8.0 = our version. Map each sentence by normalized text match against
  `ts24501_v17.8.0_clauses.jsonl` (fuzzy fallback). Needs `Gold_5G_v4.0.zip` from their Google Drive. Old note: Update the proposal wording "Retrieve ... from the SPEC5G corpus" if needed.
- [ ] 7 open (SCTP in container works: core↔gNB NGAP over SCTP runs inside `t1-learn` — effectively done).

## Notes
- Laptop has 11 GB RAM; PLAN.md §2 asks for 16 GB minimum. Build/run with limits (see memory notes).

## T1.2 Learn srsUE — STACK WORKING, full run not started
- Image `t1-enva` (`env/Dockerfile.envA`): Ubuntu 20.04, OpenJDK 11.0.27, MongoDB 4.4.31, meson 0.53, gcc 9.4.
- Versions: modified core = Open5GS 2.4.9 (single TAC 1, so no TAI-list problem); modified gNB = srsRAN
  22.04.1; srsUE = srsRAN_4G `release_22_10` (`254cc71`), cloned to `~/thrust1-lab/srsRAN_4G_22_10`.
- Build: `env/build_stack.sh` (core → srs gNB → srsUE, -j3, container capped at 6 GB / 5 CPUs).
- Learner wiring: `fgue.properties` device name selects the driver (`srsue` → `srsueSUL`, `oaiue` → `oaiueSUL`);
  learner restarts components via `start_core.sh`, `start_srs_gnb.sh`, `start_ue.sh` with `sudo -S` and the
  `password` property; scripts hard-code `/home/kai/...` paths → must be rewritten for `/work`.
- Builds OK in ~10 min total (core 2 min, gNB 4 min, srsUE 4 min). Binaries:
  `5GBaseChecker_Core/build/tests/app/5gc`, `5GBaseChecker_srs_gnb/build/srsenb/src/srsenb`,
  `srsRAN_4G_22_10/build/srsue/src/srsue`.
- Run folder `~/thrust1-lab/learnrun` (copies of scripts/configs in `implementation/env/`). Container:
  `docker run -d --init --name t1-learn --privileged --memory=6g --memory-swap=7g --cpus=5 -v ~/thrust1-lab:/work -w /work/learnrun t1-enva sleep infinity`
  then `./container_init.sh` (MongoDB + subscriber), then `./start_learner.sh`.
- Learner config: `learner_config/Sequential_learning/srsue.properties` (cold start). Note: upstream
  `CE_reverse_feeding/srsue.properties` says `device = oai` (copy-paste slip).
- Problems fixed while bringing it up:
  1. Jar has no Main-Class → run `org.example.uelearner.Learner` with `-cp`.
  2. Kill scripts must also kill the `open5gs-*d` daemons, not just `5gc`.
  3. Container needs `--init`, otherwise killed processes stay as zombies.
  4. Run folder name must not contain `srsue`/`srsenb`/`5gc`/`open5gs`: the scripts use `pkill -f` and
     killed the core and gNB through their config paths (`run_srsue` → renamed `learnrun`).
  5. gNB learner socket (60001) has no SO_REUSEADDR: the client must close first or the port is blocked
     ~60 s (TIME_WAIT). The learner already does this; the probe now does too.
  6. srsUE 22.10 looked for the SSB at 1842.05 MHz; the gNB sends it at SSB-ARFCN 368650 (1843.25 MHz) →
     `ssb_nr_arfcn = 368650` in `ue.conf`.
  7. **Ciphering:** with the ReadMe AMF block (`ciphering_order [NEA2, NEA1, NEA2]`) srsUE passes the
     integrity check but fails to decode every ciphered NAS message ("Unsupported extended protocol
     discriminator"). With NEA0 first, everything decodes. Using **NEA0 for srsUE** (`conf/sample.yaml`;
     the NEA2 variant is kept as `conf/sample.nea2.yaml`). Open question: srsUE NEA2 bug or core bug.
- Probe (NEA0): enable_s1→registration_request, auth_request_plain_text→auth_response,
  nas_sm_cmd→nas_sm_complete, registration_accept_protected→registration_complete,
  config_update_cmd_protected→config_update_complete, **nas_sm_cmd_replay→nas_sm_complete (I7)**,
  **id_request_plain_text→id_response after security (I3)**. Both match srsUE's row in Table 8.
- Learner sanity run (cold start, 31-symbol alphabet): works end to end; ~45 s per symbol query
  (3 repetitions for majority vote, full core/gNB/UE restart per query). Paper: ~30 s/query.
- **Table 4 reproduction run started 2026-10-13 ~01:35** (user's choice): `CE_reverse_feeding/srsue.properties`
  (with `device = srsue`), `CEStore/input` = `All_CEs` (29 CEs, "All CE loaded!"), 31-symbol alphabet, NEA0.
  Wrapped in `systemd-inhibit` (no suspend, lid switch ignored) for the run's duration.
  Sanity cold-start logs moved to `learnrun/logs/sanity_coldstart/`.
- Finding: in CE-feeding mode the shipped learner exits after **30 equivalence queries**
  (`LogOracle.java`: `CE_revserse_feeding == 1 && count >= 30`), cold start after `EQCount` (2000).
  So this run can reproduce Table 4's states/transitions, not its MQ/EQ/time columns (710 / 3,732 / 2,221 min).

## Analysis tool — `symbols/fsm_tools.py` (2026-10-13)
- `stats` (paper metric: states, non-self-loop transitions), `nas` (NAS-only projection + minimization),
  `issues` (direct probes of Table 8 NAS issues), `ltl` (NuSMV check of DevLyzer-syntax properties).
- Sample FSMs: FSM_A = 6 states / 16 transitions (NAS projection 5 / 11); FSM_B = 6 / 20 (NAS 6 / 20).
  FSM_A probes: I3, I4, I6, I7, I10, I17, I19 present.
- Probes I9b and I20 need `registration_accept_protected` to succeed first; on a UE that ignores it (I17),
  read them as "not reached", not "absent".

## SPEC5G → clause mapping (2026-10-13) — `extract/spec5g_map.py`
- `Gold_5G_v4.0.zip` = one 800 MB file, 3,541,952 lines, one cleaned sentence per line; documents start with a
  "3GPP specification document V..." line (version digits masked, e.g. "V1 (2026)").
- TS 24.501 = lines 2,926,568–2,930,303 (title line 2,926,569), only **3,736 lines** → `~/thrust1-lab/spec/spec5g_ts24501.txt`.
- Mapping to v17.8.0 clauses (`spec5g_ts24501_map.jsonl`): exact 62%, 5-gram 11%, unmatched 13%, too short 14%.
  The high exact rate means SPEC5G's copy is v17.8.0 or very close.
- But the content is not the procedures: ~1,957 matched lines (52%) fall in the last clause D.8, i.e. the
  change-history table at the end of the spec, and 273 in 9.11 (IE definitions). Lines in the 8 clause trees
  Thrust 1 needs: 4.4: 7, 5.1.3: 2, 5.4.1: 10, 5.4.2: 4, 5.4.3: 0, 5.4.4: 8, 5.5.1: 74, 5.5.2: 4 (≈109 lines
  against ~132k words of spec text).
- **Conclusion: SPEC5G cannot serve as the Thrust 1 retrieval corpus** (it covers well under 1% of the needed
  procedure text); the 3GPP clause index stays the primary source. Mapping is still useful to cite SPEC5G
  sentences by clause ID.

## T1.5 preparation (2026-10-13)
- PSMBench cloned to `~/thrust1-lab/psmbench` (`df0bce6`): schema `state_machine_format.json`
  ({states, initial_state, final_states, transitions[{from, event, action, to}]}), prompts in
  `prompt_generation.py` (per-section + combination), evaluator `eval_fsm_sim.py` (all-MiniLM-L6-v2 embeddings,
  cosine threshold 0.5 on states and on from/to/event+action).
- `extract/psm2dot.py`: PSMBench JSON with closed NAS vocabulary (`recv <input>` / `send <output>`, plus our
  `clause_id`, `quoted_text`, `support`, `contradiction`) → complete 5GBaseChecker `.dot`; missing
  (state, input) pairs become `UNSPECIFIED` self-loops; rejects non-determinism. Tested on a toy 3-state spec.
- Still needed before T1.5 runs: decision R4 (which LLM) and the prompt adaptation (closed vocabulary,
  states = 5GMM state × security flag, core/learner preconditions from `symbols/alignment.md`).

## T1.5 spec FSM v1 — DONE (2026-10-13)
- No Claude API key → user chose "Claude in this session" as extractor (1 sample/cell, no ensemble).
- `extract/author_spec_cells.py` → `spec_fsm/spec_cells_v1.json`: 6 states × 16 NAS inputs, each cell with
  output, also_allowed, next, kind (SPEC/INFERRED/UNDERSPECIFIED/NO_CONNECTION), clause ID, verbatim quote.
- `extract/build_spec_fsm.py`: quote check (89/89 verbatim), PSMBench JSON (`spec_v1.psm.json`), spec ⊗ harness
  `.dot` + allowed sidecar. Repairs R1, R2 in `spec_fsm/REPAIRS.md`.
- `symbols/fsm_tools.py ltl` now uses single-session semantics (enable_s1 only first), matching DevLyzer traces.

## T1.6 spec vs devices — v1 on FSM_A/FSM_B DONE; srsUE pending
- `compare/spec_vs_devices.py`: first-point deviations, uncertain-harness model, four cases, visible_to_diff,
  (c)-candidate observations in UNDERSPECIFIED cells.
- Results in `results/T1_RESULTS_v1.md` and `results/T1.6_spec_vs_AB.json`: 6 Case 2 classes invisible to
  differential testing (I3, I4, I6, I10 ×3); I19/I20 as (c) candidates; all 23 classes confirmed by the
  authors' DevLyzer (`~/thrust1-lab/devlyzer_ours`).

## T1.2 srsUE Table 4 run — incidents (2026-10-13)
- 15:23–17:01: power cut. On battery, GNOME suspended the laptop after 15 min idle (despite the systemd-inhibit
  block). The learner froze and continued after wake; no queries lost.
- 17:19–18:20: stall. Container `/dev/shm` (64 MB Docker default) filled with `mongoc-<pid>` files, one leaked
  by every core run (8,490 files). After that the core crashed silently on start, and the learner retried
  ~300 times ("Connection refused"). Fix: removed the files of dead processes; `start_core.sh` now runs
  `rm -f /dev/shm/mongoc-*` after killing the old core. For a new container, `--shm-size=256m` also helps.
- Checkpointing: `my_database.sqlite` (resume_learning) + `checkpoint.sh` (30-min snapshot to GitHub) +
  `resume_after_reboot.sh`.

## T1.2 finalized demonstration — 2026-10-14

Preserved hypothesis 5 (SHA-256 recorded in results/srsue_model_provenance.json):
6 states, 21 non-self-loop transitions versus paper 6/20. Table 8 probes recover
7/7 expected NAS issues and additionally I6. Three-device comparison yields
23 classes (6 invisible Case 2, 8 visible Case 2, 9 visible Case 3).
The learner stops at LogOracle's 30-equivalence-call System.exit(0), before
the normal final writer. Repeated cached resumes do not establish convergence.
Auto-resume was paused; archived model copies have identical hashes.
Independent extraction validation and guided-learning D4 experiments remain future work.
