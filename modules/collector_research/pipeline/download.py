from __future__ import annotations
import calendar
import hashlib
import json
import re
import threading
import time
import zipfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .common import E, RAW, REPORTS, atomic_text, bounds, disk_guard, dump, init_dirs, log, months, progress, sha256, symbols

BASE = 'https://data.binance.vision/data/futures/um'
FAMILIES = ('klines', 'markPriceKlines', 'premiumIndexKlines', 'fundingRate')
_WRITE_LOCK = threading.Lock()


class DownloadReservations:
    """Reserve the worst-case bytes of every simultaneous archive before starting."""
    def __init__(self):
        self.lock = threading.Lock()
        self.reserved = 0
        self.per_job = int(float(E('MAX_ARCHIVE_MIB')) * 2**20) + 8192

    def acquire(self):
        with self.lock:
            disk_guard(self.reserved + self.per_job)
            self.reserved += self.per_job

    def release(self):
        with self.lock:
            self.reserved -= self.per_job

    def refresh(self):
        with self.lock:
            disk_guard(self.reserved)

@dataclass(frozen=True)
class Job:
    symbol: str
    family: str
    year: int
    month: int
    day: int | None = None

    @property
    def stem(self) -> str:
        stamp = f'{self.year}-{self.month:02d}' + (f'-{self.day:02d}' if self.day else '')
        middle = 'fundingRate' if self.family == 'fundingRate' else '1m'
        return f'{self.symbol}-{middle}-{stamp}.zip'

    @property
    def path(self) -> Path:
        return RAW / self.family / self.symbol / self.stem

    @property
    def url(self) -> str:
        partition = 'daily' if self.day else 'monthly'
        interval = '' if self.family == 'fundingRate' else '/1m'
        return f'{BASE}/{partition}/{self.family}/{self.symbol}{interval}/{self.stem}'

    def record(self) -> dict:
        return {**asdict(self), 'url': self.url, 'path': str(self.path)}


def planned_jobs() -> list[Job]:
    start, end = bounds()
    families = E('FAMILIES').split(',')
    if len(families) != len(set(families)) or not set(families) <= set(FAMILIES):
        raise ValueError('Unknown/duplicate archive family')
    if not {'klines', 'markPriceKlines', 'fundingRate'} <= set(families):
        raise ValueError('Trade klines, markPriceKlines and fundingRate are required')
    return [Job(s, f, y, m) for s in symbols() for y, m in months(start, end) for f in families]


def session() -> requests.Session:
    retry = Retry(total=int(E('HTTP_RETRIES')), backoff_factor=0.8,
                  status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET', 'HEAD'],
                  respect_retry_after_header=True)
    s = requests.Session()
    s.headers['User-Agent'] = 'coin-collector-v3/20261006'
    s.mount('https://', HTTPAdapter(max_retries=retry))
    # Uses only the caller's existing proxy environment. No profile download/service changes.
    return s


def parse_checksum(text: str, filename: str) -> str:
    fields = text.strip().split()
    if len(fields) != 2 or not re.fullmatch('[0-9a-fA-F]{64}', fields[0]) or fields[1].lstrip('*') != filename:
        raise ValueError(f'Malformed or wrong-file official checksum for {filename}')
    return fields[0].lower()


def check_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        if len(infos) != 1:
            raise ValueError(f'{path.name}: expected exactly one CSV')
        i = infos[0]
        # Never extract ZIP member paths.
        if i.filename != path.name.removesuffix('.zip') + '.csv' or i.flag_bits & 1:
            raise ValueError(f'{path.name}: unexpected ZIP member or encryption')
        if not 0 < i.file_size <= float(E('MAX_UNCOMPRESSED_MIB')) * 2**20:
            raise ValueError('Uncompressed archive exceeds bound or is empty')
        if z.testzip() is not None:
            raise ValueError(f'ZIP CRC failed: {path.name}')
        return dict(csv_bytes=i.file_size, member=i.filename)


def verify_local(path: Path) -> dict:
    cp = Path(str(path) + '.CHECKSUM')
    if not cp.exists():
        raise ValueError(f'{path.name}: missing .CHECKSUM; run collect once to adopt old caches')
    expected = parse_checksum(cp.read_text(encoding='utf-8'), path.name)
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f'SHA256 mismatch: {path.name}')
    return dict(sha256=actual, bytes=path.stat().st_size, **check_zip(path))


def validate_range(header: str | None, have: int) -> tuple[int, int]:
    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', header or '')
    if not match:
        raise ValueError('Missing/malformed Content-Range on HTTP 206')
    lo, hi, total = map(int, match.groups())
    if lo != have or hi < lo or hi >= total:
        raise ValueError('HTTP Range response does not match retained partial')
    return hi, total


