"""UNRUN D035 V3: parent actual source scope evidence; D034/D033 arithmetic unchanged.
No old account arrays, original QA/CRC, strategy/backtester replay or registry writes.
Both new actual tasks must be closed0 before even the parent input-byte checks.
"""
from pathlib import Path
from datetime import UTC, datetime
import argparse, ast, copy, gc, hashlib, json, os, resource, signal, sys, time, traceback
import xml.etree.ElementTree as ET
import numpy as np
import polars as pl

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
ACCEPTED=ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'
ACCEPTED_SHA='942f006885a6e2cc5476f697b6368e586c30fe68b0344af55833aa8f4c808d78'
ACCEPTED_RECEIPT=ROOT/'reports/fast_research/VOL_MANAGED_HOLD_547D_INDEPENDENT_AUDIT_20261003_V1.json'
ACCEPTED_RECEIPT_SHA='46951463ecf0c910dc3bdf8953437afa0bc0fd2e15650627639855670a5ea2c1'
NATIVE_ACCEPTED=ROOT/'reports/fast_research/BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json'
NATIVE_ACCEPTED_SHA='70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f'
ADAPTER_PATH='scripts/investment/vol_managed_two_period_adapter.py'
ADAPTER_SHA='594b1a16117221fe2c99494199a01df2e4c2403066f82314ce4b29bdcb28d4fe'
VM='VOL_MANAGED_BUY_AND_HOLD'; MIN=60_000_000; DAY=86_400_000_000
RSS_CAP=3_500_000_000; STARTED=time.monotonic()
OUT=ROOT/'reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json'
SUCCESS='PASS_D035_TWO_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
CASES={
 '122D':dict(fold='CONT122',start='2025-08-01',end='2025-12-01',days=122,months=4,source_days=153,
  source_scope='JUL_NOV_2025',calendar=['2025-07','2025-08','2025-09','2025-10','2025-11'],
  parent='reports/fast_research/BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json',
  parent_sha='53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',
  parent_protocol='protocols/BYBIT_SPOT_2H_122D_V2.json',
  parent_protocol_sha='11a667b18ec6c3f779214c28fc0bcfe805319ee8b89e62097f6ee3aa52659192'),
 '90D':dict(fold='CONT90',start='2025-12-01',end='2026-03-01',days=90,months=3,source_days=151,
  source_scope='OCT2025_FEB2026',calendar=['2025-10','2025-11','2025-12','2026-01','2026-02'],
  parent='reports/fast_research/BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json',
  parent_sha='329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',
  parent_protocol='protocols/BYBIT_SPOT_2H_90D_V2.json',
  parent_protocol_sha='8505eec0f6406d7725962856455e3dfdbefda6139503f5e2d7856443383ca457')}

def need(ok, message):
    if not bool(ok): raise ValueError(message)
def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1_048_576),b''): result.update(chunk)
    return result.hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def scalar(value):
    if isinstance(value,np.generic): return value.item()
    raise TypeError(type(value).__name__)
def write(path, value):
    with Path(path).open('x',encoding='utf-8') as handle: json.dump(value,handle,indent=2,allow_nan=False,default=scalar)
def budget():
    need(time.monotonic()-STARTED<600,'Frozen600s independent audit budget')
    need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=RSS_CAP,'Frozen3.5GB process cap under shared5GB')
def shared(hashes):
    return {p:d for p,d in hashes.items() if p.startswith(('src/','scripts/','tests/','environments/','third_party/'))
            or p in ('protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json','protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json')}
def rooted(path, folder):
    selected=Path(path); selected=selected if selected.is_absolute() else ROOT/selected
    need(selected.resolve().is_relative_to(ROOT/folder),'Only exact small ROOT protocol/report/source')
    return selected.resolve()

