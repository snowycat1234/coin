"""Frozen portfolio adapter to the existing minute wallet and reference auditor."""
import argparse,concurrent.futures,json,multiprocessing,os,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.stats import spearmanr
from .train import atomic,sha
from .portfolio import directional,market_neutral
from .data import load_development

DAY=86_400_000_000

def prediction_metrics(pred,y,relative,active):
    use=np.isfinite(y)&active[...,None];errors=(pred['utility']-np.where(use,y,0.))**2
    mse=float(errors[use].mean()) if use.any() else None
    scores=pred['relative'][...,1];ic=[];hits=[];utility_rank=[]
    for i in range(len(scores)):
        mask=np.isfinite(relative[i,:,1])&active[i]&np.isfinite(scores[i])
        if mask.sum()>=4 and np.ptp(scores[i,mask])>1e-12 and np.ptp(relative[i,mask,1])>1e-12:
            ic.append(float(spearmanr(scores[i,mask],relative[i,mask,1]).statistic))
            delta=relative[i,mask,1,None]-relative[i,mask,1][None,:]
            estimated=scores[i,mask,None]-scores[i,mask][None,:];pairs=np.triu(np.abs(delta)>1e-12,1)
            if pairs.any():hits.append(float((np.sign(delta[pairs])==np.sign(estimated[pairs])).mean()))
        for a in np.flatnonzero(active[i]&np.isfinite(y[i]).all(1)):
            actual=[y[i,a,0],0.,y[i,a,1]];estimate=[pred['utility'][i,a,0],0.,pred['utility'][i,a,1]]
            if np.ptp(actual)>1e-12 and np.ptp(estimate)>1e-12:utility_rank.append(float(spearmanr(actual,estimate).statistic))
    return dict(outer_utility_MSE=mse,rank_IC_median=float(np.median(ic)) if ic else None,
                Spearman_mean=float(np.mean(ic)) if ic else None,cross_sectional_hit_rate=float(np.mean(hits)) if hits else None,
                utility_rank=float(np.mean(utility_rank)) if utility_rank else None,valid_IC_days=len(ic),outer_labels_used_for_diagnostics_only=True)

def portfolio_targets(pred,sma,active,mapping):
    direct=directional(pred['utility'],sma,active)
    neutral=market_neutral(pred['relative'][...,1],active)
    return dict(DIRECTIONAL=direct,NEUTRAL=neutral,COMBINED=.5*(direct+neutral))[mapping]

