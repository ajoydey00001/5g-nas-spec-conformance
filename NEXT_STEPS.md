# Next steps: finish Thrust 1, then Thrust 2, then Thrust 3

> **Finalized 2026-10-14:** the demonstration uses preserved srsUE hypothesis 5
> (6 states / 21 transitions, Table 8 recall 7/7). The learner reached its
> 30-equivalence-call budget; convergence is not established. Auto-resume is paused.
> Do not resume this completed budget run. See `thrust1/results/T1_RESULTS_v2.md`.
> `bash check_thrust1.sh` now checks local reproducibility and provenance;
> independent validation and guided-learning D4 experiments remain future work.
> Older live-run estimates and restart advice below are historical.

Written 2026-10-13 23:00. Every step is a command you can paste. Problems while the run is going: `RUNBOOK.md`.
Background and design: `thrust1/PLAN.md` (§4 is Thrust 2, §5 is Thrust 3).

Without Claude, use a free LLM (ChatGPT free, Gemini, DeepSeek, or Qwen3 locally) to help write text.
Paste it the files named in each step, plus `REVIEW.md` if it needs context.

---

## Current completion verdict

The finalized demonstration is complete; the original research plan is not.
Run `bash reproduce.sh` followed by `bash check_thrust1.sh` for artifact checks.
See `thrust1/results/T1_AUDIT.md` for semantic validation, convergence, OAI
coverage, and D4 experiments still needed. The Part A workflow below records
the historical finalization procedure, already performed for hypothesis 5.

## If the run crashes or hangs while you are away (automatic)

`auto_resume.sh` runs from cron every 15 minutes and after every boot (installed 2026-10-13). It restarts the
run from the checkpoint database when either of these happens:
- the learner is not running and there is no `learnedModel.dot` (crash, power cut, reboot);
- no query has finished for 90 minutes (stall, like the /dev/shm one).

Restarting means:
- answers already saved are replayed from `my_database.sqlite` ("Found in previous log");
- nothing is lost except the query that was running.

It stops after 6 automatic restarts, so a real fault does not loop forever.
```bash
cat ~/thrust1-lab/learnrun/logs/auto_resume.log             # what it did (empty = never needed)
touch ~/thrust1-lab/learnrun/AUTO_RESUME_OFF                 # pause it (do this before stopping the learner yourself)
rm ~/thrust1-lab/learnrun/AUTO_RESUME_OFF                    # enable again
crontab -r                                                   # remove it completely (after Thrust 1)
```
- **Manual recovery,** same thing by hand: `bash ~/thrust1-lab/learnrun/resume_after_reboot.sh`.
- **The local database is lost or damaged:** the resume script copies the GitHub checkpoint
  (`thrust1/lab/srsue_checkpoint/my_database.sqlite`, saved every 30 min) back first. Do `git pull` before that.
- `finish_thrust1.sh` turns auto-resume off by itself, because it stops the stack.

---

## Part A: finish Thrust 1 (about 1 day)

### A1. Check the run (any time)
```bash
bash ~/thrust1-lab/learnrun/status.sh
```
- `learner RUNNING` and `queries` or `check queries` growing: fine, wait.
- `hypotheses` shows `learnedModel.dot`, or `learner NOT RUNNING` with an `EXIT=` line under `run times`: it is finished. Go to A2.
- Laptop was off or rebooted: `bash ~/thrust1-lab/learnrun/resume_after_reboot.sh`
- Nothing new for an hour: `RUNBOOK.md` §2 (P3 /dev/shm, P4 timeouts, P5 learner exited).

Expected: finished on 2026-10-14. If it is not finished by **2026-10-16**, stop it and use the last hypothesis.
That is allowed; the report then says "last hypothesis after N rounds":
```bash
touch ~/thrust1-lab/learnrun/AUTO_RESUME_OFF; docker exec t1-learn pkill -f uelearner.Learner     # then A2
```

### A2. Run the whole analysis (one command, about 2 minutes)
```bash
cd ~/5g-nas-spec-conformance && git pull
bash finish_thrust1.sh
```
It stops the 5G stack and copies the model. It then prints Table 4 (size), Table 8 (recall), spec vs devices with
srsUE as the third device, and DevLyzer counts. Results go in `thrust1/results/srsue_*` and
`T1.6_*_ABsrs.*`.

**Interim result already in the repo** (hypothesis 4, files ending in `_dry`, tested 2026-10-13 22:58):
5 states and 17 transitions (paper: 6 and 20); Table 8 recall **7/7**; I6 also present (Table 8 lists it only for OAI UE);
23 classes, **6 Case 2 invisible to differential testing**; DevLyzer 23 attack, 0 unresolved.
If the final run fails completely, this is your srsUE result. Say that it comes from hypothesis 4.

