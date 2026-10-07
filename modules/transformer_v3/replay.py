"""Re-execute frozen v2 targets through the isolated-liquidation specialization.

Only byte-identical generated files are deduplicated against protected v2 via
read-only references after simulation. Every task still executes the new wallet.
"""
import argparse,concurrent.futures,json,multiprocessing,os,time,subprocess,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from modules.transformer_v2.train import atomic,sha

def same_complete_economics(old,new):
    keys=('NAV','net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','gross_fill_turnover_USDT','completed_minutes','required_minutes')
    return all(abs(old[k]-new[k])<=1e-7 for k in keys) and old['terminal_cash_realized']==new['terminal_cash_realized']

def freeze_sources(state):
    repo=Path(__file__).resolve().parents[2]
    paths=sorted((repo/'src/quant').glob('*.py'))+sorted((repo/'scripts/investment').glob('*.py'))+[Path(__file__).resolve()]
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    sources={}
    for p in paths:
        name=p.relative_to(repo).as_posix();digest=sha(p)
        committed=subprocess.check_output(['git','-C',str(repo),'show',head+':'+name])
        if hashlib.sha256(committed).hexdigest()!=digest:raise ValueError('Replay source must match committed HEAD: '+name)
        sources[name]=digest
    binding=dict(protocol_sha256=sha(state/'V2_REPLAY_PROTOCOL.json'),financial_and_replay_sources=sources)
    receipt=state/'REPLAY_SOURCE_BINDING.json'
    if receipt.exists():
        if json.loads(receipt.read_text())['binding']!=binding:raise ValueError('Frozen replay source changed; preserve and use a separately registered run')
    else:atomic(receipt,dict(binding=binding,committed_HEAD=head,frozen_at=time.time()))
    return binding

