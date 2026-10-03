"""UNRUN D043: twenty fixed213 selectors, unchanged accepted financial body.

CLI --protocol production-spec --actual production-report --run-dir --output.
ACTUAL_BINDING fields follow the accepted D041 interface: ready_to_execute,
checker_sha256, protocol_path/protocol_sha256, actual_report/actual_report_sha256,
actual_task_id, source_hashes, tolerances, budgets. Only a true closed0 producer
and a closed0 complete72-source acceptance permit any financial payload read.

The original 1c4b audit_case and HandLedger are called unchanged. Private AST
changes are limited to its reader's date-map (accepted f502 helper) and the
accepted D041 signal_reader month plus two explicit clock globals. No producer
finance, simulate, fixed_targets, parser, old QA or old account is called.
Sixteen trading accounts and one CASH artifact set receive full checks; three
other CASH selectors must have the exact same artifacts and economic summary.
This is conditional unit screening, never native execution or long-term APR.
This draft has not been compiled, run or used to read market arrays.
"""
from __future__ import annotations
import argparse, ast, copy, gc, hashlib, importlib.util, json, os, resource, shlex, subprocess, sys, time
from pathlib import Path
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
HELPER='docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
HELPER_SHA='f50223ad5ec0da2be16ae3ac5447bec2d5763260566000893f1697483b7667e4'
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
HOOK='docs/archive/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py'
HOOK_SHA='3a944f46e89600c90886053376fe2224683664e30985f3a11b089d0fd51a4d85'
ACCOUNT_SHA='cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261'
EXTRA_PINS={
    'scripts/research_v8/funding_price_source_v2.py':'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
    'scripts/research_v7/oracle_flow_ceiling.py':'959f63f40c3294b6b2b75267b9138202df79223a7e7723397cf06b8d45a1477e',
    'scripts/research_v8/registry.py':'081f881f2cb1cdc84b8c098606e9f3235c92fcdd04c0120527bee0d8493068ab'}
STATUS='PASS_D043_TWENTY_FIXED213D_PUBLIC_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
FAIL='FAIL_D043_FIXED213D_PUBLIC_PERPETUAL_INDEPENDENT_AUDIT'
ACTUAL_STATUS='COMPLETE_D043_FIXED213D_PUBLIC_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
CONTRACT='D043_FIXED_213D_SMA_DIRECTIONS_AND_PUBLIC2H_CONDITIONAL_V1'
INPUT_STATUS='PASS_D043_FIXED_213D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
SOURCE_STATUS='PASS_ROOT_D043_COMPLETE_213_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS'
SMA_ID='COIN_JESSE_SMA50_200_1D_USDT_PERPETUAL_ADAPTER'
DONCHIAN_ID='COIN_JESSE_DONCHIAN_2H_USDT_PERPETUAL_ADAPTER'
SYMS=('BTCUSDT','ETHUSDT');MODES=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH','DONCHIAN_LONG_ONLY')
PERIOD='213D';START='2024-01-01T00:00:00+00:00';END='2024-08-01T00:00:00+00:00'
WARM='2023-12-01T00:00:00+00:00'
BUDGET=dict(peak_RSS_bytes=3_000_000_000,wall_seconds=3600,new_owned_bytes=5_000_000)
RUN=STATE/'d043-perpetual-213-financial-independent-20261003-v1'
OUT=ROOT/'reports/fast_research/PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V1.json'

def need(ok,reason):
    if not bool(ok):raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def load(path,digest,name):
    p=Path(path);need(p.is_file() and not p.is_symlink() and sha(p)==digest,'Exact independent source '+str(p))
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def pin(g,fin,path,digest):
    p=fin.project(g,path)
    if path=='state/dataset_lock.json':need(sha(p)==digest,'Private scientific lock hash-only')
    else:g.small(p,digest,False)

