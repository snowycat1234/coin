"""Repair diagnostic horizon support without changing frozen causal evidence."""
import argparse,concurrent.futures,json,multiprocessing,time
from pathlib import Path
import numpy as np
from .train import atomic,sha
from .data import load_development
from .evaluate import native_worker,DAY
from .oracles import weights as oracle_weights
from .report import compact_case

def same_executed_targets(dates,old,new,window):
    selected=(dates>=window['start'])&(dates<window['end'])
    left=old[selected].copy();right=new[selected].copy()
    assert len(left)==window['days'] and len(left)>0
    left[-1]=0.;right[-1]=0.
    return np.array_equal(left,right)

def prepare(a):
    state=Path(a.state);repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    freeze=json.loads((state/'LOCKED_CANDIDATE_FREEZE.json').read_text())
    assert not freeze['locked_read'] and freeze['protocol_sha256']==sha(proto)
    assert not (state/'LOCKED_READ_AUTHORIZATION.json').exists(),'Correction must precede any locked release'
    d=load_development(a.collector_root,a.work,a.source_run)
    original=json.loads((state/'NATIVE_TASKS.json').read_text())['tasks']
    dest=state/'corrected-oracles';dest.mkdir(exist_ok=True);targets=dest/'targets';targets.mkdir(exist_ok=True)
    tasks=[];support=[]
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
        for fi,fold in enumerate(d['folds'],1):
            indices=fold['calendar'];active=d['ready'][indices]&np.array([s in fold['active'] for s in d['symbols']])[None,:]
            for name in ('DIRECTIONAL_ORACLE','EXPERT_ORACLE','CROSS_SECTIONAL_RANK_ORACLE'):
                new,valid=oracle_weights(name,d['utility'][scenario][indices],d['relative'][indices],d['close'],indices,active,d['sma'][indices])
                mapping='NEUTRAL' if name=='CROSS_SECTIONAL_RANK_ORACLE' else 'DIRECTIONAL'
                old_path=state/'targets'/f'{tag}_fold{fi}_{name}_NONCAUSAL_{mapping}.npz'
                with np.load(old_path) as f:dates=f['decision_us'];old=f['weights'];assert f['symbol_order'].tolist()==d['symbols']
                target=targets/old_path.name
                if target.exists():
                    with np.load(target) as f:assert np.array_equal(f['weights'],new)
                else:np.savez_compressed(target,decision_us=dates,weights=new,symbol_order=np.array(d['symbols']))
                for old_task in (t for t in original if t['family']==name and t['window']['fold']==fi and t['funding_scale']==(1. if scenario==0 else .01)):
                    reused=same_executed_targets(dates,old,new,old_task['window'])
                    task=dict(old_task) if reused else dict(old_task,state=str(dest),target_path=str(target),target_sha256=sha(target))
                    tasks.append(dict(task=task,reused_original=reused))
                    mask=(dates>=task['window']['start'])&(dates<task['window']['end']);v=valid[mask];eligible=active[mask]
                    support.append(dict(window=task['window']['id'],funding_scale=task['funding_scale'],oracle=name,
                                        information_horizon_days=60 if name=='EXPERT_ORACLE' else 30,
                                        supported_asset_days=int(v.sum()),eligible_asset_days=int(eligible.sum()),
                                        fully_supported_days=int(((v==eligible).all(1)&eligible.any(1)).sum()),required_days=task['window']['days'],
                                        terminal_paid_cash_day=True,reused_identical_account=reused))
    assert len(tasks)==36
    atomic(dest/'TASKS.json',dict(tasks=tasks,support=support,protocol_sha256=sha(proto),candidate_freeze_sha256=sha(state/'LOCKED_CANDIDATE_FREEZE.json')))
    return tasks,support

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True)
    p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);p.add_argument('--workers',type=int,default=10)
    a=p.parse_args();state=Path(a.state);path=state/'DEV_ORACLE_RESULTS.json'
    if path.exists():
        result=json.loads(path.read_text());assert result['status']=='COMPLETE' and not result['errors'];return
    tasks,support=prepare(a);results=[];errors=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(native_worker,item['task']):item for item in tasks}
        for future in concurrent.futures.as_completed(futures):
            item=futures[future]
            try:results.append(future.result())
            except Exception as exc:
                try:results.append(pool.submit(native_worker,item['task']).result())
                except Exception as retry:errors.append(dict(id=item['task']['id'],error=str(exc),retry_error=str(retry)))
            atomic(state/'development-oracles-progress.json',dict(stage='HORIZON_SUPPORT_DIAGNOSTICS_ONLY',completed=len(results),failed=len(errors),total=36,updated_at=time.time()))
            print(f'CORRECTED ORACLES {len(results)}/36 failed={len(errors)}',flush=True)
    atomic(path,dict(status='COMPLETE' if not errors else 'FAILED',rows=[compact_case(r) for r in results],support=support,errors=errors,
                     total=36,reused_identical_accounts=sum(i['reused_original'] for i in tasks),
                     role='NONCAUSAL_NONDEPLOYABLE_DIAGNOSTICS_ONLY',locked_read=False,no_candidate_or_gate_change=True,
                     candidate_freeze_sha256=sha(state/'LOCKED_CANDIDATE_FREEZE.json'),tasks_sha256=sha(state/'corrected-oracles/TASKS.json')))
    if errors:raise RuntimeError('Diagnostic errors preserved; no locked release')

if __name__=='__main__':main()
