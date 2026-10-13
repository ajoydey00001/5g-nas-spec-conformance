#!/bin/bash
# The shipped jar has no Main-Class in its manifest, so name the class explicitly.
cd /work/learnrun
exec java -cp /work/5GBaseChecker/StateSynth/5GBaseChecker_Statelearner/out/artifacts/5GBaseChecker_Statelearner_jar/5GBaseChecker_Statelearner.jar \
  org.example.uelearner.Learner fgue.properties > logs/learner_console.log 2>&1
