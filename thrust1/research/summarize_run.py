"""Record finite-suite completion and query counts; exact full-model equivalence for arms."""
import collections, json, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'symbols'))
from fsm_tools import Mealy


def distinguishing_word(a,b):
    if a.inputs!=b.inputs:raise ValueError('Different alphabets')
    todo=collections.deque([(a.start,b.start,[])]);seen={(a.start,b.start)}
    while todo:
        x,y,w=todo.popleft()
        for sym in a.inputs:
            nx,ox=a.delta[x,sym];ny,oy=b.delta[y,sym]
            if ox!=oy:return w+[sym]
            if (nx,ny) not in seen:seen.add((nx,ny));todo.append((nx,ny,w+[sym]))
    return None


def summarize(run,code,elapsed):
    log=run/'logs/console.log';text=log.read_text(errors='replace')
    model=run/'logs/model/learnedModel.dot'
    complete=code==0 and model.exists() and 'RESEARCH_WP_SUITE_COMPLETE' in text
    result={'arm':run.name,'exit_code':code,'elapsed_seconds':elapsed,'status':'wp_suite_complete' if complete else ('wallclock_budget_exhausted' if code==124 else 'failed'),'model':str(model) if model.exists() else None,'scope':'finite Wp suite at configured depth; no unlimited-equivalence claim'}
    for kind in ('learning','equivalence'):
        qlog=run/('logs/model/'+kind+'_queries.log')
        result[kind+'_query_log_records']=sum(l.startswith('INFO: [') for l in qlog.read_text(errors='replace').splitlines()) if qlog.exists() else None
    if complete:result['states'],result['non_self_loop_transitions']=Mealy.from_dot(model).stats()
    (run/'outcome.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


def compare(runs,out):
    records=[json.loads((runs/name/'outcome.json').read_text()) for name in ('01_wp','02_spec','03_shipped','04_both')]
    if any(r['status']!='wp_suite_complete' for r in records):raise SystemExit('Cannot claim D4 savings with incomplete arms')
    models=[Mealy.from_dot(r['model']) for r in records]
    witnesses={r['arm']:distinguishing_word(models[0],m) for r,m in zip(records[1:],models[1:])}
    result={'arms':records,'baseline_distinguishing_words':witnesses,'all_models_equivalent':all(w is None for w in witnesses.values()),'claims':'query savings must use the measured counts, including PCE checks; differing models invalidate a like-for-like savings claim'}
    out.write_text(json.dumps(result,indent=2)+'\n');print(out)

if __name__=='__main__':
    if sys.argv[1]=='--compare':compare(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
    else:summarize(pathlib.Path(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]))
