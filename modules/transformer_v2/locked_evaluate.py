"""One released locked experiment. Fixed models only; no ranking or refitting here."""
import argparse,concurrent.futures,json,multiprocessing,os,time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from .train import atomic,sha,infer,Samples,predict_forward
from .data import load_development,causal_future_targets
from .evaluate import DAY,portfolio_targets,prediction_metrics,native_worker
from .portfolio import directional,market_neutral
from .locked_gate import require_release

def permit_pre_account_engineering_repair(state,proof_path):
    state=Path(state);proof_path=Path(proof_path);proof=json.loads(proof_path.read_text())
    failure=json.loads((state/'LOCKED_FORMAL_FAILURE.json').read_text())
    assert proof['reason']=='ENGINEERING_PRE_ACCOUNT_ONLY' and not proof['economic_results_read'] and not proof['model_ranking_read']
    assert not failure['economic_results_read'] and proof['failure_sha256']==sha(state/'LOCKED_FORMAL_FAILURE.json')
    assert proof['previous_formal_marker_sha256']==sha(state/'LOCKED_FORMAL_RUN.json')
    assert not (state/'LOCKED_NATIVE_PROGRESS_RESULTS.json').exists() and not (state/'TRANSFORMER_V2_LOCKED_RESULTS.json').exists()
    assert not any((state/'locked-native').rglob('summary.json')) and not any((state/'locked-native').rglob('RESULT.json'))
    assert not (state/'LOCKED_FORMAL_PRE_ACCOUNT_ATTEMPT.json').exists(),'Only one explicitly proven engineering repair'
    (state/'LOCKED_FORMAL_RUN.json').rename(state/'LOCKED_FORMAL_PRE_ACCOUNT_ATTEMPT.json')
    (state/'LOCKED_FORMAL_FAILURE.json').rename(state/'LOCKED_FORMAL_PRE_ACCOUNT_FAILURE.json')
    atomic(state/'LOCKED_ENGINEERING_REPAIR_ACCEPTED.json',dict(proof_sha256=sha(proof_path),proof=proof,accepted_at=time.time(),no_economic_account_results_exist=True))

def baseline_weights(name,sma,active,gross=None):
    position=dict(BASE_HOLD=np.ones_like(sma),BASE_SMA200_SIGNED=sma,
                  BASE_STATIC_DIRECTION3=.5*sma+.25,BASE_CASH=np.zeros_like(sma))[name]
    position=np.where(np.isfinite(position),position,0.)*active
    if gross is None:return position*.6/np.maximum(active.sum(1,keepdims=True),1)
    budget=np.asarray(gross)[:,None];assert np.isfinite(budget).all() and (budget>=0).all() and (budget<=.6+1e-9).all()
    denom=abs(position).sum(1,keepdims=True)
    weight=np.divide(position*budget,denom,out=np.zeros_like(position),where=denom>0)
    # Preserve the observed baseline direction/magnitude ratios, respecting the
    # unchanged asset cap. Sparse signals may make the exact budget infeasible.
    weight=np.clip(weight,-.3,.3)
    for _ in range(position.shape[1]):
        residual=np.maximum(0.,budget-abs(weight).sum(1,keepdims=True))
        free=(abs(weight)<.3-1e-12)&(position!=0);basis=abs(position)*free;total=basis.sum(1,keepdims=True)
        increment=np.divide(basis*residual,total,out=np.zeros_like(basis),where=total>0)
        weight=np.clip(weight+np.sign(position)*increment,-.3,.3)
    assert abs(weight).sum(1).max(initial=0)<=.6+1e-9 and abs(weight).max(initial=0)<=.3+1e-9
    return weight