def prepared_function(module, name, integers, strings, label):
    """Only enumerated period shape/path literals; all mathematical statements retained."""
    tree=ast.parse(Path(module.__file__).read_bytes())
    functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name]
    need(len(functions)==1,'Unique accepted function: '+name)
    function=copy.deepcopy(functions[0]); original=ast.dump(function,include_attributes=False)
    counts={key:0 for key in integers}; text_counts={key:0 for key in strings}
    class PeriodLiterals(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is int and node.value in integers:
                before=node.value; counts[before]+=1
                return ast.copy_location(ast.Constant(integers[before][0]),node)
            if type(node.value) is str and node.value in strings:
                before=node.value; text_counts[before]+=1
                return ast.copy_location(ast.Constant(strings[before][0]),node)
            return node
    function=PeriodLiterals().visit(function)
    need(all(counts[key]==value[1] for key,value in integers.items()) and all(text_counts[key]==value[1] for key,value in strings.items()),'All period anchors matched exactly before arrays: '+name)
    compiled=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])); namespace=dict(vars(module)); namespace['budget']=budget
    exec(compile(compiled,str(module.__file__)+':D035:'+label,'exec'),namespace)
    proof=dict(accepted_function=name,accepted_function_AST_sha256=hashlib.sha256(original.encode()).hexdigest(),
        adapted_function_AST_sha256=hashlib.sha256(ast.dump(function,include_attributes=False).encode()).hexdigest(),
        integer_literal_replacements=[dict(old=k,new=v[0],count=counts[k]) for k,v in integers.items()],
        text_literal_replacements=[dict(old=k,new=v[0],count=text_counts[k]) for k,v in strings.items()],
        financial_or_VM_formula_statements_changed=False)
    return namespace[name],proof

def accepted_and_precompile():
    need(sha(ACCEPTED)==ACCEPTED_SHA and sha(ACCEPTED_RECEIPT)==ACCEPTED_RECEIPT_SHA,'Accepted D034 source and actual evidence')
    import importlib.util
    spec=importlib.util.spec_from_file_location('d035_accepted_d034',ACCEPTED)
    vm=importlib.util.module_from_spec(spec); spec.loader.exec_module(vm); vm.STARTED=STARTED
    old,block,finance,helper,financial_proof,reference=vm.load_accepted()
    accepted=read(ACCEPTED_RECEIPT)
    need(accepted['status']==vm.SUCCESS and accepted['binding']['checker_sha256']==ACCEPTED_SHA and accepted['completed_ledgers_verified']==1,'D034 accepted VM/numerical scope')
    old.existing_task(accepted['binding']['task_id'])
    need(sha(NATIVE_ACCEPTED)==NATIVE_ACCEPTED_SHA,'Accepted native parent composite bytes')
    native=read(NATIVE_ACCEPTED)
    need(native['status']=='PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE' and native['completed_ledgers_verified']==6,'Parent accounting accepted; prior failed suite remains failed')
    prepared={}
    for period,case in CASES.items():
        days=case['days']; source_days=days+31; rows=source_days*1440*2
        target,shape=prepared_function(vm,'vm_targets',{578:(source_days,2),579:(source_days+1,1),547:(days,2)},
            {'Complete578 source days per symbol':('Exact selected derivative source days per symbol',1)},period)
        reader,input_shape=prepared_function(old,'actual_input',{1664640:(rows,2)},
            {'CONT547-minute-input.arrow':(case['fold']+'-minute-input.arrow',1),'578 paired source days':('Exact selected derivative source days',1)},period)
        prepared[period]=dict(target=target,reader=reader,proof=dict(VM_target_period_adaptation=shape,input_period_adaptation=input_shape,
            source_receipt_days=case['source_days'],actual_derivative_days=source_days,actual_derivative_rows=rows,
            engine_risk_check_reused_without_AST_changes=True))
    proof=dict(financial_proof)
    proof.update(original_proof_metadata_declares547=financial_proof['period_days_is_explicit_function_argument']==547,
        actual_invocation_days={'122D':122,'90D':90},accepted_financial_AST_and_reuse_blocks_unchanged=True)
    return vm,old,block,finance,helper,proof,prepared