def fetch(job: Job, s: requests.Session, *, reserved: bool = False) -> dict:
    out = job.path
    out.parent.mkdir(parents=True, exist_ok=True)
    cp = Path(str(out) + '.CHECKSUM')
    tmp = Path(str(out) + '.part')
    timeout = (float(E('HTTP_CONNECT_TIMEOUT')), float(E('HTTP_READ_TIMEOUT')))
    cached_valid = None
    if out.exists() and cp.exists():
        try:
            cached_valid = verify_local(out)
        except (ValueError, zipfile.BadZipFile):
            cached_valid = None
        if cached_valid is not None and E('REFRESH_CHECKSUMS') != '1':
            return {**job.record(), 'status': 'VERIFIED_CACHE', **cached_valid}
    # Get the checksum BEFORE accepting/downloading a ZIP. 403 is not "prelisting".
    r = s.get(job.url + '.CHECKSUM', timeout=timeout)
    if r.status_code == 404:
        return {**job.record(), 'status': 'ARCHIVE_UNAVAILABLE_UNCLASSIFIED',
                'note': '404 is not proof of prelisting, delisting, or zero funding'}
    r.raise_for_status()
    if len(r.content) > 4096:
        raise ValueError('Checksum response too large')
    expected = parse_checksum(r.text, out.name)
    if out.exists() and sha256(out) == expected:
        info = check_zip(out)
        atomic_text(cp, r.text)
        return {**job.record(), 'status': 'ADOPTED_VERIFIED_CACHE', 'sha256': expected,
                'bytes': out.stat().st_size, **info}
    if out.exists():
        # Keep evidence. No replacement until a verified complete file exists.
        log(f'{out.name}: cached bytes differ from checksum; downloading replacement, old bytes retained')
    max_bytes = int(float(E('MAX_ARCHIVE_MIB')) * 2**20)
    if not reserved:
        disk_guard(max_bytes)
    last_error: Exception | None = None
    for attempt in range(int(E('HTTP_RETRIES')) + 1):
        have = tmp.stat().st_size if tmp.exists() else 0
        if have > max_bytes:
            raise ValueError('Retained partial exceeds MAX_ARCHIVE_MIB')
        headers = {'Range': f'bytes={have}-'} if have else {}
        try:
            with s.get(job.url, timeout=timeout, stream=True, headers=headers) as rr:
                if rr.status_code == 416 and have:
                    # A complete interrupted partial can be accepted only by SHA+CRC.
                    if sha256(tmp) == expected:
                        break
                    tmp.unlink(); continue
                rr.raise_for_status()
                if rr.status_code not in (200, 206):
                    raise ValueError(f'Unexpected HTTP {rr.status_code} for archive')
                append = rr.status_code == 206
                total = None
                if append:
                    _, total = validate_range(rr.headers.get('Content-Range'), have)
                else:
                    have = 0
                    if rr.headers.get('Content-Length'):
                        total = int(rr.headers['Content-Length'])
                if total is not None and total > max_bytes:
                    raise ValueError('Archive Content-Length exceeds limit')
                got = have
                with tmp.open('ab' if append else 'wb') as stream:
                    for block in rr.iter_content(1 << 20):
                        if not block:
                            continue
                        got += len(block)
                        if got > max_bytes:
                            raise ValueError('Archive stream exceeds limit')
                        # Serialize only the space check/write, never network I/O.
                        with _WRITE_LOCK:
                            disk_guard(len(block), scan=False)
                            stream.write(block)
                if total is not None and got != total:
                    raise requests.ConnectionError('Incomplete Content-Length; partial retained')
            if sha256(tmp) != expected:
                # Preserve untrusted bytes outside reusable .part; start a clean retry.
                tmp.replace(tmp.with_name(tmp.name + f'.bad-{time.time_ns()}'))
                raise requests.ConnectionError('Downloaded SHA mismatch; bad payload quarantined')
            break
        except requests.HTTPError:
            raise  # Explicit access denial does not trigger alternate venues/proxies.
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as exc:
            last_error = exc
            if attempt == int(E('HTTP_RETRIES')):
                raise
            time.sleep(min(2 ** attempt, 8))
    else:
        raise RuntimeError(f'No verified download: {job.stem}') from last_error
    if sha256(tmp) != expected:
        raise ValueError('Final partial SHA verification failed')
    # ZIP name checks need the logical final name, so stage in a separate directory.
    staging = out.parent / ('.verified-' + str(time.time_ns()))
    staging.mkdir()
    candidate = staging / out.name
    tmp.replace(candidate)
    try:
        info = check_zip(candidate)
        if out.exists():
            out.replace(out.with_name(out.name + f'.old-{time.time_ns()}'))
        candidate.replace(out)
        atomic_text(cp, r.text)
    finally:
        if not candidate.exists():
            staging.rmdir()
    return {**job.record(), 'status': 'DOWNLOADED_VERIFIED', 'sha256': expected,
            'bytes': out.stat().st_size, **info}


