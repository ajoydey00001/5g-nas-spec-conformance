# srsUE learning checkpoint (Table 4 run)

This folder is updated every 30 minutes while the run is going.

## What the files are

| File | What |
|---|---|
| `my_database.sqlite` | **The checkpoint.** Table `queryNew_srsue` holds every membership query the learner has answered. With `resume_learning = true` (in `fgue.properties`), a restarted learner takes those answers from this database instead of re-running core, gNB and UE. |
| `n_queries.txt` | Number of saved queries at the last snapshot. |
| `resume.log`, `srsue.log/`, `learner_console.log` | Logs, plus the hypotheses learned so far (`hypothesis_N.dot`). |

## Resuming after an interruption (power loss, reboot)

1. Start the container again, then run `container_init.sh` inside it (it starts mongod and adds the
   subscriber).
2. Only if `~/thrust1-lab/learnrun/my_database.sqlite` is missing or broken, copy this folder's
   `my_database.sqlite` there.
3. Start the learner the same way as before (`start_learner.sh`, with `systemd-inhibit`).

The learner replays the saved queries in seconds and continues live from the first query it hasn't
answered yet. Do **not** delete `my_database.sqlite` before restarting.
