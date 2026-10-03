"""UNRUN D044 twelve constant-long conditional perpetual account checks.

Only this cache draft is new. No Python, source arrays, HTTP, old accounts or
financial tests were run while preparing it. Root must settle the final small
production schema, freeze exact ACTUAL_BINDING and wait for actual closed0.

Original audit_case/HandLedger are direct immutable imports. 213D uses the
accepted private date-map helper;122D/90D use the original financial reader.
The only new mathematical oracle is raw(.3,.3) at each scored daily decision,
with the same200-completed-daily warm guard and last31-close sample covariance.
No producer fixed_targets or finance is imported. This is not Spot EWMA.

CLI --protocol --actual --run-dir --output. ACTUAL_BINDING: ready_to_execute,
checker_sha256, protocol_path/SHA, actual_report/SHA, actual_task_id,
source_hashes, tolerances, budgets; original_input_manifests maps the three
periods to exact old metadata refs; accepted_source_receipts lists the two
already accepted source-root refs.
The production spec supplies one virtual combined input_manifest, period_ids,
rules, cost_scenarios, unit_scenarios and required_smoke_receipt. These final
schema choices remain unbound until root reviews this unrun draft.
"""
from __future__ import annotations
import argparse, gc, hashlib, importlib.util, json, math, os, resource, shlex, subprocess, sys, time
from pathlib import Path
import numpy as np
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
BASE='docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py'
BASE_SHA='1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb'
HELPER='docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
HELPER_SHA='f50223ad5ec0da2be16ae3ac5447bec2d5763260566000893f1697483b7667e4'
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
HAND='docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
HAND_SHA='3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
ACCOUNT_SHA='cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261'
PINS={BASE:BASE_SHA,HELPER:HELPER_SHA,GUARD:GUARD_SHA,HAND:HAND_SHA,
    'scripts/research_v8/funding_price_source_v2.py':'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
    'scripts/research_v7/oracle_flow_ceiling.py':'959f63f40c3294b6b2b75267b9138202df79223a7e7723397cf06b8d45a1477e',
    'scripts/research_v8/registry.py':'081f881f2cb1cdc84b8c098606e9f3235c92fcdd04c0120527bee0d8493068ab'}
STATUS='PASS_D044_TWELVE_CONSTANT_LONG_PERPETUAL_ACCOUNTS_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
FAIL='FAIL_D044_CONSTANT_LONG_PERPETUAL_INDEPENDENT_AUDIT'
CONTRACT='D044_THREE_SEEN_USDM_PAST30_COVARIANCE_HOLD_REFERENCE_V1'
ACTUAL_STATUS='COMPLETE_D044_TWELVE_CONDITIONAL_PERPETUAL_HOLD_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
STRATEGY_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
REUSE_STATUS='PASS_D044_EXISTING_ACCEPTED_SOURCE_ONLY_NO_REPEATED_QA'
REUSE_SHA='ed697c8471f888cf5e09016d4fa117e951430f5a3a5fe61ff79a2a0df7d20485'
INPUT_STATUS='BOUND_D044_THREE_PREVIOUSLY_ACCEPTED_USDM_WINDOWS_NOT_ECONOMICS'
PERIODS=('213D','122D','90D');SYMS=('BTCUSDT','ETHUSDT');DAY=86_400_000_000
DATES={
    '213D':('2024-01-01T00:00:00+00:00','2024-08-01T00:00:00+00:00',213,306720),
    '122D':('2025-08-01T00:00:00+00:00','2025-12-01T00:00:00+00:00',122,175680),
    '90D':('2025-12-01T00:00:00+00:00','2026-03-01T00:00:00+00:00',90,129600)}
OLD_INPUTS={
    '213D':('reports/fast_research/PERPETUAL_213D_INPUT_BINDING_20261003_V1.json',
        '904e05176d8332f07c500047baf5ef8a26925f70ed5d4b8b58e3d45fc4da7553',
        'PASS_D043_FIXED_213D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'),
    '122D':('reports/fast_research/LONG_SHORT_USDM_INPUT_BINDING_20261003_V1.json',
        'f7b3e8eb724b8196280ef872454b36297171b5f487bea94410dc547eb846d045',
        'BOUND_LONG_SHORT_USDM_INPUT_METADATA_ONLY_NOT_SOURCE_OR_ECONOMIC_ACCEPTANCE'),
    '90D':('reports/fast_research/LONG_SHORT_USDM_INPUT_BINDING_20261003_V1.json',
        'f7b3e8eb724b8196280ef872454b36297171b5f487bea94410dc547eb846d045',
        'BOUND_LONG_SHORT_USDM_INPUT_METADATA_ONLY_NOT_SOURCE_OR_ECONOMIC_ACCEPTANCE')}
