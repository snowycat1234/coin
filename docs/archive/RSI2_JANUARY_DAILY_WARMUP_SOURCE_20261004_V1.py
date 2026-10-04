"""Fixed July pool January daily context: accepted BTC/ETH reuse and eight new archives.

No pool reselection, old source QA, account calculation or publication certification.
--protocol is frozen before --run-dir/--output/--experiment-id acquisition.
"""
from __future__ import annotations
import argparse, importlib.util, json, os, resource, sys, time
from datetime import UTC, datetime
from pathlib import Path
from scripts.investment import multi_asset_data as data
from scripts.investment import multi_asset_source_acceptance as qa
from scripts.research_v8.registry import FIELDS, append_event

ROOT, STATE = data.ROOT, data.STATE
CONTRACT = 'D058_FIXED_JULY_POOL_JANUARY_DAILY_WARMUP_SOURCE_V1'
STATUS = 'COMPLETE_D058_JULY_POOL_JANUARY_DAILY_WARMUP_FORMAT_PENDING_ACCEPTANCE'
BUDGETS = dict(new_owned_bytes=10_000_000, peak_RSS_bytes=1_000_000_000,
    wall_seconds=900, daily_zip_bytes=64_000, daily_csv_bytes=128_000,
    source_file_seconds=30, native_peak_bytes=250_000_000)
RUN = STATE/'d058-rsi2-daily-warmup-source-20261004-v1'
OUT = ROOT/'reports/fast_research/RSI2_JANUARY_DAILY_WARMUP_SOURCE_20261004_V1.json'
POOL_SHA = '9b8df895197e888bfb4a4dd2dec08915c5c3425659925408b289483e55e0acf7'
PARENTS = dict(
    producer=('reports/fast_research/PERPETUAL_213_SOURCE_ACTUAL_20261003_V1.json',
        '3e03d1eaad434a32219d1e2a03c3dcbacdafc923419740f5f8f20bedfbb06ca9',
        'PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA'),
    independent=('reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json',
        'dc193b2df35dda8dc011895bc9d973946321931f304ad112266b5ccf1f8090ef',
        'PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS'),
    root=('reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json',
        '795667026b7eb50ab08f1c5b07254eb2002591549b792aa4685439a2d82cc823',
        'PASS_ROOT_D043_COMPLETE_213_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS'))

def guard():
    return qa.load(qa.GUARD, qa.GUARD_SHA)

def proof(ref, g):
    p = Path(ref['path']); p = p if p.is_absolute() else ROOT/p
    value, _ = g.small(p, ref['sha256'])
    data.require(value['status'] == ref['required_status'], 'Exact accepted metadata status')
    g.closed(value['binding']['task_id'])
    return value

def pins(spec):
    for name, digest in spec['frozen_sources'].items():
        data.require(name != 'state/dataset_lock.json' and data.sha(ROOT/name) == digest,
            'Frozen nonprivate source changed: '+name)

def accepted(spec, g):
    data.require(spec['pool_receipt']['sha256'] == POOL_SHA, 'Same original July pool')
    pool = proof(spec['pool_receipt'], g)
    old = {}
    for role, (name, digest, status) in PARENTS.items():
        ref = spec['accepted_refs'][role]
        data.require(ref == dict(path=name, sha256=digest, required_status=status), 'Exact old accepted reference')
        old[role] = proof(ref, g)
    rows = [r for r in old['producer']['sources'] if (r['kind'], r.get('interval'), r['month']) ==
        ('klines', '1d', '2024-01') and r['symbol'] in ('BTCUSDT', 'ETHUSDT')]
    data.require(len(rows) == 2, 'Two accepted January control records')
    for r in rows:
        evidence = next(q for q in old['independent']['sources'] if
            (q['kind'], q.get('interval'), q['month'], q['symbol']) ==
            ('klines', '1d', '2024-01', r['symbol']))
        data.require(all(evidence[k] == r[k] for k in ('normalized_path', 'normalized_sha256',
            'rows', 'receipt_sha256')), 'Exact prior raw independent QA bridge')
        qa.payload(r['normalized_path'], STATE, r['normalized_sha256'], 32_000_000, r['normalized_bytes'])
        g.small(Path(r['receipt_path']), r['receipt_sha256'])
    return pool, rows

