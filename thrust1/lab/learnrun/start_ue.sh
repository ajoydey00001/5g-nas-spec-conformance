#!/bin/bash
# Adapted from 5GBaseChecker_Statelearner for the t1-enva container (paths under /work, ZMQ radio, srsUE).
if [ "$EUID" -ne 0 ]; then echo "Need to run as root"; exit; fi
pkill -9 -f srsue; sleep 1
/work/srsRAN_4G_22_10/build/srsue/src/srsue /work/learnrun/conf/ue.conf > /tmp/ue_fuzzing.log 2>&1 &
sleep 1; echo "srsue started, log /tmp/ue_fuzzing.log"