BUDGET=dict(peak_RSS_bytes=3_000_000_000,wall_seconds=3600,new_owned_bytes=5_000_000)
RUN=STATE/'d044-constant-long-financial-independent-20261003-v1'
OUT=ROOT/'reports/fast_research/PERPETUAL_CONSTANT_LONG_REFERENCE_INDEPENDENT_20261003_V1.json'

def need(ok,reason):
    if not bool(ok):raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def load(path,digest,name):
    p=Path(path);need(p.is_file() and not p.is_symlink() and sha(p)==digest,'Exact accepted source '+str(p))
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def pin(g,b,path,digest):
    p=b.project(g,path)
    if path=='state/dataset_lock.json':need(sha(p)==digest,'Private scientific lock SHA only, no JSON/body')
    else:g.small(p,digest,False)

def metadata_bridge(b,manifest,originals):
    """The frozen virtual catalogue has no collisions or modified file entries."""
    need(manifest['funding_rate_unit']=='UNCONFIRMED' and manifest['funding_unit_certified'] is False
        and manifest['locked_consumed'] is False,'Combined view cannot certify units or expand locked IO')
    need([w['id'] for w in manifest['windows']]==list(PERIODS),'Exactly three fixed whole windows, separate accounts')
    union={}
    for parent in originals.values():
        for identity,item in parent['source_files'].items():
            need(identity not in union or union[identity]==item,'No differing original entry under the same source ID')
            union[identity]=item
    need(len(union)==156 and manifest['source_files']==union,'Exact156 accepted entries; no prefix or modified identity/value')
    proofs=[]
    roles=('trade_1m','mark_1m','trade_1d_warmup','trade_1d_score','funding')
    for period in PERIODS:
        parent=originals[period];prior=next(w for w in parent['windows'] if w['id']==period)
        view=next(w for w in manifest['windows'] if w['id']==period)
        need((view['start'],view['end_exclusive'],view['days'],view['minutes_per_symbol'])==DATES[period]
            and view==prior,
            'Fixed original complete dates/count; no NAV stitching or shortened warmup')
        for symbol in SYMS:
            new=view['symbols'][symbol];old=prior['symbols'][symbol]
            need(new['rows_inherited_from_receipts']==old['rows_inherited_from_receipts'],
                'Actual original event counts, never assumed8h or borrowed counts')
            for role in roles:
                new_ids=new['source_ids'][role];old_ids=old['source_ids'][role]
                need(new_ids==old_ids and len(set(new_ids))==len(new_ids),'Exact original source ID count/order for each role')
                for new_id,old_id in zip(new_ids,old_ids,strict=True):
                    observed=manifest['source_files'][new_id];accepted=parent['source_files'][old_id]
                    # Source identity is metadata-only here; payload bytes are
                    # hashed by the unchanged reader at the authorized run.
                    keys=('normalized_path','normalized_sha256','normalized_bytes','rows','format_evidence_role')
                    need(all(observed[k]==accepted[k] for k in keys),'Prefix cannot alter any physical financial source')
                    for key in ('symbol','month','kind','interval','product','receipt_path','receipt_sha256','source_owner_path'):
                        if key in accepted:need(observed.get(key)==accepted[key],'Exact original source metadata '+key)
                    need(observed['symbol']==symbol,'No symbol/product source collision after prefixing')
                    proofs.append(dict(period=period,symbol=symbol,role=role,combined_id=new_id,original_id=old_id,
                        path=observed['normalized_path'],sha256=observed['normalized_sha256'],rows=observed['rows']))
            for role in set(new['source_ids'])-set(roles):
                need(role=='signal_warmup_2h' and period=='213D'
                    and [manifest['source_files'][x]['normalized_sha256'] for x in new['source_ids'][role]]
                        ==[parent['source_files'][x]['normalized_sha256'] for x in old['source_ids'][role]],
                    'Any retained2h metadata is the accepted213 warmup, never read by constant-long finance')
        if period=='213D':need(parent['preceding_547_failure_preserved'] is True,'Original rejected547 remains rejected')
    # A virtual view may retain accepted2h metadata, but it cannot introduce
    # any arbitrary path absent from both frozen original input catalogues.
    catalog_paths={v['normalized_path'] for p in originals.values() for v in p['source_files'].values()}
    need(all(v['normalized_path'] in catalog_paths for v in manifest['source_files'].values()),'Only old accepted source universe, no implicit data scan')
    return proofs