def source_metadata(h,manifest):
    """Independent metadata role normalization; no producer context imported."""
    need(manifest['status']==INPUT_STATUS and manifest['funding_rate_unit']=='UNCONFIRMED'
        and manifest['funding_unit_certified'] is False and manifest['locked_consumed'] is False
        and manifest['preceding_547_failure_preserved'] is True
        and manifest['period_chosen_on_source_completeness_before_new_PnL'] is True,
        'Complete accepted213 input only; failed547/source-selected calendar retained')
    need(len(manifest['source_files'])==72 and len(manifest['windows'])==1,'One exact72-input window')
    window=manifest['windows'][0]
    need((window['id'],window['start'],window['end_exclusive'],window['days'],window['minutes_per_symbol'])
        ==(PERIOD,START,END,213,306720),'Fixed all213 days and306720 minutes, no selected subwindow')
    expected={h.identity(e):e for e in h.source_entries()};seen=[]
    layout={
        'trade_1m':('klines','1m','trade:1m:','2024-01','2024-07',306720),
        'mark_1m':('markPriceKlines','1m','markPriceKlines:','2024-01','2024-07',306720),
        'funding':('fundingRate',None,'fundingRate:','2024-01','2024-07',None),
        'trade_1d_warmup':('klines','1d','trade:1d:','2023-06','2023-12',214),
        'trade_1d_score':('klines','1d','trade:1d:','2024-01','2024-07',213),
        'signal_warmup_2h':('klines','2h','trade:2h:','2023-12','2023-12',372)}
    for symbol in SYMS:
        roles=window['source_ids'][symbol];declared=window['symbols'][symbol]
        need(set(roles)==set(layout) and declared['source_ids']==roles,'All six independently identified source roles')
        for role,(kind,interval,prefix,first,last,count) in layout.items():
            ids=[prefix+symbol+':'+month for month in h.month_range(first,last)]
            need(roles[role]==ids,'Complete chronological product/month source IDs '+symbol+' '+role)
            for identity in ids:
                item=manifest['source_files'][identity];key=h.identity(item)
                need(key==(kind,symbol,interval,identity[-7:]) and key in expected
                    and all(item['entry'].get(k)==v for k,v in expected[key].items())
                    and type(item['rows']) is int and item['rows']>0
                    and item['format_evidence_role']=='D043_213_FIRST_INDEPENDENT_FORMAT_CALENDAR_QA',
                    'Exact first-independent source entry, no Spot/index or failedAugust substitution')
                product='USD_M_PERPETUAL_TRADE_KLINES' if kind=='klines' else 'USD_M_PERPETUAL_'+kind
                need(item['product']==product,'Explicit USD-M product and clock role')
                seen.append(identity)
            actual_count=sum(manifest['source_files'][i]['rows'] for i in ids)
            if count is not None:need(actual_count==count,'Every required score/warmup row')
            else:need(declared['rows_inherited_from_receipts']['funding']==actual_count,'Actual original funding count, no8h presumption')
    need(len(seen)==len(set(seen))==72 and set(seen)==set(manifest['source_files']),'All72 required inputs used, no extra or skipped source')
    return window

def prepare_signal_reader(h,fin):
    """Accepted independent Polars OHLC reader; three explicit metadata changes."""
    reference=load(ROOT/h.DONCHIAN_REFERENCE,h.DONCHIAN_REFERENCE_SHA,'d043_213_original_donchian_reference')
    tree=ast.parse((ROOT/h.DONCHIAN_REFERENCE).read_bytes())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='signal_reader']
    need(len(nodes)==1,'Unique accepted signal reader');node=nodes[0];matches=0
    for part in ast.walk(node):
        if isinstance(part,ast.Constant) and part.value=='2025-07':part.value='2023-12';matches+=1
    need(matches==1,'Only warmup month literal; aggregation and value checks unchanged')
    need(reference.JULY==fin.stamp('2025-07-01T00:00:00+00:00')
        and reference.AUGUST==fin.stamp('2025-08-01T00:00:00+00:00'),'Exact two accepted signal clock globals')
    namespace=dict(vars(reference),JULY=fin.stamp(WARM),AUGUST=fin.stamp(START))
    exec(compile(ast.fix_missing_locations(ast.Module([node],type_ignores=[])),
        '<D043-private-213-accepted-signal-reader>','exec'),namespace)
    proof=dict(base_sha256=h.DONCHIAN_REFERENCE_SHA,changes=[
        dict(anchor='signal_reader single warmup-month literal',old='2025-07',new='2023-12',matches=1),
        dict(anchor='private JULY clock',old='2025-07-01',new='2023-12-01'),
        dict(anchor='private AUGUST clock',old='2025-08-01',new='2024-01-01')],
        derived_signal_reader_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
        target_reference_unchanged_direct_reference=True,financial_audit_case_unchanged_direct_reference=True)
    return reference,namespace['signal_reader'],proof

