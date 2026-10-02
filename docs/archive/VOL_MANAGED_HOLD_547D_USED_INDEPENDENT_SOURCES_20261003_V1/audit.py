"""UNRUN D034 independent single-VM audit; no new financial loop or fixed_targets call.
Runtime requires a separately frozen ACTUAL_BINDING and real closed0 main/tiny.
Reuse accepted D033 V3 finance/physical-input checks. Old3 accounts: JSON only.
"""
from pathlib import Path
from datetime import UTC,datetime
import argparse,gc,hashlib,importlib.util,json,os,resource,signal,sys,time,traceback
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl
ROOT=Path('/mnt/d/codex/coin');VM='VOL_MANAGED_BUY_AND_HOLD'
ARCHIVE=ROOT/'docs/archive/PUBLIC_LONG_547D_USED_INDEPENDENT_SOURCES_20261003_V3'
OLD_SOURCE_SHA='aa0ec8da91259c0f3f10d2a60de4ee7551c842daf4852dd4dc106f3c7eb242d2'
OLD_BLOCKS_SHA='be46b204780a4c9ad39c905fda9c8dd131229e78bc31dbbf598a59d6646c9ea1'
OLD_REPORT=ROOT/'reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json'
OLD_REPORT_SHA='c70e3011f74ddbbbf250316bb2cad9a02d2bd6945b266a1a96a1083b9fcbc6e8'
OLD_AUDIT=ROOT/'reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json'
OLD_AUDIT_SHA='c7033ef299071f1d3149381fc19d923487bbbdd1040c4b20c75481058203441d'
OLD_PARQUET=Path('/home/xflops/coin-state/public-long-547d-actual-20261003-v1/shared_source_minutes.parquet')
OLD_PARQUET_SHA='69ee7e5b8bee31f1cc28cbfbee4c99176060959a0e7d831683a3fddc796a06d2'
OLD_IPC_SHA='1d1a2e49b15f0430248ac77fbc745b15e498cc7b14307244712720c6f417ec27'
MIN=60000000;DAY=86400000000;TARGET_ATOL=1e-12
STARTED=time.monotonic();RSS_CAP=3500000000
SUCCESS='PASS_D034_SINGLE_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
def sha(path):
    d=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):d.update(b)
    return d.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def need(ok,message):
    if not bool(ok):raise ValueError(message)
def scalar(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)
def write(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False,default=scalar)
def budget():
    need(time.monotonic()-STARTED<600,'Frozen600s independent budget')
    need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=RSS_CAP,'Independent3.5GB peak under shared5GB')
def load_accepted():
    need(sha(ARCHIVE/'audit.py')==OLD_SOURCE_SHA and sha(ARCHIVE/'reuse_blocks.py')==OLD_BLOCKS_SHA,'Accepted D033 V3 source bytes')
    spec=importlib.util.spec_from_file_location('reuse_blocks',ARCHIVE/'reuse_blocks.py')
    block=importlib.util.module_from_spec(spec)
    need('reuse_blocks' not in sys.modules,'Exclusive accepted block module import')
    sys.modules['reuse_blocks']=block;spec.loader.exec_module(block)
    old=block.imported(ARCHIVE/'audit.py',OLD_SOURCE_SHA,'d034_accepted_d033_checker')
    old.STARTED=STARTED
    verify,helper,proof=block.prepared_financial();helper.sha=sha;verify.__globals__['sha']=sha
    need(sha(OLD_AUDIT)==OLD_AUDIT_SHA,'Accepted D033 V3 receipt only')
    accepted=read(OLD_AUDIT)
    need(accepted['completed_ledgers_verified']==3 and accepted['status']=='PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR','Accepted numerical scope')
    need(proof['derived_financial_AST_sha256']==accepted['financial_AST_precompile']['derived_financial_AST_sha256'],'Exactly accepted full financial AST including cost8/empty-fill compatibility')
    return old,block,verify,helper,proof,accepted