### A3. Write the numbers down
Copy the printed numbers into this table (you will use it twice):

| | Paper (Table 4/8) | Ours |
|---|---|---|
| srsUE states / transitions | 6 / 20 | ? / ? |
| Table 8 issues present (I3 I4 I7 I9 I10 I19 I20) | 7 | ?/7 |
| I6 (OAI-only in Table 8) | no | ? |
| Deviation classes (A, B, srsUE) | – | ? |
| Case 2 invisible to differential testing | – | ? |
| DevLyzer attack / benign / unresolved | – | ? / ? / ? |

### A4. Results v2 and the report
```bash
cd ~/5g-nas-spec-conformance/thrust1
cp results/T1_RESULTS_v1.md results/T1_RESULTS_v2.md
```
- **`results/T1_RESULTS_v2.md`:** add the A3 table and an "srsUE" paragraph. Remove "srsUE pending" from Limitations.
- **`report/thrust1_report.tex`:** make the edits listed in `RUNBOOK.md` §3.6, item 2 (lines 51, 70–72, 135, 380, 402, 407, 416–417).
  Add the A3 table. Upload to Overleaf and compile.
- LLM help prompt: *"Here is my Thrust 1 report (LaTeX) and the new srsUE results (paste A3 table and
  `results/T1.6_summary_ABsrs.txt`). Update only the places that say srsUE is pending; keep everything else."*
- **`T1_PROGRESS.md`:** add a dated line "T1.2 srsUE done: …".

### A5. Push and stop
```bash
cd ~/5g-nas-spec-conformance
git add -A && git commit -m "Thrust 1 complete: srsUE learned, results v2" && git push
docker rm t1-learn            # optional, after the push; the images stay
```

### A6. Show Dr. Karim
- The repo link and `thrust1/report/thrust1_report.pdf`.
- **The novelty claim:** differential testing only finds behaviour where devices *disagree*. Here all
  devices agree, but they all break the spec, so differential testing cannot see it. We found ? such classes
  (6 on hypothesis 4), and each one has a verbatim TS 24.501 quote.
- Optional: send it to your friend for the Fable review (`REVIEW.md`), then fix what it finds.

---

## Part B: Thrust 2, agentic triage (months 4–8 in PLAN.md)

Goal: an LLM agent labels each deviation **a/b/c/d**:
- (a) extraction error;
- (b) benign or learning noise;
- (c) spec ambiguity;
- (d) exploitable.

Each label comes with a claim that a tool checks. The starter code is ready: `thrust2/triage.py`.

### B1. Free local LLM (once)
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b            # ~5 GB; on 11 GB RAM close the browser while it runs (qwen3:4b if it is too slow)
ollama run qwen3:8b "say ok"    # test
```

### B2. First triage run on the Thrust 1 classes
```bash
cd ~/5g-nas-spec-conformance
[ -f repro/clauses.jsonl ] || bash reproduce.sh          # makes the TS 24.501 clause index
R=thrust1/results/T1.6_spec_vs_ABsrs.json                # or ..._dry.json / T1.6_spec_vs_AB.json
mkdir -p thrust2/runs
python3 -I thrust2/triage.py $R repro/clauses.jsonl thrust2/runs/qwen3_agent.jsonl \
  --model ollama:qwen3:8b --mode agent \
  --fsm A=repro/dl/FSM_A.dot --fsm B=repro/dl/FSM_B.dot --fsm srsue=thrust1/results/srsue_learnedModel.dot
