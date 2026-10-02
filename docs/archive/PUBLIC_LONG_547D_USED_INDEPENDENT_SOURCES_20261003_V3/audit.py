"""D033: three new native Spot ledgers, accepted numerical finance plus sparse Decimal settlement.
No strategy/backtester replay, old account arrays, original ZIP/QA, or registry writes.
"""
from pathlib import Path
from datetime import UTC,datetime
import gc,hashlib,json,os,resource,signal,sys,time,traceback
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl
import pyarrow.parquet as pq
import reuse_blocks as rb
ROOT=rb.ROOT;STATE=Path(__file__).resolve().parent
OUT=ROOT/'reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json'
MANIFEST=STATE/'ACTUAL_BINDING.json'
PROTO=ROOT/'protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json'
ACTUAL=ROOT/'reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json'
CORE='docs/archive/CONDITIONAL_CARRY_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'
CORE_SHA='3aecda837532e020e99c9ab2608200477262683511b7518c7c48afac384834d1'
SUCCESS='PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
STARTED=time.monotonic();MAX_RSS_BYTES=3500000000
def sha(path):
    d=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):d.update(b)
    return d.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def need(ok,message):
    if not bool(ok):raise ValueError(message)
def write(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False,default=scalar)
def scalar(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)
def budget():
    need(time.monotonic()-STARTED<600,'Prebound 600-second independent audit budget')
    need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=MAX_RSS_BYTES,'Prebound 3.5GB independent peak RSS under shared5GB cgroup')
def terminated(signum,frame):raise TimeoutError('Actual independent audit externally terminated: '+str(signum))
def existing_task(task_id):
    path=Path('/home/xflops/coin-state/task-progress')/('task-'+task_id+'.json');t=read(path)
    need(t['id']==task_id and t['status']=='completed' and t['exit_code']==0 and t['pid']>0 and t['start_ticks']>0,'True closed0 task required before arrays')
    return dict(path=str(path),sha256=sha(path),task=t)
def source_proof(spec,actual,manifest):
    path=ROOT/spec['source_receipt'];receipt=read(path)
    need(sha(path)==spec['source_receipt_sha256']==actual['source_receipt_sha256']==manifest['source_receipt_sha256'],'Exact accepted38 source receipt')
    task=existing_task(receipt['binding']['task_id']);need(task['task']['id']==manifest['source_task_id'],'Prebound source actual task')
    need(receipt['status']=='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR' and receipt['source_files']==38 and receipt['actual_minute_rows']==1664640 and receipt['days_per_symbol']==578,'Sealed38 byte-reuse scope')
    need(receipt['source_scope']==spec['source_scope']=='DEC2023_JUN2025' and receipt['source_calendar']==spec['source_calendar'],'Full Dec2023-Jun2025 source scope')
    need(not receipt['market_price_rows_read'] and not receipt['fresh_QA_performed'] and not receipt['raw_ZIP_or_CRC_read'] and not receipt['locked_consumed'],'Accepted scope is byte reuse, not fresh QA')
    records=receipt['sources'];expected={(s,m) for s in ('BTCUSDT','ETHUSDT') for m in spec['source_calendar']}
    need(len(records)==38 and {(r['symbol'],r['month']) for r in records}==expected,'Exact source allowlist, no Jul2025 or locked market')
    for row in records:
        need(row['current_normalized_sha256']==row['normalized_sha256'] and row['row_count_verification']=='REUSED_SEALED_QA_EXACT_BYTE_SHA_NOT_ROWS_REREAD','Source byte identity and old row qualification')
        need(row['timestamp_unit']==row['old_quality']['timestamp_unit'],'Old ms/us units retained without reconversion')
    return dict(path=str(path),sha256=sha(path),actual_task=task,completed_source_files_verified=38,
        original_normalized_market_files_read_by_independent_auditor=False,fresh_QA_CRC_performed=False,
        normalized_sha256={r['normalized_path']:r['normalized_sha256'] for r in records})
