"""Eight fixed public2h long-only accounts over the accepted signed wallet.

Only signal cadence, signal input and frozen sizing price are privately adapted.
The shared financial controller, wallet, costs and UTCday evaluator are reused.
"""
import argparse, gc, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_directional as reuse
from scripts.investment import public_donchian_perpetual as strategy
from scripts.investment import public_long_development_adapter as private

BAR=7_200_000_000
CONTRACT='D041_PUBLIC_DONCHIAN_TWO_HOUR_PERPETUAL_BENCHMARK_20261003_V1'
STATUS='COMPLETE_D041_CONDITIONAL_PUBLIC_DONCHIAN_PERPETUAL_BENCHMARK_NOT_NATIVE_OR_LONG_TERM_APR'
REUSE_SHA='547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3'
RULES=dict(reuse.RULES,modes=['LONG_ONLY'],signal='ORIGINAL_PUBLIC_DONCHIAN20_SMA200_UTC2H_HOOKS',
    sizing='FROZEN_SIGNAL_NAV_AND_CLOSED_2H_TRADE_PRICE',signal_interval_us=BAR,
    warmup='JULY2025_OFFICIAL_USDM_2H_PLUS_ACCEPTED_AUGUST_ONWARD_USDM_1M',
    risk_inputs='UNCHANGED_PAST30_COMPLETED_UTC_DAILY_RETURNS',public_strategy_has_short_entry=False)


def adapted_simulate(receipt, target_module=strategy):
    reuse.need(reuse.sha(reuse.__file__)==REUSE_SHA,'Accepted financial controller unchanged')
    def transform(node,changes):
        node=private.literal(node,changes,'SIGNAL_CLOCK_2H',
            'np.arange(start,end,DAY,dtype=np.int64)',
            'np.arange(start,end,SIGNAL_US,dtype=np.int64)',1)
        node=private.literal(node,changes,'TWO_SIGNAL_AND_DAILY_RISK_INPUTS',
            "strategy.fixed_targets(window['daily'],decisions,mode)",
            "strategy.fixed_targets(window['signal_bars'],decisions,mode,risk_daily_bars=window['daily'])",1)
        before="{s:dict(zip(window['daily'].filter(pl.col('symbol')==s)['close_us'].to_list(),window['daily'].filter(pl.col('symbol')==s)['close'].to_list(),strict=True)) for s in SYMBOLS}"
        node=private.literal(node,changes,'FROZEN_SIZING_PRICE_COMPLETED_2H_NOT_RISK_DAILY',
            before,before.replace("window['daily']","window['signal_bars']"),1)
        return private.literal(node,changes,'TRUTHFUL_DIAGNOSTIC_ORDER_KIND',
            "'DAILY_TARGET'","'SIGNAL_TARGET_2H'",1)
    return private.namespace(reuse,['simulate'],dict(SIGNAL_US=BAR,strategy=target_module),receipt,transform)['simulate']


