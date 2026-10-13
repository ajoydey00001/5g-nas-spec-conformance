#!/bin/bash
# Adapted from 5GBaseChecker_Statelearner for the t1-enva container (paths under /work, ZMQ radio, srsUE).
if [ "$EUID" -ne 0 ]; then echo "Need to run as root"; exit; fi
pkill -9 -f 5gc; pkill -9 -f "open5gs-"
