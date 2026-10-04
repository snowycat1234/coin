"""UNRUN metadata binder for one predeclared winter90 financial audit.

Read only small JSON and stream source hashes. No producer loader, payload QA,
account calculation, financial span execution, correction branch or old replay.
"""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
CHECKER = 'scripts/investment/multi_asset_financial_audit.py'
CHECKER_SHA = '0d77b4b0bbb6bbb970d5ea6d101efd24ab863e00fb0c3cf37547e39248388bc1'
PRIOR = STATE / 'd054-november-ten-equal-financial-20261004-v1/ACTUAL_BINDING.json'
PRIOR_SHA = 'e402f2d22ec174da1f9ab11da52917d1223c6d5320c9381f746609f6631aa0fc'
SUFFIX = '_20261004_V1.json'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def ordinary(path):
    path = Path(path)
    resolved = path.resolve(strict=True)
    need(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)) and
         (resolved.is_relative_to(ROOT) or resolved.is_relative_to(STATE)),
         'Ordinary contained metadata/source path: ' + str(path))
    return resolved


def sha(path):
    with ordinary(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def small(path, expected=None):
    path = ordinary(path)
    need(path != ROOT / 'state/dataset_lock.json' and path.stat().st_size <= 2_000_000,
         'Only small metadata JSON; private lock is hash-only')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    need(expected is None or digest == expected, 'Exact metadata SHA: ' + str(path))
    return json.loads(raw), digest


def project(name):
    path = ordinary(ROOT / name)
    need(path.is_relative_to(ROOT), 'Project source containment')
    return path


def closed(task_id):
    need(len(task_id) == 32 and all(c in '0123456789abcdef' for c in task_id), 'Actual task identity')
    path = STATE / ('task-progress/task-' + task_id + '.json')
    task, digest = small(path)
    need(task['id'] == task_id and task['status'] == 'completed' and
         type(task['exit_code']) is int and task['exit_code'] == 0 and task.get('ended_at'),
         'Genuinely completed producer/source task with actual exit0')
    return dict(path=str(path), sha256=digest, task=task)


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', required=True, choices=('TWO_CONTROL', 'TEN_EQUAL', 'TEN_INVERSE'))
    parser.add_argument('--producer-host', required=True, nargs=3,
                        metavar=('SESSION', 'FINAL_CHUNK', 'EXIT_CODE'))
    args = parser.parse_args()
    need(os.environ.get('COIN_TASK_ID'), 'Actual bounded metadata task required')
    session, chunk, exit_code = args.producer_host
    need(session.isdigit() and chunk and exit_code == '0', 'Recorded producer host closure tuple')
    recipe = args.recipe
    stem = 'MULTI_ASSET_WINTER_' + recipe + SUFFIX
    protocol_path, actual_path = 'protocols/' + stem, 'reports/fast_research/' + stem
    spec, protocol_sha = small(ROOT / protocol_path)
    actual, actual_sha = small(ROOT / actual_path)
    prior, _ = small(PRIOR, PRIOR_SHA)
    source_hashes = dict(prior['source_hashes'])
    need(len(source_hashes) == 14 and prior['source_archives'] == {}, 'Exact accepted fourteen-helper map')
    source_hashes[CHECKER] = CHECKER_SHA
    for name, digest in source_hashes.items():
        need(sha(project(name)) == digest, 'Unchanged independent helper: ' + name)
    need(spec['independent_reference_pre_market_sha256'] == CHECKER_SHA,
         'Same pre-market-pinned normal winter auditor')
    from scripts.investment.multi_asset_financial_audit import (
        ACTUAL_STATUSES, ALLOCATION_STRATEGIES, calendar_scope, winter_source_records)
    scope = calendar_scope(spec)
    need(scope['period_days'] == 90 and scope['required_minutes'] == 129600 and
         actual['status'] in ACTUAL_STATUSES and actual['actual_calendar_days'] == 90 and
         len(actual['cases']) == actual['completed_cases'] == actual['required_cases'] == 4 and
         actual['complete_calendar_cases'] == actual['calendar_complete_cases'] == 4 and
         actual['account_path'] == spec['account_path'], 'Exactly four completed winter90 calendars')
    run = STATE / ('d056-winter-' + recipe.lower().replace('_', '-') + '-20261004-v1')
    need(Path(actual['run_dir']) == run, 'Exact new producer directory')
    rb, rb_sha = small(run / 'RUN_BINDING.json')
    task = closed(actual['binding']['task_id'])
    need(actual['binding'] == rb and rb['protocol_sha256'] == protocol_sha and
         rb['source_hashes'] == spec['source_hashes'], 'Exact report, RUN_BINDING and protocol source identities')
    for name, digest in rb['source_hashes'].items():
        need(sha(project(name)) == digest, 'Producer consumed unchanged source: ' + name)
    manifest, manifest_sha = small(Path(spec['data_manifest']['path']), spec['data_manifest']['sha256'])
    need(rb['manifest_sha256'] == manifest_sha, 'Producer consumed exact accepted manifest')
    symbols, pool_id = actual['cases'][0]['symbols'], actual['cases'][0]['pool']
    pools = [p for p in spec['pools'] if p['id'] == pool_id]
    need(len(pools) == 1 and symbols == pools[0]['symbols'] and len(symbols) == len(set(symbols)),
         'Exact configured account order, distinct from source catalogue order')
    allocation = 'INVERSE_VOL_30D' if recipe == 'TEN_INVERSE' else 'EQUAL'
    need((symbols == ['BTCUSDT', 'ETHUSDT'] if recipe == 'TWO_CONTROL' else
          len(symbols) == 10 and symbols == manifest['selected_symbols']) and
         spec['allocation'] == actual['allocation'] == allocation and
         spec['strategy'] == actual['strategy_id'] == ALLOCATION_STRATEGIES[allocation] and
         spec['initial_capital_USDT'] == actual['initial_capital_per_comparison_account_USDT'] == 10000,
         'One fixed HOLD recipe and full shared capital')
    need({(c['cost_id'], c['unit_id']) for c in actual['cases']} ==
         {(cost, unit) for cost in ('BASE27', 'STRESS43') for unit in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT')},
         'All four predeclared cost and conditional-unit scenarios')
    for case in actual['cases']:
        summary = case['summary']
        need(case['symbols'] == symbols and case['pool'] == pool_id and
             summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT' and summary['stop_us'] is None and
             summary['completed_minutes'] == summary['required_minutes'] == 129600 and
             summary['daily_metrics']['days'] == 90, 'Complete calendar with no halted prefix')
    _, certificates = winter_source_records(manifest, tuple(symbols),
        SimpleNamespace(small=small, project=project, closed=closed), scope)
    need(len(manifest['market_records']) == 90 and len(manifest['daily_records']) == 70 and
         len(manifest['warmup_minute_records']) == 30 and len(manifest['normalized_source_hashes']) == 190,
         'Exact accepted ninety score plus one hundred warmup source identities')
    financial_run = STATE / ('d056-winter-' + recipe.lower().replace('_', '-') + '-financial-20261004-v1')
    need(not financial_run.exists(), 'Exclusive new financial plan directory')
    archive = ROOT / 'docs/archive/MULTI_ASSET_WINTER_FINANCIAL_PRODUCER_TASKS_20261004_V1'
    archive.mkdir(parents=True, exist_ok=True)
    task_archive = archive / (recipe + '-COMPLETED_TASK.json')
    raw_task = ordinary(task['path']).read_bytes()
    need(hashlib.sha256(raw_task).hexdigest() == task['sha256'], 'Closed task unchanged before raw preservation')
    with task_archive.open('xb') as stream:
        stream.write(raw_task)
    need(sha(task_archive) == task['sha256'], 'Identical raw completed-task archive bytes')
    plan = dict(prior, checker_sha256=CHECKER_SHA, source_hashes=source_hashes,
        protocol_path=protocol_path, protocol_sha256=protocol_sha, actual_report=actual_path,
        actual_report_sha256=actual_sha, actual_task_id=task['task']['id'], actual_closed_task=task,
        producer_run_binding_sha256=rb_sha, required_scope=scope, strategy=spec['strategy'], allocation=allocation,
        producer_actual_host=dict(session=int(session), final_chunk=chunk, actual_exit_code=0),
        producer_completed_task_archive=dict(path=str(task_archive.relative_to(ROOT)), sha256=task['sha256']),
        accepted_source_metadata_capabilities=certificates,
        metadata_helper=dict(path=str(Path(__file__).resolve().relative_to(ROOT)), sha256=sha(__file__),
            task_id=os.environ['COIN_TASK_ID']),
        audit_scope='WINTER90_CONTINUOUS_RECORDED_SHARED_WALLET_TARGETS_BOUNDARY_COUPONS_AND_FINAL_INVENTORY',
        metadata_scope='Real new producer closed0; accepted190 metadata identities only. No source payload or financial execution.',
        budgets=dict(new_owned_bytes=100000, wall_seconds=1800, peak_RSS_bytes=1500000000),
        ready_to_execute=True, created_utc=datetime.now(UTC).isoformat())
    need(plan['tolerances'] == dict(cash_USDT=1e-7, ratio=1e-10), 'Original financial tolerances unchanged')
    financial_run.mkdir()
    path = financial_run / 'ACTUAL_BINDING.json'
    write(path, plan)
    print(json.dumps(dict(recipe=recipe, plan=str(path), sha256=sha(path), required_scope=scope,
        producer_task_id=task['task']['id'], financial_calls=0, source_payloads_read=0)))


if __name__ == '__main__':
    main()
