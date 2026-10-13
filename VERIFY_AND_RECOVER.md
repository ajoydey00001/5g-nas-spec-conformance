# Is Thrust 1 done without errors? And what if the run crashes?

> **Finalized 2026-10-14:** the demonstration uses preserved srsUE hypothesis 5
> (6 states / 21 transitions, Table 8 recall 7/7). The learner reached its
> 30-equivalence-call budget; convergence is not established. Auto-resume is paused.
> Do not resume this completed budget run. See `thrust1/results/T1_RESULTS_v2.md`.
> `bash check_thrust1.sh` now checks local reproducibility and provenance;
> independent validation and guided-learning D4 experiments remain future work.
> Older live-run estimates and restart advice below are historical.

Written 2026-10-13 23:15. More detail: `NEXT_STEPS.md` (all commands) and `RUNBOOK.md` (every problem and its fix).

## 1. How do I know Thrust 1 is done without errors?

Run this any time:
```bash
cd ~/5g-nas-spec-conformance && bash check_thrust1.sh
```
**Thrust 1 is complete when every line says PASS.** Result on 2026-10-13 23:05:

```
PASS  reproduce.sh: classes match the committed results        <- analysis reruns from scratch, same 23 classes
PASS  spec cells regenerate identically (quotes verified)      <- all 89 spec quotes found word-for-word
WAIT  learner still running (4 hypotheses so far)
PASS  Table 8 recall 7/7
PASS  Case 2 classes invisible to differential testing: 6      <- the novelty claim
PASS  DevLyzer: 0 unresolved
WAIT  results v2 / report / push not done yet
```
The C-section PASS lines come from the interim hypothesis-4 result (files ending in `_dry`).
The WAIT lines clear in this order:
1. The run finishes. Then run `bash finish_thrust1.sh`.
2. Write `thrust1/results/T1_RESULTS_v2.md`.
3. Update `thrust1/report/thrust1_report.tex` (NEXT_STEPS.md, A4).
4. Push: `git add -A && git commit -m "Thrust 1 complete" && git push`.

What each check means:

| Check | Why it matters |
|---|---|
| reproduce.sh matches | The spec FSM and the comparison are deterministic and can be rebuilt by anyone from public downloads |
| quotes verified | Every spec transition is backed by a word-for-word TS 24.501 quote, so none was invented |
| final srsUE model | The learning run reached its end (paper Table 4: 6 states, 20 transitions) |
| Table 8 recall ≥ 6/7 | Our setup finds the issues the 5GBaseChecker paper reported for srsUE |
| invisible Case 2 > 0 | All devices agree, so differential testing cannot see it, but all of them break the spec: **the new result** |
| DevLyzer 0 unresolved | An independent tool (the authors' 45 LTL properties) agrees with every deviation class |
| results v2, report, push | The write-up is finished and your supervisor can see it |

## 2. What if the run crashes while the laptop is on for days?

**It recovers automatically.** A cron job runs `~/thrust1-lab/learnrun/auto_resume.sh` every 15 minutes and after
every boot. It was installed on 2026-10-13.

It restarts the run from the checkpoint database in either of these cases:
- the learner has died (crash, power cut, reboot) and there is no `learnedModel.dot`;
- no query has finished for 90 minutes (a stall, like the /dev/shm one on 2026-10-13).

Restarting reuses the saved answers in `my_database.sqlite` ("Found in previous log" in the console). Only the
query that was running is lost. It stops after 6 restarts, so a real fault cannot loop forever.

Tested so far: the healthy path, where it correctly does nothing. The crash path uses the same
`resume_after_reboot.sh` that you would run by hand. It has not been tested end to end with a real crash.

Commands:
```bash
bash ~/thrust1-lab/learnrun/update.sh                # "what is the update?": health, speed, model size, what to do
bash ~/thrust1-lab/learnrun/status.sh                # health check (once a day is enough)
cat ~/thrust1-lab/learnrun/logs/auto_resume.log      # what auto-resume did (empty = never needed)
bash ~/thrust1-lab/learnrun/resume_after_reboot.sh   # the same restart, by hand
touch ~/thrust1-lab/learnrun/AUTO_RESUME_OFF         # pause auto-resume (do this before stopping the learner yourself)
rm ~/thrust1-lab/learnrun/AUTO_RESUME_OFF            # turn it back on
crontab -r                                           # remove it completely once Thrust 1 is done
```

**The laptop's database is lost or damaged:** run `cd ~/5g-nas-spec-conformance && git pull`, then the resume
script. It copies the GitHub backup (`thrust1/lab/srsue_checkpoint/my_database.sqlite`, saved every 30 min)
back first.

**Finishing:** `finish_thrust1.sh` turns auto-resume off by itself, because it stops the 5G stack.

**Run not finished by 2026-10-16:** stop it and use the last hypothesis:
```bash
touch ~/thrust1-lab/learnrun/AUTO_RESUME_OFF; docker exec t1-learn pkill -f uelearner.Learner
cd ~/5g-nas-spec-conformance && bash finish_thrust1.sh
```

## 3. Your part

- Keep the charger plugged in.
- Run `status.sh` once a day.
- When `learnedModel.dot` appears, or the learner stops, run `bash finish_thrust1.sh`, then `bash check_thrust1.sh`.
