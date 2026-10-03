"""UNRUN small-metadata D047 financial binder; no ledger/market reads.

Run only after the new four-selector producer truly closes. The protocol and
STATE manifest are exclusive new files, while original failures stay intact.
"""
import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
CHECKER = 'scripts/investment/audit_closing_exempt_research_v2.py'
CHECKER_SHA = 'b42a92edee8fd93c2dba0f5d055caee70ef73680bf473af7881f39abbfec514b'
ARCHIVE = 'docs/archive/CLOSING_EXEMPT_FINANCIAL_BINDER_SOURCE_20261003_V2.py'
WRAPPER = 'docs/archive/CLOSING_EXEMPT_FINANCIAL_RUN_WRAPPER_SOURCE_20261003_V2.py'
PROTOCOL = 'protocols/CLOSING_EXEMPT_RESEARCH_20261003_V1.json'
ACTUAL = 'reports/fast_research/CLOSING_EXEMPT_RESEARCH_ACTUAL_20261003_V1.json'
PLAN = 'protocols/CLOSING_EXEMPT_FINANCIAL_INDEPENDENT_BINDING_20261003_V2.json'
RUN = STATE / 'd048-closing-exempt-financial-20261003-v2'
OUT = 'reports/fast_research/CLOSING_EXEMPT_FINANCIAL_INDEPENDENT_20261003_V2.json'
ACTUAL_STATUS = 'COMPLETE_D048_EIGHT_CLOSING_EXEMPT_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
PINS = {
    'scripts/investment/audit_closing_exempt_research.py': '459b8bd766105539a0c1807b9e8053530743d1b47245ccd171723966eb2b25b2',
    'docs/archive/CLOSING_EXEMPT_FINANCIAL_AUDITOR_SOURCE_20261003_V2.py': 'b42a92edee8fd93c2dba0f5d055caee70ef73680bf473af7881f39abbfec514b',
    'scripts/investment/audit_turtle_perpetual.py': '722e48ca19b924d15f8922c13aebf021db8e11145130a97dca4e930e2f93ae53',
    GUARD: GUARD_SHA,
    CHECKER: CHECKER_SHA,
    'docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py':
        '1c4b0bcb0b4dd954ae4cdb7f12b64426f2244ba554340ee23e7d73ddbac5c7bb',
    'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py':
        '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a',
    'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py':
        '356086d2534539dba0aecf04b1e716d39ec1f5bb5e1c5817b80affdb38d36b31',
    'docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py':
        'f50223ad5ec0da2be16ae3ac5447bec2d5763260566000893f1697483b7667e4',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--peak-rss-bytes', type=int, default=3_000_000_000)
    parser.add_argument('--wall-seconds', type=int, default=3600)
    args = parser.parse_args()
    assert os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2')
    assert sha(ROOT / GUARD) == GUARD_SHA and sha(__file__) == sha(ROOT / ARCHIVE)
    module_spec = importlib.util.spec_from_file_location('d047_finance_binding_guards', ROOT / GUARD)
    g = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(g)
    g.check(0 < args.peak_rss_bytes <= 3_000_000_000 and 0 < args.wall_seconds <= 3600, 'Fixed finite financial process budget')
    spec, protocol_sha = g.small(g.project(PROTOCOL))
    actual, actual_sha = g.small(g.project(ACTUAL))
    g.check(spec['contract_id'] == 'D048_FIXED303D_TURTLE_AND_HOLD_CLOSING_EXEMPT_CONDITIONAL_V1'
        and spec['period_ids'] == ['303D'] and actual['status'] == ACTUAL_STATUS
        and actual['completed_cases'] == actual['required_cases'] == len(actual['cases']) == 8,
        'Only the eight fixed new Turtle and HOLD selectors, not four guaranteed full calendars')
    g.check(actual['binding']['protocol_sha256'] == protocol_sha
        and actual['binding']['source_hashes'] == spec['frozen_sources'], 'Exact actual scientific binding')
    actual_task = g.closed(actual['binding']['task_id'])
    rb, _ = g.small(Path(spec['run_dir']) / 'RUN_BINDING.json', actual['run_binding_sha256'])
    g.check(rb == actual['binding'], 'Exact producer RUN_BINDING')
    smoke_ref = spec['required_smoke_receipt']
    smoke, smoke_sha = g.small(g.project(smoke_ref['path']), smoke_ref['sha256'])
    g.check(smoke['status'] == smoke_ref['required_status'] and smoke['test_exit_code'] == 0
        and smoke['source_bytes_unchanged'] is True, 'Only the actual corrected new synthetic receipt')
    smoke_task = g.closed(smoke['binding']['task_id'])
    g.check(smoke_task['task']['ended_at'] <= actual_task['task']['started_at'], 'Synthetic completed before actual market task')
    pins = dict(spec['frozen_sources'])
    for path, digest in PINS.items():
        g.check(path not in pins or pins[path] == digest, 'No conflicting accepted finance dependency')
        pins[path] = digest
        g.small(g.project(path), digest, False)
    for path, digest in spec['frozen_sources'].items():
        g.check(path != 'state/dataset_lock.json', 'Private LOCK never enters portable pins/body')
        g.small(g.project(path), digest, False)
    for path in (ARCHIVE, WRAPPER, PROTOCOL, ACTUAL):
        _, digest = g.small(g.project(path), parse=False)
        pins[path] = digest
    g.check(not (ROOT / PLAN).exists() and not RUN.exists() and not (ROOT / OUT).exists(), 'Exclusive new financial attempt')
    plan = dict(ready_to_execute=True, created_utc=datetime.now(UTC).isoformat(),
        freezer_task_id=os.environ['COIN_TASK_ID'], checker_sha256=CHECKER_SHA, source_hashes=pins,
        protocol_path=PROTOCOL, protocol_sha256=protocol_sha, actual_report=ACTUAL,
        actual_report_sha256=actual_sha, actual_task_id=actual['binding']['task_id'],
        required_actual_status=ACTUAL_STATUS, period_ids=['303D'], case_ids=[r['id'] for r in actual['cases']],
        run_dir=str(RUN), output_path=OUT, financial_binding_protocol_path=PLAN,
        wrapper_source=WRAPPER, wrapper_sha256=pins[WRAPPER],
        shared_smoke=dict(path=smoke_ref['path'], sha256=smoke_sha, task_id=smoke['binding']['task_id']),
        actual_run_binding_sha256=actual['run_binding_sha256'],
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        tolerances=dict(cash_USDT=1e-7, ratio=1e-10),
        budgets=dict(peak_RSS_bytes=args.peak_rss_bytes, wall_seconds=args.wall_seconds, new_owned_bytes=5_000_000),
        financial_scope='RECORDED_FINANCE_NOT_COMPLETE_STRATEGY_OR_NATIVE_EXECUTION',
        no_market_or_ledger_arrays_read=True, funding_rate_unit='UNCONFIRMED', candidate='NO_QUALIFIED_CANDIDATE')
    g.write(ROOT / PLAN, plan)
    RUN.mkdir()
    with (RUN / 'ACTUAL_BINDING.json').open('xb') as stream:
        stream.write((ROOT / PLAN).read_bytes())
    g.check(sha(RUN / 'ACTUAL_BINDING.json') == sha(ROOT / PLAN), 'Exact small manifest copy')
    print(str(RUN / 'ACTUAL_BINDING.json') + ' SHA256 ' + sha(ROOT / PLAN))


if __name__ == '__main__':
    main()