def source_metadata(spec, actual, parent, case):
    path=ROOT/spec['source_receipt']; source=read(path); days=case['source_days']
    need(sha(path)==spec['source_receipt_sha256']==actual['source_receipt_sha256']==parent['source_receipt_sha256'],'Exact original accepted source receipt')
    need(source['status']==f'PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_{days}D_CALENDAR' and source['source_files']==10
        and source['days_per_symbol']==days and source['actual_minute_rows']==days*1440*2,'Legacy full source scope, distinct from trimmed derivative')
    need(spec['source_scope']==actual['source_scope']==parent['source_scope']==case['source_scope']
        and spec['source_calendar']==actual['source_calendar']==parent['source_calendar']==case['calendar']
        and spec['source_days_per_symbol']==actual['source_days_per_symbol']==parent['source_days_per_symbol']==days,
        'Exact explicit case, sealed receipt and pinned parent actual scope; no implicit parent protocol fields')
    need(source['binding']['spec']['source_calendar']==case['calendar'] and not source['locked_consumed']
        and not source['source_modified'] and not source['new_source_downloaded'],'Exact sealed source scope without new source work')
    records=source['sources']; expected={(s,m) for s in ('BTCUSDT','ETHUSDT') for m in case['calendar']}
    need(len(records)==10 and {(row['symbol'],row['month']) for row in records}==expected,'Exact ten allowed symbol-month records')
    for row in records:
        path_expected=ROOT/'data/normalized/spot'/row['symbol']/'1m'/(row['month']+'.parquet')
        need(Path(row['normalized_path'])==path_expected and row['rows']==row['old_quality']['rows']
            and row['timestamp_unit']==row['old_quality']['timestamp_unit']=='microseconds','Preserved normalized metadata and units; no fresh file QA')
    return dict(path=str(path),sha256=sha(path),source_days_per_symbol=days,source_rows_from_accepted_receipt=days*1440*2,
        source_files=10,source_task_id=None,source_task_scope='ORIGINAL_RECEIPT_NO_TASK_ID_NOT_RECONSTRUCTED',
        normalized_sha256={r['normalized_path']:r['normalized_sha256'] for r in records},source_QA_CRC_or_original_rows_repeated=False)

