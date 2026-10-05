"""Four frozen initial-stop accounts, two workers, existing shared finances."""
import argparse,gc,json,multiprocessing,os,resource,subprocess,time
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import polars as pl
from quant import disk,resources
from quant.paths import ROOT,STATE
from scripts.investment.run_cta_leaderboard import sha,write,stamp
from scripts.investment import cta_classics as cta,perpetual_directional as engine,audit_shared_direction as finance
from scripts.investment.cta_atr_protection import InitialATRProtection,RULES
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
from scripts.investment.bybit_cost_inputs import snapshot_cost
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS,append_event

def worker(spec,run,cost,unit):
    started=time.monotonic();peak=0;progress=Progress()
    case_id='TSMOM12M_ATR_LONG_SHORT_'+cost['id']+'_'+unit['id']
    progress.value['detail']=case_id+' · 同一10k共享组合，非独立资产钱包'
    def guard():
        nonlocal peak
        peak=max(peak,resources.status()['ram_current_bytes'])
        assert time.monotonic()-started<spec['budget']['wall_seconds']
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['budget']['RSS_bytes_per_worker']
    try:
        symbols=tuple(spec['symbols']);begin=stamp('2024-09-01');start=stamp('2025-03-01');end=stamp('2025-07-01')
        whole=load_portfolio_window(spec['data_manifest']['path'],symbols,begin,end)
        signal=pl.read_parquet(run/'frozen_signals.parquet')
        target,meta=cta.targets(signal,whole['daily'],np.arange(start,end,cta.DAY,dtype=np.int64),'LONG_SHORT',symbols,'TSMOM12M')
        window=dict(whole,start=start,end=end,events=[r for r in whole['events'] if start<=r['event_us']<end],
            minute_blocks=lambda:whole['minute_blocks'](start,end,trade_ranges=True))
        case=engine.simulate(window,'LONG_SHORT',cost,unit,progress,guard,target_factory=lambda b,d,m:(target,meta),
            account_factory=USDTLinearPerpetualAccount,persist_cash_close=True,position_protection=InitialATRProtection())
        directory=run/case_id;saved=engine.save_case(case,directory);write(directory/'summary.json',saved['summary'])
        checked=finance.verify(directory,symbols,unit['scale'])
        assert pl.read_parquet(directory/'targets.parquet').equals(target)
        assert sha(directory/'targets.parquet')==spec['original_targets_by_scenario'][cost['id']+'_'+unit['id']]
        return dict(id=case_id,cost=cost['id'],unit=unit['id'],**saved,independent=checked,
            elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            shared_RAM_sampled_peak_bytes=peak,worker_pid=os.getpid())
    finally:
        progress.stop.set();progress.thread.join(timeout=3);gc.collect()

def main():
    ap=argparse.ArgumentParser()
    for name in ('protocol','run-dir','output'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();spec=json.loads(a.protocol.read_bytes());run=a.run_dir.resolve();out=a.output.resolve()
    assert os.getenv('COIN_TASK_ID') and run.parent==STATE and not run.exists() and not out.exists()
    assert out.is_relative_to(ROOT/'reports/fast_research') and spec['protection']==RULES and spec['accounts']==4 and spec['workers']==2
    assert sha(ROOT/'state/dataset_lock.json')==spec['locked_sha256']
    for p,h in spec['source_hashes'].items():assert sha(ROOT/p)==h,p
    assert sha(spec['data_manifest']['path'])==spec['data_manifest']['sha256']
    oldpath=ROOT/spec['original_result']['path'];assert sha(oldpath)==spec['original_result']['sha256']
    old=json.loads(oldpath.read_bytes())
    import xml.etree.ElementTree as ET
    xml=ROOT/spec['regression']['path'];assert sha(xml)==spec['regression']['sha256']
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    assert sum(int(v.get('tests',0)) for v in suites)==6 and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
    run.mkdir();started=time.monotonic();progress=Progress()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha(a.protocol),source_hashes=spec['source_hashes'],CPU_workers=2)
    write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=spec['experiment_id'],event_id=spec['experiment_id']+':START',
        event_type='OPERATIONAL_RESEARCH_START',git_commit=binding['git_commit'],data_manifest_hash=spec['data_manifest']['sha256'],
        protocol_hash=binding['protocol_sha256'],feature_set='FROZEN_TSMOM12M_PAST30_SIZE_PLUS_PINNED_DAILY_ATR20',
        labels='NONE',model_family='PUBLIC_CLASSIC_FIXED_INITIAL_STOP',hyperparameters=RULES,models_fit=0,
        thresholds='NO_SEARCH_2ATR_ONLY',cost_assumptions=spec['cost'],all_folds='SEEN_MAR_JUN2025_122D',
        success_failure='START_BEFORE_NEW_ACCOUNTS',reason_for_next_experiment=spec['question'],result_influenced_later_choice=False)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    r=dict(status='FAILED',binding=binding,protocol=spec,run_dir=str(run),cases=[],required_accounts=4,
        models_fit=0,search_configurations=0,GPU_hours=0,orders_sent=0,locked_consumed=False)
    try:
        progress.update('保护退出磁盘实扫；总量未知',None,None,'扫描')
        r['disk_before']=dict(disk.check(spec['budget']['owned_bytes']),measured_utc=datetime.now(UTC).isoformat())
        whole=load_portfolio_window(spec['data_manifest']['path'],tuple(spec['symbols']),stamp('2024-09-01'),stamp('2025-07-01'))
        signal,available=cta.signals(whole['daily'],np.arange(stamp('2024-09-01'),stamp('2025-07-01'),cta.DAY,dtype=np.int64),tuple(spec['symbols']))
        signal.write_parquet(run/'frozen_signals.parquet');assert sha(run/'frozen_signals.parquet')==spec['original_signal_sha256']
        del whole,signal,available;gc.collect()
        jobs=[]
        for oldcost in engine.COSTS:
            cost=snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',symbols=tuple(spec['symbols']),
                fee_zone_by_symbol={s:'DERIVATIVES_CRYPTO_STANDARD' for s in spec['symbols']},scenario_id=oldcost['id'],
                half_spread_bps=oldcost['half_spread_bps'],slippage_bps=oldcost['slippage_bps'],execution_source_ref='ACCEPTED_BINANCE_USDM_PROXY',
                execution_status='FIXED_NON_NATIVE_SPREAD_SLIPPAGE_SCENARIO')
            jobs.extend((cost,unit) for unit in engine.UNITS)
        progress.value['detail']='2路账户并行 · 4情景固定参数 · 每账户共享10k/10币'
        with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
            futures=[pool.submit(worker,spec,run,cost,unit) for cost,unit in jobs]
            for future in as_completed(futures):
                r['cases'].append(future.result());write(run/'CHECKPOINT.json',r)
                progress.update('保护退出账户完成',len(r['cases']),4,'账户')
                assert time.monotonic()-started<spec['budget']['wall_seconds']
                assert sum(p.stat().st_size for p in run.rglob('*') if p.is_file())<spec['budget']['owned_bytes']
        r['status']='COMPLETE_FOUR_ACTUAL_PROTECTED_ACCOUNTS_OR_EXPLICIT_HALTS'
    except Exception as e:r.update(error_type=type(e).__name__,error=str(e));raise
    finally:
        r.update(elapsed_seconds=time.monotonic()-started,owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),created_utc=datetime.now(UTC).isoformat())
        write(out,r);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=spec['experiment_id']+':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT',success_failure=r['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=r['status'],accounts=len(r['cases']),elapsed_seconds=r['elapsed_seconds'])))

if __name__=='__main__':main()
