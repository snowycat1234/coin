"""Archive already completed October N10 marked-NAV audit metadata; no financial reads."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
RUN = STATE / 'd051-october-n10-financial-independent-20261004-v2'
REPORT = 'reports/fast_research/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_INDEPENDENT_20261004_V2.json'
CODE = 'scripts/investment/multi_asset_financial_audit.py'
CODE_ARCHIVE = 'docs/archive/MULTI_ASSET_FINANCIAL_AUDIT_USED_OCTOBER_N10_20261004_V2.py'
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert os.environ.get('COIN_TASK_ID') and sha(ROOT / GUARD) == GUARD_SHA
spec = importlib.util.spec_from_file_location('d051_n10_metadata_exit_guard', ROOT / GUARD)
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)
audit, report_sha = guard.small(ROOT / REPORT, 'a8f8ddb3f46556eb99ecfae39cceaaa4f2718cc0148f2da528db8eb01b23c204')
assert audit['status'] == 'PASS_CONFIGURED_N_SHARED_PERPETUAL_RECORDED_ACCOUNTING_AND_TARGET_SCOPE_NOT_NATIVE_OR_APR'
assert audit['completed_cases_verified'] == audit['financial_case_calls'] == audit['completed_full_calendar_cases_verified'] == 4
assert audit['incomplete_or_halted_cases_verified'] == 0 and audit['complete_period_days'] == 31
assert sum(c['terminal_cash_realized'] for c in audit['cases']) == 0
task = guard.closed(audit['binding']['task_id'])
binding, binding_sha = guard.small(RUN / 'ACTUAL_BINDING.json', audit['binding']['ACTUAL_BINDING_sha256'])
rb, rb_sha = guard.small(RUN / 'RUN_BINDING.json', audit['run_binding_sha256'])
assert rb == audit['binding'] and binding['required_scope'] == audit['required_scope']
assert sha(ROOT / CODE) == sha(ROOT / CODE_ARCHIVE) == audit['independent_source_sha256'] == binding['checker_sha256']
assert audit['maximum_errors']['cash'] <= 1e-7 and audit['maximum_errors']['ratio'] <= 1e-10
actual, actual_sha = guard.small(ROOT / binding['actual_report'], binding['actual_report_sha256'])
original = {c['id']: c for c in actual['cases']}
assert set(original) == {c['id'] for c in audit['cases']}
terminal = []
for case in audit['cases']:
    observed = original[case['id']]['summary']
    assert case['complete_calendar_verified'] and not observed['terminal_cash_realized']
    terminal.append(dict(id=case['id'], complete_calendar_verified=True,
        terminal_cash_realized=False, marked_net_PnL_USDT=case['summary']['net_PnL'],
        unrealized_PnL_USDT=case['summary']['unrealized_PnL'],
        terminal_marked_notional_USDT=case['actual_terminal_marked_notional'],
        terminal_signed_quantities_from_verified_producer={s:p['quantity']
            for s,p in observed['positions'].items() if p['quantity']},
        liquidated_return='NOT_EVALUABLE_UNEXECUTABLE_TERMINAL_EXIT',
        original_producer_completion_label=observed['completion'],
        interpretation='FULL_CALENDAR_MARKED_NAV_NOT_LIQUIDATED_CAPITAL'))
directory = ROOT / 'docs/archive/MULTI_ASSET_OCTOBER_N10_INDEPENDENT_USED_METADATA_20261004_V2'
directory.mkdir()
copies = [(RUN / 'ACTUAL_BINDING.json', 'ACTUAL_BINDING.json'),
          (RUN / 'RUN_BINDING.json', 'RUN_BINDING.json'),
          (Path(task['path']), 'COMPLETED_TASK.json')]
archives = {}
for source, name in copies:
    destination = directory / name
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())
    assert sha(destination) == sha(source)
    archives[str(destination.relative_to(ROOT))] = sha(destination)
for source, name in [(Path(__file__), 'MULTI_ASSET_OCTOBER_N10_INDEPENDENT_EXIT_HELPER_20261004_V2.py'),
                     (ROOT / '.cache/d051_n10_audit_bind_20261004_v2.py', 'MULTI_ASSET_OCTOBER_N10_INDEPENDENT_BINDER_20261004_V2.py')]:
    destination = ROOT / 'docs/archive' / name
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())
    assert sha(destination) == sha(source)
    archives[str(destination.relative_to(ROOT))] = sha(destination)
source_hashes = {CODE: sha(ROOT / CODE), CODE_ARCHIVE: sha(ROOT / CODE_ARCHIVE), GUARD: GUARD_SHA, **archives}
result = dict(status='PASS_REAL_EXIT0_METADATA_FOR_OCTOBER_N10_MARKED_FINANCE_NOT_LIQUIDATED_RETURN',
    binding=dict(task_id=os.environ['COIN_TASK_ID'], source_hashes=source_hashes),
    actual_audit_task=task, actual_audit_exit_code=0, actual_host_session=1754, actual_host_chunk='796752',
    audit_report=dict(path=REPORT, sha256=report_sha, status=audit['status']),
    checker_sha256=audit['independent_source_sha256'], ACTUAL_BINDING_sha256=binding_sha,
    RUN_BINDING_sha256=rb_sha, protocol_path=binding['protocol_path'], protocol_sha256=binding['protocol_sha256'],
    actual_reports=audit['binding']['actual_reports'], required_scope=audit['required_scope'],
    completed_cases_verified=4, financial_case_calls=4,
    calendar_complete_cases=4, terminal_cash_realized_cases=0,
    terminal_inventory=terminal, liquidated_return='NOT_EVALUABLE_UNEXECUTABLE_TERMINAL_EXIT',
    investment_qualification_pass=False, original_metadata_failed_audit_preserved=binding['prior_failure'],
    completed_source_files_verified=audit['completed_source_files_verified'],
    completed_minutes_verified=audit['completed_minutes_verified'],
    completed_days_verified=audit['completed_days_verified'],
    completed_months_verified=audit['completed_months_verified'], tolerances=audit['tolerances'],
    maximum_errors=audit['maximum_errors'], elapsed_seconds=audit['elapsed_seconds'],
    peak_RSS_bytes=audit['peak_RSS_bytes'], payloads_or_financial_math_reread=False,
    native_filters_or_funding_units_or_full_quantity_sizing_or_APR_certified=False)
out = ROOT / 'reports/fast_research/MULTI_ASSET_OCTOBER_TEN_PORTFOLIO_INDEPENDENT_ACTUAL_EXIT_20261004_V2.json'
guard.write(out, result)
print(json.dumps(dict(output=str(out), sha256=sha(out), audit_task=task['task']['id'], actual_exit_code=0,
    source_hashes=source_hashes)))
