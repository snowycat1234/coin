"""Zero-transition cold restore using only the fixed three-case dispatcher/original class."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from provenance import (HERE, ROOT, MODULE, STATE, CASE_IDS, sha, read,
    verify_terminal_run, dispatch_case, verify_case_binding, input_file_hashes, case_availability)
from gate import require_bounded_worker


def same(a, b, label):
    if a != b:
        raise ValueError('Fine SMA cold mismatch: ' + label)


@contextmanager
def forbid_financial_transitions(simulator, account_class):
    """Restore may read tape, but it may never mark, fund, fill, or advance."""
    names = ((simulator, ('advance_day', 'schedule', 'attempt', 'funding_through',
                          'risk_schedule', 'observe')),
             (account_class, ('execute_fill', 'apply_funding', 'update_marks')))
    previous = []
    def forbidden(*args, **kwargs):
        raise RuntimeError('Cold audit cannot execute a financial transition')
    try:
        for cls, methods in names:
            for name in methods:
                previous.append((cls, name, cls.__dict__.get(name), name in cls.__dict__))
                setattr(cls, name, forbidden)
        yield
    finally:
        for cls, name, value, owned in reversed(previous):
            if owned:
                setattr(cls, name, value)
            else:
                delattr(cls, name)


def verify_snapshot_state(sim, snapshot, pointer, binding):
    same(pointer['binding'], binding, 'pointer binding')
    same(sim.state_hash(), pointer['state_hash'], 'restored state hash')
    same(sim.cursor, pointer['cursor'], 'cursor')
    same(sim.stop, pointer['stop'], 'stop')
    same(sim.rows_written, pointer['completed_minutes'], 'minute rows')
    same(sum(r['rows'] for r in pointer['chunks']), sim.rows_written, 'saved day rows')
    same(sim.account.snapshot(), snapshot['account'], 'all exact account state and journals')
    for key, value in snapshot['state'].items():
        expected = deepcopy(value)
        if key == 'pending':
            from decimal import Decimal
            expected = {s: {**order, 'target': Decimal(order['target'])}
                        for s, order in value.items()}
        elif key in ('weights', 'decision_kinds'):
            expected = {int(stamp): rows for stamp, rows in value.items()}
        same(getattr(sim, key), expected, 'scheduler snapshot state:' + key)


def verify_accepted_output(output, saved, result, numeric, sim, port, source, identity):
    summary = output['summary']
    same(output['summary'], saved['summary'], 'account summary')
    for key in ('trades', 'funding', 'rejections', 'breaches', 'extrema', 'target_meta',
                'protective_policy'):
        same(output.get(key), saved.get(key), 'account journal:' + key)
    same(output['targets'].to_dicts(), saved['targets'], 'all target rows')
    same(output.get('liquidations', []), saved.get('liquidations', []), 'liquidation journal')
    same(port.fingerprint(output['minute']), numeric['columns'], 'all numeric minute bytes')
    same(result['case_id'], identity, 'result case')
    same(result['genuine_state_hash'], sim.state_hash(), 'result state hash')
    required = (source['end'] - source['start']) // 60_000_000
    full = summary['completed_minutes'] == required
    paid = full and summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and bool(summary['terminal_cash_realized'])
    checks = {'full_calendar': full, 'paid_flat': paid, 'completed_minutes': sim.rows_written,
        'required_minutes': required, 'stop_us': summary['stop_us'],
        'paid_cash_PnL_USDT': summary['net_PnL'] if paid else None,
        'marked_PnL_USDT': summary['net_PnL'], 'marked_return': summary['net_PnL'] / 10000,
        'minute_drawdown': summary['all_observation_max_drawdown'],
        'mean_actual_gross': float(output['minute']['gross_weight'].mean()) if sim.rows_written else None,
        'max_actual_gross': float(output['minute']['gross_weight'].max()) if sim.rows_written else None,
        'trade_legs': summary['trade_legs'],
        'rejection_counts': port.native.rejection_counts(output['rejections']),
        'terminal_residual_gross_notional_USDT': summary['terminal_marked_notional'],
        'terminal_residual_marked_notional_USDT': summary['terminal_signed_marked_notional'],
        'terminal_residual_quantity': {s: str(sim.account.positions[s].quantity) for s in source['symbols']},
        'halt_count': int(summary['account_status'] in ('BANKRUPT_HALT', 'LIQUIDATION_REQUIRED_HALT')),
        'liquidation_event_count': len(output.get('liquidations', [])),
        'completion': summary['completion'], 'account_status': summary['account_status'],
        'protective_policy': output.get('protective_policy'),
        'daily_observed_days': output['minute'].filter(port.native.pl.col('close_us') % 86_400_000_000 == 0).height,
        'status': 'COMPLETE_PAID_FLAT' if paid else 'FULL_NOT_PAID_OR_NOT_EVALUABLE' if full else 'STOP_PARTIAL'}
    import numpy as np
    minute=output['minute']
    daily=minute.filter(port.native.pl.col('close_us') % 86_400_000_000 == 0)
    nav=np.r_[10000.,daily['nav'].to_numpy()]
    returns=np.diff(nav)/nav[:-1]
    net=(sum(minute[f'{symbol}_signed_marked_notional'].to_numpy() for symbol in source['symbols']) / minute['nav'].to_numpy() if sim.rows_written else np.array([]))
    checks.update(mode='ORIGINAL',year=int(identity[1:5]),
        arm=identity[6:-len('_FINE_ORIGINAL')],
        annual_daily_vol=float(returns.std(ddof=1)*np.sqrt(365)) if full and len(returns)>1 else None,
        worst_observed_30_days=float(np.min(nav[30:]/nav[:-30]-1)) if len(nav)>30 else None,
        mean_actual_signed_net=float(net.mean()) if len(net) else None,
        max_actual_abs_signed_net=float(np.abs(net).max()) if len(net) else None)
    for key in ('gross_fill_turnover_USDT','fees_USDT','execution_cost_USDT','funding_USDT','risk_reduction_signal_count'):
        checks[key]=summary[key]
    for key, expected in checks.items():
        same(result[key], expected, 'reported:' + key)


def main(identity):
    if sys.flags.optimize:
        raise RuntimeError('Assertions must stay enabled')
    require_bounded_worker('AUDIT')
    plan = read(MODULE / 'CASE_BINDINGS.json')
    verify_terminal_run(state=STATE, module=MODULE, plan=plan)
    case = dispatch_case(identity, plan)
    controller = read(STATE / 'RESOURCE_RECEIPTS.json')
    availability = case_availability(STATE, identity, controller)
    if availability in ('UNSTARTED_NO_WALLET', 'STARTED_NO_RECOVERABLE_CHECKPOINT'):
        raise RuntimeError('No recoverable wallet to cold-restore: ' + availability)
    state = STATE / identity
    binding = read(state / 'BINDING.json')
    verify_case_binding(binding, identity, case)
    # Verify bootstrap/source before loading the exact frozen transport. The
    # transport installs quant/repository imports before FineGridAccount import.
    sys.path[:0] = [str(MODULE), str(ROOT / 'coin_quantity_resolution_20261013')]
    spec = importlib.util.spec_from_file_location('sma_fine_cold_transport', ROOT / 'coin_margin_protective_runner_20261013/run_guard_cases.py')
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    port, source, _unused_guard = transport.load_port(case['year'])
    Simulator=port.native.NativeDailySimulator
    from fine_account import FineGridAccount, profile_sha
    same(binding['fine_account_class'], FineGridAccount.VERSION, 'fine account class')
    same(binding['fine_profile_SHA256'], profile_sha(), 'fine profile')
    same(binding['calendar'], [source['start'], source['end']], 'source calendar')
    same(binding['mode'], 'ORIGINAL', 'frozen mode')
    same(tuple(source['symbols']), tuple(case['symbols']), 'source symbol order')
    snapshot, pointer = port.restore_snapshot(state / 'recovery', binding)
    same(snapshot['mode'], 'LONG_SHORT', 'frozen simulation mode')
    same(snapshot['cost'], port.native.COSTS[0], 'frozen assumed cost')
    same(snapshot['unit'], port.native.UNITS[0], 'frozen assumed funding unit')
    same(snapshot['persist_cash_close'], False, 'cash-close convention')
    same(snapshot['final_day_target_zero'], False, 'terminal target convention')
    same(snapshot['target_meta'], {'kind': 'EXACT_FROZEN_ORIGINAL_SMA200_10PCT_TARGET', 'binding': binding},
         'frozen target provenance')
    before_files = input_file_hashes(STATE, identity, pointer)
    with forbid_financial_transitions(Simulator, FineGridAccount):
        sim = Simulator.from_snapshot(snapshot, source, account_class=FineGridAccount)
        if type(sim.account) is not FineGridAccount:
            raise ValueError('Restored wrong account class')
        verify_snapshot_state(sim, snapshot, pointer, binding)
        output = sim.result()
        same(sim.state_hash(), pointer['state_hash'], 'result is read-only')
    import numpy as np
    with np.load(ROOT / case['target_archive_local_locator'], allow_pickle=False) as archive:
        clocks = archive['decision_us'].copy()
        weights = archive[case['arm']].copy()
    np.testing.assert_array_equal(clocks, np.arange(source['start'], source['end'], 86_400_000_000))
    same(__import__('hashlib').sha256(weights.tobytes(order='C')).hexdigest(),
         case['target_array_SHA256'], 'target array raw bytes')
    restored_weights=output['targets']['target_weight'].to_numpy().reshape(-1,5)
    same(restored_weights.tobytes(order='C'),weights.tobytes(order='C'),'all frozen target raw bits including signed zero')
    accepted = availability == 'ACCEPTED_RESULT'
    if accepted:
        same(output['minute'].filter(port.native.pl.col('close_us') % 86_400_000_000 == 0).write_csv(),
             (state / 'DAILY.csv').read_text(), 'all daily CSV bytes')
        verify_accepted_output(output, read(state / 'ACCOUNT.json'), read(state / 'RESULT.json'),
                               read(state / 'MINUTE_NUMERIC.json'), sim, port, source, identity)
    _, inventory = port.native.episodes(output['trades'], tuple(source['symbols']))
    for symbol in source['symbols']:
        same(inventory[symbol], sim.account.positions[symbol].quantity, 'signed inventory:' + symbol)
    bridge = port.native.nav_bridge(output['trades'], output['funding'], inventory,
        output['summary']['terminal_mark_prices'], sim.account.nav())
    if accepted:
        same(bridge, read(state / 'RESULT.json')['independent_decimal_NAV_bridge'], 'frozen Decimal NAV bridge')
    same(input_file_hashes(STATE, identity, pointer), before_files, 'all input files unchanged')
    receipt = {'case_id': identity,
        'status': 'PASS_COLD_RESTORE_ZERO_ADVANCE' if accepted else 'PASS_PARTIAL_COLD_RESTORE_ZERO_ADVANCE',
        'financial_advances': 0, 'historical_wallets_opened': 0, 'controls_rerun': 0,
        'simulator_class': Simulator.__name__, 'account_class': FineGridAccount.VERSION,
        'availability': availability, 'controller_case_receipt': controller['per_case'][identity],
        'day_chunks_sha_verified': len(pointer['chunks']), 'minute_rows_sha_verified': sim.rows_written,
        'state_hash': sim.state_hash(), 'all_snapshot_state_equal': True,
        'all_journals_equal': True, 'all_targets_equal': True,
        'all_numeric_minute_bytes_equal_to_saved_result': True if accepted else None,
        'all_daily_bytes_equal_to_saved_result': True if accepted else None,
        'input_files_SHA256': before_files,
        'observed_summary': output['summary'],
        'observed_protective_policy': output.get('protective_policy'),
        'observed_rejection_counts': port.native.rejection_counts(output['rejections']),
        'observed_journal_counts': {k: len(output[k]) for k in ('trades', 'funding', 'rejections', 'breaches', 'extrema')},
        'observed_terminal_residual_quantity': {s: str(sim.account.positions[s].quantity) for s in source['symbols']},
        'observed_minute_metrics': {
            'mean_actual_gross': float(output['minute']['gross_weight'].mean()) if sim.rows_written else None,
            'max_actual_gross': float(output['minute']['gross_weight'].max()) if sim.rows_written else None},
        'independent_decimal_NAV_bridge': bridge, 'frozen_targets_raw_bytes_verified': True,
        'runner_RESULT_acceptance_present': accepted,
        'runner_SHA256': sha(MODULE / 'run_cases.py'),
        'fine_account_SHA256': sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'observer_manifest_SHA256': sha(HERE / 'REVIEWED_POSTRUN_CODE.json'),
        'postrun_GO_SHA256': sha(HERE / 'POSTRUN_GO.json')}
    receipts = HERE / 'receipts'
    receipts.mkdir(exist_ok=True)
    with (receipts / (identity + '.json')).open('x') as file:
        json.dump(receipt, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')
    print(receipt['status'], identity, 'minutes', sim.rows_written, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case_id', choices=CASE_IDS)
    main(parser.parse_args().case_id)
