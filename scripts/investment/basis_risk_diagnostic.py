"""Fixed-quantity Spot/mark/index close valuation risk, never execution or APR.

Each window uses its own first Spot close as denominator. Funding coupons are
context only: fixed-event notional and fixed coin quantity are different units.
"""
from __future__ import annotations

import argparse
import calendar
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import polars as pl

from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS, append_event

SYMBOLS = ('BTCUSDT', 'ETHUSDT')
MONTHS = ('2025-08', '2025-09', '2025-10', '2025-11')
KINDS = ('spot1m', 'markPriceKlines', 'indexPriceKlines')
MINUTE_US = 60_000_000
START_US, END_US = 1754006400000000, 1764547200000000
OPTIONS_PATH = 'reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json'
OPTIONS_SHA = 'fd1b4c5683b3569a9e770600d325c26a86ffa235aa9fbefc595eafaabaee7de7'
PRICE_STATE = STATE / 'v8-funding-mark-index-source-20261002-v1'
TEST = 'tests/test_basis_risk_diagnostic.py'
SMOKE_STATUS = 'PASS_BASIS_RISK_SYNTHETIC_MATH_ALIGNMENT_NOT_MARKET_RESULT'
ACTUAL_STATUS = 'COMPLETE_FIXED_QUANTITY_BASIS_CLOSE_PROXY_RISK_NOT_CASH_NAV_OR_APR'
MATH = dict(quantity_per_leg=1, basis='MARK_MINUS_SPOT', normalization='WINDOW_FIRST_SPOT_CLOSE',
    adverse='POSITIVE_BASIS_CHANGE', valuation='NEGATIVE_BASIS_CHANGE',
    drawdown='PREFIX_RUNNING_PEAK_WITH_INITIAL_ZERO', month_scope='ALL_FOUR_LOCAL_BASELINES_DESCRIPTIVE_ONLY')
PREFIXES = ('basis', 'mark_index', 'index_spot')
TOLERANCE_BP = 1e-8


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_json(path, expected=None):
    path = Path(path)
    path = path if path.is_absolute() else ROOT / path
    need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
         and path.stat().st_size < 2_000_000, 'Explicit small ordinary project proof required')
    need(expected is None or sha(path) == expected, 'Frozen proof changed: ' + str(path))
    return json.loads(path.read_bytes())


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as writer:
        json.dump(value, writer, indent=2, ensure_ascii=False, allow_nan=False); writer.write('\n')


def month_bounds(month):
    year, number = map(int, month.split('-'))
    opened = int(datetime(year, number, 1, tzinfo=UTC).timestamp()) * 1_000_000
    return opened, opened + calendar.monthrange(year, number)[1] * 1440 * MINUTE_US


def canonical_prices(kind, frame, symbol):
    """Only project one existing close per source candle; never fill or resample."""
    need(kind in KINDS and symbol in SYMBOLS and frame.height > 0, 'Explicit accepted source stream')
    if kind == 'spot1m':
        required = ('open_us', 'close_us', 'close', 'symbol', 'valid_day')
        need(set(required) <= set(frame.columns), 'Original Spot schema required')
        need(frame['open_us'].dtype == frame['close_us'].dtype == pl.Int64
             and frame['valid_day'].dtype == pl.Boolean and frame['valid_day'].null_count() == 0
             and frame['symbol'].null_count() == 0 and frame['valid_day'].all()
             and frame['symbol'].eq(symbol).all(), 'Original Spot time, symbol and valid day fields')
        result = frame.select('open_us', 'close_us', pl.col('close').alias('spot_close'))
    else:
        required = ('timestamp_ms', 'close_time_ms', 'close')
        need(set(required) <= set(frame.columns), 'Original mark/index schema required')
        need(frame['timestamp_ms'].dtype == frame['close_time_ms'].dtype == pl.Int64
             and frame['close_time_ms'].eq(frame['timestamp_ms'] + 59999).all(),
             'Original inclusive epoch-ms endpoint required; never silently rebase')
        result = frame.select((pl.col('timestamp_ms') * 1000).alias('open_us'),
            ((pl.col('close_time_ms') + 1) * 1000).alias('close_us'),
            pl.col('close').alias('mark_close' if kind == 'markPriceKlines' else 'index_close'))
    price = result.columns[-1]
    need(frame['close'].dtype == pl.Float64 and result.null_count().to_numpy().sum() == 0
         and result[price].is_finite().all() and result[price].gt(0).all(), 'Finite positive original double closes only')
    need(result['close_us'].eq(result['open_us'] + MINUTE_US).all(), 'All closes describe the same logical one-minute endpoint')
    return result.sort('open_us')


