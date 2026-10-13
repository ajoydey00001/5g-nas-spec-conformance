# Runbook: keep the srsUE run alive, fix known problems, finish Thrust 1 without help

Written 2026-10-13 so that every step can be done by hand, without Claude. Commands are for the
laptop (Ubuntu, user `ajoy-dey`).

## 0. Where things are

| Path | What |
|---|---|
| `~/thrust1-lab/` | Lab: 5GBaseChecker source and builds, the learning run, spec files, DevLyzer copy |
| `~/thrust1-lab/learnrun/` | The live learning run: scripts, `fgue.properties`, **`my_database.sqlite` (checkpoint)** |
| `~/thrust1-lab/learnrun/logs/srsue.log/` | Learner output: `hypothesis_N.dot`, finally **`learnedModel.dot`** |
| `~/thrust1-lab/learnrun/logs/learner_console.log` | Everything the learner prints (errors are here) |
| `~/thrust1-lab/learnrun/logs/run_table4_time.txt` | Start / resume / `EXIT=` lines |
| `~/5g-nas-spec-conformance/` | This git repo (GitHub). **Work here from now on.** |
| `~/Downloads/imtiaz/imtiaz/implementation/` | Original working copy (same code as `thrust1/` here) |

Docker: container **`t1-learn`** (image `t1-enva`: core, gNB, srsUE, learner) and image **`t1-offline`**
(Python 2.7 + NuSMV, used for DevLyzer).

## 1. Is everything OK? (run this first, any time)

```bash
bash ~/thrust1-lab/learnrun/status.sh
```

Healthy looks like this:
- `charger plugged in`
- `learner RUNNING`
- `queries` growing by about 1 every 2 minutes. The last-finished time is in UTC, so add 6 h.
- `/dev/shm` well below 100%
- `sleep blocker 1 active`
- `github backup running`

If the query count hasn't grown for **more than 20 minutes**, something is wrong. Go to section 2.

## 2. Known problems: symptom → cause → fix

### P1. Laptop was switched off, rebooted, or the battery died
**Symptom:** after power-on, `status.sh` says `learner NOT RUNNING`.
**Fix:**
```bash
bash ~/thrust1-lab/learnrun/resume_after_reboot.sh
```
The script restarts the container, MongoDB and the subscriber, cleans up leftovers, restores the checkpoint
from GitHub if the laptop copy is missing, and restarts the learner and the GitHub backup. Saved queries are
replayed from `my_database.sqlite` in seconds (the console prints `Found in previous log`), and the run
continues live from there. Details: `thrust1/lab/srsue_checkpoint/RESUME.md`.
**Never delete `~/thrust1-lab/learnrun/my_database.sqlite`.**

### P2. Power cut, laptop went to sleep (happened 2026-10-13 15:37)
**Symptom:** a gap in progress. `journalctl --since today | grep "suspend now"` shows a suspend.
**Cause:** on battery, Ubuntu suspends after 15 min idle, even with the sleep blocker.
**Fix:** nothing to do. The run continues when the laptop wakes. To keep learning on battery instead:
```bash
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
```
(To undo it: `gsettings reset org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type`.)

### P3. Learner stuck in "Connection refused", core won't start (happened 2026-10-13 17:19)
**Symptom:** queries stop. The console repeats `Connecting to core..` and
`java.net.ConnectException: Connection refused`. `status.sh` shows `/dev/shm 100% used` or `core running 0`.
**Cause:** every core start leaves a `/dev/shm/mongoc-<pid>` file. The container has only 64 MB there.
When it is full, the core crashes silently on start.
**Fix** (already built into `start_core.sh` since 18:20 that day; do this by hand only if it shows up
again):
```bash
docker exec t1-learn bash -c 'rm -f /dev/shm/mongoc-*; df -h /dev/shm'
```
The learner reconnects by itself within about a minute.
**Other reasons the core might not start:**
```bash
docker exec t1-learn bash -c 'cd /work/5GBaseChecker/StateSynth/modified_cellular_stack/5GBaseChecker_Core && timeout 6 ./build/tests/app/5gc -c /work/learnrun/conf/sample.yaml 2>&1 | tail -20'
docker exec t1-learn pgrep -a mongod || docker exec t1-learn /work/learnrun/container_init.sh   # MongoDB died
```

### P4. One query takes much longer than 2 minutes, with "Timeout occured for ..." in the console
**Normal.** Many inputs get no answer from the UE, and the learner waits for a timeout, then records
`null_action`. A `java.lang.NullPointerException` followed by `Retrying...` after a `registration_accept_*`
sent before authentication is also normal: the core crashes on that input, and the learner restarts it.
It's only a problem if the query count doesn't move for 20+ minutes (then see P3).

