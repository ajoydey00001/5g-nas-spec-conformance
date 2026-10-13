#!/bin/bash
# Run once per container start: MongoDB 4.4 + the test subscriber (same keys as conf/ue.conf).
rm -f /tmp/mongo/mongod.lock; mkdir -p /tmp/mongo && mongod --dbpath /tmp/mongo --bind_ip 127.0.0.1 --fork --logpath /tmp/mongod.log >/dev/null
DBCTL=/work/5GBaseChecker/StateSynth/modified_cellular_stack/5GBaseChecker_Core/misc/db/open5gs-dbctl
$DBCTL remove 001010123456780 >/dev/null 2>&1
$DBCTL add 001010123456780 00112233445566778899aabbccddeeff 63BFA50EE6523365FF14C1F45F88737D
echo "subscribers: $(mongo --quiet open5gs --eval 'db.subscribers.count()')"
