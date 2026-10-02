"""Independent raw-string Decimal funding coupon audit, no prices or execution."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, math, os, resource, sys, time, zipfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
AUDIT_STATE = STATE / 'test-funding-income-independent-audit-20261003-v1'
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
MONTHS = ('2025-08', '2025-09', '2025-10', '2025-11')
COUNTS = {'2025-08': 93, '2025-09': 90, '2025-10': 93, '2025-11': 90}
THRESHOLDS = (Decimal('31'), Decimal('51'), Decimal('55'), Decimal('63'))
BP = Decimal('10000')
ZERO = Decimal(0)
ACCEPTANCE = ROOT / 'reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json'
ACCEPTANCE_SHA = '318622721ed9733d84ae66082f750e8b7d4ed960d7812c9e899c94b3cb5188aa'


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write('\n')


def exact_decimal(raw):
    value = Decimal(raw)
    need(value.is_finite(), 'Nonfinite funding raw value')
    return value


def epoch_ms(month):
    return int(datetime.fromisoformat(month + '-01').replace(tzinfo=UTC).timestamp()) * 1000


def month_of_ms(value):
    return (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)).strftime('%Y-%m')


def raw_funding(entry):
    """Only the already accepted 8 funding archives, not the 16 price archives."""
    need(entry['kind'] == 'fundingRate' and entry['symbol'] in SYMBOLS and entry['month'] in MONTHS,
         'Nonfunding or out-of-scope source is forbidden')
    receipt_path = Path(entry['receipt_path'])
    zip_path = Path(entry['zip_path'])
    need(receipt_path.is_relative_to(STATE) and zip_path.is_relative_to(STATE), 'Funding path outside STATE')
    need(sha(receipt_path) == entry['receipt_sha256'], 'Accepted funding receipt identity changed')
    receipt = load(receipt_path)
    need(receipt['entry']['kind'] == 'fundingRate' and receipt['entry']['symbol'] == entry['symbol']
         and receipt['entry']['month'] == entry['month'], 'Funding receipt scope changed')
    need(receipt['zip_path'] == str(zip_path) and receipt['zip_sha256'] == entry['zip_sha256'],
         'Raw funding ZIP binding differs')
    need(sha(zip_path) == entry['zip_sha256'], 'Accepted raw funding ZIP bytes changed')
    need(zip_path.stat().st_size == entry['zip_bytes'], 'Accepted raw funding ZIP size changed')
    # Reuse the accepted Parquet identity as metadata. Do not replay source QA/read its values.
    need(receipt['parquet_path'] == entry['parquet_path']
         and receipt['parquet_sha256'] == entry['parquet_sha256'], 'Funding Parquet metadata differs')
    rows = []
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        need(len(members) == 1 and not members[0].is_dir(), 'Ambiguous funding CSV member')
        need(members[0].file_size < 100000, 'Unexpected funding archive expansion')
        with archive.open(members[0]) as stream, io.TextIOWrapper(stream, encoding='utf-8-sig', newline='') as text:
            reader = csv.reader(text)
            need(next(reader) == ['calc_time', 'funding_interval_hours', 'last_funding_rate'],
                 'Funding raw column/unit schema differs')
            for raw in reader:
                need(len(raw) == 3 and raw[0].isdigit(), 'Malformed funding raw row')
                timestamp = int(raw[0])
                hours, fraction = exact_decimal(raw[1]), exact_decimal(raw[2])
                need(hours > 0 and month_of_ms(timestamp) == entry['month'],
                     'Funding epoch-ms/month or nominal-hours boundary differs')
                rows.append({'calc_time_ms': timestamp, 'interval_hours': hours,
                             'rate': fraction, 'raw_rate_string': raw[2]})
    need(len(rows) == entry['rows'] == COUNTS[entry['month']], 'Funding monthly count differs')
    need(rows[0]['calc_time_ms'] == entry['first_timestamp_ms']
         and rows[-1]['calc_time_ms'] == entry['last_timestamp_ms'], 'Accepted funding boundary differs')
    need(all(a['calc_time_ms'] < b['calc_time_ms'] for a, b in zip(rows, rows[1:])),
         'Funding source events are not strictly chronological')
    return rows, {'kind': 'fundingRate', 'symbol': entry['symbol'], 'month': entry['month'],
                  'receipt_path': str(receipt_path), 'receipt_sha256': entry['receipt_sha256'],
                  'zip_path': str(zip_path), 'zip_sha256': entry['zip_sha256'],
                  'parquet_path': entry['parquet_path'], 'parquet_sha256': entry['parquet_sha256'],
                  'rows': len(rows), 'raw_decimal_parse': True, 'parquet_values_read': False}


def coupon_stats(rows):
    """Per-symbol normalized coupon; strict negatives, zero resets, initial prefix 0."""
    rates = [row['rate'] for row in rows]
    need(bool(rates), 'Empty coupon scope')
    negative = [rate for rate in rates if rate < 0]
    positive = [rate for rate in rates if rate > 0]
    runs, current = [], []
    prefix, peak, max_drawdown = ZERO, ZERO, ZERO
    for index, row in enumerate(rows):
        rate = row['rate']
        if rate < 0:
            current.append(row)
        elif current:
            runs.append(current)
            current = []
        prefix += rate * BP
        peak = max(peak, prefix)
        max_drawdown = max(max_drawdown, peak - prefix)
    if current:
        runs.append(current)
    longest = max(runs, key=lambda run: len(run), default=[])
    worst = min(runs, key=lambda run: sum((r['rate'] for r in run), ZERO), default=[])
    def run_value(run):
        return {'event_count': len(run), 'signed_sum_bps': str(sum((r['rate'] for r in run), ZERO) * BP),
                'first_calc_time_ms': run[0]['calc_time_ms'] if run else None,
                'last_calc_time_ms': run[-1]['calc_time_ms'] if run else None}
    total = sum(rates, ZERO) * BP
    return {'events': len(rows), 'positive_events': len(positive), 'negative_events': len(negative),
            'zero_events': sum(rate == 0 for rate in rates), 'sum_rate_fraction': str(sum(rates, ZERO)),
            'sum_funding_bps': str(total),
            'positive_sum_bps': str(sum(positive, ZERO) * BP),
            'negative_sum_bps': str(sum(negative, ZERO) * BP),
            'min_event_bps': str(min(rates) * BP), 'max_event_bps': str(max(rates) * BP),
            'negative_runs_count': len(runs), 'longest_negative_run': run_value(longest),
            'worst_negative_run': run_value(worst), 'coupon_drawdown_bps': str(max_drawdown),
            'cost_thresholds': [{'threshold_bps': str(cost), 'coupon_minus_threshold_bps': str(total-cost),
                                 'covers_threshold': total >= cost} for cost in THRESHOLDS]}


def float_decimal_check(observed, expected, context):
    """Fixed diagnostic tolerance, tighter than any economic bp and not outcome-selected."""
    need(isinstance(observed, (int, float)) and not isinstance(observed, bool) and math.isfinite(observed),
         context + ': missing/nonfinite reported numeric value')
    error = abs(Decimal.from_float(float(observed)) - Decimal(expected))
    tolerance = Decimal('0.000000001')
    need(error <= tolerance, context + ': reported float differs from raw Decimal by >1e-9 bp')
    return {'absolute_error_bps': str(error), 'tolerance_bps': str(tolerance)}

# The CLI/report mapping will be appended only after the new frozen contract/source schema is read.
# No real funding event has been read or statistics computed during preparation.

def task_evidence(identity, expected_status="completed", expected_code=0):
    need(isinstance(identity, str) and len(identity) == 32 and all(c in '0123456789abcdef' for c in identity),
         'Invalid actual task identity')
    path = STATE / 'task-progress' / ('task-' + identity + '.json')
    value = load(path)
    need(value['id'] == identity and value['status'] == expected_status and value['exit_code'] == expected_code,
         'Actual wrapper task status/exit differ from explicitly required outcome')
    need(type(value.get('pid')) is int and type(value.get('start_ticks')) is int,
         'Actual child process identity missing')
    return {'path': str(path), 'sha256': sha(path), **{key: value[key] for key in
            ('id', 'status', 'exit_code', 'pid', 'start_ticks', 'started_at', 'ended_at')}}


def progress(completed):
    identity = os.environ['COIN_TASK_ID']
    path = STATE / 'task-progress' / ('task-' + identity + '.json')
    value = load(path)
    value.update(phase='独立原CSV Decimal券息核验', completed=completed, total=8,
                 unit='资金费档', last_activity_at=time.time())
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)


def compare_stats(observed, exact, label):
    mapping = {'signed_coupon_bp': 'sum_funding_bps', 'positive_coupon_bp': 'positive_sum_bps',
               'negative_coupon_bp': 'negative_sum_bps', 'max_prefix_coupon_drawdown_bp': 'coupon_drawdown_bps',
               'worst_negative_run_signed_coupon_bp': None}
    errors = {}
    need(Decimal(observed['signed_raw_rate_sum_decimal']) == Decimal(exact['sum_rate_fraction']),
         label + ':exact raw rate sum before assumed unit interpretation')
    errors['signed_raw_rate_sum'] = float_decimal_check(observed['signed_raw_rate_sum'] * 10000,
                                                        exact['sum_funding_bps'], label+':raw sum assumed bp')
    for key, wanted in mapping.items():
        expected_value = exact[wanted] if wanted is not None else exact['worst_negative_run']['signed_sum_bps']
        errors[key] = float_decimal_check(observed[key], expected_value, label + ':' + key)
    for key in ('events', 'positive_events', 'negative_events', 'zero_events'):
        need(type(observed[key]) is int and observed[key] == exact[key], label + ':' + key)
    need(observed['longest_negative_run_events'] == exact['longest_negative_run']['event_count'],
         label + ':longest strict negative run')
    need(observed['initial_coupon_bp'] == 0 and observed['drawdown_scope'] ==
         'ABSOLUTE_COUPON_BP_DIFFERENCE_NOT_NAV_MDD', label + ':coupon drawdown interpretation')
    return errors


def independent_runs(rows):
    result, run = [], []
    for row in rows:
        if row['rate'] < 0:
            run.append(row['rate'])
        elif run:
            result.append({'events': len(run), 'signed_coupon_bp': sum(run, ZERO) * BP})
            run = []
    if run:
        result.append({'events': len(run), 'signed_coupon_bp': sum(run, ZERO) * BP})
    return result


def verify_run_list(observed, rows, label):
    expected_runs = independent_runs(rows)
    need(len(observed) == len(expected_runs), label + ':negative run count')
    for index, (actual, exact) in enumerate(zip(observed, expected_runs)):
        need(actual['events'] == exact['events'], label + ':negative run events')
        float_decimal_check(actual['signed_coupon_bp'], exact['signed_coupon_bp'], label + ':negative run ' + str(index))


def verify_prefix(path, by_symbol):
    # New derived coupon output only; never read an original price/mark/index/Parquet array.
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pq.read_table(path)
    need(table.column_names == ['symbol', 'calc_time_ms', 'coupon_bp', 'cumulative_coupon_bp', 'prefix_coupon_drawdown_bp'],
         'Unexpected coupon prefix columns')
    need(table.schema.types == [pa.string(), pa.int64(), pa.float64(), pa.float64(), pa.float64()],
         'Coupon prefix physical schema changed')
    observed = table.to_pylist()
    need(len(observed) == 732, 'Coupon prefix must retain all732 funding events')
    position, maximum_error = 0, ZERO
    for symbol in SYMBOLS:
        prefix, peak = ZERO, ZERO
        for row in by_symbol[symbol]:
            actual = observed[position]
            need(actual['symbol'] == symbol and actual['calc_time_ms'] == row['calc_time_ms'],
                 'Coupon prefix time/symbol/order disagreement')
            bp = row['rate'] * BP
            prefix += bp
            peak = max(peak, prefix)
            for key, wanted in (('coupon_bp', bp), ('cumulative_coupon_bp', prefix),
                                ('prefix_coupon_drawdown_bp', peak - prefix)):
                error = float_decimal_check(actual[key], wanted, symbol + ':' + str(position) + ':' + key)
                maximum_error = max(maximum_error, Decimal(error['absolute_error_bps']))
            position += 1
    return {'rows_verified': position, 'maximum_absolute_error_bps': str(maximum_error),
            'tolerance_bps': '0.000000001', 'includes_initial0_in_calculation': True,
            'actual_initial0_output_row_required': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(args.run_dir.resolve() == AUDIT_STATE and args.binding.resolve() == AUDIT_STATE / 'ACTUAL_BINDING.json',
         'Exclusive predetermined independent STATE required')
    need(args.output.resolve() == ROOT / 'reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json'
         and not args.output.exists(), 'Exclusive new independent report required')
    need(sys.prefix == str(STATE / 'v8-clean-env-20261002-v2'), 'Frozen clean Python interpreter required')
    need(os.environ.get('COIN_TASK_ID') and os.environ.get('POLARS_MAX_THREADS') == '2'
         and os.environ.get('OPENBLAS_NUM_THREADS') == '2', 'Bounded CPU2 progress invocation required')
    frozen = load(args.binding)
    need(sha(__file__) == frozen['checker_sha256'], 'Independent checker changed after binding')
    report = {'status': 'FAIL_CONDITIONAL_RAW_FRACTION_ASSUMPTION_DECIMAL_COUPON_AUDIT',
              'binding': {'task_id': os.environ['COIN_TASK_ID'], 'checker_sha256': sha(__file__),
                          'actual_report': frozen['actual_report'], 'actual_report_sha256': frozen['actual_report_sha256'],
                          'ACTUAL_BINDING_sha256': sha(args.binding), 'exact_command': [sys.executable, *sys.argv]},
              'independent_source': str(Path(__file__).resolve()), 'independent_source_sha256': sha(__file__),
              'candidate_status': 'NO_QUALIFIED_CANDIDATE', 'NAV_or_APR_or_net_PnL_computed': False,
              'no_models_or_orders_or_price_mark_index_locked': True, 'sources': [], 'per_symbol': [],
              'completed_sources_verified': 0, 'completed_events_verified': 0,
              'fraction_scope': 'UNCONFIRMED_RAW_UNIT_ASSUMED_FRACTION_EXPLICITLY_BEFORE_INCOME_AFTER_HTTP451_NO_MATCHES',
              'coupon_scope': 'CONDITIONAL_ON_RAW_FRACTION_ASSUMPTION_PER_SYMBOL_FIXED_EVENT_SINGLE_LEG_NOTIONAL_SUM_NOT_REAL_CASH',
              'cost_scope': 'ONCE_FULL_PERIOD_MATCHED_NOTIONAL_HEDGE_TWO_LEG_OPEN_CLOSE_NOT_MONTHLY',
              'old24_SOURCE_QA_replayed': False, 'original_parquet_values_read': False,
              'float_comparison_absolute_tolerance_bps': '0.000000001'}
    started = time.monotonic()
    try:
        need(sha(frozen['actual_report']) == frozen['actual_report_sha256'], 'Actual funding report bytes changed')
        actual = load(frozen['actual_report'])
        need(actual['status'] == 'COMPLETE_CONDITIONAL_FUNDING_COUPON_COST_HURDLE_DIAGNOSTIC_UNCERTIFIED_UNIT_NOT_APR'
             and actual['source_bytes_unchanged'] and actual['completed_files'] == 8
             and actual['completed_events'] == 732, 'Actual full funding diagnostic not completed')
        need(actual['binding']['task_id'] == frozen['actual_task_id'], 'Actual task binding differs')
        report['actual_task_evidence'] = task_evidence(frozen['actual_task_id'])
        need(sha(frozen['protocol']) == frozen['protocol_sha256'] == actual['binding']['protocol_sha256'],
             'Actual protocol bytes changed')
        spec = load(frozen['protocol'])
        report['verified_source_hashes'] = actual['binding']['source_hashes']
        for path, digest in report['verified_source_hashes'].items():
            need(sha(ROOT / path) == digest, 'Prebound producer dependency changed: ' + path)
        need(spec['period_start'] == '2025-08-01' and spec['period_end_exclusive'] == '2025-12-01'
             and spec['symbols'] == list(SYMBOLS) and spec['source_calendar'] == list(MONTHS), 'Fixed seen122day scope differs')
        need(spec['funding_rate_unit'] == 'UNCONFIRMED' and spec['assumed_funding_rate_unit'] == 'FRACTION'
             and spec['bp_multiplier'] == 10000 and spec['unit_probe']['basis'] ==
             'EXPLICIT_UNVERIFIED_FRACTION_ASSUMPTION_AFTER_HTTP451', 'Conditional preregistered fraction assumption missing')
        interpretation = actual['unit_interpretation']
        need(interpretation['raw_rate_unit'] == 'UNCONFIRMED'
             and interpretation['assumed_funding_rate_unit'] == 'FRACTION' and interpretation['bp_multiplier'] == 10000
             and interpretation['basis'] == 'EXPLICIT_UNVERIFIED_FRACTION_ASSUMPTION_AFTER_HTTP451'
             and interpretation['conditional_fraction_assumption'] is True
             and interpretation['full_732_event_unit_certified'] is False and interpretation['sampled_API_unit_certified'] is False
             and interpretation['calc_time_publication_or_exact_account_charge_certified'] is False
             and interpretation['realized_rate_is_available_trading_signal'] is False
             and interpretation['probe_funding_rows_read'] == 0
             and actual['conditional_fraction_assumption'] is True
             and actual['income_unit_certification'] == 'UNCONFIRMED_NOT_AN_INVESTMENT_GATE_PASS',
             'Explicit conditional flags missing or unit/availability falsely promoted')
        unit_path = ROOT / spec['unit_probe']['path']
        need(sha(unit_path) == spec['unit_probe']['sha256'] == actual['unit_probe_sha256'], 'Failed unit probe receipt changed')
        unit = load(unit_path)
        need(unit['status'] == 'FAIL_OFFICIAL_FUNDING_API_PARITY_UNCONFIRMED'
             and unit['funding_rate_unit'] == 'UNCONFIRMED' and unit['bp_multiplier'] is None
             and unit['unit_evidence']['matched_records'] == 0 and unit['actual_operation_exit_code'] == 1,
             'Conditional branch must retain the actual failed zero-match unit probe')
        report['unit_task_evidence'] = task_evidence(frozen['unit_task_id'], expected_status='failed', expected_code=1)
        need(unit['binding']['task_id'] == frozen['unit_task_id'], 'Failed unit task does not match receipt')
        need(len(unit['requests']) == 1 and unit['requests'][0]['http_status'] == 451
             and unit['requests'][0]['retries'] == 0 and unit['comparisons'] == [],
             'Explicit failed HTTP451 no-retry/no-parity condition differs')
        report.update(raw_funding_rate_unit='UNCONFIRMED', assumed_funding_rate_unit='FRACTION',
                      unit_certified=False, sampled_API_parity_confirmed=False, semantic_failure_preserved=True)
        need(sha(ACCEPTANCE) == ACCEPTANCE_SHA == spec['source_acceptance_sha256'], 'Original source acceptance changed')
        acceptance = load(ACCEPTANCE)
        need(acceptance['status'] == 'PASS_NEW_OFFICIAL_INPUT_SOURCE_FORMAT_ONLY_INDEPENDENT_QA', 'OldQA source status differs')
        for key, digest_key in (('independent_qa_path', 'independent_qa_sha256'), ('producer_path', 'producer_sha256')):
            need(sha(acceptance[key]) == acceptance[digest_key], 'Preserved old source evidence changed')
        selected = [row for row in acceptance['sources'] if row['kind'] == 'fundingRate']
        need(len(selected) == 8 and {(e['symbol'], e['month']) for e in selected}
             == {(s, m) for s in SYMBOLS for m in MONTHS}, 'Exactly8 accepted funding inputs required')
        need(len(actual['input_bindings']) == 8, 'Actual source binding count differs')
        binding_map = {(r['symbol'], r['month']): r for r in actual['input_bindings']}
        need(len(binding_map) == 8, 'Duplicate actual funding source binding')
        by_symbol = {symbol: [] for symbol in SYMBOLS}
        for entry in sorted(selected, key=lambda e: (SYMBOLS.index(e['symbol']), e['month'])):
            need(binding_map[(entry['symbol'], entry['month'])] ==
                 {key: entry[key] for key in ('symbol', 'month', 'receipt_path', 'receipt_sha256', 'parquet_path', 'parquet_sha256', 'rows')},
                 'Actual input identity differs from accepted funding subset')
            rows, metadata = raw_funding(entry)
            by_symbol[entry['symbol']].extend(rows)
            report['sources'].append(metadata)
            report['completed_sources_verified'] = len(report['sources'])
            report['completed_events_verified'] += len(rows)
            progress(len(report['sources']))
        need(report['completed_events_verified'] == 732, 'Not all732 raw funding rows verified')
        observed_symbols = {value['symbol']: value for value in actual['per_symbol']}
        need(len(actual['per_symbol']) == 2 and set(observed_symbols) == set(SYMBOLS), 'No combined or missing symbol income')
        expected_hurdles = [(31,0,0), (51,4,16), (55,8,16), (63,16,16)]
        need(len(actual['cost_hurdles']) == 4, 'All4 fixed cost hurdles required')
        for hurdle, (total, spread, slippage) in zip(actual['cost_hurdles'], expected_hurdles):
            need(hurdle['fee_bps'] == 31 and hurdle['assumed_spread_bps'] == spread
                 and hurdle['assumed_slippage_bps'] == slippage and hurdle['total_hurdle_bps'] == total,
                 'Two-leg31fee/51,55,63 hurdle arithmetic differs')
        for symbol in SYMBOLS:
            rows, observed = by_symbol[symbol], observed_symbols[symbol]
            need(len(rows) == 366 and all(a['calc_time_ms'] < b['calc_time_ms'] for a,b in zip(rows,rows[1:])),
                 'Per-symbol full chronology differs')
            exact = coupon_stats(rows)
            errors = compare_stats(observed, exact, symbol)
            verify_run_list(observed['negative_runs'], rows, symbol)
            need(observed['first_calc_time_ms'] == rows[0]['calc_time_ms'] and observed['last_calc_time_ms'] == rows[-1]['calc_time_ms'],
                 'Per-symbol exactms bounds differ')
            need(not observed['negative_run_duration_or_exposure_inferred'], 'MS jitter used as exposure/duration')
            need(len(observed['months']) == 4 and [m['month'] for m in observed['months']] == list(MONTHS),
                 'No monthly outcome selection allowed')
            months = []
            for monthly in observed['months']:
                month = monthly['month']
                subset = [row for row in rows if month_of_ms(row['calc_time_ms']) == month]
                monthly_exact = coupon_stats(subset)
                compare_stats(monthly, monthly_exact, symbol + ':' + month)
                verify_run_list(monthly['negative_runs'], subset, symbol + ':' + month)
                need(not monthly['monthly_costs_subtracted'], 'Whole-period entry/exit cost wrongly repeated monthly')
                months.append({'month': month, **monthly_exact})
            need(sum((Decimal(m['sum_funding_bps']) for m in months),ZERO) == Decimal(exact['sum_funding_bps']),
                 'Exact month sums do not equal fullperiod coupon')
            positive_months = [Decimal(m['sum_funding_bps']) for m in months if Decimal(m['sum_funding_bps']) > 0]
            need(observed['positive_month_count'] == len(positive_months), 'Positive month count differs')
            concentration = max(positive_months)/sum(positive_months,ZERO) if positive_months else None
            if concentration is None:
                need(observed['max_positive_month_contribution_share'] is None, 'Undefined concentration was fabricated')
            else:
                float_decimal_check(observed['max_positive_month_contribution_share'], concentration, symbol+':monthconcentration')
            need(len(observed['coupon_minus_roundtrip_hurdle']) == 4, 'All costs must be reported without picking cheapest')
            for item, threshold in zip(observed['coupon_minus_roundtrip_hurdle'], THRESHOLDS):
                need(item['total_hurdle_bps'] == float(threshold) and item['headroom_is_not_net_capital_return'],
                     'Coupon headroom misidentified as return')
                float_decimal_check(item['headroom_bp'], Decimal(exact['sum_funding_bps'])-threshold, symbol+':cost'+str(threshold))
            report['per_symbol'].append({'symbol': symbol, **exact, 'months': months, 'reported_float_errors': errors,
                'max_positive_month_contribution_share': str(concentration) if concentration is not None else None})
        artifact = actual['output_artifacts']
        need(len(artifact) == 1 and artifact[0]['rows'] == 732, 'Only full coupon prefix output accepted')
        prefix_path = Path(actual['run_dir']) / 'coupon_prefix.parquet'
        need(Path(artifact[0]['path']) == prefix_path and sha(prefix_path) == artifact[0]['sha256'], 'Derived coupon prefix bytes changed')
        report['coupon_prefix'] = {'path': str(prefix_path), 'sha256': sha(prefix_path), **verify_prefix(prefix_path, by_symbol)}
        need(actual['capital_net_APR'] == 'NOT_EVALUABLE' and not actual['fills_NAV_or_realized_funding_cash_computed']
             and not actual['mark_index_spot_arrays_read'] and not actual['locked_consumed']
             and actual['models_fit'] == 0 and actual['orders_sent'] == 0 and actual['GPU'] == 0
             and actual['candidate_status'] == 'NO_QUALIFIED_CANDIDATE', 'Diagnostic scope or qualification broadened')
        need(sha(frozen['actual_report']) == frozen['actual_report_sha256'] and sha(__file__) == frozen['checker_sha256'],
             'Bound actual/source changed during independent audit')
        for path, digest in report['verified_source_hashes'].items():
            need(sha(ROOT/path) == digest, 'Frozen source changed during audit: '+path)
        report['status'] = 'PASS_CONDITIONAL_RAW_FRACTION_ASSUMPTION_DECIMAL_COUPON_MATH_UNCERTIFIED_UNIT_NOT_APR'
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write_new(args.output, report)
    print(json.dumps({'status': report['status'], 'sha256': sha(args.output),
                      'completed_events_verified': report['completed_events_verified']}))


if __name__ == '__main__':
    with localcontext() as context:
        context.prec = 60
        main()