### P5. Learner exited
**Symptom:** `learner NOT RUNNING`, and `run_table4_time.txt` has an `EXIT=` line.
- If `logs/srsue.log/learnedModel.dot` exists, **learning finished.** Go to section 3.
- Otherwise it crashed. Look at the end of the console:
  ```bash
  grep -av '^\s*at ' ~/thrust1-lab/learnrun/logs/learner_console.log | tail -40
  ```
  Fix the cause if it's one of P3/P7/P8, then run `resume_after_reboot.sh` (P1).

### P6. GitHub backup didn't push (no internet, power cut)
The commit stays local and goes up with the next successful push. To push by hand:
```bash
cd ~/5g-nas-spec-conformance && git push
```
If git says `rejected (fetch first)`, run: `git pull --rebase origin main && git push`.

### P7. Container or image missing
- Container gone (`docker ps -a` doesn't list `t1-learn`): `resume_after_reboot.sh` recreates it from
  image `t1-enva`.
- Image gone (`docker images` doesn't list `t1-enva`): rebuild with `thrust1/env/Dockerfile.envA`,
  then `thrust1/env/build_stack.sh` inside the container. That takes several hours. **Build with limits,
  or the laptop freezes:**
  `systemd-run --user --scope -p MemoryMax=6G -p CPUQuota=500% nice -n 19 make -j3`.

### P8. srsUE problems found during setup (already fixed in the configs; listed in case you rebuild)
| Symptom | Fix (file) |
|---|---|
| srsUE never finds the cell | `ssb_nr_arfcn = 368650` in `conf/ue.conf` |
| srsUE can't decode Registration Accept ("TAI list Length") | only one TAC in the core config |
| srsUE can't decode ciphered NAS | `ciphering_order` with NEA0 first in `conf/sample.yaml` (NEA2 copy: `sample.nea2.yaml`) |
| learner talks to the wrong device | `device = srsue` in `fgue.properties` (the shipped CE_reverse_feeding file says `oai`) |
| gNB "address already in use" on port 60001 | close the learner's client socket first (already handled by the kill scripts) |
| zombie processes pile up | container started with `--init` |
| `pkill -f srsue` kills your own shell | never put the pattern you kill in the same command line or directory name |

### P9. Laptop freezes / white screen
**Cause:** out of memory (11 GB laptop). **Fix:** don't build or run other heavy jobs while the learner
runs. The container is capped at 6 GB of memory and 5 CPUs.

## 3. When learning has finished: analysis, step by step

### 3.1 Confirm the end and stop the stack
```bash
cat ~/thrust1-lab/learnrun/logs/run_table4_time.txt             # has an EXIT= line
ls ~/thrust1-lab/learnrun/logs/srsue.log/                        # learnedModel.dot (or take the last hypothesis_N.dot)
grep -a "Learning complete\|States in this hypothesis" ~/thrust1-lab/learnrun/logs/learner_console.log | tail -3
docker exec t1-learn bash -c 'cd /work/learnrun; ./kill_uecontroller.sh; ./kill_gnb.sh; ./kill_core.sh' ; docker stop t1-learn
```
The GitHub backup loop stops by itself when the learner is gone.

### 3.2 Save the model into the repo
```bash
cd ~/5g-nas-spec-conformance/thrust1
M=~/thrust1-lab/learnrun/logs/srsue.log/learnedModel.dot      # or the last hypothesis_N.dot
cp $M results/srsue_learnedModel.dot
```

### 3.3 Compare with the paper: Table 4 (size) and Table 8 (issues)
```bash
python3 -I symbols/fsm_tools.py stats  results/srsue_learnedModel.dot
python3 -I symbols/fsm_tools.py issues results/srsue_learnedModel.dot | tee results/srsue_issues.txt
python3 -I symbols/fsm_tools.py nas    results/srsue_learnedModel.dot results/srsue_nas.dot
```
- **Table 4 (srsUE):** 6 states, 20 transitions (non-self-loop). Write down what you got. A difference is a
  result too; explain it (e.g. CE-feeding mode stops after 30 equivalence queries).
- **Table 8 (srsUE truth):** I3, I4, I7, I9 (our probes I9a/I9b), I10, I19 and I20 are expected `PRESENT`.
  Recall = (number of these 7 that are PRESENT) / 7.
- Table 8 lists **I6** (replayed SMC right after SMC) only for OAI UE, but our srsUE answers it with
  `nas_sm_complete` (already in hypothesis 3 and in the raw queries). Report this as a difference from
  Table 8 rather than as an error. I17 is not listed for srsUE.
- Dry run on hypothesis 3 (4 states), 2026-10-13: srsUE added as a third device still leaves
  **6 Case 2 classes invisible to differential testing** (23 classes). Expect similar numbers with the
  final model.

### 3.4 Spec vs devices with srsUE as the third device
The two 5GBaseChecker FSMs: `bash ../reproduce.sh` downloads them to `../repro/dl/`.
```bash
cd ~/5g-nas-spec-conformance && bash reproduce.sh && cd thrust1
python3 -I compare/spec_vs_devices.py spec_fsm/spec_cells_v1.json results/T1.6_spec_vs_ABsrs.json \
  A=../repro/dl/FSM_A.dot B=../repro/dl/FSM_B.dot srsue=results/srsue_learnedModel.dot | tee results/T1.6_summary_ABsrs.txt
```
What to read in the output:
- `summary:` gives the number of classes per case. **`Case 2 INVISIBLE to diff`** is the main claim:
  all devices answer the same way, and all of them break the spec.
- Each class line shows the input, the spec state, the allowed outputs, every device's output, and the
  clause note.
- `(c) candidates`: device behaviour where the spec is silent (I19, I20).
- Check that the srsUE I3, I4, I7, I10 deviations appear. They match the early raw queries
  (`id_response`, `auth_response`, `nas_sm_complete` after SMC).

### 3.5 Independent check with DevLyzer (the authors' 45 properties)
```bash
D=~/thrust1-lab/devlyzer_srs; mkdir -p $D
cp -r ~/thrust1-lab/5GBaseChecker/DevLyzer/main.py ~/thrust1-lab/5GBaseChecker/DevLyzer/attack_trace_checker $D/
python3 -I compare/to_devlyzer.py results/T1.6_spec_vs_ABsrs.json $D/deviant-queries.json
docker run --rm --cpus=2 -u $(id -u):$(id -g) -v $D:/work -w /work t1-offline python3 main.py 2>&1 | tail -3
python3 -I -c "import json;[print(f, len(json.load(open('$D/deviant-queries_'+f+'.json'))['traces'])) for f in ('attack','benign','unresolved')]"
cp $D/deviant-queries*.json lab/devlyzer/   # optional: keep with the results (rename to *_srs.json)
```
`attack` = classes that violate one of the 45 properties (independent confirmation). For FSM_A/B it was
23/23 with 0 unresolved.

### 3.6 Write it up
1. **`results/T1_RESULTS_v2.md`**: copy v1. Add srsUE to the tables (Table 4 numbers, Table 8 recall, new
   classes from `T1.6_summary_ABsrs.txt`, DevLyzer counts). Then go through the v1 "Limitations" list:
   remove "srsUE pending", and the S4 classes no longer rest on FSM_B alone.
2. **`report/thrust1_report.tex`**: places to change (line numbers as of v1):
   - l.51: `version 1 (srsUE learning run in progress)` → `version 2`
   - l.70–72: "is still being learned" → the result
   - l.135: `FSM\_A, FSM\_B, (srsUE)` → remove the brackets
   - l.380: the status row → `done: N states, M transitions`
   - l.402, l.407: limitations that mention srsUE pending
   - l.416–417: the next-step item → move into the results section, with a table: issue | Table 8 | ours
     (PRESENT/–) | spec class | case | DevLyzer
   Compile in Overleaf (upload the .tex).
3. **`T1_PROGRESS.md`**: add a "T1.2 srsUE result" section with the numbers and the date.
4. Push:
   ```bash
   cd ~/5g-nas-spec-conformance && git add -A && git commit -m "srsUE learned: Table 4/8 comparison, results v2" && git push
   ```

## 4. Restarting a learning run from zero (only if ever needed)
```bash
docker exec t1-learn /work/learnrun/container_init.sh
mv ~/thrust1-lab/learnrun/my_database.sqlite ~/thrust1-lab/learnrun/my_database.sqlite.old   # fresh start = no checkpoint
mv ~/thrust1-lab/learnrun/logs/srsue.log ~/thrust1-lab/learnrun/logs/srsue.log.old
nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --who=thrust1 --why=learning \
  docker exec t1-learn /work/learnrun/start_learner.sh >/dev/null 2>&1 &
nohup ~/thrust1-lab/learnrun/checkpoint.sh >/dev/null 2>&1 &
```
The configuration is `~/thrust1-lab/learnrun/fgue.properties`: `device = srsue`, `CE_revserse_feeding = 1`,
`resume_learning = true`, `cache_active = true`, and the 29 stored counterexamples in `CEStore/input`.