def signal_input_proofs(manifest,window):
    roles=window['source_ids'];identities=[roles[s]['signal_warmup_2h'][0] for s in SYMS]
    for i in range(7):identities.extend(roles[s]['trade_1m'][i] for s in SYMS)
    result=[]
    for identity in identities:
        item=manifest['source_files'][identity]
        result.append(dict(id=identity,path=item['normalized_path'],sha256=item['normalized_sha256'],
            bytes=item['normalized_bytes'],rows=item['rows'],format_evidence_role=item['format_evidence_role'],
            role='SIGNAL_ONLY_NOT_EXECUTION_OR_RISK'))
    return result

def cash_alias(fin,case,original,verified,maximum):
    """No second minute scan: exact artifacts and all economic summary fields."""
    need(case['mode']==original['mode']=='CASH' and case['artifacts']==original['artifacts']
        and case['shared_constant_cash_artifact_directory']==str(Path(original['artifacts']['targets.parquet']['path']).parent),
        'Constant CASH selector shares exact same saved files, not a new finance result')
    excluded={'cost_scenario','unit_scenario','configured_nominal_roundtrip_bps'}
    need({k:v for k,v in case['summary'].items() if k not in excluded}
        =={k:v for k,v in original['summary'].items() if k not in excluded},'Every other constant-cash economic/clock summary field exact')
    for k in ('net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','terminal_marked_notional'):
        fin.same(fin.exact(case['summary'],k),0.,'CASH alias has no configured-cost or unit income',maximum)
    result=copy.deepcopy(verified)
    result.update(id=case['id'],cost_id=case['cost_id'],unit_id=case['unit_id'],
        verification_method='EXACT_SAME_CASH_ARTIFACTS_AND_ALL_ECONOMIC_SUMMARY_FIELDS_REUSE',
        financial_artifact_set_reused_from=original['id'],financial_body_executed_for_this_selector=False)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    for key in ('protocol','actual','run_dir','output'):setattr(a,key,getattr(a,key).absolute())
    g=load(ROOT/GUARD,GUARD_SHA,'d043_financial_guards');own=sha(__file__);task=os.getenv('COIN_TASK_ID')
    need(task and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Bounded clean progress CPU2 runtime')
    need(a.protocol.parent==ROOT/'protocols' and a.actual.parent==ROOT/'reports/fast_research'
        and a.run_dir==RUN and a.run_dir.is_dir() and not a.run_dir.is_symlink()
        and {f.name for f in RUN.iterdir()}=={'ACTUAL_BINDING.json'} and a.output==OUT and not OUT.exists(),
        'Exclusive manifest-only financial audit and unique output')
    plan,plan_sha=g.small(RUN/'ACTUAL_BINDING.json')
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['budgets']==BUDGET
        and plan['protocol_path']==a.protocol.relative_to(ROOT).as_posix()
        and plan['actual_report']==a.actual.relative_to(ROOT).as_posix()
        and plan['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10),'Exact prebound invocation and original tolerance')
    binding=dict(task_id=task,checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,
        source_hashes=plan['source_hashes'],actual_reports={str(a.actual):plan['actual_report_sha256']},
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        exact_command=shlex.join([sys.executable,*sys.argv]))
    g.write(RUN/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status();rows=[];maximum=dict(cash=0.,ratio=0.)
    report=dict(status=FAIL,binding=binding,run_dir=str(RUN),run_binding_sha256=sha(RUN/'RUN_BINDING.json'),
        independent_source_sha256=own,cases=rows,tolerances=plan['tolerances'],maximum_errors=maximum,
        financial_method='UNCHANGED_1C4B_SPARSE_HANDLEDGER_DECIMAL_MARGIN_AND_NUMPY_MINUTE_DAY_MONTH_ASSERTIONS',
        source_QA_repeated=False,old_accounts_replayed=False,original_failed547_replayed=False,
        full_market_frozen_order_quantity_sizing_independently_rebuilt=False,
        future_poison_payload_independently_replayed=False,
        causal_scope='EXACT_NEW_TARGETS_AND_AVAILABILITY_AT_ALL_DECISIONS_PLUS_PINNED_PRIOR_TARGET_CONTROLLER_FIXTURES_AND_NEW_DATE_WIRING_RECEIPT',
        funding_rate_unit='UNCONFIRMED',unit_certified=False,publication_or_exact_charge_certified=False,
        native_market_certified=False,long_term_APR='NOT_EVALUABLE',candidate='NO_QUALIFIED_CANDIDATE',
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,financial_case_calls=0,shared_CASH_artifact_equivalences_verified=0)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D043-213D-TWENTY-FINANCIAL-INDEPENDENT-20261003-V1',
        event_id=task+':START',event_type='INDEPENDENT_FINANCIAL_START',git_commit=binding['git_commit'],
        protocol_hash=plan['protocol_sha256'],data_manifest_hash=plan['actual_report_sha256'],
        feature_set='SMA_DAILY_FOUR_DIRECTION_AND_DONCHIAN2H_LONG_ONLY',labels='NONE',model_family='NONE',seed=None,
        thresholds=dict(**BUDGET,**plan['tolerances']),cost_assumptions='BASE27_STRESS43_TWO_UNCONFIRMED_UNIT_SCALES',
        all_folds='SEEN_COMPLETE213_JAN_JUL2024_ONE_INDEPENDENT_ACCOUNT_WINDOW',success_failure='START_BEFORE_FINANCIAL_ARRAYS',
        reason_for_next_experiment='Independent accounting of fixed213 source-complete screening; preserve rejected547 interval',
        result_influenced_later_choice=False,source_hashes=plan['source_hashes'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    error=None;progress=None
    def budget():
        need(time.monotonic()-started<=3600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=3_000_000_000,
            'Frozen3600s/RSS3GB financial-only audit')
    try:
        g.bounded(before)
        need(plan['source_hashes'].get(HELPER)==HELPER_SHA and plan['source_hashes'].get(GUARD)==GUARD_SHA
            and plan['source_hashes'].get(HOOK)==HOOK_SHA
            and plan['source_hashes'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,
            'Own, date adapter, raw-hook and guard sources explicitly frozen')
        h=load(g.project(HELPER),HELPER_SHA,'d043_financial_date_adapter')
        fin,reader,reader_proof=h.prepare_financial_adapter()
        reference,signal_reader,signal_proof=prepare_signal_reader(h,fin)
        hand=load(ROOT/h.HAND,h.HAND_SHA,'d043_financial_hand')
        hook=load(ROOT/HOOK,HOOK_SHA,'d043_financial_donchian_hooks')
        report['private_derivations']=dict(financial_reader=reader_proof,signal_reader=signal_proof)
        need(fin.CASH_TOL==1e-7 and fin.RATIO_TOL==1e-10 and h.TOLERANCES==plan['tolerances'],'Financial body/tolerances exact')
        imported={HELPER:HELPER_SHA,GUARD:GUARD_SHA,HOOK:HOOK_SHA,h.FINANCE:h.FINANCE_SHA,h.HAND:h.HAND_SHA,
            h.DONCHIAN_REFERENCE:h.DONCHIAN_REFERENCE_SHA,**EXTRA_PINS}
        need(all(plan['source_hashes'].get(p)==v for p,v in imported.items()),'All imported independent financial/scientific/progress dependencies pinned')
        spec,proto_sha=g.small(a.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(a.actual,plan['actual_report_sha256'])
        need(spec['contract_id']==CONTRACT and spec['period_ids']==[PERIOD]
            and actual['status']==ACTUAL_STATUS and actual['required_cases']==actual['completed_cases']==20
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'] and actual['unit_certified'] is False
            and actual['native_market_certified'] is False,'Actual20 fixed conditional selectors and exact new protocol')
        report['actual_task']=g.closed(plan['actual_task_id']);run=Path(spec['run_dir'])
        need(run.parent==STATE and not run.is_symlink(),'One explicit new financial producer owner')
        rb,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Actual producer RUN_BINDING')
        hashes={a.protocol.relative_to(ROOT).as_posix():proto_sha,a.actual.relative_to(ROOT).as_posix():actual_sha}
        for path,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(path not in hashes or hashes[path]==digest,'No conflicting source/dependency map');pin(g,fin,path,digest);hashes[path]=digest
        need(spec['frozen_sources']['src/quant/perpetual_account.py']==ACCOUNT_SHA,'Accepted exact settlement core, no fee or debt epsilon modification')
        rules=spec['rules'];need(all(rules[k]==v for k,v in dict(initial_capital_USDT=10000.,annual_vol_target=.10,
            past_covariance_completed_days=30,asset_abs_cap=.3,gross_cap=.6,leverage=1,MMR=.005,sizing_buffer=.99,
            taker_fee_bps_per_side=5.5,participation_rate=.001,maximum_attempts=5,
            period_id=PERIOD,score_start=START,score_end_exclusive=END,planned_selectors=20,
            planned_trading_account_simulations=16,planned_constant_cash_baselines=1,
            fresh_flat_each_strategy_direction=True,no_saved_old_financial_accounts_replayed=True,
            original_547D_source_failure_preserved=True,original_547D_source_completed=False).items()),
            'Same original capital/cost/caps/covariance/latency assumptions; new exact213 period')
        need(rules['strategy_design']==[dict(strategy_id=SMA_ID,mode=m) for m in MODES[:-1]]
            +[dict(strategy_id=DONCHIAN_ID,mode='LONG_ONLY')],'Exactly four SMA modes and original Donchian long-only')
        costs=spec['cost_scenarios'];units=spec['unit_scenarios']
        need([(c['id'],c['half_spread_bps'],c['slippage_bps'],c['roundtrip_bps']) for c in costs]==[(k,*v) for k,v in fin.COSTS.items()]
            and [(u['id'],fin.dec(u['scale'])) for u in units]==list(fin.UNITS.items()),'Original two cost and two unconfirmed unit scales')
        source_ref=spec['trade_source_acceptance'];source,source_sha=g.small(fin.project(g,source_ref['path']),source_ref['sha256'])
        need(source['status']==source_ref['required_status']==SOURCE_STATUS and source['actual_archives']==72
            and source['reused_failed_parent_complete_files']==51 and source['new_files']==21
            and source['funding_rate_unit']=='UNCONFIRMED' and source['funding_unit_certified'] is False,'Complete new72 mixed-owner source acceptance only')
        report['source_acceptance_task']=g.closed(source['binding']['task_id'])
        hashes[source_ref['path']]=source_sha
        failed_ref=spec['preceding_failed_source'];failed,failed_sha=g.small(fin.project(g,failed_ref['path']),failed_ref['sha256'])
        need(failed_sha=='82cae26a2313417c59e6a63af8458d775851e7c1e341d51bc9e7fa9a2cf6c427'
            and failed['status']==failed_ref['required_status']=='FAIL_D042_HISTORY_SOURCE'
            and failed['completed_files']==83 and failed['required_files']==148 and failed['source_acceptance_granted'] is False,
            'Original full547 real source failure stays rejected')
        report['preceding_failure_task']=g.closed(failed['binding']['task_id'],1);hashes[failed_ref['path']]=failed_sha
        mref=spec['input_manifest'];manifest,manifest_sha=g.small(fin.project(g,mref['path']),mref['sha256'])
        need(mref['path']==source['input_binding_path'] and manifest_sha==source['input_binding_sha256'],'Source acceptance pins this exact new input manifest')
        window=source_metadata(h,manifest);hashes[mref['path']]=manifest_sha
        smoke_ref=spec['required_smoke_receipt'];smoke,smoke_sha=g.small(fin.project(g,smoke_ref['path']),smoke_ref['sha256'])
        need(smoke['status']==smoke_ref['required_status'] and smoke['test_exit_code']==0 and smoke['source_bytes_unchanged'] is True,
            'New route smoke actually passed against unchanged source; no old suite replay')
        report['synthetic_task']=g.closed(smoke['binding']['task_id']);hashes[smoke_ref['path']]=smoke_sha
        selectors=[f'{PERIOD}_{m}_{c}_{u}' for m in MODES for c in fin.COSTS for u in fin.UNITS]
        need([c['id'] for c in actual['cases']]==selectors and len(actual['input_windows'])==1
            and actual['planned_trading_account_simulations']==actual['completed_trading_account_simulations']==16
            and actual['planned_constant_cash_baselines']==actual['completed_constant_cash_baselines']==1,
            'All20 selectors,16 physical trading accounts and1 exact constant CASH account')
        # Both reader AST spans have compiled before the first payload read.
        report['metadata_and_private_anchors_complete_before_payload']=True;budget()
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(20);w=reader(manifest,window);produced=actual['input_windows'][0]
        need(produced['id']==PERIOD and produced['input_proofs']==w['proofs']+signal_input_proofs(manifest,window)
            and produced['original_funding_events']==len(w['events'])
            and produced['score_start_us']==w['start'] and produced['score_end_exclusive_us']==w['end'],
            'Every financial input and every signal-only input exact; no array filtering or replacement')
        warm=dict(sources=[manifest['source_files'][window['source_ids'][s]['signal_warmup_2h'][0]] for s in SYMS])
        signal,signal_sources=signal_reader(fin,manifest,warm,w)
        need(signal.height==2*(372+213*12),'Full December2h warmup and all213 scored days')
        report['signal_source_proofs']=signal_sources
        expected_targets={m:fin.target_reference(w,m) for m in MODES[:-1]}
        expected_targets['DONCHIAN_LONG_ONLY']=reference.target_reference(fin,w,signal,hook)
        cash_original=cash_verified=None
        for case in actual['cases']:
            selector=case['selector_mode'];need(selector in MODES,'One fixed selector identity')
            expected_mode='LONG_ONLY' if selector=='DONCHIAN_LONG_ONLY' else selector
            strategy=DONCHIAN_ID if selector=='DONCHIAN_LONG_ONLY' else SMA_ID
            need(case['period']==PERIOD and case['mode']==expected_mode and case['strategy_id']==strategy
                and case['summary']['strategy_id']==strategy
                and case['summary']['cost_scenario']==next(c for c in costs if c['id']==case['cost_id'])
                and case['summary']['unit_scenario']==next(u for u in units if u['id']==case['unit_id']),
                'No conflation of SMA LONG_ONLY and Donchian; exact configured cost/unit')
            progress.update('固定213日 · 20选择器独立资金与原hook因果',len(rows),20,'选择器',strategy=selector,cost=case['cost_id'],funding_unit=case['unit_id'])
            target,witness=expected_targets[selector]
            if selector=='CASH' and cash_original is not None:
                item=cash_alias(fin,case,cash_original,cash_verified,maximum)
                report['shared_CASH_artifact_equivalences_verified']+=1
            else:
                item=h.financial_case_interface(fin,w,case,g,hand,run,target,witness,maximum)
                item.update(verification_method='UNCHANGED_ACCEPTED_FULL_FINANCIAL_BODY',financial_body_executed_for_this_selector=True)
                report['financial_case_calls']+=1
                if selector=='CASH':cash_original,cash_verified=case,item
            item.update(selector_mode=selector,strategy_id=strategy,
                signal_reference=dict(decision_rows=target.height,timeframe_minutes=120 if selector=='DONCHIAN_LONG_ONLY' else 1440,
                    independent_reference='UNCHANGED_D041_SCALAR_PRIOR20_CURRENT200_RAW_HOOKS' if selector=='DONCHIAN_LONG_ONLY' else 'UNCHANGED_1C4B_SCALAR50_200_DIRECTION_STATE',
                    covariance_completed_daily_returns=30,warmup_position_carried=False,
                    closed_bar_availability_proxy_not_certified_publication=True))
            rows.append(item);gc.collect();budget()
        del w,signal,expected_targets;gc.collect()
        need(len(rows)==20 and report['financial_case_calls']==17 and report['shared_CASH_artifact_equivalences_verified']==3,
            'Truthful17 full financial calls plus3 identical cash aliases, not20 physical replays')
        need(actual['completed_full_calendar_cases']==sum(c['complete_calendar_verified'] for c in rows)
            and actual['incomplete_or_halted_cases']==sum(not c['complete_calendar_verified'] for c in rows),
            'Producer full/prefix-halt counts match independent financial scope')
        for path,digest in hashes.items():pin(g,fin,path,digest)
        report.update(status=STATUS,verified_source_hashes=hashes,actual_report_sha256=actual_sha,protocol_sha256=proto_sha,
            actual_run_binding_sha256=rb_sha,required_cases=20,completed_cases_verified=20,
            completed_full_calendar_cases_verified=sum(c['complete_calendar_verified'] for c in rows),
            incomplete_or_halted_cases_verified=sum(not c['complete_calendar_verified'] for c in rows),
            source_files_verified_by_prior_accepted_QA=72,
            original_funding_events=sum(manifest['windows'][0]['symbols'][s]['rows_inherited_from_receipts']['funding'] for s in SYMS),
            unique_score_minutes_per_account=306720,unique_score_days=213,unique_score_months=7,
            financial_observation_counts_scope='FULL_OR_PREFIX_CASE_COUNTS_INCLUDE_EXACT_IDENTICAL_CASH_SELECTOR_ALIASES',
            realized_risk_matched_claimed=False,complete547_research_claimed=False)
        budget()
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        gc.collect();report.update(completed_cases_verified=len(rows),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after']);budget()
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if error:report['status']=FAIL
        digest,size=g.write(OUT,report)
        need(sum(p.stat().st_size for p in RUN.iterdir() if p.is_file())+size<=5_000_000,'Only small metadata audit output budget')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='INDEPENDENT_FINANCIAL_RESULT',
            success_failure=report['status'],artifact_path=OUT.relative_to(ROOT).as_posix(),artifact_sha256=digest))
        print(json.dumps(dict(status=report['status'],report=str(OUT),sha256=digest,completed_cases=len(rows),task_id=task)),flush=True)
    if error:raise error

if __name__=='__main__':main()