def native_worker(task):
    repo=Path(__file__).resolve().parents[2]
    os.environ.setdefault('POLARS_MAX_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
    from modules.collector_research.validation import runtime
    state=Path(task['state'])
    if task['window']['end']>1772323200000000:
        from .locked_gate import require_release
        require_release(task.get('release_state',state),task['protocol_sha256'])
    runtime.configure(SimpleNamespace(collector_root=task['collector_root'],collector_work=task['work'],source_run=task['source_run'],
        run_dir=state/'native-control',resource_policy='server',workers=1,minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation.data import market_window,Reporter,engine,independent,USDTLinearPerpetualAccount,saved_case_valid
    import polars as pl
    base=state/'native'/task['id'];result_path=base/'RESULT.json';base.mkdir(parents=True,exist_ok=True)
    binding=dict(protocol_sha256=task['protocol_sha256'],target_sha256=task['target_sha256'],
        evaluation_source_sha256=sha(Path(__file__)),native_financial_source_sha256={str(p.relative_to(repo)):sha(p)
        for p in sorted((repo/'src/quant').glob('*.py'))+sorted((repo/'scripts/investment').glob('*.py'))})
    if result_path.exists():
        result=json.loads(result_path.read_text());saved_case_valid(result,binding);return result
    attempts=list(base.glob('attempt-*'))
    if len(attempts)>=2:raise RuntimeError('At most one automatic retry; inspect failed case')
    attempt=base/f'attempt-{len(attempts)+1}';attempt.mkdir()
    try:
        path=Path(task['target_path']);assert sha(path)==task['target_sha256']
        with np.load(path,allow_pickle=False) as f:dates=f['decision_us'];weights=f['weights'];symbols=f['symbol_order'].tolist()
        window=task['window'];sel=(dates>=window['start'])&(dates<window['end']);dates=dates[sel];weights=weights[sel].copy()
        assert np.array_equal(dates,np.arange(window['start'],window['end'],DAY))
        assert np.isfinite(weights).all() and np.abs(weights).sum(1).max()<=.6+1e-9 and np.abs(weights).max()<=.3+1e-9
        weights[-1]=0.
        targets=pl.DataFrame(dict(available_us=np.repeat(dates,len(symbols)),symbol=symbols*len(dates),target_weight=weights.reshape(-1)))
        inputs=market_window(symbols,window['start'],window['end']);blocks=inputs['minute_blocks']
        def complete_blocks():
            for block in blocks():
                assert set(window['active_symbols'])<=set(block['market']),'Unexpected gap in frozen common window'
                yield block
        inputs['minute_blocks']=complete_blocks
        def factory(bars,decisions,mode):
            assert np.array_equal(decisions,dates)
            return targets,dict(source='FROZEN_V2_SEED_OR_ENSEMBLE',mapping=task['mapping'],noncausal=task.get('noncausal',False),
                                native_initial_capital=10000,no_spliced_return=True)
        reporter=Reporter(base/'progress.json',task['id'])
        scale=task['funding_scale']
        case=engine.simulate(inputs,'LONG_SHORT',engine.COSTS[0],dict(id='RAW_AS_FRACTION' if scale==1 else 'RAW_AS_PERCENT',scale=scale),
            reporter,runtime.kernel_guard,target_factory=factory,account_factory=USDTLinearPerpetualAccount,persist_cash_close=True)
        directory=attempt/'account';saved=engine.save_case(case,directory);atomic(directory/'summary.json',saved['summary'])
        del case,inputs,targets
        audit=independent.verify(directory,symbols,scale);atomic(attempt/'INDEPENDENT_AUDIT.json',audit)
        summary=saved['summary'];value=dict(binding=binding,task=task,summary=summary,artifacts=saved['artifacts'],independent_audit=audit,
            summary_path=str(directory/'summary.json'),summary_sha256=sha(directory/'summary.json'),
            independent_audit_path=str(attempt/'INDEPENDENT_AUDIT.json'),independent_audit_sha256=sha(attempt/'INDEPENDENT_AUDIT.json'),
            economic_calendar_complete=summary['completed_minutes']==summary['required_minutes'],terminal_cash_realized=summary['terminal_cash_realized'])
        atomic(result_path,value);return value
    except BaseException as exc:atomic(attempt/'FAILURE.json',dict(error=str(exc),error_type=type(exc).__name__));raise

def prepare(a):
    state=Path(a.state);repo=Path(__file__).resolve().parents[2]
    protocol_path=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json';protocol=json.loads(protocol_path.read_text())
    d=load_development(a.collector_root,a.work,a.source_run)
    plan=json.loads(Path(a.complete_run,'VALIDATION_PLAN.json').read_text())
    tasks=[];metrics=[];targets=state/'targets';targets.mkdir(exist_ok=True)
    def add(folder,family,seed,tag,fi,pred,active,mapping,noncausal=False,explicit_weights=None):
        indices=d['folds'][fi-1]['calendar'];weights=portfolio_targets(pred,d['sma'][indices],active,mapping) if explicit_weights is None else explicit_weights
        dest=targets/f'{tag}_fold{fi}_{family}_{seed}_{mapping}.npz'
        if not dest.exists():np.savez_compressed(dest,decision_us=d['dates'][indices].as_unit('us').asi8+DAY,weights=weights,symbol_order=np.array(d['symbols']))
        else:
            with np.load(dest) as old:assert np.array_equal(old['weights'],weights),'Frozen targets changed'
        for window in (w for w in plan['windows'] if w['fold']==fi):
            tasks.append(dict(id=f'{tag}/{window["id"]}/{family}/{seed}/{mapping}',state=str(state),collector_root=a.collector_root,
                work=a.work,source_run=a.source_run,family=family,seed=str(seed),mapping=mapping,window=window,
                funding_scale=1. if tag=='raw_fraction' else .01,target_path=str(dest),target_sha256=sha(dest),protocol_sha256=sha(protocol_path),noncausal=noncausal))
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
      for fi,fold in enumerate(d['folds'],1):
        active=d['ready'][fold['calendar']]&np.array([s in fold['active'] for s in d['symbols']])[None,:]
        for family in protocol['models']:
            predictions=[]
            for seed in protocol['seeds']:
                folder=state/'fits'/tag/f'fold{fi}'/family/f'seed{seed}'
                fit=json.loads((folder/'FIT_COMPLETE.json').read_text());assert sha(folder/'refit/PREDICTIONS.npz')==fit['prediction_sha256']
                with np.load(folder/'refit/PREDICTIONS.npz') as f:pred={k:f[k].copy() for k in f.files}
                predictions.append(pred);metric=prediction_metrics(pred,d['utility'][scenario][fold['calendar']],d['relative'][fold['calendar']],active)
                metric.update(family=family,seed=seed,fold=fi,funding_scale=1. if scenario==0 else .01,
                    inner_val_loss=json.loads((folder/'inner/RESULT.json').read_text())['inner_validation_loss'])
                metrics.append(metric)
                for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):add(folder,family,seed,tag,fi,pred,active,mapping)
            ensemble={k:np.mean([p[k] for p in predictions],axis=0) for k in ('utility','relative','utility_pool','relative_pool')}
            metric=prediction_metrics(ensemble,d['utility'][scenario][fold['calendar']],d['relative'][fold['calendar']],active)
            metric.update(family=family,seed='ENSEMBLE',fold=fi,funding_scale=1. if scenario==0 else .01);metrics.append(metric)
            for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):add(None,family,'ENSEMBLE',tag,fi,ensemble,active,mapping)
            if family!='TRANSFORMER_SHARED':
                for pool,name in enumerate(('CLS','ATTENTION','LAST')):
                    pooled=dict(utility=ensemble['utility_pool'][:,pool],relative=ensemble['relative_pool'][:,pool])
                    add(None,family,'ENSEMBLE_POOL_'+name,tag,fi,pooled,active,'DIRECTIONAL')
        # Future-informed diagnostics are never added to causal model rankings.
        indices=fold['calendar'];y=d['utility'][scenario][indices]
        for name in ('DIRECTIONAL_ORACLE','EXPERT_ORACLE','CROSS_SECTIONAL_RANK_ORACLE'):
            u=np.where(np.isfinite(y),y,0.);rel=np.where(np.isfinite(d['relative'][indices]),d['relative'][indices],0.)
            if name=='DIRECTIONAL_ORACLE':
                future=d['close'][np.minimum(indices+30,len(d['close'])-1)]/d['close'][indices]-1
            pred=dict(utility=u,relative=rel)
            oracle_active=active&np.isfinite(y).all(-1)&np.isfinite(d['relative'][indices,:,1])
            if name=='DIRECTIONAL_ORACLE':
                weight=np.sign(np.where(np.isfinite(future),future,0.))*oracle_active*.6/np.maximum(oracle_active.sum(1,keepdims=True),1)
            elif name=='EXPERT_ORACLE':
                chosen=np.argmax(np.stack([u[...,0],np.zeros_like(u[...,0]),u[...,1]],-1),axis=-1)
                position=np.where(chosen==0,np.where(np.isfinite(d['sma'][indices]),d['sma'][indices],0.),np.where(chosen==1,1.,0.))
                weight=position*oracle_active*.6/np.maximum(oracle_active.sum(1,keepdims=True),1)
            else:weight=market_neutral(rel[...,1],oracle_active)
            add(None,name,'NONCAUSAL',tag,fi,pred,oracle_active,'NEUTRAL' if name=='CROSS_SECTIONAL_RANK_ORACLE' else 'DIRECTIONAL',True,weight)
    atomic(state/'PREDICTION_METRICS.json',dict(rows=metrics,locked_read=False))
    atomic(state/'NATIVE_TASKS.json',dict(status='FROZEN_BEFORE_V2_NATIVE_RESULTS',tasks=tasks,protocol_sha256=sha(protocol_path)))
    return tasks

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True)
    p.add_argument('--source-run',required=True);p.add_argument('--complete-run',required=True);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();state=Path(a.state);progress=state/'FIT_PROGRESS.json'
    while True:
        training=json.loads(progress.read_text()) if progress.exists() else {}
        if training.get('status')=='COMPLETE':break
        import subprocess
        unit=subprocess.check_output(['systemctl','show','coin-transformer-v2-train-20261007','-p','ActiveState','--value'],text=True).strip()
        if unit not in ('active','activating'):raise RuntimeError('Training service not live; no silent restart')
        atomic(state/'economic-progress.json',dict(stage='WAIT_VERIFIED_LIVE_TRAINING',completed_fits=training.get('completed',0),total_fits=120,pid=os.getpid(),updated_at=time.time()))
        time.sleep(15)
    tasks=prepare(a);completed=[];errors=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(native_worker,t):t for t in tasks}
        for f in concurrent.futures.as_completed(futures):
            task=futures[f]
            try:completed.append(f.result())
            except Exception as exc:
                # One retry is allowed by the per-case immutable attempt directory.
                try:completed.append(pool.submit(native_worker,task).result())
                except Exception as retry:errors.append(dict(task_id=task['id'],error=str(exc),retry_error=str(retry)))
            atomic(state/'NATIVE_DEV_RESULTS.json',dict(status='RUNNING',cases=completed,errors=errors,total_cases=len(tasks)))
            atomic(state/'economic-progress.json',dict(stage='DEV_NATIVE_ACCOUNTS',completed=len(completed),failed=len(errors),total=len(tasks),pid=os.getpid(),updated_at=time.time()))
            print(f'NATIVE {len(completed)}/{len(tasks)} failed={len(errors)} {task["id"]}',flush=True)
    atomic(state/'NATIVE_DEV_RESULTS.json',dict(status='COMPLETE' if not errors else 'FAILED',cases=completed,errors=errors,total_cases=len(tasks)))
    if errors:raise RuntimeError('Native errors preserved; inspect before continuing')

if __name__=='__main__':main()