def vm_targets(frame,intent,targets,receipt,calendar,helper):
    """Independent explicit exponential weights, not the production EWMA or target function.
    adjust=False alpha=.25: first observation weight=.75**(n-1); later weights
    .25*.75**age. bias=False divisor is sumw-sumw2/sumw. All past seed retained.
    """
    need(receipt['strategy_id']==VM and receipt['paired_comparison_allowed'] and not receipt['warmup_failed'],'Sole VM evaluable target')
    need(receipt['implementation_version']=='V8_BENCHMARK_TARGET_INTENTS_V2_20261002' and receipt['resource_adapter']=='ONE_PASS_OFFICIAL_POLARS_ON_ACCEPTED_CONTINUOUS_SOURCE','Original VM resource/rule route')
    need(receipt['preserved_V1_rule_source_sha256']==sha(ROOT/'scripts/research_v8/benchmark_targets.py') and receipt['benchmark_contract_sha256']==sha(ROOT/'protocols/BENCHMARK_CONTRACT_V1.json') and receipt['cost_scenarios_sha256']==sha(ROOT/'protocols/EXECUTION_COST_SCENARIOS_V8.json'),'Original benchmark contracts and seed definition')
    need(not receipt['P1_economic_gate_passed'] and not receipt['candidate_qualification_allowed'] and not receipt['costs_paid'],'Intent receipt is not an economic gate')
    need(receipt['calendar_sha256']==hashlib.sha256(calendar.tobytes()).hexdigest() and receipt['decision_count']==len(calendar) and receipt['targets_sha256']==helper.frame_sha(targets),'Full target calendar and value digest')
    lower=int(frame['open_us'].min());daily=[]
    for symbol in helper.SYMS:
        rows=frame.filter(pl.col('symbol')==symbol).sort('open_us')
        need(rows.height==578*1440,'Complete578 source days per symbol')
        daily.append(rows['close'].to_numpy().reshape(578,1440)[:,-1])
    # Fixed .3/.3 gross reference, no fee/NAV/recursively held portfolio input.
    returns=np.stack([x[1:]/x[:-1]-1 for x in daily],axis=1)
    reference=.3*(returns[:,0]+returns[:,1]);times=lower+np.arange(2,579,dtype=np.int64)*DAY
    need(np.isfinite(reference).all() and np.all(reference>-1) and np.all(np.diff(times)==DAY),'Finite contiguous causal reference returns')
    day_stamps=calendar.reshape(547,1440)[:,0];day_weights=[];checks=[]
    for decision in day_stamps:
        n=int(np.searchsorted(times,decision,side='right'));need(n>=7 and times[n-1]==decision,'Newest completed day available at00UTC; no forward fill')
        x=reference[:n];w=np.r_[.75**(n-1),.25*np.power(.75,np.arange(n-2,-1,-1))]
        total=float(w.sum());mean=float(w@x/total);denominator=total-float(w@w)/total
        need(denominator>0,'Unbiased EWMA weight denominator')
        variance=float(w@((x-mean)**2)/denominator);estimate=float(np.sqrt(max(0.,variance))*np.sqrt(365))
        multiplier=min(1.,.10/max(.01,estimate));day_weights.append(.3*multiplier)
        checks.append(dict(decision_us=int(decision),latest_completed_day_end_us=int(times[n-1]),observations=n,
            first_seed_day_end_us=int(times[0]),EWMA_span=7,EWMA_adjust=False,EWMA_bias=False,
            estimated_annual_vol=estimate,multiplier=multiplier,raw_symbol_weight=.3*multiplier))
    expected=np.repeat(np.asarray(day_weights),1440);expected[-1]=0.;observed_rows=[];maximum_error=0.
    for symbol in helper.SYMS:
        one=intent.filter(pl.col('symbol')==symbol).sort('decision_us');stamp=one['decision_us'].to_numpy();value=one['target_weight'].to_numpy()
        need(one.height==len(calendar) and np.array_equal(stamp,calendar),'Every minute has a VM decision')
        need(np.array_equal(one['available_us'].to_numpy(),stamp) and np.array_equal(one['comparison_order_eligible_us'].to_numpy(),stamp+MIN) and np.array_equal(one['preserved_v8_intent_earliest_order_us'].to_numpy(),stamp+5000000),'Original availability/latency metadata')
        need(np.isfinite(value).all() and np.all((value>=0)&(value<=.3)) and value[-1]==0,'Original unlevered VM cap and terminal zero')
        error=float(np.max(np.abs(value-expected)));maximum_error=max(maximum_error,error);need(error<=TARGET_ATOL,'Independent all-past unbiased daily EWMA target mismatch')
        frozen=np.repeat(value.reshape(547,1440)[:,0],1440);frozen[-1]=0.
        need(np.array_equal(value,frozen),'Daily00UTC target held exactly within day except terminal')
        need(one['reason'][:-1].eq('DAILY_EWMA_DOWNSCALED_HOLD_INTENT').all() and one['reason'][-1]=='COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL','Original VM reason and feasible-terminal semantics')
        mask=np.r_[True,np.diff(value)!=0];observed_rows.extend(dict(available_us=int(t),symbol=symbol,target_weight=float(v)) for t,v in zip(stamp[mask],value[mask]))
    reconstructed=pl.DataFrame(observed_rows).sort(['available_us','symbol'])
    need(targets.sort(['available_us','symbol']).equals(reconstructed),'Compressed targets match exact saved minute weights; no extra rebalance')
    return returns,times,dict(strategy=VM,independent_formula='EXPLICIT_ADJUST_FALSE_EXPONENTIAL_WEIGHTS_UNBIASED_VARIANCE_ALL_PAST_SEED',
        fixed_targets_or_production_EWMA_called=False,decision_minutes=len(calendar),completed_day_checks=checks,
        maximum_raw_target_weight_error=maximum_error,raw_target_weight_absolute_tolerance=TARGET_ATOL,
        reference_return='.3*BTC_daily_close_return+.3*ETH_daily_close_return; no cash NAV or fees',
        day_update_UTC='00:00',terminal_last_minute_zero_intent=True,seed_is_all_fixed_past_not_last7_only=True)