def closed_two_hours(minutes):
    """Reuse accepted public bar builder; add original open and base volume."""
    reuse.need(minutes.height and minutes.schema['open_us']==pl.Int64,'Actual minute clocks')
    for symbol in reuse.SYMBOLS:
        one=minutes.filter(pl.col('symbol')==symbol).sort('open_us')
        times=one['open_us'].to_numpy()
        reuse.need(len(times)>0 and times[0]%BAR==0 and (times[-1]+reuse.MINUTE)%BAR==0
            and np.array_equal(times,np.arange(times[0],times[-1]+reuse.MINUTE,reuse.MINUTE,dtype=np.int64)),
            'Complete full2h feature calendar; missing minutes never dropped')
    hours=strategy.public.closed_hours(minutes,timeframe_minutes=120)
    extras=minutes.sort(['symbol','open_us']).with_columns(
        (pl.col('open_us')//BAR*BAR).alias('hour_open_us')).group_by(['symbol','hour_open_us']).agg(
        pl.col('open').first(),pl.col('volume').sum())
    result=hours.join(extras,on=['symbol','hour_open_us'],how='inner',validate='1:1').select(
        'symbol',pl.lit('2h').alias('interval'),pl.col('hour_open_us').alias('open_us'),
        'close_us','available_us','open','high','low','close','volume').sort(['symbol','open_us'])
    reuse.need(result.height*120==minutes.height,'Every feature minute retained in a complete2h bar')
    return result


def signal_history(manifest,july,end):
    """New signal features from accepted inputs; no old source QA or new feeds."""
    columns=['symbol','open_us','close_us','available_us','open','high','low','close','volume']
    signal_columns=['symbol','interval',*columns[1:]]
    frames=[];proofs=[]
    for entry in july['sources']:
        p=Path(entry['normalized_path']);reuse.need(p.resolve().is_relative_to(STATE)
            and p.stat().st_size==entry['normalized_bytes'] and reuse.sha(p)==entry['normalized_sha256'],
            'Accepted official July2h input binding')
        frames.append(pl.read_parquet(p,columns=signal_columns))
        proofs.append(dict(id='trade:2h:'+entry['symbol']+':2025-07',path=str(p),sha256=entry['normalized_sha256'],
            bytes=entry['normalized_bytes'],rows=entry['rows'],format_evidence_role='JULY2H_NEW_SOURCE'))
    minute_ids=[key for key,entry in manifest['source_files'].items()
        if entry.get('product')=='USD_M_PERPETUAL_TRADE_KLINES' and entry.get('interval')=='1m'
        and '2025-08'<=entry['month']<datetime.fromtimestamp(end/1e6,UTC).strftime('%Y-%m')]
    reuse.need(len(minute_ids) in (8,14),'Fixed August-November or August-February signal source files')
    # Financial controller reads minute open/capacity/mark separately. This
    # projection is solely new OHLC/volume features, not repeated format QA.
    minutes=[]
    for identity in minute_ids:
        entry=manifest['source_files'][identity];p=Path(entry['normalized_path'])
        reuse.need(p.resolve().is_relative_to(STATE) and p.stat().st_size==entry['normalized_bytes']
            and reuse.sha(p)==entry['normalized_sha256'],'Accepted signal minute byte binding')
        minutes.append(pl.read_parquet(p,columns=columns))
        proofs.append(dict(id=identity,path=str(p),sha256=entry['normalized_sha256'],
            bytes=entry['normalized_bytes'],rows=entry['rows'],format_evidence_role=entry['format_evidence_role']))
    frames.append(closed_two_hours(pl.concat(minutes)))
    bars=pl.concat(frames).sort(['symbol','open_us'])
    reuse.need(bars.height==2*((end-strategy.SOURCE_BEGIN_US)//BAR),'FullJuly-through-score calendar, no warmup positions')
    return bars,proofs,dict(method='REUSED_PUBLIC_CLOSED_HOURS_120_PLUS_POLARS_FIRST_OPEN_SUM_VOLUME',
        rows=bars.height,interval_us=BAR,begin_us=strategy.SOURCE_BEGIN_US,end_exclusive_us=end,
        columns=signal_columns,raw_source_QA_repeated=False)


def closed_proof(ref):
    value=reuse.relative_proof(ref)
    task=reuse.small(STATE/'task-progress'/f"task-{value['binding']['task_id']}.json")
    reuse.need(task['status']=='completed' and task['exit_code']==0,'Prerequisite actually closed0 '+ref['path'])
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','run-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--experiment-id',required=True);a=p.parse_args()
    spec=reuse.small(a.protocol);run=a.run_dir.resolve();out=a.output.resolve()
    reuse.need(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
        and pl.thread_pool_size()<=2,'Actual bounded clean CPU2 task')
    reuse.need(spec['contract_id']==CONTRACT and spec['rules']==RULES and spec['cost_scenarios']==reuse.COSTS
        and spec['unit_scenarios']==reuse.UNITS and spec['period_ids']==['122D','90D'],'Fixed eight accounts, no search')
    reuse.need(run.parent==STATE and not run.exists() and out.parent==ROOT/'reports/fast_research' and not out.exists()
        and str(run)==spec['run_dir'] and str(out.relative_to(ROOT))==spec['output_path'],'Exclusive frozen output')
    hashes=spec['frozen_sources'];reuse.need(hashes[Path(__file__).relative_to(ROOT).as_posix()]==reuse.sha(__file__),'Own pinned source')
    for name,digest in hashes.items():reuse.need(reuse.sha(ROOT/name)==digest,'Frozen source '+name)
    test=closed_proof(spec['required_new_tests']);reuse.need(test['test_exit_code']==0,'Actual new2h causal/entry cases')
    july=closed_proof(spec['july_signal_source_receipt']);closed_proof(spec['july_signal_independent_receipt'])
    closed_proof(spec['original_root']);manifest=reuse.relative_proof(spec['input_manifest'])
    run.mkdir();began=time.monotonic();budget=spec['budgets'];before=resources.status();derivation=[]
    simulate=adapted_simulate(derivation)
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(Path(__file__).resolve()),source_sha256=reuse.sha(__file__),
        source_hashes=hashes,protocol_path=str(a.protocol.resolve()),protocol_sha256=reuse.sha(a.protocol),
        exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sys_prefix=sys.prefix,rules=RULES,private_signal_derivation=derivation)
    reuse.write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(reuse.FIELDS);event.update(experiment_id=a.experiment_id,event_id=a.experiment_id+':START',event_type='RESEARCH_START',
        git_commit=binding['git_commit'],data_manifest_hash=spec['input_manifest']['sha256'],protocol_hash=binding['protocol_sha256'],
        feature_set='PUBLIC_DONCHIAN20_SMA200_ORIGINAL2H',labels='NONE',model_family='NONE',hyperparameters={},seed=None,
        thresholds=RULES,cost_assumptions={'costs':reuse.COSTS,'units':reuse.UNITS},all_folds=['SEEN_122D','SEEN_90D'],
        success_failure='START_BEFORE_MARKET_ARRAYS',reason_for_next_experiment='Compare SMA directional improvement to stronger public same-product benchmark',
        result_influenced_later_choice=True,source_hashes=hashes,exact_command=binding['exact_command'])
    report=dict(status='FAIL_D041_PUBLIC_PERPETUAL_BENCHMARK',binding=binding,run_dir=str(run),run_binding_sha256=reuse.sha(run/'RUN_BINDING.json'),
        registration_start=reuse.append_event(ROOT/'reports/experiment_registry.jsonl',event),required_cases=8,completed_cases=0,cases=[],input_windows=[],
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,candidate='NO_QUALIFIED_CANDIDATE',
        long_term_APR='NOT_EVALUABLE',old_SMA_financial_accounts_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before)
    progress=reuse.support.progress_writer(8)
    def guard():
        reuse.need(reuse.support.owned_bytes(run)<=budget['new_owned_bytes']
            and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=budget['peak_RSS_bytes']
            and time.monotonic()-began<=budget['wall_seconds'],'Declared new8 account resource budget')
    try:
        progress.update('实际容量扫描，总量未知',None,None,'扫描')
        report['disk']=dict(scan_started_utc=datetime.now(UTC).isoformat(),**disk.check(budget['new_owned_bytes']))
        report['disk']['scan_finished_utc']=datetime.now(UTC).isoformat()
        reuse.need(report['disk']['total_bytes']+budget['new_owned_bytes']+1_000_000_000<=32_000_000_000,'Capacity including temporary reserve')
        for window_spec in manifest['windows']:
            w=reuse.load_window(manifest,window_spec)
            w['signal_bars'],proofs,feature=signal_history(manifest,july,w['end'])
            report['input_windows'].append(dict(id=window_spec['id'],input_proofs=w['input_proofs'],
                signal_source_proofs=proofs,feature_receipt=feature,original_funding_events=len(w['events']),
                score_start_us=w['start'],score_end_exclusive_us=w['end']))
            for cost in reuse.COSTS:
                for unit in reuse.UNITS:
                    selector=window_spec['id']+'_LONG_ONLY_'+cost['id']+'_'+unit['id']
                    case=simulate(w,'LONG_ONLY',cost,unit,progress,guard)
                    saved=reuse.save_case(case,run/selector);del case;gc.collect()
                    report['cases'].append(dict(id=selector,period=window_spec['id'],mode='LONG_ONLY',cost_id=cost['id'],unit_id=unit['id'],**saved))
                    report['completed_cases']=len(report['cases']);guard();s=saved['summary']
                    reuse.need(s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and s['completed_minutes']==s['required_minutes']
                        and s['unpaid_liability']==0,'Full account calendar, real halts cannot be hidden')
                    progress.update('公开2小时永续参照',report['completed_cases'],8,'账户')
            del w;gc.collect()
        reuse.need(report['completed_cases']==8 and all(reuse.sha(ROOT/n)==h for n,h in hashes.items()),'Eight actual accounts and source stability')
        report.update(status=STATUS,completed_full_calendar_cases=8,incomplete_or_halted_cases=0)
    except Exception as e:report.update(error_type=type(e).__name__,reason=str(e));raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=reuse.support.owned_bytes(run),resources_after=resources.status())
        reuse.write(out,report);reuse.append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=a.experiment_id+':RESULT',
            event_type='RESEARCH_RESULT',success_failure=report['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=reuse.sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=report['status'],completed_cases=report['completed_cases'],sha256=reuse.sha(out))))

if __name__=='__main__':main()
