"""Funding-only fixed-period coupon and two-leg opening/closing hurdle.

No price, quantity, fills, NAV, financing, margin, basis, forecasts or APR engine.
Coupon is the signed rate sum per fixed event nominal, not actual account cash.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal
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
START_MS = 1754006400000
END_MS = 1764547200000
BP_MULTIPLIER = Decimal(10000)
SCHEMA = {'calc_time_ms': pl.Int64, 'funding_interval_hours': pl.Float64, 'last_funding_rate': pl.Float64}
SOURCE_STATE = STATE / 'v8-funding-mark-index-source-20261002-v1'
PROBE_STATUS = 'PASS_OFFICIAL_FUNDING_DOCUMENTARY_SEMANTICS_AND_SAMPLED_API_PARITY'
SMOKE_STATUS = 'PASS_FUNDING_INCOME_DIAGNOSTIC_SYNTHETIC_NOT_MARKET_RESULT'
ACTUAL_STATUS = 'COMPLETE_FUNDING_ONLY_COUPON_COST_HURDLE_DIAGNOSTIC_NOT_APR'


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_json(path, expected=None):
    path = Path(path)
    path = path if path.is_absolute() else ROOT / path
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
        and path.stat().st_size < 2_000_000, 'Ordinary explicit small project receipt required')
    require(expected is None or file_sha(path) == expected, 'Frozen project receipt changed: ' + str(path))
    return json.loads(path.read_text())


def exclusive_json(path, value):
    with Path(path).open('x') as writer:
        json.dump(value, writer, ensure_ascii=False, indent=2, allow_nan=False)
        writer.write('\n')


def cost_hurdles(costs):
    require(costs == dict(spot_fee_bps_per_side=10, perp_taker_fee_bps_per_side=5.5,
        assumed_slippage_bps_per_side=4, assumed_each_leg_roundtrip_spread_bps=[2, 4, 8]),
        'Only the fixed ordinary Spot/perp-taker cost hypotheses')
    fee = 2 * Decimal(str(costs['spot_fee_bps_per_side'])) + 2 * Decimal(str(costs['perp_taker_fee_bps_per_side']))
    result = [dict(scenario='FEE_ONLY', fee_bps=float(fee), assumed_spread_bps=0.,
                   assumed_slippage_bps=0., total_hurdle_bps=float(fee))]
    for spread in costs['assumed_each_leg_roundtrip_spread_bps']:
        both_leg_spread = 2 * Decimal(str(spread))
        four_fill_slip = 4 * Decimal(str(costs['assumed_slippage_bps_per_side']))
        result.append(dict(scenario='ASSUMED_EACH_LEG_RT_SPREAD_' + str(spread), fee_bps=float(fee),
            assumed_spread_bps=float(both_leg_spread), assumed_slippage_bps=float(four_fill_slip),
            total_hurdle_bps=float(fee + both_leg_spread + four_fill_slip)))
    return result


def validate_units(spec, probe):
    require(spec['funding_rate_unit'] == 'FRACTION' and spec['bp_multiplier'] == 10000,
            'Explicit fraction contract and10000bp multiplier required; no inferred scale')
    require(spec['unit_probe']['basis'] == 'SAMPLED_API_PARITY' and
            spec['unit_probe']['required_status'] == PROBE_STATUS, 'No automatic assumption fallback')
    require(probe['status'] == PROBE_STATUS and probe['funding_rate_unit'] == 'FRACTION' and
            probe['bp_multiplier'] == 10000, 'Official unit probe must support the explicit fraction interpretation')
    return dict(raw_rate_unit='FRACTION', bp_multiplier=10000,
        qualification=probe['unit_evidence'], full_732_event_unit_certified=False,
        calc_time_publication_or_exact_account_charge_certified=False,
        realized_rate_is_available_trading_signal=False)


def _statistics(rows):
    cumulative, peak, drawdown = Decimal(0), Decimal(0), Decimal(0)
    positive, negative = Decimal(0), Decimal(0)
    positive_count = negative_count = zero_count = current_run = longest_run = 0
    run_coupon, worst_run = Decimal(0), Decimal(0)
    completed_runs, prefixes = [], []
    for stamp, raw in rows:
        bp = Decimal(str(raw)) * BP_MULTIPLIER
        cumulative += bp
        peak = max(peak, cumulative)  # Includes the initial0 coupon before the first event.
        drawdown = max(drawdown, peak - cumulative)
        if bp < 0:
            negative_count += 1; negative += bp
            current_run += 1; run_coupon += bp
            longest_run = max(longest_run, current_run)
            worst_run = min(worst_run, run_coupon)
        else:
            if current_run:
                completed_runs.append(dict(events=current_run, signed_coupon_bp=float(run_coupon)))
            current_run, run_coupon = 0, Decimal(0)  # Exact0 also breaks a strictly negative run.
            if bp > 0:
                positive_count += 1; positive += bp
            else:
                zero_count += 1
        prefixes.append(dict(calc_time_ms=int(stamp), coupon_bp=float(bp),
            cumulative_coupon_bp=float(cumulative), prefix_coupon_drawdown_bp=float(peak - cumulative)))
    if current_run:
        completed_runs.append(dict(events=current_run, signed_coupon_bp=float(run_coupon)))
    return dict(events=len(rows), signed_coupon_bp=float(cumulative), positive_coupon_bp=float(positive),
        negative_coupon_bp=float(negative), positive_events=positive_count, negative_events=negative_count,
        zero_events=zero_count, longest_negative_run_events=longest_run,
        worst_negative_run_signed_coupon_bp=float(worst_run), negative_runs=completed_runs,
        max_prefix_coupon_drawdown_bp=float(drawdown), initial_coupon_bp=0.,
        drawdown_scope='ABSOLUTE_COUPON_BP_DIFFERENCE_NOT_NAV_MDD'), prefixes


def coupon_statistics(events):
    require(set(events.columns) == {'symbol', *SCHEMA}, 'Only bound funding fields, no price/signal inputs')
    require(events.schema == {'symbol': pl.String, **SCHEMA} or
        all(events.schema[name] == dtype for name, dtype in {'symbol': pl.String, **SCHEMA}.items()),
        'Original integer-ms/float funding schema required')
    require(events.height > 0 and set(events['symbol'].unique().to_list()) == set(SYMBOLS), 'Fixed complete two-symbol universe')
    require(events.null_count().to_numpy().sum() == 0 and events.height == events.unique(['symbol','calc_time_ms']).height,
        'No missing/duplicate funding values')
    require(events.filter((pl.col('calc_time_ms') < START_MS) | (pl.col('calc_time_ms') >= END_MS)).is_empty(),
        'Fixed2025Aug-Nov only; no time rescale or locked access')
    require(events['last_funding_rate'].is_finite().all() and events['funding_interval_hours'].is_finite().all()
        and (events['funding_interval_hours'] > 0).all(), 'Finite raw rates and actual reported positive intervals')
    result, prefix_rows = [], []
    for symbol in SYMBOLS:
        frame = events.filter(pl.col('symbol') == symbol).sort('calc_time_ms')
        rows = list(frame.select('calc_time_ms', 'last_funding_rate').iter_rows())
        stats, prefixes = _statistics(rows)
        months = []
        for month in MONTHS:
            selected = [(stamp, rate) for stamp, rate in rows
                if datetime.fromtimestamp(stamp / 1000, UTC).strftime('%Y-%m') == month]
            monthly, _ = _statistics(selected)
            monthly.update(month=month, monthly_costs_subtracted=False,
                run_and_coupon_drawdown_scope='MONTH_LOCAL_DESCRIPTIVE_PREFIX_NOT_ACCOUNT_RESET')
            months.append(monthly)
        positive_month_sum = sum(Decimal(str(row['positive_coupon_bp'])) for row in months)
        # Concentration of positive monthly NET signed coupon, not selected events.
        positive_month_nets = [Decimal(str(row['signed_coupon_bp'])) for row in months if row['signed_coupon_bp'] > 0]
        positive_month_net_sum = sum(positive_month_nets, Decimal(0))
        stats.update(symbol=symbol, months=months, reported_interval_hours=sorted(frame['funding_interval_hours'].unique().to_list()),
            first_calc_time_ms=int(frame['calc_time_ms'][0]), last_calc_time_ms=int(frame['calc_time_ms'][-1]),
            positive_month_count=len(positive_month_nets),
            max_positive_month_contribution_share=float(max(positive_month_nets)/positive_month_net_sum) if positive_month_net_sum else None,
            monthly_positive_events_coupon_bp=float(positive_month_sum),
            negative_run_duration_or_exposure_inferred=False)
        result.append(stats)
        prefix_rows.extend(dict(symbol=symbol, **row) for row in prefixes)
    return result, pl.DataFrame(prefix_rows)


def accepted_sources(spec):
    acceptance = project_json(spec['source_acceptance_path'], spec['source_acceptance_sha256'])
    require(acceptance['status'] == 'PASS_NEW_OFFICIAL_INPUT_SOURCE_FORMAT_ONLY_INDEPENDENT_QA', 'Accepted independent source format required')
    qa = project_json(acceptance['independent_qa_path'], acceptance['independent_qa_sha256'])
    require(qa['status'] == 'PASS_OFFICIAL_CARRY_INPUT_FORMAT_ONLY_INDEPENDENT_QA', 'Original independent QA changed')
    project_json(acceptance['producer_path'], acceptance['producer_sha256'])
    selected = [row for row in acceptance['sources'] if row['kind'] == 'fundingRate']
    require(len(selected) == 8 and {(v['symbol'],v['month']) for v in selected} ==
        {(symbol, month) for symbol in SYMBOLS for month in MONTHS}, 'Exactly the eight accepted funding sources')
    for row in selected:
        expected = SOURCE_STATE / ('fundingRate-' + row['symbol'] + '-' + row['month'])
        require(Path(row['parquet_path']).resolve() == (expected / 'source.parquet').resolve() and
                Path(row['receipt_path']).resolve() == (expected / 'receipt.json').resolve(), 'Exact accepted STATE path; no discovery')
        receipt_path = Path(row['receipt_path'])
        require(receipt_path.is_file() and not receipt_path.is_symlink() and file_sha(receipt_path) == row['receipt_sha256'],
            'Accepted original per-file receipt changed')
        receipt = json.loads(receipt_path.read_text())
        require(receipt['parquet_sha256'] == row['parquet_sha256'] and receipt['stats']['rows'] == row['rows'] and
            receipt['stats']['schema'] == 'calc_time_ms: int64\nfunding_interval_hours: double\nlast_funding_rate: double',
            'Accepted published input binding/schema changed')
        checked = [v for v in qa['sources'] if v['kind'] == 'fundingRate' and
            (v['symbol'],v['month']) == (row['symbol'],row['month'])]
        require(len(checked) == 1 and checked[0]['status'] == 'PASS_SOURCE_FORMAT_ONLY' and
            checked[0]['receipt_sha256'] == row['receipt_sha256'] and checked[0]['all_published_values_equal_raw']
            and checked[0]['zip_crc_full_read'], 'Existing independent per-file QA binding required')
    require(sum(row['rows'] for row in selected) == 732, 'Exact accepted fullperiod732 funding events')
    return selected


def verify_spec(spec):
    require(spec['contract_id'] == 'FUNDING_INCOME_DIAGNOSTIC_V1' and
        spec['period_start'] == '2025-08-01' and spec['period_end_exclusive'] == '2025-12-01' and
        spec['symbols'] == list(SYMBOLS) and spec['source_calendar'] == list(MONTHS), 'Only fixed122day full two-symbol income scope')
    cost_hurdles(spec['costs'])
    require(0 < spec['maximum_new_owned_bytes'] <= 10_000_000 and 0 < spec['maximum_wall_seconds'] <= 600,
        'Small bounded diagnostics budget only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true'); mode.add_argument('--research', action='store_true')
    for name in ('protocol', 'run-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--experiment-id', required=True)
    args = parser.parse_args()
    work, output, protocol_path = args.run_dir.resolve(), args.output.resolve(), args.protocol.resolve()
    require(work.is_relative_to(STATE.resolve()) and not work.exists(), 'Exclusive new D-hosted STATE run')
    require(output.is_relative_to((ROOT / 'reports/fast_research').resolve()) and not output.exists(), 'Exclusive small report')
    require(os.environ.get('COIN_TASK_ID'), 'Use actual bounded/progress wrapper')
    resources.status()
    spec = project_json(protocol_path); verify_spec(spec)
    test_path = 'tests/test_funding_income_diagnostic.py'
    hashes = {name:file_sha(ROOT / name) for name in spec['frozen_sources']}
    require(hashes == spec['frozen_sources'], 'Frozen source bytes changed before operation')
    require(test_path in hashes and 'environments/v8/uv.lock' in hashes, 'Explicit new test and unchanged environment binding')
    hashes.update({str(protocol_path.relative_to(ROOT)):file_sha(protocol_path),
        str(Path(__file__).resolve().relative_to(ROOT)):file_sha(__file__)})
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    test_command = [sys.executable, '-m', 'pytest', test_path, '-q', '--basetemp='+str(work/'pytest'),
        '-o', 'cache_dir='+str(work/'pytest-cache'), '--junitxml='+str(work/'junit.xml')]
    binding = dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes=hashes, protocol_sha256=file_sha(protocol_path), exact_command=shlex.join(command),
        exact_test_command=shlex.join(test_command) if args.smoke else None,
        task_id=os.environ['COIN_TASK_ID'], sys_prefix=sys.prefix, python=sys.executable,
        environment_lock_sha256=hashes['environments/v8/uv.lock'], data_scope='SYNTHETIC_ONLY' if args.smoke else 'FIXED_732_FUNDING_EVENTS_ONLY')
    work.mkdir(); exclusive_json(work/'RUN_BINDING.json',binding)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',event_type='OPERATIONAL_START',
        git_commit=binding['git_commit'],data_manifest_hash=hashes[test_path] if args.smoke else spec['source_acceptance_sha256'],
        protocol_hash=binding['protocol_sha256'],feature_set='FUNDING_EVENT_RATES_ONLY',labels='NONE',model_family='NONE',
        hyperparameters='FIXED_FULL122D_BTC_ETH_UNIT_NOMINAL_COUPON',seed='NONE_DETERMINISTIC',
        thresholds='NO_TRADE_THRESHOLDS;_31_51_55_63BP_COST_HURDLES',cost_assumptions=spec['costs'],
        all_folds='2025-08-01..<2025-12-01_BTC_ETH_SEPARATE',success_failure='START',
        reason_for_next_experiment='Determine income/cost headroom before any two-leg carry engine or APR claim',
        result_influenced_later_choice=False,source_hashes=hashes,exact_command=binding['exact_command'],
        run_binding_sha256=file_sha(work/'RUN_BINDING.json'))
    registered = append_event(ROOT/'reports/experiment_registry.jsonl',event)
    report = dict(status='FAIL_FUNDING_INCOME_DIAGNOSTIC',binding=binding,registration_start=registered,
        run_dir=str(work),market_inputs_read=False,mark_index_spot_arrays_read=False,raw_zip_or_source_QA_repeated=False,
        locked_consumed=False,models_fit=0,orders_sent=0,GPU=0,candidate_status='NO_QUALIFIED_CANDIDATE',
        capital_net_APR='NOT_EVALUABLE',fills_NAV_or_realized_funding_cash_computed=False,
        normalized_coupon_scope='SIGNED_RATE_SUM*10000;_FIXED_SINGLE_LEG_EVENT_NOMINAL_NOT_CONSTANT_QUANTITY_CASH',
        paired_fee_scope='ONE_FULL_MATCHED_NOMINAL_TWO_LEG_OPEN_AND_CLOSE_ACROSS_ALL122D_NOT_PER_MONTH',
        unknowns=['Both-leg quantity and execution','actual account/venue funding cash and fee assets','collateral/capital denominator',
            'margin/liquidation/ADL','basis PnL','financing/transfer/dust','historical executable spread/slippage'],
        source_bytes_unchanged=False)
    started = time.monotonic(); progress = Progress()
    progress.value['detail'] = '固定全期资金费coupon与双腿成本门槛；没有NAV或净APR'
    try:
        progress.update('核对单位与来源凭证',0,8,'资金费文件')
        probe = project_json(spec['unit_probe']['path'],spec['unit_probe']['sha256'])
        report['unit_interpretation'] = validate_units(spec,probe)
        report['unit_probe_sha256'] = spec['unit_probe']['sha256']
        sources = accepted_sources(spec)
        report['disk'] = dict(scan_started_utc=datetime.now(UTC).isoformat(),
            **disk.check(spec['maximum_new_owned_bytes']),scan_finished_utc=datetime.now(UTC).isoformat())
        if args.smoke:
            progress.update('唯一新coupon数值合成验收',0,1,'用例')
            run = subprocess.run(test_command,cwd=ROOT,check=False)
            report['test_exit_code'] = run.returncode
            if (work/'junit.xml').is_file():
                tree = ET.parse(work/'junit.xml').getroot()
                report['junit_counts'] = {key:sum(int(s.attrib.get(key,0)) for s in tree.iter('testsuite'))
                    for key in ('tests','errors','failures','skipped')}
                report['junit_sha256'] = file_sha(work/'junit.xml')
            require(run.returncode == 0 and report.get('junit_counts') == dict(tests=1,errors=0,failures=0,skipped=0),
                'Only the unique new numeric test must pass')
            report['status'] = SMOKE_STATUS
        else:
            smoke = project_json(spec['required_smoke_receipt'])
            require(smoke['status'] == SMOKE_STATUS and smoke['test_exit_code'] == 0 and smoke['source_bytes_unchanged']
                and not smoke['market_inputs_read'] and smoke['junit_counts'] == dict(tests=1,errors=0,failures=0,skipped=0),
                'Actual same-source synthetic acceptance required')
            require(smoke['binding']['source_hashes'] == hashes and smoke['unit_probe_sha256'] == spec['unit_probe']['sha256'],
                'Exact same source/protocol/unit probe as accepted synthetic run')
            report['accepted_smoke_sha256'] = file_sha(ROOT/spec['required_smoke_receipt'])
            frames, inputs = [], []
            report['input_bindings'] = inputs
            report['completed_files'],report['completed_events'] = 0,0
            for index,row in enumerate(sources,1):
                path = Path(row['parquet_path'])
                require(path.is_file() and not path.is_symlink() and file_sha(path) == row['parquet_sha256'], 'Actual accepted Parquet bytes changed')
                report['market_inputs_read'] = True
                frame = pl.read_parquet(path)
                require(frame.schema == SCHEMA and frame.height == row['rows'], 'Accepted funding field/count binding')
                frames.append(frame.with_columns(pl.lit(row['symbol']).alias('symbol')))
                require(file_sha(path) == row['parquet_sha256'], 'Input changed while consumed')
                inputs.append({key:row[key] for key in ('symbol','month','receipt_path','receipt_sha256','parquet_path','parquet_sha256','rows')})
                report['completed_files'],report['completed_events'] = len(inputs),sum(v['rows'] for v in inputs)
                progress.update('真实资金费来源已读取',index,8,'文件',实际事件=sum(v['rows'] for v in inputs))
            events = pl.concat(frames).select('symbol',*SCHEMA).sort('symbol','calc_time_ms')
            require(events.height == 732 and all(events.filter(pl.col('symbol')==symbol).height == 366 for symbol in SYMBOLS),
                'All accepted events, no selection of favorable rows/months')
            report['per_symbol'], prefix = coupon_statistics(events)
            hurdles = cost_hurdles(spec['costs']); report['cost_hurdles'] = hurdles
            for stats in report['per_symbol']:
                stats['coupon_minus_roundtrip_hurdle'] = [dict(**cost,
                    headroom_bp=float(Decimal(str(stats['signed_coupon_bp']))-Decimal(str(cost['total_hurdle_bps']))),
                    headroom_is_not_net_capital_return=True) for cost in hurdles]
            path = work/'coupon_prefix.parquet'; prefix.write_parquet(path)
            report['output_artifacts'] = [dict(path=str(path),sha256=file_sha(path),rows=prefix.height,
                schema={name:str(dtype) for name,dtype in prefix.schema.items()})]
            report['completed_files'],report['completed_events'] = 8,732
            report['status'] = ACTUAL_STATUS
            progress.update('全期coupon与四门槛已完成',732,732,'事件')
        require(time.monotonic()-started <= spec['maximum_wall_seconds'],'Wall budget exceeded')
        require(hashes == {name:file_sha(ROOT/name) for name in hashes},'Source bytes changed during execution')
        report['source_bytes_unchanged'] = True
    except Exception as error:
        report.update(status='FAIL_FUNDING_INCOME_DIAGNOSTIC',error_type=type(error).__name__,reason=str(error))
        raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(path.stat().st_size for path in work.rglob('*') if path.is_file()),resources=resources.status())
        if report['owned_bytes'] > spec['maximum_new_owned_bytes']:
            report.update(status='FAIL_FUNDING_INCOME_DIAGNOSTIC',reason='Actual owned output exceeds budget')
        exclusive_json(output,report)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',
            event_type='OPERATIONAL_RESULT',success_failure=report['status'],artifact_path=str(output.relative_to(ROOT)),
            artifact_sha256=file_sha(output)))
        progress.stop.set();progress.thread.join(timeout=3)
    require(report['status'] in (SMOKE_STATUS,ACTUAL_STATUS),'Diagnostic failed; preserved result')
    print(json.dumps(dict(status=report['status'],output=str(output),sha256=file_sha(output))))


if __name__ == '__main__':
    main()
