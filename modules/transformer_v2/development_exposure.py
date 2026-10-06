"""Registered gross-budget controls for the frozen development candidate only."""
import argparse,concurrent.futures,json,multiprocessing,time
from pathlib import Path
import numpy as np
from .train import atomic,sha
from .data import load_development
from .evaluate import native_worker
from .locked_evaluate import baseline_weights
from .report import compact_case

def prepare(a):
    state=Path(a.state);repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    freeze=json.loads((state/'LOCKED_CANDIDATE_FREEZE.json').read_text());assert not freeze['locked_read'] and freeze['protocol_sha256']==sha(proto)
    d=load_development(a.collector_root,a.work,a.source_run);plan=json.loads(Path(a.complete_run,'VALIDATION_PLAN.json').read_text())
    dest=state/'development-exposure';dest.mkdir(exist_ok=True);targets=dest/'targets';targets.mkdir(exist_ok=True);tasks=[];chosen=freeze['chosen']
    for tag,scale in [('raw_fraction',1.),('raw_percent',.01)]:
        for fi,fold in enumerate(d['folds'],1):
            path=state/'targets'/f'{tag}_fold{fi}_{chosen["family"]}_ENSEMBLE_{chosen["mapping"]}.npz'
            with np.load(path) as f:dates=f['decision_us'];weights=f['weights'];assert f['symbol_order'].tolist()==d['symbols']
            active=d['ready'][fold['calendar']]&np.array([s in fold['active'] for s in d['symbols']])[None,:]
            gross=abs(weights).sum(1)
            for name in ('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3'):
                budget=baseline_weights(name,d['sma'][fold['calendar']],active,gross)
                target=targets/f'{tag}_fold{fi}_{name}.npz'
                if target.exists():
                    with np.load(target) as f:assert np.array_equal(f['weights'],budget)
                else:np.savez_compressed(target,decision_us=dates,weights=budget,symbol_order=np.array(d['symbols']))
                for window in (w for w in plan['windows'] if w['fold']==fi):
                    tasks.append(dict(id=f'{tag}/{window["id"]}/{name}',state=str(dest),collector_root=a.collector_root,work=a.work,source_run=a.source_run,
                                      family='EXPOSURE_MATCHED_'+name,seed='FROZEN_RULE',mapping='DIRECTIONAL',window=window,funding_scale=scale,
                                      target_path=str(target),target_sha256=sha(target),protocol_sha256=sha(proto),noncausal=False))
    assert len(tasks)==36
    atomic(dest/'TASKS.json',dict(tasks=tasks,candidate_freeze_sha256=sha(state/'LOCKED_CANDIDATE_FREEZE.json'),same_requested_gross_only=True,no_reselection=True))
    return tasks

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True)
    p.add_argument('--source-run',required=True);p.add_argument('--complete-run',required=True);p.add_argument('--workers',type=int,default=10);a=p.parse_args();state=Path(a.state)
    if (state/'DEV_EXPOSURE_RESULTS.json').exists():
        saved=json.loads((state/'DEV_EXPOSURE_RESULTS.json').read_text());assert saved['status']=='COMPLETE' and not saved['errors'];return
    tasks=prepare(a);results=[];errors=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(native_worker,t):t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            task=futures[future]
            try:results.append(future.result())
            except Exception as exc:
                try:results.append(pool.submit(native_worker,task).result())
                except Exception as retry:errors.append(dict(id=task['id'],error=str(exc),retry_error=str(retry)))
            atomic(state/'development-exposure-progress.json',dict(stage='FROZEN_CANDIDATE_GROSS_BUDGET_CONTROLS',completed=len(results),failed=len(errors),total=36,updated_at=time.time()))
            print(f'DEV EXPOSURE {len(results)}/36 failed={len(errors)}',flush=True)
    result=dict(status='COMPLETE' if not errors else 'FAILED',rows=[compact_case(r) for r in results],errors=errors,total=36,
                candidate_freeze_sha256=sha(state/'LOCKED_CANDIDATE_FREEZE.json'),tasks_sha256=sha(state/'development-exposure/TASKS.json'),
                diagnostic='Same contemporaneously observable requested gross; report realized differences; never change selected architecture, mapping or gate',locked_read=False)
    atomic(state/'DEV_EXPOSURE_RESULTS.json',result)
    if errors:raise RuntimeError('Exposure control engineering failures preserved; no locked release')

if __name__=='__main__':main()
