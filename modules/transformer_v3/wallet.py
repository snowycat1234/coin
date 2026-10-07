"""Frozen target adapter: existing engine + isolated specialization + lossless storage."""
import argparse,concurrent.futures,json,multiprocessing,os,time,subprocess,hashlib
from dataclasses import replace
from decimal import Decimal
from functools import partial
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from modules.transformer_v2.train import atomic,sha
from .storage import pack_case,hydrated_account
from .market_reference import prepare_reference
from .market_binding import prepare_binding,verify_binding
from .isolated_audit import verify as verify_isolated

DAY=86_400_000_000

def frozen_sources(state):
    repo=Path(__file__).resolve().parents[2]
    paths=sorted((repo/'src/quant').glob('*.py'))+sorted((repo/'scripts/investment').glob('*.py'))+[Path(__file__),Path(__file__).with_name('storage.py'),Path(__file__).with_name('market_reference.py'),Path(__file__).with_name('market_binding.py'),Path(__file__).with_name('isolated_audit.py')]
    sources={str(p.relative_to(repo)):sha(p) for p in paths};path=Path(state)/'WALLET_SOURCE_BINDING.json'
    for name,digest in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+name])).hexdigest()!=digest:raise ValueError('Wallet sources must be committed before execution: '+name)
    if path.exists():
        if json.loads(path.read_text())!=sources:raise ValueError('Frozen wallet or lossless codec changed; register a separate run')
    else:atomic(path,sources)
    return sources

def profile_account(config,*,profile,**kwargs):
    from quant.bybit_isolated_account import BybitIsolatedAccount
    if profile not in ('FULL','HALF'):raise ValueError('Only preregistered risk profiles')
    return BybitIsolatedAccount(replace(config,max_gross_weight=Decimal('.6') if profile=='FULL' else Decimal('.3')),**kwargs)

