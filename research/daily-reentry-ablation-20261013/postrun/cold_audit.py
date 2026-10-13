"""Zero-transition cold restore using only the new three-case dispatcher/class."""
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
        raise ValueError('Daily reentry cold mismatch: ' + label)


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
                'protective_policy', 'daily_reentry_policy'):
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
        'protective_policy': output['protective_policy'], 'daily_reentry_policy': output['daily_reentry_policy'],
        'daily_observed_days': output['minute'].filter(port.native.pl.col('close_us') % 86_400_000_000 == 0).height,
        'status': 'COMPLETE_PAID_FLAT' if paid else 'FULL_NOT_PAID_OR_NOT_EVALUABLE' if full else 'STOP_PARTIAL'}
    for key, expected in checks.items():
        same(result[key], expected, 'reported:' + key)


def verify_prefix(output, case, state, accepted):
    """Use frozen bit verifier; partial checkpoints prove only saved prefix."""
    from prefix_acceptance import verify_result_prefix, financial_prefix, compare_prefix, load_minute
    if accepted:
        proof = verify_result_prefix(output, case, ROOT)
        saved = read(state / 'PREFIX_ACCEPTANCE.json')
        same(proof, saved, 'runner mandatory prefix acceptance')
        same(proof, read(state / 'RESULT.json')['guard_prefix_acceptance'], 'result prefix acceptance')
        return proof, 'VERIFIED_RUNNER_ACCEPTANCE_EXACT'
    first = output['daily_reentry_policy']['first_same_direction_signal_us']
    if first is not None:
        proof = verify_result_prefix(output, case, ROOT)
        return proof, 'VERIFIED_PARTIAL_PREFIX_THROUGH_FIRST_SIGNAL_NO_RESULT_ACCEPTANCE'
    comparator = case['fine_comparators']['GUARD50']
    old_state = ROOT / comparator['state_locator']
    old_account = read(old_state / 'ACCOUNT.json')
    through = case['calendar'][0] + output['minute'].height * 60_000_000
    old_pointer = read(old_state / 'recovery/POINTER.json')
    if old_pointer['completed_minutes'] < output['minute'].height:
        raise ValueError('No-same-direction partial path exceeds saved guard horizon')
    new = financial_prefix(output['minute'].drop('close_us').to_numpy(), output['trades'], output['funding'],
                           start_us=case['calendar'][0], through_us=through)
    old = financial_prefix(load_minute(old_state / 'recovery'), old_account['trades'], old_account['funding'],
                           start_us=case['calendar'][0], through_us=through)
    proof = compare_prefix(new, old, through_us=through)
    proof.update(comparator_case_id=comparator['case_id'],
                 comparator_pointer_SHA256=comparator['files']['pointer']['SHA256'],
                 no_same_direction_signal_requires_full_path_identity=False,
                 scope='ALL_SAVED_COMPLETED_MINUTES_ONLY_NO_RUNNER_RESULT_ACCEPTANCE',
                 excludes_post_last_completed_minute_halt_marks=True)
    return proof, 'VERIFIED_SAVED_PARTIAL_PREFIX_NO_SAME_SIGNAL_NO_RESULT_ACCEPTANCE'


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
    guard_path = ROOT / 'coin_margin_protective_runner_20261013/run_guard_cases.py'
    spec = importlib.util.spec_from_file_location('reentry_cold_verified_transport', guard_path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    port, source, _unused_old_guard = guard.load_port(case['year'])
    sys.path[:0] = [str(MODULE), str(ROOT / 'coin_quantity_resolution_20261013')]
    from daily_reentry_policy import FreshDailyReentrySimulator
    from fine_account import FineGridAccount, profile_sha
    from build_report import reentry_entry_evidence
    same(binding['fine_account_class'], FineGridAccount.VERSION, 'fine account class')
    same(binding['fine_profile_SHA256'], profile_sha(), 'fine profile')
    same(binding['calendar'], [source['start'], source['end']], 'source calendar')
    same(binding['mode'], 'FRESH_DAILY_REENTRY', 'new mode')
    same(tuple(source['symbols']), tuple(case['symbols']), 'source symbol order')
    snapshot, pointer = port.restore_snapshot(state / 'recovery', binding)
    same(snapshot['mode'], 'LONG_SHORT', 'frozen simulation mode')
    same(snapshot['cost'], port.native.COSTS[0], 'frozen assumed cost')
    same(snapshot['unit'], port.native.UNITS[0], 'frozen assumed funding unit')
    same(snapshot['persist_cash_close'], False, 'cash-close convention')
    same(snapshot['final_day_target_zero'], False, 'terminal target convention')
    same(snapshot['target_meta'], {'kind': 'EXACT_FROZEN_THREE_PAIR_TARGET', 'binding': binding},
         'frozen target provenance')
    before_files = input_file_hashes(STATE, identity, pointer)
    with forbid_financial_transitions(FreshDailyReentrySimulator, FineGridAccount):
        sim = FreshDailyReentrySimulator.from_snapshot(snapshot, source, account_class=FineGridAccount)
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
    np.testing.assert_array_equal(output['targets']['target_weight'].to_numpy().reshape(-1, 5), weights)
    accepted = availability == 'ACCEPTED_RESULT'
    if accepted:
        verify_accepted_output(output, read(state / 'ACCOUNT.json'), read(state / 'RESULT.json'),
                               read(state / 'MINUTE_NUMERIC.json'), sim, port, source, identity)
    proof, proof_status = verify_prefix(output, case, state, accepted)
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
        'simulator_class': FreshDailyReentrySimulator.VERSION, 'account_class': FineGridAccount.VERSION,
        'availability': availability, 'controller_case_receipt': controller['per_case'][identity],
        'day_chunks_sha_verified': len(pointer['chunks']), 'minute_rows_sha_verified': sim.rows_written,
        'state_hash': sim.state_hash(), 'all_snapshot_state_equal': True,
        'all_journals_equal': True, 'all_targets_equal': True,
        'all_numeric_minute_bytes_equal_to_saved_result': True if accepted else None,
        'input_files_SHA256': before_files,
        'observed_summary': output['summary'],
        'observed_daily_reentry_policy': output['daily_reentry_policy'],
        'observed_protective_policy': output['protective_policy'],
        'observed_reentry_entry_evidence': reentry_entry_evidence(output['trades'],
            output['daily_reentry_policy'], output['protective_policy']),
        'observed_rejection_counts': port.native.rejection_counts(output['rejections']),
        'observed_journal_counts': {k: len(output[k]) for k in ('trades', 'funding', 'rejections', 'breaches', 'extrema')},
        'observed_terminal_residual_quantity': {s: str(sim.account.positions[s].quantity) for s in source['symbols']},
        'observed_minute_metrics': {
            'mean_actual_gross': float(output['minute']['gross_weight'].mean()) if sim.rows_written else None,
            'max_actual_gross': float(output['minute']['gross_weight'].max()) if sim.rows_written else None},
        'independent_decimal_NAV_bridge': bridge, 'prefix_financial_proof': proof,
        'prefix_financial_proof_verified': True, 'prefix_verification_status': proof_status,
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
