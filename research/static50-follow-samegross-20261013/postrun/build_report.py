"""Bounded GO-gated observer of six saved samegross cases and three reused S.

Imports execute no historical read or financial code. Aggregation uses saved
minute chunks only; neither cold restore nor a simulator is invoked here.
"""
from __future__ import annotations

from decimal import Decimal
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


def pointer_at(recovery: Path) -> dict:
    pointer = read_json(recovery / 'POINTER.json')
    completed = integer(pointer['completed_minutes'], 'completed minutes')
    rows, paths = 0, set()
    for index, chunk in enumerate(pointer['chunks']):
        count = integer(chunk['rows'], 'chunk rows', 1)
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
            'mean_actual_signed_net', 'max_actual_abs_signed_net', 'mean_l1_target_weight_gap', 'trade_legs',
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
            'saved_cumulative_b_minus_a': {k: right['saved_cumulative_at_last_completed_minute'][k] - value if value is not None and right['saved_cumulative_at_last_completed_minute'][k] is not None else None
                                         for k, value in left['saved_cumulative_at_last_completed_minute'].items()}}


def verify_audit_stage(audit: dict, *, manifest_sha: str, run_binding_sha: str, controller_sha: str, state_locator: str) -> None:
    if (audit.get('stage') != 'AUDIT' or audit.get('status') != 'ALL_OBSERVERS_FINISHED' or audit.get('case_ids') != list(CASE_IDS)
            or set(audit.get('per_observer', {})) != set(CASE_IDS) or audit.get('unstarted_observer_ids') != []
            or audit.get('financial_advances') != 0 or audit.get('historical_wallets_opened') != 0 or audit.get('observer_manifest_SHA256') != manifest_sha):
        raise ValueError('Successful full-population bounded AUDIT receipt missing')
    original_go = audit.get('postrun_GO_text')
    if not isinstance(original_go, str) or hashlib.sha256(original_go.encode()).hexdigest() != audit.get('postrun_GO_SHA256'):
        raise ValueError('Original AUDIT GO exact bytes/hash missing')
    go = json.loads(original_go)
    if (go.get('parent_GO') is not True or 'AUDIT' not in go.get('approved_stages', []) or not set(go.get('approved_stages', [])) <= {'AUDIT', 'REPORT'}
            or go.get('manifest_SHA256') != manifest_sha or go.get('state_locator') != state_locator
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


def load_weights(case: dict, *, original: bool = False):
    import numpy as np
    ref = case['original_STATIC50'] if original else case
    path = safe_path(ROOT, ref['target_archive_local_locator'])
    if sha(path) != ref['target_archive_SHA256']:
        raise ValueError('Frozen target archive SHA differs')
    with np.load(path, allow_pickle=False) as archive:
        weights = archive['STATIC50' if original else case['arm']].copy()
        clocks = archive['decision_us'].copy()
    if (weights.dtype != np.float64 or list(weights.shape) != case['target_shape'] or not np.isfinite(weights).all()
            or hashlib.sha256(weights.tobytes(order='C')).hexdigest() != ref['target_array_SHA256']
            or not np.array_equal(clocks, np.arange(*case['calendar'], DAY))):
        raise ValueError('Frozen target/calendar numerical identity differs')
    return weights


def observed_row(case: dict, identity: str, summary: dict, result: dict | None, metrics: dict, *, quantities, rejections, journals, bridge) -> dict:
    required = (case['calendar'][1] - case['calendar'][0]) // MINUTE
    row = {'case_id': identity, 'available': True, **censoring(summary, required, official_result=result is not None),
           'marked_PnL_USDT': summary['net_PnL'], 'completion': summary['completion'], 'account_status': summary['account_status'],
           'stop_us': summary.get('stop_us'), 'observed_clock_us': summary.get('clock_us'),
           'minute_drawdown': summary['all_observation_max_drawdown'], 'halt_witness': summary.get('halt_witness'),
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
        for key in ('mean_actual_gross', 'max_actual_gross', 'annual_daily_vol'):
            if key in result and (result[key] is None) != (row[key] is None):
                raise ValueError('Saved result daily/gross metric availability differs')
            if key in result and result[key] is not None and abs(result[key] - row[key]) > 1e-12:
                raise ValueError('Saved result daily/gross metric differs')
    return row


def new_case(case: dict, receipt: dict, weights) -> tuple[dict, Path | None]:
    identity, state = case['case_id'] + '_FINE_ORIGINAL', STATE / (case['case_id'] + '_FINE_ORIGINAL')
    if receipt['status'] not in (FULL_COLD, PARTIAL_COLD):
        return {'case_id': identity, 'available': False, 'observation_class': 'UNAVAILABLE', 'reason': receipt['status'],
                'full_calendar': False, 'paid_flat': False, 'annual_paid_return': None, 'paid_cash_PnL_USDT': None}, None
    result = read_json(state / 'RESULT.json') if (state / 'RESULT.json').exists() else None
    summary = receipt['observed_summary']
    if result is not None and read_json(state / 'ACCOUNT.json')['summary'] != summary:
        raise ValueError('Cold receipt/account summary differs')
    numeric = read_json(state / 'MINUTE_NUMERIC.json') if result is not None else None
    metrics = stream_prefix(state / 'recovery', summary['completed_minutes'], weights, numeric=numeric, start_us=case['calendar'][0])
    row = observed_row(case, identity, summary, result, metrics, quantities=receipt.get('observed_terminal_residual_quantity'),
                       rejections=receipt.get('observed_rejection_counts'), journals=receipt.get('observed_journal_counts'), bridge=receipt.get('independent_decimal_NAV_bridge'))
    row.update(input_files_SHA256=receipt['input_files_SHA256'], cold_receipt_SHA256=sha(HERE / 'receipts' / (identity + '.json')))
    return row, state / 'recovery'


def original_s(case: dict, weights) -> tuple[dict, Path]:
    refs = case['reused_original_STATIC50_fine_comparator']
    needed = {'RESULT.json', 'ACCOUNT.json', 'BINDING.json', 'MINUTE_NUMERIC.json', 'recovery/POINTER.json'}
    if set(refs) != needed:
        raise ValueError('Reused original S pinned file population differs')
    for record in refs.values():
        if sha(safe_path(ROOT, record['local_locator'])) != record['SHA256']:
            raise ValueError('Hash-bound reused original fine S changed')
    state = safe_path(ROOT, refs['RESULT.json']['local_locator']).parent
    if any(safe_path(ROOT, ref['local_locator']) != state / name for name, ref in refs.items()):
        raise ValueError('Reused comparator file locators do not identify one state')
    result, account, binding = read_json(state / 'RESULT.json'), read_json(state / 'ACCOUNT.json'), read_json(state / 'BINDING.json')
    pointer = pointer_at(state / 'recovery')
    identity = f"Y{case['year']}_STATIC50_FINE_ORIGINAL"
    if (binding.get('case_id') != identity or binding.get('calendar') != case['calendar'] or pointer['binding'] != binding
            or binding.get('target_array_SHA256') != case['original_STATIC50']['target_array_SHA256']
            or binding.get('source_index_SHA256') != case['source_index_SHA256'] or result.get('genuine_state_hash') != pointer['state_hash']
            or sha(safe_path(state / 'recovery', pointer['snapshot_path'])) != pointer['snapshot_SHA256']):
        raise ValueError('Original fine S binding/checkpoint/target/source differs')
    metrics = stream_prefix(state / 'recovery', pointer['completed_minutes'], weights,
                            numeric=read_json(state / 'MINUTE_NUMERIC.json'), start_us=case['calendar'][0])
    row = observed_row(case, identity, account['summary'], result, metrics, quantities=result['terminal_residual_quantity'],
                       rejections=result['rejection_counts'], journals={k: len(account.get(k, [])) for k in ('trades', 'funding', 'rejections', 'breaches', 'liquidations')},
                       bridge=result['independent_decimal_NAV_bridge'])
    row.update(reused_without_restore_or_advance=True, input_files_SHA256={ref['local_locator']: ref['SHA256'] for ref in refs.values()})
    return row, state / 'recovery'


def target_description(control, pool, original, follow) -> dict:
    """Descriptions of frozen targets, never a forecast or performance gate."""
    import numpy as np
    raw = .5 * original + .5 * follow
    cancellation = .5 * np.abs(original) + .5 * np.abs(follow) - np.abs(raw)
    return {'days': len(control),
            'FOLLOW_cash_days': int(np.count_nonzero(np.abs(follow).sum(axis=1) == 0)),
            'opposite_nonzero_S_F_symbol_day_cells': int(np.count_nonzero(original * follow < 0)),
            'mean_raw_pool_internal_netting_gross_reduction': float(cancellation.sum(axis=1).mean()),
            'new_control_downscaled_days_vs_original_S': int(np.count_nonzero(np.abs(control).sum(axis=1) < np.abs(original).sum(axis=1) - 1e-14)),
            'new_control': {'mean_target_gross': float(np.abs(control).sum(axis=1).mean()),
                            'max_target_gross': float(np.abs(control).sum(axis=1).max()),
                            'mean_signed_target_net': float(control.sum(axis=1).mean()),
                            'active_symbol_day_cells': int(np.count_nonzero(control))},
            'pool_candidate': {'mean_target_gross': float(np.abs(pool).sum(axis=1).mean()),
                               'max_target_gross': float(np.abs(pool).sum(axis=1).max()),
                               'mean_signed_target_net': float(pool.sum(axis=1).mean()),
                               'active_symbol_day_cells': int(np.count_nonzero(pool))},
            'pool_control_different_sign_symbol_day_cells': int(np.count_nonzero(np.sign(pool) != np.sign(control))),
            'internal_netting_is_one_shared_one_way_wallet': True,
            'equal_target_gross_is_not_equal_covariance_or_realized_risk': True}


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


def render_summary(report: dict) -> str:
    def number(value, percent=False):
        return 'null' if value is None else f'{value * 100:.6f}%' if percent else f'{value:.6f}'
    lines = ['# Fixed same-target-gross pool comparison', '',
             'All six new fine cases and three reused original fine S wallets are retained. Report creates zero wallets, advances zero financial steps and reruns zero controls.', '',
             'New control depends on FOLLOW through G=min(gross(S),gross(.5S+.5F)); it is a new risk-timing control. Equal daily target gross does not establish equal actual gross or realized risk.', '']
    for year in report['years']:
        lines += [f"## {year['year']}", '', '| Path | Class | Minutes | Marked PnL USDT | Paid PnL USDT | Daily vol | Mean/max actual gross | Residual gross USDT |',
                  '|---|---|---:|---:|---:|---:|---:|---:|']
        for name in ('new_control', 'pool_candidate', 'reused_original_S'):
            row = year[name]
            if not row['available']:
                lines.append(f"| {name} | UNAVAILABLE | null | null | null | null | null | null |")
                continue
            vol = row['annual_daily_vol']
            label = ' full-calendar' if vol is not None else ' observed-prefix annualized'
            if vol is None:
                vol = row['observed_prefix_daily_vol_annualized']
            lines.append(f"| {name} | {row['observation_class']} | {row['completed_minutes']}/{row['required_minutes']} | {number(row['marked_PnL_USDT'])} | {number(row['paid_cash_PnL_USDT'])} | {number(vol, True)}{label} | {number(row['mean_actual_gross'])}/{number(row['max_actual_gross'])} | {number(row['terminal_residual_gross_notional_USDT'])} |")
            if row['halt_count']:
                lines.append(f"\n{name} halted at {row['stop_us']} us; the marked halt endpoint is separate from the last completed-minute prefix.")
            nonzero = {s: q for s, q in row['terminal_residual_quantity'].items() if exact_quantity(q) != 0}
            if nonzero:
                lines.append('\n' + name + ' exact residual quantity: ' + ', '.join(s + '=' + q for s, q in nonzero.items()) + '. No free terminal flattening.')
        lines.append('')
        for name, comparison in year['comparisons'].items():
            lines.append(name + ': paid cash delta ' + number(comparison['paid_cash_PnL_delta_USDT']) + ' USDT; same-full-calendar marked delta ' + number(comparison['same_full_calendar_observed_deltas']['marked_PnL_USDT']) + ' USDT.')
            prefix = comparison['common_observed_minute_prefix']
            if prefix is not None:
                p = prefix['paths']
                lines.append(f"Common completed-minute prefix {prefix['common_completed_minutes']} (close_us={prefix['last_completed_minute_close_us']}), excluding post-minute halt mark: a marked {number(p['a']['last_completed_minute_marked_PnL_USDT'])}, b marked {number(p['b']['last_completed_minute_marked_PnL_USDT'])}, b−a {number(prefix['b_minus_a']['last_completed_minute_marked_PnL_USDT'])} USDT; observed-prefix annualized daily vol a/b {number(p['a']['daily_statistics']['annualized_daily_vol'], True)}/{number(p['b']['daily_statistics']['annualized_daily_vol'], True)}. No annual paid return or cross-horizon endpoint delta.")
        volatility = year['comparisons']['pool_minus_new_control']['matched_daily_volatility']
        delta = volatility['b_minus_a_daily_vol_annualized']
        if delta is not None:
            direction = 'higher' if delta > 0 else 'lower' if delta < 0 else 'equal'
            scope = 'same full calendar' if volatility['scope'] == 'SAME_FULL_CALENDAR' else 'same completed-minute prefix, complete UTC days only'
            lines.append(f"Pool daily volatility is {direction} than the new control on the {scope}: difference {number(delta, True)}; volatility decreased={str(volatility['b_daily_vol_lower_than_a']).lower()}.")
        lines.append('')
    matched = [year['comparisons']['pool_minus_new_control']['matched_daily_volatility'] for year in report['years']]
    if len(matched) == 3 and all(v['b_minus_a_daily_vol_annualized'] is not None and v['b_minus_a_daily_vol_annualized'] > 0 for v in matched):
        lines += ['Pool volatility did not fall in any of the three matched observed comparisons: it is higher on the 2023/2025 full calendars and the 2024 common observed prefix. The 2024 pool full-year volatility is not directly compared with the halted control’s partial volatility.', '']
    lines += ['## Interpretation' , '', VOL_FORMULA + '. Prefix volatility uses complete UTC days only and is not a full-year estimate.',
              '2025 marked-only residue remains marked-only even when small. Same-gross target matching does not remove different fills, costs, funding, actual exposure or covariance.',
              'Original FOLLOW cash-confidence STOP and other strategy STOP decisions remain. These are conditional seen-path observations, not alpha, selection-adjusted/OOS evidence, venue-validated fills or promised APR.',
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
    if tuple(ids) != tuple(CASE_IDS) or len(ids) != 6 or tuple(c['case_id'] + '_FINE_ORIGINAL' for c in plan['cases']) != tuple(CASE_IDS):
        raise ValueError('Terminal run differs from fixed ordered six-case population')
    audit = read_json(HERE / 'AUDIT_RESOURCE_RECEIPTS.json')
    verify_audit_stage(audit, manifest_sha=sha(HERE / 'REVIEWED_POSTRUN_CODE.json'), run_binding_sha=sha(STATE / 'RUN_BINDING.json'),
                       controller_sha=sha(STATE / 'RESOURCE_RECEIPTS.json'), state_locator=str(STATE.relative_to(ROOT)))
    if {p.stem for p in (HERE / 'receipts').glob('*.json')} != set(CASE_IDS):
        raise ValueError('Cold receipt population differs from exactly six planned cases')
    receipts = {identity: read_json(HERE / 'receipts' / (identity + '.json')) for identity in CASE_IDS}
    for identity, receipt in receipts.items():
        verify_receipt(identity, receipt, audit)
    import numpy as np
    years = []
    for year in (2023, 2024, 2025):
        cases = [c for c in plan['cases'] if c['year'] == year]
        if len(cases) != 2 or [c['arm'] for c in cases] != ['STATIC50_SAMEGROSS', 'FOLLOW_POOL_SAMEGROSS']:
            raise ValueError('Year-specific control/candidate population differs')
        control_case, pool_case = cases
        if any(control_case[k] != pool_case[k] for k in ('calendar', 'symbols', 'source_index_SHA256', 'original_STATIC50', 'reused_original_STATIC50_fine_comparator')):
            raise ValueError('Paired calendar/source/original comparator differs')
        cw, pw, ow = load_weights(control_case), load_weights(pool_case), load_weights(control_case, original=True)
        with np.load(safe_path(ROOT, control_case['target_archive_local_locator']), allow_pickle=False) as archive:
            frozen_follow = archive['FOLLOW'].copy()
        target_stats = target_description(cw, pw, ow, frozen_follow)
        target_error = float(np.max(np.abs(np.abs(cw).sum(axis=1) - np.abs(pw).sum(axis=1))))
        if target_error > 1e-14:
            raise ValueError('Frozen daily target gross is not equal')
        control, cr = new_case(control_case, receipts[control_case['case_id'] + '_FINE_ORIGINAL'], cw)
        pool, pr = new_case(pool_case, receipts[pool_case['case_id'] + '_FINE_ORIGINAL'], pw)
        old, oldr = original_s(control_case, ow)
        start = control_case['calendar'][0]
        comparisons = {'pool_minus_new_control': pair_comparison(control, pool, cr, pr, cw, pw, start_us=start),
                       'pool_minus_reused_original_S': pair_comparison(old, pool, oldr, pr, ow, pw, start_us=start),
                       'new_control_minus_reused_original_S': pair_comparison(old, control, oldr, cr, ow, cw, start_us=start)}
        triple = common_prefix({'new_control': control, 'pool_candidate': pool, 'reused_original_S': old},
                               {'new_control': cr, 'pool_candidate': pr, 'reused_original_S': oldr},
                               {'new_control': cw, 'pool_candidate': pw, 'reused_original_S': ow}, start_us=start) if year == 2024 and cr is not None and pr is not None else None
        years.append({'year': year, 'calendar_us': control_case['calendar'], 'source_index_SHA256': control_case['source_index_SHA256'],
                      'new_control': control, 'pool_candidate': pool, 'reused_original_S': old, 'comparisons': comparisons,
                      'three_way_common_observed_prefix': triple, 'daily_target_gross_max_abs_error': target_error,
                      'target_descriptive_statistics': target_stats,
                      'target_array_SHA256': {'new_control': control_case['target_array_SHA256'], 'pool_candidate': pool_case['target_array_SHA256'], 'reused_original_S': control_case['original_STATIC50']['target_array_SHA256']}})
    report = {'kind': 'FIXED_SIX_CASE_SAMEGROSS_READ_ONLY_OBSERVER', 'case_ids': list(CASE_IDS), 'years': years,
              'all_predeclared_cases_retained': True, 'new_wallets_by_observer': 0, 'historical_wallets_advanced_by_observer': 0,
              'fine_control_wallets_rerun': 0, 'reused_original_fine_S_wallets': 3, 'initial_capital_USDT_per_independent_wallet': CAPITAL,
              'source_target_identity_manifest_SHA256': sha(MODULE / 'CASE_BINDINGS.json'),
              'reviewed_execution_freeze_manifest_SHA256': sha(MODULE / 'FROZEN_CODE.json'),
              'independent_pre_execution_review_SHA256': sha(MODULE / 'REVIEW_RECEIPT.json'),
              'postrun_reviewed_code_manifest_SHA256': sha(HERE / 'REVIEWED_POSTRUN_CODE.json'),
              'bounded_AUDIT_resource_receipt_SHA256': sha(HERE / 'AUDIT_RESOURCE_RECEIPTS.json'),
              'controller_terminal_status': read_json(STATE / 'RESOURCE_RECEIPTS.json')['status'],
              'daily_vol_formula': VOL_FORMULA, 'common_gross_is_target_only': True,
              'control_is_new_F_dependent_risk_timing_not_original_S': True,
              'original_FOLLOW_cash_STOP_and_other_STOPs_preserved': True,
              'interpretation': 'Conditional seen-path observations only. No alpha/OOS/venue-validation claim; unequal horizons use matched completed-minute prefixes. Full marked residue is never promoted to paid cash.'}
    write_outputs(report)
    print('SIX_CASE_SAMEGROSS_REPORT_COMPLETE', len(CASE_IDS), len(years), flush=True)


if __name__ == '__main__':
    main()