def complete_calendar(frame, start, end):
    need(end > start and (end - start) % MINUTE_US == 0 and start % MINUTE_US == 0,
         'Explicit aligned closed-minute calendar')
    expected = (end - start) // MINUTE_US
    need(frame.height == expected and frame['open_us'][0] == start and frame['open_us'][-1] == end - MINUTE_US
         and frame['open_us'].diff().drop_nulls().eq(MINUTE_US).all(),
         'Every source must have the entire exact common calendar; no missing/duplicate/outside rows')


def join_prices(spot, mark, index, start, end):
    for frame in (spot, mark, index):
        complete_calendar(frame, start, end)
    joined = spot.join(mark.rename({'close_us': 'mark_close_us'}), on='open_us', how='inner', validate='1:1')
    joined = joined.join(index.rename({'close_us': 'index_close_us'}), on='open_us', how='inner', validate='1:1').sort('open_us')
    need(joined.height == (end - start) // MINUTE_US
         and joined['close_us'].eq(joined['mark_close_us']).all()
         and joined['close_us'].eq(joined['index_close_us']).all(), 'Exact three-close common calendar and endpoints required')
    return joined.select('open_us', 'close_us', 'spot_close', 'mark_close', 'index_close')


def basis_path(joined):
    """Polars arithmetic and cumulative maxima under the fixed window convention."""
    need(joined.height > 0 and all(joined[name].is_finite().all() and joined[name].gt(0).all()
        for name in ('spot_close', 'mark_close', 'index_close')), 'Finite positive source closes')
    s0 = float(joined['spot_close'][0])
    path = joined.with_columns((pl.col('mark_close') - pl.col('spot_close')).alias('basis'),
        (pl.col('mark_close') - pl.col('index_close')).alias('mark_index'),
        (pl.col('index_close') - pl.col('spot_close')).alias('index_spot'))
    path = path.with_columns([((pl.col(name) - float(path[name][0])) / s0 * 10000).alias(name + '_change_bp')
                             for name in PREFIXES])
    path = path.with_columns([(-pl.col(name + '_change_bp')).alias(name + '_valuation_change_bp') for name in PREFIXES])
    path = path.with_columns([(pl.col(name + '_valuation_change_bp').cum_max().clip(lower_bound=0)
        - pl.col(name + '_valuation_change_bp')).alias(name + '_drawdown_bp') for name in PREFIXES])
    level_error = (path['basis'] - path['mark_index'] - path['index_spot']).abs() / s0 * 10000
    change_error = (path['basis_change_bp'] - path['mark_index_change_bp'] - path['index_spot_change_bp']).abs()
    need(float(level_error.max()) <= TOLERANCE_BP and float(change_error.max()) <= TOLERANCE_BP,
         'Decomposition uses the same fixed S0 and preserves both levels and changes')
    return path


def window_statistics(joined):
    path = basis_path(joined)
    result = dict(rows=path.height, first_open_us=int(path['open_us'][0]), last_open_us=int(path['open_us'][-1]),
        first_close_us=int(path['close_us'][0]), last_close_us=int(path['close_us'][-1]),
        spot_close_start=float(path['spot_close'][0]), spot_close_end=float(path['spot_close'][-1]),
        mark_close_start=float(path['mark_close'][0]), mark_close_end=float(path['mark_close'][-1]),
        index_close_start=float(path['index_close'][0]), index_close_end=float(path['index_close'][-1]),
        denominator_S0=float(path['spot_close'][0]), quantity_per_leg=1, initial_valuation_change_bp=0.,
        scope='FIXED_COIN_QUANTITY_MARKED_PRICE_DIFFERENCE_NOT_CASH_PNL_OR_CAPITAL_RETURN',
        extrema_ties='FIRST_CHRONOLOGICAL_ROW', components={})
    for name in PREFIXES:
        change, valuation, drawdown = (path[name + suffix] for suffix in ('_change_bp', '_valuation_change_bp', '_drawdown_bp'))
        indices = dict(max_adverse=int(change.arg_max()), max_favorable=int(change.arg_min()), max_drawdown=int(drawdown.arg_max()))
        fields = ('open_us', 'close_us', 'spot_close', 'mark_close', 'index_close', name,
                  name + '_change_bp', name + '_valuation_change_bp', name + '_drawdown_bp')
        stats = dict(start_difference=float(path[name][0]), end_difference=float(path[name][-1]),
            terminal_change_bp=float(change[-1]), terminal_valuation_change_bp=float(valuation[-1]),
            max_adverse_change_bp=max(0., float(change.max())), max_favorable_change_bp=max(0., -float(change.min())),
            max_valuation_drawdown_bp=float(drawdown.max()), initial_zero_in_running_peak=True,
            witnesses={label:path.select(*fields).row(position, named=True) for label, position in indices.items()})
        if name == 'basis':
            result.update(stats)
        else:
            result['components'][name] = stats
    result['maximum_decomposition_level_error_bp'] = float(((path['basis'] - path['mark_index'] - path['index_spot']).abs()
                                                           / result['denominator_S0'] * 10000).max())
    result['maximum_decomposition_change_error_bp'] = float((path['basis_change_bp'] - path['mark_index_change_bp']
                                                           - path['index_spot_change_bp']).abs().max())
    return result


