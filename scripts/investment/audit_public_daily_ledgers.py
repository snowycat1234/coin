"""D037: one independent check of three new daily-signal native Spot accounts.

The accepted D033 numerical financial body and sparse Decimal settlement are
reused. Only source/period bindings and an independent daily target oracle are
new. No production simulator/target generator, old account replay, ZIP or QA.
CLI: --binding STATE/ACTUAL_BINDING.json --run-dir STATE --output ROOT/report.
"""
from pathlib import Path
from datetime import UTC, date, datetime, timedelta
import argparse, gc, hashlib, importlib.util, json, os, resource, signal, sys, time, traceback
import numpy as np
import polars as pl
import pyarrow.parquet as pq
from quant import resources

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
REUSE='docs/archive/PUBLIC_LONG_547D_USED_INDEPENDENT_SOURCES_20261003_V3/reuse_blocks.py'
REUSE_SHA='be46b204780a4c9ad39c905fda9c8dd131229e78bc31dbbf598a59d6646c9ea1'
CORE='docs/archive/CONDITIONAL_CARRY_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'
CORE_SHA='3aecda837532e020e99c9ab2608200477262683511b7518c7c48afac384834d1'
TARGET='docs/archive/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py'
TARGET_SHA='3a944f46e89600c90886053376fe2224683664e30985f3a11b089d0fd51a4d85'
STRATEGY='COIN_JESSE_DONCHIAN_1D_SPOT_ADAPTER'; MINUTE=60_000_000; DAY=86_400_000_000
FEE_SHA='d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f'
FINANCE_AST='39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73'
SOURCE_REPORT='reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ACTUAL_20261003_V2.json'
SOURCE_STATUS='PASS_D037_OFFICIAL_SPOT_DAILY_SOURCE_FORMAT_AND_CALENDAR_ONLY'
OUT=ROOT/'reports/fast_research/PUBLIC_DONCHIAN_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json'
SUCCESS='PASS_D037_THREE_DAILY_PUBLIC_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
CASES=(('CONT547','547D','2024-01-01','2025-07-01',547,1664640),
       ('CONT122','122D','2025-08-01','2025-12-01',122,440640),
       ('CONT90','90D','2025-12-01','2026-03-01',90,348480))
STARTED=time.monotonic(); MAX_RSS=3_500_000_000

def need(value,message):
    if not bool(value):raise ValueError(message)
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def imported(path,digest,name):
    need(sha(path)==digest,'Exact independent method source SHA')
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def stamp(value):return int(datetime.combine(date.fromisoformat(value),datetime.min.time(),UTC).timestamp())*1_000_000
def scalar(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)
def write(g,path,value):return g.write(path,json.loads(json.dumps(value,allow_nan=False,default=scalar)))
def budget():
    need(time.monotonic()-STARTED<=600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=MAX_RSS,'Prebound600s/3.5GB independent budget')