def metadata(item, manifest, actual, vm, old):
    case=CASES[item['period']]; protocol=rooted(item['protocol_path'],'protocols'); spec=read(protocol)
    need(sha(protocol)==item['protocol_sha256'] and actual['binding']['protocol_sha256']==sha(protocol),'Exact selected child protocol')
    run=Path(actual['run_dir']); binding=read(run/'RUN_BINDING.json')
    need(binding==actual['binding'] and sha(run/'RUN_BINDING.json')==actual['run_binding_sha256'],'New actual binding file')
    need(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['completed_ledgers']==1 and actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'],'One complete new VM per period')
    need(binding['fits']==actual['market_models_fit']==0 and actual['orders_sent']==0 and not actual['locked_consumed'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Only seen proxy screening, zero fits/orders')
    need(spec['strategy_ids']==binding['strategies']==[VM] and spec['planned_ledgers']==binding['planned_ledgers']==1
        and spec['folds']==binding['all_folds']==[dict(id=case['fold'],period_start=case['start'],period_end_exclusive=case['end'])]
        and spec['warmup_days']==31 and len(actual['folds'])==1,'Exact fixed account/period and warmup')
    parent_path=ROOT/case['parent']; parent_protocol=ROOT/case['parent_protocol']
    need(sha(parent_path)==case['parent_sha'] and sha(parent_protocol)==case['parent_protocol_sha'],'Accepted parent report/protocol metadata')
    parent=read(parent_path); parent_spec=read(parent_protocol); parent_task=old.existing_task(parent['binding']['task_id'])
    need(parent['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and parent['all_planned_ledgers_complete'],'Accepted complete native parent')
    base=read(ROOT/'protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V2.json')
    need(spec['common_config']==parent_spec['common_config']==base['common_config'] and spec['costs']==base['costs'],'Unchanged36bp/10k/risk semantics')
    for key in ('source_receipt','source_receipt_sha256','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type'):
        need(spec[key]==parent_spec[key],'Exact parent shared condition: '+key)
    reuse=dict(report_path=case['parent'],report_sha256=case['parent_sha'],path=parent['minute_source']['path'],sha256=parent['minute_source']['sha256'])
    need(spec['reused_minute_input']==actual['reused_minute_input']==reuse and actual['raw_normalized_market_files_read'] is False,'Exact accepted parent Parquet reuse, no source QA')
    need(sha(reuse['path'])==reuse['sha256'] and parent['minute_source']['rows']==(case['days']+31)*1440*2,'Parent input-byte identity, not old account arrays')
    hashes=binding['source_hashes']; need(all(hashes.get(p)==digest for p,digest in spec['frozen_sources'].items()),'Frozen source union')
    for relative,digest in hashes.items():
        path=rooted(relative,''); need(sha(path)==digest and sha(run/'source-snapshot'/relative)==digest,'Current and actual source snapshot bytes')
    need(sys.prefix==spec['environment']['sys_prefix'] and sha(ROOT/'environments/v8/uv.lock')==spec['environment']['lock_sha256'],'Clean locked environment')
    entry=item['production_entrypoint']; need(entry==ADAPTER_PATH and hashes.get(entry)==ADAPTER_SHA,'Exact statically reviewed VM route and rule source')
    adapter=old.rb.imported(ROOT/entry,hashes[entry],'d035_frozen_route_'+item['period'])
    need(spec['strategy_rules']==adapter.VM_RULES and VM in adapter.VM_RULES and 'PUBLIC' not in adapter.VM_RULES,
        'Exact pinned explicit VM rules; wording keys need not equal historical547day labels')
    namespace=adapter.context(spec)
    need(namespace['PERIOD_DERIVATION']==actual['period_namespace_derivation'],'Production route/date ASTs precompile before arrays')
    tiny_path=ROOT/spec['required_smoke_receipt']; tiny=read(tiny_path); tb=read(Path(tiny['run_dir'])/'RUN_BINDING.json')
    need(sha(tiny_path)==actual['accepted_smoke_sha256']==manifest['smoke_sha256'] and tb==tiny['binding']
        and sha(Path(tiny['run_dir'])/'RUN_BINDING.json')==tiny['run_binding_sha256'],'One shared new tiny exact bytes')
    tiny_task=old.existing_task(tb['task_id']); need(tb['task_id']==manifest['smoke_task_id'],'One true new synthetic task0')
    need(tiny['status']=='PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT' and shared(tb['source_hashes'])==shared(hashes)
        and tiny['registration_start']['hyperparameters']==spec['common_config'] and tiny['registration_start']['cost_assumptions']==spec['costs']
        and tiny['registration_start']['thresholds']==spec['strategy_rules'],'Original cross-period shared code and economics acceptance')
    junit=Path(tiny['run_dir'])/'junit.xml'; tree=ET.parse(junit).getroot()
    counts={key:sum(int(s.get(key,0)) for s in tree.iter('testsuite')) for key in ('tests','failures','errors','skipped')}
    need(counts==dict(tests=1,failures=0,errors=0,skipped=0) and sha(junit)==tiny['junit_sha256'],'Exactly one new integrated case; old greens not repeated')
    need(actual['fee_derivation']['derived_AST_SHA256']==parent['fee_derivation']['derived_AST_SHA256']=='39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73'
        and actual['fee_profile_sha256']==parent['fee_profile_sha256']==base['fee_profile_sha256'],'Unchanged native fee math/profile')
    return spec,dict(actual_task=old.existing_task(binding['task_id']),actual_smoke_task=tiny_task,parent_actual_task=parent_task,
        parent_report_sha256=case['parent_sha'],parent_input= reuse,source=source_metadata(spec,actual,parent,case),
        verified_source_hashes=hashes,protocol_sha256=sha(protocol),fresh_shared_synthetic_cases=counts)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--binding',type=Path,required=True); parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=OUT); args=parser.parse_args(); state=args.run_dir.resolve(); output=args.output.resolve()
    need(os.environ.get('COIN_TASK_ID') and state.is_relative_to(STATE) and output==OUT and not output.exists(),'Exclusive progress/bounded STATE and combined report')
    manifest=read(args.binding); items=manifest['cases']
    need([c['period'] for c in items]==['122D','90D'] and manifest['checker_sha256']==sha(__file__)
        and manifest['maximum_independent_RSS_bytes']==RSS_CAP and manifest['maximum_wall_seconds']==600,'Frozen code/resources and explicit two-case selectors')
    reports={str(rooted(c['actual_report'],'reports/fast_research')):c['actual_report_sha256'] for c in items}; need(len(reports)==2,'Two distinct canonical ROOT actual reports')
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),actual_manifest_path=str(args.binding.resolve()),
        actual_manifest_sha256=sha(args.binding),actual_reports=reports,exact_command=' '.join(sys.argv),python=sys.executable,sys_prefix=sys.prefix,
        explicit_financial_selectors=[dict(fold=c['fold'],days=c['days'],strategy=VM,spread_bps=8) for c in CASES.values()])
    state.mkdir(exist_ok=True); write(state/'RUN_BINDING.json',binding)
    audit=dict(status='FAIL_D035_TWO_VM_INDEPENDENT_AUDIT',binding=binding,independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),
        ledgers=[],cases=[],runtime_inputs=[],verified_source_hashes={},completed_ledgers_verified=0,all_event_drawdown_verified=False,
        run_binding_sha256=sha(state/'RUN_BINDING.json'),maximum_independent_RSS_bytes=RSS_CAP,maximum_wall_seconds=600,
        old_account_arrays_replayed=False,original_source_QA_CRC_repeated=False,fixed_targets_called=False,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
    progress=None
    def terminate(signum,frame): raise TimeoutError('Independent task terminated: '+str(signum))
    signal.signal(signal.SIGTERM,terminate)
    try:
        vm,old,block,finance,helper,proof,prepared=accepted_and_precompile(); audit['financial_AST_precompile']=proof
        audit['both_period_shape_precompiles']={period:value['proof'] for period,value in prepared.items()}
        actuals=[]
        for item in items:
            path=rooted(item['actual_report'],'reports/fast_research'); need(sha(path)==item['actual_report_sha256'],'New actual report SHA')
            actual=read(path); need(actual['binding']['task_id']==item['actual_task_id'],'Prebound actual task identity')
            old.existing_task(item['actual_task_id']); actuals.append(actual)
        # No parent input bytes or market arrays until BOTH actuals are closed0.
        metas=[]; specs=[]
        for item,actual in zip(items,actuals):
            spec,meta=metadata(item,manifest,actual,vm,old); metas.append(meta); specs.append(spec)
            audit['verified_source_hashes'][CASES[item['period']]['fold']]=meta['verified_source_hashes']
        need(shared(metas[0]['verified_source_hashes'])==shared(metas[1]['verified_source_hashes']) and specs[0]['strategy_rules']==specs[1]['strategy_rules'],'One unchanged shared VM route/rules')
        from quant import resources
        audit['actual_cgroup_before_arrays']=resources.status()
        from scripts.research_v7.oracle_flow_ceiling import Progress
        progress=Progress(); core=block.imported(ROOT/old.CORE,old.CORE_SHA,'d035_sparse_spot_decimal')
        for item,actual,spec,meta in zip(items,actuals,specs,metas):
            case=CASES[item['period']]; start,end=helper.stamp(case['start']),helper.stamp(case['end']); days=case['days']; fold=actual['folds'][0]
            need(fold['fold']==case['fold'] and fold['start_us']==start and fold['end_us']==end and fold['days']==days
                and fold['status']=='COMPLETE_PROXY_COMPARISON' and len(fold['results'])==1,'Exact complete selected fold')
            frame,input_proof=prepared[item['period']]['reader'](actual,fold,start,end); audit['runtime_inputs'].append(input_proof)
            calendar=np.arange(start,end,MIN,dtype=np.int64); directory=Path(actual['run_dir'])/(case['fold']+'-'+VM)
            intent=pl.read_parquet(directory/'intent_calendar.parquet'); targets=pl.read_parquet(directory/'targets.parquet'); receipt=read(directory/'target_receipt.json')
            returns,times,causal=prepared[item['period']]['target'](frame,intent,targets,receipt,calendar,helper)
            target_bound=dict(target_sha256=sha(directory/'targets.parquet'),intent_sha256=sha(directory/'intent_calendar.parquet'),receipt_sha256=sha(directory/'target_receipt.json'))
            per={s:frame.filter((pl.col('symbol')==s)&(pl.col('open_us')>=start)).select('open','close') for s in helper.SYMS}
            capacity=frame.select('symbol','quote_volume'); del frame,intent,calendar; gc.collect(); budget()
            result=fold['results'][0]; need(result['strategy']==VM and result['spread_bps']==8,'Only new VM36bp account')
            fills=pl.read_parquet(Path(result['directory'])/'trades.parquet').sort('execution_us',maintain_order=True)
            risk=vm.engine_risk_check(fills,targets,returns,times,start,end); del fills,targets,returns,times; gc.collect()
            progress.update('Verify fixed new VM account',len(audit['cases']),2,'account',period=item['period'])
            entry=finance(result,fold,spec,actual,audit,start,end,days,capacity,per,np.arange(start+MIN,end+MIN,MIN,dtype=np.int64),{VM:target_bound})
            entry['sparse_Decimal_settlement']=block.sparse_decimal(result,per,core,start,end)
            need(len(entry['months'])==case['months'] and sum(m['days'] for m in entry['months'])==days,'Every continuous calendar month without reset')
            published=actual['aggregate']; need(len(published)==1 and published[0]['strategy']==VM and published[0]['spread_bps']==8
                and published[0]['period_lengths_days']==[days] and helper.close(published[0]['period_net_return'],entry['net_return'],1e-12),'Sole account/aggregate identity')
            entry.update(period=item['period'],completed_minutes_verified=days*1440,completed_days_verified=days,completed_months_verified=case['months'],
                all_event_drawdown_verified=False,financial_assertions_all_passed=True,sparse_Decimal_cash_tolerance_USDT=1e-7,sparse_Decimal_quantity_tolerance=1e-12,
                global_maximum_numeric_error_not_instrumented=True)
            audit['cases'].append(dict(period=item['period'],fold=case['fold'],actual_report_sha256=item['actual_report_sha256'],**meta,
                runtime_input=input_proof,target_causality=causal,existing_two_stage_risk_check=risk,all_observation_max_drawdown=None,
                minute_MDD=entry['minute_MDD'],daily_MDD=entry['daily_MDD'],completed_minutes_verified=days*1440,completed_days_verified=days,completed_months_verified=case['months']))
            audit['completed_ledgers_verified']=len(audit['cases']); del capacity,per; gc.collect(); budget()
        for item,meta in zip(items,metas):
            need(sha(rooted(item['actual_report'],'reports/fast_research'))==item['actual_report_sha256'] and sha(rooted(item['protocol_path'],'protocols'))==item['protocol_sha256']
                and all(sha(ROOT/p)==digest for p,digest in meta['verified_source_hashes'].items()),'Final unchanged actual/protocol/source bytes')
        need(len(audit['cases'])==len(audit['ledgers'])==2,'Exactly both new accounts fully verified')
        audit.update(status=SUCCESS,completed_days_verified=212,completed_minutes_verified=305280,completed_months_verified=7,
            completed_source_file_references_metadata_verified=20,distinct_accepted_source_files_metadata_verified=16,fresh_synthetic_cases=1,
            financial_numeric_scope='EXACT_ACCEPTED_D034_D033_NUMPY_FINANCE_PLUS_SPARSE_DECIMAL_RECORDED_SETTLEMENT',
            limitations=['Both periods are previously seen development screening, not unseen or native long-term APR.',
                'Original7-day all-past VM EWMA and common30-day/min20 risk mechanism remain two stages, not equal realized risk.',
                'Minute/daily MDD checked separately; all-event drawdown not proven. Terminal residuals remain marked.',
                'Original153/151day receipts have no task IDs; exact saved source qualification only, no invented task or new QA.'])
        progress.update('Both new VM accounts verified',2,2,'account')
    except Exception as error:
        audit.update(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),completed_ledgers_before_failure=len(audit['cases'])); raise
    finally:
        if progress is not None: progress.stop.set(); progress.thread.join(timeout=3)
        audit.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-STARTED,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write(output,audit); print(json.dumps(dict(status=audit['status'],report=str(output),sha256=sha(output),completed_ledgers_verified=audit['completed_ledgers_verified'])),flush=True)
if __name__=='__main__': main()
