"""Metadata-only root acceptance, after separate actual producer and audit exit0.

Never opens raw archives, CHECKSUM bodies or Parquet files. Their byte hashes and
format proofs are delegated to the completed independent QA, not re-computed.
Prepared statically; this file itself has not performed any acceptance.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path
from quant import resources

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
PROTOCOL = ROOT/'protocols/OFFICIAL_CARRY_CHRONOLOGY_SOURCE_20261003_V1.json'
PRODUCER = ROOT/'reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ACTUAL_20261003_V1.json'
AUDIT = ROOT/'reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_INDEPENDENT_QA_20261003_V1.json'
AUDIT_SOURCE = ROOT/'scripts/investment/audit_carry_chronology_source.py'
OUT = ROOT/'reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ROOT_ACCEPTANCE_20261003_V1.json'
MONTHS = ['2025-12', '2026-01', '2026-02']
KINDS = ['fundingRate', 'indexPriceKlines', 'markPriceKlines']
SYMBOLS = ['BTCUSDT', 'ETHUSDT']
LIMIT = 200_000_000


def check(ok, message):
    if not ok: raise ValueError(message)


def small(path, expected=None, as_json=True):
    original = Path(path)
    path = original.resolve()
    check((path.is_relative_to(ROOT) or path.is_relative_to(STATE)) and not original.is_symlink()
          and path.is_file() and path.stat().st_size <= 2_000_000, 'Ordinary small D-hosted metadata/code only')
    check(path.suffix in {'.json', '.py', '.sh', '.ps1', '.lock'}, 'No market-data bytes may be opened')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    check(expected is None or digest == expected, 'Frozen small source/receipt hash: '+str(path))
    return (json.loads(raw) if as_json else None), digest


def task(identity):
    check(isinstance(identity, str) and re.fullmatch(r'[0-9a-f]{32}', identity), 'Exact task identity')
    path = STATE/'task-progress'/('task-'+identity+'.json')
    value, digest = small(path)
    check(value['id'] == identity and value['status'] == 'completed' and value['exit_code'] == 0
          and value['ended_at'] >= value['started_at'], 'Actual task must be truly closed exit0')
    return dict(path=str(path), sha256=digest, task=value)


def stat_source(path, expected_bytes=None):
    original = Path(path)
    value = original.resolve()
    check(value.is_relative_to(STATE) and not original.is_symlink() and value.is_file(), 'D-hosted ordinary source file')
    check(expected_bytes is None or value.stat().st_size == expected_bytes, 'Saved source bytes metadata changed')
    return dict(path=str(value), bytes=value.stat().st_size, content_read=False, hash_recomputed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer-host-session', required=True)
    parser.add_argument('--audit-host-session', required=True)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve() == STATE/'v8-clean-env-20261002-v2',
          'Existing bounded/progress and clean environment required')
    own_resources = resources.status()
    output = args.output.resolve()
    check(output.is_relative_to(ROOT/'reports/fast_research') and not output.exists(), 'Exclusive root acceptance report')
    protocol, protocol_sha = small(PROTOCOL)
    source, producer_sha = small(PRODUCER)
    qa, audit_sha = small(AUDIT)
    check(protocol['contract_id'] == 'OFFICIAL_CARRY_CHRONOLOGY_SOURCE_V1'
          and protocol['period_start'] == '2025-12-01' and protocol['period_end_exclusive'] == '2026-03-01'
          and protocol['months'] == MONTHS and protocol['kinds'] == KINDS and protocol['symbols'] == SYMBOLS
          and protocol['expected_archives'] == 18 and protocol['maximum_new_owned_bytes'] == LIMIT,
          'Frozen fixed source calendar and budget')
    check(protocol['funding_events_expected'] is None and protocol['funding_rate_unit_certified'] is False
          and protocol['economic_scope'] == 'NOT_EVALUATED' and protocol['shared_RAM_hard_bytes'] == 5_000_000_000
          and protocol['swap'] == 0 and protocol['GPU'] is False, 'No source/unit/economic promotion')
    check(source['status'] == 'OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA'
          and source['completed_files'] == source['required_files'] == source['source_file_universe_unique'] == 18
          and source['complete_archives'] == 18, 'All18 actual producer conversions')
    binding = source['binding']
    check(binding['protocol_path'] == str(PROTOCOL) and binding['protocol_sha256'] == protocol_sha
          and binding['source_sha256'] == protocol['runner_sha256'], 'Exact producer/protocol binding')
    source_hashes = dict(protocol['frozen_sources'])
    check(source_hashes == binding['source_hashes'], 'Unchanged frozen source map')
    for relative, digest in source_hashes.items():
        check(not Path(relative).is_absolute() and (ROOT/relative).resolve().is_relative_to(ROOT), 'ROOT-relative frozen source')
        small(ROOT/relative, digest, as_json=False)
    small(Path(binding['source_path']), binding['source_sha256'], as_json=False)
    producer_task = task(binding['task_id'])
    audit_task = task(qa['binding']['task_id'])
    check(producer_task['task']['id'] != audit_task['task']['id']
          and audit_task['task']['started_at'] >= producer_task['task']['ended_at'], 'Genuine separate later independent audit task')
    check(qa['status'] == 'PASS_D031_OFFICIAL_SOURCE18_FORMAT_ONLY_INDEPENDENT_QA'
          and qa['actual_archives'] == 18 and qa['funding_archives'] == 6 and qa['price_proxy_archives'] == 12
          and qa['cross_month_funding_gaps'] == 'PASS_ADJACENT_REPORTED_INTERVALS_WITH_FROZEN_JITTER',
          'Completed independent new18 format and cross-month audit')
    check(qa['producer_actual_task']['id'] == binding['task_id']
          and qa['producer_actual_task']['sha256'] == producer_task['sha256'], 'Independent audit saw the same closed producer task')
    _, checker_sha = small(AUDIT_SOURCE, qa['binding']['checker_sha256'], as_json=False)
    verified_small = {}
    for path, digest in qa['verified_source_hashes'].items():
        small(path, digest, as_json=False)
        verified_small[path] = digest
    check(verified_small.get(str(PRODUCER)) == producer_sha and verified_small.get(str(PROTOCOL)) == protocol_sha,
          'Independent QA bound this exact actual report and protocol')
    check(source['source_only'] is True and source['funding_unit_certified'] is False
          and source['source_acceptance_granted'] is False and source['independent_audit_task_executed'] is False
          and source['economic_eligibility'] is False and source['carry_NAV_or_APR_computed'] is False
          and source['model_fits'] == source['orders_sent'] == source['GPU'] == 0 and source['locked_consumed'] is False,
          'Producer is format-only; no fake independent, units or economics')
    check(qa['source_only'] is True and qa['funding_rate_unit'] == 'UNCONFIRMED'
          and qa['economics_or_unit_gate_passed'] is False and qa['charge_publication_availability_certified'] is False
          and qa['models_fit'] == qa['orders_sent'] == qa['actual_HTTP_requests'] == 0
          and qa['locked_consumed'] is False and qa['CSV_extracted_to_disk'] is False,
          'Independent QA did not certify units, economics, publication or execution')
    check(source['resources']['ram_limit_bytes'] <= 5_000_000_000 and source['resources']['swap_bytes'] == 0
          and source['resources']['gpu_used'] is False and qa['peak_RSS_bytes'] <= 512_000_000,
          'Actual shared5GB/no swap/GPU and bounded audit RSS')
    expected = {(k, s, m) for k in KINDS for s in SYMBOLS for m in MONTHS}
    checks = {(v['kind'], v['symbol'], v['month']): v for v in qa['sources']}
    check(len(qa['sources']) == len(checks) == 18 and set(checks) == expected, 'Exact independent18 unique source universe')
    receipts, completed = [], set()
    for item in source['sources']:
        receipt, digest = small(item['path'], item['sha256'])
        entry, stats = receipt['entry'], receipt['stats']
        key = (entry['kind'], entry['symbol'], entry['month'])
        check(key in expected and key not in completed, 'Unique required producer receipt')
        completed.add(key)
        proof = checks[key]
        check(receipt['status'] == item['status'] == 'SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA'
              and proof['status'] == 'PASS_SOURCE_FORMAT_ONLY' and proof['receipt_path'] == item['path']
              and proof['receipt_sha256'] == digest and proof['rows'] == stats['rows']
              and proof['zip_crc_full_read'] is True and proof['all_published_values_equal_raw'] is True,
              'Reuse independently verified format/hash/equality proof; never redo data QA')
        for name in ('zip_sha256', 'checksum_sha256', 'parquet_sha256'):
            check(re.fullmatch(r'[0-9a-f]{64}', receipt[name]) is not None, 'Saved source hash encoding')
        check(receipt['zip_sha256'] == entry['checksum']['announced_zip_sha256'], 'Official saved SHA identity')
        if entry['kind'] != 'fundingRate':
            check(stats['rows'] == (40_320 if entry['month'] == '2026-02' else 44_640)
                  and proof['exact_1m_calendar'] is True, 'Complete90day price proxy metadata')
        receipts.append(dict(kind=key[0], symbol=key[1], month=key[2], rows=stats['rows'],
            receipt_path=item['path'], receipt_sha256=digest,
            zip=dict(**stat_source(receipt['zip_path'], entry['announced_zip_bytes']), sha256=receipt['zip_sha256']),
            checksum=dict(**stat_source(receipt['checksum_path']), sha256=receipt['checksum_sha256']),
            parquet=dict(**stat_source(receipt['parquet_path'], receipt['parquet_bytes']), sha256=receipt['parquet_sha256'])))
    check(completed == expected and len(source['sources']) == 18, 'All18 producer receipt proofs')
    price_rows = sum(v['rows'] for v in checks.values() if v['kind'] != 'fundingRate')
    funding_rows = sum(v['rows'] for v in checks.values() if v['kind'] == 'fundingRate')
    check(price_rows == 518_400 == source['actual_price_rows']
          and funding_rows == source['actual_funding_events'] == qa['actual_funding_events']
          and price_rows + funding_rows == qa['actual_rows'], 'Real price/event totals; no assumed540 or8h count')
    check(0 < source['owned_bytes'] <= LIMIT and qa['actual_source_owned_bytes'] <= LIMIT
          and source['declared_uncompressed_csv_bytes'] == qa['declared_uncompressed_csv_bytes'] <= LIMIT
          and source['disk']['total_bytes'] + LIMIT <= 32_000_000_000, 'Recorded source-only200MB/expected32GB capacity')
    for path, digest in verified_small.items():
        if Path(path).is_relative_to(ROOT):
            source_hashes[str(Path(path).relative_to(ROOT))] = digest
    for path in (AUDIT, Path(__file__).resolve(),
                 ROOT/'protocols/CARRY_CHRONOLOGY_SOURCE_INDEPENDENT_BINDING_20261003_V1.json',
                 ROOT/'docs/archive/CARRY_CHRONOLOGY_SOURCE_QA_BINDER_20261003_V1.ps1',
                 ROOT/'docs/archive/CARRY_CHRONOLOGY_SOURCE_PREPARED_QA_BINDING_20261003_V1.json'):
        source_hashes[str(path.relative_to(ROOT))] = small(path, as_json=False)[1]
    report = dict(status='PASS_ROOT_D031_SOURCE18_FORMAT_ONLY_METADATA_ACCEPTANCE_NOT_ECONOMICS',
        created_utc=datetime.now(UTC).isoformat(), git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_hashes=source_hashes, producer_report_sha256=producer_sha, independent_audit_report_sha256=audit_sha,
        protocol_path=str(PROTOCOL), protocol_sha256=protocol_sha, actual_task_bindings=[producer_task, audit_task],
        actual_host_sessions=dict(producer=args.producer_host_session, independent_audit=args.audit_host_session),
        root_helper=dict(path=str(Path(__file__).resolve()), sha256=small(__file__, as_json=False)[1], task_id=os.environ['COIN_TASK_ID']),
        independent_checker=dict(path=str(AUDIT_SOURCE), sha256=checker_sha), independently_verified_small_inputs=verified_small,
        accepted_format=dict(archives=18, funding_archives=6, price_proxy_archives=12, price_rows=price_rows, funding_events=funding_rows,
            total_rows=price_rows+funding_rows, cross_month_funding_gaps=qa['cross_month_funding_gaps']), source_receipt_proofs=receipts,
        source_data_directory=protocol['source_data_directory'], source_data_leave_STATE_not_Git=True,
        actual_resources=dict(producer=source['resources'], producer_peak_RSS_bytes=source['peak_RSS_bytes'], audit_peak_RSS_bytes=qa['peak_RSS_bytes'], root=own_resources),
        actual_disk_scan=source['disk'], owned_bytes=qa['actual_source_owned_bytes'], no_new_scan=True,
        source_only=True, funding_rate_unit='UNCONFIRMED', funding_unit_certified=False, economic_gate_passed=False,
        carry_NAV_or_APR='NOT_EVALUABLE', models_fit=0, orders_sent=0, locked_consumed=False, GPU=0,
        raw_or_parquet_bytes_reopened_by_root=False, source_hashes_recomputed_for_market_data=False,
        data_QA_repeated=False, old_green_tests_repeated=False, readonly_metadata_acceptance=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(status=report['status'], output=str(output), sha256=small(output)[1])))


if __name__ == '__main__': main()