def build_features(a):
    state=Path(a.state);repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    require_release(state,sha(proto));manifest=json.loads((state/'LOCKED_DATA_MANIFEST.json').read_text())
    assert manifest['status']=='COMPLETE184DAY_ACTUAL_INPUTS'
    for artifact in manifest['artifacts']:assert sha(artifact['path'])==artifact['sha256']
    d=load_development(a.collector_root,a.work,a.source_run)
    from pipeline.make_labels import feature_frame,BASE_FEATURES
    from pipeline.train import market_features
    base=Path(manifest['work'])/'data/normalized';frames={};features={}
    for symbol in d['symbols']:
        frame=pd.read_parquet(base/f'{symbol}_daily.parquet').reset_index(drop=True);frames[symbol]=frame
        f=feature_frame(frame,256);f['feature_ready']&=f.dt>=pd.Timestamp('2022-09-01',tz='UTC');features[symbol]=f
    dates=pd.DatetimeIndex(features[d['symbols'][0]].dt)
    assert dates.max()==pd.Timestamp('2026-08-31',tz='UTC') and dates.is_unique
    assert all(pd.DatetimeIndex(f.dt).equals(dates) for f in features.values())
    market=market_features(features).reset_index(drop=True)
    x=np.stack([pd.concat([features[s][BASE_FEATURES],market],axis=1).to_numpy('float32') for s in d['symbols']],1)
    assert np.allclose(x[:len(d['x'])],d['x'],equal_nan=True,rtol=1e-6,atol=1e-7),'Past feature recipe changed'
    n=len(dates);past=len(d['dates']);extra=n-past
    d.update(dates=dates,x=x,availability=np.stack([np.isfinite(features[s].close) for s in d['symbols']],1),
             ready=np.stack([features[s].feature_ready for s in d['symbols']],1),
             sma=np.stack([features[s].sma_signal.to_numpy(float) for s in d['symbols']],1),
             close=np.stack([features[s].close.to_numpy(float) for s in d['symbols']],1))
    d['utility']=[np.concatenate([v,np.full((extra,len(d['symbols']),2),np.nan)],0) for v in d['utility']]
    d['relative']=np.concatenate([d['relative'],np.full((extra,len(d['symbols']),3),np.nan)],0)
    d['regime']=np.concatenate([d['regime'],np.full((extra,3),np.nan)],0)
    indices=np.flatnonzero((dates>=pd.Timestamp('2026-02-28',tz='UTC'))&(dates<pd.Timestamp('2026-08-31',tz='UTC')))
    assert len(indices)==184 and np.array_equal(dates[indices].as_unit('us').asi8+DAY,np.arange(1772323200000000,1788220800000000,DAY))
    return d,indices,frames,manifest

def old_predictions(d,indices,study,name):
    from pipeline.models import build_model,transform
    folder=Path(study)/'models/fold5'/name;checkpoint=json.loads((folder/'CHECKPOINT.json').read_text())
    for entry in checkpoint['models']:assert sha(folder/entry['name'])==entry['sha256']
    with np.load(folder/'scaler.npz') as f:scaler=(f['mu'],f['sd'])
    if name=='PER_ASSET_XGB':
        from xgboost import XGBRegressor
        y=np.empty((len(indices),len(d['symbols']),2),np.float32)
        for sid,symbol in enumerate(d['symbols']):
            x=transform(d['x'][indices,sid],*scaler)
            for head in range(2):
                model=XGBRegressor();model.load_model(folder/f'{symbol}_head{head}.json');y[:,sid,head]=model.predict(x)
    else:
        network=build_model('TRANSFORMER_SHARED',48,len(d['symbols']),256).cuda()
        network.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));network.eval()
        loader=torch.utils.data.DataLoader(Samples(d,indices,0,np.ones(len(d['symbols']),bool),scaler,(np.ones(2),np.zeros(3),np.ones(3))),batch_size=32,shuffle=False,num_workers=2)
        out=[]
        with torch.no_grad():
            for batch in loader:out.append(predict_forward(network,[v.cuda() for v in batch],True)['utility'][:,0].cpu().numpy())
        y=np.concatenate(out);del network;torch.cuda.empty_cache()
    assert np.isfinite(y).all()
    return dict(utility=y,relative=np.repeat((-y[...,1])[...,None],3,-1)),dict(checkpoint_sha256=sha(folder/'CHECKPOINT.json'),source_folder=str(folder),stale_last_development_fold=True)

