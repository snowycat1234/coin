"""Reuse ten sealed Oct2025--Feb2026 Spot minute files; no price rows or ledger writes."""
from datetime import UTC, datetime
from pathlib import Path
import argparse
import calendar
import hashlib
import json
import resource
import sqlite3
import subprocess
import sys
import time

import pyarrow.parquet as pq

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
sys.path.insert(0, str(ROOT))
from scripts.research_v8.funding_price_source_v2 import progress_writer

MONTHS = ('2025-10', '2025-11', '2025-12', '2026-01', '2026-02')
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
LOCK_SHA = '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
QUALITY_SHA = '27aa56b33b12c1e6085230318bef6bd41cb3d95b23ca8714a35fc9a5b62125cf'
POLICY_SHA = '3e1adcfbed86d0cc2414d37934126dcc2ddcdfcbe52b4e74ec58ff3447a7d880'
PROGRESS_PROVIDER_SHA = '2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path,
                        default=STATE / 'public-strategy-chronology-source-reuse-20261002-v1')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'reports/fast_research/PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_20261002_V1.json')
    args = parser.parse_args()
    run_dir, output = args.run_dir.resolve(), args.output.resolve()
    require(run_dir.is_relative_to(STATE), 'Independent run directory must stay in STATE')
    require(output.is_relative_to(ROOT / 'reports/fast_research') or output.is_relative_to(STATE),
            'Receipt must stay in explicit D-backed reports or STATE')
    require(not run_dir.exists() and not output.exists(), 'Preserve existing run and receipt bytes')
    run_dir.mkdir(parents=True)
    started = time.monotonic()
    progress = None
    lock_path = ROOT / 'state/dataset_lock.json'
    quality_path = ROOT / 'reports/generated/DATA_QUALITY_REPORT.json'
    policy_path = ROOT / 'configs/dataset_policy.json'
    spec = {
        'scope': 'Reuse original sealed selected monthly source QA; hashes and Parquet metadata only',
        'source_sha256': sha(__file__),
        'source_calendar': list(MONTHS), 'source_scope': 'OCT2025_FEB2026', 'symbols': list(SYMBOLS),
        'source_start': '2025-10-01', 'source_end_exclusive': '2026-03-01',
        'research_start': '2025-12-01', 'research_end_exclusive': '2026-03-01',
        'warmup_start': '2025-10-31', 'warmup_end_exclusive': '2025-12-01',
        'expected_source_days_per_symbol': 151, 'expected_source_files': 10,
        'expected_source_minute_rows': 434880,
        'expected_sealed_lock_sha256': LOCK_SHA,
        'expected_sealed_quality_sha256': QUALITY_SHA,
        'expected_dataset_policy_sha256': POLICY_SHA,
        'progress_provider_path': str(ROOT / 'scripts/research_v8/funding_price_source_v2.py'),
        'expected_progress_provider_sha256': PROGRESS_PROVIDER_SHA,
        'crc_scope': 'No new CRC or CSV scan; reuse qualified original ingested archive/calendar evidence',
        'new_downloads': False, 'fits': 0, 'shared_RAM_limit_bytes': 5_000_000_000,
        'swap': 0, 'GPU': False, 'maximum_planned_new_owned_bytes': 1_000_000,
    }
    binding = {
        'exact_command': [sys.executable, *sys.argv], 'source_sha256': sha(__file__),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'spec': spec, 'created_utc': datetime.now(UTC).isoformat(),
    }
    with (run_dir / 'RUN_BINDING.json').open('x') as stream:
        json.dump(binding, stream, indent=2, allow_nan=False)
        stream.write('\n')
    report = {
        'status': 'FAILED_FROZEN_SPOT_CHRONOLOGY_SOURCE_REUSE', 'binding': binding,
        'run_binding_path': str(run_dir / 'RUN_BINDING.json'),
        'run_binding_sha256': sha(run_dir / 'RUN_BINDING.json'), 'sources': [],
        'market_price_rows_or_model_results_read': False, 'locked_consumed': False,
        'aggregated_bars_read': False, 'source_modified': False, 'new_source_downloaded': False,
        'original_CSV_or_ZIP_body_decompressed': False, 'registry_written': False,
        'economic_state': 'NOT_EVALUATED_SOURCE_ONLY_OHLC_PROXY_NOT_BBO',
    }
    try:
        require(sha(spec['progress_provider_path']) == PROGRESS_PROVIDER_SHA, 'Reused progress provider changed')
        require(sha(lock_path) == LOCK_SHA, 'Original sealed dataset lock bytes changed')
        lock = json.loads(lock_path.read_bytes())
        require(sha(quality_path) == lock['quality_report_sha256'] == QUALITY_SHA,
                'Original sealed quality report bytes changed')
        require(sha(policy_path) == lock['dataset_policy_sha256'] == POLICY_SHA,
                'Original sealed policy bytes changed')
        policy = json.loads(policy_path.read_bytes())
        holdout_start = datetime.fromisoformat(policy['holdout_start_utc'].replace('Z', '+00:00'))
        require(holdout_start == datetime(2026, 3, 1, tzinfo=UTC), 'Locked boundary changed')
        report['original_evidence'] = {
            'lock_path': str(lock_path), 'lock_sha256': LOCK_SHA,
            'quality_report_path': str(quality_path), 'quality_report_sha256': QUALITY_SHA,
            'policy_path': str(policy_path), 'policy_sha256': POLICY_SHA,
            'locked_start_utc': policy['holdout_start_utc'],
        }
        progress = progress_writer(10)
        with sqlite3.connect(f'file:{STATE}/archive_manifest.sqlite3?mode=ro', uri=True, timeout=5) as db:
            db.row_factory = sqlite3.Row
            for symbol in SYMBOLS:
                for month in MONTHS:
                    year, month_number = map(int, month.split('-'))
                    days = calendar.monthrange(year, month_number)[1]
                    opened = datetime(year, month_number, 1, tzinfo=UTC)
                    next_month = (datetime(year + 1, 1, 1, tzinfo=UTC) if month_number == 12
                                  else datetime(year, month_number + 1, 1, tzinfo=UTC))
                    require(next_month <= holdout_start, 'Selected month reaches locked history')
                    name = f'{symbol}-1m-{month}.zip'
                    raw = ROOT / 'data/raw/spot' / symbol / '1m' / name
                    checksum = raw.with_name(name + '.CHECKSUM')
                    normalized = ROOT / 'data/normalized/spot' / symbol / '1m' / f'{month}.parquet'
                    row = db.execute('SELECT * FROM archives WHERE name=? AND symbol=? AND month=?',
                                     (name, symbol, month)).fetchone()
                    require(row is not None, 'No original qualified archive row: ' + name)
                    manifest = dict(row)
                    old_quality = json.loads(manifest['quality_json'])
                    relative = str(normalized.relative_to(ROOT))
                    raw_sha, normalized_sha = sha(raw), sha(normalized)
                    require(manifest['status'] == 'ingested' and raw_sha == manifest['sha256'],
                            'Actual ZIP does not match original ingested manifest: ' + name)
                    fields = checksum.read_text().split()
                    require(len(fields) == 2 and fields[0].lower() == raw_sha
                            and fields[1].lstrip('*') == name, 'Saved official CHECKSUM mismatch: ' + name)
                    require(normalized_sha == manifest['normalized_sha256'] == lock['minute_files'][relative],
                            'Actual Parquet does not match original sealed source: ' + name)
                    expected_rows = days * 1440
                    require(manifest['rows'] == old_quality['rows'] == old_quality['expected_rows'] == expected_rows,
                            'Original month row/calendar count mismatch: ' + name)
                    require(manifest['timestamp_unit'] == old_quality['timestamp_unit'] == 'microseconds',
                            'Original minute timestamp unit mismatch: ' + name)
                    require(all(old_quality[key] == 0 for key in (
                        'missing_rows', 'bad_timestamps', 'bad_values', 'duplicate_rows', 'quarantined_rows')),
                            'Original selected source has quality defects: ' + name)
                    require(not old_quality['incomplete_days'] and not old_quality['quarantined_days']
                            and not old_quality.get('missing_start') and not old_quality.get('missing_end'),
                            'Original selected month calendar is incomplete: ' + name)
                    first_us = int(opened.timestamp() * 1_000_000)
                    require(old_quality['first_open_us'] == first_us
                            and old_quality['last_open_us'] == first_us + (expected_rows - 1) * 60_000_000,
                            'Original calendar month endpoints mismatch: ' + name)
                    metadata = pq.read_metadata(normalized)
                    schema = pq.read_schema(normalized)
                    require(metadata.num_rows == expected_rows and str(schema.field('open_us').type) == 'int64',
                            'Actual Parquet metadata differs from sealed calendar: ' + name)
                    report['sources'].append({
                        'symbol': symbol, 'month': month, 'zip_path': str(raw), 'zip_sha256': raw_sha,
                        'checksum_path': str(checksum), 'checksum_sha256': sha(checksum),
                        'normalized_path': str(normalized), 'normalized_sha256': normalized_sha,
                        'rows': expected_rows, 'days': days, 'timestamp_unit': 'microseconds',
                        'old_quality': old_quality, 'actual_parquet_schema': str(schema),
                        'calendar_qa': 'REUSED_SEALED_ORIGINAL_QA_WITH_ACTUAL_PARQUET_METADATA',
                        'new_CSV_or_CRC_QA': False,
                    })
                    progress.update('冻结现货分钟源薄复用', len(report['sources']), 10, '文件')
        require(len(report['sources']) == 10 and sum(row['rows'] for row in report['sources']) == 434880,
                'Selected ten-file source count changed')
        report.update(status='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR',
                      source_files=10, days_per_symbol=151, actual_minute_rows=434880,
                      complete_days_across_symbols=302, research_days=90, warmup_days=31,
                      old_qualified_calendar_evidence_reused=True)
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error)[:1024])
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        report['peak_RSS_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        report['created_utc'] = datetime.now(UTC).isoformat()
        with output.open('x') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        if progress is not None:
            progress.stop.set()
            progress.thread.join(timeout=3)
    print(json.dumps({'status': report['status'], 'output_path': str(output),
                      'output_sha256': sha(output), 'source_files': report['source_files'],
                      'rows': report['actual_minute_rows'], 'elapsed_seconds': report['elapsed_seconds'],
                      'peak_RSS_bytes': report['peak_RSS_bytes']}))


if __name__ == '__main__':
    main()