def allowed_path(row):
    need(row['symbol'] in SYMBOLS and row['month'] in MONTHS and row['kind'] in KINDS, 'Explicit authorized price scope')
    expected = ROOT / 'data/normalized/spot' / row['symbol'] / '1m' / (row['month'] + '.parquet') if row['kind'] == 'spot1m' else (
        PRICE_STATE / (row['kind'] + '-' + row['symbol'] + '-' + row['month']) / 'source.parquet')
    need(Path(row['parquet_path']).resolve() == expected.resolve() and not expected.is_symlink(), 'Exact existing source path, never source discovery/locked')
    opened, closed = month_bounds(row['month'])
    need(row['rows'] == (closed - opened) // MINUTE_US, 'Existing complete month metadata')
    return expected, opened, closed


def accepted_options(spec):
    need(spec['source_options_path'] == OPTIONS_PATH and spec['source_options_sha256'] == OPTIONS_SHA, 'Original metadata selection binding')
    saved = project_json(OPTIONS_PATH, OPTIONS_SHA)
    need(saved['status'] == 'READONLY_METADATA_NOT_QA_NOT_ECONOMICS' and saved['source_file_count'] == 24
         and saved['source_calendar'] == list(MONTHS) and not saved['Parquet_bytes_or_rows_read'], 'Source options remain metadata-only')
    expected = {(kind, symbol, month) for kind in KINDS for symbol in SYMBOLS for month in MONTHS}
    rows = saved['sources']
    need(len(rows) == 24 and {(r['kind'], r['symbol'], r['month']) for r in rows} == expected, 'Exactly all24 selected sources')
    for row in rows:
        allowed_path(row)
    for name, digest in saved['source_proofs'].items():
        path = ROOT / name
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve()) and sha(path) == digest,
             'Original small source proof changed: ' + name)
    return rows


