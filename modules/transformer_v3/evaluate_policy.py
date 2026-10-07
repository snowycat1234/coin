"""Prepare fixed seed/ensemble targets and both risk profiles; no PnL search."""
import argparse,json
from pathlib import Path
import numpy as np
from modules.transformer_v2.train import atomic,sha
from .teachers import load_teacher_development
from .train_policy import FAMILIES,SEEDS
from .policy_portfolio import policy_targets
from .prediction_metrics import metrics
from .wallet import run_tasks

DAY=86_400_000_000

def save_targets(path,dates,weights,symbols):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        with np.load(path) as old:
            if not np.array_equal(old['weights'],weights) or not np.array_equal(old['decision_us'],dates) or old['symbol_order'].tolist()!=symbols:raise ValueError('Frozen target changed')
    else:np.savez_compressed(path,decision_us=dates,weights=weights,symbol_order=np.array(symbols))

def half_controls(state,protocol_sha):
    plan=json.loads((state/'V2_REPLAY_TASKS.json').read_text())['tasks'];tasks=[]
    families=('CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK')
    baselines=('BASE_CASH','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3','OLD_FROZEN_TRANSFORMER_SHARED')
    for old in plan:
        model=old['family'] in families and str(old['seed']) in tuple(map(str,SEEDS))+('ENSEMBLE',) and not old['id'].startswith(('corrected-oracles/','development-exposure/'))
        baseline=old['id'].startswith('legacy-controls/') and old['family'] in baselines
        if not model and not baseline:continue
        if sha(old['target_path'])!=old['target_sha256']:raise ValueError('Protected full-profile targets changed')
        with np.load(old['target_path']) as f:dates=f['decision_us'];weights=f['weights']*.5;symbols=f['symbol_order'].tolist()
        path=state/'half-control-targets'/(old['id'].replace('/','_')+'.npz');save_targets(path,dates,weights,symbols)
        task=dict(old,id='half-controls/'+old['id'],state=str(state/'half-controls'),target_path=str(path),target_sha256=sha(path),
                  protocol_sha256=protocol_sha,profile='HALF',full_profile_reference=str(state/'native'/old['id']/'RESULT.json'))
        tasks.append(task)
    if len(tasks)!=348:raise ValueError('Fixed 288 multitask/patch seed/ensemble and 60 baseline half-control tasks required')
    return tasks

def policy_tasks(a,protocol_sha):
    state=Path(a.state);d=load_teacher_development(a.collector_root,a.work,a.source_run)
    plan=json.loads((state/'V2_REPLAY_TASKS.json').read_text())['tasks'];windows={t['window']['id']:t['window'] for t in plan}
    tasks=[];diagnostics=[];binding=json.loads((state/'POLICY_TRAIN_BINDING.json').read_text())
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
      for fi,fold in enumerate(d['folds'],1):
        indices=fold['calendar'];active=d['ready'][indices]&np.array([s in fold['active'] for s in d['symbols']])[None,:]
        for family in FAMILIES:
            predictions=[];receipts=[]
            for seed in SEEDS:
                base=state/'policy-fits'/tag/f'fold{fi}'/family/f'seed{seed}'
                done=json.loads((base/'FIT_COMPLETE.json').read_text());path=base/'refit/PREDICTIONS.npz'
                if done['binding']!=binding or sha(path)!=done['prediction_sha256']:raise ValueError('Protected policy prediction changed')
                with np.load(path) as f:pred={k:f[k].copy() for k in f.files}
                if not np.array_equal(pred['indices'],indices):raise ValueError('Prediction calendar changed')
                predictions.append((str(seed),pred));receipts.append(dict(seed=seed,prediction_sha256=sha(path)))
            ensemble={k:np.mean([p[k] for _,p in predictions],axis=0) for k in predictions[0][1] if k!='indices'}
            predictions.append(('ENSEMBLE',ensemble))
            for seed,pred in predictions:
                diagnostic=metrics(pred,d['relative'][indices],d['expert_utilities'][scenario][indices],active)
                diagnostics.append(dict(diagnostic,family=family,seed=seed,fold=fi,funding_scale=1. if scenario==0 else .01))
                for profile in ('FULL','HALF'):
                    for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
                        weights=policy_targets(pred,d['sma'][indices],active,mapping,profile)
                        target=state/'policy-targets'/f'{tag}_fold{fi}_{family}_{seed}_{profile}_{mapping}.npz'
                        save_targets(target,d['dates'][indices].as_unit('us').asi8+DAY,weights,d['symbols'])
                        for w in (w for w in windows.values() if w['fold']==fi):
                            tasks.append(dict(id=f'{tag}/{w["id"]}/{family}/{seed}/{profile}/{mapping}',state=str(state/'policy-development'),
                                collector_root=a.collector_root,work=a.work,source_run=a.source_run,family=family,seed=seed,profile=profile,mapping=mapping,window=w,
                                funding_scale=1. if scenario==0 else .01,target_path=str(target),target_sha256=sha(target),protocol_sha256=protocol_sha,
                                prediction_sources=receipts if seed=='ENSEMBLE' else [r for r in receipts if str(r['seed'])==seed],noncausal=False))
    if len(tasks)!=576:raise ValueError('Exactly 576 fixed seed/ensemble three-mapping two-profile tasks required')
    atomic(state/'POLICY_PREDICTION_METRICS.json',dict(rows=diagnostics,diagnostic_labels_not_inference_inputs=True,source_sha256=sha(__file__)))
    atomic(state/'POLICY_DEVELOPMENT_TASKS.json',dict(tasks=tasks,protocol_sha256=protocol_sha,targets_frozen_before_native_economics=True))
    return tasks

