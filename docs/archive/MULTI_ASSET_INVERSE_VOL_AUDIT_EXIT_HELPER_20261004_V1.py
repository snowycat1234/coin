"""Archive one already completed D052 audit's small metadata; no financial replay."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
CODE = 'scripts/investment/multi_asset_financial_audit.py'
CODE_ARCHIVE = 'docs/archive/MULTI_ASSET_INVERSE_VOL_FINANCIAL_AUDITOR_20261004_V1.py'
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', choices=('september', 'october'), required=True)
    parser.add_argument('--report-sha256', required=True)
    parser.add_argument('--host-session', type=int, required=True)
    parser.add_argument('--host-chunk', required=True)
    args = parser.parse_args()
    assert os.environ.get('COIN_TASK_ID') and sha(ROOT / GUARD) == GUARD_SHA
    module_spec = importlib.util.spec_from_file_location('d052_completed_metadata_guard', ROOT / GUARD)
    guard = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = guard
    module_spec.loader.exec_module(guard)
    month = args.month.upper()
    run = STATE / f'd052-inverse-vol-{args.month}-financial-20261004-v1'
    report = f'reports/fast_research/MULTI_ASSET_INVERSE_VOL_{month}_INDEPENDENT_20261004_V1.json'
    audit, report_sha = guard.small(ROOT / report, args.report_sha256)
    assert audit['status'] == 'PASS_CONFIGURED_N_SHARED_PERPETUAL_RECORDED_ACCOUNTING_AND_TARGET_SCOPE_NOT_NATIVE_OR_APR'
    assert audit['completed_cases_verified'] == audit['financial_case_calls'] == audit['completed_full_calendar_cases_verified'] == 4
    assert audit['incomplete_or_halted_cases_verified'] == 0
    assert audit['allocation'] == 'INVERSE_VOL_30D'
    task = guard.closed(audit['binding']['task_id'])
    plan, plan_sha = guard.small(run / 'ACTUAL_BINDING.json', audit['binding']['ACTUAL_BINDING_sha256'])
    rb, rb_sha = guard.small(run / 'RUN_BINDING.json', audit['run_binding_sha256'])
    assert rb == audit['binding'] and plan['required_scope'] == audit['required_scope']
    assert audit['complete_period_days'] == (30 if args.month == 'september' else 31)
    assert sha(ROOT / CODE) == sha(ROOT / CODE_ARCHIVE) == audit['independent_source_sha256'] == plan['checker_sha256']
    assert audit['maximum_errors']['cash'] <= 1e-7 and audit['maximum_errors']['ratio'] <= 1e-10
    actual, _ = guard.small(ROOT / plan['actual_report'], plan['actual_report_sha256'])
    originals = {c['id']: c for c in actual['cases']}
    assert set(originals) == {c['id'] for c in audit['cases']}
    terminal = []
    for case in audit['cases']:
        observed = originals[case['id']]['summary']
        assert case['terminal_cash_realized'] == observed['terminal_cash_realized']
        terminal.append(dict(id=case['id'], complete_calendar_verified=case['complete_calendar_verified'],
            terminal_cash_realized=case['terminal_cash_realized'],
            marked_net_PnL_USDT=case['summary']['net_PnL'], unrealized_PnL_USDT=case['summary']['unrealized_PnL'],
            terminal_marked_notional_USDT=case['actual_terminal_marked_notional'],
            terminal_signed_quantities_from_verified_producer={s: p['quantity']
                for s, p in observed['positions'].items() if p['quantity']},
            liquidated_return_evaluable=case['terminal_cash_realized']))
    directory = ROOT / f'docs/archive/MULTI_ASSET_INVERSE_VOL_{month}_INDEPENDENT_USED_METADATA_20261004_V1'
    directory.mkdir()
    archives = {}
    for source, name in [(run / 'ACTUAL_BINDING.json', 'ACTUAL_BINDING.json'),
                         (run / 'RUN_BINDING.json', 'RUN_BINDING.json'),
                         (Path(task['path']), 'COMPLETED_TASK.json')]:
        destination = directory / name
        with destination.open('xb') as stream:
            stream.write(source.read_bytes())
        assert sha(destination) == sha(source)
        archives[str(destination.relative_to(ROOT))] = sha(destination)
    helper = ROOT / 'docs/archive/MULTI_ASSET_INVERSE_VOL_AUDIT_EXIT_HELPER_20261004_V1.py'
    if helper.exists():
        assert not helper.is_symlink() and sha(helper) == sha(__file__)
    else:
        with helper.open('xb') as stream:
            stream.write(Path(__file__).read_bytes())
    hashes = {CODE: sha(ROOT / CODE), CODE_ARCHIVE: sha(ROOT / CODE_ARCHIVE), GUARD: GUARD_SHA,
              str(helper.relative_to(ROOT)): sha(helper), **archives}
    result = dict(status='PASS_REAL_EXIT0_METADATA_FOR_D052_INVERSE_VOL_RECORDED_FINANCE_NOT_NATIVE_OR_APR',
        binding=dict(task_id=os.environ['COIN_TASK_ID'], source_hashes=hashes),
        actual_audit_task=task, actual_audit_exit_code=0,
        actual_host_session=args.host_session, actual_host_chunk=args.host_chunk,
        audit_report=dict(path=report, sha256=report_sha, status=audit['status']),
        checker_sha256=audit['independent_source_sha256'], ACTUAL_BINDING_sha256=plan_sha,
        RUN_BINDING_sha256=rb_sha, protocol_path=plan['protocol_path'], protocol_sha256=plan['protocol_sha256'],
        actual_reports=audit['binding']['actual_reports'], required_scope=audit['required_scope'],
        allocation=audit['allocation'], completed_cases_verified=4, financial_case_calls=4,
        calendar_complete_cases=4, terminal_cash_realized_cases=sum(c['terminal_cash_realized'] for c in audit['cases']),
        terminal_inventory=terminal, completed_source_files_verified=audit['completed_source_files_verified'],
        completed_minutes_verified=audit['completed_minutes_verified'], completed_days_verified=audit['completed_days_verified'],
        completed_months_verified=audit['completed_months_verified'], tolerances=audit['tolerances'],
        maximum_errors=audit['maximum_errors'], elapsed_seconds=audit['elapsed_seconds'], peak_RSS_bytes=audit['peak_RSS_bytes'],
        payloads_or_financial_math_reread=False, investment_qualification_pass=False,
        native_filters_or_funding_units_or_full_quantity_sizing_or_APR_certified=False)
    out = ROOT / f'reports/fast_research/MULTI_ASSET_INVERSE_VOL_{month}_INDEPENDENT_ACTUAL_EXIT_20261004_V1.json'
    guard.write(out, result)
    print(json.dumps(dict(output=str(out), sha256=sha(out), audit_task=task['task']['id'], actual_exit_code=0)))


if __name__ == '__main__':
    main()
