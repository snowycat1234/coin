"""One bounded official-document / historical API funding semantics probe.

Only two accepted August funding files supply at most three comparison rows
each. No mark/index arrays, funding income, models, fills or account IO.
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
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import polars as pl

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
PROTOCOL = ROOT / 'protocols/FUNDING_SEMANTICS_PROBE_20261003_V1.json'
OUTPUT = ROOT / 'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V1.json'
SOURCE = STATE / 'v8-funding-mark-index-source-20261002-v1'


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def load(path):
    return json.loads(Path(path).read_text())


def progress(phase, completed):
    path = STATE / 'task-progress' / ('task-' + os.environ['COIN_TASK_ID'] + '.json')
    value = load(path)
    value.update(phase=phase, completed=completed, total=4, unit='官方请求', last_activity_at=time.time())
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False))
    os.replace(temp, path)


def request_once(url, destination, timeout, maximum, is_api=False):
    """Standard verified HTTPS, one request, no retries or transport fallback."""
    need(urlparse(url).scheme == 'https' and urlparse(url).hostname in
         {'developers.binance.com', 'www.binance.com', 'fapi.binance.com'}, 'Official HTTPS host only')
    info = dict(url=url, requested_at_utc=datetime.now(UTC).isoformat(), retries=0,
                TLS_verification='SYSTEM_DEFAULT_ENABLED', maximum_response_bytes=maximum)
    start = time.monotonic()
    try:
        request = Request(url, headers={'User-Agent': 'COIN-Funding-Semantics-ReadOnly/1',
                                      'Accept': 'application/json' if is_api else 'text/html',
                                      'Accept-Encoding': 'identity'})
        with urlopen(request, timeout=timeout) as response:
            info.update(http_status=response.status, final_url=response.geturl(),
                        content_type=response.headers.get('Content-Type'))
            need(urlparse(response.geturl()).hostname in
                 {'developers.binance.com', 'www.binance.com', 'fapi.binance.com'}, 'Official redirect only')
            payload = response.read(maximum + 1)
            need(len(payload) <= maximum, 'Response exceeds fixed small evidence limit')
        destination.write_bytes(payload)
        info.update(status='RETRIEVED', raw_path=str(destination), raw_sha256=sha(destination), bytes=len(payload))
        return payload, info
    except HTTPError as error:
        payload = error.read(min(maximum, 64000))
        destination.write_bytes(payload)
        info.update(status='HTTP_FAILURE', http_status=error.code, error_type=type(error).__name__,
                    reason=str(error), raw_error_path=str(destination), raw_error_sha256=sha(destination), bytes=len(payload))
        return None, info
    except Exception as error:
        info.update(status='NETWORK_OR_RESPONSE_FAILURE', error_type=type(error).__name__, reason=str(error))
        return None, info
    finally:
        info['elapsed_seconds'] = time.monotonic() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    work = args.run_dir.resolve()
    need(work == STATE / 'funding-semantics-probe-20261003-v1' and not work.exists() and
         not OUTPUT.exists(), 'Exclusive predetermined STATE/report required')
    need(sys.prefix == str(STATE / 'v8-clean-env-20261002-v2'), 'Frozen clean interpreter required')
    spec = load(PROTOCOL)
    need(sha(__file__) == spec['source_sha256'], 'Probe source changed after protocol freeze')
    need(sha(ROOT / 'environments/v8/uv.lock') == spec['environment_lock_sha256'], 'Base environment changed')
    need(spec['symbols'] == ['BTCUSDT', 'ETHUSDT'] and spec['api_limit_per_symbol'] == 3 and
         spec['startTime_ms'] == 1754006400000 and spec['endTime_ms'] == 1754064001000,
         'Only fixed first-three-August2025 history scope; no latest/locked query')
    sources = {path: sha(ROOT / path) for path in spec['frozen_sources']}
    need(sources == spec['frozen_sources'], 'Frozen source evidence changed')
    acceptance = load(ROOT / spec['acceptance_path'])
    need(acceptance['status'] == 'PASS_NEW_OFFICIAL_INPUT_SOURCE_FORMAT_ONLY_INDEPENDENT_QA',
         'Accepted official source format evidence required')
    need({(s['symbol'], s['month']) for s in spec['funding_sources']} ==
         {(symbol, month) for symbol in spec['symbols'] for month in ('2025-08', '2025-09', '2025-10', '2025-11')},
         'Exactly eight existing development funding metadata identities')
    for row in spec['funding_sources']:
        expected = SOURCE / ('fundingRate-' + row['symbol'] + '-' + row['month'])
        need(Path(row['receipt_path']) == expected / 'receipt.json' and
             Path(row['parquet_path']) == expected / 'source.parquet', 'Exact accepted funding route only')
        need(sha(row['receipt_path']) == row['receipt_sha256'], 'Saved funding metadata changed')
        need(any(s['kind'] == 'fundingRate' and s['symbol'] == row['symbol'] and s['month'] == row['month'] and
                 s['parquet_sha256'] == row['parquet_sha256'] and s['receipt_sha256'] == row['receipt_sha256']
                 for s in acceptance['sources']), 'Source must belong to accepted eight-file subset')
    work.mkdir()
    binding = dict(git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        task_id=os.environ['COIN_TASK_ID'], protocol_path=str(PROTOCOL.relative_to(ROOT)), protocol_sha256=sha(PROTOCOL),
        source_sha256=sha(__file__), source_hashes=sources, environment_lock_sha256=spec['environment_lock_sha256'],
        sys_prefix=sys.prefix, exact_command=shlex.join([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]),
        data_scope='TWO_AUGUST_FUNDING_PARQUETS_MAX_THREE_ROWS_EACH_PLUS_OFFICIAL_DOCUMENT_AND_BOUNDED_API_EVIDENCE',
        seed='NOT_APPLICABLE', models_fit=0, GPU=0)
    write(work / 'RUN_BINDING.json', binding)
    sys.path.insert(0, str(ROOT))
    from scripts.research_v8.registry import FIELDS, append_event
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=spec['experiment_id'], git_commit=binding['git_commit'],
        data_manifest_hash=sha(ROOT / spec['acceptance_path']), protocol_hash=binding['protocol_sha256'],
        feature_set='NONE_SOURCE_SEMANTICS_ONLY', labels='NONE', model_family='NONE',
        hyperparameters='NO_FIT_MAX3_API_RECORDS_PER_SYMBOL_FIXED_FIRST_DAY', seed='NOT_APPLICABLE',
        thresholds={'time_tolerance_ms': 1000, 'rate_fraction_absolute_tolerance': '0.000000000001'},
        cost_assumptions='NOT_EVALUATED_NO_FUNDING_INCOME_OR_CAPITAL_OR_FEE_APPLICATION',
        all_folds='FIRST_THREE_EVENTS_2025_AUGUST_BTC_ETH', result_influenced_later_choice=False,
        reason_for_next_experiment='Establish limited official archive-to-API semantic bridge before funding-only hurdle diagnostic')
    start_event = append_event(ROOT / 'reports/experiment_registry.jsonl',
        {**event, 'event_id': spec['experiment_id'] + ':START', 'event_type': 'OPERATIONAL_SOURCE_SEMANTICS_START',
         'success_failure': 'START_BEFORE_OFFICIAL_REQUESTS_OR_FUNDING_ROWS', 'binding': binding})
    write(work / 'START.json', start_event)
    report = dict(status='FAIL_OFFICIAL_FUNDING_API_PARITY_UNCONFIRMED', binding=binding, run_dir=str(work),
        funding_rate_unit='UNCONFIRMED', bp_multiplier=None,
        unit_evidence={'qualification': 'NOT_YET_ESTABLISHED', 'sample_scope': spec['api_scope'],
                       'sample_parity_status': 'UNCONFIRMED', 'time_tolerance_ms': 1000, 'matched_records': 0},
        requests=[], comparisons=[], source_metadata_identities=spec['funding_sources'],
        market_scope='BINANCE_USD_M_PUBLIC_FUNDING_SOURCE_ONLY_NOT_BYBIT', locked_consumed=False,
        mark_index_arrays_read=False, funding_income_calculated=False, orders_sent=0, models_fit=0, GPU=0,
        candidate_status='NO_QUALIFIED_CANDIDATE', carry_economics='NOT_EVALUABLE', source_only=True)
    start = time.monotonic()
    exit_code = 1
    try:
        write(work / 'DOCUMENTARY_PRIMARY_BROWSE_EVIDENCE.json', spec['documentary_evidence'])
        report['documentary_evidence'] = dict(path=str(work / 'DOCUMENTARY_PRIMARY_BROWSE_EVIDENCE.json'),
            sha256=sha(work / 'DOCUMENTARY_PRIMARY_BROWSE_EVIDENCE.json'),
            provenance='PRIMARY_OFFICIAL_PAGES_READ_WITH_WEB_TOOL_BEFORE_PROTOCOL_NO_ACCOUNT_OR_HISTORICAL_CHARGE_PROOF')
        report['documented_payment_direction'] = 'POSITIVE_LONG_PAYS_SHORT_NEGATIVE_SHORT_PAYS_LONG'
        report['documented_event_mark_definition'] = 'REST_MARKPRICE_ASSOCIATED_WITH_FUNDING_CHARGE_NOT_1M_MARK_OHLC_OR_EXECUTABLE_PRICE'
        report['calc_time_boundaries'] = {'archive_calc_time_is_exact_charge_timestamp': False,
            'archive_calc_time_is_publication_or_feature_availability': False,
            'timestamp_matching_tolerance_is_charge_or_availability_proof': False,
            'account_charge_or_receipt_matched': False, 'same_window_doc_definitions_qualify_all_history': False}
        progress('读取官方资金费语义页面', 0)
        for index, document in enumerate(spec['document_urls'], 1):
            _, receipt = request_once(document['url'], work / document['filename'], spec['timeout_seconds'],
                                      spec['maximum_document_bytes'])
            report['requests'].append(receipt)
            progress('官方文档请求已处理', index)
        for index, symbol in enumerate(spec['symbols'], 3):
            url = spec['api_endpoint'] + '?' + urlencode(dict(symbol=symbol, startTime=spec['startTime_ms'],
                endTime=spec['endTime_ms'], limit=spec['api_limit_per_symbol']))
            payload, receipt = request_once(url, work / (symbol + '-official-response.json'), spec['timeout_seconds'],
                                           spec['maximum_API_bytes'], is_api=True)
            report['requests'].append(receipt)
            progress('固定历史事件请求已处理', index)
            if payload is None:
                continue
            records = json.loads(payload)
            need(isinstance(records, list) and len(records) == 3, 'Exactly three fixed historical records required')
            need(all(isinstance(r, dict) and r['symbol'] == symbol and type(r['fundingTime']) is int and
                spec['startTime_ms'] <= r['fundingTime'] <= spec['endTime_ms'] and
                isinstance(r['fundingRate'], str) for r in records), 'API returned wrong symbol/time/encoding')
            stamps = [r['fundingTime'] for r in records]
            need(stamps == sorted(set(stamps)), 'Distinct chronological fundingTime required')
            row = next(s for s in spec['funding_sources'] if s['symbol'] == symbol and s['month'] == '2025-08')
            path = Path(row['parquet_path'])
            need(sha(path) == row['parquet_sha256'], 'Accepted August funding file changed')
            sample = (pl.scan_parquet(path).filter(pl.col('calc_time_ms').is_between(
                spec['startTime_ms'], spec['endTime_ms'])).sort('calc_time_ms').limit(3)
                .select('calc_time_ms', 'funding_interval_hours', 'last_funding_rate').collect())
            need(sample.height == 3 and sample['calc_time_ms'].dtype == pl.Int64, 'Three preserved ms archive rows required')
            matched_ids = set()
            for api in records:
                candidates = [r for r in sample.iter_rows(named=True)
                              if abs(r['calc_time_ms'] - api['fundingTime']) <= spec['time_tolerance_ms']]
                need(len(candidates) == 1, 'One unique archive event within preregistered ms tolerance')
                archived = candidates[0]
                need(archived['calc_time_ms'] not in matched_ids, 'No duplicate event matching')
                matched_ids.add(archived['calc_time_ms'])
                rate, saved_rate = Decimal(api['fundingRate']), Decimal(str(archived['last_funding_rate']))
                need(rate.is_finite() and saved_rate.is_finite() and abs(rate) <= 1,
                     'Finite bounded published numeric rate required')
                difference = abs(rate - saved_rate)
                need(difference <= Decimal(spec['rate_absolute_tolerance']), 'Direct raw archive/API rates disagree; no rescale')
                mark = api.get('markPrice')
                if mark is not None:
                    need(isinstance(mark, str) and Decimal(mark).is_finite() and Decimal(mark) > 0,
                         'API-associated charge mark must be positive finite string')
                report['comparisons'].append(dict(symbol=symbol, archive_calc_time_ms=archived['calc_time_ms'],
                    API_fundingTime_ms=api['fundingTime'], actual_timestamp_difference_ms=archived['calc_time_ms'] - api['fundingTime'],
                    API_fundingRate=api['fundingRate'], archive_last_funding_rate=str(saved_rate),
                    absolute_rate_difference=str(difference), archive_rate_rescaling_applied=False,
                    API_associated_charge_mark_present=mark is not None,
                    historical_account_charge_or_feature_availability_confirmed=False))
        count = len(report['comparisons'])
        report['unit_evidence'].update(matched_records=count, documentary_sources=spec['documentary_evidence'],
            max_abs_rate_difference=max((r['absolute_rate_difference'] for r in report['comparisons']),
                                       key=Decimal, default=None))
        need(count == 6, 'Historical API bridge not established for both symbols; preserve any network/API failure')
        report.update(status='PASS_OFFICIAL_FUNDING_DOCUMENTARY_SEMANTICS_AND_SAMPLED_API_PARITY',
                      funding_rate_unit='FRACTION', bp_multiplier=10000)
        report['unit_evidence'].update(qualification='DOCUMENTARY_API_RATIO_CONVENTION_AND_SIX_SAMPLED_ARCHIVE_API_PARITY',
            sample_parity_status='PASS_SIX_RECORDS_NO_RESCALE', full_732_event_API_certification=False,
            fraction_encoding_basis='REST_NUMERIC_RATIO_CONVENTION_WITH_OFFICIAL_FUNDING_AMOUNT_MULTIPLICATIVE_FORMULA;PARITY_CONFIRMS_ARCHIVE_USES_SAME_ENCODING',
            claimed_scope='RAW_UNIT_BRIDGE_FOR_EXISTING_BINANCE_FUNDING_ONLY_DIAGNOSTIC_NOT_A_COSTED_OR_BYBIT_STRATEGY')
        need(sha(__file__) == spec['source_sha256'] and sha(PROTOCOL) == binding['protocol_sha256'] and
             all(sha(ROOT / path) == digest for path, digest in sources.items()), 'Prebound source bytes changed')
        exit_code = 0
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error))
    finally:
        from quant import resources
        report.update(created_utc=datetime.now(UTC).isoformat(), actual_operation_exit_code=exit_code,
            elapsed_seconds=time.monotonic() - start, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            resources=resources.status(), owned_bytes=sum(p.stat().st_size for p in work.rglob('*') if p.is_file()))
        write(OUTPUT, report)
        result_event = append_event(ROOT / 'reports/experiment_registry.jsonl',
            {**event, 'event_id': spec['experiment_id'] + ':RESULT', 'event_type': 'OPERATIONAL_SOURCE_SEMANTICS_RESULT',
             'success_failure': report['status'], 'artifact_path': str(OUTPUT.relative_to(ROOT)),
             'artifact_sha256': sha(OUTPUT), 'actual_operation_exit_code': exit_code,
             'actual_task_id': binding['task_id'], 'source_sha256': binding['source_sha256']})
        write(work / 'RESULT.json', result_event)
        print(json.dumps(dict(status=report['status'], output=str(OUTPUT), sha256=sha(OUTPUT), actual_exit=exit_code)))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
