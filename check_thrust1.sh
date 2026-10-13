#!/bin/bash
# Validate the finalized demonstration; research-wide D4/independent extraction remain separate.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I - <<'PY'
import collections, hashlib, json, pathlib, subprocess, sys, tempfile
root=pathlib.Path.cwd(); r=root/'thrust1/results'; failures=[]
def check(ok,msg):
    print(('PASS  ' if ok else 'FAIL  ')+msg)
    if not ok: failures.append(msg)
with tempfile.TemporaryDirectory() as tmp:
    cells=pathlib.Path(tmp)/'cells.json'
    subprocess.run([sys.executable,'-I','thrust1/extract/author_spec_cells.py',str(cells)],check=True,stdout=subprocess.DEVNULL)
    check(cells.read_bytes()==pathlib.Path('thrust1/spec_fsm/spec_cells_v1.json').read_bytes(),'spec cells regenerate identically')
    build=subprocess.run([sys.executable,'-I','thrust1/extract/build_spec_fsm.py',str(cells),'repro/clauses.jsonl',tmp],check=True,capture_output=True,text=True)
    check('89 checked, 0 not found verbatim' in build.stdout,'89 evidence quotes found in cached specification')
    out=pathlib.Path(tmp)/'comparison.json'
    subprocess.run([sys.executable,'-I','thrust1/compare/spec_vs_devices.py',str(cells),str(out),'A=repro/dl/FSM_A.dot','B=repro/dl/FSM_B.dot','srsue=thrust1/results/srsue_learnedModel.dot'],check=True,stdout=subprocess.DEVNULL)
    check(json.loads(out.read_text())==json.loads((r/'T1.6_spec_vs_ABsrs.json').read_text()),'three-device comparison reproduces exactly')
model=r/'srsue_learnedModel.dot'; meta=json.loads((r/'srsue_model_provenance.json').read_text())
check(hashlib.sha256(model.read_bytes()).hexdigest()==meta['sha256'],'model matches recorded source hash')
check(meta['status']=='budget_limited_hypothesis' and meta['converged'] is False,'budget-limited stopping condition explicitly recorded')
issues=subprocess.check_output([sys.executable,'-I','thrust1/symbols/fsm_tools.py','issues',str(model)],text=True)
present={line.split()[0] for line in issues.splitlines() if line.split()[1]=='PRESENT'}
check({'I3','I4','I7','I10','I19','I20'}<=present and bool({'I9a','I9b'}&present),'Table 8 recall 7/7')
d=json.loads((r/'T1.6_spec_vs_ABsrs.json').read_text()); invisible=[c for c in d['classes'] if c['case']==2 and not c['visible_to_diff']]
check(len(d['classes'])==23 and len(invisible)==6,'23 classes, six invisible witnesses')
check(all(len({tuple(v) for v in c['device_outputs'].values()})==1 and c['n']==3 and c['k']==0 for c in invisible),'all three devices agree along every invisible witness and violate its final cell')
base=pathlib.Path('thrust1/lab/devlyzer_srs'); counts={k:len(json.loads((base/('deviant-queries_'+k+'.json')).read_text())['traces']) for k in ('attack','benign','unresolved')}
check(counts=={'attack':23,'benign':7,'unresolved':0},'DevLyzer: 23 attack / 7 benign / 0 unresolved records')
check((r/'T1_RESULTS_v2.md').exists() and 'budget-limited' in pathlib.Path('thrust1/report/thrust1_report.tex').read_text(),'results v2 and report disclose model limitation')
print('Scope: finalized Thrust 1 demonstration; independent validation and D4 experiments remain future work.')
sys.exit(bool(failures))
PY