```
- Each output line has the label, the confidence, the claim (an LTL property for a/d), and the tool calls it made.
- Test without any LLM: add `--model dummy`.
- If it stops, run it again; it skips classes that are already done.
- Second model (free tier, OpenAI-compatible), for the independence check T2.5:
  ```bash
  export LLM_BASE_URL=https://api.deepseek.com LLM_API_KEY=...        # or Gemini:
  # export LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai LLM_API_KEY=...
  python3 -I thrust2/triage.py $R repro/clauses.jsonl thrust2/runs/deepseek_agent.jsonl --model openai:deepseek-chat --mode agent ...
  ```

### B3. Check the agent's claims (the confirmers, T2.4)
- **(a) or (d) with an LTL claim:** add the property to DevLyzer's property list. Then run DevLyzer as in
  `finish_thrust1.sh` step 5. A violation confirms the label.
  The 45 expert properties are in `~/thrust1-lab/5GBaseChecker/DevLyzer/attack_trace_checker/`.
- **(b):** replay the input sequence 10 times on the live srsUE stack (RUNBOOK P7 starts the container).
  Use the membership-query path, or `thrust1/env/probe.py`. If the output changes between runs, it is (b).
- **(c):** compare the two clauses by hand. Print them with `python3 -I thrust1/extract/dump_clauses.py repro/clauses.jsonl 5.5.1.2.4 5.5.1.3.4`.

### B4. Evaluate (PLAN.md §4.1)
- **Property recovery:** how many of the 45 expert properties have an agent property that gives the same verdict
  on every deviating trace. Target: 70% or more.
- Precision and recall per label against the truth labels (B5, built together with Thrust 3).
- Minutes per deviation (the `seconds` field) against 5GBaseChecker's ~2 minutes per deviation by hand.

### B5. Truth labels
Fill in `thrust3/truth_template.json`: one a/b/c/d per class, and only for confirmed ones. Save it as `thrust3/truth.json`.
Seeds from PLAN.md §4.2:
- (d): the I3, I4, I6 and I10 classes;
- (c): the I19 and I20 classes, and the gap between 5.5.1.2.4 and 5.5.1.3.4;
- (a): repairs R1 and R2 in `spec_fsm/REPAIRS.md`.

### B6. More devices (optional, makes the paper stronger)
OAI UE learning, which was skipped in Thrust 1: same 5GBaseChecker setup; in `fgue.properties` change `device`, `db_table_name` and `output_dir` (now `srsue`), and use OAI's start scripts.
Expect several days of compute.

---

## Part C: Thrust 3, trust in the triage agent (months 8–10)

Question: do the evidence tools reduce wrong labels, overconfidence and bias, compared with an LLM alone?

### C1. Benchmark
`thrust3/truth.json` from B5. The classes come from Thrust 1 and the confirmed cases from Thrust 2.

### C2. Runs: 2 modes × several models
```bash
R=thrust1/results/T1.6_spec_vs_ABsrs.json; C=repro/clauses.jsonl; F="--fsm srsue=thrust1/results/srsue_learnedModel.dot"
for mode in agent alone; do
  python3 -I thrust2/triage.py $R $C thrust3/runs/qwen3_$mode.jsonl --model ollama:qwen3:8b --mode $mode $F
done
```
Repeat the loop with `--model openai:deepseek-chat` and any other model you can access.

### C3. Bias probes (counterfactual pairs, PLAN.md §5.2)
```bash
python3 -I thrust2/triage.py $R $C thrust3/runs/qwen3_alone_devOAI.jsonl  --model ollama:qwen3:8b --mode alone --swap device=OAI-UE
python3 -I thrust2/triage.py $R $C thrust3/runs/qwen3_alone_devVendor.jsonl --model ollama:qwen3:8b --mode alone --swap device=Samsung-Galaxy-S21
python3 -I thrust2/triage.py $R $C thrust3/runs/qwen3_alone_rel16.jsonl   --model ollama:qwen3:8b --mode alone --swap release=Rel-16
```
Run the same with `--mode agent`. The truth does not change under a swap, so every label change is a flip.

### C4. Score
```bash
python3 -I thrust3/score.py thrust3/truth.json thrust3/runs/qwen3_alone.jsonl \
  thrust3/runs/qwen3_alone_devOAI.jsonl thrust3/runs/qwen3_alone_devVendor.jsonl thrust3/runs/qwen3_alone_rel16.jsonl
python3 -I thrust3/score.py thrust3/truth.json thrust3/runs/qwen3_agent.jsonl ...
```
It prints accuracy, per-label F1, macro-F1, ECE (10 bins), Brier, and flip rate with a 95% bootstrap CI.
The main table compares the agent row with the alone row for each model.

### C5. Push after every session
```bash
cd ~/5g-nas-spec-conformance && git add -A && git commit -m "thrust2/3: <what you did>" && git push
```

---

## Files added for this

| File | What |
|---|---|
| `check_thrust1.sh` | PASS/FAIL check of all of Thrust 1 |
| `thrust1/lab/learnrun/auto_resume.sh` | Cron job: restarts a crashed or stalled run from the checkpoint |
| `finish_thrust1.sh` | Part A2. Tested with `--dry` on hypothesis 4. |
| `thrust1/results/*_dry.*`, `thrust1/lab/devlyzer_srs_dry/` | Interim srsUE result (hypothesis 4) |
| `thrust2/triage.py` | Part B/C: agent or alone, with Ollama, any OpenAI-compatible API, or a dummy model. Tools: retrieve, confidence, replay. Resumable. |
| `thrust3/score.py` | Part C4 metrics |
| `thrust3/truth_template.json` | The 23 class IDs, waiting for labels |

Tested 2026-10-13 with `--model dummy` only (no LLM was installed). The first real run may need prompt tuning:
check that the model's last line is the JSON object.
