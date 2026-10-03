"""Only close and archive already completed N10 audit metadata; no journals."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
RUN = STATE / 'd050-n10-financial-independent-20261004'
REPORT = 'reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_INDEPENDENT_20261004.json'
CODE = 'scripts/investment/multi_asset_financial_audit.py'
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert os.environ.get('COIN_TASK_ID') and sha(ROOT / GUARD) == GUARD_SHA
spec = importlib.util.spec_from_file_location('d050_metadata_exit_guard', ROOT / GUARD)
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)
audit, report_sha = guard.small(ROOT / REPORT, '05d705e4e260941d8b4801a1701e11d0f56791a85f20400aba2b78484e76535f')
assert audit['status'] == 'PASS_CONFIGURED_N_SHARED_PERPETUAL_RECORDED_ACCOUNTING_AND_TARGET_SCOPE_NOT_NATIVE_OR_APR'
assert audit['completed_cases_verified'] == audit['financial_case_calls'] == audit['completed_full_calendar_cases_verified'] == 4
assert audit['incomplete_or_halted_cases_verified'] == 0
task = guard.closed(audit['binding']['task_id'])
binding, binding_sha = guard.small(RUN / 'ACTUAL_BINDING.json', audit['binding']['ACTUAL_BINDING_sha256'])
run_binding, rb_sha = guard.small(RUN / 'RUN_BINDING.json', audit['run_binding_sha256'])
assert run_binding == audit['binding'] and sha(ROOT / CODE) == audit['independent_source_sha256'] == binding['checker_sha256']
assert audit['maximum_errors']['cash'] <= 1e-7 and audit['maximum_errors']['ratio'] <= 1e-10
directory = ROOT / 'docs/archive/MULTI_ASSET_N10_INDEPENDENT_USED_METADATA_20261004'
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
source_hashes = {CODE: sha(ROOT / CODE), GUARD: GUARD_SHA,
    'docs/archive/MULTI_ASSET_FINANCIAL_AUDIT_USED_N2_20261004.py': audit['independent_source_sha256'],
    **archives}
helper = ROOT / 'docs/archive/MULTI_ASSET_N10_INDEPENDENT_EXIT_HELPER_20261004.py'
with helper.open('xb') as stream:
    stream.write(Path(__file__).read_bytes())
source_hashes[str(helper.relative_to(ROOT))] = sha(helper)
result = dict(status='PASS_REAL_EXIT0_METADATA_FOR_N10_INDEPENDENT_RECORDED_FINANCE',
    binding=dict(task_id=os.environ['COIN_TASK_ID'], source_hashes=source_hashes),
    actual_audit_task=task, actual_audit_exit_code=0, actual_host_session=27066, actual_host_chunk='08cd7f',
    audit_report=dict(path=REPORT, sha256=report_sha, status=audit['status']),
    checker_sha256=audit['independent_source_sha256'], ACTUAL_BINDING_sha256=binding_sha,
    RUN_BINDING_sha256=rb_sha, actual_reports=audit['binding']['actual_reports'],
    completed_cases_verified=4, financial_case_calls=4, tolerances=audit['tolerances'],
    maximum_errors=audit['maximum_errors'], elapsed_seconds=audit['elapsed_seconds'],
    peak_RSS_bytes=audit['peak_RSS_bytes'], payloads_or_financial_math_reread=False,
    original_failed_producer_preserved=binding['original_failed_producer_task'],
    native_filters_or_funding_units_or_full_quantity_sizing_or_APR_certified=False)
out = ROOT / 'reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_INDEPENDENT_ACTUAL_EXIT_20261004.json'
guard.write(out, result)
print(json.dumps(dict(output=str(out), sha256=sha(out), audit_task=task['task']['id'], actual_exit_code=0)))
