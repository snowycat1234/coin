"""Bounded GO-gated observer of four saved original 2021 strategy cases.

Imports execute no historical read or financial code. Aggregation uses saved
minute chunks only; neither cold restore nor a simulator is invoked here.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from itertools import combinations
import hashlib
import json
from pathlib import Path

import gate
import provenance

HERE, ROOT, MODULE, STATE = provenance.HERE, provenance.ROOT, provenance.MODULE, provenance.STATE
CASE_IDS, sha = provenance.CASE_IDS, provenance.sha
MINUTE, DAY, CAPITAL = 60_000_000, 86_400_000_000, 10000.0
FULL_COLD, PARTIAL_COLD = 'PASS_COLD_RESTORE_ZERO_ADVANCE', 'PASS_PARTIAL_COLD_RESTORE_ZERO_ADVANCE'
VOL_FORMULA = 'UTC completed-day NAV simple returns, initial NAV 10000; sample std ddof=1 times sqrt(365)'
PREFIX_SCOPE = 'SAME_COMPLETED_MINUTE_PREFIX_EXCLUDES_POST_MINUTE_HALT_MARK'
ARMS = ('STATIC50', 'SMA200_10PCT', 'EXACTHALF', 'VOL_MATCHED')
TARGET_ARCHIVE_SHA256 = '48fbcdd8881700341dfd8d07c00cf0e6a6ead851658dd8b93f15d00044084494'
SOURCE_INDEX_SHA256 = '13a0d6551deef1e5cc6865ff4487ebf3fed5dd518364e909fb25ab228838eb33'
CALENDAR = (1609459200000000, 1640995200000000)


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_new(path: Path, obj) -> None:
    with path.open('x', encoding='utf-8') as file:
        json.dump(obj, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')


def safe_path(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Absolute/traversing observer locator')
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Observer locator escapes root')
    return path


def integer(value, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError('Invalid observer integer: ' + label)
    return value


def exact_quantity(value) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError('Nonfinite observed inventory')
    return number


def exact_quantity_delta(a, b) -> str:
    """b minus a without decimal-context rounding, including tiny residues."""
    left, right = exact_quantity(a), exact_quantity(b)
    exponent = min(left.as_tuple().exponent, right.as_tuple().exponent, 0)
    highest = max(left.adjusted(), right.adjusted(), 0)
    with localcontext() as context:
        context.prec = max(28, highest - exponent + 2)
        return str(right - left)


def pointer_at(recovery: Path) -> dict:
    pointer = read_json(recovery / 'POINTER.json')
    completed = integer(pointer['completed_minutes'], 'completed minutes')
    rows, paths = 0, set()
    for index, chunk in enumerate(pointer['chunks']):
        count = integer(chunk['rows'], 'chunk rows')
        if count > 1440 or chunk['columns'] != 36 or chunk['path'] in paths:
            raise ValueError('Checkpoint minute metadata/geometry differs')
        if index < len(pointer['chunks']) - 1 and count != 1440:
            raise ValueError('Non-final checkpoint day is incomplete')
        safe_path(recovery, chunk['path'])
        paths.add(chunk['path'])
        rows += count
    if rows != completed:
        raise ValueError('Checkpoint minute count differs')
    return pointer


def execution_components(total) -> dict:
    """Label the frozen 4bp+4bp halves of an existing cost; never charge again."""
    half = total * .5 if total is not None else None
    return {'half_spread_cost_USDT': half,
            'slippage_cost_USDT': total - half if total is not None else None}


def daily_stats(day_nav: list[float]) -> dict:
    """Same numerical formula as the frozen runner, no incomplete day endpoint."""
    import numpy as np
    nav = np.r_[CAPITAL, np.asarray(day_nav, dtype=np.float64)]
    if not np.isfinite(nav).all() or np.any(nav <= 0):
        raise ValueError('Nonpositive/nonfinite daily NAV')
    returns = np.diff(nav) / nav[:-1]
    return {'completed_UTC_days': len(day_nav),
            'annualized_daily_vol': float(returns.std(ddof=1) * np.sqrt(365)) if len(returns) > 1 else None,
            'worst_observed_30_complete_days': float(np.min(nav[30:] / nav[:-30] - 1)) if len(nav) > 30 else None,
            'daily_NAV_raw_SHA256': hashlib.sha256(nav[1:].tobytes()).hexdigest(),
            'formula': VOL_FORMULA,
            'incomplete_UTC_day_excluded_from_daily_returns': True}


def stream_prefix(recovery: Path, minutes: int, weights=None, *, numeric=None, start_us=None) -> dict:
    """SHA/float64-verified chunks, one day at a time; no post-minute halt mark.

    All referenced chunks are verified even beyond the selected prefix. Optional
    full fingerprint validation binds all 36 saved numeric columns and close_us.
    """
    import numpy as np
    pointer = pointer_at(recovery)
    minutes = integer(minutes, 'requested prefix')
    if minutes > pointer['completed_minutes']:
        raise ValueError('Requested common prefix exceeds checkpoint')
    if weights is not None:
        weights = np.asarray(weights)
        if (weights.dtype != np.float64 or weights.ndim != 2 or weights.shape[1] != 5
                or not np.isfinite(weights).all() or len(pointer['chunks']) > len(weights)):
            raise ValueError('Frozen target weight geometry differs')
    if numeric is not None:
        if minutes != pointer['completed_minutes'] or type(start_us) is not int:
            raise ValueError('Numeric fingerprint requires the complete saved horizon and clock')
        if len(numeric.get('columns', [])) != 37:
            raise ValueError('Saved numeric fingerprint geometry differs')
        column_hashes = [hashlib.sha256() for _ in range(37)]
    count, peak, drawdown, last = 0, CAPITAL, 0.0, None
    gross_sum, gross_max, gap_sum, net_sum, net_max = 0.0, None, 0.0, 0.0, None
    raw_hash, day_nav = hashlib.sha256(), []
    cumulative = dict.fromkeys(('fees_USDT', 'execution_cost_USDT', 'funding_USDT', 'gross_fill_turnover_USDT'))
    for day, meta in enumerate(pointer['chunks']):
        path = safe_path(recovery, meta['path'])
        if sha(path) != meta['SHA256']:
            raise ValueError('Saved minute chunk SHA differs')
        with np.load(path, allow_pickle=False) as archive:
            if archive.files != ['minute_chunk']:
                raise ValueError('Checkpoint minute archive schema differs')
            chunk = archive['minute_chunk']
        if chunk.dtype != np.float64 or chunk.shape != (meta['rows'], 36):
            raise ValueError('Saved minute chunk float64 geometry differs')
        if numeric is not None:
            for column in range(36):
                column_hashes[column].update(chunk[:, column].tobytes())
            clocks = start_us + np.arange(day * 1440 + 1, day * 1440 + len(chunk) + 1, dtype=np.int64) * MINUTE
            column_hashes[36].update(clocks.tobytes())
        used = chunk[:max(0, min(len(chunk), minutes - count))]
        if not len(used):
            continue
        if (not np.isfinite(used[:, 0]).all() or np.any(used[:, 0] <= 0)
                or not np.isfinite(used[:, 5:9]).all() or not np.isfinite(used[:, 29:36]).all()
                or np.any(used[:, 34] < 0)):
            raise ValueError('Invalid minute NAV/cost/weights or negative gross exposure')
        raw_hash.update(used.tobytes(order='C'))
        for nav in used[:, 0]:
            last = float(nav)
            peak = max(peak, last)
            drawdown = max(drawdown, 1.0 - last / peak)
        gross_sum += float(used[:, 34].sum())
        maximum = float(used[:, 34].max())
        gross_max = maximum if gross_max is None else max(gross_max, maximum)
        net_sum += float(used[:, 35].sum())
        maximum = float(np.abs(used[:, 35]).max())
        net_max = maximum if net_max is None else max(net_max, maximum)
        if weights is not None:
            gap_sum += float(np.abs(used[:, 29:34] - weights[day]).sum())
        if len(used) == 1440:
            day_nav.append(float(used[-1, 0]))
        for column, key in enumerate(cumulative, start=5):
            cumulative[key] = float(used[-1, column])
        count += len(used)
    if count != minutes:
        raise ValueError('Truncated saved common prefix')
    if numeric is not None:
        names = ('nav', 'free_cash', 'isolated_balance', 'gross_notional', 'net_signed_notional',
                 'cumulative_fees', 'cumulative_execution_costs', 'cumulative_funding', 'cumulative_turnover')
        if tuple(row.get('name') for row in numeric['columns'][:9]) != names or numeric['columns'][-1].get('name') != 'close_us':
            raise ValueError('Saved numeric column order differs')
        for index, row in enumerate(numeric['columns']):
            dtype = '<i8' if index == 36 else '<f8'
            if row.get('rows') != minutes or row.get('dtype') != dtype or row.get('raw_SHA256') != column_hashes[index].hexdigest():
                raise ValueError('All saved numeric minute bits differ: ' + str(row.get('name')))
    cumulative.update(execution_components(cumulative['execution_cost_USDT']))
    return {'common_completed_minutes': count, 'last_completed_minute_NAV_USDT': last,
            'last_completed_minute_marked_PnL_USDT': last - CAPITAL if last is not None else None,
            'max_drawdown_of_completed_minute_prefix': drawdown if count else None,
            'mean_minute_close_gross_weight_of_prefix': gross_sum / count if count else None,
            'max_minute_close_gross_weight_of_prefix': gross_max,
            'mean_actual_signed_net_of_prefix': net_sum / count if count else None,
            'max_actual_abs_signed_net_of_prefix': net_max,
            'mean_l1_target_weight_gap_of_prefix': gap_sum / count if count and weights is not None else None,
            'minute_prefix_raw_SHA256': raw_hash.hexdigest(),
            'chunks_sha_and_geometry_verified': len(pointer['chunks']),
            'all_saved_numeric_bits_verified': numeric is not None,
            'daily_statistics': daily_stats(day_nav),
            'saved_cumulative_at_last_completed_minute': cumulative,
            'excludes_halt_mark_after_last_completed_minute': True, 'financial_advances': 0}


def censoring(summary: dict, required: int, *, official_result: bool) -> dict:
    completed = integer(summary['completed_minutes'], 'completed minutes')
    required = integer(required, 'required minutes', 1)
    if completed > required:
        raise ValueError('Observed horizon exceeds fixed calendar')
    positions = summary.get('positions', {})
    flat = bool(positions) and all(exact_quantity(r.get('decimal_strings', {}).get('quantity', r['quantity'])) == 0 for r in positions.values())
    full = official_result and completed == required
    paid = full and flat and summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and summary.get('terminal_cash_realized') is True
    halted = summary['account_status'] in ('BANKRUPT_HALT', 'LIQUIDATION_REQUIRED_HALT')
    return {'completed_minutes': completed, 'required_minutes': required, 'full_calendar': full,
            'paid_flat': bool(paid), 'exact_terminal_flat': flat,
            'observation_class': 'FULL_PAID_FLAT' if paid else 'FULL_MARKED' if full else 'PARTIAL_HALTED' if halted else 'PARTIAL_CENSORED',
            'official_runner_result_present': official_result,
            'annual_paid_return': summary['net_PnL'] / CAPITAL if paid else None,
            'paid_cash_PnL_USDT': summary['net_PnL'] if paid else None}


def contrast(a: dict, b: dict) -> dict:
    """b minus a; no cash, marked endpoint or full-vol delta across horizons."""
    same_full = bool(a.get('available') and b.get('available') and a['full_calendar'] and b['full_calendar']
                     and a['completed_minutes'] == b['completed_minutes'] and a['required_minutes'] == b['required_minutes'])
    both_paid = bool(same_full and a['paid_flat'] and b['paid_flat'])
    keys = ('marked_PnL_USDT', 'minute_drawdown', 'annual_daily_vol', 'mean_actual_gross', 'max_actual_gross',
            'mean_actual_signed_net', 'max_actual_abs_signed_net', 'mean_l1_target_weight_gap', 'worst_observed_30_complete_days', 'trade_legs', 'halt_count',
            'risk_reduction_signal_count',
            'gross_fill_turnover_USDT', 'fees_USDT', 'execution_cost_USDT', 'half_spread_cost_USDT', 'slippage_cost_USDT', 'funding_USDT', 'terminal_residual_gross_notional_USDT')
    return {'same_full_calendar': same_full, 'both_paid_flat': both_paid,
            'paid_cash_PnL_delta_USDT': b['paid_cash_PnL_USDT'] - a['paid_cash_PnL_USDT'] if both_paid else None,
            'annual_paid_return_delta': b['annual_paid_return'] - a['annual_paid_return'] if both_paid else None,
            'same_full_calendar_observed_deltas': {k: b[k] - a[k] if same_full and a.get(k) is not None and b.get(k) is not None else None for k in keys},
            'unequal_or_partial_horizon_needs_common_prefix': not same_full,
            'marked_full_calendar_delta_is_not_paid_profit': bool(same_full and not both_paid)}


def common_prefix(rows: dict, recoveries: dict, weights: dict, *, start_us: int) -> dict:
    minutes = min(row['completed_minutes'] for row in rows.values())
    paths = {name: stream_prefix(recoveries[name], minutes, weights[name]) for name in rows}
    return {'scope': PREFIX_SCOPE, 'common_completed_minutes': minutes,
            'last_completed_minute_close_us': start_us + minutes * MINUTE if minutes else None,
            'paths': paths, 'daily_vol_label': 'OBSERVED_PREFIX_ANNUALIZED_NOT_FULL_YEAR',
            'annual_paid_return_delta': None, 'paid_cash_PnL_delta_USDT': None, 'no_full_year_or_paid_profit_claim': True}


def prefix_deltas(prefix: dict, a: str, b: str) -> dict:
    left, right = prefix['paths'][a], prefix['paths'][b]
    keys = ('last_completed_minute_marked_PnL_USDT', 'max_drawdown_of_completed_minute_prefix',
            'mean_minute_close_gross_weight_of_prefix', 'max_minute_close_gross_weight_of_prefix',
            'mean_actual_signed_net_of_prefix', 'max_actual_abs_signed_net_of_prefix', 'mean_l1_target_weight_gap_of_prefix')
    return {'b_minus_a': {k: right[k] - left[k] if left[k] is not None and right[k] is not None else None for k in keys},
            'annualized_daily_vol_delta_same_completed_UTC_days': right['daily_statistics']['annualized_daily_vol'] - left['daily_statistics']['annualized_daily_vol']
                if left['daily_statistics']['annualized_daily_vol'] is not None and right['daily_statistics']['annualized_daily_vol'] is not None else None,
            'worst_observed_30_complete_days_delta_same_completed_UTC_days': right['daily_statistics']['worst_observed_30_complete_days'] - left['daily_statistics']['worst_observed_30_complete_days']
                if left['daily_statistics']['worst_observed_30_complete_days'] is not None and right['daily_statistics']['worst_observed_30_complete_days'] is not None else None,
            'saved_cumulative_b_minus_a': {k: right['saved_cumulative_at_last_completed_minute'][k] - value if value is not None and right['saved_cumulative_at_last_completed_minute'][k] is not None else None
                                         for k, value in left['saved_cumulative_at_last_completed_minute'].items()}}


def verify_audit_stage(audit: dict, *, manifest_sha: str, terminal_inputs_sha: str, run_binding_sha: str, controller_sha: str, state_locator: str) -> None:
    if (audit.get('stage') != 'AUDIT' or audit.get('status') != 'ALL_OBSERVERS_FINISHED' or audit.get('case_ids') != list(CASE_IDS)
            or set(audit.get('per_observer', {})) != set(CASE_IDS) or audit.get('unstarted_observer_ids') != []
            or audit.get('financial_advances') != 0 or audit.get('historical_wallets_opened') != 0 or audit.get('observer_manifest_SHA256') != manifest_sha):
        raise ValueError('Successful full-population bounded AUDIT receipt missing')
    original_go = audit.get('postrun_GO_text')
    if not isinstance(original_go, str) or hashlib.sha256(original_go.encode()).hexdigest() != audit.get('postrun_GO_SHA256'):
        raise ValueError('Original AUDIT GO exact bytes/hash missing')
    go = json.loads(original_go)
    if (go.get('parent_GO') is not True or 'AUDIT' not in go.get('approved_stages', []) or not set(go.get('approved_stages', [])) <= {'AUDIT', 'REPORT'}
            or go.get('manifest_SHA256') != manifest_sha or go.get('terminal_inputs_SHA256') != terminal_inputs_sha or go.get('state_locator') != state_locator
            or go.get('run_binding_SHA256') != run_binding_sha or go.get('controller_receipt_SHA256') != controller_sha
            or go.get('historical_controller_released') is not True):
        raise ValueError('Original AUDIT GO does not authorize these frozen inputs')


def verify_receipt(case_id: str, receipt: dict, audit: dict) -> None:
    path = HERE / 'receipts' / (case_id + '.json')
    worker = audit['per_observer'][case_id]
    if (receipt.get('case_id') != case_id or receipt.get('financial_advances') != 0
            or receipt.get('historical_wallets_opened') != 0 or receipt.get('controls_rerun') != 0
            or receipt.get('observer_manifest_SHA256') != audit['observer_manifest_SHA256']
            or receipt.get('postrun_GO_SHA256') != audit['postrun_GO_SHA256'] or worker.get('cold_receipt_SHA256') != sha(path)):
        raise ValueError('Cold receipt identity/zero-advance/reviewed-byte verdict differs')
    files = receipt.get('input_files_SHA256')
    if not isinstance(files, dict):
        raise ValueError('Cold receipt pinned input-file map missing')
    for locator, digest in files.items():
        if sha(safe_path(ROOT, locator)) != digest:
            raise ValueError('Post-cold-audit file drift: ' + locator)
    for name in ('RUN_BINDING.json', 'RESOURCE_RECEIPTS.json'):
        source = STATE / name
        if files.get(str(source.relative_to(ROOT))) != sha(source):
            raise ValueError('Required cold run/controller pin missing')
    if receipt.get('status') not in (FULL_COLD, PARTIAL_COLD):
        if receipt.get('status') not in ('UNSTARTED_NO_WALLET', 'STARTED_NO_RECOVERABLE_CHECKPOINT') or receipt.get('observed_summary') is not None:
            raise ValueError('Cold receipt is neither restored nor explicitly unavailable')
        if {k: v for k, v in worker.items() if k != 'cold_receipt_SHA256'} != receipt:
            raise ValueError('Unavailable receipt differs from exact AUDIT record')
        return
    if (worker.get('exit_code') != 0 or worker.get('stop_reason') is not None or type(worker.get('sampled_peak_RSS')) is not int
            or not 0 <= worker['sampled_peak_RSS'] <= 2_000_000_000 or worker.get('RSS_ceiling_bytes') != 2_000_000_000
            or receipt.get('runner_SHA256') != sha(MODULE / 'run_cases.py')
            or receipt.get('fine_account_SHA256') != sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py')
            or any(receipt.get(k) is not True for k in ('all_snapshot_state_equal', 'all_journals_equal', 'all_targets_equal'))):
        raise ValueError('Cold receipt lacks successful bounded code/state/journal evidence')
    state = STATE / case_id
    pointer = pointer_at(state / 'recovery')
    if receipt.get('state_hash') != pointer['state_hash'] or receipt['observed_summary']['completed_minutes'] != pointer['completed_minutes']:
        raise ValueError('Cold restored checkpoint state/horizon differs')
    mandatory = [state / 'BINDING.json', state / 'recovery/POINTER.json', safe_path(state / 'recovery', pointer['snapshot_path'])]
    for name in ('RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv'):
        if (state / name).exists():
            mandatory.append(state / name)
    mandatory += [safe_path(state / 'recovery', c['path']) for c in pointer['chunks']]
    for source in mandatory:
        if files.get(str(source.relative_to(ROOT))) != sha(source):
            raise ValueError('Required cold input pin missing: ' + str(source.relative_to(ROOT)))
    if sha(safe_path(state / 'recovery', pointer['snapshot_path'])) != pointer['snapshot_SHA256']:
        raise ValueError('Checkpoint snapshot SHA differs')
    accepted = (state / 'RESULT.json').exists()
    if (receipt['status'] == FULL_COLD) != accepted:
        raise ValueError('Cold finished/partial status differs from official result presence')
    if accepted and receipt.get('all_numeric_minute_bytes_equal_to_saved_result') is not True:
        raise ValueError('Accepted cold receipt numeric equality missing')


def load_weights(case: dict):
    import numpy as np
    path = safe_path(ROOT, case['target_archive_local_locator'])
    if sha(path) != case['target_archive_SHA256']:
        raise ValueError('Frozen target archive SHA differs')
    with np.load(path, allow_pickle=False) as archive:
        weights = archive[case['arm']].copy()
        clocks = archive['decision_us'].copy()
        symbols = archive['symbol_order'].copy()
    if (weights.dtype != np.float64 or list(weights.shape) != case['target_shape'] or not np.isfinite(weights).all()
            or hashlib.sha256(weights.tobytes(order='C')).hexdigest() != case['target_array_SHA256']
            or clocks.dtype != np.int64 or not np.array_equal(clocks, np.arange(*case['calendar'], DAY))
            or list(symbols) != case['symbols']):
        raise ValueError('Frozen target/calendar numerical identity differs')
    return weights


def validate_four_arm_plan(plan: dict) -> list[dict]:
    cases = plan.get('cases', [])
    if (plan.get('case_count') != 4 or tuple(c.get('arm') for c in cases) != ARMS
            or tuple(c.get('case_id', '') + '_FINE_ORIGINAL' for c in cases) != tuple(CASE_IDS)):
        raise ValueError('Expected exactly the ordered four original 2021 cases')
    for case in cases:
        if (case.get('case_id') != 'Y2021_' + case['arm'] or case.get('year') != 2021
                or tuple(case.get('calendar', [])) != CALENDAR or case.get('target_shape') != [365, 5]
                or case.get('target_dtype') != '<f8' or len(case.get('symbols', [])) != 5
                or case.get('source_index_SHA256') != SOURCE_INDEX_SHA256
                or case.get('target_archive_SHA256') != TARGET_ARCHIVE_SHA256
                or case.get('protective_enabled') is not False):
            raise ValueError('Fixed 2021 target/source/calendar identity differs')
    paired = ('calendar', 'symbols', 'source_index_SHA256', 'source_index_local_locator',
              'target_archive_SHA256', 'target_archive_local_locator')
    if any(case[key] != cases[0][key] for case in cases[1:] for key in paired):
        raise ValueError('Four-arm calendar/source/archive population differs')
    return cases


def observed_row(case: dict, identity: str, summary: dict, result: dict | None, metrics: dict, *, quantities, rejections, journals, bridge) -> dict:
    required = (case['calendar'][1] - case['calendar'][0]) // MINUTE
    row = {'case_id': identity, 'available': True, **censoring(summary, required, official_result=result is not None),
           'marked_PnL_USDT': summary['net_PnL'], 'completion': summary['completion'], 'account_status': summary['account_status'],
           'stop_us': summary.get('stop_us'), 'observed_clock_us': summary.get('clock_us'),
           'minute_drawdown': summary['all_observation_max_drawdown'], 'halt_witness': summary.get('halt_witness'),
           'minute_drawdown_scope': 'ALL_SAVED_OBSERVATIONS_INCLUDES_POST_MINUTE_HALT_MARK_IF_PRESENT',
           'halt_count': int(summary['account_status'] in ('BANKRUPT_HALT', 'LIQUIDATION_REQUIRED_HALT')),
           'annual_daily_vol': metrics['daily_statistics']['annualized_daily_vol'] if result is not None and summary['completed_minutes'] == required else None,
           'observed_prefix_daily_vol_annualized': metrics['daily_statistics']['annualized_daily_vol'],
           'daily_vol_scope': 'FULL_CALENDAR' if result is not None and summary['completed_minutes'] == required else 'OBSERVED_PREFIX_ANNUALIZED_NOT_FULL_YEAR',
           'worst_observed_30_complete_days': metrics['daily_statistics']['worst_observed_30_complete_days'],
           'mean_actual_gross': metrics['mean_minute_close_gross_weight_of_prefix'], 'max_actual_gross': metrics['max_minute_close_gross_weight_of_prefix'],
           'mean_actual_signed_net': metrics['mean_actual_signed_net_of_prefix'], 'max_actual_abs_signed_net': metrics['max_actual_abs_signed_net_of_prefix'],
           'mean_l1_target_weight_gap': metrics['mean_l1_target_weight_gap_of_prefix'],
           'terminal_residual_quantity': quantities, 'terminal_residual_signed_marked_notional_USDT': summary.get('terminal_signed_marked_notional'),
           'terminal_residual_gross_notional_USDT': summary.get('terminal_marked_notional'), 'rejection_counts': rejections,
           'observed_journal_counts': journals, 'independent_decimal_NAV_bridge': bridge, 'completed_minute_prefix_metrics': metrics}
    for key in ('trade_legs', 'gross_fill_turnover_USDT', 'fees_USDT', 'execution_cost_USDT', 'funding_USDT', 'risk_reduction_signal_count', 'pending_orders_at_stop'):
        row[key] = summary.get(key)
    row.update(execution_components(row['execution_cost_USDT']))
    row['execution_cost_components_basis'] = 'PURE_ARITHMETIC_FIXED_BASE27_HALF_SPREAD_4BP_SLIPPAGE_4BP_ALREADY_INCLUDED_NO_ADDITIONAL_CHARGE'
    if quantities is None or set(quantities) != set(case['symbols']):
        raise ValueError('Exact terminal inventory population missing')
    if any(exact_quantity(quantities[s]) != exact_quantity(summary['positions'][s].get('decimal_strings', {}).get('quantity', summary['positions'][s]['quantity'])) for s in case['symbols']):
        raise ValueError('Exact terminal inventory differs from observed account')
    if result is not None:
        checks = ('completed_minutes', 'required_minutes', 'full_calendar', 'paid_flat', 'paid_cash_PnL_USDT', 'marked_PnL_USDT', 'completion', 'account_status', 'minute_drawdown', 'trade_legs')
        if result.get('case_id') != identity or any(result.get(k) != row[k] for k in checks):
            raise ValueError('Saved result/account/cold observation classification differs')
        for key in ('mean_actual_gross', 'max_actual_gross', 'mean_actual_signed_net', 'max_actual_abs_signed_net', 'annual_daily_vol'):
            if key in result and (result[key] is None) != (row[key] is None):
                raise ValueError('Saved result daily/gross metric availability differs')
            if key in result and result[key] is not None and abs(result[key] - row[key]) > 1e-12:
                raise ValueError('Saved result daily/gross metric differs')
    return row


def new_case(case: dict, receipt: dict, weights) -> tuple[dict, Path | None]:
    identity, state = case['case_id'] + '_FINE_ORIGINAL', STATE / (case['case_id'] + '_FINE_ORIGINAL')
    if receipt['status'] not in (FULL_COLD, PARTIAL_COLD):
        return {'case_id': identity, 'available': False, 'observation_class': 'UNAVAILABLE', 'reason': receipt['status'],
                'full_calendar': False, 'paid_flat': False, 'annual_paid_return': None, 'paid_cash_PnL_USDT': None,
                'input_files_SHA256': receipt['input_files_SHA256'],
                'cold_receipt_SHA256': sha(HERE / 'receipts' / (identity + '.json'))}, None
    result = read_json(state / 'RESULT.json') if (state / 'RESULT.json').exists() else None
    summary = receipt['observed_summary']
    if result is not None and read_json(state / 'ACCOUNT.json')['summary'] != summary:
        raise ValueError('Cold receipt/account summary differs')
    numeric = read_json(state / 'MINUTE_NUMERIC.json') if result is not None else None
    metrics = stream_prefix(state / 'recovery', summary['completed_minutes'], weights, numeric=numeric, start_us=case['calendar'][0])
    row = observed_row(case, identity, summary, result, metrics, quantities=receipt.get('observed_terminal_residual_quantity'),
                       rejections=receipt.get('observed_rejection_counts'), journals=receipt.get('observed_journal_counts'), bridge=receipt.get('independent_decimal_NAV_bridge'))
    row.update(input_files_SHA256=receipt['input_files_SHA256'], cold_receipt_SHA256=sha(HERE / 'receipts' / (identity + '.json')))
    if result is not None and result.get('worst_observed_30_days') != row['worst_observed_30_complete_days']:
        raise ValueError('Saved result worst 30-complete-day return differs')
    return row, state / 'recovery'


def target_description(weights) -> dict:
    """Statistics of a frozen schedule, independent of executed wallet horizon."""
    import numpy as np
    weights = np.asarray(weights)
    if (weights.dtype != np.float64 or weights.ndim != 2 or weights.shape[1] != 5
            or len(weights) == 0 or not np.isfinite(weights).all()):
        raise ValueError('Target description requires finite float64 five-symbol schedule')
    gross = np.abs(weights).sum(axis=1)
    active = np.count_nonzero(weights, axis=1)
    return {'days': len(weights), 'cash_days': int(np.count_nonzero(gross == 0)),
            'mean_target_gross': float(gross.mean()), 'max_target_gross': float(gross.max()),
            'mean_signed_target_net': float(weights.sum(axis=1).mean()),
            'max_abs_signed_target_net': float(np.abs(weights.sum(axis=1)).max()),
            'max_abs_target_asset_weight': float(np.abs(weights).max()),
            'active_symbol_day_cells': int(np.count_nonzero(weights)),
            'days_by_nonzero_target_symbol_count': {str(k): int(np.count_nonzero(active == k)) for k in range(6)},
            'last_decision_target_gross': float(gross[-1]),
            'scope': 'ALL_365_FROZEN_DECISIONS_NOT_ACTUAL_EXPOSURE',
            'target_gross_is_not_actual_gross_or_realized_risk': True}


def original_dynamic_context(case: dict, weights: dict) -> dict:
    """Verify, then describe original warm-up masks; never fit or re-size."""
    import numpy as np
    path = safe_path(ROOT, case['target_archive_local_locator'])
    if sha(path) != case['target_archive_SHA256']:
        raise ValueError('Frozen original mask archive SHA differs')
    with np.load(path, allow_pickle=False) as archive:
        mask = archive['SMA_mask'].copy()
        hold_mask = archive['HOLD_mask'].copy()
    expected_counts = np.r_[np.full(25, 3), np.full(66, 4), np.full(274, 5)]
    static, sma, half, vol = (weights[arm] for arm in ARMS)
    if (mask.dtype != np.bool_ or mask.shape != (365, 5) or not np.array_equal(mask, hold_mask)
            or not np.array_equal(mask.sum(axis=1), expected_counts) or np.any(sma[~mask] != 0)
            or not np.array_equal(half, .5 * static + .5 * sma)
            or np.any(static[:91] != 0) or np.any(np.abs(static[91:]).sum(axis=1) == 0)
            or not np.array_equal(half[:91], .5 * sma[:91]) or np.any(vol[:91] != 0)):
        raise ValueError('Original 2021 dynamic masks/cash/half arithmetic differ')
    return {'decisions': 365, 'all_calendar_rows_retained': True,
            'STATIC50_initial_cash_decisions': 91,
            'STATIC50_initial_cash_decision_interval_UTC': ['2021-01-01', '2021-04-01'],
            'SMA200_10PCT_original_eligible_asset_phases': [{'days': 25, 'assets': 3}, {'days': 66, 'assets': 4}, {'days': 274, 'assets': 5}],
            'SMA200_10PCT_mask_counts_by_symbol': dict(zip(case['symbols'], (int(v) for v in mask.sum(axis=0)))),
            'EXACTHALF_bit_exact_half_STATIC50_plus_half_SMA200_10PCT': True,
            'EXACTHALF_first_91_decisions_bit_exact_half_SMA200_10PCT': True,
            'no_final_forced_cash_target': True,
            'one_shared_one_way_wallet_per_arm': True,
            'new_fits_or_target_recomputation_by_observer': 0,
            'no_all_five_warmup_drop_or_end_of_year_cash_override': True}


def matched_volatility(a: dict, b: dict, prefix: dict | None) -> dict:
    if prefix is not None:
        left = prefix['paths']['a']['daily_statistics']['annualized_daily_vol']
        right = prefix['paths']['b']['daily_statistics']['annualized_daily_vol']
        scope = 'OBSERVED_PREFIX_ANNUALIZED_NOT_FULL_YEAR'
    elif contrast(a, b)['same_full_calendar']:
        left, right, scope = a.get('annual_daily_vol'), b.get('annual_daily_vol'), 'SAME_FULL_CALENDAR'
    else:
        left, right, scope = None, None, 'UNAVAILABLE_NO_MATCHED_HORIZON'
    delta = right - left if left is not None and right is not None else None
    return {'scope': scope, 'a_daily_vol_annualized': left, 'b_daily_vol_annualized': right,
            'b_minus_a_daily_vol_annualized': delta,
            'b_daily_vol_lower_than_a': delta < 0 if delta is not None else None}


def pair_comparison(a, b, ar, br, aw, bw, *, start_us):
    comparison = contrast(a, b)
    if comparison['unequal_or_partial_horizon_needs_common_prefix'] and ar is not None and br is not None:
        prefix = common_prefix({'a': a, 'b': b}, {'a': ar, 'b': br}, {'a': aw, 'b': bw}, start_us=start_us)
        prefix.update(a_case_id=a['case_id'], b_case_id=b['case_id'], **prefix_deltas(prefix, 'a', 'b'))
        comparison['common_observed_minute_prefix'] = prefix
    else:
        comparison['common_observed_minute_prefix'] = None
    comparison['matched_daily_volatility'] = matched_volatility(a, b, comparison['common_observed_minute_prefix'])
    return comparison


def all_pairwise_comparisons(rows: dict, recoveries: dict, weights: dict, *, start_us: int) -> dict:
    if set(rows) != set(ARMS) or set(recoveries) != set(ARMS) or set(weights) != set(ARMS):
        raise ValueError('Pairwise comparison must retain all four arms')
    comparisons = {}
    for a, b in combinations(ARMS, 2):
        comparison = pair_comparison(rows[a], rows[b], recoveries[a], recoveries[b], weights[a], weights[b], start_us=start_us)
        comparison.update(a_arm=a, b_arm=b, a_case_id=rows[a]['case_id'], b_case_id=rows[b]['case_id'], direction='b_minus_a')
        comparison['full_schedule_target_b_minus_a'] = {key: rows[b]['frozen_target_descriptive_statistics'][key] - rows[a]['frozen_target_descriptive_statistics'][key]
            for key in ('mean_target_gross', 'max_target_gross', 'mean_signed_target_net', 'max_abs_signed_target_net', 'active_symbol_day_cells', 'cash_days')}
        comparison['full_schedule_target_delta_is_not_actual_exposure_delta'] = True
        same_full = comparison['same_full_calendar']
        left_counts, right_counts = rows[a].get('rejection_counts'), rows[b].get('rejection_counts')
        comparison['same_full_calendar_rejection_count_b_minus_a'] = {key: right_counts.get(key, 0) - left_counts.get(key, 0) for key in sorted(set(left_counts) | set(right_counts))} if same_full and left_counts is not None and right_counts is not None else None
        left_q, right_q = rows[a].get('terminal_residual_quantity'), rows[b].get('terminal_residual_quantity')
        comparison['same_full_calendar_exact_terminal_quantity_b_minus_a'] = {key: exact_quantity_delta(left_q[key], right_q[key]) for key in sorted(left_q)} if same_full and left_q is not None and right_q is not None and set(left_q) == set(right_q) else None
        comparisons[b + '_minus_' + a] = comparison
    return comparisons


def render_summary(report: dict) -> str:
    def number(value, percent=False):
        return 'null' if value is None else f'{value * 100:.6f}%' if percent else f'{value:.6f}'
    def mapping(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'))
    year = report['years'][0]
    lines = ['# Fixed four-arm original 2021 strategy comparison', '',
             'All four original 2021 fine-grid cases are retained, including economic halts and unavailable cases. Report creates zero wallets, advances zero financial steps and reruns zero controls.', '',
             'Each arm uses its own independent 10,000 USDT one-way wallet. All rows come from one authorized run state; no reused comparator wallets.', '',
             '| Arm | Class | Minutes | Marked PnL USDT | Paid PnL USDT | Minute DD | Full daily vol | Observed daily vol | Worst 30 complete days |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for arm in ARMS:
        row = year['arms'][arm]
        if not row['available']:
            lines.append(f"| {arm} | UNAVAILABLE: {row['reason']} | null | null | null | null | null | null | null |")
            continue
        lines.append(f"| {arm} | {row['observation_class']} | {row['completed_minutes']}/{row['required_minutes']} | {number(row['marked_PnL_USDT'])} | {number(row['paid_cash_PnL_USDT'])} | {number(row['minute_drawdown'], True)} | {number(row['annual_daily_vol'], True)} | {number(row['observed_prefix_daily_vol_annualized'], True)} | {number(row['worst_observed_30_complete_days'], True)} |")
    lines += ['', '| Arm | Mean/max target gross | Mean/max actual gross | Mean actual signed net/max absolute | Mean L1 target gap | Turnover USDT | Fees USDT | Execution cost USDT | Funding USDT | Trade legs |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for arm in ARMS:
        row = year['arms'][arm]
        target = row['frozen_target_descriptive_statistics']
        target_gross = number(target['mean_target_gross']) + '/' + number(target['max_target_gross'])
        if not row['available']:
            lines.append(f"| {arm} | {target_gross} | null | null | null | null | null | null | null | null |")
            continue
        lines.append(f"| {arm} | {target_gross} | {number(row['mean_actual_gross'])}/{number(row['max_actual_gross'])} | {number(row['mean_actual_signed_net'])}/{number(row['max_actual_abs_signed_net'])} | {number(row['mean_l1_target_weight_gap'])} | {number(row['gross_fill_turnover_USDT'])} | {number(row['fees_USDT'])} | {number(row['execution_cost_USDT'])} | {number(row['funding_USDT'])} | {row['trade_legs']} |")
    lines += ['', 'Target statistics use all 365 frozen decisions. Actual exposure statistics use the observed completed-minute horizon. Neither equates target gross with actual gross or realized risk.', '', '## Saved account details', '']
    for arm in ARMS:
        row = year['arms'][arm]
        if not row['available']:
            lines.append(arm + ': unavailable, ' + row['reason'] + '. No observed PnL, costs, exposure or paid-return claim.')
            continue
        lines.append(arm + ': account ' + row['account_status'] + '; completion ' + row['completion']
                     + '; halts ' + str(row['halt_count']) + '; stop_us ' + str(row['stop_us'])
                     + '; exact flat ' + str(row['exact_terminal_flat']).lower()
                     + '; residual gross USDT ' + number(row['terminal_residual_gross_notional_USDT'])
                     + '; residual signed marked USDT ' + number(row['terminal_residual_signed_marked_notional_USDT']) + '.')
        lines.append('Exact terminal quantities ' + mapping(row['terminal_residual_quantity'])
                     + '; rejections ' + mapping(row['rejection_counts'])
                     + '; journals ' + mapping(row['observed_journal_counts']) + '.')
        lines.append('Existing execution-cost components: half-spread ' + number(row['half_spread_cost_USDT'])
                     + ' USDT; slippage ' + number(row['slippage_cost_USDT']) + ' USDT. No additional charge.')
        if row['halt_count']:
            lines.append('Halt witness ' + mapping(row['halt_witness']) + '. The marked halt endpoint is separate from the last completed-minute prefix.')
    lines += ['', '## All six pairwise contrasts', '', 'Every contrast is b minus a. Paid cash and annual paid-return deltas require both complete paid-flat wallets on the same full calendar.', '']
    for name, comparison in year['comparisons'].items():
        lines.append(name + ': paid cash delta ' + number(comparison['paid_cash_PnL_delta_USDT'])
                     + ' USDT; annual paid-return delta ' + number(comparison['annual_paid_return_delta'], True)
                     + '; same-full-calendar marked delta ' + number(comparison['same_full_calendar_observed_deltas']['marked_PnL_USDT']) + ' USDT.')
        lines.append('Full frozen schedule target deltas ' + mapping(comparison['full_schedule_target_b_minus_a']) + '. These are descriptive target deltas, independent of actual wallet horizons.')
        if comparison['same_full_calendar']:
            lines.append('Same-full-calendar observed deltas ' + mapping(comparison['same_full_calendar_observed_deltas']) + '.')
            lines.append('Same-full-calendar rejection-count deltas ' + mapping(comparison['same_full_calendar_rejection_count_b_minus_a']) + '; exact terminal quantity deltas ' + mapping(comparison['same_full_calendar_exact_terminal_quantity_b_minus_a']) + '.')
        prefix = comparison['common_observed_minute_prefix']
        if prefix is not None:
            p = prefix['paths']
            lines.append(f"Common completed-minute prefix {prefix['common_completed_minutes']} (close_us={prefix['last_completed_minute_close_us']}), excluding post-minute halt mark: a marked {number(p['a']['last_completed_minute_marked_PnL_USDT'])}, b marked {number(p['b']['last_completed_minute_marked_PnL_USDT'])}, b-a {number(prefix['b_minus_a']['last_completed_minute_marked_PnL_USDT'])} USDT. No annual paid return or cross-horizon endpoint delta.")
            lines.append('Matched-prefix observed deltas ' + mapping(prefix['b_minus_a'])
                         + '; matched completed-UTC-day volatility delta ' + number(prefix['annualized_daily_vol_delta_same_completed_UTC_days'], True)
                         + '; matched worst-30-complete-day return delta ' + number(prefix['worst_observed_30_complete_days_delta_same_completed_UTC_days'], True)
                         + '; saved cumulative costs/turnover deltas ' + mapping(prefix['saved_cumulative_b_minus_a']) + '.')
        elif comparison['unequal_or_partial_horizon_needs_common_prefix']:
            lines.append('Common prefix unavailable because at least one arm has no recoverable checkpoint. No cross-horizon endpoint, volatility or paid delta.')
        volatility = comparison['matched_daily_volatility']
        lines.append('Matched daily volatility scope ' + volatility['scope'] + ': a/b '
                     + number(volatility['a_daily_vol_annualized'], True) + '/' + number(volatility['b_daily_vol_annualized'], True)
                     + '; b-a ' + number(volatility['b_minus_a_daily_vol_annualized'], True) + '.')
        lines.append('')
    four = year['four_way_common_observed_prefix']
    if four is not None:
        lines += ['Four-way common completed-minute prefix: ' + str(four['common_completed_minutes']) + '. It excludes post-minute halt marks and contains no full-year or paid-profit claim.', '']
    lines += ['## Original target admission and interpretation', '',
              'STATIC50 keeps its first 91 daily decisions, January 1 through April 1, in cash. SMA200_10PCT retains original masks: 25 days with 3 eligible assets, 66 days with 4, and 274 days with 5. EXACTHALF is the bit-exact half-STATIC50 plus half-SMA schedule; its first 91 decisions are half-SMA. All 365 decisions remain, with no final forced-cash target.',
              VOL_FORMULA + '. Observed-prefix volatility uses complete UTC days only and is not a full-year estimate. Worst 30-day returns use 30 complete UTC days, excluding incomplete days.',
              'Small or economically material exact terminal residue remains marked-only unless the complete account is exactly flat and terminal cash is realized. No free terminal flattening.',
              'Funding retains the raw-fraction interpretation and unchanged signed economics of the frozen run. Funding units and source provenance remain conditional.',
              'Seen development replication only. This is not OOS evidence, native quantity-resolution certification, venue-validated fills, alpha or promised APR. All prior strategy STOP statuses remain.',
              'Half-spread and slippage split the existing execution cost equally under the unchanged BASE27 4bp+4bp assumption; this is arithmetic attribution, not additional charging.',
              'Binance observations, derived-mark overlay and assumed Bybit costs/fine grid retain their existing qualifications.', '']
    return '\n'.join(lines)


def write_outputs(report: dict) -> None:
    paths = (HERE / 'RESULTS_COMPACT.json', HERE / 'SUMMARY.md')
    if any(path.exists() for path in paths):
        raise FileExistsError('Observer outputs already exist; no overwrite permitted')
    summary = render_summary(report)
    save_new(paths[0], report)
    with paths[1].open('x', encoding='utf-8') as file:
        file.write(summary)


def main() -> None:
    gate.require_bounded_worker('REPORT')
    gate.verify_observer_go('REPORT')
    plan = read_json(MODULE / 'CASE_BINDINGS.json')
    ids = provenance.verify_terminal_run(state=STATE, module=MODULE, plan=plan)
    cases = validate_four_arm_plan(plan)
    if tuple(ids) != tuple(CASE_IDS) or len(ids) != 4:
        raise ValueError('Terminal run differs from fixed ordered four-case population')
    audit = read_json(HERE / 'AUDIT_RESOURCE_RECEIPTS.json')
    verify_audit_stage(audit, manifest_sha=sha(HERE / 'REVIEWED_POSTRUN_CODE.json'), terminal_inputs_sha=sha(HERE / 'TERMINAL_INPUTS.json'), run_binding_sha=sha(STATE / 'RUN_BINDING.json'),
                       controller_sha=sha(STATE / 'RESOURCE_RECEIPTS.json'), state_locator=str(STATE.relative_to(ROOT)))
    if {p.stem for p in (HERE / 'receipts').glob('*.json')} != set(CASE_IDS):
        raise ValueError('Cold receipt population differs from exactly four planned cases')
    receipts = {identity: read_json(HERE / 'receipts' / (identity + '.json')) for identity in CASE_IDS}
    for identity, receipt in receipts.items():
        verify_receipt(identity, receipt, audit)
    weights = {case['arm']: load_weights(case) for case in cases}
    context = original_dynamic_context(cases[0], weights)
    rows, recoveries = {}, {}
    for case in cases:
        arm, identity = case['arm'], case['case_id'] + '_FINE_ORIGINAL'
        row, recovery = new_case(case, receipts[identity], weights[arm])
        row.update(arm=arm, year=2021, target_array_SHA256=case['target_array_SHA256'],
                   frozen_target_descriptive_statistics=target_description(weights[arm]))
        rows[arm], recoveries[arm] = row, recovery
    comparisons = all_pairwise_comparisons(rows, recoveries, weights, start_us=CALENDAR[0])
    four_way = common_prefix(rows, recoveries, weights, start_us=CALENDAR[0]) if all(recoveries[arm] is not None for arm in ARMS) else None
    year = {'year': 2021, 'calendar_us': list(CALENDAR), 'source_index_SHA256': SOURCE_INDEX_SHA256,
            'target_archive_SHA256': TARGET_ARCHIVE_SHA256, 'arms': rows, 'comparisons': comparisons,
            'four_way_common_observed_prefix': four_way, 'original_dynamic_target_context': context}
    report = {'kind': 'FIXED_FOUR_CASE_ORIGINAL_2021_READ_ONLY_OBSERVER', 'case_ids': list(CASE_IDS), 'years': [year],
              'all_predeclared_cases_retained': True, 'pairwise_contrast_count': 6, 'contrast_direction': 'b_minus_a',
              'new_wallets_by_observer': 0, 'historical_wallets_advanced_by_observer': 0,
              'fine_control_wallets_rerun': 0, 'reused_comparator_wallets': 0,
              'single_authorized_run_state_locator': str(STATE.relative_to(ROOT)),
              'initial_capital_USDT_per_independent_wallet': CAPITAL,
              'source_target_identity_manifest_SHA256': sha(MODULE / 'CASE_BINDINGS.json'),
              'reviewed_execution_freeze_manifest_SHA256': sha(MODULE / 'FROZEN_CODE.json'),
              'independent_pre_execution_review_SHA256': sha(MODULE / 'REVIEW_RECEIPT.json'),
              'postrun_reviewed_code_manifest_SHA256': sha(HERE / 'REVIEWED_POSTRUN_CODE.json'),
              'terminal_inputs_manifest_SHA256': sha(HERE / 'TERMINAL_INPUTS.json'),
              'bounded_AUDIT_resource_receipt_SHA256': sha(HERE / 'AUDIT_RESOURCE_RECEIPTS.json'),
              'controller_terminal_status': read_json(STATE / 'RESOURCE_RECEIPTS.json')['status'],
              'daily_vol_formula': VOL_FORMULA, 'all_prior_strategy_STOP_statuses_preserved': True,
              'funding_raw_fraction_economics_conditional': True, 'no_OOS_or_native_quantity_resolution_certification': True,
              'interpretation': 'Conditional seen development replication only. No alpha/OOS/native-grid/venue-validation claim; unequal horizons use matched completed-minute prefixes. Full marked residue is never promoted to paid cash.'}
    write_outputs(report)
    print('FOUR_CASE_ORIGINAL_2021_REPORT_COMPLETE', len(CASE_IDS), len(comparisons), flush=True)


if __name__ == '__main__':
    main()
