"""Generate confidence-ranked spec transition-cover inputs, without consulting UEs.
The learner ignores predicted outputs: these are candidate test words, not assertions.
UNDERSPECIFIED/NO_CONNECTION cells are excluded; inferred cells are opt-in.
"""
import argparse, collections, hashlib, json, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'compare'))
from spec_vs_devices import Spec


def generate(doc, include_inferred=False):
    spec=Spec(doc); access={spec.start:[]}; todo=collections.deque([spec.start]); candidates={}
    while todo:
        q=todo.popleft()
        for a in spec.inputs:
            cell=spec.cells[q[0]][a]
            word=access[q]+[a]
            if cell['kind']=='SPEC' or include_inferred and cell['kind']=='INFERRED':
                key=(q[0],a)
                if key not in candidates or len(word)<len(candidates[key]['word']):
                    candidates[key]={'state':q[0],'input':a,'kind':cell['kind'],'word':word,'evidence':cell['evidence']}
            # Exclude uncertain optional state transitions from access paths.
            if cell['kind'] in ('UNDERSPECIFIED','NO_CONNECTION'):continue
            _,nq,_=spec.step(q,a,cell['output'])
            if nq not in access:access[nq]=word;todo.append(nq)
    ordered=sorted(candidates.values(),key=lambda c:(c['kind']!='SPEC',len(c['word']),c['state'],c['input']))
    unique=[];seen=set()
    for c in ordered:
        w=tuple(c['word'])
        if w not in seen:unique.append(c);seen.add(w)
    return unique


def main():
    p=argparse.ArgumentParser();p.add_argument('cells',type=pathlib.Path);p.add_argument('outdir',type=pathlib.Path);p.add_argument('--include-inferred',action='store_true');a=p.parse_args()
    doc=json.loads(a.cells.read_text());records=generate(doc,a.include_inferred);a.outdir.mkdir(parents=True,exist_ok=True)
    # Outputs are placeholders and not parsed by upstream loadCE().
    content=''.join('INFO: ['+' '.join(c['word'])+' / null_action]\n' for c in records)
    (a.outdir/'spec_inputs').write_text(content)
    (a.outdir/'spec_inputs.json').write_text(json.dumps({'source_sha256':hashlib.sha256(a.cells.read_bytes()).hexdigest(),'include_inferred':a.include_inferred,'records':records},indent=2)+'\n')
    print('%d candidate input words'%len(records))

if __name__=='__main__':main()
