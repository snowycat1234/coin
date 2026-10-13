"""Minimal fixed-three-year report of saved SMA and exact old fine controls."""
from __future__ import annotations
import hashlib
from itertools import combinations
import json
import gate
import provenance as p
import report_helpers as h


def new_row(case, receipt, weights):
    identity = case['case_id'] + '_FINE_ORIGINAL'
    base = p.STATE / identity
    if receipt['status'] not in (h.FULL_COLD, h.PARTIAL_COLD):
        return {'case_id': identity, 'available': False, 'observation_class': 'UNAVAILABLE',
            'reason': receipt['status'], 'full_calendar': False, 'paid_flat': False,
            'annual_paid_return': None, 'paid_cash_PnL_USDT': None, 'completed_minutes': 0,
            'required_minutes': (case['calendar'][1] - case['calendar'][0]) // h.MINUTE}, None
    result = p.read(base / 'RESULT.json') if (base / 'RESULT.json').exists() else None
    summary = receipt['observed_summary']
    if result is not None and p.read(base / 'ACCOUNT.json')['summary'] != summary:
        raise ValueError('Cold receipt/account summary differs')
    numeric = p.read(base / 'MINUTE_NUMERIC.json') if result is not None else None
    metrics = h.stream_prefix(base / 'recovery', summary['completed_minutes'], weights,
        numeric=numeric, start_us=case['calendar'][0])
    if result is not None:
        h.verify_daily_csv(base / 'recovery', base / 'DAILY.csv', case['calendar'][0], numeric)
    row = h.observed_row(case, identity, summary, result, metrics,
        quantities=receipt['observed_terminal_residual_quantity'], rejections=receipt['observed_rejection_counts'],
        journals=receipt['observed_journal_counts'], bridge=receipt['independent_decimal_NAV_bridge'])
    row.update(new_historical_case=True, cold_receipt_SHA256=p.sha(p.HERE / 'receipts' / (identity + '.json')))
    return row, base / 'recovery'


def old_row(case, arm):
    ref = case['existing_fine_controls'][arm]
    base = p.safe_path(p.ROOT, ref['state_local_locator'])
    for name, digest in ref['files_SHA256'].items():
        p.pinned(p.safe_path(base, name), digest, 'bound old control:' + name)
    binding, account, result = (p.read(base / name) for name in ('BINDING.json', 'ACCOUNT.json', 'RESULT.json'))
    expected = {'case_id': ref['case_id'], 'year': case['year'], 'mode': 'ORIGINAL',
        'calendar': case['calendar'], 'capital_USDT': 10000, 'source_index_SHA256': case['source_index_SHA256'],
        'target_archive_SHA256': case['target_archive_SHA256'], 'fine_profile_SHA256': p.read(p.MODULE / 'CASE_BINDINGS.json')['fine_profile_SHA256'],
        'fine_account_SHA256': p.sha(p.ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'run_binding_SHA256': p.sha(p.OLD_STATE / 'RUN_BINDING.json'),
        'persist_cash_close': False, 'final_day_target_zero': False}
    if any(binding.get(k) != v for k, v in expected.items()) or account.get('protective_policy') is not None:
        raise ValueError('Old fine control pairing/protective classification differs')
    pointer = h.pointer_at(base / 'recovery')
    if (pointer['binding'] != binding or result['genuine_state_hash'] != pointer['state_hash']
            or result['completed_minutes'] != pointer['completed_minutes']):
        raise ValueError('Old control exact terminal pointer/result identity differs')
    p.pinned(p.safe_path(base / 'recovery', pointer['snapshot_path']), pointer['snapshot_SHA256'], 'old terminal snapshot')
    control_case = {**case, 'arm': binding['arm'], 'target_array_SHA256': binding['target_array_SHA256']}
    weights = h.load_weights(control_case)
    numeric = p.read(base / 'MINUTE_NUMERIC.json')
    metrics = h.stream_prefix(base / 'recovery', result['completed_minutes'], weights,
        numeric=numeric, start_us=case['calendar'][0])
    h.verify_daily_csv(base / 'recovery', base / 'DAILY.csv', case['calendar'][0], numeric)
    bridge = h.journal_reconciliation(account, result, case['symbols'])
    rejections = {}
    for row in account['rejections']:
        reason = row.get('reason') or row.get('status') or 'UNKNOWN'
        rejections[reason] = rejections.get(reason, 0) + 1
    if rejections != result['rejection_counts']:
        raise ValueError('Saved control rejection counts differ')
    row = h.observed_row(case, ref['case_id'], account['summary'], result, metrics,
        quantities=result['terminal_residual_quantity'], rejections=rejections,
        journals={key: len(account[key]) for key in ('trades', 'funding', 'rejections', 'breaches', 'extrema')}, bridge=bridge)
    row.update(new_historical_case=False, old_wallet_restores=0, old_wallet_reruns=0,
        control_alias=arm, frozen_arm=binding['arm'], result_SHA256=p.sha(base / 'RESULT.json'))
    return row, base / 'recovery', weights


def pair(a, b, ar, br, aw, bw, start_us):
    result = h.contrast(a, b)
    result.update(a_case_id=a['case_id'], b_case_id=b['case_id'], delta_direction='b_minus_a')
    if result['unequal_or_partial_horizon_needs_common_prefix'] and ar is not None and br is not None:
        prefix = h.common_prefix({'a': a, 'b': b}, {'a': ar, 'b': br}, {'a': aw, 'b': bw}, start_us=start_us)
        prefix.update(h.prefix_deltas(prefix, 'a', 'b'))
        result['common_observed_minute_prefix'] = prefix
    else:
        result['common_observed_minute_prefix'] = None
    return result


def render_summary(report):
    lines = ['# Fine SMA completion and existing fine controls', '',
        'All three fixed SMA cases and all six existing fine controls are retained.',
        'Paid cash needs a complete calendar and exact zero residual quantity. Halted or residual endpoints are marked; unequal horizons use completed-minute prefixes.', '']
    for year in report['years']:
        lines.append('## ' + str(year['year']))
        for arm, row in year['cases'].items():
            if not row['available']:
                lines.append(f'- {arm}: unavailable ({row["reason"]})')
            else:
                lines.append(f'- {arm}: {row["observation_class"]}; {row["completed_minutes"]}/{row["required_minutes"]} minutes; marked PnL {row["marked_PnL_USDT"]:.6f} USDT; paid PnL {row["paid_cash_PnL_USDT"]}; DD {row["minute_drawdown"]:.6%}; account {row["account_status"]}; exact quantities ' + json.dumps(row['terminal_residual_quantity'], sort_keys=True))
        for label, row in year['comparisons'].items():
            prefix = row['common_observed_minute_prefix']
            if row['same_full_calendar']:
                lines.append(f'- {label}: paid PnL delta {row["paid_cash_PnL_delta_USDT"]}; same-calendar marked PnL delta {row["same_full_calendar_observed_deltas"]["marked_PnL_USDT"]}')
            elif prefix is not None:
                lines.append(f'- {label}: {prefix["common_completed_minutes"]} common completed minutes; marked prefix PnL delta {prefix["b_minus_a"]["last_completed_minute_marked_PnL_USDT"]}; annual/paid delta unavailable')
            else:
                lines.append(f'- {label}: common prefix unavailable; annual/paid delta unavailable')
        lines.append('')
    lines.append(report['interpretation'])
    return '\n'.join(lines) + '\n'


def main():
    gate.require_bounded_worker('REPORT')
    p.verify_terminal_run()
    before = p.read(p.HERE / 'TERMINAL_INPUTS.json')
    plan = p.read(p.MODULE / 'CASE_BINDINGS.json')
    audit = p.read(p.HERE / 'AUDIT_RESOURCE_RECEIPTS.json')
    h.verify_audit_stage(audit, manifest_sha=p.sha(p.HERE / 'REVIEWED_POSTRUN_CODE.json'),
        terminal_inputs_sha=p.sha(p.HERE / 'TERMINAL_INPUTS.json'), run_binding_sha=p.sha(p.STATE / 'RUN_BINDING.json'),
        controller_sha=p.sha(p.STATE / 'RESOURCE_RECEIPTS.json'), state_locator=str(p.STATE.relative_to(p.ROOT)))
    if {path.stem for path in (p.HERE / 'receipts').glob('*.json')} != set(p.CASE_IDS):
        raise ValueError('Exactly three new cold/unavailable receipts required')
    years = []
    for case in plan['cases']:
        identity = case['case_id'] + '_FINE_ORIGINAL'
        receipt = p.read(p.HERE / 'receipts' / (identity + '.json'))
        h.verify_receipt(identity, receipt, audit)
        weights = {'SMA200_10PCT': h.load_weights(case)}
        rows, recoveries = {}, {}
        rows['SMA200_10PCT'], recoveries['SMA200_10PCT'] = new_row(case, receipt, weights['SMA200_10PCT'])
        for arm in ('STATIC50', 'EXACTHALF'):
            rows[arm], recoveries[arm], weights[arm] = old_row(case, arm)
        comparisons = {b + '_minus_' + a: pair(rows[a], rows[b], recoveries[a], recoveries[b], weights[a], weights[b], case['calendar'][0])
            for a, b in combinations(('STATIC50', 'SMA200_10PCT', 'EXACTHALF'), 2)}
        years.append({'year': case['year'], 'calendar': case['calendar'], 'cases': rows, 'comparisons': comparisons})
    p.verify_terminal_run()
    if before != p.read(p.HERE / 'TERMINAL_INPUTS.json'):
        raise ValueError('Terminal pins changed during report')
    report = {'kind': 'FIXED_THREE_FINE_SMA_PLUS_EXISTING_FINE_CONTROLS', 'new_case_ids': list(p.CASE_IDS),
        'all_predeclared_cases_retained': True, 'no_result_based_omission': True, 'years': years,
        'financial_advances': 0, 'new_wallets_opened_by_observer': 0, 'old_wallets_restored': 0, 'old_wallets_rerun': 0,
        'observer_manifest_SHA256': p.sha(p.HERE / 'REVIEWED_POSTRUN_CODE.json'),
        'terminal_inputs_SHA256': p.sha(p.HERE / 'TERMINAL_INPUTS.json'),
        'audit_resource_receipt_SHA256': p.sha(p.HERE / 'AUDIT_RESOURCE_RECEIPTS.json'),
        'interpretation': 'Conditional already-seen development simulation. Original frozen targets and fine-grid sensitivity remain unchanged. RAW_AS_FRACTION funding is conditional. No alpha, OOS, native-grid or venue-execution certification claim. No free terminal close; no annual return comparison across partial horizons.'}
    for name in ('RESULTS_COMPACT.json', 'SUMMARY.md'):
        if (p.HERE / name).exists():
            raise FileExistsError('Never overwrite report outputs')
    summary = render_summary(report)
    h.save_new(p.HERE / 'RESULTS_COMPACT.json', report)
    with (p.HERE / 'SUMMARY.md').open('x') as file:
        file.write(summary)
    print('FIXED_THREE_YEAR_FINE_SMA_REPORT_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
