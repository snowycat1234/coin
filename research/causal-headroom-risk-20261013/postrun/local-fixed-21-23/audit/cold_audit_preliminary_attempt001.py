"""Minimal read-only HEADROOM cold/prefix/ledger audit. Never advances history."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / 'coin_headroom_risk_candidate_20261013'
FREEZE = 'c1c50dd484400a175bf28b16ae16a500a5c195f0f88403e5d5dc4d08f275d5e6'
REVIEW = '3ccc9f206dcd7df9e3ed0e718851eda206fa29185604d9d0c38f44c6abd91b33'
MINUTE = 60_000_000
DAY = 86_400_000_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def same(actual, expected, label):
    if actual != expected:
        raise ValueError('HEADROOM cold audit mismatch: ' + label)


def near(actual, expected, label, tolerance=Decimal('1e-25')):
    if abs(actual-expected) > tolerance:
        raise ValueError('HEADROOM ledger mismatch: ' + label)


@contextmanager
def forbid_transitions(simulator, account_class):
    methods = ((simulator, ('advance_day', 'schedule', 'attempt', 'funding_through',
                            'risk_schedule', 'observe')),
               (account_class, ('execute_fill', 'apply_funding', 'update_marks')))
    previous = []
    def forbidden(*args, **kwargs):
        raise RuntimeError('Read-only audit cannot execute a financial transition')
    try:
        for cls, names in methods:
            for name in names:
                previous.append((cls, name, cls.__dict__.get(name), name in cls.__dict__))
                setattr(cls, name, forbidden)
        yield
    finally:
        for cls, name, value, owned in reversed(previous):
            if owned:
                setattr(cls, name, value)
            else:
                delattr(cls, name)


def verify_state(sim, snapshot, pointer, binding):
    same(pointer['binding'], binding, 'pointer binding')
    same(sim.state_hash(), pointer['state_hash'], 'state hash')
    same(sim.cursor, pointer['cursor'], 'cursor')
    same(sim.stop, pointer['stop'], 'stop')
    same(sim.rows_written, pointer['completed_minutes'], 'rows')
    same(sum(row['rows'] for row in pointer['chunks']), sim.rows_written, 'chunk rows')
    same(sim.account.snapshot(), snapshot['account'], 'full exact account state')
    for key, value in snapshot['state'].items():
        expected = deepcopy(value)
        if key == 'pending':
            expected = {s: {**order, 'target': Decimal(order['target'])} for s, order in value.items()}
        elif key in ('weights', 'decision_kinds'):
            expected = {int(stamp): row for stamp, row in value.items()}
        same(getattr(sim, key), expected, 'scheduler state:' + key)


def input_hashes(state_root, state, pointer, baseline, baseline_pointer, case):
    paths = [state_root/'RUN_BINDING.json', state_root/'RESOURCE_RECEIPTS.json',
             state/'BINDING.json', state/'recovery/POINTER.json',
             state/'recovery'/pointer['snapshot_path']]
    paths += [state/'recovery'/row['path'] for row in pointer['chunks']]
    paths += [state/name for name in ('ACCOUNT.json', 'RESULT.json', 'DAILY.csv', 'MINUTE_NUMERIC.json') if (state/name).exists()]
    paths += [baseline/name for name in case['baseline_files_SHA256']]
    paths += [baseline/'recovery'/baseline_pointer['snapshot_path']]
    paths += [baseline/'recovery'/row['path'] for row in baseline_pointer['chunks']]
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}


def prefix_proof(output, case, baseline, pointer):
    import numpy as np
    signals = [row['event_us'] for row in output['protective_policy']['events'] if row['kind'] == 'FULL_EXIT_SIGNAL']
    first = min(signals) if signals else None
    saved_through = case['calendar'][0] + output['minute'].height*MINUTE
    old_through = case['calendar'][0] + pointer['completed_minutes']*MINUTE
    through = min(saved_through, old_through, first if first is not None else saved_through)
    rows = (through-case['calendar'][0])//MINUTE
    new = output['minute'].drop('close_us').to_numpy()[:rows]
    parts = []
    for record in pointer['chunks']:
        path = baseline/'recovery'/record['path']
        same(sha(path), record['SHA256'], 'baseline chunk SHA')
        with np.load(path, allow_pickle=False) as archive:
            same(archive.files, ['minute_chunk'], 'baseline chunk schema')
            a = archive['minute_chunk'].copy()
        same(a.dtype, np.dtype('float64'), 'baseline chunk dtype')
        same(list(a.shape), [record['rows'], record['columns']], 'baseline chunk shape')
        if not np.isfinite(a).all():
            raise ValueError('Nonfinite baseline minute')
        parts.append(a)
    old = np.concatenate(parts)[:rows] if parts else np.empty((0, 36), dtype=np.float64)
    same(new.shape, old.shape, 'financial prefix shape')
    same(new.dtype, old.dtype, 'financial prefix dtype')
    same(new.tobytes(order='C'), old.tobytes(order='C'), 'all financial minute prefix bits')
    saved = read(baseline/'ACCOUNT.json')
    counts = {}
    for key in ('trades', 'funding'):
        a = [r for r in output[key] if r['event_us'] <= through]
        b = [r for r in saved[key] if r['event_us'] <= through]
        same(a, b, key + ' exact inclusive financial prefix')
        counts[key] = len(a)
    return {'status': 'PASS_EXACT_MINUTE_TRADE_FUNDING_COMMON_PREFIX',
            'first_HEADROOM_protective_signal_us': first,
            'through_us_inclusive': through, 'minute_rows': rows,
            'minute_raw_SHA256': hashlib.sha256(new.tobytes(order='C')).hexdigest(),
            'trade_legs': counts['trades'], 'funding_rows': counts['funding'],
            'through_first_HEADROOM_signal': first is not None and through == first,
            'scope': 'NUMERIC_FINANCIAL_MINUTE_BITS_AND_TRADE_FUNDING_JOURNALS_ONLY',
            'new_metadata_or_full_snapshot_identity_claimed': False,
            'controls_rerun': 0}


def ledger_proof(account, output, source):
    """Journal arithmetic and economic wallet bridge only, no account transitions."""
    with localcontext() as ctx:
        ctx.prec = 40
        totals = {'fees': Decimal(0), 'execution_cost': Decimal(0),
                  'realized_PnL': Decimal(0), 'gross_fill_turnover': Decimal(0), 'funding_cash': Decimal(0)}
        for row in output['trades']:
            x = {k: Decimal(v) for k, v in row['decimal_strings'].items()}
            q, mid, fill = (x[k] for k in ('quantity', 'mid_price', 'fill_price'))
            direction = Decimal(1) if row['side'] == 'BUY' else Decimal(-1)
            same(fill, mid*(1+direction*Decimal('.0008')), 'per-leg 4bp+4bp fill')
            same(x['fee_amount'], q*fill*Decimal('.00055'), 'per-leg 5.5bp fee')
            same(x['execution_cost'], q*abs(fill-mid), 'per-leg execution cost')
            same(q % Decimal('1e-8'), Decimal(0), 'per-leg fine quantity grid')
            if row['leg'] == 'OPEN':
                same(x['margin_allocated'], q*fill, 'per-leg isolated 1x collateral')
            for key, journal_key in (('fees', 'fee_amount'), ('execution_cost', 'execution_cost'),
                                     ('realized_PnL', 'realized_PnL')):
                totals[key] += x[journal_key]
            totals['gross_fill_turnover'] += q*fill
        quantity = {s: Decimal(0) for s in source['symbols']}
        trades = sorted(output['trades'], key=lambda row: row['event_us'])
        ti = 0
        if len(output['funding']) > len(source['events']):
            raise ValueError('Funding journal exceeds original events')
        for row, raw in zip(output['funding'], source['events']):
            for key, value in raw.items():
                same(row[key], value, 'source funding row:' + key)
            while ti < len(trades) and trades[ti]['event_us'] < row['event_us']:
                trade = trades[ti]
                quantity[trade['symbol']] += Decimal(trade['decimal_strings']['position_delta'])
                ti += 1
            x = row.get('decimal_strings', {})
            owned_q = Decimal(x.get('quantity', str(row['quantity'])))
            same(owned_q, quantity[row['symbol']], 'strict pre-funding signed inventory')
            same(bool(owned_q), row['owned'], 'funding ownership')
            rate = Decimal(str(raw['raw_rate']))*Decimal(str(row['conditional_rate_scale']))
            same(Decimal(row['assumed_fraction_decimal']), rate, 'unchanged source funding scale')
            amount = Decimal(x.get('signed_funding_USDT', str(row['signed_funding_USDT'])))
            if row['mark_price'] is not None:
                mark = Decimal(x['mark_price'])
                same(amount, -owned_q*mark*rate if row['owned'] else Decimal(0), 'funding arithmetic')
                if not row['mark_close_us'] < row['event_us']:
                    raise ValueError('Funding lacks strict past mark')
            else:
                same((owned_q, amount), (Decimal(0), Decimal(0)), 'fresh flat no-mark funding')
            totals['funding_cash'] += amount
        for key, value in totals.items():
            near(value, getattr(account, key), 'exact journal total:' + key)
        collateral = sum((p.isolated_balance for p in account.positions.values()), Decimal(0))
        unrealized = sum((p.quantity*(account.marks[s][-1]['price']-p.entry_price)
                          for s, p in account.positions.items() if p.quantity), Decimal(0))
        capital = account.free_cash+collateral-account.unpaid_liability
        expected_capital = Decimal(10000)+totals['realized_PnL']-totals['fees']+totals['funding_cash']
        near(capital, expected_capital, 'free+isolated-liability capital')
        near(account.nav(), capital+unrealized, 'live economic NAV with signed inventory')
        return {'status': 'PASS_OLD_KERNEL_JOURNAL_AND_LIVE_ECONOMIC_BRIDGES',
                'per_trade_cost_legs_verified': len(output['trades']),
                'source_funding_rows_verified': len(output['funding']),
                'exact_journal_totals': {k: str(v) for k, v in totals.items()},
                'free_cash_USDT': str(account.free_cash), 'isolated_collateral_USDT': str(collateral),
                'isolated_collateral_by_symbol': {s: str(p.isolated_balance) for s, p in account.positions.items()},
                'unpaid_liability_USDT': str(account.unpaid_liability),
                'unrealized_signed_inventory_PnL_USDT': str(unrealized),
                'live_economic_NAV_USDT': str(account.nav()),
                'capital_bridge_error_USDT': str(capital-expected_capital),
                'financial_transitions': 0}


def main(args):
    if sys.flags.optimize:
        raise RuntimeError('Frozen assertions must stay enabled')
    if len(os.sched_getaffinity(0)) != 1 or any(not 0 < x <= 4_000_000_000 for x in resource.getrlimit(resource.RLIMIT_AS)) or any(not 0 < x <= 300 for x in resource.getrlimit(resource.RLIMIT_CPU)):
        raise RuntimeError('Audit requires one CPU, AS<=4GB and CPU<=300 seconds')
    if not args.controller_released:
        raise RuntimeError('Explicit terminal controller release confirmation required')
    sys.path[:0] = [str(MODULE)]
    same(sha(MODULE/'FROZEN_CODE.json'), FREEZE, 'reviewed freeze pin')
    same(sha(MODULE/'REVIEW_RECEIPT.json'), REVIEW, 'review receipt pin')
    from freeze_candidate import verify
    verify(ROOT, require_review=True)
    plan = read(MODULE/'CASE_BINDINGS.json')
    case = next(c for c in plan['cases'] if c['year'] == args.year)
    if args.year not in (2021, 2023):
        raise ValueError('Local observer limited to 2021/2023')
    state_root = args.state_root.resolve()
    state = state_root/(case['case_id']+'_FINE_HEADROOM')
    binding = read(state/'BINDING.json')
    run = read(state_root/'RUN_BINDING.json')
    controller = read(state_root/'RESOURCE_RECEIPTS.json')
    same(binding['run_binding_SHA256'], sha(state_root/'RUN_BINDING.json'), 'run binding hash')
    same(run['parent_GO'], True, 'historical controller GO')
    if binding['case_id'] not in controller['per_case']:
        raise ValueError('Terminal controller lacks this case receipt')
    for key in ('calendar', 'year', 'arm', 'source_index_SHA256', 'target_archive_SHA256', 'target_array_SHA256'):
        same(binding[key], case[key], 'fixed case:' + key)
    same(binding['mode'], 'HEADROOM', 'mode')
    same(binding['freeze_manifest_SHA256'], FREEZE, 'case freeze')
    same(run['review_receipt_SHA256'], REVIEW, 'run review')
    same(binding['terminal_opens'], 5, 'original terminal opens')
    same(binding['terminal_signal_us'], case['calendar'][1]-6*MINUTE, 'original terminal clock')
    from source_adapter import load_port, source_window
    from feature_tape import FeatureTape
    port = load_port(ROOT)
    source_root = Path(binding['source_root'])
    source = source_window(case, source_root, port, ROOT)
    source['headroom_features'] = FeatureTape.load(MODULE/'features'/f'Y{args.year}.npz', read(MODULE/'features'/f'Y{args.year}.json'))
    same(binding['feature_binding'], source['headroom_features'].binding, 'feature binding')
    from headroom_policy import HeadroomFullExitSimulator
    from fine_account import FineGridAccount, profile_sha
    same(binding['fine_account_class'], FineGridAccount.VERSION, 'account class')
    same(binding['fine_profile_SHA256'], profile_sha(), 'fine profile')
    for key, path in (('fine_account_SHA256', ROOT/'coin_quantity_resolution_20261013/fine_account.py'),
                      ('account_SHA256', ROOT/'coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py'),
                      ('scheduler_SHA256', ROOT/'coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py'),
                      ('guard_policy_SHA256', ROOT/'coin_margin_protective_policy_20261013/protective_policy.py'),
                      ('headroom_adapter_SHA256', MODULE/'headroom_policy.py')):
        same(binding[key], sha(path), 'unchanged kernel/code:' + key)
    baseline = ROOT/case['baseline_state_local_locator']
    for name, digest in case['baseline_files_SHA256'].items():
        same(sha(baseline/name), digest, 'prebound original file:' + name)
    old_binding = read(baseline/'BINDING.json')
    for key in ('calendar', 'capital_USDT', 'fine_account_SHA256', 'fine_account_class', 'fine_profile_SHA256',
                'account_SHA256', 'scheduler_SHA256', 'source_index_SHA256', 'target_archive_SHA256', 'target_array_SHA256'):
        same(binding[key], old_binding[key], 'original binding:' + key)
    old_pointer = read(baseline/'recovery/POINTER.json')
    old_snapshot_path = baseline/'recovery'/old_pointer['snapshot_path']
    same(sha(old_snapshot_path), old_pointer['snapshot_SHA256'], 'baseline snapshot hash')
    old_snapshot = json.loads(gzip.decompress(old_snapshot_path.read_bytes()))
    snapshot, pointer = port.restore_snapshot(state/'recovery', binding)
    for key in ('mode', 'cost', 'unit', 'persist_cash_close', 'final_day_target_zero'):
        same(snapshot[key], old_snapshot[key], 'original configuration:' + key)
    for key in ('version', 'config', 'contract', 'instrument_profiles', 'closing_min_notional_exempt', 'cost_context'):
        same(snapshot['account'][key], old_snapshot['account'][key], 'original account identity:' + key)
    same(snapshot['cost'], port.native.COSTS[0], 'original cost')
    same(snapshot['unit'], port.native.UNITS[0], 'original funding unit')
    same(snapshot['target_meta'], {'kind': 'EXACT_ORIGINAL_STATIC50_CSH_HEADROOM_ONLY', 'binding': binding}, 'target provenance')
    before_files = input_hashes(state_root, state, pointer, baseline, old_pointer, case)
    with forbid_transitions(HeadroomFullExitSimulator, FineGridAccount):
        sim = HeadroomFullExitSimulator.from_snapshot(snapshot, source, account_class=FineGridAccount)
        same(type(sim.account), FineGridAccount, 'restored exact account type')
        verify_state(sim, snapshot, pointer, binding)
        output = sim.result()
        same(sim.state_hash(), pointer['state_hash'], 'result has no state mutation')
        same(sim.account.snapshot(), snapshot['account'], 'result has no account mutation')
    import numpy as np
    target_path = Path(binding['target_archive'])
    same(sha(target_path), case['target_archive_SHA256'], 'target archive')
    with np.load(target_path, allow_pickle=False) as archive:
        clocks, weights = archive['decision_us'].copy(), archive[case['arm']].copy()
    np.testing.assert_array_equal(clocks, np.arange(*case['calendar'], DAY))
    same(weights.dtype.str, case['target_dtype'], 'target dtype')
    same(list(weights.shape), case['target_shape'], 'target shape')
    same(hashlib.sha256(weights.tobytes(order='C')).hexdigest(), case['target_array_SHA256'], 'original target bits')
    same(output['targets']['target_weight'].to_numpy().reshape(-1, 5).tobytes(order='C'), weights.tobytes(order='C'), 'restored original STATIC50/CSH target bits')
    accepted = (state/'RESULT.json').exists()
    result = read(state/'RESULT.json') if accepted else None
    if accepted:
        saved = read(state/'ACCOUNT.json')
        for key in ('summary', 'trades', 'funding', 'rejections', 'breaches', 'extrema', 'target_meta', 'protective_policy'):
            same(output[key], saved[key], 'saved ACCOUNT:' + key)
        same(output['targets'].to_dicts(), saved['targets'], 'saved all targets')
        same(output.get('liquidations', []), saved.get('liquidations', []), 'liquidation journal')
        same(port.fingerprint(output['minute']), read(state/'MINUTE_NUMERIC.json')['columns'], 'all saved minute numeric bits')
        same(result['genuine_state_hash'], sim.state_hash(), 'reported state hash')
    summary = output['summary']
    same(len(output['funding']), sim.event_cursor, 'funding cursor/journal count')
    required = (source['end']-source['start'])//MINUTE
    full = sim.rows_written == required
    paid = full and summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and bool(summary['terminal_cash_realized'])
    minute = output['minute']
    daily = minute.filter(port.native.pl.col('close_us') % DAY == 0)
    nav = np.r_[10000., daily['nav'].to_numpy()]
    returns = np.diff(nav)/nav[:-1]
    net = minute['net_signed_weight'].to_numpy()
    metrics = {'full_calendar': full, 'paid_flat': paid, 'paid_cash_PnL_USDT': summary['net_PnL'] if paid else None,
               'marked_PnL_USDT': summary['net_PnL'], 'marked_return': summary['net_PnL']/10000,
               'minute_drawdown': summary['all_observation_max_drawdown'],
               'mean_actual_gross': float(minute['gross_weight'].mean()) if sim.rows_written else None,
               'max_actual_gross': float(minute['gross_weight'].max()) if sim.rows_written else None,
               'completed_minutes': sim.rows_written, 'required_minutes': required,
               'completion': summary['completion'], 'account_status': summary['account_status'], 'stop_us': summary['stop_us'],
               'daily_observed_days': len(nav)-1,
               'annual_daily_vol_full_calendar_only': float(returns.std(ddof=1)*np.sqrt(365)) if full and len(returns)>1 else None,
               'worst_observed_30_days': float(np.min(nav[30:]/nav[:-30]-1)) if len(nav)>30 else None,
               'mean_actual_signed_net': float(net.mean()) if len(net) else None,
               'max_actual_abs_signed_net': float(np.abs(net).max()) if len(net) else None,
               'terminal_residual_quantity': {s: str(sim.account.positions[s].quantity) for s in source['symbols']},
               'terminal_residual_marked_notional_USDT': summary['terminal_signed_marked_notional'],
               'terminal_residual_gross_notional_USDT': summary['terminal_marked_notional'],
               'trade_legs': summary['trade_legs'],
               'rejection_counts': port.native.rejection_counts(output['rejections']),
               'halt_count': int(summary['account_status'] in ('BANKRUPT_HALT', 'LIQUIDATION_REQUIRED_HALT')),
               'liquidation_event_count': len(output.get('liquidations', [])),
               'status': 'COMPLETE_PAID_FLAT' if paid else 'FULL_NOT_PAID_OR_NOT_EVALUABLE' if full else 'STOP_PARTIAL',
               **{key: summary[key] for key in ('gross_PnL_same_quantities', 'gross_fill_turnover_USDT',
                   'fees_USDT', 'execution_cost_USDT', 'funding_USDT', 'risk_reduction_signal_count')}}
    if accepted:
        same(daily.write_csv().encode(), (state/'DAILY.csv').read_bytes(), 'all saved daily CSV bytes')
        same(result['case_id'], binding['case_id'], 'reported case')
        same((result['year'], result['arm'], result['mode']), (args.year, case['arm'], 'HEADROOM'), 'reported case factors')
        for key, value in metrics.items():
            if key in result:
                same(result[key], value, 'reported classification/metric:' + key)
        same(result['protective_policy'], output['protective_policy'], 'reported protective policy')
    _, inventory = port.native.episodes(output['trades'], tuple(source['symbols']))
    for s in source['symbols']:
        same(inventory[s], sim.account.positions[s].quantity, 'terminal signed inventory:' + s)
    bridge = port.native.nav_bridge(output['trades'], output['funding'], inventory,
                                   summary['terminal_mark_prices'], sim.account.nav())
    if accepted:
        same(bridge, result['independent_decimal_NAV_bridge'], 'saved old kernel Decimal NAV bridge')
    ledger = ledger_proof(sim.account, output, source)
    prefix = prefix_proof(output, case, baseline, old_pointer)
    same(input_hashes(state_root, state, pointer, baseline, old_pointer, case), before_files, 'all state/input files unchanged')
    receipt = {'case_id': binding['case_id'], 'status': 'PASS_COLD_RESTORE_ZERO_ADVANCE' if accepted else 'PASS_PARTIAL_COLD_RESTORE_ZERO_ADVANCE',
               'historical_wallets_opened': 0, 'financial_advances': 0, 'controls_rerun': 0,
               'state_hash': sim.state_hash(), 'day_chunks_sha_verified': len(pointer['chunks']), 'minute_rows_sha_verified': sim.rows_written,
               'all_snapshot_state_equal': True, 'all_financial_journals_equal_to_checkpoint': True,
               'saved_result_verified': accepted, 'original_account_cost_source_targets_binding_verified': True,
               'input_files_SHA256': before_files, 'metrics': metrics, 'summary': summary,
               'protective_policy': output['protective_policy'], 'rejection_counts': port.native.rejection_counts(output['rejections']),
               'old_kernel_decimal_NAV_bridge': bridge, 'live_economic_ledger_proof': ledger, 'original_financial_prefix_proof': prefix,
               'baseline_result': read(baseline/'RESULT.json'),
               'controller_case_receipt': controller['per_case'][binding['case_id']],
               'observer_code_SHA256': sha(__file__), 'reviewed_freeze_SHA256': FREEZE, 'review_receipt_SHA256': REVIEW}
    (HERE/'receipts').mkdir(exist_ok=True)
    target = HERE/'receipts'/(binding['case_id']+'.json')
    with target.open('x') as file:
        json.dump(receipt, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')
    print(json.dumps({'status': receipt['status'], 'case_id': binding['case_id'], 'metrics': metrics, 'prefix': prefix, 'receipt_SHA256': sha(target)}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--year', type=int, choices=(2021, 2023), required=True)
    parser.add_argument('--controller-released', action='store_true')
    main(parser.parse_args())