def collect() -> dict:
    init_dirs()
    jobs = planned_jobs()
    workers = int(E('DOWNLOAD_WORKERS', '16'))
    if not 1 <= workers <= 64:
        raise ValueError('DOWNLOAD_WORKERS must be between 1 and 64')
    completed = 0
    records = {}
    errors = []
    sessions = []
    session_lock = threading.Lock()
    thread_local = threading.local()
    reservations = DownloadReservations()
    report = REPORTS / 'download_manifest.json'

    def worker(job):
        items = []
        acquired = False
        try:
            reservations.acquire()
            acquired = True
            if not hasattr(thread_local, 'session'):
                thread_local.session = session()
                with session_lock:
                    sessions.append(thread_local.session)
            items.append(fetch(job, thread_local.session, reserved=True))
            if items[0]['status'] == 'ARCHIVE_UNAVAILABLE_UNCLASSIFIED' and E('DAILY_FALLBACK') == '1' and job.family != 'fundingRate':
                a, b = bounds()
                for day in range(1, calendar.monthrange(job.year, job.month)[1] + 1):
                    if a <= date(job.year, job.month, day) <= b:
                        reservations.refresh()
                        items.append(fetch(Job(job.symbol, job.family, job.year, job.month, day),
                                           thread_local.session, reserved=True))
            return items, None
        except Exception as exc:
            return items, exc
        finally:
            if acquired:
                reservations.release()

    def rows():
        # Completion order varies; the manifest's planned source order does not.
        return [row for index in sorted(records) for row in records[index]]

    log(f'COLLECT using {workers} independent HTTP workers for {len(jobs)} monthly jobs')
    progress('COLLECT', 0, len(jobs), f'Parallel download: {workers} workers')
    try:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='coin-download') as pool:
            pending = {}
            next_index = 0
            while next_index < len(jobs) or pending:
                while not errors and next_index < len(jobs) and len(pending) < workers:
                    pending[pool.submit(worker, jobs[next_index])] = next_index
                    next_index += 1
                if not pending:
                    break
                finished, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in finished:
                    index = pending.pop(future)
                    items, error = future.result()
                    records[index] = items
                    job = jobs[index]
                    if error is None:
                        completed += 1
                        log(f'COLLECT {completed}/{len(jobs)} {job.symbol}/{job.family}/{job.stem}: {items[0]["status"]}')
                    else:
                        errors.append((index, error))
                        log(f'COLLECT failed {job.symbol}/{job.family}/{job.stem}: {type(error).__name__}: {error}')
                    progress('COLLECT', completed, len(jobs),
                             f'{job.stem}:{job.family}; workers={workers}; in_flight={len(pending)}')
                    dump(dict(status='FAILED_DRAINING' if errors else 'RUNNING', completed=completed,
                              planned=len(jobs), workers=workers, archives=rows()), report)
                # Once a job fails, drain the already-running workers and preserve
                # their successful results, but launch no further source requests.
        if errors:
            raise sorted(errors, key=lambda item: item[0])[0][1]
        result = dict(status='FINISHED_SOURCE_INVENTORY_NOT_COMPLETENESS_CERTIFICATION',
                      completed=completed, planned=len(jobs), workers=workers, archives=rows(),
                      source='Binance USD-M public archive; not Bybit native',
                      created_utc=datetime.now(timezone.utc).isoformat())
        dump(result, report)
        progress('COLLECT', len(jobs), len(jobs), 'Finished; normalization/audit still required')
        return result
    except Exception as exc:
        dump(dict(status='FAILED_PARTIAL_PRESERVED', completed=completed, planned=len(jobs), workers=workers,
                  error_type=type(exc).__name__, error=str(exc), archives=rows()), report)
        raise
    finally:
        for s in sessions:
            s.close()


def sources_for_month(symbol: str, family: str, y: int, m: int) -> list[Path]:
    # Explicit allow-listed dates, not recursive discovery of old/locked caches.
    a, b = bounds()
    j = Job(symbol, family, y, m)
    if j.path.exists():
        return [j.path]
    result = []
    for day in range(1, calendar.monthrange(y, m)[1] + 1):
        if a <= date(y, m, day) <= b:
            p = Job(symbol, family, y, m, day).path
            if p.exists():
                result.append(p)
    return result
