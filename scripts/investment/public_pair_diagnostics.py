"""UNRUN D036: three separate accepted public-pair ledger diagnostics.

Twelve projected Parquets only; no prices, fills, targets, account replay,
combined NAV, new strategy, fits, parameter search or investment qualification.
CLI: --protocol --run-dir --output --experiment-id. Root freezes input metadata
and decision_rule before execution; this script reports evidence, not adoption.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, json, math, os, resource, shlex, shutil, subprocess, sys, threading, time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import numpy as np
import polars as pl
from scipy.stats import pearsonr, spearmanr
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

P = 'COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
H = 'COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
MINUTE, DAY, INITIAL = 60_000_000, 86_400_000_000, 10_000.
FEE_PATH = 'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json'
FEE_SHA = 'd6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f'
FINANCE_AST = '39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73'
PROGRESS_SOURCE = 'scripts/research_v7/oracle_flow_ceiling.py'
RULES = dict(cash_tolerance=1e-7, ratio_tolerance=1e-12, tail_fraction=.10,
    tail_count='CEIL_N_TIMES_0.10_TIES_BY_EARLIER_UTC_DATE', negative_predicate='STRICT_DAILY_NET_PNL_LT_ZERO',
    active_exposure='STRICT_POSITIVE_MARKED_NOTIONAL_INCLUDING_DUST',
    weight_overlap='SUM_MIN_WEIGHT_DIV_SUM_MAX_WEIGHT', combined_NAV_generated=False,
    periods_independent=True, correlations='DESCRIPTIVE_PEARSON_AND_SPEARMAN_NO_SIGNIFICANCE_CLAIM')
R = 'reports/fast_research/'
REPORTS = {
    R+'PUBLIC_LONG_547D_ACTUAL_20261003_V1.json':'c70e3011f74ddbbbf250316bb2cad9a02d2bd6945b266a1a96a1083b9fcbc6e8',
    R+'BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json':'53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',
    R+'BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json':'329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',
    R+'PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1.json':'9e7727b41b994db2ab1d3496094e22ef12de98ab841d050cd1c9c7fd31310313',
    R+'PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1.json':'3b6e1f58c9f76411a5d8bcddde29fdfc3c7bdb955a9f04013269599199c3bfb6',
}
AUDITS = {
    R+'PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json':
        ('c7033ef299071f1d3149381fc19d923487bbbdd1040c4b20c75481058203441d',
         'PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'),
    R+'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json':
        ('70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f',
         'PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE'),
    R+'PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json':
        ('a1af8448c0b44b6e79cbb0123f942bde05b773f90ebb01b0a7b751c4f23f77c9',
         'PASS_HYBRID_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE'),
}
FIXED_PERIODS = (('CONT547','2024-01-01','2025-07-01',547),
    ('CONT122','2025-08-01','2025-12-01',122), ('CONT90','2025-12-01','2026-03-01',90))
DAILY = ('date','nav','return','cash','fees','execution_costs','turnover','gross_weight','stale_prices','stale_exposure')
INVENTORY = ('close_us','cash','BTCUSDT_quantity','BTCUSDT_marked_notional','ETHUSDT_quantity',
    'ETHUSDT_marked_notional','nav','gross_marked_nav_same_quantities','cumulative_fee','cumulative_execution_cost','gross_weight')
PROJECTED = ('close_us','nav','gross_weight','BTCUSDT_marked_notional','ETHUSDT_marked_notional')
FILES = ('daily_nav.parquet','minute_nav_inventory.parquet')
STATUS = 'COMPLETE_D036_SAVED_PUBLIC_PAIR_COMPLEMENTARITY_DIAGNOSTIC_NOT_ENSEMBLE_OR_LONG_TERM_APR'

def require(ok, reason):
    if not ok: raise ValueError(reason)

def sha(path):
    with Path(path).open('rb') as handle: return hashlib.file_digest(handle, 'sha256').hexdigest()

def small(path, digest=None):
    original = Path(path); path = original.resolve()
    require(not original.is_symlink() and path.is_relative_to(ROOT) and path.is_file()
        and path.stat().st_size < 2_000_000, 'Ordinary bounded ROOT small metadata/source')
    data = path.read_bytes(); actual = hashlib.sha256(data).hexdigest()
    require(digest is None or actual == digest, 'Frozen small metadata changed: '+str(path))
    return json.loads(data), actual

def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')

def timestamp(value):
    return int(datetime.combine(date.fromisoformat(value), datetime.min.time(), UTC).timestamp())*1_000_000

def near(left, right, tolerance):
    require(math.isfinite(float(left)) and math.isfinite(float(right)) and abs(float(left)-float(right)) <= tolerance,
        'Saved diagnostic input/summary identity outside fixed numerical tolerance')

def guard_runtime(spec, started):
    require(time.monotonic()-started <= spec['budgets']['wall_seconds'], 'Preserve partial report: wall budget')
    require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= spec['budgets']['peak_RSS_bytes'], 'Preserve partial report: peak RAM budget')

def progress_class(digest):
    source = ROOT/PROGRESS_SOURCE; require(sha(source) == digest, 'Pinned original Progress class')
    nodes = [n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'Progress']
    require(len(nodes) == 1, 'One exact original Progress class')
    original_ast = hashlib.sha256(ast.dump(nodes[0],include_attributes=False).encode()).hexdigest()
    changed = []
    for node in ast.walk(nodes[0]):
        if isinstance(node,ast.Dict):
            for i,key in enumerate(node.keys):
                if isinstance(key,ast.Constant) and key.value in ('total','detail'):
                    require(isinstance(node.values[i],ast.Constant), 'Progress adapter changes literal initialization only')
                    node.values[i] = ast.Constant(value=12 if key.value=='total' else '已接受公开策略账本互补性诊断；不是新组合账户或APR')
                    changed.append(key.value)
    require(sorted(changed)==['detail','total'], 'Exactly two original Progress display literals before thread start')
    ast.fix_missing_locations(nodes[0])
    namespace = dict(os=os, Path=Path, STATE=STATE, json=json, threading=threading, time=time)
    exec(compile(ast.Module(nodes, type_ignores=[]), str(source)+'<original-Progress-only>', 'exec'), namespace)
    return namespace['Progress'], original_ast, hashlib.sha256(ast.dump(nodes[0],include_attributes=False).encode()).hexdigest()

def accepted_inputs(spec):
    """Small saved proofs only. Parquet opens occur later and only for12 files."""
    producers = {path:small(ROOT/path,digest)[0] for path,digest in REPORTS.items()}
    proofs = {path:small(ROOT/path,item[0])[0] for path,item in AUDITS.items()}
    require(all(proofs[p]['status'] == item[1] for p,item in AUDITS.items()), 'Retain exact original accepted audit scopes')
    require(all(spec['frozen_sources'].get(p) == d for p,d in REPORTS.items())
        and all(spec['frozen_sources'].get(p) == v[0] for p,v in AUDITS.items()), 'Bind all original small producer/audit proofs')
    require(len(spec['periods']) == 3, 'All three independent fixed windows required')
    contexts = []
    for period, (fold, first, end, days) in zip(spec['periods'], FIXED_PERIODS, strict=True):
        require((period['id'],period['start'],period['end_exclusive'],period['days'],period['minutes'],period['initial_nav'])
            == (fold,first,end,days,days*1440,INITIAL) and set(period['legs']) == {'P','H'}, 'Exact fixed full UTC window/capital')
        legs = {}
        for side, strategy in (('P',P),('H',H)):
            item = period['legs'][side]; path = item['producer_path']
            require(path in REPORTS and item['producer_sha256'] == REPORTS[path] and item['strategy'] == strategy, 'Exact saved producer/strategy binding')
            producer = producers[path]
            require(producer['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and producer['source_bytes_unchanged']
                and producer['all_planned_ledgers_complete'], 'Previously completed accepted producer only')
            folds = [f for f in producer['folds'] if f['fold'] == fold]
            require(len(folds) == 1 and folds[0]['days'] == days and folds[0]['start_us'] == timestamp(first)
                and folds[0]['end_us'] == timestamp(end), 'Saved actual whole period boundaries')
            rows = [r for r in folds[0]['results'] if r['strategy'] == strategy and r['spread_bps'] == 8]
            require(len(rows) == 1 and rows[0]['nominal_roundtrip_bps'] == 36, 'Unique fixed36bp original account')
            row = rows[0]; summary = row['summary']
            require(summary['initial_nav'] == INITIAL and summary['period_days'] == days
                and summary['fee_settlement_version'] == 'BYBIT_SPOT_RECEIVED_ASSET_V1'
                and summary['bybit_fee_profile_sha256'] == FEE_SHA and summary['derived_AST_SHA256'] == FINANCE_AST
                and not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven'], 'Original proxy finance/capital/qualification scope')
            audit_rows = [r for proof in proofs.values() for r in proof['ledgers']
                if r['fold'] == fold and r['strategy'] == strategy and r['spread_bps'] == 8]
            require(len(audit_rows) == 1, 'One accepted audit selector, not a new old-account financial audit')
            require(set(item['artifacts']) == set(FILES), 'Only two saved Parquet types; fills/market input forbidden')
            for name in FILES:
                artifact = item['artifacts'][name]; prior = row['artifacts'][name]
                expected = str(Path(row['directory'])/name)
                require(artifact == dict(path=expected,sha256=prior['sha256'],bytes=prior['bytes'],rows=days if name==FILES[0] else days*1440)
                    and audit_rows[0]['ledger_artifact_hashes'][name] == prior['sha256'], 'Exact accepted path/hash/size/row-count metadata')
            legs[side] = dict(producer=producer,summary=summary,artifacts=item['artifacts'],audit_selector=fold+':'+strategy)
        left,right = legs['P']['producer'],legs['H']['producer']
        require(left['minute_source']['sha256'] == right['minute_source']['sha256']
            and left['source_receipt_sha256'] == right['source_receipt_sha256']
            and left['registration_start']['hyperparameters'] == right['registration_start']['hyperparameters'], 'Same pair source/capital/risk rules; realized risk can differ')
        contexts.append((period,legs))
    return contexts

def read_artifact(item, name, progress, completed, spec, started, report):
    path = Path(item['path']); resolved = path.resolve()
    require(not path.is_symlink() and resolved.is_relative_to(STATE) and resolved.is_file()
        and resolved.stat().st_size == item['bytes'] and sha(resolved) == item['sha256'], 'Exact immutable saved Parquet bytes before read')
    schema = pl.read_parquet_schema(resolved)
    expected = DAILY if name == FILES[0] else INVENTORY
    require(set(schema) == set(expected), 'Exact accepted ledger columns; no missing projection')
    require(schema['date'] == pl.Date if name == FILES[0] else schema['close_us'] == pl.Int64, 'Original date/integer timestamp type')
    report['saved_ledger_array_read_attempts'] += 1
    frame = pl.read_parquet(resolved,columns=DAILY if name == FILES[0] else PROJECTED)
    report['saved_ledger_arrays_read'] = True
    require(frame.height == item['rows'] and sum(frame.null_count().row(0)) == 0, 'Complete original rows without fill/filter/imputation')
    guard_runtime(spec,started); progress.update('读取已接受账本投影',completed,12,'文件')
    return frame

def daily_arrays(frame, period, summary):
    days = frame['date'].to_numpy().astype('datetime64[D]')
    expected = np.arange(np.datetime64(period['start'],'D'),np.datetime64(period['end_exclusive'],'D'))
    require(np.array_equal(days,expected), 'Full daily UTC scoring date calendar, no reorder or drop')
    numeric = frame.select(pl.exclude('date','stale_prices','stale_exposure')).to_numpy()
    require(np.isfinite(numeric).all() and not frame['stale_prices'].any() and not frame['stale_exposure'].any(), 'Complete finite accepted daily valuations')
    nav = frame['nav'].to_numpy(); require(np.all(nav > 0), 'Positive recorded daily NAV')
    previous = np.r_[INITIAL,nav[:-1]]; delta = nav-previous; returns = delta/previous
    require(np.allclose(returns,frame['return'].to_numpy(),rtol=0,atol=RULES['ratio_tolerance']), 'Recorded net return and continuous NAV arithmetic agree')
    for key,actual,tolerance in (('net_cash_PnL',float(nav[-1]-INITIAL),RULES['cash_tolerance']),
        ('fees',frame['fees'].sum(),RULES['cash_tolerance']),('execution_costs',frame['execution_costs'].sum(),RULES['cash_tolerance']),
        ('turnover',frame['turnover'].sum(),RULES['ratio_tolerance'])):
        near(actual,summary[key],tolerance)
    return dict(nav=nav,pnl=delta,returns=returns,dates=days)

def correlation(left, right):
    if len(left)<2 or np.ptp(left)==0 or np.ptp(right)==0:
        return dict(pearson=None,spearman=None,reason='UNDEFINED_CONSTANT_OR_INSUFFICIENT_SERIES')
    return dict(pearson=float(pearsonr(left,right).statistic),spearman=float(spearmanr(left,right).statistic),reason=None)

def fraction(numerator, denominator):
    return float(numerator/denominator) if denominator else None

def conditional_losses(mask, own, other):
    n = int(mask.sum()); own_loss = float(-own[own<0].sum()); other_loss = float(-other[other<0].sum())
    return dict(days=n,own_signed_PnL_USDT=float(own[mask].sum()),other_signed_PnL_USDT=float(other[mask].sum()),
        other_negative_fraction=fraction(int(np.sum(other[mask]<0)),n),
        own_negative_loss_share=fraction(float(-own[mask & (own<0)].sum()),own_loss),
        other_negative_loss_share=fraction(float(-other[mask & (other<0)].sum()),other_loss))

def diagnose(period, legs, daily, inventory):
    p,h = daily['P'],daily['H']; dp,dh = p['pnl'],h['pnl']; both = (dp<0)&(dh<0)
    n = period['days']; k = math.ceil(n*RULES['tail_fraction']); tails={}; masks={}
    for side,own,other in (('P',dp,dh),('H',dh,dp)):
        selected = np.lexsort((np.arange(n),own))[:k]; mask=np.zeros(n,dtype=bool); mask[selected]=True
        masks[side] = mask; other_sum=float(other[mask].sum()); negative_count=int(np.sum(own<0))
        tails[side] = {**conditional_losses(mask,own,other), 'k':k,'negative_day_count':negative_count,
            'all_k_negative':bool(np.all(own[selected]<0)),
            'tail_status':'QUALIFIED_FIXED_NEGATIVE_TAIL' if negative_count>=k else 'UNKNOWN_INSUFFICIENT_NEGATIVE_DAYS',
            'other_leg_tail_net_PnL_USDT':other_sum,'other_leg_offset_point_condition':bool(other_sum>=0),
            'other_rounding_sensitive':abs(other_sum)<=RULES['cash_tolerance'],
            'offset_interpretation':'CASH_EQUIVALENT_ZERO_AT_POINT' if other_sum==0 else ('POSITIVE_OTHER_LEG_PNL' if other_sum>0 else 'NEGATIVE_OTHER_LEG_PNL'),
            'UTC_dates':[str(day) for day in p['dates'][selected]],'selection_uses_saved_outcomes_not_a_trading_signal':True}
    expected = np.arange(timestamp(period['start'])+MINUTE,timestamp(period['end_exclusive'])+MINUTE,MINUTE,dtype=np.int64)
    weights={}; active={}
    for side in ('P','H'):
        frame=inventory[side]; require(np.array_equal(frame['close_us'].to_numpy(),expected), 'Complete exact shared minute close calendar')
        values=frame.select(pl.exclude('close_us')).to_numpy(); require(np.isfinite(values).all() and np.all(frame['nav'].to_numpy()>0), 'Finite positive recorded minute NAV')
        weights[side]=frame.select('BTCUSDT_marked_notional','ETHUSDT_marked_notional').to_numpy()/frame['nav'].to_numpy()[:,None]
        require(np.all(weights[side]>=0), 'Actual long-only marked exposures, no silent clipping')
        require(np.allclose(weights[side].sum(axis=1),frame['gross_weight'].to_numpy(),rtol=0,atol=RULES['ratio_tolerance']), 'Recorded gross exposure projection agrees')
        require(np.allclose(frame['nav'].to_numpy()[1439::1440],daily[side]['nav'],rtol=0,atol=RULES['cash_tolerance']), 'UTC date maps to next-day exclusive minute close; accepted daily NAV alignment')
        active[side]=weights[side].sum(axis=1)>0
    wp,wh=weights['P'],weights['H']; gp,gh=wp.sum(axis=1),wh.sum(axis=1)
    weight_denominator=float(np.maximum(wp,wh).sum())
    overlap=dict(strict_positive_including_dust=True,actual_marked_positions_not_targets=True,
        both_active_fraction=float(np.mean(active['P']&active['H'])),
        either_active_fraction=float(np.mean(active['P']|active['H'])),
        active_time_Jaccard=fraction(int(np.sum(active['P']&active['H'])),int(np.sum(active['P']|active['H']))),
        active_indicator_correlation=correlation(active['P'].astype(float),active['H'].astype(float)),
        gross_weight_correlation=correlation(gp,gh),mean_gross_weight_P=float(gp.mean()),mean_gross_weight_H=float(gh.mean()),
        matched_asset_weight_overlap=fraction(float(np.minimum(wp,wh).sum()),weight_denominator),
        weight_overlap_status='DEFINED' if weight_denominator>0 else 'UNKNOWN_ZERO_DENOMINATOR',
        per_asset={symbol:dict(weight_overlap=fraction(float(np.minimum(wp[:,i],wh[:,i]).sum()),float(np.maximum(wp[:,i],wh[:,i]).sum())),
            weight_correlation=correlation(wp[:,i],wh[:,i])) for i,symbol in enumerate(('BTCUSDT','ETHUSDT'))})
    return dict(period=period['id'],days=n,minutes=period['minutes'],
        net_return={s:float(daily[s]['nav'][-1]/INITIAL-1) for s in ('P','H')},
        net_PnL_USDT={s:float(daily[s]['nav'][-1]-INITIAL) for s in ('P','H')},
        saved_costs={s:{key:legs[s]['summary'][key] for key in ('fees','spread_cost','slippage_cost','turnover','trade_count')} for s in ('P','H')},
        daily_PnL_correlation=correlation(dp,dh),daily_net_return_correlation=correlation(p['returns'],h['returns']),
        co_negative_days=int(both.sum()),co_negative_fraction_all_days=float(both.mean()),
        on_P_negative_days=conditional_losses(dp<0,dp,dh),on_H_negative_days=conditional_losses(dh<0,dh,dp),
        both_negative_loss_concentration={s:conditional_losses(both,own,other) for s,own,other in (('P',dp,dh),('H',dh,dp))},
        worst_10_percent_days=tails,worst_tail_intersection_days=int(np.sum(masks['P']&masks['H'])),
        worst_tail_intersection_fraction=fraction(int(np.sum(masks['P']&masks['H'])),k),
        worst_tail_overlap_status='DEFINED' if all(tails[s]['all_k_negative'] for s in ('P','H')) else 'UNKNOWN_INSUFFICIENT_NEGATIVE_DAYS',
        actual_marked_exposure_overlap=overlap,no_ensemble_NAV_or_return_generated=True,summary_scope='DESCRIPTIVE_SAVED_LEDGER_NOT_COMMON_ACCOUNT_OR_APR')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','run-dir','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True); args=parser.parse_args()
    work,out,protocol=args.run_dir.resolve(),args.output.resolve(),args.protocol.resolve(); started=time.monotonic()
    require(work.is_relative_to(STATE) and not work.exists() and out.is_relative_to(ROOT/'reports/fast_research')
        and not out.exists() and protocol.is_relative_to(ROOT/'protocols') and os.environ.get('COIN_TASK_ID'), 'Exclusive new bounded/progress task, STATE and report')
    before=resources.status(); spec,protocol_sha=small(protocol)
    calculation=spec['calculation_rules']
    require(spec['classification']=='SCREENING_SAVED_LEDGER_COMPLEMENTARITY_NOT_ENSEMBLE'
        and all(calculation[k]==RULES[k] for k in ('cash_tolerance','ratio_tolerance','tail_fraction'))
        and calculation['no_ensemble_NAV'] is True and calculation['periods_independent'] is True
        and isinstance(spec['decision_rule'],dict), 'Root-frozen diagnostic scope/constants; adoption is external')
    require(all(spec['budgets'][k]==v for k,v in dict(new_owned_bytes=5_000_000,module_combined_STATE_bytes=5_000_000,
        peak_RSS_bytes=1_000_000_000,wall_seconds=300,additional_market_copy_bytes=0,input_files=12).items()), 'Only fixed5MB/1GB/300s/12file budget')
    require(all(spec['fee_profile'][k]==v for k,v in dict(path=FEE_PATH,sha256=FEE_SHA,market_type='SPOT',
        fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1',fee_bps_per_side=10,half_spread_bps_per_side=4,
        slippage_bps_per_side=4,nominal_roundtrip_bps=36,data_venue='Binance',fee_reference_venue='Bybit',native_market_certified=False).items())
        and Path(sys.prefix).resolve()==Path(spec['environment']['sys_prefix']).resolve()
        and sha(ROOT/spec['environment']['lock_path'])==spec['environment']['lock_sha256']
        and pl.thread_pool_size()<=2, 'Same accepted clean CPU environment and ordinary Bybit fee reference')
    require(out==(ROOT/spec['output_path']).resolve() and work==Path(spec['run_dir']).resolve(), 'Exact frozen exclusive output routing')
    hashes=spec['frozen_sources']; own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    require(own in hashes and PROGRESS_SOURCE in hashes and hashes.get(FEE_PATH)==FEE_SHA, 'Bind actual entrypoint/Progress/fee source')
    for path,digest in hashes.items():
        target=ROOT/path; require(target.resolve().is_relative_to(ROOT) and target.is_file() and target.stat().st_size<2_000_000
            and sha(target)==digest, 'Frozen bounded source changed: '+path)
    snapshot_bytes=sum((ROOT/path).stat().st_size for path in hashes)
    require(snapshot_bytes<=2_000_000, 'Bound original small source snapshot to2MB within shared5MB module')
    require(spec['budgets']['input_bytes']==sum(a['bytes'] for p in spec['periods'] for leg in p['legs'].values() for a in leg['artifacts'].values()), 'Actual metadata input bytes, no price copies')
    Progress,progress_ast,progress_derived_ast=progress_class(hashes[PROGRESS_SOURCE]); work.mkdir()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes=hashes,protocol_sha256=protocol_sha,exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),
        environment_lock_sha256=spec['environment']['lock_sha256'],sys_prefix=sys.prefix,python=sys.executable,
        original_Progress_class_AST_sha256=progress_ast,derived_Progress_class_AST_sha256=progress_derived_ast,
        Progress_literal_changes=dict(total=12,detail='DIAGNOSTIC_ONLY'),source_snapshot_bytes=snapshot_bytes,models_fit=0,orders_sent=0,GPU=0)
    save(work/'RUN_BINDING.json',binding)
    for path in hashes:
        target=work/'source-snapshot'/path; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/path,target)
    event=dict.fromkeys(FIELDS); event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',event_type='OPERATIONAL_START',
        git_commit=binding['git_commit'],data_manifest_hash=hashlib.sha256(json.dumps(spec['periods'],sort_keys=True).encode()).hexdigest(),
        protocol_hash=protocol_sha,feature_set='SAVED_DAILY_NAV_AND_ACTUAL_MARKED_EXPOSURE_ONLY',labels='NONE',model_family='NONE',
        hyperparameters=spec['calculation_rules'],seed='NOT_APPLICABLE_DETERMINISTIC',thresholds=spec['decision_rule'],
        cost_assumptions=spec['fee_profile'],all_folds=spec['periods'],success_failure='START',
        reason_for_next_experiment='Diagnose saved public-pair complementarity before any fixed common-capital ensemble',
        result_influenced_later_choice=False,source_hashes=hashes,exact_command=binding['exact_command'],run_binding_sha256=sha(work/'RUN_BINDING.json'))
    report=dict(status='FAIL_D036_SAVED_LEDGER_DIAGNOSTIC',binding=binding,run_dir=str(work),run_binding_sha256=sha(work/'RUN_BINDING.json'),
        registration_start=append_event(ROOT/'reports/experiment_registry.jsonl',event),cases=[],input_bindings=[],
        calculation_rules=calculation,implemented_calculation_constants=RULES,decision_rule=spec['decision_rule'],resources_before=before,
        candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',native_account_certified=False,
        saved_ledger_arrays_read=False,saved_ledger_array_read_attempts=0,market_arrays_read=False,original_source_QA_repeated=False,old_accounts_replayed=False,
        ensemble_NAV_generated=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    progress=Progress()
    try:
        contexts=accepted_inputs(spec)
        progress.update('真实容量扫描；不造总量',0,None,'扫描')
        report['disk']=dict(scan_started_utc=datetime.now(UTC).isoformat(),**disk.check(spec['budgets']['new_owned_bytes']),scan_finished_utc=datetime.now(UTC).isoformat())
        count=0
        for period,legs in contexts:
            daily={}; inventory={}
            for side in ('P','H'):
                for name in FILES:
                    count+=1; item=legs[side]['artifacts'][name]
                    frame=read_artifact(item,name,progress,count,spec,started,report)
                    report['input_bindings'].append(dict(period=period['id'],side=side,filename=name,**item))
                    if name==FILES[0]: daily[side]=daily_arrays(frame,period,legs[side]['summary'])
                    else: inventory[side]=frame
            progress.update('计算保存损益和实际仓位互补性',len(report['cases']),3,'窗口',period=period['id'])
            report['cases'].append(diagnose(period,legs,daily,inventory)); del frame,daily,inventory; gc.collect()
            guard_runtime(spec,started)
        require(count==12 and len(report['cases'])==3, 'All fixed inputs/windows complete; no partial winner selection')
        require(all(sha(ROOT/path)==digest for path,digest in hashes.items()), 'Frozen small source bytes unchanged')
        report.update(status=STATUS,completed_files=12,completed_periods=3,source_bytes_unchanged=True,
            economic_action='DIAGNOSTIC_EVIDENCE_ONLY_ROOT_PREDECLARED_DECISION_NO_INVESTMENT_ADOPTION')
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error)); raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(p.stat().st_size for p in work.rglob('*') if p.is_file()),resources_after=resources.status())
        if report['owned_bytes']>spec['budgets']['new_owned_bytes']:
            report.update(status='FAIL_D036_SAVED_LEDGER_DIAGNOSTIC',budget_error='STATE owned bytes exceed frozen budget')
        save(out,report)
        append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':args.experiment_id+':RESULT','event_type':'OPERATIONAL_RESULT',
            'success_failure':report['status'],'artifact_path':str(out.relative_to(ROOT)),'artifact_sha256':sha(out)})
        progress.stop.set(); progress.thread.join(timeout=3)
        print(json.dumps(dict(status=report['status'],output=str(out),sha256=sha(out)),ensure_ascii=False))
        if report['status'].startswith('FAIL'): raise RuntimeError('Preserved diagnostic failure: '+report.get('reason',report.get('budget_error','unknown')))

if __name__=='__main__': main()