def daily_source(g,spec):
    reference=spec['daily_source_receipt']
    need(reference['path']==SOURCE_REPORT and reference['required_status']==SOURCE_STATUS,'Fixed official1d source-only reference')
    proof,digest=g.small(g.project(reference['path']),reference['sha256']);task=g.closed(proof['binding']['task_id'])
    need(proof['status']==SOURCE_STATUS and proof['completed_files']==proof['source_files']==66
        and proof['actual_daily_rows']==proof['actual_total_rows']==2008 and proof['days_per_symbol']==1004
        and proof['full_common_calendar'] and proof['source_bytes_unchanged'],'True complete66-file/1004-day source-only provenance')
    need(not proof['old_1m_QA_repeated'] and not proof['old_database_written'] and not proof['locked_consumed']
        and not proof['publication_time_certified'] and proof['models_fit']==proof['orders_sent']==proof['GPU']==0,'Source format acceptance is not publication/market qualification')
    source_spec,proto_sha=g.small(proof['binding']['protocol_path'],proof['binding']['protocol_sha256'])
    run=Path(source_spec['run_dir']);binding,rb_sha=g.small(run/'RUN_BINDING.json',proof['run_binding_sha256'])
    need(binding==proof['binding'] and run.parent==STATE and run.name.startswith('d037-official-spot-daily-source-'),'Dynamic actually bound source directory, not failedV1')
    need(binding['source_hashes']==source_spec['frozen_sources'],'Actual source code/protocol map')
    for name,value in binding['source_hashes'].items():g.small(g.project(name),value,False)
    records=proof['sources'];months=[f'{year}-{month:02d}' for year in (2023,2024,2025,2026) for month in range(1,13) if '2023-06'<=f'{year}-{month:02d}'<='2026-02']
    need(len(records)==66 and {(r['symbol'],r['month']) for r in records}=={(s,m) for s in ('BTCUSDT','ETHUSDT') for m in months},'Exact66 unique symbol-month source universe')
    for row in records:
        path=Path(row['normalized_path']);need(path==run/(row['symbol']+'-'+row['month'])/'source.parquet','Approved daily path from true source binding')
        for ancestor in (path,*path.parents):
            need(not ancestor.is_symlink(),'No daily source path symlinks')
            if ancestor==STATE:break
        need(path.is_file() and path.stat().st_size==row['normalized_bytes'] and sha(path)==row['normalized_sha256'],'Accepted normalized source byte identity, no CRC/QA replay')
    g.bounded(proof['resources_before']);g.bounded(proof['resources_after'])
    return proof,dict(path=reference['path'],sha256=digest,protocol_sha256=proto_sha,run_binding_sha256=rb_sha,actual_task=task,
        completed_daily_signal_files_verified=66,full_daily_source_rows=2008,publication_availability_certified=False,old_1m_QA_repeated=False)