def verify_spec(spec):
    need(spec['contract_id'] == 'BASIS_RISK_DIAGNOSTIC_V1' and spec['period_start'] == '2025-08-01'
         and spec['period_end_exclusive'] == '2025-12-01' and spec['symbols'] == list(SYMBOLS)
         and spec['source_calendar'] == list(MONTHS) and spec['math'] == MATH,
         'Only preregistered full122day same-quantity close-proxy math')
    need(spec['expected_files'] == 24 and spec['expected_minutes_per_symbol'] == 175680
         and 0 < spec['maximum_new_owned_bytes'] <= 10_000_000 and 0 < spec['maximum_wall_seconds'] <= 600,
         'Fixed small bounded scope')
    need(spec['coupon_headroom_context_bp'] == {'BTCUSDT': 116.6165, 'ETHUSDT': 90.6858}, 'Existing conditional context values only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true'); mode.add_argument('--research', action='store_true')
    for name in ('protocol', 'run-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--experiment-id', required=True)
    args = parser.parse_args()
    work, output, protocol = args.run_dir.resolve(), args.output.resolve(), args.protocol.resolve()
    need(work.is_relative_to(STATE.resolve()) and not work.exists() and output.is_relative_to((ROOT / 'reports/fast_research').resolve())
         and not output.exists() and os.environ.get('COIN_TASK_ID'), 'Exclusive STATE/output with actual bounded/progress wrapper')
    resources.status()
    need(sys.prefix == str(STATE / 'v8-clean-env-20261002-v2'), 'Frozen clean interpreter required')
    spec = project_json(protocol); verify_spec(spec)
    hashes = {name:sha(ROOT / name) for name in spec['frozen_sources']}
    need(hashes == spec['frozen_sources'] and TEST in hashes and 'environments/v8/uv.lock' in hashes, 'Explicit current source/test/environment binding')
    hashes.update({str(protocol.relative_to(ROOT)):sha(protocol), str(Path(__file__).resolve().relative_to(ROOT)):sha(__file__)})
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    test_command = [sys.executable, '-m', 'pytest', TEST, '-q', '--basetemp=' + str(work / 'pytest'),
        '-o', 'cache_dir=' + str(work / 'pytest-cache'), '--junitxml=' + str(work / 'junit.xml')]
    binding = dict(git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_hashes=hashes, protocol_sha256=sha(protocol), task_id=os.environ['COIN_TASK_ID'], sys_prefix=sys.prefix,
        exact_command=shlex.join(command), exact_test_command=shlex.join(test_command) if args.smoke else None,
        environment_lock_sha256=hashes['environments/v8/uv.lock'], mathematical_convention=MATH,
        data_scope='SYNTHETIC_ONLY' if args.smoke else 'FIXED24_PRICE_CLOSE_FILES_AUG2025_NOV2025')
    work.mkdir(); write_json(work / 'RUN_BINDING.json', binding)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ':START', event_type='OPERATIONAL_START',
        git_commit=binding['git_commit'], data_manifest_hash=OPTIONS_SHA, protocol_hash=binding['protocol_sha256'],
        feature_set='SPOT_MARK_INDEX_ORIGINAL_MINUTE_CLOSES', labels='NONE', model_family='NONE',
        hyperparameters=MATH, seed='NONE_DETERMINISTIC', thresholds='NO_TRADING_OR_OPTIMIZATION_THRESHOLDS',
        cost_assumptions='NONE_NO_FEES_COMPUTED;_CONDITIONAL_COUPON_CONTEXT_DIFFERENT_UNITS_NOT_ADDED',
        all_folds='ALL122D_PLUS_EACH_FOUR_UTC_MONTHS_SEPARATE_BASELINES', success_failure='START_BEFORE_PRICE_READ',
        reason_for_next_experiment='Diagnose basis valuation risk scale before further carry investment engineering',
        result_influenced_later_choice=False, source_hashes=hashes, exact_command=binding['exact_command'],
        run_binding_sha256=sha(work / 'RUN_BINDING.json'))
    start = append_event(ROOT / 'reports/experiment_registry.jsonl', event)
    report = dict(status='FAIL_BASIS_RISK_DIAGNOSTIC', binding=binding, registration_start=start, run_dir=str(work),
        candidate_status='NO_QUALIFIED_CANDIDATE', capital_net_APR='NOT_EVALUABLE', models_fit=0, orders_sent=0, GPU=0,
        locked_consumed=False, price_arrays_read=False, funding_arrays_read=False, old_QA_or_tests_repeated=False,
        fees_fills_NAV_cash_PnL_or_realized_funding_computed=False, mark_close_is_execution_or_charge_price=False,
        funding_units_certified=False, price_unit='USDT_PER_COIN_SAME_SYMBOL', quantity_per_leg=1,
        coupon_headroom_context_bp=spec['coupon_headroom_context_bp'], coupon_context_is_different_unit=True,
        coupon_added_to_basis=False, no_monthly_strategy_or_cost_selection=True, completed_files=0, input_bindings=[], per_symbol=[],
        source_bytes_unchanged=False, limitations=['Close proxies, not executable basis or charge mark',
            'Funding unit, event cash, hedge net quantity and fee assets unresolved',
            'Capital/collateral, margin/liquidation/ADL and financing unresolved', 'Seen history, no investment/APR/unseen qualification'])
    progress = Progress(); progress.value['detail'] = '同币固定数量基差标记风险尺度；不计算现金、费用、净值或APR'
    started = time.monotonic()
    try:
        progress.update('读取已接受来源的小凭证', 0, 24, '价格文件')
        sources = accepted_options(spec)
        report['disk'] = dict(scan_started_utc=datetime.now(UTC).isoformat(),
            **disk.check(spec['maximum_new_owned_bytes']), scan_finished_utc=datetime.now(UTC).isoformat())
        if args.smoke:
            progress.update('唯一新数学与时间对齐合成验收', 0, 1, '用例')
            run = subprocess.run(test_command, cwd=ROOT, check=False)
            report['test_exit_code'] = run.returncode
            if (work / 'junit.xml').is_file():
                tree = ET.parse(work / 'junit.xml').getroot()
                report['junit_counts'] = {key:sum(int(s.attrib.get(key, 0)) for s in tree.iter('testsuite'))
                                        for key in ('tests', 'errors', 'failures', 'skipped')}
                report['junit_sha256'] = sha(work / 'junit.xml')
            need(run.returncode == 0 and report.get('junit_counts') == dict(tests=1, errors=0, failures=0, skipped=0), 'Only the new unique fixture must pass')
            report['status'] = SMOKE_STATUS
        else:
            smoke = project_json(spec['required_smoke_receipt'])
            need(smoke['status'] == SMOKE_STATUS and smoke['test_exit_code'] == 0 and not smoke['price_arrays_read']
                 and smoke['source_bytes_unchanged'] and smoke['binding']['source_hashes'] == hashes,
                 'Actual same-source synthetic acceptance required')
            smoke_task = json.loads((STATE / 'task-progress' / ('task-' + smoke['binding']['task_id'] + '.json')).read_bytes())
            need(smoke_task['status'] == 'completed' and smoke_task['exit_code'] == 0
                 and smoke_task['id'] == smoke['binding']['task_id'], 'Synthetic task must actually be closed with exit zero')
            report['accepted_smoke_sha256'] = sha(ROOT / spec['required_smoke_receipt'])
            for symbol in SYMBOLS:
                streams = {}
                for kind in KINDS:
                    months = []
                    for month in MONTHS:
                        row = next(r for r in sources if (r['kind'], r['symbol'], r['month']) == (kind, symbol, month))
                        path, opened, closed = allowed_path(row)
                        need(path.is_file() and sha(path) == row['parquet_sha256'], 'Actual explicitly selected Parquet bytes changed')
                        columns = ['open_us', 'close_us', 'close', 'symbol', 'valid_day'] if kind == 'spot1m' else ['timestamp_ms', 'close_time_ms', 'close']
                        report['price_arrays_read'] = True
                        frame = canonical_prices(kind, pl.read_parquet(path, columns=columns), symbol)
                        complete_calendar(frame, opened, closed)
                        need(sha(path) == row['parquet_sha256'], 'Source changed while read')
                        months.append(frame)
                        report['input_bindings'].append({key:row[key] for key in ('kind', 'symbol', 'month', 'parquet_path', 'parquet_sha256', 'rows',
                                                                                'source_receipt_path', 'source_receipt_sha256')})
                        report['completed_files'] = len(report['input_bindings'])
                        progress.update('已读取并绑定原价格close', report['completed_files'], 24, '价格文件')
                    streams[kind] = pl.concat(months).sort('open_us')
                joined = join_prices(*(streams[kind] for kind in KINDS), START_US, END_US)
                monthly = []
                for month in MONTHS:
                    opened, closed = month_bounds(month)
                    selected = joined.filter(pl.col('open_us').is_between(opened, closed, closed='left'))
                    monthly.append(dict(month=month, baseline_scope='MONTH_LOCAL_DESCRIPTIVE_NOT_ACCOUNT_RESET', **window_statistics(selected)))
                report['per_symbol'].append(dict(symbol=symbol, full_period=window_statistics(joined), months=monthly))
                progress.update('基差标记风险已计算', report['completed_files'], 24, '价格文件', 已完成币种=len(report['per_symbol']))
            report['status'] = ACTUAL_STATUS
        need(time.monotonic() - started <= spec['maximum_wall_seconds'], 'Fixed wall budget exceeded')
        need(hashes == {name:sha(ROOT / name) for name in hashes}, 'Frozen source bytes changed during task')
        report['source_bytes_unchanged'] = True
    except Exception as error:
        report.update(status='FAIL_BASIS_RISK_DIAGNOSTIC', error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic() - started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            owned_bytes=sum(path.stat().st_size for path in work.rglob('*') if path.is_file()), resources=resources.status())
        if report['owned_bytes'] > spec['maximum_new_owned_bytes']:
            report.update(status='FAIL_BASIS_RISK_DIAGNOSTIC', reason='Actual owned output budget exceeded')
        write_json(output, report)
        append_event(ROOT / 'reports/experiment_registry.jsonl', dict(event, event_id=args.experiment_id + ':RESULT', event_type='OPERATIONAL_RESULT',
            success_failure=report['status'], artifact_path=str(output.relative_to(ROOT)), artifact_sha256=sha(output)))
        progress.stop.set(); progress.thread.join(timeout=3)
    need(report['status'] in (SMOKE_STATUS, ACTUAL_STATUS), 'Failed result preserved')
    print(json.dumps(dict(status=report['status'], output=str(output), sha256=sha(output))))


if __name__ == '__main__':
    main()