def native_worker(task):
    os.environ.setdefault('POLARS_MAX_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
    repo=Path(__file__).resolve().parents[2];state=Path(task['state']);base=state/'native'/task['id'];base.mkdir(parents=True,exist_ok=True)
    source_binding=json.loads((state/'WALLET_SOURCE_BINDING.json').read_text())
    if any(sha(repo/name)!=digest for name,digest in source_binding.items()):raise ValueError('Wallet worker sources changed after freeze')
    if task['window']['end']>1772323200000000:
        freeze=Path(task['locked_release_path'])
        release=json.loads(freeze.read_text())
        if sha(freeze)!=task['locked_release_sha256'] or release['protocol_sha256']!=task['protocol_sha256'] or release['status']!='FROZEN_DEVELOPMENT_WEIGHTS_AND_RISK_BEFORE_LOCKED_ECONOMICS':
            raise ValueError('Locked wallet requires frozen development release')
        if task['scenario'] not in release['funding_bridges']:raise ValueError('Unregistered funding bridge')
    from modules.collector_research.validation import runtime
    runtime.configure(SimpleNamespace(collector_root=task['collector_root'],collector_work=task['work'],source_run=task['source_run'],
                      run_dir=state/'native-control',resource_policy='server',workers=1,minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation import data
    if data.WORK!=Path(task['work']).resolve():raise ValueError('Each market source/bridge requires a fresh worker process pool')
    import polars as pl
    binding=dict(protocol_sha256=task['protocol_sha256'],target_sha256=task['target_sha256'],profile=task['profile'],
                 wallet_source_sha256=sha(__file__),storage_source_sha256=sha(Path(__file__).with_name('storage.py')),
                 observed_mark_reference_sha256=sha(task['mark_reference']),
                 financial_sources={str(p.relative_to(repo)):sha(p) for p in sorted((repo/'src/quant').glob('*.py'))+sorted((repo/'scripts/investment').glob('*.py'))})
    binding['frozen_wallet_sources']=source_binding
    if task.get('market_input_manifest_path'):
        if sha(task['market_input_manifest_path'])!=task['market_input_manifest_sha256']:raise ValueError('Admitted market source manifest changed')
        binding['market_input_manifest_sha256']=task['market_input_manifest_sha256']
    verify_binding(task['native_market_binding_path'],task['native_market_binding_sha256'])
    binding['native_market_binding_sha256']=task['native_market_binding_sha256']
    path=base/'RESULT.json'
    if path.exists():
        result=json.loads(path.read_text());data.saved_case_valid(result,binding);return result
    attempts=list(base.glob('attempt-*'))
    if len(attempts)>=2:raise RuntimeError('Only one automatic retry; inspect preserved failed wallet')
    attempt=base/f'attempt-{len(attempts)+1}';attempt.mkdir()
    try:
        if sha(task['target_path'])!=task['target_sha256']:raise ValueError('Frozen target changed')
        with np.load(task['target_path'],allow_pickle=False) as f:dates=f['decision_us'];weights=f['weights'];symbols=f['symbol_order'].tolist()
        w=task['window'];select=(dates>=w['start'])&(dates<w['end']);dates=dates[select];weights=weights[select].copy()
        cap=.6 if task['profile']=='FULL' else .3
        if not np.array_equal(dates,np.arange(w['start'],w['end'],DAY)) or not np.isfinite(weights).all() or np.abs(weights).sum(1).max()>cap+1e-9 or np.abs(weights).max()>.3+1e-9:
            raise ValueError('Complete target calendar, capital and registered risk budget required')
        weights[-1]=0.
        targets=pl.DataFrame(dict(available_us=np.repeat(dates,len(symbols)),symbol=symbols*len(dates),target_weight=weights.reshape(-1)))
        inputs=data.market_window(symbols,w['start'],w['end']);blocks=inputs['minute_blocks']
        estimates={(r['symbol'],r['event_us']):r for r in task.get('funding_estimates',[])}
        for event in inputs['events']:
            if (event['symbol'],event['event_us']) in estimates:
                row=estimates[event['symbol'],event['event_us']]
                if event['raw_rate']!=row['engine_raw_rate']:raise ValueError('Frozen funding estimate changed')
                event.update(funding_source_role=row['role'],funding_bridge_scenario=row['scenario'],exact_Binance_settlement=False,
                             observed_settlement_event=False,preregistration_sha256=task['bridge_preregistration_sha256'])
        def complete_blocks():
            for block in blocks():
                if not set(w['active_symbols'])<=set(block['market']):raise ValueError('Held active input calendar gap')
                yield block
        inputs['minute_blocks']=complete_blocks
        def factory(_bars,decisions,_mode):
            if not np.array_equal(decisions,dates):raise ValueError('Decision calendar changed')
            return targets,dict(source='FROZEN_POLICY_OR_CONTROL_TARGET',mapping=task['mapping'],risk_profile=task['profile'],
                                native_initial_capital=10000,no_spliced_return=True,teacher_inference_input=False)
        scale=task['funding_scale']
        case=data.engine.simulate(inputs,'LONG_SHORT',data.engine.COSTS[0],dict(id='RAW_AS_FRACTION' if scale==1 else 'RAW_AS_PERCENT',scale=scale),
              data.Reporter(base/'progress.json',task['id']),runtime.kernel_guard,target_factory=factory,
              account_factory=partial(profile_account,profile=task['profile']),persist_cash_close=True)
        verify_binding(task['native_market_binding_path'],task['native_market_binding_sha256'])
        directory=attempt/'account';saved=data.engine.save_case(case,directory);atomic(directory/'summary.json',saved['summary']);del case,inputs,targets
        # An unobserved held-data prefix or true whole-wallet insolvency remains
        # explicit. Its final partial timestamp may not match full mark reference.
        full=saved['summary']['completed_minutes']==saved['summary']['required_minutes']
        pack_case(saved,directory,task['mark_reference'] if full else None)
        with hydrated_account(directory,attempt/'audit-scratch') as hydrated:
            audit=verify_isolated(hydrated,symbols,scale)
        atomic(attempt/'INDEPENDENT_AUDIT.json',audit)
        value=dict(binding=binding,task=task,summary=saved['summary'],artifacts=saved['artifacts'],independent_audit=audit,
                   summary_path=str(directory/'summary.json'),summary_sha256=sha(directory/'summary.json'),
                   independent_audit_path=str(attempt/'INDEPENDENT_AUDIT.json'),independent_audit_sha256=sha(attempt/'INDEPENDENT_AUDIT.json'),
                   economic_calendar_complete=full,terminal_cash_realized=saved['summary']['terminal_cash_realized'])
        atomic(path,value);return value
    except BaseException as exc:atomic(attempt/'FAILURE.json',dict(error_type=type(exc).__name__,error=str(exc),time=time.time()));raise

def registered_protocol(tasks,protocol_path=None):
    """Default v3 stays unchanged; new frozen research may bind its own protocol."""
    protocol=Path(protocol_path) if protocol_path is not None else Path(__file__).resolve().parents[2]/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
    registered=json.loads(protocol.read_text())
    if any(t['protocol_sha256']!=sha(protocol) for t in tasks):raise ValueError('Native tasks do not match committed protocol')
    return registered


def run_tasks(tasks,state,result_name,workers=10,*,protocol_path=None,on_progress=None):
    if len({t['work'] for t in tasks})!=1:raise ValueError('Separate process pools required for each imputed market source')
    state=Path(state);results=[];errors=[]
    frozen_sources(state)
    registered=registered_protocol(tasks,protocol_path)
    inputs_by_window={}
    for t in tasks:
        with np.load(t['target_path']) as f:symbols=f['symbol_order'].tolist()
        key=(t['window']['id'],t['work'])
        identity=dict(window=t['window'],symbols=symbols,manifest=t.get('market_input_manifest_path'))
        if key in inputs_by_window:
            previous,binding=inputs_by_window[key]
            if previous!=identity:raise ValueError('Same named wallet window has different market identity')
        else:
            binding=prepare_binding(state,t['window'],symbols,t['work'],t.get('market_input_manifest_path'),
                t.get('market_input_manifest_sha256') or registered['data_manifest_sha256'])
            inputs_by_window[key]=(identity,binding)
        t['native_market_binding_path']=str(binding);t['native_market_binding_sha256']=sha(binding)
        t['mark_reference']=str(prepare_reference(state,t['window'],symbols,t['collector_root'],t['work'],t['source_run']))
    atomic(state/(result_name+'_TASKS.json'),dict(tasks=tasks,actual_target_calendar=True))
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(native_worker,t):t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            task=futures[future]
            try:results.append(future.result())
            except Exception as exc:
                try:results.append(pool.submit(native_worker,task).result())
                except Exception as retry:errors.append(dict(task_id=task['id'],error=str(exc),retry_error=str(retry)))
            atomic(state/(result_name+'.json'),dict(status='RUNNING',cases=results,errors=errors,total_cases=len(tasks)))
            atomic(state/(result_name+'_progress.json'),dict(stage=result_name,completed=len(results),failed=len(errors),total=len(tasks),pid=os.getpid(),updated_at=time.time()))
            if on_progress is not None:on_progress(len(results),len(errors),len(tasks),task['id'])
            print(f'{result_name} {len(results)}/{len(tasks)} failed={len(errors)} {task["id"]}',flush=True)
    atomic(state/(result_name+'.json'),dict(status='COMPLETE' if not errors else 'FAILED',cases=results,errors=errors,total_cases=len(tasks)))
    if errors:raise RuntimeError('Wallet errors preserved; no silent continuation')
    return results

def main():
    p=argparse.ArgumentParser();p.add_argument('--tasks',required=True);p.add_argument('--state',required=True);p.add_argument('--name',required=True);p.add_argument('--workers',type=int,default=10);a=p.parse_args()
    run_tasks(json.loads(Path(a.tasks).read_text())['tasks'],a.state,a.name,a.workers)

if __name__=='__main__':main()
