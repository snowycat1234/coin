"""Authorized, bounded OKX DOGE December 2025 minute-mark stage only."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from .common import dump, sha256
from .public_supplement import (
    BASES,
    Budget,
    Failure,
    _read,
    bars_request,
    coverage,
    fingerprint,
    instrument_identity,
    mark_job,
    metadata_request,
    normalize,
)

VERSION = 'okx-doge-december-mark-1'


@dataclass
class MarkBudget(Budget):
    max_requests: int = 460
    max_bytes: int = 10_000_000
    min_interval_seconds: float = 1.0

    def __post_init__(self):
        if (not 1 <= self.max_requests <= 460 or not 0 < self.max_bytes <= 10_000_000
                or not 0 < self.max_response_bytes <= 1_000_000
                or not 1 <= self.max_attempts <= 2
                or not math.isfinite(self.min_interval_seconds)
                or self.min_interval_seconds < 1.0
                or not 0 <= self.requests_used <= self.max_requests
                or not 0 <= self.bytes_used <= self.max_bytes):
            raise ValueError('DOGE minute mark stage exceeds its explicit public-read budget')


def collect_doge_marks(cache, session=None, budget=None):
    """Read one 100-minute pilot, then continue only with complete retained pages.

    Success pages are reused by raw SHA; stage requests/bytes include previous
    attempts. Every incomplete page stops acquisition, with no venue/host fallback.
    Compressed JSONL keeps the normalized provenance small enough to publish.
    """
    cache = Path(cache).resolve()
    if cache.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('Mark cache must be outside the source checkout')
    job = mark_job('okx')
    binding = dict(version=VERSION, job=asdict(job), source_sha256=sha256(Path(__file__)),
                   adapter_source_sha256=sha256(Path(__file__).with_name('public_supplement.py')),
                   endpoint=BASES['okx'] + '/api/v5/market/history-mark-price-candles',
                   dataset_role='ALTERNATIVE_VENUE_ROBUSTNESS_ONLY', original_provider='Binance',
                   replaces_original_observations=False, frozen_selector_certified=False,
                   limits=dict(requests=460, response_body_bytes=10_000_000,
                               per_response_bytes=1_000_000, minimum_spacing_seconds=1,
                               acquisition_wall_seconds=900))
    directory = cache / 'okx-mark' / fingerprint([VERSION, asdict(job)])[:24]
    directory.mkdir(parents=True, exist_ok=True)
    receipt, output = directory / 'manifest.json', directory / 'bars.jsonl.gz'
    manifest = json.loads(receipt.read_text()) if receipt.exists() else dict(
        binding=binding, requests=[], status='PENDING')
    if manifest['binding'] != binding:
        raise ValueError('Saved mark source or request binding changed')
    for record in manifest['requests']:
        if 'raw_file' in record and sha256(directory / record['raw_file']) != record['raw_sha256']:
            raise ValueError('Retained mark raw checksum mismatch')
    if output.exists() and sha256(output) != manifest.get('normalized_sha256'):
        raise ValueError('Retained mark normalized checksum mismatch')
    budget = budget or MarkBudget(requests_used=len(manifest['requests']),
                                  bytes_used=sum(r.get('body_bytes', 0)
                                                 for r in manifest['requests']))
    if not isinstance(budget, MarkBudget):
        raise ValueError('Explicit independent mark-stage budget required')
    if (cache / 'okx/access-stop.json').exists():
        budget.denied_providers.add('okx')
    started = time.monotonic()
    owned_session = session is None
    session = session or requests.Session()
    rows = []
    try:
        raw, metadata = _read(job, *metadata_request(job), directory, manifest, budget, session)
        identity = instrument_identity(job, raw)
        identity['metadata_raw_sha256'] = metadata['raw_sha256']
        manifest['identity'] = identity
        total_pages = (job.count + 99) // 100
        for page_number, start in enumerate(range(job.start_ms, job.end_ms, 100 * job.step), 1):
            if time.monotonic() - started > 880:
                raise Failure('WALL_BUDGET_EXHAUSTED', 'Stop before the 900-second wall limit')
            end = min(start + 100 * job.step, job.end_ms)
            raw, record = _read(job, *bars_request(job, start, end),
                                directory, manifest, budget, session)
            page = normalize(job, raw, identity, record['received_ms'],
                             record['raw_sha256'], start, end)
            for row in page:
                row['volume_units'] = None  # mark prices have no traded-volume observation
            rows.extend(page)
            record['observed_bars'] = len(page)
            if len(page) != (end - start) // job.step:
                record['coverage_note'] = 'HISTORY_UNAVAILABLE_UNCLASSIFIED' if not page \
                    else 'INCOMPLETE_COVERAGE'
                raise Failure('INCOMPLETE_COVERAGE',
                              f'Page {page_number}: {len(page)} completed marks; stopped endpoint')
            record['coverage_note'] = 'COMPLETE_PAGE'
            if page_number == 1 or page_number % 30 == 0 or page_number == total_pages:
                print(json.dumps(dict(stage='DOGE_MARK', pages=page_number, total_pages=total_pages,
                                      observed_bars=len(rows))), flush=True)
        manifest['status'] = coverage(job, rows)['status']
        manifest.pop('last_failure', None)
    except Failure as exc:
        manifest.update(status=exc.status, last_failure=dict(status=exc.status, detail=str(exc)))
        if exc.status in ('PERMISSION_DENIED', 'RATE_LIMITED'):
            stop = cache / 'okx/access-stop.json'
            if not stop.exists():
                dump(dict(provider='okx', status=exc.status, detail=str(exc),
                          manifest=str(receipt)),
                     stop)
    finally:
        if owned_session:
            session.close()
    raw_jsonl = ''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n'
                        for row in rows).encode()
    temporary = output.with_suffix('.part')
    temporary.write_bytes(gzip.compress(raw_jsonl, mtime=0))
    temporary.replace(output)
    manifest.update(coverage=coverage(job, rows), normalized_file=output.name,
                    normalized_sha256=sha256(output), normalized_encoding='GZIP_JSONL_UTF8',
                    stage_requests=budget.requests_used,
                    stage_response_body_bytes=budget.bytes_used,
                    elapsed_seconds=time.monotonic() - started,
                    updated_ms=time.time_ns() // 1_000_000)
    dump(manifest, receipt)
    return dict(status=manifest['status'], coverage=manifest['coverage'],
                manifest=str(receipt), normalized_file=str(output),
                requests=budget.requests_used, body_bytes=budget.bytes_used,
                frozen_selector_certified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    result = collect_doge_marks(args.cache)
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