def metadata(manifest,old):
    need(Path(manifest['actual_report'])==ACTUAL and Path(manifest['protocol_path'])==PROTO,'One explicit prebound D033 actual selector')
    need(sha(ACTUAL)==manifest['actual_report_sha256'] and sha(PROTO)==manifest['protocol_sha256'],'Actual/protocol hash before arrays')
    actual=read(ACTUAL);spec=read(PROTO);run=Path(actual['run_dir']);binding=read(run/'RUN_BINDING.json')
    need(binding==actual['binding'] and sha(run/'RUN_BINDING.json')==actual['run_binding_sha256'],'Actual RUN_BINDING exact bytes')
    task=existing_task(binding['task_id']);need(binding['task_id']==manifest['actual_task_id'],'Prebound actual closed0')
    need(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['completed_ledgers']==3 and actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'],'Three complete frozen new actual accounts')
    need(binding['fits']==actual['market_models_fit']==0 and not actual['locked_consumed'] and actual['orders_sent']==0 and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Seen proxy scope only')
    need(spec['planned_ledgers']==binding['planned_ledgers']==3 and tuple(spec['strategy_ids'])==tuple(binding['strategies'])==rb.SLEEVES and binding['all_folds']==spec['folds'],'Exactly three fixed strategies and one cost')
    need(spec['folds']==[dict(id='CONT547',period_start='2024-01-01',period_end_exclusive='2025-07-01')] and spec['warmup_days']==31 and len(actual['folds'])==1,'547 continuous days plus31 warmup')
    need(spec['costs']['spread_bps']==[8] and spec['costs']['nominal_roundtrip_bps']==[36] and spec['costs']['fee_bps_per_side']==10 and spec['costs']['slippage_bps_per_side']==4,'Same frozen36bp scenario')
    hashes=binding['source_hashes'];need(all(hashes.get(p)==d for p,d in spec['frozen_sources'].items()),'Actual protocol source union')
    for relative,digest in hashes.items():
        p=ROOT/relative;need(p.resolve().is_relative_to(ROOT) and sha(p)==digest and sha(run/'source-snapshot'/relative)==digest,'Current/source-snapshot dependency binding')
    need(binding['protocol_sha256']==sha(PROTO) and hashes.get(str(PROTO.relative_to(ROOT)))==sha(PROTO),'Selected frozen protocol in actual source union')
    tiny_path=ROOT/spec['required_smoke_receipt'];tiny=read(tiny_path);tb=read(Path(tiny['run_dir'])/'RUN_BINDING.json')
    need(tb==tiny['binding'] and sha(Path(tiny['run_dir'])/'RUN_BINDING.json')==tiny['run_binding_sha256'] and sha(tiny_path)==actual['accepted_smoke_sha256']==manifest['smoke_sha256'],'Exact sole new tiny binding')
    tiny_task=existing_task(tb['task_id']);need(tb['task_id']==manifest['smoke_task_id'],'Prebound new boundary task0')
    need(tiny['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and old.shared(tb['source_hashes'])==old.shared(hashes),'Exact shared native strategy code smoke')
    need(tiny['registration_start']['hyperparameters']==spec['common_config'] and tiny['registration_start']['cost_assumptions']==spec['costs'] and tiny['registration_start']['thresholds']==spec['strategy_rules'],'Exact common risk/cost/strategy economics')
    junit=Path(tiny['run_dir'])/'junit.xml';tree=ET.parse(junit).getroot();counts={k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    need(counts==dict(tests=1,failures=0,errors=0,skipped=0) and sha(junit)==tiny['junit_sha256'],'One new boundary case; old greens reused')
    deriv=actual['fee_derivation'];need(deriv['derived_AST_SHA256']=='39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73' and sha(deriv['derived_source_path'])==deriv['derived_source_file_sha256']=='a33c4f392c033d44224be5f64a42456b529e973d9af0925c8a454043f2762a8f' and sha(deriv['receipt_path'])==deriv['receipt_sha256'],'Native fee financial kernel unchanged')
    need(actual['fee_settlement']==spec['fee_settlement']=='BYBIT_SPOT_RECEIVED_ASSET_V1' and actual['fee_profile_sha256']==spec['fee_profile_sha256']=='d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f','Native received-asset fees, no doublefee')
    # All private date/cost alias ASTs compile before the first array read.
    relative='scripts/investment/public_long_development_adapter.py';adapter=rb.imported(ROOT/relative,hashes[relative],'d033_frozen_date_namespace')
    namespace=adapter.context(spec);need(namespace['PERIOD_DERIVATION']==actual['period_namespace_derivation'],'Every production private date/source/cost AST mapping matches actual')
    source=source_proof(spec,actual,manifest)
    return actual,spec,dict(actual_task=task,actual_smoke_task=tiny_task,fresh_synthetic_cases=counts,
        protocol_sha256=sha(PROTO),verified_source_hashes=hashes,source=source,
        date_alias_ASTs_precompiled_before_arrays=True,period_namespace_derivation=actual['period_namespace_derivation'])
def actual_input(actual,fold,start,end):
    path=Path(fold['minute_input_path']);parquet=Path(actual['minute_source']['path']);run=Path(actual['run_dir'])
    need(path==run/'CONT547-minute-input.arrow' and parquet==run/'shared_source_minutes.parquet','Only newly bound derived physical inputs')
    need(sha(path)==fold['minute_input_sha256'] and sha(parquet)==actual['minute_source']['sha256'] and fold['minute_input_format']=='IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION','Physical Parquet and Arrow SHA, never reserialized digest')
    frame=pl.read_ipc(path,memory_map=False);need(frame.height==actual['minute_source']['rows']==1664640 and actual['minute_source']['invalid_minutes']==0,'578 paired source days')
    pf=pq.ParquetFile(parquet);offset=0
    for batch in pf.iter_batches(batch_size=32768):
        part=pl.from_arrow(batch);need(part.schema==frame.schema and part.equals(frame.slice(offset,len(part))),'Exact logical source values across physical Parquet/Arrow')
        offset+=len(part)
    need(offset==len(frame),'Complete source comparison, no clipped rows')
    required={'symbol','open_us','close_us','available_us','open','high','low','close','quote_volume','minute_valid','valid_day','missing_reason'}
    need(required<=set(frame.columns) and set(frame['symbol'].unique().to_list())=={'BTCUSDT','ETHUSDT'},'Exact accounting/causal source schema')
    need(frame['minute_valid'].null_count()==0 and frame['minute_valid'].all() and frame['valid_day'].null_count()==0 and frame['valid_day'].all() and frame['missing_reason'].null_count()==len(frame),'No unknown/missing source admitted')
    for field in ('open_us','close_us','available_us'):need(frame.schema[field]==pl.Int64 and frame[field].null_count()==0,'Known integer microsecond calendar')
    need(np.array_equal(frame['close_us'].to_numpy(),frame['open_us'].to_numpy()+rb.MIN) and np.array_equal(frame['available_us'].to_numpy(),frame['close_us'].to_numpy()),'Past-only completed source availability')
    for field in ('open','high','low','close','quote_volume'):
        v=frame[field].to_numpy();need(np.isfinite(v).all() and np.all(v>=0 if field=='quote_volume' else v>0),'Finite accepted primitive accounting values')
    for symbol in ('BTCUSDT','ETHUSDT'):
        rows=frame.filter(pl.col('symbol')==symbol);need(np.array_equal(rows['open_us'].to_numpy(),np.arange(start-31*rb.DAY,end,rb.MIN,dtype=np.int64)),'Full UTC source calendar including warmup without account rows')
    del part,pf,rows;gc.collect();budget()
    return frame,dict(fold=fold['fold'],arrow_path=str(path),arrow_sha256=sha(path),parquet_sha256=sha(parquet),source_rows_verified=1664640,
        logical_values_and_schema_equal=True,physical_file_hash_checked=True,IPC_reserialization_performed=False,
        original_normalized_market_arrays_read=False,warmup_days_without_account=31)
def target_check(actual,fold,frame,calendar,strategy,old):
    directory=Path(actual['run_dir'])/(fold['fold']+'-'+strategy);intent=pl.read_parquet(directory/'intent_calendar.parquet')
    target=pl.read_parquet(directory/'targets.parquet');receipt=read(directory/'target_receipt.json')
    need(receipt['targets_sha256']==old.frame_sha(target) and intent.height==2*len(calendar),'Target logical digest and complete minute intents')
    causal=rb.targets(frame,intent,receipt,calendar,strategy,old)
    rows=[]
    for symbol in old.SYMS:
        one=intent.filter(pl.col('symbol')==symbol).sort('decision_us');times=one['decision_us'].to_numpy();weights=one['target_weight'].to_numpy()
        need(np.array_equal(times,calendar) and np.array_equal(one['available_us'].to_numpy(),times) and np.array_equal(one['comparison_order_eligible_us'].to_numpy(),times+rb.MIN) and np.array_equal(one['preserved_v8_intent_earliest_order_us'].to_numpy(),times+5000000),'Signal causal availability and distinct latency metadata')
        need(np.isfinite(weights).all() and np.all((weights==0)|(weights==.3)) and weights[-1]==0,'Fixed long-only weights and costed terminal target')
        mask=np.r_[True,np.diff(weights)!=0];rows.extend(dict(available_us=int(t),symbol=symbol,target_weight=float(w)) for t,w in zip(times[mask],weights[mask]))
    reconstructed=pl.DataFrame(rows).sort(['available_us','symbol']);need(target.sort(['available_us','symbol']).equals(reconstructed),'Compressed targets exactly match full causal intent changes')
    bound=dict(target_sha256=sha(directory/'targets.parquet'),intent_sha256=sha(directory/'intent_calendar.parquet'),receipt_sha256=sha(directory/'target_receipt.json'))
    del intent,target,reconstructed,one;gc.collect();budget();return bound,dict(fold=fold['fold'],strategy=strategy,**bound,**causal)
def main():
    need(os.environ.get('COIN_TASK_ID') and not OUT.exists(),'New bounded/progress task and exclusive report')
    signal.signal(signal.SIGTERM,terminated);manifest=read(MANIFEST)
    need(manifest['checker_sha256']==sha(__file__) and manifest['reuse_blocks_sha256']==sha(rb.__file__),'Frozen independent code bytes')
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),reuse_blocks_sha256=sha(rb.__file__),
        actual_manifest_path=str(MANIFEST),actual_manifest_sha256=sha(MANIFEST),actual_reports={str(ACTUAL.relative_to(ROOT)):manifest['actual_report_sha256']},
        exact_command=' '.join(sys.argv),python=sys.executable,sys_prefix=sys.prefix,environment_lock_sha256=sha(ROOT/'environments/v8/uv.lock'),
        explicit_financial_selector=dict(fold='CONT547',days=547,strategies=list(rb.SLEEVES),spread_bps=[8],accounts=3))
    write(STATE/'RUN_BINDING.json',binding)
    audit=dict(status='FAIL_D033_THREE_NATIVE_SPOT_LEDGER_AUDIT',binding=binding,independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),
        actual_report_sha256=manifest['actual_report_sha256'],run_binding_sha256=sha(STATE/'RUN_BINDING.json'),ledgers=[],runtime_inputs=[],target_causality=[],
        completed_ledgers_verified=0,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',classification='PREVIOUSLY_SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN',
        original_strategy_or_engine_replayed=False,old_account_arrays_read=False,source_QA_CRC_repeated=False,registry_appended=False,maximum_independent_RSS_bytes=MAX_RSS_BYTES,maximum_wall_seconds=600,
        all_event_drawdown_verified=False,full_financial_numerics='REUSED_ACCEPTED_NUMPY_ASSERTIONS',sparse_Decimal_scope='RECORDED_SETTLEMENT_ONLY')
    progress=None
    try:
        verify,old,proof=rb.prepared_financial();old.sha=sha;verify.__globals__['sha']=sha
        core=rb.imported(ROOT/CORE,CORE_SHA,'d033_sparse_spot_settlement')
        audit['financial_AST_precompile']=proof;budget()
        need(manifest['maximum_independent_RSS_bytes']==MAX_RSS_BYTES and manifest['maximum_wall_seconds']==600,'Explicit revised independent resource prebinding')
        from quant import resources
        audit['actual_cgroup_status_before_arrays']=resources.status()
        actual,spec,meta=metadata(manifest,old);audit.update(period_binding=meta,verified_source_hashes=meta['verified_source_hashes'],completed_source_files_verified=38)
        from scripts.research_v7.oracle_flow_ceiling import Progress
        progress=Progress();progress.value['detail']='D033 三个新完整账户数值核验；不重跑控制或原QA'
        start,end=old.stamp('2024-01-01'),old.stamp('2025-07-01');days=547;fold=actual['folds'][0]
        need(fold['fold']=='CONT547' and fold['start_us']==start and fold['end_us']==end and fold['days']==days and fold['status']=='COMPLETE_PROXY_COMPARISON' and len(fold['results'])==3,'Full continuous547day fold')
        frame,input_proof=actual_input(actual,fold,start,end);audit['runtime_inputs'].append(input_proof);calendar=np.arange(start,end,rb.MIN,dtype=np.int64);target_bound={}
        for i,strategy in enumerate(rb.SLEEVES):
            progress.update('独立核固定意图与可用时点',i,3,'策略',strategy=strategy)
            target_bound[strategy],causal=target_check(actual,fold,frame,calendar,strategy,old);audit['target_causality'].append(causal)
        # Keep only accepted financial body's actual dependencies before ledger arrays.
        close_times=np.arange(start+rb.MIN,end+rb.MIN,rb.MIN,dtype=np.int64)
        per={s:frame.filter((pl.col('symbol')==s)&(pl.col('open_us')>=start)).select('open','close') for s in old.SYMS}
        capacity=frame.select('symbol','quote_volume');del frame,calendar;gc.collect();budget()
        seen=set()
        for item in fold['results']:
            key=(item['strategy'],item['spread_bps']);need(key not in seen and key in {(s,8) for s in rb.SLEEVES},'Unique three existing sleeves / one cost');seen.add(key)
            progress.update('逐账户核资金净库存成本与完整分钟月表',len(audit['ledgers']),3,'账户',strategy=item['strategy'])
            entry=verify(item,fold,spec,actual,audit,start,end,days,capacity,per,close_times,target_bound)
            entry['sparse_Decimal_settlement']=rb.sparse_decimal(item,per,core,start,end)
            entry.update(completed_minutes_verified=787680,completed_days_verified=547,completed_months_verified=18,all_event_drawdown_verified=False,
                sparse_Decimal_cash_tolerance_USDT=1e-7,sparse_Decimal_quantity_tolerance=1e-12,
                inherited_minute_money_absolute_tolerance_USDT=1e-6,inherited_published_ratio_absolute_tolerance=1e-12,
                global_maximum_numeric_error_not_instrumented=True,financial_assertions_all_passed=True)
            need(len(entry['months'])==18 and sum(m['days'] for m in entry['months'])==547,'All18 continuous months, no resets')
            published=next(a for a in actual['aggregate'] if a['strategy']==item['strategy'] and a['spread_bps']==8)
            need(published['complete_periods']==1 and published['period_lengths_days']==[547] and old.close(published['period_net_return'],entry['net_return'],1e-12) and old.close(published['fees_USDT_across_period_accounts'],entry['fees']) and old.close(published['execution_cost_USDT_across_period_accounts'],entry['execution_costs']) and old.close(published['max_observed_minute_MDD'],entry['minute_MDD'],1e-12),'Aggregate matches independently checked account')
            audit['completed_ledgers_verified']=len(audit['ledgers']);gc.collect();budget()
        need(seen=={(s,8) for s in rb.SLEEVES} and len(audit['ledgers'])==3,'Exactly all three new accounts')
        need(sha(ACTUAL)==manifest['actual_report_sha256'] and sha(PROTO)==manifest['protocol_sha256'] and all(sha(ROOT/p)==d for p,d in audit['verified_source_hashes'].items()),'Frozen actual and dependencies unchanged after finance')
        audit.update(status=SUCCESS,completed_minutes_per_account_verified=787680,completed_days_per_account_verified=547,completed_months_per_account_verified=18,
            limits=['Previously seen development sample; no unseen or locked qualification.','Minute and daily MDD independently checked separately; all-event NAV/MDD is not proven.',
            'Full ledger assertions use accepted NumPy arithmetic; Decimal independently checks recorded fills and terminal cash/net quantity bridge only.',
            'Same risk mechanism does not mean identical realized risk or continuous hard caps; passive drift is measured.',
            'Binance minute proxy with current Bybit global Non-VIP fee counterfactual, not native Bybit execution or long-term APR.',
            'Independent input checks read immutable derived Parquet/physical Arrow; original38 normalized file identity relies on actual source byte-reuse proof, no repeated QA/CRC.'])
        progress.update('三账户独立核验完成',3,3,'账户')
    except Exception as error:
        audit.update(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),completed_ledgers_before_failure=len(audit['ledgers']));raise
    finally:
        if progress is not None:progress.stop.set();progress.thread.join(timeout=3)
        audit.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-STARTED,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        try:
            from quant import resources
            audit['actual_cgroup_status_at_exit']=resources.status()
        except Exception as e:audit['actual_cgroup_status_at_exit_error']=str(e)
        write(OUT,audit);print(json.dumps(dict(status=audit['status'],report=str(OUT),sha256=sha(OUT),completed_ledgers_verified=audit['completed_ledgers_verified'])),flush=True)
if __name__=='__main__':main()