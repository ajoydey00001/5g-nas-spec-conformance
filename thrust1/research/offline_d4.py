"""Actual TTT+Wp on deterministic saved models. Supplemental, not live D4 evidence.
Requires container t1-learn with Java 11; results include exact target equivalence.
"""
import json, pathlib, subprocess, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'symbols'))
from fsm_tools import Mealy
from summarize_run import distinguishing_word
ROOT=pathlib.Path(__file__).resolve().parents[2]

def main():
    lab=pathlib.Path.home()/'thrust1-lab';work=lab/'research/offline';work.mkdir(parents=True,exist_ok=True)
    source=ROOT/'thrust1/research/OfflineD4.java';(work/source.name).write_text(source.read_text())
    jar='/work/research/build/research-learner.jar'
    subprocess.run(['docker','exec','-w','/work/research/offline','t1-learn','javac','-proc:none','--release','11','-cp',jar,'OfflineD4.java'],check=True)
    config=(lab/'research/runs/01_wp/fgue.properties').read_text()
    inputs=config.split('alphabet = ',1)[1].splitlines()[0].split()
    (work/'alphabet.txt').write_text(' '.join(inputs)+'\n')
    result=[]
    for name,path in [('A',ROOT/'repro/dl/FSM_A.dot'),('B',ROOT/'repro/dl/FSM_B.dot'),('srsue_h5',ROOT/'thrust1/results/srsue_learnedModel.dot')]:
        target=Mealy.from_dot(path)
        if set(inputs)!=set(target.inputs):raise ValueError('Alphabet mismatch')
        tsv=work/(name+'.tsv');tsv.write_text(''.join('\t'.join((s,a,d,o))+'\n' for (s,a),(d,o) in sorted(target.delta.items())))
        for arm in ('01_wp','02_spec','03_shipped','04_both'):
            ce=lab/'research/runs'/arm/'CEStore/input';cefile=work/(arm+'.txt');cefile.write_bytes(ce.read_bytes())
            model=work/(name+'_'+arm+'.dot')
            cmd=['docker','exec','-w','/work/research/offline','t1-learn','java','-Xmx512m','-cp',jar+':.','OfflineD4',name+'.tsv','alphabet.txt',cefile.name,'1',model.name]
            run=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=120)
            metrics=json.loads(next(l[7:] for l in run.stdout.splitlines() if l.startswith('RESULT ')))
            learned=Mealy.from_dot(model);w=distinguishing_word(target,learned)
            metrics.update({'target':name,'arm':arm,'distinguishing_word':w,'exactly_equivalent_to_target':w is None})
            result.append(metrics);print(name,arm,metrics['mq'],metrics['eq'],'equivalent',w is None)
    out=ROOT/'thrust1/results/D4_offline.json'
    out.write_text(json.dumps({'scope':'Fixed previously learned FSM oracle. Does not measure UE learning time, nondeterminism or live query savings. Not a substitute for planned live D4.','learner':'LearnLib TTT + Wp, depth 1, 29-symbol alphabet, fresh oracle counters, no persistent cache','results':result},indent=2)+'\n')

if __name__=='__main__':main()