def metadata(g,item,fixed):
    fold,period,start,end,days,rows=fixed
    proto=f'protocols/PUBLIC_DONCHIAN_DAILY_{fold}_20261003_V1.json'
    report=f'reports/fast_research/PUBLIC_DONCHIAN_DAILY_{period}_ACTUAL_20261003_V1.json'
    need(item['fold']==fold and item['protocol_path']==proto and item['actual_report']==report,'One exact preregistered case selector')
    spec,proto_sha=g.small(g.project(proto),item['protocol_sha256']);actual,report_sha=g.small(g.project(report),item['actual_report_sha256'])
    task=g.closed(item['actual_task_id']);need(actual['binding']['task_id']==item['actual_task_id'],'Manifest binds true completed new research task')
    need(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['completed_ledgers']==actual['planned_ledgers']==1
        and actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'],'One complete fresh daily ledger, not a partial result')
    run=Path(actual['run_dir']);binding,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256'])
    need(binding==actual['binding'] and binding['protocol_sha256']==proto_sha and binding['fits']==actual['market_models_fit']==0
        and actual['orders_sent']==0 and not actual['locked_consumed'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Actual unchanged binding/no fits/orders/locked/candidate')
    need(spec['strategy_ids']==binding['strategies']==[STRATEGY] and spec['planned_ledgers']==1
        and spec['folds']==binding['all_folds']==[dict(id=fold,period_start=start,period_end_exclusive=end)],'Only one daily sleeve and fixed full seen period')
    need(spec['costs']['spread_bps']==[8] and spec['costs']['nominal_roundtrip_bps']==[36] and spec['costs']['fee_bps_per_side']==10
        and spec['costs']['slippage_bps_per_side']==4 and actual['fee_settlement']==spec['fee_settlement']=='BYBIT_SPOT_RECEIVED_ASSET_V1'
        and actual['fee_profile_sha256']==spec['fee_profile_sha256']==FEE_SHA,'Original conservative36bp/native received-asset fee settlement')
    parent,_=g.small(g.project(spec['namespace_parent_protocol']['path']),spec['namespace_parent_protocol']['sha256'])
    for key in ('common_config','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type','source_receipt','source_receipt_sha256'):
        need(spec[key]==parent[key],'Original parent capital/risk/fee/minute source unchanged: '+key)
    need(spec['common_config']['initial_cash']==10000 and spec['strategy_rules']['timeframe_minutes']==1440
        and spec['strategy_rules']['channel_period']==20 and spec['strategy_rules']['SMA_period']==200
        and spec['strategy_rules']['fresh_flat_each_scoring_period'] and not spec['strategy_rules']['warmup_positions'],'Fixed daily recipe/fresh-flat/10k capital')
    need(actual['fee_derivation']['derived_AST_SHA256']==FINANCE_AST,'Original native financial kernel unchanged')
    hashes=binding['source_hashes'];need(hashes.get(proto)==proto_sha and all(hashes.get(p)==d for p,d in spec['frozen_sources'].items()),'Exact new research source union')
    for name,value in hashes.items():g.small(g.project(name),value,False);g.small(run/'source-snapshot'/name,value,False)
    tiny,tiny_sha=g.small(g.project(spec['required_smoke_receipt']),actual['accepted_smoke_sha256']);g.closed(tiny['binding']['task_id'])
    tb,tb_sha=g.small(Path(tiny['run_dir'])/'RUN_BINDING.json',tiny['run_binding_sha256'])
    need(tb==tiny['binding'] and old_shared(tb['source_hashes'])==old_shared(hashes),'Exact shared newcase source pins across three periods')
    g.small(Path(tiny['run_dir'])/'junit.xml',tiny['junit_sha256'],False)
    need(tiny['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and tiny['test_exit_code']==0
        and tiny['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0),'Exactly the new integrated onecase, no old suite replay')
    need(spec['smoke_test_path']=='tests/test_public_donchian_daily.py' and tiny['registration_start']['hyperparameters']==spec['common_config']
        and tiny['registration_start']['cost_assumptions']==spec['costs'] and tiny['registration_start']['thresholds']==spec['strategy_rules'],'Same newcase risk/cost/daily recipe')
    reference=spec['reused_minute_input'];prior,_=g.small(g.project(reference['report_path']),reference['report_sha256'])
    need(reference==dict(report_path=reference['report_path'],report_sha256=reference['report_sha256'],path=prior['minute_source']['path'],sha256=prior['minute_source']['sha256'])
        and prior['minute_source']['rows']==rows and actual['reused_minute_input']==reference and actual['raw_normalized_market_files_read'] is False,'Exact accepted parent derivative, no raw1m source reread')
    entry=item['production_entrypoint'];runner=imported(g.project(entry),hashes[entry],'d037_private_metadata_'+fold)
    need(runner.context(spec)['PERIOD_DERIVATION']==actual['period_namespace_derivation'],'All private date/dispatch ASTs precompiled before arrays')
    folds=actual['folds'];need(len(folds)==1 and folds[0]['fold']==fold and folds[0]['start_us']==stamp(start)
        and folds[0]['end_us']==stamp(end) and folds[0]['days']==days and folds[0]['status']=='COMPLETE_PROXY_COMPARISON'
        and len(folds[0]['results'])==1,'Complete continuous single-account period')
    row=folds[0]['results'][0];need(row['strategy']==STRATEGY and row['spread_bps']==8 and row['nominal_roundtrip_bps']==36,'Unique original-cost daily ledger')
    return spec,actual,dict(period=period,fold=fold,actual_task=task,actual_report_sha256=report_sha,protocol_sha256=proto_sha,smoke_sha256=tiny_sha,verified_source_hashes=hashes)

def old_shared(hashes):
    return {k:v for k,v in hashes.items() if k.startswith(('src/','scripts/','tests/','environments/','third_party/')) or k in ('protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json','protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json')}

def minute_input(actual,fold,spec,fixed):
    identifier,period,start,end,days,count=fixed;run=Path(actual['run_dir']);ipc=Path(fold['minute_input_path']);parquet=Path(actual['minute_source']['path'])
    need(ipc==run/(identifier+'-minute-input.arrow') and parquet==run/'shared_source_minutes.parquet'
        and sha(ipc)==fold['minute_input_sha256'] and sha(parquet)==actual['minute_source']['sha256']
        and fold['minute_input_format']=='IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION','New immutable physical input files, no IPC reserialization')
    frame=pl.read_ipc(ipc,memory_map=False);need(frame.height==actual['minute_source']['rows']==count and actual['minute_source']['invalid_minutes']==0,'Exact accepted derivative count')
    reference=spec['reused_minute_input'];need(sha(reference['path'])==reference['sha256'],'Parent Parquet bytes remain exact')
    for path in (parquet,Path(reference['path'])):
        offset=0
        for batch in pq.ParquetFile(path).iter_batches(batch_size=32768):
            part=pl.from_arrow(batch);need(part.schema==frame.schema and part.equals(frame.slice(offset,len(part))),'New Arrow/new Parquet/accepted parent exact logical values and schema')
            offset+=len(part)
        need(offset==len(frame),'Complete source logical comparison')
    need(frame['minute_valid'].null_count()==frame['valid_day'].null_count()==0 and frame['minute_valid'].all() and frame['valid_day'].all()
        and frame['missing_reason'].null_count()==frame.height,'Complete accepted source eligibility, no fill/drop')
    for field in ('open_us','close_us','available_us'):need(frame.schema[field]==pl.Int64 and frame[field].null_count()==0,'Known integer minute times')
    need(np.array_equal(frame['close_us'].to_numpy(),frame['open_us'].to_numpy()+MINUTE)
        and np.array_equal(frame['available_us'].to_numpy(),frame['close_us'].to_numpy()),'Original completed-close availability proxy')
    for field in ('open','high','low','close','quote_volume'):
        values=frame[field].to_numpy();need(np.isfinite(values).all() and np.all(values>=0 if field=='quote_volume' else values>0),'Finite accounting primitives')
    need(set(frame['symbol'].unique().to_list())=={'BTCUSDT','ETHUSDT'},'Exactly the original two coins')
    for symbol in ('BTCUSDT','ETHUSDT'):
        need(np.array_equal(frame.filter(pl.col('symbol')==symbol)['open_us'].to_numpy(),np.arange(stamp(start)-31*DAY,stamp(end),MINUTE,dtype=np.int64)),'Complete31day risk warmup/source calendar')
    return frame,dict(fold=identifier,source_rows_verified=count,arrow_sha256=sha(ipc),new_parquet_sha256=sha(parquet),parent_parquet_sha256=reference['sha256'],logical_values_equal=True,IPC_reserialization_performed=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('binding','run-dir','output'):parser.add_argument('--'+arg,type=Path,required=True)
    args=parser.parse_args();g=imported(ROOT/GUARD,GUARD_SHA,'d037_small_guards');work=args.run_dir.resolve()
    need(os.environ.get('COIN_TASK_ID') and work.parent==STATE and work.name.startswith('d037-') and work.is_dir()
        and not (work/'RUN_BINDING.json').exists() and args.output.resolve()==OUT and not OUT.exists(),'Exclusive actual bounded/progress audit, preboundSTATE only')
    plan,plan_sha=g.small(args.binding.resolve());need(args.binding.resolve()==work/'ACTUAL_BINDING.json' and plan['checker_sha256']==sha(__file__)
        and plan['maximum_independent_RSS_bytes']==MAX_RSS and plan['maximum_wall_seconds']==600,'Exact independent prebinding/budgets')
    need(Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Locked cleanCPU2 environment')
    rb=imported(ROOT/REUSE,REUSE_SHA,'d037_accepted_native_finance');verify,old,proof=rb.prepared_financial()
    core=imported(ROOT/CORE,CORE_SHA,'d037_sparse_decimal');oracle=imported(ROOT/TARGET,TARGET_SHA,'d037_independent_daily_oracle')
    old.sha=sha;verify.__globals__['sha']=sha
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),guard_source_sha256=GUARD_SHA,reuse_blocks_sha256=REUSE_SHA,
        target_oracle_sha256=TARGET_SHA,actual_manifest_path=str(args.binding.resolve()),actual_manifest_sha256=plan_sha,
        actual_reports={str(ROOT/i['actual_report']):i['actual_report_sha256'] for i in plan['cases']},python=sys.executable,sys_prefix=sys.prefix,exact_command=' '.join(sys.argv))
    rb_sha,_=write(g,work/'RUN_BINDING.json',binding)
    audit=dict(status='FAIL_D037_THREE_DAILY_PUBLIC_LEDGER_AUDIT',binding=binding,run_binding_sha256=rb_sha,independent_source=str(Path(__file__).resolve()),independent_source_sha256=sha(__file__),
        financial_AST_precompile=proof,original_proof_metadata_declares_days=547,actual_invocation_days=[547,122,90],ledgers=[],cases=[],runtime_inputs=[],target_causality=[],verified_source_hashes={},
        completed_ledgers_verified=0,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',native_account_certified=False,original_simulator_or_fixed_targets_called=False,
        old_control_accounts_replayed=False,raw1m_QA_or_ZIP_CRC_repeated=False,all_event_drawdown_verified=False,full_financial_numerics='ACCEPTED_NUMPY_ASSERTIONS',sparse_Decimal_scope='RECORDED_NATIVE_SPOT_SETTLEMENT_ONLY')
    signal.signal(signal.SIGTERM,lambda *a:(_ for _ in ()).throw(TimeoutError('Bounded audit terminated')))
    try:
        audit['resources_before']=resources.status();g.bounded(audit['resources_before']);need(len(plan['cases'])==3,'Exactly three fixed cases')
        contexts=[metadata(g,item,fixed) for item,fixed in zip(plan['cases'],CASES,strict=True)]
        source,source_meta=daily_source(g,contexts[0][0]);audit['daily_source_binding']=source_meta
        need(all(spec['daily_source_receipt']==contexts[0][0]['daily_source_receipt'] for spec,actual,meta in contexts),'One shared actually completed official1d source')
        daily_hashes={};full_daily=[]
        for row in source['sources']:
            frame=pl.read_parquet(row['normalized_path']);need(frame.height==row['rows'],'Bound daily file row count')
            full_daily.append(frame);daily_hashes[row['normalized_path']]=row['normalized_sha256']
        daily=pl.concat(full_daily).sort(['symbol','open_us']);del full_daily,frame;budget()
        for fixed,(spec,actual,meta) in zip(CASES,contexts,strict=True):
            fold_id,period,start,end,days,count=fixed;fold=actual['folds'][0];audit['cases'].append(meta);audit['verified_source_hashes'][fold_id]=meta['verified_source_hashes']
            frame,input_proof=minute_input(actual,fold,spec,fixed);audit['runtime_inputs'].append(input_proof)
            calendar=np.arange(stamp(start),stamp(end),MINUTE,dtype=np.int64);directory=Path(actual['run_dir'])/(fold_id+'-'+STRATEGY)
            target=pl.read_parquet(directory/'targets.parquet');intent=pl.read_parquet(directory/'intent_calendar.parquet');receipt,_=g.small(directory/'target_receipt.json')
            need(receipt['targets_sha256']==old.frame_sha(target) and receipt['daily_source_input_binding']==fold['daily_signal_source'],'Bound saved target/daily source receipt')
            signal_frame=daily.filter((pl.col('open_us')>=stamp(start)-200*DAY)&(pl.col('open_us')<stamp(end)))
            causal=oracle.verify_saved_targets(signal_frame,calendar,intent,target,receipt)
            warmup_start=(date.fromisoformat(start)-timedelta(days=200)).isoformat()
            selected=sorted([r for r in source['sources'] if warmup_start[:7]<=r['month']<end[:7]],key=lambda r:(r['month'],r['symbol']))
            expected_selected=[{k:r[k] for k in ('symbol','month','normalized_path','normalized_sha256','rows')} for r in selected]
            need(fold['daily_signal_source']['selected_sources']==expected_selected and fold['daily_signal_source']['source_receipt']==spec['daily_source_receipt'],'Exact bound monthly daily signal subset')
            need(signal_frame.height==fold['daily_signal_source']['rows'] and fold['daily_signal_source']['warmup_start']==warmup_start
                and not fold['daily_signal_source']['daily_prices_used_for_execution_or_risk'],'Same exact200day signal source, separate minute execution')
            target_bound={STRATEGY:dict(target_sha256=sha(directory/'targets.parquet'),intent_sha256=sha(directory/'intent_calendar.parquet'),receipt_sha256=sha(directory/'target_receipt.json'))}
            audit['target_causality'].append(dict(fold=fold_id,**target_bound[STRATEGY],**causal));del signal_frame,intent,target,calendar;gc.collect();budget()
            close_times=np.arange(stamp(start)+MINUTE,stamp(end)+MINUTE,MINUTE,dtype=np.int64)
            per={s:frame.filter((pl.col('symbol')==s)&(pl.col('open_us')>=stamp(start))).select('open','close') for s in old.SYMS}
            capacity=frame.select('symbol','quote_volume');del frame;gc.collect()
            row=fold['results'][0];entry=verify(row,fold,spec,actual,audit,stamp(start),stamp(end),days,capacity,per,close_times,target_bound)
            entry['sparse_Decimal_settlement']=rb.sparse_decimal(row,per,core,stamp(start),stamp(end))
            audit['completed_ledgers_verified']+=1;print('Verified new daily account '+fold_id,flush=True);del capacity,per,close_times;gc.collect();budget()
        need(len(audit['ledgers'])==3 and {(x['fold'],x['strategy'],x['spread_bps']) for x in audit['ledgers']}=={(f[0],STRATEGY,8) for f in CASES},'All three unique new accounts, no skipped window')
        need(sum(len(x['months']) for x in audit['ledgers'])==25 and sum(x['period_days'] for x in audit['ledgers'])==759,'All25 monthly periods and759 verified account-days')
        for path,digest in daily_hashes.items():need(sha(path)==digest,'Final daily source bytes remain unchanged')
        for item in plan['cases']:g.small(g.project(item['actual_report']),item['actual_report_sha256']);g.small(g.project(item['protocol_path']),item['protocol_sha256'])
        for hashes in audit['verified_source_hashes'].values():
            for path,digest in hashes.items():g.small(g.project(path),digest,False)
        owned=sum(p.stat().st_size for p in work.rglob('*') if p.is_file());need(owned<=10_000_000,'Small independent metadata-only footprint')
        audit.update(status=SUCCESS,completed_minutes_verified=1_092_960,completed_days_verified=759,completed_months_verified=25,completed_daily_signal_files_verified=66,
            completed_accepted_minute_source_file_references=58,original_normalized_minute_market_files_reread=0,owned_bytes=owned,maximum_independent_RSS_bytes=MAX_RSS,maximum_wall_seconds=600)
    except Exception as error:
        audit.update(error_type=type(error).__name__,reason=str(error),traceback=traceback.format_exc());raise
    finally:
        audit.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-STARTED,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_after=resources.status())
        digest,_=write(g,OUT,audit);print(str(OUT)+' '+digest,flush=True)

if __name__=='__main__':main()
