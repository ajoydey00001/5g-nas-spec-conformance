#!/bin/bash
# Adapted from 5GBaseChecker_Statelearner for the t1-enva container (paths under /work, ZMQ radio, srsUE).
if [ "$EUID" -ne 0 ]; then echo "Need to run as root"; exit; fi
pkill -9 -f srsenb; sleep 1
cd /work/learnrun/conf && /work/5GBaseChecker/StateSynth/modified_cellular_stack/5GBaseChecker_srs_gnb/build/srsenb/src/srsenb /work/learnrun/conf/enb.conf &> /tmp/enb_fuzzing.log &
sleep 1; echo "srs gNB started, log /tmp/enb_fuzzing.log"
