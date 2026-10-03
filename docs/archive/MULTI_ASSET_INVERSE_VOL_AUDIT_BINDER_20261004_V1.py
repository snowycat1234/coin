"""Freeze one completed D052 month and reused finance span; no financial payload IO."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
CHECKER = 'scripts/investment/multi_asset_financial_audit.py'
CHECKER_SHA = '05b20df6e6409132aa2a5db7a041f3d4d582698124d0385c97a53ddb0fb03d96'
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', '1000PEPEUSDT', 'XRPUSDT',
           'WIFUSDT', 'WLDUSDT', 'DOGEUSDT', '1000SATSUSDT', 'ORDIUSDT')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archive_exact(source, relative):
    destination = ROOT / relative
    if destination.exists():
        assert not destination.is_symlink() and sha(destination) == sha(source)
    else:
        with destination.open('xb') as stream:
            stream.write(Path(source).read_bytes())
        assert sha(destination) == sha(source)
    return relative


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', choices=('september', 'october'), required=True)
    for name in ('actual-sha256', 'protocol-sha256', 'actual-task-id'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    run = STATE / f'd052-inverse-vol-{args.month}-financial-20261004-v1'
    name = f'MULTI_ASSET_INVERSE_VOL_{args.month.upper()}_20261004_V1.json'
    actual_path, proto_path = 'reports/fast_research/' + name, 'protocols/' + name
    assert os.environ.get('COIN_TASK_ID') and not run.exists()
    code = ROOT / CHECKER
    assert sha(code) == CHECKER_SHA
    ast.parse(code.read_bytes())
    spec = importlib.util.spec_from_file_location('d052_metadata_compile_only_audit', code)
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    base, _, derivation = checker.prepare_financial(SYMBOLS)
    guard = base.module(base.GUARD, 'd052_metadata_small_guard', base.GUARD_SHA)
    actual, actual_sha = guard.small(ROOT / actual_path, args.actual_sha256)
    protocol, proto_sha = guard.small(ROOT / proto_path, args.protocol_sha256)
    assert actual['status'] in checker.ACTUAL_STATUSES
    assert actual['binding']['protocol_sha256'] == proto_sha
    assert actual['binding']['task_id'] == args.actual_task_id
    task = guard.closed(args.actual_task_id)
    scope = checker.calendar_scope(protocol)
    expected_month, days = ('2024-09', 30) if args.month == 'september' else ('2024-10', 31)
    assert (scope['score_month'], scope['period_days']) == (expected_month, days)
    assert protocol['allocation'] == 'INVERSE_VOL_30D' and protocol['initial_capital_USDT'] == 10000
    assert protocol['strategy'] == checker.ALLOCATION_STRATEGIES['INVERSE_VOL_30D']
    assert next(p for p in protocol['pools'] if p['id'] == 'LIQUIDITY_TEN')['symbols'] == list(SYMBOLS)
    assert len(actual['cases']) == actual['completed_cases'] == actual['required_cases'] == actual['complete_calendar_cases'] == 4
    assert all(c['symbols'] == list(SYMBOLS) and c['pool'] == 'LIQUIDITY_TEN' and
               c['summary']['completed_minutes'] == c['summary']['required_minutes'] == days * 1440
               for c in actual['cases'])
    assert {(c['cost_id'], c['unit_id']) for c in actual['cases']} == {(c, u) for c in base.COSTS for u in base.UNITS}
    for path, digest in protocol['source_hashes'].items():
        assert sha(guard.project(path)) == digest  # LOCK, if present, is only streamed for its hash.
    rb, rb_sha = guard.small(Path(actual['run_dir']) / 'RUN_BINDING.json')
    assert rb == actual['binding'] and rb['source_hashes'] == protocol['source_hashes']
    pins = [CHECKER, checker.REUSE, checker.PATCH,
            'scripts/investment/audit_closing_exempt_research.py',
            'docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py',
            base.REFERENCE, base.GUARD, 'scripts/research_v7/oracle_flow_ceiling.py',
            'scripts/research_v8/registry.py', 'src/quant/resources.py',
            'scripts/with_task_progress.sh', 'scripts/bounded.sh',
            'scripts/task_progress_run.py', 'environments/v8/uv.lock']
    hashes = {path: sha(guard.project(path)) for path in pins}
    assert hashes[checker.REUSE] == checker.REUSE_SHA and hashes[checker.PATCH] == checker.PATCH_SHA
    archive_exact(code, 'docs/archive/MULTI_ASSET_INVERSE_VOL_FINANCIAL_AUDITOR_20261004_V1.py')
    binder_archive = archive_exact(Path(__file__), 'docs/archive/MULTI_ASSET_INVERSE_VOL_AUDIT_BINDER_20261004_V1.py')
    hashes[binder_archive] = sha(guard.project(binder_archive))
    run.mkdir()
    plan = dict(ready_to_execute=True, checker_sha256=CHECKER_SHA,
        protocol_path=proto_path, protocol_sha256=proto_sha,
        actual_report=actual_path, actual_report_sha256=actual_sha,
        actual_task_id=args.actual_task_id, source_hashes=hashes, source_archives={}, required_scope=scope,
        tolerances=dict(cash_USDT=1e-7, ratio=1e-10),
        budgets=dict(peak_RSS_bytes=1_000_000_000, wall_seconds=1200, new_owned_bytes=5_000_000),
        metadata_freezer_task_id=os.environ['COIN_TASK_ID'], actual_closed_task=task,
        producer_run_binding_sha256=rb_sha, complete_financial_span_compiled_before_arrays=derivation,
        allocation='INVERSE_VOL_30D', inverse_is_not_ERC=True, old_QA_or_accounts_replayed=False,
        audit_scope='COMPLETE_MONTH_MARKED_NAV_WITH_ACTUAL_TERMINAL_INVENTORY_CASH_REALIZATION_SEPARATE',
        investment_qualification_pass=False)
    guard.write(run / 'ACTUAL_BINDING.json', plan)
    print(json.dumps(dict(ready=True, checker_sha256=CHECKER_SHA,
        ACTUAL_BINDING_sha256=sha(run / 'ACTUAL_BINDING.json'), run_dir=str(run),
        protocol_sha256=proto_sha, actual_report_sha256=actual_sha, financial_payloads_read=0)))


if __name__ == '__main__':
    main()
