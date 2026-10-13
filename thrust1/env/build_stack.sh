#!/bin/bash
# Builds the T1.2 stack inside t1-enva, one component at a time (laptop has 11 GB RAM).
set -u
J=3
L=/work/logs
SS=/work/5GBaseChecker/StateSynth/modified_cellular_stack
step() { echo "== $1 start $(date)"; }
done_() { echo "== $1 exit=$2 $(date)"; }

step core
cd $SS/5GBaseChecker_Core && { [ -d build ] || meson build --prefix=$PWD/install; } > $L/T1.2_core_meson.log 2>&1 \
  && ninja -C build -j$J > $L/T1.2_core_ninja.log 2>&1; done_ core $?

step srs_gnb
cd $SS/5GBaseChecker_srs_gnb && mkdir -p build && cd build && cmake .. > $L/T1.2_gnb_cmake.log 2>&1 \
  && make srsenb -j$J > $L/T1.2_gnb_make.log 2>&1; done_ srs_gnb $?

step srsue
cd /work/srsRAN_4G_22_10 && mkdir -p build && cd build && cmake .. > $L/T1.2_ue_cmake.log 2>&1 \
  && make srsue -j$J > $L/T1.2_ue_make.log 2>&1; done_ srsue $?
