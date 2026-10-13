# Resuming the srsUE learning run after the laptop was off

## Short version (what to type)

After switching the laptop on and logging in, open a terminal and run:

```bash
bash ~/thrust1-lab/learnrun/resume_after_reboot.sh
```

That's all. The script prints 6 steps and ends with `Resumed. The learner is running.`
Keep the charger plugged in. You can close the terminal afterwards, because the learner runs in the
background.

To watch the learner (Ctrl+C stops only the watching, not the learner):

```bash
tail -f ~/thrust1-lab/learnrun/logs/learner_console.log | grep -E 'Found in previous log|Not found|Starting round'
```

- `Found in previous log` lines: queries answered instantly from the checkpoint. A few hundred of these
  appear in the first minutes.
- `Not found in previous log` lines: the learner is past the checkpoint and running live (about 2 min per
  query).

To check whether it is still running:

```bash
docker exec t1-learn pgrep -f uelearner.Learner && echo RUNNING || echo STOPPED
cat ~/thrust1-lab/learnrun/logs/run_table4_time.txt    # start / resume / EXIT times
```

## What the script does (if you want to do it by hand)

```bash
# 1. start the container (it survives reboots, only stopped)
docker start t1-learn
# 2. MongoDB + test subscriber (inside the container)
docker exec t1-learn bash -c 'pkill mongod; sleep 2; rm -rf /tmp/mongo'
docker exec t1-learn /work/learnrun/container_init.sh          # prints "subscribers: 1"
# 3. clear leftover core/gNB/UE processes
for k in kill_uecontroller kill_gnb kill_core; do docker exec t1-learn /work/learnrun/$k.sh; done
# 4. checkpoint: ~/thrust1-lab/learnrun/my_database.sqlite must exist.
#    Only if it is missing or broken: cp this folder's my_database.sqlite to ~/thrust1-lab/learnrun/
# 5. keep old logs (the learner starts new hypothesis_N.dot files from 1)
mv ~/thrust1-lab/learnrun/logs/srsue.log ~/thrust1-lab/learnrun/logs/srsue.log.before_resume_$(date +%Y%m%d_%H%M)
# 6. start the learner with sleep blocked, then the GitHub checkpoint loop
nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --who=thrust1 --why="srsUE learning" \
  docker exec t1-learn /work/learnrun/start_learner.sh > /dev/null 2>&1 &
sleep 60; nohup ~/thrust1-lab/learnrun/checkpoint.sh > /dev/null 2>&1 &
```

## Why resuming loses almost nothing

`my_database.sqlite` stores every answered membership query (table `queryNew_srsue`). With
`resume_learning = true` in `fgue.properties`, the learner does two things on start:

1. It moves those rows into `query_srsue`.
2. Before running any query on the radio stack, it looks the query up there (`LearningResumer.query_resumer`).

The algorithm is deterministic, so it asks the same queries again in the same order. It gets them back
from the database in seconds, and continues live from the first unanswered one. An interruption costs
only the query that was in progress.

**Do not delete `~/thrust1-lab/learnrun/my_database.sqlite`.**

## Files in this folder (updated every 30 min while the run is going)

| File | What |
|---|---|
| `my_database.sqlite` | Copy of the checkpoint (consistent SQLite backup) |
| `n_queries.txt` | Number of saved answers at the last snapshot |
| `srsue.log/` | Learner logs and hypotheses so far (`hypothesis_N.dot`) |
| `learner_console.log`, `resume.log`, `run_table4_time.txt` | Console output, resume log, start/stop times |

Scripts: `thrust1/lab/learnrun/resume_after_reboot.sh`, `checkpoint.sh`, `container_init.sh`.
