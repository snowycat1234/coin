"""Small independent venue cache; never writes or certifies frozen Binance inputs.

Reuses the collector's atomic receipt writer and file checksum helper. Prices and
volumes retain their native units. Historical publication time is UNKNOWN; a
completed candle's close is only a boundary, not proof of past availability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

import requests

from .common import DAY_MS, MINUTE_MS, atomic_text, dump, sha256

VERSION = 'public-supplement-1'
BASES = {'bybit': 'https://api.bybit.com', 'okx': 'https://www.okx.com'}
DAILY_START, DAILY_END = 1751328000000, 1767225600000
REFERENCES = ('WIFUSDT', 'WLDUSDT', 'ORDIUSDT', '1000PEPEUSDT', '1000SATSUSDT')
NATIVE_BASES = dict(zip(REFERENCES, ('WIF', 'WLD', 'ORDI', 'PEPE', 'SATS'), strict=True))
BYBIT_IDS = dict(zip(REFERENCES, ('WIFUSDT', 'WLDUSDT', 'ORDIUSDT',
                                 '1000PEPEUSDT', '10000SATSUSDT'), strict=True))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Job:
    provider: str
    reference_symbol: str
    instrument_id: str
    market: str
    kind: str
    interval: str
    start_ms: int
    end_ms: int  # exclusive
    retention_start_ms: int | None = None
    retention_evidence: str | None = None

    def __post_init__(self):
        if self.provider not in BASES or self.market not in ('spot', 'perpetual'):
            raise ValueError('Explicit independent provider and spot/perpetual market required')
        if self.reference_symbol not in (*REFERENCES, 'DOGEUSDT'):
            raise ValueError('Only the requested six reference instruments are authorized')
        if self.kind not in ('trade', 'mark') or self.interval not in ('1d', '1m'):
            raise ValueError('Only trade/mark daily/minute bars are supported')
        if self.market == 'spot' and self.kind == 'mark':
            raise ValueError('Spot trade candles are not perpetual mark prices')
        step = self.step
        if (type(self.start_ms) is not int or type(self.end_ms) is not int
                or self.start_ms % step or self.end_ms % step or self.start_ms >= self.end_ms):
            raise ValueError('Exact UTC millisecond aligned exclusive bounds required')
        if not DAILY_START <= self.start_ms < self.end_ms <= DAILY_END:
            raise ValueError('Only July–December 2025 is authorized')
        if self.interval == '1d' and self.count > 184:
            raise ValueError('At most 184 daily bars per instrument')
        if self.interval == '1m' and (self.reference_symbol != 'DOGEUSDT'
                                      or self.kind != 'mark' or self.start_ms < 1764547200000):
            raise ValueError('Minute interface is only for DOGE December mark prices')
        if not self.instrument_id or not self.instrument_id.replace('-', '').isalnum():
            raise ValueError('Explicit native instrument id required')
        if self.retention_start_ms is not None and not self.retention_evidence:
            raise ValueError('Retention limits require explicit evidence, not an empty response')

    @property
    def step(self):
        return DAY_MS if self.interval == '1d' else MINUTE_MS

    @property
    def count(self):
        return (self.end_ms - self.start_ms) // self.step


def daily_jobs(provider):
    return [Job(provider, ref, BYBIT_IDS[ref] if provider == 'bybit'
                else NATIVE_BASES[ref] + '-USDT-SWAP', 'perpetual', 'trade', '1d',
                DAILY_START, DAILY_END) for ref in REFERENCES]


def mark_job(provider):
    return Job(provider, 'DOGEUSDT', 'DOGEUSDT' if provider == 'bybit'
               else 'DOGE-USDT-SWAP', 'perpetual', 'mark', '1m', 1764547200000, DAILY_END)


class Failure(RuntimeError):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status


@dataclass
class Budget:
    max_requests: int = 20
    max_bytes: int = 5_000_000
    max_response_bytes: int = 1_000_000
    max_attempts: int = 2
    min_interval_seconds: float = 1.0
    requests_used: int = 0
    bytes_used: int = 0
    denied_providers: set = field(default_factory=set)
    last_request: float = 0.0

    def __post_init__(self):
        if (not 1 <= self.max_requests <= 20 or not 0 < self.max_bytes <= 5_000_000
                or not 0 < self.max_response_bytes <= 1_000_000
                or not 1 <= self.max_attempts <= 3
                or not math.isfinite(self.min_interval_seconds)
                or self.min_interval_seconds < 0.5
                or not 0 <= self.requests_used <= self.max_requests
                or not 0 <= self.bytes_used <= self.max_bytes):
            raise ValueError('Public read budget exceeds task bounds')


def _payload(raw, provider):
    try:
        value = json.loads(raw)
        code = value['retCode'] if provider == 'bybit' else value['code']
    except (ValueError, KeyError, TypeError) as exc:
        raise Failure('INVALID_RESPONSE', 'Not a recognized provider JSON envelope') from exc
    if str(code) != '0':
        message = str(value.get('retMsg', value.get('msg', '')))
        if str(code) in ('10009', '10010', '10024', '10027', '50110', '50120'):
            raise Failure('PERMISSION_DENIED', f'Provider code {code}: {message}')
        if str(code) in ('10006', '50011'):
            raise Failure('RATE_LIMITED', f'Provider code {code}: {message}')
        raise Failure('API_FAILURE', f'Provider code {code}: {message}')
    return value


def metadata_request(job):
    if job.provider == 'bybit':
        return '/v5/market/instruments-info', {'category': 'linear' if job.market == 'perpetual'
                                             else 'spot', 'symbol': job.instrument_id}
    return '/api/v5/public/instruments', {'instType': 'SWAP' if job.market == 'perpetual'
                                        else 'SPOT', 'instId': job.instrument_id}


def instrument_identity(job, raw):
    value = _payload(raw, job.provider)
    records = value.get('result', {}).get('list') if job.provider == 'bybit' else value.get('data')
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise Failure('INVALID_RESPONSE', 'Missing native instrument metadata list')
    id_field = 'symbol' if job.provider == 'bybit' else 'instId'
    matches = [row for row in records if row.get(id_field) == job.instrument_id]
    if len(matches) != 1:
        raise Failure('INSTRUMENT_UNAVAILABLE', 'No unique exact native instrument metadata')
    row = matches[0]
    expected_base = NATIVE_BASES.get(job.reference_symbol, 'DOGE')
    if job.provider == 'bybit':
        base, quote = row.get('baseCoin'), row.get('quoteCoin')
        multiplier = '1'
        if expected_base == 'PEPE' and base == '1000PEPE':
            multiplier = '1000'
        elif expected_base == 'SATS' and base == '10000SATS':
            multiplier = '10000'
        elif base != expected_base:
            raise Failure('IDENTITY_MISMATCH', 'Native base coin is not the requested asset')
        product = row.get('contractType') if job.market == 'perpetual' else 'Spot'
        if job.market == 'perpetual' and product != 'LinearPerpetual':
            raise Failure('IDENTITY_MISMATCH', 'Exact linear perpetual metadata required')
        settle = row.get('settleCoin') if job.market == 'perpetual' else None
        contract_value, contract_currency, contract_multiplier = multiplier, expected_base, '1'
    else:
        base = row.get('baseCcy') if job.market == 'spot' else row.get('ctValCcy')
        quote = row.get('quoteCcy') if job.market == 'spot' else row.get('settleCcy')
        expected_type = 'SPOT' if job.market == 'spot' else 'SWAP'
        if row.get('instType') != expected_type or base != expected_base:
            raise Failure('IDENTITY_MISMATCH', 'Wrong native product or contract value currency')
        product, settle = expected_type, row.get('settleCcy') or None
        if job.market == 'perpetual' and row.get('ctType') != 'linear':
            raise Failure('IDENTITY_MISMATCH', 'Linear USDT swap required')
        multiplier = '1'  # quoted price is USDT per underlying; ctVal governs contract volume
        contract_value = row.get('ctVal') if job.market == 'perpetual' else '1'
        contract_multiplier = row.get('ctMult') if job.market == 'perpetual' else '1'
        contract_currency = base
        try:
            for number in (contract_value, contract_multiplier):
                if not Decimal(number).is_finite() or Decimal(number) <= 0:
                    raise ValueError('Nonpositive contract value/multiplier')
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise Failure('IDENTITY_MISMATCH',
                          'Known positive native contract value/multiplier required') from exc
    if quote != 'USDT' or (job.market == 'perpetual' and settle != 'USDT'):
        raise Failure('IDENTITY_MISMATCH', 'Exact USDT quote and settlement required')
    return dict(provider=job.provider, instrument_id=job.instrument_id, market=job.market,
                native_base=base, underlying_asset=expected_base, quote_currency=quote,
                settlement_currency=settle, product=product,
                price_underlying_multiplier=multiplier, contract_value=contract_value,
                contract_value_currency=contract_currency, contract_multiplier=contract_multiplier,
                reference_provider='Binance', reference_symbol=job.reference_symbol,
                reference_price_underlying_multiplier=(
                    '1000' if job.reference_symbol.startswith('1000') else '1'),
                prices_rescaled=False, metadata_scope='CURRENT_NOT_HISTORICAL_CERTIFICATION',
                native_metadata=row)


def bars_request(job, start, end):
    limit = min((end - start) // job.step, 100)
    if job.provider == 'bybit':
        path = '/v5/market/kline' if job.kind == 'trade' else '/v5/market/mark-price-kline'
        return path, dict(category='linear' if job.market == 'perpetual' else 'spot',
                          symbol=job.instrument_id, interval='D' if job.interval == '1d' else '1',
                          start=start, end=end - 1, limit=limit)
    path = '/api/v5/market/history-candles' if job.kind == 'trade' else \
        '/api/v5/market/history-mark-price-candles'
    return path, dict(instId=job.instrument_id, bar='1Dutc' if job.interval == '1d' else '1m',
                      after=end, before=start - 1, limit=limit)


def normalize(job, raw, identity, received_ms, raw_sha256, start=None, end=None):
    if any(identity.get(key) != getattr(job, key)
           for key in ('provider', 'instrument_id', 'market')):
        raise Failure('IDENTITY_MISMATCH', 'Normalization identity does not match the job')
    value = _payload(raw, job.provider)
    start, end = job.start_ms if start is None else start, job.end_ms if end is None else end
    if job.provider == 'bybit':
        result = value.get('result', {})
        category = 'linear' if job.market == 'perpetual' else 'spot'
        if result.get('symbol') != job.instrument_id or result.get('category') != category:
            raise Failure('IDENTITY_MISMATCH', 'Bybit returned a different instrument/category')
        records = result.get('list')
    else:
        records = value.get('data')  # OKX omits instrument; exact request is the binding
    if not isinstance(records, list):
        raise Failure('INVALID_RESPONSE', 'Missing candle list')
    rows, seen = [], set()
    for row in records:
        expected_width = (7 if job.kind == 'trade' else 5) if job.provider == 'bybit' \
            else (9 if job.kind == 'trade' else 6)
        if (not isinstance(row, list) or len(row) != expected_width
                or any(not isinstance(item, str) for item in row)):
            raise Failure('INVALID_RESPONSE', 'Unexpected native row schema')
        if not row[0].isascii() or not row[0].isdigit():
            raise Failure('INVALID_RESPONSE', 'Explicit millisecond timestamp string required')
        stamp = int(row[0])
        if stamp % job.step or not start <= stamp < end or stamp in seen:
            raise Failure('INVALID_RESPONSE', 'Unaligned, duplicate, or out-of-window timestamp')
        seen.add(stamp)
        try:
            op, hi, lo, cl = map(Decimal, row[1:5])
            numbers = [Decimal(v) for v in (row[1:-1] if job.provider == 'okx' else row[1:])]
            if (any(not n.is_finite() for n in numbers) or min(op, hi, lo, cl) <= 0
                    or hi < max(op, lo, cl) or lo > min(op, hi, cl)
                    or any(n < 0 for n in numbers[4:])):
                raise ValueError('Invalid native OHLC/volume')
        except (ValueError, ArithmeticError) as exc:
            raise Failure('INVALID_RESPONSE', 'Invalid native numeric values') from exc
        if job.provider == 'okx' and row[-1] not in ('0', '1'):
            raise Failure('INVALID_RESPONSE', 'Unknown candle completion flag')
        if (job.provider == 'okx' and row[-1] != '1') or stamp + job.step > received_ms:
            continue  # unfinished observations never count toward complete coverage
        rows.append(dict(provider=job.provider, instrument_id=job.instrument_id,
                         market=job.market, kind=job.kind, interval=job.interval,
                         identity_sha256=fingerprint(identity), open_ms=stamp,
                         close_ms_exclusive=stamp + job.step, received_ms=received_ms,
                         historical_available_ms=None, publication_time_certified=False,
                         available_ms=received_ms, availability_basis='LOCAL_RETRIEVAL_ONLY',
                         open=row[1], high=row[2], low=row[3], close=row[4],
                         native_volume_fields=(row[5:-1] if job.provider == 'okx' else row[5:])
                         if job.kind == 'trade' else None,
                         volume_units=('contracts,base,quote' if job.market == 'perpetual'
                                       else 'base,base,quote') if job.provider == 'okx'
                         else 'base,quote', raw_sha256=raw_sha256))
    return sorted(rows, key=lambda row: row['open_ms'])


def coverage(job, rows):
    actual = {row['open_ms'] for row in rows}
    missing = [stamp for stamp in range(job.start_ms, job.end_ms, job.step) if stamp not in actual]
    ranges = []
    for stamp in missing:
        if ranges and ranges[-1][1] == stamp:
            ranges[-1][1] += job.step
        else:
            ranges.append([stamp, stamp + job.step])
    return dict(expected_bars=job.count, observed_bars=len(actual), missing_bars=len(missing),
                missing_ranges_ms_exclusive=ranges,
                status='COMPLETE' if not missing else 'INCOMPLETE_COVERAGE')


def _read(job, path, params, directory, manifest, budget, session):
    url = BASES[job.provider] + path
    request_key = fingerprint([url, params])
    attempts = [r for r in manifest['requests'] if r['request_key'] == request_key]
    for record in attempts:
        if record['status'] == 'OK':
            return (directory / record['raw_file']).read_bytes(), record
        if record['status'] in ('PERMISSION_DENIED', 'RATE_LIMITED'):
            budget.denied_providers.add(job.provider)
            raise Failure(record['status'], 'Persisted endpoint denial; no retry')
    if attempts and not attempts[-1].get('retryable', True):
        raise Failure(attempts[-1]['status'], attempts[-1].get('detail', 'Persisted failure'))
    if job.provider in budget.denied_providers:
        raise Failure('PERMISSION_DENIED', 'Provider was already denied in this invocation')
    for attempt in range(len(attempts), budget.max_attempts):
        if budget.requests_used >= budget.max_requests or budget.bytes_used >= budget.max_bytes:
            raise Failure('BUDGET_EXHAUSTED', 'Bounded public read budget exhausted')
        time.sleep(max(0, budget.min_interval_seconds - (time.monotonic() - budget.last_request)))
        budget.last_request = time.monotonic()
        budget.requests_used += 1
        record = dict(request_key=request_key, url=url, params=params, attempt=attempt + 1,
                      requested_ms=time.time_ns() // 1_000_000, status='REQUEST_STARTED')
        manifest['requests'].append(record)
        dump(manifest, directory / 'manifest.json')  # interrupted calls consume their retry slot
        retryable, raw = False, bytearray()
        try:
            with session.get(url, params=params, timeout=(5, 10), stream=True,
                             allow_redirects=False) as response:
                record['http_status'] = response.status_code
                record['response_headers'] = {k: response.headers.get(k)
                                              for k in ('Date', 'Content-Type')}
                for block in response.iter_content(64 * 1024):
                    budget.bytes_used += len(block)
                    if (len(raw) + len(block) > budget.max_response_bytes
                            or budget.bytes_used > budget.max_bytes):
                        raise Failure('RESPONSE_LIMIT', 'Public response exceeded the byte bound')
                    raw.extend(block)
                if response.status_code in (401, 403, 418, 451):
                    raise Failure('PERMISSION_DENIED', f'HTTP {response.status_code}')
                if response.status_code == 429:
                    raise Failure('RATE_LIMITED', 'HTTP 429; endpoint stopped')
                if response.status_code != 200:
                    retryable = response.status_code in (500, 502, 503, 504)
                    raise Failure('HTTP_FAILURE',
                                  f'HTTP {response.status_code}; not retention evidence')
                _payload(raw, job.provider)
                record['status'] = 'OK'
        except requests.RequestException as exc:
            record.update(status='TRANSPORT_FAILURE', detail=type(exc).__name__ + ': ' + str(exc))
            retryable = isinstance(exc, (requests.ConnectionError, requests.Timeout))
        except Failure as exc:
            record.update(status=exc.status, detail=str(exc))
        finally:
            record['retryable'] = retryable
            record['received_ms'] = time.time_ns() // 1_000_000
            record['body_bytes'] = len(raw)
            record['raw_sha256'] = hashlib.sha256(raw).hexdigest()
            record['raw_file'] = record['raw_sha256'] + '.raw'
            target = directory / record['raw_file']
            if not target.exists():
                target.write_bytes(raw)
            record['checksum_basis'] = 'LOCAL_SHA256_NOT_PROVIDER_ATTESTATION'
            dump(manifest, directory / 'manifest.json')
        if record['status'] == 'OK':
            return bytes(raw), record
        if record['status'] in ('PERMISSION_DENIED', 'RATE_LIMITED'):
            budget.denied_providers.add(job.provider)
        if not retryable or attempt + 1 == budget.max_attempts:
            raise Failure(record['status'], record['detail'])
        time.sleep(min(2 ** attempt, 2))
    raise Failure('RETRY_EXHAUSTED', 'Persisted request attempt bound exhausted')


def collect(job, cache, budget, session=None):
    """Daily live supplementation only. Minute plans can be normalized offline.

    Resume verifies all retained raw/normalized bytes and skips successful pages.
    There is no implicit provider fallback or automatic failed-page budget reset.
    """
    cache = Path(cache).resolve()
    checkout = Path(__file__).resolve().parents[3]
    if cache.is_relative_to(checkout):
        raise ValueError('Supplement cache must be outside the source checkout')
    if job.interval == '1m':
        return dict(job=asdict(job), status='NOT_RUN_MINUTE_HISTORY_NOT_AUTHORIZED',
                    frozen_selector_certified=False)
    binding = dict(version=VERSION, job=asdict(job), source_sha256=sha256(Path(__file__)),
                   dataset_role='ALTERNATIVE_VENUE_ROBUSTNESS_ONLY', original_provider='Binance',
                   frozen_selector_certified=False, replaces_original_observations=False)
    directory = cache / job.provider / fingerprint([VERSION, asdict(job)])[:24]
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / 'manifest.json'
    manifest = json.loads(receipt.read_text()) if receipt.exists() else dict(
        binding=binding, requests=[], status='PENDING')
    if manifest['binding'] != binding:
        raise ValueError('Saved supplement source or request binding changed')
    access_stop = cache / job.provider / 'access-stop.json'
    if access_stop.exists():
        budget.denied_providers.add(job.provider)
    for record in manifest['requests']:
        if 'raw_file' in record and sha256(directory / record['raw_file']) != record['raw_sha256']:
            raise ValueError('Retained raw checksum mismatch')
    output = directory / 'bars.jsonl'
    if output.exists() and sha256(output) != manifest.get('normalized_sha256'):
        raise ValueError('Retained normalized checksum mismatch')
    rows = []
    owned_session = session is None
    session = session or requests.Session()  # defaults only; no proxy/security/credential changes
    try:
        if job.retention_start_ms is not None and job.start_ms < job.retention_start_ms:
            raise Failure('HISTORICAL_RETENTION_MISSING', job.retention_evidence)
        raw, metadata = _read(job, *metadata_request(job), directory, manifest, budget, session)
        identity = instrument_identity(job, raw)
        identity['metadata_raw_sha256'] = metadata['raw_sha256']
        manifest['identity'] = identity
        for start in range(job.start_ms, job.end_ms, 100 * job.step):
            end = min(start + 100 * job.step, job.end_ms)
            raw, record = _read(job, *bars_request(job, start, end), directory,
                                manifest, budget, session)
            page = normalize(job, raw, identity, record['received_ms'],
                             record['raw_sha256'], start, end)
            record['observed_bars'] = len(page)
            record['coverage_note'] = 'OBSERVED' if page else 'HISTORY_UNAVAILABLE_UNCLASSIFIED'
            rows.extend(page)
        manifest['status'] = coverage(job, rows)['status']
        manifest.pop('last_failure', None)
    except Failure as exc:
        manifest.update(status=exc.status, last_failure=dict(status=exc.status, detail=str(exc)))
        if exc.status in ('PERMISSION_DENIED', 'RATE_LIMITED') and not access_stop.exists():
            dump(dict(provider=job.provider, status=exc.status, detail=str(exc),
                      manifest=str(receipt), stopped_ms=time.time_ns() // 1_000_000), access_stop)
    finally:
        if owned_session:
            session.close()
    # If an interrupted resume failed before replaying cached pages, retain its good prior bars.
    if output.exists():
        prior = [json.loads(line) for line in output.read_text().splitlines()]
        merged = {row['open_ms']: row for row in prior}
        merged.update({row['open_ms']: row for row in rows})
        rows = list(merged.values())
    rows.sort(key=lambda row: row['open_ms'])
    atomic_text(output, ''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n'
                               for row in rows))
    manifest.update(coverage=coverage(job, rows), normalized_sha256=sha256(output),
                    normalized_file='bars.jsonl', updated_ms=time.time_ns() // 1_000_000)
    dump(manifest, receipt)
    return dict(status=manifest['status'], coverage=manifest['coverage'],
                identity=manifest.get('identity'), manifest=str(receipt),
                manifest_sha256=sha256(receipt), frozen_selector_certified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=tuple(BASES), required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--collect-daily', action='store_true', help='Otherwise print plan; no IO')
    args = parser.parse_args()
    jobs = daily_jobs(args.provider)
    if not args.collect_daily:
        print(json.dumps(dict(daily=[asdict(j) for j in jobs], mark=asdict(mark_job(args.provider)),
                              minute_network_status='NOT_AUTHORIZED',
                              frozen_selector_certified=False)))
        return 0
    budget, results = Budget(), []
    with requests.Session() as session:
        for job in jobs:
            results.append(collect(job, args.cache, budget, session))
            if (budget.denied_providers
                    or results[-1]['status'] in ('BUDGET_EXHAUSTED', 'RESPONSE_LIMIT')):
                break
    print(json.dumps(dict(results=results, requests=budget.requests_used,
                          body_bytes=budget.bytes_used)))
    return 0 if len(results) == len(jobs) and all(r['status'] == 'COMPLETE' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
