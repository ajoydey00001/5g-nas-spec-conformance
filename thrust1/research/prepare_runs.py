"""Prepare isolated cold srsUE runs. Never copies the previous SQLite/checkpoint.
python3 prepare_runs.py REPO LAB [--lookahead 1] [--hours 48]
LAB must be the directory mounted as /work in t1-learn.
"""
import argparse, hashlib, json, pathlib, re, shutil
from spec_pces import generate


def set_property(text,key,value):
    pattern=r'(?m)^'+re.escape(key)+r'\s*=.*$'
    if not re.search(pattern,text):raise ValueError('Missing property '+key)
    return re.sub(pattern,lambda _:key+' = '+str(value),text)


def main():
    p=argparse.ArgumentParser();p.add_argument('repo',type=pathlib.Path);p.add_argument('lab',type=pathlib.Path);p.add_argument('--lookahead',type=int,default=1);p.add_argument('--hours',type=float,default=48);a=p.parse_args()
    if a.lookahead<0 or a.hours<=0:raise SystemExit('Invalid experiment limits')
    out=a.lab/'research';runs=out/'runs'
    if runs.exists():raise SystemExit('Runs already exist; refusing overwrite')
    base=a.lab/'learnrun'; doc=json.loads((a.repo/'thrust1/spec_fsm/spec_cells_v1.json').read_text())
    pces=generate(doc);spec=['INFO: ['+' '.join(c['word'])+' / null_action]' for c in pces]
    shipped_path=a.lab/'5GBaseChecker/StateSynth/5GBaseChecker_Statelearner/CEStore/configured_CEs/CE_reverse_feeding/All_CEs'
    shipped=[l for l in shipped_path.read_text().splitlines() if 'INFO' in l]
    if len(shipped)!=30:raise SystemExit('Expected 30 canonical shipped counterexample records')
    arms=[('01_wp',[]),('02_spec',spec),('03_shipped',shipped),('04_both',spec+shipped)]
    for name,lines in arms:
        run=runs/name;run.mkdir(parents=True);(run/'CEStore').mkdir();(run/'logs').mkdir()
        shutil.copytree(base/'conf',run/'conf')
        shutil.copytree(base/'UEController',run/'UEController')
        container_path='/work/research/runs/'+name
        for filename in ('start_core.sh','start_gnb.sh','start_srs_gnb.sh','start_ue.sh','kill_core.sh','kill_core_handle.sh','kill_evt.sh','kill_gnb.sh','kill_gnb_handle.sh','kill_uecontroller.sh','container_init.sh'):
            text=(base/filename).read_text().replace('/work/learnrun',container_path)
            (run/filename).write_text(text);(run/filename).chmod(0o755)
        text=(base/'fgue.properties').read_text()
        values={'EQCount':0,'CE_revserse_feeding':0,'DIKEUE_compare':0,'resume_learning':'false','cache_active':'false','output_dir':'./logs/model','max_depth':a.lookahead,'tgbot_enable':0}
        for k,v in values.items():text=set_property(text,k,v)
        (run/'fgue.properties').write_text(text)
        (run/'CEStore/input').write_text('\n'.join(lines)+ ('\n' if lines else ''))
        for f in ('resume.log','plain_replay.log','cache.log'):(run/f).write_text('')
        (run/'run.json').write_text(json.dumps({'arm':name,'device':'srsue release_22_10','alphabet':text.split('alphabet = ',1)[1].splitlines()[0].split(),'cold_start':True,'persistent_cache':False,'lookahead':a.lookahead,'wallclock_limit_seconds':int(a.hours*3600),'pce_count':len(lines),'shipped_source_sha256':hashlib.sha256(shipped_path.read_bytes()).hexdigest(),'pce_sha256':hashlib.sha256((run/'CEStore/input').read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256((a.repo/'thrust1/spec_fsm/spec_cells_v1.json').read_bytes()).hexdigest(),'interpretation':'live UE experiment; completion means finite Wp suite completed; timeout means budget-limited','status':'prepared'},indent=2)+'\n')
    (out/'spec_inputs.json').write_text(json.dumps(pces,indent=2)+'\n')
    print(runs)

if __name__=='__main__':main()
