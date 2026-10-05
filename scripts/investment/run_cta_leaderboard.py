"""Frozen zero-fit CTA directions through the existing shared account."""
import argparse,gc,hashlib,json,os,resource,subprocess,time
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import polars as pl
from quant import disk,resources
from quant.paths import ROOT,STATE
from scripts.investment import cta_classics as cta, audit_cta_classics as reference
from scripts.investment import perpetual_directional as engine,audit_shared_direction as finance
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
from scripts.investment.bybit_cost_inputs import snapshot_cost
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS,append_event

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def native(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError('Unsupported research JSON type: '+type(value).__name__)
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=native)+'\n',encoding='utf-8')
def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())*1_000_000

def main():
    ap=argparse.ArgumentParser()
    for k in ('protocol','run-dir','output'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();spec=json.loads(a.protocol.read_bytes());run=a.run_dir.resolve();out=a.output.resolve()
    assert os.getenv('COIN_TASK_ID') and run.parent==STATE and not run.exists() and not out.exists()
    assert out.is_relative_to(ROOT/'reports/fast_research') and pl.thread_pool_size()<=2
    assert spec['families']==list(cta.FAMILIES) and spec['modes']==list(cta.MODES) and spec['models_fit']==0
    for p,h in spec['frozen_source_hashes'].items():assert sha(ROOT/p)==h,'Frozen rule/source '+p
    assert sha(ROOT/'state/dataset_lock.json')==spec['locked_sha256']
    manifest=spec['data_manifest'];assert sha(manifest['path'])==manifest['sha256']
    import xml.etree.ElementTree as ET
    test=spec['regression'];assert sha(ROOT/test['path'])==test['sha256'] and sha(ROOT/'tests/test_cta_classics.py')==test['source_sha256']
    suites=list(ET.parse(ROOT/test['path']).getroot().iter('testsuite'))
    assert sum(int(v.get('tests',0)) for v in suites)==2 and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
    paths=['scripts/investment/'+p+'.py' for p in ('cta_classics','audit_cta_classics','run_cta_leaderboard',
        'multi_asset_data','public_sma_perpetual','donchian_daily_pool_target','perpetual_directional','perpetual_closing_exempt_account',
        'bybit_cost_inputs','audit_shared_direction','market_regime','shared_direction_model')]
    paths+=['src/quant/perpetual_account.py','tests/test_cta_classics.py']
    paths+=['third_party/jesse_example_donchian/'+p for p in cta.PINNED_HASHES]
    binding=dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha(a.protocol),source_hashes={p:sha(ROOT/p) for p in paths},input_manifest_sha256=manifest['sha256'])
    run.mkdir();write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=spec['experiment_id'],event_id=spec['experiment_id']+':'+run.name+':START',
        event_type='OPERATIONAL_RESEARCH_START',git_commit=binding['git_commit'],data_manifest_hash=manifest['sha256'],protocol_hash=binding['protocol_sha256'],
        feature_set='CLOSED_1D_PRICE_PRIOR_CHANNEL_PAST30_RETURNS',labels='NONE_ZERO_TRAINING',model_family='FROZEN_PUBLIC_CLASSIC_CTA',
        hyperparameters=spec['rules'],seed=None,thresholds='NO_FITTED_OR_POST_RESULT_THRESHOLD',cost_assumptions=spec['cost'],
        all_folds='COMMON_SEEN_DEVELOPMENT_MAR_JUN_2025_122D',success_failure='START_BEFORE_ACCOUNTS',reason_for_next_experiment=spec['question'],
        result_influenced_later_choice=False,models_fit=0)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    started=time.monotonic();shared_peak=0;progress=Progress();progress.value['detail']='冻结经典CTA；零训练；同10币共享资本代理账户';r=dict(status='FAILED',binding=binding,protocol=spec,
        run_dir=str(run),cases=[],models_fit=0,search_configurations=0,GPU_hours=0.,locked_consumed=False,orders_sent=0)
    def guard():
        nonlocal shared_peak
        shared_peak=max(shared_peak,resources.status()['ram_current_bytes'])
        assert time.monotonic()-started<spec['budget']['wall_seconds']
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['budget']['RSS_bytes']
        assert sum(p.stat().st_size for p in run.rglob('*') if p.is_file())<spec['budget']['owned_bytes']
    try:
        progress.update('CTA磁盘实扫；总量未知',None,None,'扫描')
        r['disk_before']=dict(disk.check(spec['budget']['owned_bytes']),measured_utc=datetime.now(UTC).isoformat())
        symbols=tuple(spec['symbols']);begin=stamp('2024-09-01');start=stamp('2025-03-01');end=stamp('2025-07-01')
        whole=load_portfolio_window(manifest['path'],symbols,begin,end);bars=whole['daily']
        signal,available=cta.signals(bars,np.arange(begin,end,cta.DAY,dtype=np.int64),symbols)
        r['signal_reference']=reference.verify_signals(signal,bars,np.arange(begin,end,cta.DAY,dtype=np.int64),symbols)
        signal.write_parquet(run/'frozen_signals.parquet');write(run/'SIGNAL_AVAILABILITY.json',available)
        score=signal.filter(pl.col('close_us')>=start)
        assert score.height==122*len(symbols) and score.select(cta.FAMILIES).null_count().select(pl.sum_horizontal(pl.all())).item()==0
        decisions=np.arange(start,end,cta.DAY,dtype=np.int64)
        window=dict(whole,start=start,end=end,events=[v for v in whole['events'] if start<=v['event_us']<end],
                    minute_blocks=lambda:whole['minute_blocks'](start,end))
        from scripts.investment.shared_direction_model import feature_table
        from scripts.investment.market_regime import past_state
        btc=feature_table(bars,symbols)[0].filter((pl.col('symbol')=='BTCUSDT')&(pl.col('close_us')>=start)&(pl.col('close_us')<end))
        states={v['close_us']:past_state(v) for v in btc.iter_rows(named=True)};r['descriptive_past_states']=states
        plans=[(f,m) for f in cta.FAMILIES for m in ('LONG_ONLY','SHORT_ONLY','LONG_SHORT')]+[('CASH','CASH'),('HOLD','LONG_ONLY')]
        r['required_accounts']=len(plans)*4
        for family,mode in plans:
            target_family='SMA200_SIGNED' if family=='CASH' else family
            target,meta=cta.targets(signal,bars,decisions,mode,symbols,target_family)
            target_ref=reference.verify_targets(target,signal,bars,symbols,target_family,mode)
            for oldcost in engine.COSTS:
                cost=snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',symbols=symbols,
                    fee_zone_by_symbol={s:'DERIVATIVES_CRYPTO_STANDARD' for s in symbols},scenario_id=oldcost['id'],
                    half_spread_bps=oldcost['half_spread_bps'],slippage_bps=oldcost['slippage_bps'],execution_source_ref='ACCEPTED_BINANCE_USDM_PROXY',
                    execution_status='FIXED_NON_NATIVE_SPREAD_SLIPPAGE_SCENARIO')
                for unit in engine.UNITS:
                    guard();case_id='_'.join((family,mode,cost['id'],unit['id']));directory=run/case_id;began=time.monotonic()
                    progress.value['detail']=f"CTA账户{len(r['cases'])+1}/{r['required_accounts']} · {case_id} · 零训练"
                    progress.update('经典CTA组合账户对照',len(r['cases']),r['required_accounts'],'账户',family=family,mode=mode)
                    case=engine.simulate(window,mode,cost,unit,progress,guard,target_factory=lambda b,d,m:(target,meta),
                        account_factory=USDTLinearPerpetualAccount,persist_cash_close=True)
                    saved=engine.save_case(case,directory);write(directory/'summary.json',saved['summary'])
                    checked=finance.verify(directory,symbols,unit['scale']);checked['target_reference']=target_ref
                    assert pl.read_parquet(directory/'targets.parquet').equals(target)
                    buckets={}
                    for day in checked['daily_direction_contributions']:
                        key=states[day['day_end_us']-cta.DAY];v=buckets.setdefault(key,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        v['days']+=1
                        for k in ('LONG','SHORT','CASH'):v[k]+=day[k]
                        v['net']+=day['LONG']+day['SHORT']
                    part=checked['partial_stop_direction_contribution']
                    if part:
                        key=states[part['stop_us']//cta.DAY*cta.DAY];v=buckets.setdefault(key,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        for k in ('LONG','SHORT','CASH'):v[k]+=part[k]
                        v['net']+=part['LONG']+part['SHORT'];v['partial_stop_day']=True
                    checked['by_past_regime']=buckets
                    r['cases'].append(dict(id=case_id,strategy=family,mode=mode,cost=cost['id'],unit=unit['id'],
                        elapsed_seconds=time.monotonic()-began,**saved,independent=checked))
                    write(run/'CHECKPOINT.json',r);del case;gc.collect()
        r['status']='COMPLETE_FROZEN_CTA_56_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS'
    except Exception as e:r.update(error_type=type(e).__name__,error=str(e));raise
    finally:
        r.update(elapsed_seconds=time.monotonic()-started,shared_RAM_sampled_peak_bytes=shared_peak,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),created_utc=datetime.now(UTC).isoformat())
        write(out,r)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=spec['experiment_id']+':'+run.name+':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT',success_failure=r['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=r['status'],accounts=len(r['cases']),models_fit=0)))

if __name__=='__main__':main()
