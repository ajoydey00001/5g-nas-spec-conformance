#!/bin/bash
# Blocks sleep/suspend for as long as the srsUE learner runs (independent of any terminal or Claude session).
exec systemd-inhibit --what=sleep:idle:handle-lid-switch --who=thrust1 --why="srsUE learning run" \
  bash -c 'while docker exec t1-learn pgrep -f uelearner.Learner >/dev/null 2>&1; do sleep 300; done'