def replay_worker(task):
    os.environ.setdefault('POLARS_MAX_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
    from modules.collector_research.validation import runtime
    repo=Path(__file__).resolve().parents[2];state=Path(task['state']);dest=state/'native'/task['id'];dest.mkdir(parents=True,exist_ok=True)
    source=repo/'src/quant/bybit_isolated_account.py';proto=state/'V2_REPLAY_PROTOCOL.json'
    binding=dict(protocol_sha256=sha(proto),frozen_target_sha256=task['target_sha256'],
                 financial_sources={str(p.relative_to(repo)):sha(p) for p in sorted((repo/'src/quant').glob('*.py'))+sorted((repo/'scripts/investment').glob('*.py'))},
                 replay_source_sha256=sha(__file__))
    frozen=json.loads((state/'REPLAY_SOURCE_BINDING.json').read_text())['binding']
    actual=dict(binding['financial_sources']);actual['modules/transformer_v3/replay.py']=binding['replay_source_sha256']
    if frozen!=dict(protocol_sha256=binding['protocol_sha256'],financial_and_replay_sources=actual):raise ValueError('Worker sources changed after replay freeze')
    runtime.configure(SimpleNamespace(collector_root=task['collector_root'],collector_work=task['work'],source_run=task['source_run'],run_dir=state/'native-control',
                                      resource_policy='server',workers=1,minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation.data import market_window,Reporter,engine,independent,saved_case_valid
    from quant.bybit_isolated_account import BybitIsolatedAccount
    import polars as pl
    path=dest/'RESULT.json'
    if path.exists():
        result=json.loads(path.read_text());saved_case_valid(result,binding);return result
    attempts=list(dest.glob('attempt-*'))
    if len(attempts)>=2:raise RuntimeError('One retry only; preserve failed task')
    attempt=dest/f'attempt-{len(attempts)+1}';attempt.mkdir()
    try:
        assert sha(task['target_path'])==task['target_sha256']
        with np.load(task['target_path']) as f:dates=f['decision_us'];weights=f['weights'];symbols=f['symbol_order'].tolist()
        w=task['window'];select=(dates>=w['start'])&(dates<w['end']);dates=dates[select];weights=weights[select].copy();weights[-1]=0.
        assert np.array_equal(dates,np.arange(w['start'],w['end'],86_400_000_000))
        targets=pl.DataFrame(dict(available_us=np.repeat(dates,len(symbols)),symbol=symbols*len(dates),target_weight=weights.reshape(-1)))
        inputs=market_window(symbols,w['start'],w['end']);blocks=inputs['minute_blocks']
        def complete_blocks():
            for block in blocks():
                assert set(w['active_symbols'])<=set(block['market']);yield block
        inputs['minute_blocks']=complete_blocks
        def factory(_bars,decisions,_mode):
            assert np.array_equal(decisions,dates)
            return targets,dict(source='FROZEN_V2_SEED_OR_ENSEMBLE',mapping=task['mapping'],noncausal=task.get('noncausal',False),native_initial_capital=10000,no_spliced_return=True)
        case=engine.simulate(inputs,'LONG_SHORT',engine.COSTS[0],dict(id='RAW_AS_FRACTION' if task['funding_scale']==1 else 'RAW_AS_PERCENT',scale=task['funding_scale']),
                             Reporter(dest/'progress.json',task['id']),runtime.kernel_guard,target_factory=factory,account_factory=BybitIsolatedAccount,persist_cash_close=True)
        directory=attempt/'account';saved=engine.save_case(case,directory);atomic(directory/'summary.json',saved['summary']);del case,inputs,targets
        prior=json.loads(Path(task['prior_result']).read_text());reused=[]
        for name,e in saved['artifacts'].items():
            previous=prior['artifacts'].get(name)
            if previous and e['sha256']==previous['sha256']:
                assert sha(previous['path'])==previous['sha256']
                own=Path(e['path']);assert own.resolve().is_relative_to(attempt.resolve()) and own.is_file() and not own.is_symlink()
                own.unlink();own.symlink_to(Path(previous['path']))
                reused.append(name)
        audit=independent.verify(directory,symbols,task['funding_scale']);atomic(attempt/'INDEPENDENT_AUDIT.json',audit)
        summary=saved['summary'];was_complete=prior['economic_calendar_complete'] and prior['terminal_cash_realized']
        parity=same_complete_economics(prior['summary'],summary) if was_complete and summary['liquidation_count']==0 else None
        if parity is False:raise ValueError('Previously complete non-liquidating account changed economics; inspect before claiming replay')
        result=dict(binding=binding,task=task,summary=summary,artifacts=saved['artifacts'],independent_audit=audit,
                    summary_path=str(directory/'summary.json'),summary_sha256=sha(directory/'summary.json'),independent_audit_path=str(attempt/'INDEPENDENT_AUDIT.json'),
                    independent_audit_sha256=sha(attempt/'INDEPENDENT_AUDIT.json'),economic_calendar_complete=summary['completed_minutes']==summary['required_minutes'],
                    terminal_cash_realized=summary['terminal_cash_realized'],old_complete=was_complete,old_completion=prior['summary']['completion'],
                    nonliquidating_economic_parity=parity,generated_byte_identical_artifacts_reused=reused,
                    liquidation_semantics_role='BYBIT_STYLE_RESEARCH_WITH_UNCERTIFIED_LEGACY005_MMR; NO_NATIVE_RISK_SNAPSHOT_OR_INTRAMINUTE_CERTIFICATION')
        atomic(path,result);return result
    except BaseException as exc:atomic(attempt/'FAILURE.json',dict(error=str(exc),type=type(exc).__name__));raise

def prepare(state,v2):
    protocol=json.loads((state/'V2_REPLAY_PROTOCOL.json').read_text());original=json.loads((v2/'NATIVE_TASKS.json').read_text())['tasks'];tasks=[]
    assert len(original)==720
    for t in original:
        task=dict(t,state=str(state),prior_result=str(v2/'native'/t['id']/'RESULT.json'));tasks.append(task)
    for folder in ('development-exposure','corrected-oracles'):
        for item in json.loads((v2/folder/'TASKS.json').read_text())['tasks']:
            t=item.get('task',item);prior=Path(t['state'])/'native'/t['id']/'RESULT.json'
            tasks.append(dict(t,state=str(state),id=folder+'/'+t['id'],prior_result=str(prior)))
    import polars as pl
    legacy=json.loads(Path(protocol['complete_run'],'NATIVE_RESULTS.json').read_text())['cases']
    targets=state/'legacy-targets';targets.mkdir(exist_ok=True)
    for c in legacy:
        if c['model'] not in ('BASE_CASH','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3','TRANSFORMER_SHARED','PER_ASSET_XGB'):continue
        symbols=c['summary']['symbols'];artifact=c['artifacts']['targets.parquet'];assert sha(artifact['path'])==artifact['sha256']
        frame=pl.read_parquet(artifact['path']);dates=np.array(sorted(frame['available_us'].unique()))
        weights=[]
        for date in dates:
            records={r['symbol']:r['target_weight'] for r in frame.filter(pl.col('available_us')==date).iter_rows(named=True)}
            assert set(records)==set(symbols);weights.append([records[s] for s in symbols])
        name='OLD_FROZEN_TRANSFORMER_SHARED' if c['model']=='TRANSFORMER_SHARED' else c['model']
        tag='raw_fraction' if c['funding_scale']==1 else 'raw_percent';identifier=f'legacy-controls/{tag}/{c["window"]["id"]}/{name}'
        target=targets/(identifier.replace('/','_')+'.npz')
        if target.exists():
            with np.load(target) as f:assert np.array_equal(f['weights'],np.array(weights))
        else:np.savez_compressed(target,decision_us=dates,weights=np.array(weights),symbol_order=np.array(symbols))
        prior_path=state/'legacy-case-receipts'/f'{identifier.replace("/","_")}.json';prior_path.parent.mkdir(exist_ok=True)
        if not prior_path.exists():atomic(prior_path,c)
        tasks.append(dict(id=identifier,state=str(state),collector_root=protocol['collector_root'],work=protocol['work'],source_run=protocol['source_run'],
                          family=name,seed='FROZEN_LEGACY',mapping='DIRECTIONAL',window=c['window'],funding_scale=c['funding_scale'],
                          target_path=str(target),target_sha256=sha(target),prior_result=str(prior_path),noncausal=False))
    assert len(tasks)==864
    atomic(state/'V2_REPLAY_TASKS.json',dict(tasks=tasks,protocol_sha256=sha(state/'V2_REPLAY_PROTOCOL.json'),no_new_prediction_or_fit=True))
    return tasks

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);p.add_argument('--workers',type=int,default=10);p.add_argument('--probe-only',action='store_true');a=p.parse_args()
    state=Path(a.state);v2=Path(a.v2_state);freeze_sources(state);tasks=prepare(state,v2)
    if a.probe_only:
        tasks=[t for t in tasks if t['id'] in ('raw_fraction/fold5-2026-01-02/CROSS_ASSET_MULTITASK/ENSEMBLE/NEUTRAL','raw_percent/fold5-2026-01-02/CROSS_ASSET_MULTITASK/ENSEMBLE/NEUTRAL')]
        assert len(tasks)==2
    results=[];errors=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(replay_worker,t):t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            task=futures[future]
            try:results.append(future.result())
            except Exception as exc:
                try:results.append(pool.submit(replay_worker,task).result())
                except Exception as retry:errors.append(dict(id=task['id'],error=str(exc),retry_error=str(retry)))
            atomic(state/'replay-progress.json',dict(stage='FROZEN_V2_LIQUIDATION_REPLAY',completed=len(results),failed=len(errors),total=len(tasks),updated_at=time.time(),pid=os.getpid()))
            atomic(state/('PROBE_REPLAY_RESULTS.json' if a.probe_only else 'V2_REPLAY_PROGRESS_RESULTS.json'),dict(cases=results,errors=errors,total=len(tasks)))
            print(f'LIQUIDATION REPLAY {len(results)}/{len(tasks)} failed={len(errors)}',flush=True)
    atomic(state/('PROBE_REPLAY_RESULTS.json' if a.probe_only else 'V2_BYBIT_LIQUIDATION_REPLAY.json'),dict(status='COMPLETE' if not errors else 'FAILED',cases=results,errors=errors,total_cases=len(tasks),
          all_targets_frozen_v2=True,no_fits=True,risk_snapshot_certified=False,conditional_MMR=.005,protocol_sha256=sha(state/'V2_REPLAY_PROTOCOL.json')))
    if errors:raise RuntimeError('Replay failures preserved; no silent continuation')

if __name__=='__main__':main()
