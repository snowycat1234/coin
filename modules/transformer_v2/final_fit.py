"""Registered past-only final refits. No locked inputs, labels or early stopping."""
import argparse,json,os,platform,subprocess,time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from .data import load_development
from .train import atomic,sha,fit_phase

def final_indices(d,scenario,min_rows=180):
    cutoff=pd.Timestamp('2026-03-01',tz='UTC')-pd.Timedelta(days=60)
    causal=d['ready'].copy()
    for a in range(len(d['symbols'])):
        causal[:,a]&=pd.Series(d['availability'][:,a]).rolling(256,min_periods=256).sum().eq(256).to_numpy()
    valid=causal&np.isfinite(d['utility'][scenario]).all(-1)&(d['label_end']<cutoff)[:,None]
    active=valid.sum(0)>=min_rows
    indices=np.flatnonzero((valid&active).any(1))
    assert len(indices) and indices.min()>=255 and (d['label_end'][indices]<cutoff).all()
    return indices,active,cutoff

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True)
    p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);p.add_argument('--wait',action='store_true');a=p.parse_args()
    assert platform.system()=='Linux' and not os.environ.get('WSL_DISTRO_NAME') and 'microsoft' not in platform.release().lower()
    state=Path(a.state);repo=Path(__file__).resolve().parents[2]
    protocol_path=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json';protocol=json.loads(protocol_path.read_text())
    assert sha(protocol_path)==protocol_path.with_suffix('.sha256').read_text().strip()
    assert subprocess.check_output(['git','-C',str(repo),'show','HEAD:modules/transformer_v2/final_fit.py'])==Path(__file__).read_bytes()
    while json.loads((state/'FIT_PROGRESS.json').read_text()).get('status')!='COMPLETE':
        if not a.wait:raise RuntimeError('All five development folds must finish before the fixed median epoch is available')
        live=subprocess.check_output(['systemctl','show','coin-transformer-v2-train-20261007','-p','ActiveState','--value'],text=True).strip()
        assert live in ('active','activating'),'Training is not live; no automatic restart'
        atomic(state/'final-fit-progress.json',dict(stage='WAIT_DEVELOPMENT_FITS',pid=os.getpid(),updated_at=time.time()));time.sleep(15)
    assert torch.cuda.is_available(),'CUDA required; CPU fallback prohibited';torch.ones(1,device='cuda')
    torch.set_num_threads(len(os.sched_getaffinity(0)))
    binding=json.loads((state/'TRAIN_BINDING.json').read_text());d=load_development(a.collector_root,a.work,a.source_run)
    assert all(sha(Path(__file__).with_name(name))==digest for name,digest in binding['source_sha256'].items())
    plan=[]
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
        indices,active,cutoff=final_indices(d,scenario)
        for family in protocol['models']:
            for seed in protocol['seeds']:
                selected=[json.loads((state/'fits'/tag/f'fold{fold}'/family/f'seed{seed}'/'inner/RESULT.json').read_text())['best_epoch'] for fold in range(1,6)]
                epochs=max(1,int(round(float(np.median(selected)))))
                plan.append(dict(scenario=scenario,tag=tag,family=family,seed=seed,epochs=epochs,development_inner_epochs=selected,
                                 training_indices=indices.tolist(),active=active.tolist(),cutoff=str(cutoff),max_label_end=str(d['label_end'][indices].max())))
    recipe=dict(status='FIXED_FROM_REGISTERED_PAST_ONLY_RULE',protocol_sha256=sha(protocol_path),final_fit_source_sha256=sha(__file__),tasks=plan)
    path=state/'FINAL_FIT_PLAN.json'
    if path.exists():assert json.loads(path.read_text())==recipe
    else:atomic(path,recipe)
    results=[]
    for number,task in enumerate(plan,1):
        folder=state/'final-fits'/task['tag']/task['family']/f'seed{task["seed"]}'
        own_binding=dict(**binding,final_fit_plan_sha256=sha(path),final_fit_source_sha256=sha(__file__))
        context=dict(stage='FIXED_EPOCH_FINAL_PAST_ONLY_REFIT',fold='FINAL_PAST_ONLY',status=state/'final-fit-progress.json')
        for attempt in range(2):
            try:
                result=fit_phase(d,task['training_indices'],[],task['scenario'],np.array(task['active']),task['family'],task['seed'],folder,task['epochs'],False,own_binding,context);break
            except Exception as exc:
                atomic(folder/f'FINAL_FAILURE_{attempt+1}.json',dict(error=str(exc),time=time.time()))
                if attempt==1:raise
        results.append(dict(task=task,result=result,folder=str(folder)))
        atomic(state/'FINAL_FITS.json',dict(status='RUNNING',completed=number,total=len(plan),results=results,protocol_sha256=sha(protocol_path)))
        print(f'FINAL FIT {number}/{len(plan)} {task["tag"]} {task["family"]} seed{task["seed"]}',flush=True)
    atomic(state/'FINAL_FITS.json',dict(status='COMPLETE',completed=len(results),total=len(plan),results=results,protocol_sha256=sha(protocol_path),locked_read=False))

if __name__=='__main__':main()
