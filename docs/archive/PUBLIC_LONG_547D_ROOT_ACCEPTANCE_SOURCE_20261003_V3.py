"""UNEXECUTED D033 metadata acceptance; no price/row QA or financial replay."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
ACTUAL='reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json'
AUDIT='reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json'
AUDIT_STATUS='PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
ARCHIVE='docs/archive/PUBLIC_LONG_547D_ROOT_ACCEPTANCE_SOURCE_20261003_V3.py'
OUT=ROOT/'reports/fast_research/PUBLIC_LONG_547D_ROOT_ACCEPTANCE_20261003_V1.json'
STRATEGIES=('CASH','COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER','COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER')
MONTHS=[f'2024-{m:02d}' for m in range(1,13)]+[f'2025-{m:02d}' for m in range(1,7)]
METRICS={'net_cash_PnL':'net_PnL','gross_cash_PnL_same_quantities':'gross_PnL_same_quantities',
 'fees':'fees','execution_costs':'execution_costs','turnover':'normalized_daily_turnover',
 'max_observed_minute_MDD':'minute_MDD','max_drawdown':'daily_MDD','terminal_marked_notional':'terminal_marked_notional'}

def check(ok, reason):
    if not ok: raise ValueError(reason)

def small(path, expected=None, parse=True):
    original=Path(path); path=original.resolve()
    check(not original.is_symlink() and (path.is_relative_to(ROOT) or path.is_relative_to(STATE))
        and path.is_file() and path.stat().st_size<2_000_000
        and (path.suffix in {'.json','.py','.ps1','.sh','.md','.lock','.toml'} or path.name in {'LICENSE','JESSE_LICENSE'}), 'Ordinary small metadata/code only')
    data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
    check(expected is None or digest==expected,'Frozen small proof changed: '+str(path))
    return (json.loads(data) if parse else None),digest

def closed(report):
    identity=report['binding']['task_id'];check(re.fullmatch('[0-9a-f]{32}',identity) is not None,'Exact real task id')
    path=STATE/'task-progress'/('task-'+identity+'.json');task,digest=small(path)
    check(task['id']==identity and task['status']=='completed' and task['exit_code']==0,'Real closed0, no premanufactured PASS')
    return dict(path=str(path),sha256=digest,task=task)

def stamp(value):
    check(type(value) in (int,float) and math.isfinite(value),'Real Unix task time')
    return value

def near(a,b,tolerance):
    a,b=float(a),float(b);check(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tolerance,'Saved financial summary differs from independent proof')

def bounded(record):
    check(record['ram_limit_bytes']<=5_000_000_000 and record['swap_bytes']==0 and not record['gpu_used'],'Original shared5GB/swap0/noGPU')

def byte_hash(path, expected, work, byte_count=None):
    original=Path(path);path=original.resolve()
    check(not original.is_symlink() and path.is_relative_to(work) and path.is_file()
        and path.stat().st_size<=400_000_000 and path.suffix in {'.json','.parquet'},'New saved target/ledger bytes only, never rows')
    check(byte_count is None or path.stat().st_size==byte_count,'Saved new artifact size')
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    check(digest==expected,'New saved artifact byte SHA changed')
    return dict(path=str(path),sha256=digest,bytes=path.stat().st_size)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--audit-source',type=Path,required=True)
    for key in ('source-host','tiny-host','actual-host','audit-host'):parser.add_argument('--'+key,required=True)
    parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args()
    check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Existing bounded/progress clean runtime')
    own_resources=resources.status();bounded(own_resources);out=args.output.resolve()
    check(out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(),'Exclusive root metadata report')
    _,own_sha=small(__file__,parse=False);small(ROOT/ARCHIVE,own_sha,parse=False)
    protocol=args.protocol.resolve();check(protocol.is_relative_to(ROOT/'protocols'),'Frozen ROOT protocol')
    spec,protocol_sha=small(protocol);actual,actual_sha=small(ROOT/ACTUAL);audit,audit_sha=small(ROOT/AUDIT)
    tiny,tiny_sha=small(ROOT/spec['required_smoke_receipt']);source,source_sha=small(ROOT/spec['source_receipt'],spec['source_receipt_sha256'])
    check(tuple(spec['strategy_ids'])==STRATEGIES and spec['planned_ledgers']==3 and spec['costs']['spread_bps']==[8]
        and spec['costs']['nominal_roundtrip_bps']==[36] and len(spec['folds'])==1,'Exactly three fixed sleeves, one full period and one cost')
    period=spec['folds'][0];check(period['period_start']=='2024-01-01' and period['period_end_exclusive']=='2025-07-01','547day scoring with no future locked IO')
    check(source['status']=='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR' and source['source_files']==38
        and source['days_per_symbol']==578 and source['actual_minute_rows']==1664640 and actual['source_receipt_sha256']==source_sha,'Only actual accepted38-source reuse, no new source QA')
    check(source['source_scope']==spec['source_scope']==actual['source_scope']=='DEC2023_JUN2025'
        and source['source_calendar']==spec['source_calendar']==actual['source_calendar']==['2023-12']+MONTHS
        and actual['source_days_per_symbol']==578 and actual['source_month_files']==38
        and not source['locked_consumed'] and source['models_fit']==source['orders_sent']==source['GPU']==0,'Exact accepted warmup/calendar and source-only scope')
    hashes=dict(spec['frozen_sources']);hashes[str(protocol.relative_to(ROOT))]=protocol_sha
    check(actual['binding']['source_hashes']==tiny['binding']['source_hashes']==hashes
        and audit['verified_source_hashes']==hashes,'Same actually frozen inputs/code across new smoke/actual/audit')
    for name,digest in hashes.items():
        check(not Path(name).is_absolute() and (ROOT/name).resolve().is_relative_to(ROOT),'Only ROOT-relative small source bindings')
        small(ROOT/name,digest,parse=False)
    check(tiny['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and tiny['test_exit_code']==0
        and tiny['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0) and not tiny['market_inputs_read'],'Exactly one new synthetic boundary case')
    check(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['all_planned_ledgers_complete']
        and actual['completed_ledgers']==actual['planned_ledgers']==3 and actual['accepted_smoke_sha256']==tiny_sha
        and actual['binding']['protocol_sha256']==protocol_sha and len(actual['folds'])==1,'Full new three-account actual completed, not preview')
    check(audit['status']==AUDIT_STATUS and audit['completed_ledgers_verified']==3
        and audit['binding']['actual_reports']=={ACTUAL:actual_sha},'Actual independent numerical/causal proof')
    _,checker_sha=small(args.audit_source,audit['binding']['checker_sha256'],parse=False)
    check(checker_sha==audit['independent_source_sha256'],'Executed independent checker bytes')
    tasks={'source':closed(source),'tiny':closed(tiny),'actual':closed(actual),'audit':closed(audit)}
    check(len({r['task']['id'] for r in tasks.values()})==4 and stamp(tasks['tiny']['task']['started_at'])>=stamp(tasks['source']['task']['ended_at'])
        and stamp(tasks['actual']['task']['started_at'])>=stamp(tasks['tiny']['task']['ended_at'])
        and stamp(tasks['audit']['task']['started_at'])>=stamp(tasks['actual']['task']['ended_at']),'Distinct tasks truly closed0 in execution order')
    fold=actual['folds'][0];check(fold['status']=='COMPLETE_PROXY_COMPARISON' and fold['days']==547 and len(fold['results'])==3,'One uninterrupted547day account per strategy')
    rows={r['strategy']:r for r in fold['results']};ledgers={r['strategy']:r for r in audit['ledgers']}
    check(len(rows)==len(ledgers)==len(audit['ledgers'])==3 and set(rows)==set(ledgers)==set(STRATEGIES),'No missing/extra/selected ledger')
    work=Path(actual['run_dir']).resolve();check(work.is_relative_to(STATE),'New isolated STATE only')
    run_binding,run_binding_sha=small(work/'RUN_BINDING.json',actual['run_binding_sha256'])
    check(run_binding==actual['binding'],'Completed run binding remains exact, no price content read')
    summaries={};months={};artifacts={};targets={}
    for strategy in STRATEGIES:
        row=rows[strategy];proof=ledgers[strategy];summary=row['summary'];directory=Path(row['directory']).resolve()
        check(directory.is_relative_to(work) and row['spread_bps']==proof['spread_bps']==8 and row['nominal_roundtrip_bps']==36
            and proof['fold']==fold['fold'] and proof['period_days']==proof['completed_days_verified']==summary['period_days']==summary['days']==547
            and proof['completed_minutes_verified']==787680 and proof['completed_months_verified']==18,'Complete fixed cost/date ledger')
        for key,audit_key in METRICS.items():near(summary[key],proof[audit_key],1e-10 if key in ('max_observed_minute_MDD','max_drawdown','turnover') else 1e-7)
        near(proof['sparse_Decimal_settlement']['maximum_Decimal_cash_error_USDT'],0,1e-7)
        check(summary['trade_count']==proof['trade_count'] and [m['month'] for m in proof['months']]==MONTHS,'All observed trades and18months retained')
        check(summary['annualized_return_is_descriptive_only'] and not summary['net_long_term_CAGR_proven']
            and not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven']
            and not summary['real_BBO'] and summary['fee_settlement_version']=='BYBIT_SPOT_RECEIVED_ASSET_V1','No longAPR/native/BBO or investment qualification')
        check(set(row['artifacts'])=={'daily_nav.parquet','trades.parquet','orders.parquet','round_trips.parquet','minute_nav_inventory.parquet','config_and_summary.json'}
            and {name:value['sha256'] for name,value in row['artifacts'].items()}==proof['ledger_artifact_hashes'],'Exact independently verified six saved artifacts')
        artifacts[strategy]={name:byte_hash(directory/name,item['sha256'],work,item['bytes']) for name,item in row['artifacts'].items()}
        target_dir=directory.parent;targets[strategy]={}
        for key,name in [('target_sha256','targets.parquet'),('intent_sha256','intent_calendar.parquet'),('receipt_sha256','target_receipt.json')]:
            targets[strategy][name]=byte_hash(target_dir/name,proof['target_bindings'][key],work)
        receipt,_=small(target_dir/'target_receipt.json',proof['target_bindings']['receipt_sha256'])
        check(receipt['strategy_id']==strategy and receipt['decision_count']==787680 and not receipt['warmup_failed'] and receipt['paired_comparison_allowed'],'Actual common full target calendar')
        summaries[strategy]=summary;months[strategy]=proof['months']
    check(actual['candidate_status']=='NO_QUALIFIED_CANDIDATE' and not actual['locked_consumed']
        and actual['market_models_fit']==actual['orders_sent']==0 and actual['source_bytes_unchanged'],'No fit/order/locked/candidate promotion')
    bounded(source['resources_after']);bounded(actual['resources']);bounded(tiny['resources']);check(actual['disk']['status']=='OK' and actual['owned_bytes']<=spec['maximum_new_owned_bytes']<=400_000_000,'Recorded runtime/STATE budget, no new scan')
    value=dict(status='PASS_ROOT_D033_547D_THREE_ACCOUNT_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR',created_utc=datetime.now(UTC).isoformat(),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own_sha),
        root_helper=dict(path=str(Path(__file__).resolve()),sha256=own_sha,archive=ARCHIVE),source_hashes=hashes,
        small_reports={str(protocol.relative_to(ROOT)):protocol_sha,ACTUAL:actual_sha,AUDIT:audit_sha,spec['required_smoke_receipt']:tiny_sha,spec['source_receipt']:source_sha},
        actual_run_binding=dict(path=str(work/'RUN_BINDING.json'),sha256=run_binding_sha),
        actual_task_copies=tasks,actual_host_results=dict(source=args.source_host,tiny=args.tiny_host,actual=args.actual_host,audit=args.audit_host),independent_checker=dict(path=str(args.audit_source.resolve()),sha256=checker_sha),
        completed_accounts=3,period_days=547,source_files=38,source_days_per_symbol=578,score_minutes_per_asset=787680,source_rows=1664640,
        financial_summaries=summaries,months_from_independent_saved_audit=months,independent_ledgers=audit['ledgers'],
        net_PnL_difference_vs_cash={s:summaries[s]['net_cash_PnL']-summaries['CASH']['net_cash_PnL'] for s in STRATEGIES},
        ledger_byte_bindings=artifacts,target_byte_bindings=targets,output_bytes_SHA_reverified=True,source_rows_or_financial_math_or_old_green_tests_replayed=False,
        independent_all_event_drawdown_verified=False,same_caps_not_equal_realized_risk=True,monthly_winners_or_independent_curves_concatenated=False,
        capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE',native_account_certified=False,unseen_qualification=False,
        actual_resources=actual['resources'],actual_disk=actual['disk'],actual_elapsed_seconds=actual['elapsed_seconds'],actual_peak_RSS_bytes=actual['orchestrator_peak_RSS_bytes'],
        owned_actual_bytes=actual['owned_bytes'],root_resources=own_resources,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=value['status'],output=str(out),sha256=small(out)[1])))

if __name__=='__main__':main()