def target_reference(b,w):
    """Daily constant LONG_ONLY; original200 availability and last30 covariance."""
    rows=[];witness=[]
    for t in range(w['start'],w['end'],DAY):
        returns=[];local=[]
        for symbol in SYMS:
            bars=w['bars'][symbol]
            need(all(bars.schema[k]==pl.Int64 and bars[k].null_count()==0 for k in ('close_us','available_us')),
                'Known integer daily observation clocks')
            closes_us=bars['close_us'].to_numpy();available=bars['available_us'].to_numpy()
            i=int(np.searchsorted(closes_us,t,side='right')-1)
            need(i>=199 and closes_us[i]==t and np.all(np.diff(closes_us[i-199:i+1])==DAY)
                and np.all(available[i-199:i+1]<=t),'Same200 completed contiguous available daily warm guard')
            selected=bars['close'][i-199:i+1].to_numpy()
            need(np.isfinite(selected).all() and np.all(selected>0),'Finite positive actual observed daily prices')
            prices=selected[-31:];returns.append(np.diff(prices)/prices[:-1])
            local.append(dict(decision_us=int(t),symbol=symbol,raw_signed_target=.3,
                completed_daily_warmup_observations=200,risk_first_close_us=int(closes_us[i-30]),
                risk_last_close_us=int(closes_us[i]),maximum_available_us=int(available[i-199:i+1].max()),
                covariance_returns=30,signal_is_constant_not_SMA_or_EWMA=True))
        observations=np.column_stack(returns);center=observations-observations.mean(axis=0)
        covariance=center.T@center/29*365
        raw=np.asarray([.3,.3]);sigma=math.sqrt(max(float(raw@covariance@raw),0.))
        weights=raw*(.10/sigma) if sigma>.10 else raw
        for symbol,weight,info in zip(SYMS,weights,local,strict=True):
            rows.append((int(t),symbol,float(weight),.3,'LONG_ONLY'));witness.append(info)
    return pl.DataFrame(rows,schema=['available_us','symbol','target_weight','raw_signed_target','mode'],orient='row'),witness

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    for key in ('protocol','actual','run_dir','output'):setattr(a,key,getattr(a,key).absolute())
    b=load(ROOT/BASE,BASE_SHA,'d044_original_financial');g=load(ROOT/GUARD,GUARD_SHA,'d044_frozen_guards')
    h=load(ROOT/HELPER,HELPER_SHA,'d044_accepted_213_reader');hand=load(ROOT/HAND,HAND_SHA,'d044_sparse_hand')
    _,reader213,reader_proof=h.prepare_financial_adapter() # Compile only the date map before any arrays.
    own=sha(__file__);task=os.getenv('COIN_TASK_ID')
    need(task and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Clean bounded CPU2 progress task')
    need(a.protocol.parent==ROOT/'protocols' and a.actual.parent==ROOT/'reports/fast_research'
        and a.run_dir==RUN and a.run_dir.is_dir() and not RUN.is_symlink()
        and {f.name for f in RUN.iterdir()}=={'ACTUAL_BINDING.json'} and a.output==OUT and not OUT.exists(),
        'Exclusive new manifest-only financial STATE and output')
    plan,plan_sha=g.small(RUN/'ACTUAL_BINDING.json')
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['budgets']==BUDGET
        and plan['protocol_path']==a.protocol.relative_to(ROOT).as_posix()
        and plan['actual_report']==a.actual.relative_to(ROOT).as_posix()
        and plan['tolerances']==dict(cash_USDT=b.CASH_TOL,ratio=b.RATIO_TOL)
        and b.CASH_TOL==1e-7 and b.RATIO_TOL==1e-10,'Prebound new invocation and original tolerances unchanged')
    binding=dict(task_id=task,checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,source_hashes=plan['source_hashes'],
        actual_reports={str(a.actual):plan['actual_report_sha256']},
        exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    g.write(RUN/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status();rows=[];maximum=dict(cash=0.,ratio=0.)
    report=dict(status=FAIL,binding=binding,run_dir=str(RUN),run_binding_sha256=sha(RUN/'RUN_BINDING.json'),
        independent_source_sha256=own,cases=rows,tolerances=plan['tolerances'],maximum_errors=maximum,
        financial_method='UNCHANGED_1C4B_SPARSE_DECIMAL_HAND_MARGIN_PLUS_NUMPY_ALL_MINUTE_DAY_MONTH_ASSERTIONS',
        private213_reader_derivation=reader_proof,original122_90_reader_unchanged=True,
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,publication_or_exact_charge_certified=False,
        long_term_APR='NOT_EVALUABLE',candidate='NO_QUALIFIED_CANDIDATE',source_QA_repeated=False,
        old_financial_accounts_replayed=False,Spot_EWMA_reference_used=False,financial_case_calls=0,
        full_market_frozen_order_quantity_sizing_independently_rebuilt=False,
        sizing_evidence_scope='ORIGINAL_FROZEN_CONTROLLER_AND_NEW_REQUIRED_ROUTE_RECEIPT_NOT_ALL_MARKET_FROZEN_INTENTS',
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D044-CONSTANT-LONG-TWELVE-INDEPENDENT-20261003-V1',
        event_id=task+':START',event_type='INDEPENDENT_FINANCIAL_START',git_commit=binding['git_commit'],
        protocol_hash=plan['protocol_sha256'],data_manifest_hash=plan['actual_report_sha256'],
        feature_set='CONSTANT_RAW_LONG_03_03_DAILY_30_RETURN_SIGNED_COVARIANCE',labels='NONE',model_family='NONE',seed=None,
        thresholds=dict(**BUDGET,**plan['tolerances']),cost_assumptions='BASE27_STRESS43_TWO_UNCONFIRMED_FUNDING_UNIT_SCALES',
        all_folds='THREE_COMPLETE_SEEN_WINDOWS_SEPARATE_10000_CAPITAL_NO_NAV_STITCH',success_failure='START_BEFORE_FINANCIAL_ARRAYS',
        reason_for_next_experiment='Fixed same-product always-long reference, unchanged risk/cost/account primitives',
        result_influenced_later_choice=False,source_hashes=plan['source_hashes'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    error=None;progress=None
    def budget():
        need(time.monotonic()-started<=3600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=3_000_000_000,
            'Frozen3600s/RSS3GB independent task budget')
    try:
        g.bounded(before)
        need(all(plan['source_hashes'].get(p)==v for p,v in PINS.items())
            and plan['source_hashes'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,'All imported sources and own exact bytes frozen')
        spec,proto_sha=g.small(a.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(a.actual,plan['actual_report_sha256'])
        need(spec['contract_id']==CONTRACT and spec['period_ids']==list(PERIODS)
            and actual['status']==ACTUAL_STATUS and actual['completed_cases']==actual['required_cases']==12
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'] and actual['unit_certified'] is False
            and actual['native_market_certified'] is False,'Exactly twelve real completed conditional selectors')
        report['actual_task']=g.closed(plan['actual_task_id']);run=Path(spec['run_dir'])
        need(run.parent==STATE and not run.is_symlink(),'Explicit new financial producer owner')
        rb,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Exact actual producer RUN_BINDING')
        hashes={a.protocol.relative_to(ROOT).as_posix():proto_sha,a.actual.relative_to(ROOT).as_posix():actual_sha}
        for path,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(path not in hashes or hashes[path]==digest,'No conflicting frozen dependency');pin(g,b,path,digest);hashes[path]=digest
        need(spec['frozen_sources']['src/quant/perpetual_account.py']==ACCOUNT_SHA,'Original exact-settlement core unchanged')
        rules=spec['rules'];need(all(rules[k]==v for k,v in dict(initial_capital_USDT=10000.,annual_vol_target=.10,
            past_covariance_completed_days=30,asset_abs_cap=.3,gross_cap=.6,leverage=1,MMR=.005,sizing_buffer=.99,
            taker_fee_bps_per_side=5.5,participation_rate=.001,maximum_attempts=5).items()),'Original product/capital/risk/fee/latency/capacity')
        need(all(rules[k]==v for k,v in dict(modes=['LONG_ONLY'],strategy_id=STRATEGY_ID,
            signal='CONSTANT_LONG_RAW_POINT3_EACH_ASSET_NO_ALPHA_FILTER',planned_selectors=12,
            planned_trading_account_simulations=12,planned_constant_cash_baselines=0,
            signal_and_risk_timeframe_minutes=1440,raw_targets=[.3,.3],minimum_completed_available_daily_history=200,
            risk_histories='SAME30_COMPLETED_UTC_DAILY_RETURN_COVARIANCE',old_Spot_EWMA_reference_replicated=False,
            original_SMA_alpha_hooks_used=False,old_accounts_or_source_QA_replayed=False,
            original_547D_source_failure_preserved=True,realized_risk_equalized=False).items()),
            'One exact fixed constant-long target and common200-day warm guard')
        need([(c['id'],c['half_spread_bps'],c['slippage_bps'],c['roundtrip_bps']) for c in spec['cost_scenarios']]==[(k,*v) for k,v in b.COSTS.items()]
            and [(u['id'],b.dec(u['scale'])) for u in spec['unit_scenarios']]==list(b.UNITS.items()),'Two frozen costs and conditional scales, no unit inference')
        originals={};need(set(plan['original_input_manifests'])==set(PERIODS),'Exact three original metadata parents')
        for period,ref in plan['original_input_manifests'].items():
            need((ref['path'],ref['sha256'],ref['required_status'])==OLD_INPUTS[period],'Exact previously accepted input view for '+period)
            value,digest=g.small(b.project(g,ref['path']),ref['sha256']);need(value['status']==ref['required_status'],'Original metadata status retained')
            originals[period]=value;hashes[ref['path']]=digest
        source_receipts=[]
        need(len(plan['accepted_source_receipts'])==2,'Two accepted source-root capabilities, no fictitious old source task')
        for ref in plan['accepted_source_receipts']:
            receipt,digest=g.small(b.project(g,ref['path']),ref['sha256'])
            need(receipt['status']==ref['required_status'],'Exact source-root accepted status')
            source_receipts.append(dict(path=ref['path'],sha256=digest,actual_task=g.closed(receipt['binding']['task_id'])))
            hashes[ref['path']]=digest
        report['accepted_source_root_tasks']=source_receipts
        reuse_ref=spec['trade_source_acceptance'];reuse,reuse_sha=g.small(b.project(g,reuse_ref['path']),reuse_ref['sha256'])
        need(reuse_ref['path']=='reports/fast_research/PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json'
            and reuse_sha==REUSE_SHA and reuse['status']==reuse_ref['required_status']==REUSE_STATUS
            and reuse['source_files']==156 and reuse['new_source_QA_or_payload_IO'] is False
            and reuse['old_accounts_replayed'] is False and reuse['funding_unit_certified'] is False,
            'Closed source-only reuse keeps exact156 entries, without new QA or old accounts')
        report['source_reuse_task']=g.closed(reuse['binding']['task_id']);hashes[reuse_ref['path']]=reuse_sha
        original_refs=reuse['original_input_manifests']
        need(plan['original_input_manifests']['213D']==original_refs['213D']['manifest']
            and all(plan['original_input_manifests'][p]==original_refs['122D90D']['manifest'] for p in ('122D','90D')),
            'Original manifests independently match accepted source-reuse capability')
        need({(r['path'],r['sha256'],r['required_status']) for r in plan['accepted_source_receipts']}
            =={(r['root']['path'],r['root']['sha256'],r['root']['required_status']) for r in original_refs.values()},
            'The exact two original source roots, not substitute completed tasks')
        mref=spec['input_manifest'];manifest,manifest_sha=g.small(b.project(g,mref['path']),mref['sha256'])
        need(manifest['status']==mref['required_status']==INPUT_STATUS and mref['path']==reuse['combined_manifest_path']
            and manifest_sha==reuse['combined_manifest_sha256'],'Exact combined metadata view bound by source reuse')
        report['input_source_alias_bridges']=metadata_bridge(b,manifest,originals);hashes[mref['path']]=manifest_sha
        smoke_ref=spec['required_smoke_receipt'];smoke,smoke_sha=g.small(b.project(g,smoke_ref['path']),smoke_ref['sha256'])
        need(smoke['status']==smoke_ref['required_status'] and smoke['test_exit_code']==0 and smoke['source_bytes_unchanged'] is True,
            'Exact passed new route receipt, no rerun old smoke/account/source tests')
        report['synthetic_task']=g.closed(smoke['binding']['task_id']);hashes[smoke_ref['path']]=smoke_sha
        expected=[f'{period}_LONG_ONLY_{cost}_{unit}' for period in PERIODS for cost in b.COSTS for unit in b.UNITS]
        need([c['id'] for c in actual['cases']]==expected and len(actual['input_windows'])==3
            and actual['planned_trading_account_simulations']==actual['completed_trading_account_simulations']==12
            and actual['planned_constant_cash_baselines']==actual['completed_constant_cash_baselines']==0,
            'All12 predeclared constant-long selectors; no result-based case selection')
        report['metadata_and_all_private_anchors_complete_before_payload']=True;budget()
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(12)
        for window,produced in zip(manifest['windows'],actual['input_windows'],strict=True):
            period=window['id'];reader=reader213 if period=='213D' else b.window_reader
            w=reader(manifest,window)
            need(produced['id']==period and produced['input_proofs']==w['proofs']
                and produced['original_funding_events']==len(w['events'])
                and produced['score_start_us']==w['start'] and produced['score_end_exclusive_us']==w['end'],
                'Exact same necessary financial source values/calendar, no Donchian2h input extras')
            target,witness=target_reference(b,w)
            for case in [c for c in actual['cases'] if c['period']==period]:
                need(case['mode']=='LONG_ONLY' and case['strategy_id']==case['summary']['strategy_id']==STRATEGY_ID
                    and case['summary']['cost_scenario']==next(c for c in spec['cost_scenarios'] if c['id']==case['cost_id'])
                    and case['summary']['unit_scenario']==next(u for u in spec['unit_scenarios'] if u['id']==case['unit_id'])
                    and case['summary']['configured_nominal_roundtrip_bps']==b.COSTS[case['cost_id']][2],
                    'Same fixed constant-long recipe and exact cost/unit labels, not original SMA or Donchian state')
                progress.update('常量多头参考 · 新12账户独立资金与过去风险',len(rows),12,'账户',
                    period=period,cost=case['cost_id'],funding_unit=case['unit_id'])
                item=b.audit_case(w,case,g,hand,run,target,witness,maximum)
                item.update(strategy_id=STRATEGY_ID,verification_method='UNCHANGED_ACCEPTED_FINANCIAL_BODY',
                    signal_reference=dict(decision_rows=target.height,raw_signed_weights=[.3,.3],
                        timeframe_minutes=1440,warmup_completed_observations=200,covariance_completed_daily_returns=30,
                        independent_constant_target_and_sample_covariance=True,
                        warmup_position_carried=False,closed_bar_proxy_not_publication_certification=True))
                rows.append(item);report['financial_case_calls']+=1;gc.collect();budget()
            del w,target,witness;gc.collect()
        need(len(rows)==report['financial_case_calls']==12,'Twelve actual new financial body calls, no shared-CASH aliases')
        need(actual['completed_full_calendar_cases']==sum(c['complete_calendar_verified'] for c in rows)
            and actual['incomplete_or_halted_cases']==sum(not c['complete_calendar_verified'] for c in rows),'Honest complete/prefix-halt scope')
        for path,digest in hashes.items():pin(g,b,path,digest)
        report.update(status=STATUS,verified_source_hashes=hashes,actual_report_sha256=actual_sha,protocol_sha256=proto_sha,
            actual_run_binding_sha256=rb_sha,required_cases=12,completed_cases_verified=12,
            completed_full_calendar_cases_verified=sum(c['complete_calendar_verified'] for c in rows),
            incomplete_or_halted_cases_verified=sum(not c['complete_calendar_verified'] for c in rows),
            distinct_seen_windows=3,full_window_required_days=dict(zip(PERIODS,[213,122,90])),
            full_window_required_minutes=dict(zip(PERIODS,[306720,175680,129600])),
            realized_risk_matched_claimed=False,financial_results_stitched=False)
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
        need(sum(p.stat().st_size for p in RUN.iterdir() if p.is_file())+size<=5_000_000,'Only new small audit metadata')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='INDEPENDENT_FINANCIAL_RESULT',
            success_failure=report['status'],artifact_path=OUT.relative_to(ROOT).as_posix(),artifact_sha256=digest))
        print(json.dumps(dict(status=report['status'],report=str(OUT),sha256=digest,completed_cases=len(rows),task_id=task)),flush=True)
    if error:raise error

if __name__=='__main__':main()
