"""Measure assumption sensitivity; baseline cells/results are not overwritten."""
import copy, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]

def main():
    base=json.loads((ROOT/'thrust1/spec_fsm/spec_cells_v1.json').read_text())
    out=ROOT/'thrust1/results/sensitivity';out.mkdir(exist_ok=True)
    variants={'baseline':copy.deepcopy(base),'optional_smc_state':copy.deepcopy(base),'r2_open':copy.deepcopy(base),'no_inferred_judgments':copy.deepcopy(base)}
    variants['optional_smc_state']['cells']['S2']['nas_sm_cmd_protected']['next_by_output']={'nas_sm_complete':'S3'}
    c=variants['r2_open']['cells']['S4']['registration_accept_protected'];c['kind']='UNDERSPECIFIED';c['also_allowed']=['registration_complete']
    outputs=['registration_request','id_response','auth_response','nas_sm_complete','nas_sm_reject','registration_complete','deregistration_accept','config_update_complete','null_action']
    for row in variants['no_inferred_judgments']['cells'].values():
        for c in row.values():
            if c['kind']=='INFERRED':c['kind']='UNDERSPECIFIED';c['also_allowed']=[o for o in outputs if o!=c['output']]
    summary={}
    for name,doc in variants.items():
        cells=out/(name+'_cells.json');result=out/(name+'_comparison.json');cells.write_text(json.dumps(doc,indent=1)+'\n')
        proc=subprocess.run([sys.executable,'-I',str(ROOT/'thrust1/compare/spec_vs_devices.py'),str(cells),str(result),'A='+str(ROOT/'repro/dl/FSM_A.dot'),'B='+str(ROOT/'repro/dl/FSM_B.dot'),'srsue='+str(ROOT/'thrust1/results/srsue_learnedModel.dot')],check=True,capture_output=True,text=True)
        (out/(name+'_summary.txt')).write_text(proc.stdout)
        d=json.loads(result.read_text());invisible=[c for c in d['classes'] if c['case']==2 and not c['visible_to_diff']]
        summary[name]={'classes':len(d['classes']),'invisible':len(invisible),'invisible_cells':[[c['spec_state'],c['input']] for c in invisible]}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