def event(spec, psha, task, stage, status):
    row = dict.fromkeys(FIELDS)
    row.update(event_type=stage, event_id=spec['experiment_id']+'-'+task+'-'+stage,
        experiment_id=spec['experiment_id'], git_commit=spec['git_commit'], data_manifest_hash=POOL_SHA,
        protocol_hash=psha, feature_set='JANUARY_OFFICIAL_DAILY_INDICATOR_WARMUP_ONLY',
        labels='SOURCE_ONLY', model_family='NONE', hyperparameters={}, seed=None,
        thresholds={}, cost_assumptions='NO_ACCOUNT_CALCULATION', all_folds=[], success_failure=status,
        reason_for_next_experiment='FIXED_240_BAR_INDICATOR_CONTEXT_NO_POOL_RESELECTION',
        result_influenced_later_choice=False, source_hashes={spec['protocol_path']:psha}, task_id=task)
    append_event(ROOT/'reports/experiment_registry.jsonl', row)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'run-dir', 'output', 'experiment-id'): parser.add_argument('--'+name, required=True)
    args = parser.parse_args(); g = guard(); spec, psha = g.small(Path(args.protocol))
    data.require(spec['contract_id'] == CONTRACT and spec['ready_for_execution'] is True and
        spec['capacity_registered'] is True and spec['budgets'] == BUDGETS and
        Path(args.run_dir).resolve() == RUN and Path(args.output).resolve() == OUT and
        spec['run_dir'] == str(RUN) and spec['output_path'] == str(OUT) and
        spec['experiment_id'] == args.experiment_id and spec['protocol_path'] == str(Path(args.protocol).relative_to(ROOT)),
        'Frozen fixed source scope/bounds/CLI')
    task = os.environ['COIN_TASK_ID']; data.require(Path(sys.prefix) == STATE/'v8-clean-env-20261002-v2', 'Clean bounded Python')
    pins(spec); pool, reused = accepted(spec, g)
    data.require(not RUN.exists() and not OUT.exists(), 'Exclusive source/report')
    RUN.mkdir(); started = time.monotonic(); progress = data.formats.progress_writer(10)
    binding = dict(task_id=task, protocol_path=str(args.protocol), protocol_sha256=psha,
        source_sha256=data.sha(__file__), source_hashes=dict(spec['frozen_sources']),
        command=[sys.executable, *sys.argv], spec=spec, environment=dict(sys_prefix=sys.prefix))
    data.save(RUN/'RUN_BINDING.json', binding)
    report = dict(status='FAIL_D058_JANUARY_DAILY_WARMUP_SOURCE', binding=binding,
        run_dir=str(RUN), run_binding_sha256=data.sha(RUN/'RUN_BINDING.json'),
        source_only=True, pool_receipt=spec['pool_receipt'], symbols=sorted(pool['symbols']),
        selected_symbols=pool['symbols'], accepted_refs=spec['accepted_refs'], sources=[],
        required_files=10, completed_files=0, reused_files=0, new_files=0,
        funding_unit_certified=False, native_market_certified=False, publication_time_certified=False,
        old_source_QA_repeated=False, models_fit=0, GPU=0, orders_sent=0, locked_consumed=False,
        warmup_240_eligibility_certified=False, resources_before=data.resources.status())
    code = 1; client = data.WindowsSourceTransport(ROOT/'scripts/investment/multi_asset_official_transport.ps1', RUN)
    try:
        event(spec, psha, task, 'START', 'RUNNING')
        with data.deadline(BUDGETS['wall_seconds']):
            scan_started = datetime.now(UTC).isoformat(); report['disk'] = data.disk.check(BUDGETS['new_owned_bytes'])
            report['disk'].update(scan_started_utc=scan_started, actual_scan_completed_utc=datetime.now(UTC).isoformat())
            authorization = dict(phase='WARMUP_DAILY', ready_for_execution=True, capacity_registered=True,
                pool_receipt=spec['pool_receipt'], pool_receipt_sha256=POOL_SHA, symbols=report['symbols'])
            limits = dict(data.DEFAULT_BUDGETS, market_owned_bytes=BUDGETS['new_owned_bytes'],
                source_wall_seconds=BUDGETS['wall_seconds'])
            for symbol in report['symbols']:
                if symbol in ('BTCUSDT', 'ETHUSDT'):
                    row = dict(next(r for r in reused if r['symbol'] == symbol),
                        acquisition='REUSED_ACCEPTED_BYTES_NO_REPEAT_QA_OR_DOWNLOAD')
                    report['reused_files'] += 1
                else:
                    row = data.acquire(data.entry(symbol, 'klines', '1d', '2024-01'), RUN, client,
                        authorization=authorization, budgets=limits); report['new_files'] += 1
                report['sources'].append(row); report['completed_files'] += 1
                progress.update('一月日线：新8档/已接受2档', report['completed_files'], 10, '档')
                data.require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= BUDGETS['peak_RSS_bytes'], 'Source RSS')
        pins(spec); data.require((report['reused_files'],report['new_files'],client.requests) == (2,8,16), 'Actual complete counts')
        data.require(data.owned(RUN) <= BUDGETS['new_owned_bytes'], 'Source owned bytes')
        report['status'] = STATUS; code = 0
    except Exception as error:
        report.update(status='FAIL_D058_JANUARY_DAILY_WARMUP_SOURCE', error_type=type(error).__name__, reason=str(error))
    finally:
        report.update(actual_exit_code=code, elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, owned_bytes=data.owned(RUN),
            requests=client.requests, HTTP_status_counts=client.http_status_counts,
            native_peak_bytes=client.native_peak, combined_conservative_peak_bound_bytes=client.combined_peak,
            resources_after=data.resources.status())
        data.save(OUT, report); event(spec, psha, task, 'RESULT' if code == 0 else 'FAIL', report['status'])
        progress.update('一月补暖来源已退出',report['completed_files'],10,'档',actual_exit_code=code); progress.stop.set()
    return code

if __name__ == '__main__': raise SystemExit(main())
