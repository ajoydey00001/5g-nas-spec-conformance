#!/bin/bash
# Re-run the Thrust 1 offline analysis from scratch (no 5G stack, no Docker, Python 3 standard library only).
#   bash reproduce.sh            -> writes everything under ./repro/
# Downloads: TS 24.501 v17.8.0 from 3GPP, and the two learned UE FSMs from 5GBaseChecker (AGPL-3.0),
# both pinned to exact versions.
set -euo pipefail
cd "$(dirname "$0")"
OUT=repro; mkdir -p $OUT/dl
UA="Mozilla/5.0 (X11; Linux x86_64)"   # 3GPP's server refuses requests with curl's default user agent
FSM=https://raw.githubusercontent.com/SyNSec-den/5GBaseChecker/642443b765043c71e32d2db927278e691dee23aa/DevScan/fsm_checking/fsm_equivalence_checker_5GBaseChecker/FSM

echo "== 1. downloads"
[ -f $OUT/dl/24501-h80.zip ] || curl -fsSL -A "$UA" -o $OUT/dl/24501-h80.zip \
  https://www.3gpp.org/ftp/Specs/archive/24_series/24.501/24501-h80.zip
for f in FSM_A FSM_B; do [ -f $OUT/dl/$f.dot ] || curl -fsSL -o $OUT/dl/$f.dot $FSM/$f.dot; done

echo "== 2. TS 24.501 clause index"
python3 -I thrust1/extract/spec_clauses.py $OUT/dl/24501-h80.zip $OUT/clauses.jsonl

echo "== 3. spec cells -> spec FSM; every quote checked verbatim against the clause text"
python3 -I thrust1/extract/author_spec_cells.py $OUT/spec_cells_v1.json
cmp -s $OUT/spec_cells_v1.json thrust1/spec_fsm/spec_cells_v1.json \
  && echo "   spec_cells_v1.json identical to the committed one" \
  || { echo "   ERROR: regenerated spec_cells_v1.json differs from the committed one"; exit 1; }
python3 -I thrust1/extract/build_spec_fsm.py thrust1/spec_fsm/spec_cells_v1.json $OUT/clauses.jsonl $OUT/spec_fsm

echo "== 4. device FSMs: size and Table 8 issue probes"
for f in FSM_A FSM_B; do
  python3 -I thrust1/symbols/fsm_tools.py stats $OUT/dl/$f.dot
  python3 -I thrust1/symbols/fsm_tools.py issues $OUT/dl/$f.dot
done

echo "== 5. spec vs devices (T1.6): deviation classes and four-case classification"
python3 -I thrust1/compare/spec_vs_devices.py thrust1/spec_fsm/spec_cells_v1.json $OUT/T1.6_spec_vs_AB.json \
  A=$OUT/dl/FSM_A.dot B=$OUT/dl/FSM_B.dot | tee $OUT/T1.6_summary.txt
python3 -I - $OUT/T1.6_spec_vs_AB.json thrust1/results/T1.6_spec_vs_AB.json <<'EOF'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
key = lambda d: sorted((c['spec_state'], c['input'], c['case'], c['visible_to_diff']) for c in d['classes'])
matches = a == b
print('   classes match committed results:', matches, '(%d vs %d)' % (len(a['classes']), len(b['classes'])))
if not matches:
    raise SystemExit('reproduced comparison differs from committed artifact')
EOF
echo "done -> $OUT/"
