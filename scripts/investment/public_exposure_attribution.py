"""D039: read accepted inventory/fills once; describe asset PnL and snapshots.

No account replay, price-source IO, alpha/beta identification or new NAV.
Root freezes all nine selectors before --protocol --run-dir --output
--experiment-id execution. This file is initially prepared, not executed.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, json, math, os, resource, shlex, shutil, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
from scripts.investment import public_pair_diagnostics as base
from scripts.investment import public_pair_diagnostics_v2 as display

require, sha, small, save = base.require, base.sha, base.small, base.save
timestamp, near, guard_runtime = base.timestamp, base.near, base.guard_runtime
ROOT, STATE, MINUTE = base.ROOT, base.STATE, base.MINUTE
BASE_PATH = 'scripts/investment/public_pair_diagnostics.py'
BASE_SHA = '7cac018b7d98b428211b8bee7e6b012df24854b5fa84c7e312b96540da7cce6b'
DISPLAY_PATH = 'scripts/investment/public_pair_diagnostics_v2.py'
DISPLAY_SHA = '3084088ae17a0dc1e2d052663c16ba51fb3a3b5923843e3218bc9eed5fd4c892'
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
STRATEGIES = ('COIN_JESSE_SMA50_200_1D_SPOT_ADAPTER', 'VOL_MANAGED_BUY_AND_HOLD', base.P)
FILES = ('minute_nav_inventory.parquet', 'trades.parquet')
TRADE_COLUMNS = ('execution_us', 'signal_us', 'capacity_open_us', 'target_weight', 'symbol', 'side',
    'quantity', 'mid_price', 'fill_price', 'notional', 'fee', 'execution_cost', 'cash_after', 'nav_after',
    'asset_weight_after', 'gross_weight_after', 'capacity', 'gross_quantity', 'position_delta',
    'cash_delta', 'fee_asset', 'fee_amount', 'fee_USDT_mid')
RULES = dict(cash_tolerance=1e-7, ratio_tolerance=1e-12, material_notional_USDT=10.0,
    above_target_weight=0.3, spread_execution_fraction=0.5, slippage_execution_fraction=0.5,
    gross_formula='SUM_NEG_POSITION_DELTA_TIMES_FILL_MID_PLUS_TERMINAL_MARKED',
    net_formula='GROSS_MINUS_FEE_USDT_MID_MINUS_GROSS_EXECUTION_COST', windows_independent=True,
    snapshot_holding_scope='RECORDED_MINUTE_SNAPSHOTS_NOT_EVENT_HOLDING_DURATION',
    alpha_beta_identified=False, new_account_NAV_generated=False)
BUDGETS = dict(new_owned_bytes=5_000_000, module_combined_STATE_bytes=10_000_000,
    peak_RSS_bytes=1_000_000_000, wall_seconds=600, additional_market_copy_bytes=0, input_files=18, cases=9)
STATUS = 'COMPLETE_D039_SAVED_ASSET_PNL_AND_MINUTE_EXPOSURE_ATTRIBUTION_NOT_ALPHA_BETA_OR_APR'


def activity(mask, stamps):
    """Official Polars run-length kernel; counts do not certify event duration."""
    runs = pl.Series('active', mask, dtype=pl.Boolean).rle()
    lengths = runs.struct.field('len').to_numpy()
    values = runs.struct.field('value').to_numpy()
    longest = int(lengths[values].max()) if np.any(values) else 0
    witness = dict(observed_minutes=longest, minute_occupancy_seconds=longest*60,
        snapshot_span_seconds=max(0, longest-1)*60, first_close_us=None, last_close_us=None,
        right_censored=False, left_censored=False)
    if longest:
        index = int(np.flatnonzero(values & (lengths == longest))[0])
        first = int(lengths[:index].sum()); last = first+longest-1
        witness.update(first_close_us=int(stamps[first]), last_close_us=int(stamps[last]),
            right_censored=last == len(stamps)-1, left_censored=first == 0)
    count = int(np.count_nonzero(mask))
    return dict(observed_minutes=count, minute_occupancy_seconds=count*60,
        full_window_minutes=len(stamps), fraction_full_window=float(count/len(stamps)),
        longest_streak=witness, tie_rule='EARLIEST_LONGEST_RUN', event_holding_duration_certified=False)


def summarize_inventory_trades(inv, trades, summary):
    """Calculate asset contributions from actual NET deltas, never reported PnL."""
    require(set(inv.columns) == set(base.INVENTORY) and inv.schema['close_us'] == pl.Int64
        and inv.height > 0 and sum(inv.null_count().row(0)) == 0, 'Complete original inventory schema/calendar')
    require(set(trades.columns) == set(TRADE_COLUMNS) and sum(trades.null_count().row(0)) == 0,
        'Original 23-column native trade schema, retained even for empty trades')
    require(all(trades.schema[k] == pl.Int64 for k in ('execution_us','signal_us','capacity_open_us'))
        and all(trades.schema[k] == pl.String for k in ('symbol','side','fee_asset'))
        and all(trades.schema[k] == pl.Float64 for k in TRADE_COLUMNS
            if k not in ('execution_us','signal_us','capacity_open_us','symbol','side','fee_asset')),
        'Original integer, string and Float64 native trade columns')
    stamps = inv['close_us'].to_numpy()
    require(np.all(stamps % MINUTE == 0) and np.all(np.diff(stamps) == MINUTE),
        'Exact continuous minute close order; no sorting, dropping or filling')
    require(all(inv.schema[k] == pl.Float64 for k in base.INVENTORY if k != 'close_us'), 'Original Float64 inventory fields')
    require(np.isfinite(inv.select(pl.exclude('close_us')).to_numpy()).all()
        and np.isfinite(trades.select(pl.col(pl.Float64)).to_numpy()).all(), 'Finite saved numerical fields')
    nav = inv['nav'].to_numpy()
    require(np.all(nav > 0), 'Positive recorded NAV for each asset weight denominator')
    require(set(trades['symbol'].unique().to_list()) <= set(SYMBOLS)
        and set(trades['side'].unique().to_list()) <= {'buy','sell'}, 'Only two accepted long Spot assets/sides')
    require(np.all(trades['gross_quantity'].to_numpy() > 0)
        and np.all(trades['mid_price'].to_numpy() > 0)
        and np.all(trades['fee_USDT_mid'].to_numpy() >= 0)
        and np.all(trades['execution_cost'].to_numpy() >= 0), 'Positive fills/mids, nonnegative recorded costs')
    require(np.allclose(trades['gross_quantity'].to_numpy(), trades['quantity'].to_numpy(),
        rtol=0, atol=RULES['ratio_tolerance']), 'Gross trade quantity alias is not net inventory')
    require(np.allclose(trades['fee'].to_numpy(), trades['fee_USDT_mid'].to_numpy(),
        rtol=0, atol=RULES['cash_tolerance']), 'Original fee alias is USDT mid-valued recorded commission')
    weights = []
    result = {}
    for symbol in SYMBOLS:
        rows = trades.filter(pl.col('symbol') == symbol)
        buy = rows.filter(pl.col('side') == 'buy'); sell = rows.filter(pl.col('side') == 'sell')
        require(set(buy['fee_asset'].unique().to_list()) <= {symbol[:-4]}
            and set(sell['fee_asset'].unique().to_list()) <= {'USDT'}, 'Accepted received-asset commission units')
        require(np.all(buy['position_delta'].to_numpy() > 0) and np.all(sell['position_delta'].to_numpy() < 0),
            'Actual received buy position and gross sell position signs')
        qty = inv[symbol+'_quantity'].to_numpy(); marked = inv[symbol+'_marked_notional'].to_numpy()
        require(np.all(qty >= 0) and np.all(marked >= 0) and np.all((qty > 0) == (marked > 0)),
            'Positive marked inventory including dust; no silent clipping')
        weight = marked/nav; weights.append(weight)
        terminal = float(marked[-1])
        # Base fee is already absent from position_delta; its mid-value is
        # deducted once as a recorded cost, never as a second inventory debit.
        gross = math.fsum(-float(delta)*float(mid) for delta,mid
            in zip(rows['position_delta'], rows['mid_price'], strict=True))+terminal
        fee = math.fsum(rows['fee_USDT_mid']); execution = math.fsum(rows['execution_cost'])
        near(math.fsum(rows['position_delta']), qty[-1], RULES['cash_tolerance'])
        near(qty[-1], summary['open_positions'][symbol], RULES['cash_tolerance'])
        result[symbol] = dict(gross_PnL_USDT=gross, net_PnL_USDT=gross-fee-execution,
            fee_USDT_mid=fee, execution_cost_USDT=execution,
            spread_cost_USDT=execution*RULES['spread_execution_fraction'],
            slippage_cost_USDT=execution*RULES['slippage_execution_fraction'],
            buy_base_fee_amount=math.fsum(buy['fee_amount']), buy_base_fee_asset=symbol[:-4],
            sell_quote_fee_amount=math.fsum(sell['fee_amount']), sell_quote_fee_asset='USDT',
            terminal_quantity=float(qty[-1]), terminal_marked_notional_USDT=terminal,
            buy_fills=buy.height, sell_fills=sell.height, mean_marked_weight=float(weight.mean()),
            max_marked_weight=float(weight.max()), above_target_weight_minutes=int(np.sum(weight > .3)),
            material_activity=activity(marked >= RULES['material_notional_USDT'], stamps),
            positive_activity=activity(marked > 0, stamps))
    require(np.allclose(weights[0]+weights[1], inv['gross_weight'].to_numpy(), rtol=0,
        atol=RULES['ratio_tolerance']), 'Recorded two-asset NAV weights reconcile gross snapshot weight')
    fields = ('gross_PnL_USDT','net_PnL_USDT','fee_USDT_mid','execution_cost_USDT',
        'spread_cost_USDT','slippage_cost_USDT','terminal_marked_notional_USDT')
    total = {key:math.fsum(row[key] for row in result.values()) for key in fields}
    mapping = dict(gross_PnL_USDT='gross_cash_PnL_same_quantities',net_PnL_USDT='net_cash_PnL',
        fee_USDT_mid='fees',execution_cost_USDT='execution_costs',spread_cost_USDT='spread_cost',
        slippage_cost_USDT='slippage_cost',terminal_marked_notional_USDT='terminal_marked_notional')
    errors = {}
    for key,saved in mapping.items():
        near(total[key], summary[saved], RULES['cash_tolerance']); errors[key] = abs(total[key]-float(summary[saved]))
    near(float(nav[-1])-summary['initial_nav'], total['net_PnL_USDT'], RULES['cash_tolerance'])
    require(trades.height == summary['trade_count'], 'Exact accepted fill count')
    near(inv['cumulative_fee'][-1], total['fee_USDT_mid'], RULES['cash_tolerance'])
    near(inv['cumulative_execution_cost'][-1], total['execution_cost_USDT'], RULES['cash_tolerance'])
    return dict(per_asset=result, totals=total, summary_bridge_absolute_errors_USDT=errors,
        summary_bridge_tolerance_USDT=RULES['cash_tolerance'], observed_minutes=inv.height,
        first_close_us=int(stamps[0]), last_close_us=int(stamps[-1]),
        snapshot_scope=RULES['snapshot_holding_scope'], alpha_beta_identified=False,
        event_holding_duration_certified=False, new_account_NAV_generated=False)


def progress_class(digest):
    """Reuse repaired initialization-only Progress adaptation; two display literals."""
    require(sha(ROOT/BASE_PATH) == BASE_SHA and sha(ROOT/DISPLAY_PATH) == DISPLAY_SHA,
        'Frozen diagnostic helpers and successful initialization-only display repair')
    nodes = [n for n in ast.parse((ROOT/DISPLAY_PATH).read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == 'progress_class']
    require(len(nodes) == 1, 'One pinned repaired display function')
    changes = []
    for node in ast.walk(nodes[0]):
        if isinstance(node, ast.Constant) and node.value == 12:
            node.value = 18; changes.append('total')
        elif isinstance(node, ast.Constant) and node.value == '已接受公开策略账本互补性诊断；不是新组合账户或APR':
            node.value = '九个已接受账户分币贡献与分钟快照暴露；非alpha/beta或APR'; changes.append('detail')
    require(sorted(changes) == ['detail','total'], 'Only two pinned initializer display values')
    namespace = dict(vars(display)); ast.fix_missing_locations(nodes[0])
    exec(compile(ast.Module(nodes, type_ignores=[]), str(ROOT/DISPLAY_PATH)+'<D039-display-only>', 'exec'), namespace)
    return namespace['progress_class'](digest)


def accepted_cases(spec):
    recon, digest = small(ROOT/spec['recon_path'], spec['recon_sha256'])
    require(recon['status'] == 'READONLY_ACCEPTED_SAVED_LEDGER_METADATA_RECON_NOT_NEW_QA_OR_ECONOMICS'
        and recon['actual_case_count'] == 9 and recon['artifact_files'] == 18, 'Exact root prior metadata recon')
    proofs = {}
    for path,value in recon['small_report_hashes'].items():
        require(spec['frozen_sources'].get(path) == value, 'Freeze every recon prior small proof')
        proofs[path] = small(ROOT/path,value)[0]
    expected = {(fold,strategy) for fold,_,_,_ in base.FIXED_PERIODS for strategy in STRATEGIES}
    cases = recon['cases']; require(len(cases) == 9 and len({c['id'] for c in cases}) == 9
        and {(c['fold'],c['selected_strategy']) for c in cases} == expected, 'All fixed selectors exactly once')
    for case in cases:
        fold,first,end,days = next(p for p in base.FIXED_PERIODS if p[0] == case['fold'])
        require(all(type(case[k]) is int for k in ('start_us','end_us','days'))
            and (case['start_us'],case['end_us'],case['days']) == (timestamp(first),timestamp(end),days)
            and case['initial_nav'] == 10_000. and case['spread_bps'] == 8
            and case['nominal_roundtrip_bps'] == 36, 'Unchanged fixed scoring calendar/capital/cost')
        producer = proofs[case['producer_path']]
        require(spec['frozen_sources'][case['producer_path']] == case['producer_sha256']
            and producer['status'] == case['producer_status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',
            'Previously completed frozen producer only')
        saved_folds = [f for f in producer['folds'] if f['fold'] == fold]
        require(len(saved_folds) == 1 and (saved_folds[0]['start_us'],saved_folds[0]['end_us'],saved_folds[0]['days'])
            == (case['start_us'],case['end_us'],days), 'Exact prior fold source metadata')
        saved_rows = [r for r in saved_folds[0]['results'] if r['strategy'] == case['selected_strategy'] and r['spread_bps'] == 8]
        require(len(saved_rows) == 1 and saved_rows[0]['summary'] == case['summary']
            and saved_rows[0]['directory'] == case['directory'], 'Unmodified prior summary/directory, not calculated PnL input')
        summary = case['summary']
        require(summary['fee_settlement_version'] == 'BYBIT_SPOT_RECEIVED_ASSET_V1'
            and summary['bybit_fee_profile_sha256'] == base.FEE_SHA and summary['derived_AST_SHA256'] == base.FINANCE_AST
            and not summary['candidate_qualification_allowed'], 'Reuse exact accepted received-asset financial identity')
        for name in ('accepted_independent_audit','accepted_root_acceptance'):
            item = case[name]
            require(spec['frozen_sources'].get(item['path']) == item['sha256']
                and proofs[item['path']]['status'] == item['status'], 'Exact prior accepted proof status, no fake old task')
        require(set(case['artifacts']) == set(FILES), 'Only inventory and native trades, no raw prices')
        for name,item in case['artifacts'].items():
            old = saved_rows[0]['artifacts'][name]
            require(item['path'] == str(Path(case['directory'])/name) and item['sha256'] == old['sha256']
                and item['bytes'] == old['bytes'] and item['expected_rows'] == (days*1440 if name == FILES[0] else summary['trade_count']),
                'Exact accepted derivative artifact metadata, no new source QA')
    return cases, digest


def read_artifact(item, name, spec, started, report):
    path = Path(item['path']); resolved = path.resolve()
    require(not path.is_symlink() and resolved.is_relative_to(STATE) and resolved.is_file()
        and resolved.stat().st_size == item['bytes'] and sha(resolved) == item['sha256'], 'Frozen ordinary saved ledger bytes')
    columns = base.INVENTORY if name == FILES[0] else TRADE_COLUMNS
    require(set(pl.read_parquet_schema(resolved)) == set(columns), 'Original exact saved schema before projection')
    report['saved_ledger_array_read_attempts'] += 1
    frame = pl.read_parquet(resolved, columns=columns)
    report['saved_ledger_arrays_read'] = True
    require(frame.height == item['expected_rows'], 'Keep complete accepted rows, including zero-trade schema')
    guard_runtime(spec, started)
    return frame


def state_metadata(path):
    original = Path(path); resolved = original.resolve()
    require(not original.is_symlink() and resolved.is_relative_to(STATE) and resolved.is_file()
        and resolved.stat().st_size < 2_000_000, 'Bounded ordinary STATE task/RUN_BINDING metadata only')
    data = resolved.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def accepted_smoke(spec, protocol, protocol_sha):
    """Read true completed proof; never rerun a test or fabricate a source task."""
    path = ROOT/spec['required_smoke_receipt']; value,digest = small(path)
    hashes = {**spec['frozen_sources'],protocol.relative_to(ROOT).as_posix():protocol_sha}
    binding = value['binding']; task_id = binding['task_id']
    require(value['status'] == 'PASS_D039_NEW_ATTRIBUTION_SYNTHETIC_CASE_NOT_MARKET_RESULT'
        and value['test_exit_code'] == 0 and value['junit_counts'] == dict(tests=1,errors=0,failures=0,skipped=0)
        and value['source_bytes_unchanged'] is True and binding['source_hashes'] == hashes
        and binding['protocol_sha256'] == protocol_sha and binding['data_scope'] == 'SYNTHETIC_ONLY'
        and Path(binding['sys_prefix']).resolve() == Path(spec['environment']['sys_prefix']).resolve()
        and binding['environment_lock_sha256'] == spec['environment']['lock_sha256'], 'Exact new one-case acceptance/source/environment')
    require(type(task_id) is str and len(task_id) == 32 and set(task_id) <= set('0123456789abcdef'), 'Actual synthetic task identifier')
    run = Path(value['run_dir']); run_binding,run_sha = state_metadata(run/'RUN_BINDING.json')
    require(run_binding == binding and run_sha == value['run_binding_sha256'], 'Synthetic RUN_BINDING exact bytes')
    junit = run/'junit.xml'
    require(not junit.is_symlink() and junit.resolve().is_relative_to(STATE) and junit.is_file()
        and junit.stat().st_size < 2_000_000 and sha(junit) == value['junit_sha256'], 'Saved actual JUnit byte binding, no test execution')
    task_path = STATE/'task-progress'/('task-'+task_id+'.json'); task,task_sha = state_metadata(task_path)
    require(task['id'] == task_id and task['status'] == 'completed' and type(task['exit_code']) is int
        and task['exit_code'] == 0, 'Actual case task is terminal completed0 before saved ledger arrays')
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=digest,run_binding_sha256=run_sha,
        junit_sha256=value['junit_sha256'],junit_counts=value['junit_counts'],
        actual_closed0_task=dict(path=str(task_path),sha256=task_sha,task=task))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','run-dir','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True); args = parser.parse_args()
    work,out,protocol = args.run_dir.resolve(),args.output.resolve(),args.protocol.resolve()
    require(work.is_relative_to(STATE) and not work.exists() and out.is_relative_to(ROOT/'reports/fast_research')
        and not out.exists() and protocol.is_relative_to(ROOT/'protocols') and os.environ.get('COIN_TASK_ID'),
        'Exclusive new bounded/progress task and output routing')
    started = time.monotonic(); before = base.resources.status(); spec,protocol_sha = small(protocol)
    work.mkdir(); own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    binding = dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes=spec['frozen_sources'],protocol_sha256=protocol_sha,recon_sha256=spec['recon_sha256'],
        exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),
        python=sys.executable,sys_prefix=sys.prefix,environment_lock_sha256=spec['environment']['lock_sha256'])
    save(work/'RUN_BINDING.json',binding)
    event = dict.fromkeys(base.FIELDS); event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',
        event_type='OPERATIONAL_START',git_commit=binding['git_commit'],data_manifest_hash=spec['recon_sha256'],
        protocol_hash=protocol_sha,feature_set='ACCEPTED_NATIVE_FILL_ASSET_CASH_SHADOW_AND_RECORDED_MINUTE_EXPOSURE',
        labels='NONE',model_family='NONE',hyperparameters=RULES,seed='NOT_APPLICABLE_DETERMINISTIC',thresholds='FIXED_DESCRIPTIVE_NO_STRATEGY_THRESHOLDS',
        cost_assumptions=spec['fee_profile'],all_folds=[p[0] for p in base.FIXED_PERIODS],success_failure='START',
        reason_for_next_experiment='Describe per-asset contributions and actual exposure before selecting a causal risk experiment',
        result_influenced_later_choice=False,source_hashes=spec['frozen_sources'],exact_command=binding['exact_command'],
        run_binding_sha256=sha(work/'RUN_BINDING.json'))
    report = dict(status='FAIL_D039_SAVED_EXPOSURE_ATTRIBUTION',binding=binding,run_dir=str(work),run_binding_sha256=sha(work/'RUN_BINDING.json'),
        registration_start=base.append_event(ROOT/'reports/experiment_registry.jsonl',event),cases=[],input_bindings=[],
        calculation_rules=RULES,resources_before=before,saved_ledger_arrays_read=False,saved_ledger_array_read_attempts=0,
        raw_market_source_arrays_read=False,market_derived_saved_trade_mids_used=True,original_source_QA_repeated=False,
        old_accounts_replayed=False,new_account_NAV_generated=False,alpha_beta_identified=False,
        event_holding_duration_certified=False,models_fit=0,HPO=0,orders_sent=0,GPU=0,locked_consumed=False,
        candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',native_account_certified=False)
    progress = None
    try:
        require(spec['calculation_rules'] == RULES and all(spec['budgets'][k] == v for k,v in BUDGETS.items()), 'Exact frozen attribution rules and budgets')
        require(Path(sys.prefix).resolve() == Path(spec['environment']['sys_prefix']).resolve()
            and sha(ROOT/spec['environment']['lock_path']) == spec['environment']['lock_sha256'] and pl.thread_pool_size() <= 2,
            'Accepted clean CPU environment without dependency changes')
        require(all(spec['fee_profile'][k] == v for k,v in dict(path=base.FEE_PATH,sha256=base.FEE_SHA,market_type='SPOT',
            fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1',fee_bps_per_side=10,half_spread_bps_per_side=4,
            slippage_bps_per_side=4,nominal_roundtrip_bps=36,data_venue='Binance',fee_reference_venue='Bybit',native_market_certified=False).items()),
            'Original proxy venue, received-asset10bp and fixed36bp profile')
        require(out == (ROOT/spec['output_path']).resolve() and work == Path(spec['run_dir']).resolve(), 'Exact protocol routing')
        hashes = spec['frozen_sources']
        require(hashes.get(BASE_PATH) == BASE_SHA and hashes.get(DISPLAY_PATH) == DISPLAY_SHA and own in hashes
            and hashes.get(spec['recon_path']) == spec['recon_sha256'] and base.PROGRESS_SOURCE in hashes, 'Bind current entry/helpers/recon/display')
        require(hashes.get(spec['method_review_path']) == spec['method_review_sha256']
            and hashes.get(spec['synthetic_test_path']) == sha(ROOT/spec['synthetic_test_path'])
            and hashes.get(spec['environment']['lock_path']) == spec['environment']['lock_sha256']
            and hashes.get(base.FEE_PATH) == base.FEE_SHA, 'Bind method review, new case, environment and fee profile')
        for path,digest in hashes.items():
            target = ROOT/path
            require(not target.is_symlink() and target.resolve().is_relative_to(ROOT) and target.is_file()
                and target.stat().st_size < 2_000_000 and sha(target) == digest, 'Frozen small source/proof changed: '+path)
        cases,recon_sha = accepted_cases(spec)
        report['synthetic_acceptance'] = accepted_smoke(spec,protocol,protocol_sha)
        Progress,original_ast,derived_ast = progress_class(hashes[base.PROGRESS_SOURCE])
        report['progress_derivation'] = dict(original_AST_sha256=original_ast,derived_AST_sha256=derived_ast,display_total=18)
        # Small local reproducibility copies only; original ledgers and old
        # reports stay in place and are bound by byte hashes, not copied.
        for path in (own,spec['synthetic_test_path'],spec['recon_path'],protocol.relative_to(ROOT).as_posix()):
            target = work/'source-snapshot'/path; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/path,target)
        progress = Progress(); progress.update('真实容量扫描；不造总量',0,None,'扫描')
        report['disk'] = dict(scan_started_utc=datetime.now(UTC).isoformat(),**base.disk.check(BUDGETS['new_owned_bytes']),scan_finished_utc=datetime.now(UTC).isoformat())
        count = 0
        for case in cases:
            frames = {}
            for name in FILES:
                frames[name] = read_artifact(case['artifacts'][name],name,spec,started,report); count += 1
                report['input_bindings'].append(dict(case_id=case['id'],filename=name,**case['artifacts'][name]))
                progress.update('读取已接受库存与成交',count,18,'文件',case=case['id'])
            inv = frames[FILES[0]]
            require(inv['close_us'][0] == case['start_us']+MINUTE and inv['close_us'][-1] == case['end_us'], 'Complete exact scoring minute endpoint calendar')
            attribution = summarize_inventory_trades(inv,frames[FILES[1]],case['summary'])
            report['cases'].append(dict(id=case['id'],family=case['family'],period=case['period'],fold=case['fold'],
                selected_strategy=case['selected_strategy'],start_us=case['start_us'],end_us=case['end_us'],days=case['days'],
                producer_path=case['producer_path'],producer_sha256=case['producer_sha256'],**attribution))
            progress.update('完成分币归因',len(report['cases']),9,'账户',case=case['id'])
            del inv,frames,attribution; gc.collect(); guard_runtime(spec,started)
        require(count == 18 and len(report['cases']) == 9 and all(sha(ROOT/path) == digest for path,digest in hashes.items()), 'All fixed inputs complete, source bytes unchanged')
        report.update(status=STATUS,completed_files=18,completed_cases=9,completed_periods=3,
            completed_snapshot_minutes=sum(c['observed_minutes'] for c in report['cases']),source_bytes_unchanged=True,
            economic_action='DESCRIPTIVE_CONTRIBUTIONS_AND_EXPOSURE_ONLY_NOT_SIGNAL_OR_RISK_POLICY_ADOPTION')
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error)); raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(p.stat().st_size for p in work.rglob('*') if p.is_file()),resources_after=base.resources.status())
        if report['owned_bytes'] > BUDGETS['new_owned_bytes'] or report['elapsed_seconds'] > BUDGETS['wall_seconds'] or report['peak_RSS_bytes'] > BUDGETS['peak_RSS_bytes']:
            report.update(status='FAIL_D039_SAVED_EXPOSURE_ATTRIBUTION',budget_error='Fixed resource budget exceeded')
        save(out,report)
        base.append_event(ROOT/'reports/experiment_registry.jsonl',{**event,'event_id':args.experiment_id+':RESULT','event_type':'OPERATIONAL_RESULT',
            'success_failure':report['status'],'artifact_path':str(out.relative_to(ROOT)),'artifact_sha256':sha(out)})
        if progress is not None: progress.stop.set(); progress.thread.join(timeout=3)
        print(json.dumps(dict(status=report['status'],output=str(out),sha256=sha(out)),ensure_ascii=False))
        if report['status'].startswith('FAIL'): raise RuntimeError('Preserved attribution failure: '+report.get('reason',report.get('budget_error','unknown')))


if __name__ == '__main__': main()