def engine_risk_check(fills,targets,returns,times,start,end):
    """Pure expected effective weights at recorded signals; no order/account replay.
    VM7-day downscale precedes the unchanged engine30-day/min20 covariance .10 cap.
    The engine only rescales compressed intent events, not passive drift each minute.
    """
    mapping={}
    for row in targets.iter_rows(named=True):mapping.setdefault(row['available_us'],{})[row['symbol']]=row['target_weight']
    # Original engine config also adds a separate feasible final-minute zero intent.
    # Its signal=end-2min, distinct from saved plan's last-minute terminal row.
    terminal_signal=end-2*MIN
    need(terminal_signal not in mapping,'VM daily intents do not collide with engine terminal signal')
    mapping[terminal_signal]={'BTCUSDT':0.,'ETHUSDT':0.}
    buffered=1-2*.6*(.0008+(1+.0008)*.001);maximum=0.;additional=set()
    for row in fills.iter_rows(named=True):
        signal=row['signal_us'];need(signal in mapping and set(mapping[signal])=={'BTCUSDT','ETHUSDT'},'Fill signal has exact paired compressed intent event')
        raw=np.asarray([mapping[signal][s] for s in ('BTCUSDT','ETHUSDT')],dtype=float);weights=raw.copy()
        n=int(np.searchsorted(times,max(start,signal),side='right'))
        history=returns[max(0,n-30):n]
        if len(history)<20:weights[:]=0.
        elif weights.sum()>0:
            cov=np.cov(history.T,ddof=1)*365;annual=float(np.sqrt(max(0.,weights@cov@weights)))
            if annual>.1:weights*=.1/annual;additional.add(signal)
        weights*=buffered;expected=float(weights[('BTCUSDT','ETHUSDT').index(row['symbol'])])
        error=abs(row['target_weight']-expected);maximum=max(maximum,error);need(error<=1e-12,'Original common30-day risk and cost buffer differs at fill signal')
    return dict(fills_checked=fills.height,maximum_effective_fill_weight_error=maximum,ratio_absolute_tolerance=1e-12,
        existing_two_downscales_preserved=True,additional_common_covariance_downscale_signals=len(additional),
        VM_target='.10 all-past EWMA span7/min7 gross-reference cap',engine_target='.10 rolling30day/min20 asset-return covariance cap',
        cost_rebalance_buffer=buffered,common_risk_runs_at_compressed_intent_events=True,original_engine_terminal_signal_us=terminal_signal,original_engine_terminal_event_open_us=end-MIN,
        continuously_equalized_actual_vol_or_passive_drift_caps_claimed=False)

