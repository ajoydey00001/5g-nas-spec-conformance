#!/bin/bash
# Adapted from 5GBaseChecker_Statelearner for the t1-enva container (paths under /work, ZMQ radio, srsUE).
if [ "$EUID" -ne 0 ]; then echo "Need to run as root"; exit; fi
pkill -9 -f 5gc; pkill -9 -f "open5gs-"; sleep 1
# every core run leaves a /dev/shm/mongoc-<pid> file; the container has only 64 MB of shm, so clear them
rm -f /dev/shm/mongoc-*
cd /work/5GBaseChecker/StateSynth/modified_cellular_stack/5GBaseChecker_Core && ./build/tests/app/5gc -c /work/learnrun/conf/sample.yaml &> /tmp/core_fuzzing.log &
echo "core started, log /tmp/core_fuzzing.log"
