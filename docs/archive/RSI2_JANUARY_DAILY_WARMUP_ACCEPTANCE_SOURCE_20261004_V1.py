"""Independent QA of eight new January archives; two old accepted rows are metadata reuse."""
from __future__ import annotations
import argparse, importlib.util, os, resource, sys, time
from pathlib import Path
from scripts.investment import multi_asset_data as data
from scripts.investment import multi_asset_source_acceptance as qa

CONTRACT = 'D058_JANUARY_DAILY_WARMUP_FORMAT_ACCEPTANCE_V1'
STATUS = 'PASS_D058_JANUARY_DAILY_WARMUP_SOURCE_FORMAT_ONLY'
RUN = data.STATE/'d058-rsi2-daily-warmup-acceptance-20261004-v1'
OUT = data.ROOT/'reports/fast_research/RSI2_JANUARY_DAILY_WARMUP_ACCEPTANCE_20261004_V1.json'
HELPER = data.ROOT/'docs/archive/RSI2_JANUARY_DAILY_WARMUP_SOURCE_20261004_V1.py'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'run-dir', 'output', 'experiment-id'): parser.add_argument('--'+name, required=True)
    args = parser.parse_args(); g = qa.load(qa.GUARD, qa.GUARD_SHA)
    spec, psha = g.small(Path(args.protocol))
    data.require(spec['contract_id'] == CONTRACT and spec['ready_for_execution'] is True and
        spec['capacity_registered'] is True and Path(args.run_dir).resolve() == RUN and
        Path(args.output).resolve() == OUT and spec['run_dir'] == str(RUN) and spec['output_path'] == str(OUT)
        and spec['experiment_id'] == args.experiment_id and
        spec['protocol_path'] == str(Path(args.protocol).relative_to(data.ROOT)), 'Fixed independent QA CLI/scope')
    data.require(Path(sys.prefix) == data.STATE/'v8-clean-env-20261002-v2', 'Clean bounded Python')
    module_spec = importlib.util.spec_from_file_location('d058_source_metadata', HELPER)
    source = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(source)
    data.require(spec['budgets'] == source.BUDGETS and not RUN.exists() and not OUT.exists(), 'Bounds/fresh QA owner')
    source.pins(spec); pool, old = source.accepted(spec, g)
    actual = source.proof(spec['source_actual'], g)
    data.require(actual['status'] == source.STATUS and actual['actual_exit_code'] == 0 and
        actual['source_only'] is True and actual['completed_files'] == actual['required_files'] == 10
        and actual['reused_files'] == 2 and actual['new_files'] == 8 and actual['requests'] == 16
        and actual['pool_receipt'] == spec['pool_receipt'] and actual['accepted_refs'] == spec['accepted_refs']
        and actual['selected_symbols'] == pool['symbols'] and actual['symbols'] == sorted(pool['symbols'])
        and actual['run_dir'] == str(source.RUN), 'Actual completed source and same selected pool')
    g.small(source.RUN/'RUN_BINDING.json', actual['run_binding_sha256'])
    rows = actual['sources']
    data.require(len(rows) == 10 and len({qa.key(r) for r in rows}) == 10 and
        {qa.key(r) for r in rows} == {('klines',s,'1d','2024-01') for s in actual['symbols']}, 'Exact unique ten January identities')
    task = os.environ['COIN_TASK_ID']; data.require(task != actual['binding']['task_id'], 'Independent actual task')
    RUN.mkdir(); started = time.monotonic(); progress = data.formats.progress_writer(10)
    binding = dict(task_id=task, checker_sha256=data.sha(__file__), protocol_path=str(args.protocol),
        protocol_sha256=psha, source_hashes=dict(spec['frozen_sources']),
        actual_reports={str((data.ROOT/spec['source_actual']['path']).resolve()):spec['source_actual']['sha256']},
        command=[sys.executable,*sys.argv], spec=spec)
    data.save(RUN/'RUN_BINDING.json', binding)
    report = dict(status='FAIL_D058_JANUARY_DAILY_WARMUP_ACCEPTANCE', binding=binding, run_dir=str(RUN),
        run_binding_sha256=data.sha(RUN/'RUN_BINDING.json'), pool_receipt=spec['pool_receipt'],
        symbols=actual['symbols'], selected_symbols=actual['selected_symbols'], sources=[],
        normalized_source_hashes={}, source_only=True, resources_before=data.resources.status(),
        accepted_refs=spec['accepted_refs'], source_actual=spec['source_actual'],
        completed_files_verified=0, new_files_verified=0, accepted_files_reused=0,
        old_source_QA_repeated=False, no_imputation=True, warmup_240_eligibility_certified=False,
        funding_unit_certified=False, native_market_certified=False, publication_time_certified=False,
        models_fit=0, GPU=0, orders_sent=0, locked_consumed=False)
    code = 1
    try:
        source.event(spec,psha,task,'START','RUNNING'); independent = qa.load(qa.TRADE,qa.TRADE_SHA)
        with data.deadline(source.BUDGETS['wall_seconds']):
            for row in rows:
                if row['symbol'] in ('BTCUSDT','ETHUSDT'):
                    previous = next(r for r in old if r['symbol'] == row['symbol'])
                    data.require(all(row[k] == previous[k] for k in (*qa.IDENTITY,'receipt_path','receipt_sha256','quality')),
                        'Exact previously accepted January row, no old payload QA')
                    result = dict(status='REUSED_PRIOR_INDEPENDENT_QA_EXACT_METADATA_ONLY', rows=row['rows'],
                        first_open_us=row['quality']['first_open_us'],
                        last_close_us=row['quality']['last_close_us'])
                    report['accepted_files_reused'] += 1
                else:
                    parquet, archive, _ = qa.new_receipt(row, source.RUN, g)
                    result, _ = qa.audit_trade(row,parquet,archive,independent,allow_partial_before_listing=True)
                    data.require(data.sha(parquet) == row['normalized_sha256'] and data.sha(archive) == row['zip_sha256'],
                        'New raw and normalized bytes unchanged')
                    report['new_files_verified'] += 1
                report['sources'].append(dict(row,independent_QA=result,
                    observed_first_open_us=result['first_open_us'],
                    january_missing_prefix_days=(result['first_open_us']-1704067200000000)//data.DAY))
                report['normalized_source_hashes'][row['normalized_path']] = row['normalized_sha256']
                report['completed_files_verified'] += 1
                progress.update('独立一月源核验：仅新8档',report['completed_files_verified'],10,'档')
                data.require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= source.BUDGETS['peak_RSS_bytes'], 'QA RSS')
        source.pins(spec)
        data.require((report['completed_files_verified'],report['new_files_verified'],report['accepted_files_reused']) == (10,8,2)
            and data.owned(RUN)+data.owned(source.RUN) <= source.BUDGETS['new_owned_bytes'], 'Actual QA/reuse counts and combined owned bytes')
        report['status'] = STATUS; code = 0
    except Exception as error:
        report.update(status='FAIL_D058_JANUARY_DAILY_WARMUP_ACCEPTANCE',error_type=type(error).__name__,reason=str(error))
    finally:
        report.update(actual_exit_code=code,elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=data.owned(RUN),resources_after=data.resources.status())
        data.save(OUT,report);source.event(spec,psha,task,'RESULT' if code==0 else 'FAIL',report['status'])
        progress.update('独立补暖源核验已退出',report['completed_files_verified'],10,'档',actual_exit_code=code);progress.stop.set()
    return code

if __name__ == '__main__': raise SystemExit(main())