def new_metadata(manifest,old,reference_audit):
    actual_path=Path(manifest['actual_report']);protocol=Path(manifest['protocol_path'])
    need(actual_path.resolve().is_relative_to(ROOT/'reports/fast_research') and protocol.resolve().is_relative_to(ROOT/'protocols'),'New frozen ROOT actual/protocol paths')
    need(actual_path!=OLD_REPORT and sha(actual_path)==manifest['actual_report_sha256'] and sha(protocol)==manifest['protocol_sha256'],'New actual/protocol bytes')
    actual=read(actual_path);spec=read(protocol);run=Path(actual['run_dir']);binding=read(run/'RUN_BINDING.json')
    need(binding==actual['binding'] and sha(run/'RUN_BINDING.json')==actual['run_binding_sha256'],'New actual RUN_BINDING exact')
    task=old.existing_task(binding['task_id']);need(binding['task_id']==manifest['actual_task_id'],'Actual new sole account closed0 before arrays')
    need(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['completed_ledgers']==1 and actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'],'Only one complete new VM account')
    need(binding['fits']==actual['market_models_fit']==0 and actual['orders_sent']==0 and not actual['locked_consumed'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Conditional proxy scope: no models, locked use or sent orders')
    need(spec['strategy_ids']==binding['strategies']==[VM] and spec['planned_ledgers']==binding['planned_ledgers']==1 and binding['all_folds']==spec['folds'],'One predeclared existing VM sleeve')
    need(spec['folds']==[dict(id='CONT547',period_start='2024-01-01',period_end_exclusive='2025-07-01')] and spec['warmup_days']==31 and len(actual['folds'])==1,'Same547+31 full calendar')
    need(sha(OLD_REPORT)==OLD_REPORT_SHA and reference_audit['actual_report_sha256']==OLD_REPORT_SHA,'Saved D033 reference metadata only')
    reference=read(OLD_REPORT);reference_spec=read(ROOT/'protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json')
    for key in ('common_config','costs','folds','warmup_days','source_receipt','source_receipt_sha256','source_scope','source_calendar','source_days_per_symbol','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type'):
        need(spec[key]==reference_spec[key],'Paired common conditions unchanged: '+key)
    need(spec['reused_minute_input']==dict(report_path=str(OLD_REPORT.relative_to(ROOT)),report_sha256=OLD_REPORT_SHA,path=str(OLD_PARQUET),sha256=OLD_PARQUET_SHA),'Exact existing Parquet reuse contract')
    need(reference['minute_source']['sha256']==OLD_PARQUET_SHA and reference_audit['runtime_inputs'][0]['arrow_sha256']==OLD_IPC_SHA and sha(OLD_PARQUET)==OLD_PARQUET_SHA,'Current referenced input bytes and prior physical IPC identity; no old row replay')
    need(actual['reused_minute_input']==spec['reused_minute_input'] and actual['raw_normalized_market_files_read'] is False,'Original38 prices/QA not re-read')
    hashes=binding['source_hashes'];need(all(hashes.get(p)==d for p,d in spec['frozen_sources'].items()),'New frozen source union')
    for relative,digest in hashes.items():need(sha(ROOT/relative)==digest and sha(run/'source-snapshot'/relative)==digest,'Current/new actual snapshot bytes')
    need(binding['protocol_sha256']==sha(protocol),'Selected protocol')
    need(sys.prefix==spec['environment']['sys_prefix'] and sha(ROOT/'environments/v8/uv.lock')==spec['environment']['lock_sha256'],'Locked clean environment')
    entry=manifest['production_entrypoint'];need(entry.startswith('scripts/investment/') and entry in hashes,'Frozen specific production entrypoint')
    adapter=old.rb.imported(ROOT/entry,hashes[entry],'d034_frozen_vm_namespace')
    private=adapter.context(spec);need(private['PERIOD_DERIVATION']==actual['period_namespace_derivation'],'All private date/rule ASTs precompile before arrays')
    need(private['benchmarks'].causal_vol_multiplier.__globals__['_time'] is private['benchmarks']._time and private['benchmarks'].causal_vol_multiplier.__globals__['_v1'] is private['benchmarks']._v1,'VM date wrapper is bound to private accepted namespaces')
    tiny_path=ROOT/spec['required_smoke_receipt'];tiny=read(tiny_path);tb=read(Path(tiny['run_dir'])/'RUN_BINDING.json')
    need(tb==tiny['binding'] and sha(Path(tiny['run_dir'])/'RUN_BINDING.json')==tiny['run_binding_sha256'] and sha(tiny_path)==actual['accepted_smoke_sha256']==manifest['smoke_sha256'],'New sole tiny binding')
    smoke_task=old.existing_task(tb['task_id']);need(tb['task_id']==manifest['smoke_task_id'],'Actual sole synthetic closed0')
    need(tiny['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and {p:d for p,d in tb['source_hashes'].items() if p.startswith(('src/','scripts/','tests/','environments/','third_party/'))}=={p:d for p,d in hashes.items() if p.startswith(('src/','scripts/','tests/','environments/','third_party/'))},'Exact new shared source smoke')
    need(tiny['registration_start']['hyperparameters']==spec['common_config'] and tiny['registration_start']['cost_assumptions']==spec['costs'] and tiny['registration_start']['thresholds']==spec['strategy_rules'],'New smoke economics match')
    junit=Path(tiny['run_dir'])/'junit.xml';tree=ET.parse(junit).getroot();counts={k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    need(counts==dict(tests=1,failures=0,errors=0,skipped=0) and sha(junit)==tiny['junit_sha256'],'Only one fresh new case')
    need(actual['fee_derivation']['derived_AST_SHA256']==reference['fee_derivation']['derived_AST_SHA256'] and actual['fee_profile_sha256']==reference['fee_profile_sha256'],'Frozen native accounting/profile reused')
    return actual,spec,dict(actual_task=task,actual_smoke_task=smoke_task,verified_source_hashes=hashes,
        source=old.source_proof(spec,actual,manifest),fresh_synthetic_cases=counts,protocol_sha256=sha(protocol),
        saved_control_report_sha256=OLD_REPORT_SHA,saved_control_audit_sha256=OLD_AUDIT_SHA,old_account_arrays_replayed=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binding',type=Path,required=True);parser.add_argument('--run-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    state=args.run_dir.resolve();out=args.output.resolve();manifest_path=args.binding.resolve();manifest=read(manifest_path)
    need(os.environ.get('COIN_TASK_ID') and state.is_relative_to(Path('/home/xflops/coin-state')) and out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(),'New exclusive bounded STATE/report')
    need(manifest['checker_sha256']==sha(__file__) and manifest['maximum_independent_RSS_bytes']==RSS_CAP and manifest['maximum_wall_seconds']==600,'Prebound draft code/resources before actual run')
    state.mkdir(exist_ok=True);binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),actual_manifest_path=str(manifest_path),actual_manifest_sha256=sha(manifest_path),actual_reports={manifest['actual_report']:manifest['actual_report_sha256']},
        exact_command=' '.join(sys.argv),python=sys.executable,sys_prefix=sys.prefix,explicit_financial_selector=dict(fold='CONT547',strategy=VM,spread_bps=8,accounts=1,days=547))
    write(state/'RUN_BINDING.json',binding);audit=dict(status='FAIL_D034_SINGLE_VM_INDEPENDENT_AUDIT',binding=binding,independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),actual_report_sha256=manifest['actual_report_sha256'],ledgers=[],runtime_inputs=[],
        completed_ledgers_verified=0,original3_accounts_replayed=False,original38_source_QA_CRC_repeated=False,fixed_targets_called=False,all_event_drawdown_verified=False,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
    progress=None
    try:
        old,block,verify,helper,proof,reference_audit=load_accepted();audit['financial_AST_precompile']=proof
        from quant import resources
        audit['actual_cgroup_before_arrays']=resources.status();actual,spec,meta=new_metadata(manifest,old,reference_audit);audit.update(period_binding=meta,verified_source_hashes=meta['verified_source_hashes'])
        from scripts.research_v7.oracle_flow_ceiling import Progress
        progress=Progress();progress.value['detail']='D034 sole VM independent audit; no old three accounts or QA replay'
        start,end=helper.stamp('2024-01-01'),helper.stamp('2025-07-01');fold=actual['folds'][0]
        need(fold['fold']=='CONT547' and fold['start_us']==start and fold['end_us']==end and fold['days']==547 and fold['status']=='COMPLETE_PROXY_COMPARISON' and len(fold['results'])==1,'Sole full547day fold')
        frame,input_proof=old.actual_input(actual,fold,start,end);audit['runtime_inputs'].append(input_proof);calendar=np.arange(start,end,MIN,dtype=np.int64)
        directory=Path(actual['run_dir'])/('CONT547-'+VM);intent=pl.read_parquet(directory/'intent_calendar.parquet');targets=pl.read_parquet(directory/'targets.parquet');receipt=read(directory/'target_receipt.json')
        returns,times,causal=vm_targets(frame,intent,targets,receipt,calendar,helper);audit['target_causality']=causal
        bound=dict(target_sha256=sha(directory/'targets.parquet'),intent_sha256=sha(directory/'intent_calendar.parquet'),receipt_sha256=sha(directory/'target_receipt.json'))
        per={s:frame.filter((pl.col('symbol')==s)&(pl.col('open_us')>=start)).select('open','close') for s in helper.SYMS};capacity=frame.select('symbol','quote_volume')
        del frame,intent,calendar;gc.collect();budget();item=fold['results'][0];need(item['strategy']==VM and item['spread_bps']==8,'One original VM spread8 new account')
        fills=pl.read_parquet(Path(item['directory'])/'trades.parquet').sort('execution_us',maintain_order=True);audit['existing_two_stage_risk_check']=engine_risk_check(fills,targets,returns,times,start,end)
        del fills,targets,returns,times;gc.collect();progress.update('Verify one new VM complete account',0,1,'account')
        entry=verify(item,fold,spec,actual,audit,start,end,547,capacity,per,np.arange(start+MIN,end+MIN,MIN,dtype=np.int64),{VM:bound})
        core=block.imported(ROOT/old.CORE,old.CORE_SHA,'d034_sparse_spot_decimal');entry['sparse_Decimal_settlement']=block.sparse_decimal(item,per,core,start,end)
        need(len(entry['months'])==18 and sum(m['days'] for m in entry['months'])==547,'All18 continuous months')
        entry.update(completed_minutes_verified=787680,completed_days_verified=547,completed_months_verified=18,all_event_drawdown_verified=False,
            sparse_Decimal_cash_tolerance_USDT=1e-7,sparse_Decimal_quantity_tolerance=1e-12,financial_assertions_all_passed=True,global_maximum_numeric_error_not_instrumented=True)
        published=actual['aggregate'];need(len(published)==1 and published[0]['strategy']==VM and published[0]['spread_bps']==8 and published[0]['period_lengths_days']==[547] and helper.close(published[0]['period_net_return'],entry['net_return'],1e-12),'One aggregate/account identity')
        budget();need(sha(manifest['actual_report'])==manifest['actual_report_sha256'] and sha(manifest['protocol_path'])==manifest['protocol_sha256'] and all(sha(ROOT/p)==d for p,d in meta['verified_source_hashes'].items()),'Final frozen bytes')
        audit.update(status=SUCCESS,completed_ledgers_verified=1,completed_source_files_verified=38,completed_minutes_verified=787680,completed_days_verified=547,completed_months_verified=18,
            financial_numeric_scope='REUSED_D033_V3_NUMPY_MINUTE_DAY_MONTH_ASSERTIONS_PLUS_SPARSE_DECIMAL_RECORDED_SETTLEMENT',limits=['Seen development sample, not unseen or native long-term APR evidence.',
            'Existing7-day all-past EWMA intent cap and common30-day/min20 covariance cap both retained; not a single-layer equal-risk guarantee.',
            'Risk updates at compressed intent events; passive drift and actual risk reported, no continuous hardcaps claim.',
            'Terminal residual positions remain marked and may be material; do not call all residuals dust or realized cash.',
            'Minute and daily MDD checked; all-event MDD unproven. Old3 financial arrays and original38 price QA are not replayed.'])
        progress.update('One new VM account verified',1,1,'account')
    except Exception as error:audit.update(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),completed_ledgers_before_failure=len(audit['ledgers']));raise
    finally:
        if progress is not None:progress.stop.set();progress.thread.join(timeout=3)
        audit.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-STARTED,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write(out,audit);print(json.dumps(dict(status=audit['status'],report=str(out),sha256=sha(out))),flush=True)
if __name__=='__main__':main()