def prepare(a):
    state=Path(a.state);repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json';protocol=json.loads(proto.read_text())
    require_release(state,sha(proto));final=json.loads((state/'FINAL_FITS.json').read_text());assert final['status']=='COMPLETE'
    d,indices,frames,manifest=build_features(a);sma=d['sma'][indices];finalplan=json.loads((state/'FINAL_FIT_PLAN.json').read_text())
    active=d['ready'][indices]&np.array(finalplan['tasks'][0]['active'])[None,:];assert active.shape==(184,10)
    assert all(t['active']==finalplan['tasks'][0]['active'] for t in finalplan['tasks'])
    predictions={};proofs=[];dest=state/'locked-predictions';dest.mkdir(exist_ok=True)
    assert torch.cuda.is_available(),'Locked inference requires CUDA';torch.set_num_threads(len(os.sched_getaffinity(0)))
    for fit in final['results']:
        task=fit['task'];folder=Path(fit['folder']);assert sha(folder/'weights.pt')==fit['result']['weights_sha256'] and sha(folder/'scaler.npz')==fit['result']['scaler_sha256']
        path=dest/f'{task["tag"]}_{task["family"]}_{task["seed"]}.npz'
        if path.exists():
            with np.load(path) as f:pred={k:f[k].copy() for k in f.files}
        else:
            pred=infer(d,indices,task['scenario'],np.array(task['active']),task['family'],folder)
            # infer's fixed weights are untouched; exported predictions are external.
            (folder/'PREDICTIONS.npz').rename(path)
        assert np.array_equal(pred['indices'],indices) and np.isfinite(pred['utility']).all() and np.isfinite(pred['relative']).all()
        predictions[task['tag'],task['family'],str(task['seed'])]=pred
        proofs.append(dict(path=str(path),sha256=sha(path),weights_sha256=fit['result']['weights_sha256']))
    for tag in ('raw_fraction','raw_percent'):
        study=json.loads(Path(a.source_run,tag,'RESEARCH.json').read_text())['study_dir']
        for original,name in [('TRANSFORMER_SHARED','OLD_FROZEN_TRANSFORMER_SHARED'),('PER_ASSET_XGB','PER_ASSET_XGB')]:
            pred,proof=old_predictions(d,indices,study,original);predictions[tag,name,'FROZEN_LEGACY']=pred;proofs.append(dict(tag=tag,family=name,**proof))
        for family in protocol['models']:
            predictions[tag,family,'ENSEMBLE']={k:np.mean([predictions[tag,family,str(seed)][k] for seed in protocol['seeds']],0) for k in ('utility','relative')}
    atomic(state/'LOCKED_PREDICTIONS_FROZEN.json',dict(protocol_sha256=sha(proto),locked_data_manifest_sha256=sha(state/'LOCKED_DATA_MANIFEST.json'),files=proofs,
               chosen=json.loads((state/'LOCKED_CANDIDATE_FREEZE.json').read_text())['chosen'],no_locked_labels_used_for_fitting=True))
    # Future labels are diagnostic only, built after every prediction is frozen.
    relative,regime=causal_future_targets(d['close'],d['ready']);utility=[]
    from pipeline.economics import continuous_expert_returns
    from pipeline.make_labels import future_compound
    for scale in (1.,.01):
        own=[]
        for sid,symbol in enumerate(d['symbols']):
            returns={name:future_compound(continuous_expert_returns(frames[symbol],signal,.30,scale,.00135),60).to_numpy(float) for name,signal in
                     [('sma',d['sma'][:,sid]),('hold',np.ones(len(d['dates']))),('cash',np.zeros(len(d['dates'])))]}
            own.append(np.stack([returns['sma']-returns['hold'],returns['cash']-returns['hold']],-1))
        utility.append(np.stack(own,1)[indices])
    tasks=[];metrics=[];targets=state/'locked-targets';targets.mkdir(exist_ok=True)
    window=dict(id='LOCKED_20260301_20260831',start=1772323200000000,end=1788220800000000,days=184,fold='LOCKED',active_symbols=[s for s,on in zip(d['symbols'],np.array(finalplan['tasks'][0]['active'])) if on])
    def add(tag,family,seed,mapping,weights,noncausal=False):
        path=targets/f'{tag}_{family}_{seed}_{mapping}.npz';weights=weights.copy();weights[-1]=0.
        if path.exists():
            with np.load(path) as f:assert np.array_equal(f['weights'],weights),'Frozen locked targets changed'
        else:np.savez_compressed(path,decision_us=d['dates'][indices].as_unit('us').asi8+DAY,weights=weights,symbol_order=np.array(d['symbols']))
        tasks.append(dict(id=f'{tag}/LOCKED/{family}/{seed}/{mapping}',state=str(state/'locked-native'),release_state=str(state),collector_root=a.collector_root,
                          work=manifest['work'],source_run=a.source_run,family=family,seed=str(seed),mapping=mapping,window=window,funding_scale=1. if tag=='raw_fraction' else .01,
                          target_path=str(path),target_sha256=sha(path),protocol_sha256=sha(proto),noncausal=noncausal))
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
        for (own_tag,family,seed),pred in predictions.items():
            if own_tag!=tag:continue
            metric=prediction_metrics(pred,utility[scenario],relative[indices],active);metric.update(family=family,seed=seed,funding_scale=1. if scenario==0 else .01);metrics.append(metric)
            for mapping in (('DIRECTIONAL',) if seed=='FROZEN_LEGACY' else ('DIRECTIONAL','NEUTRAL','COMBINED')):
                add(tag,family,seed,mapping,portfolio_targets(pred,sma,active,mapping))
        for name in ('BASE_CASH','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3'):add(tag,name,'FROZEN_RULE','DIRECTIONAL',baseline_weights(name,sma,active))
        chosen=json.loads((state/'LOCKED_CANDIDATE_FREEZE.json').read_text())['chosen']
        chosen_weights=portfolio_targets(predictions[tag,chosen['family'],'ENSEMBLE'],sma,active,chosen['mapping']);gross=np.abs(chosen_weights).sum(1)
        for name in ('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3'):add(tag,'EXPOSURE_MATCHED_'+name,'FROZEN_RULE','DIRECTIONAL',baseline_weights(name,sma,active,gross))
        from .oracles import weights as oracle_weights
        y=utility[scenario];rel=relative[indices];support={}
        for name in ('DIRECTIONAL_ORACLE','EXPERT_ORACLE','CROSS_SECTIONAL_RANK_ORACLE'):
            weights,oracle_active=oracle_weights(name,y,rel,d['close'],indices,active,sma)
            add(tag,name,'NONCAUSAL','NEUTRAL' if name=='CROSS_SECTIONAL_RANK_ORACLE' else 'DIRECTIONAL',weights,True)
            support[name]=dict(information_horizon_days=60 if name=='EXPERT_ORACLE' else 30,supported_asset_days=int(oracle_active.sum()),eligible_asset_days=int(active.sum()),
                               fully_supported_days=int(((oracle_active==active).all(1)&active.any(1)).sum()),required_days=184)
        atomic(state/f'LOCKED_ORACLE_SUPPORT_{tag}.json',dict(oracles=support,terminal_missing_horizon_cash=True,not_a_tight_full_calendar_upper_bound=True))
    atomic(state/'LOCKED_PREDICTION_METRICS.json',dict(rows=metrics,diagnostic_labels_only=True))
    atomic(state/'LOCKED_NATIVE_TASKS.json',dict(tasks=tasks,protocol_sha256=sha(proto),formal_experiment=1,targets_frozen_before_native_results=True))
    return tasks

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True)
    p.add_argument('--source-run',required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--engineering-repair-proof');a=p.parse_args();state=Path(a.state)
    repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json';require_release(state,sha(proto))
    marker=state/'LOCKED_FORMAL_RUN.json'
    if marker.exists():
        if not a.engineering_repair_proof:raise RuntimeError('Formal locked experiment already started. No automatic second run, outcome-driven repair, or silent resume.')
        permit_pre_account_engineering_repair(state,a.engineering_repair_proof)
    atomic(marker,dict(status='FORMAL_RUN_STARTED',protocol_sha256=sha(proto),source_sha256=sha(__file__),started_at=time.time(),economic_results_read=False,model_ranking_read=False))
    try:
        manifest=json.loads((state/'LOCKED_DATA_MANIFEST.json').read_text())
        if manifest['status']!='COMPLETE184DAY_ACTUAL_INPUTS':
            atomic(state/'TRANSFORMER_V2_LOCKED_RESULTS.json',dict(status='NOT_EVALUABLE_INCOMPLETE_LOCKED_CALENDAR',cases=[],errors=[],data_audit=manifest['audit'],promotion=False,protocol_sha256=sha(proto)));return
        tasks=prepare(a);results=[];errors=[]
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            futures={pool.submit(native_worker,task):task for task in tasks}
            for future in concurrent.futures.as_completed(futures):
                task=futures[future]
                try:results.append(future.result())
                except Exception as exc:errors.append(dict(task_id=task['id'],error=str(exc),automatic_retry=False))
                atomic(state/'locked-economic-progress.json',dict(stage='LOCKED_NATIVE_ACCOUNTS',completed=len(results),failed=len(errors),total=len(tasks),updated_at=time.time(),pid=os.getpid()))
                atomic(state/'LOCKED_NATIVE_PROGRESS_RESULTS.json',dict(cases=results,errors=errors,total=len(tasks)))
                print(f'LOCKED NATIVE {len(results)}/{len(tasks)} failed={len(errors)} {task["id"]}',flush=True)
        atomic(state/'TRANSFORMER_V2_LOCKED_RESULTS.json',dict(status='COMPLETE_ONE_FORMAL_LOCKED_EXPERIMENT' if not errors else 'FAILED_ONE_FORMAL_LOCKED_EXPERIMENT_NO_RERUN',
                    cases=results,errors=errors,total_cases=len(tasks),protocol_sha256=sha(proto),formal_run=1,predictions_sha256=sha(state/'LOCKED_PREDICTIONS_FROZEN.json'),
                    tasks_sha256=sha(state/'LOCKED_NATIVE_TASKS.json'),no_outcome_driven_selection=True,investment_state='NONE/CASH'))
    except BaseException as exc:
        atomic(state/'LOCKED_FORMAL_FAILURE.json',dict(error=str(exc),time=time.time(),economic_results_read=(state/'LOCKED_NATIVE_PROGRESS_RESULTS.json').exists(),no_automatic_rerun=True));raise

if __name__=='__main__':main()