def frozen_prediction_diagnostics(a):
    state=Path(a.state);old=Path(a.v2_state);d=load_teacher_development(a.collector_root,a.work,a.source_run);rows=[]
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
      for fi,fold in enumerate(d['folds'],1):
        indices=fold['calendar'];active=d['ready'][indices]&np.array([s in fold['active'] for s in d['symbols']])[None,:]
        for family in ('TRANSFORMER_SHARED','CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK'):
            predictions=[]
            for seed in SEEDS:
                base=old/'fits'/tag/f'fold{fi}'/family/f'seed{seed}'
                done=json.loads((base/'FIT_COMPLETE.json').read_text());path=base/'refit/PREDICTIONS.npz'
                if sha(path)!=done['prediction_sha256']:raise ValueError('Frozen v2 predictions changed')
                with np.load(path) as f:pred={k:f[k].copy() for k in f.files}
                predictions.append((str(seed),pred))
            ensemble={k:np.mean([p[k] for _,p in predictions],axis=0) for k in ('utility','relative')};predictions.append(('ENSEMBLE',ensemble))
            for seed,pred in predictions:
                result=metrics(pred,d['relative'][indices],d['expert_utilities'][scenario][indices],active)
                rows.append(dict(result,family=family,seed=seed,fold=fi,funding_scale=1. if scenario==0 else .01))
    atomic(state/'FROZEN_V2_PREDICTION_DIAGNOSTICS.json',dict(rows=rows,no_new_fit=True,source_sha256=sha(__file__)))
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);p.add_argument('--workers',type=int,default=10);p.add_argument('--half-controls-only',action='store_true');p.add_argument('--frozen-diagnostics-only',action='store_true');a=p.parse_args()
    state=Path(a.state)
    if a.frozen_diagnostics_only:frozen_prediction_diagnostics(a);return
    repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
    protocol=json.loads(proto.read_text())
    if sha(state/'V2_REPLAY_ANALYSIS.json')!=protocol['replay_analysis_sha256']:raise ValueError('Registered neutral analysis must precede new wallets')
    if a.half_controls_only:run_tasks(half_controls(state,sha(proto)),state/'half-controls','HALF_CONTROL_RESULTS',a.workers)
    else:
        fits=json.loads((state/'POLICY_FIT_PROGRESS.json').read_text())
        if fits['status']!='COMPLETE' or fits['completed']!=60:raise RuntimeError('All 60 fixed policy fits required')
        run_tasks(policy_tasks(a,sha(proto)),state/'policy-development','POLICY_DEVELOPMENT_RESULTS',a.workers)

if __name__=='__main__':main()
