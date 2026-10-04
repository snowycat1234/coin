"""Historical USD-M universe, causal daily pool and daily minute blocks.

The existing pinned official downloader and format parsers do the source work.
Inventory includes historical folders; current exchangeInfo is never a pool.
Pool prices precede September. Explicit September/October/November source windows use
the same frozen July pool. Missing assets stay missing, not zero.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import re
import resource
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
import numpy as np
import polars as pl
from quant import data, disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_trade_source as trade
from scripts.research_v8 import funding_price_source_v2 as formats

DAY = 86_400_000_000
MINUTE = 60_000_000
START = int(datetime(2024, 9, 1, tzinfo=UTC).timestamp()) * 1_000_000
END = int(datetime(2024, 10, 1, tzinfo=UTC).timestamp()) * 1_000_000
OCT_END = int(datetime(2024, 11, 1, tzinfo=UTC).timestamp()) * 1_000_000
NOV_END = int(datetime(2024, 12, 1, tzinfo=UTC).timestamp()) * 1_000_000
WINTER_JAN = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) * 1_000_000
WINTER_FEB = int(datetime(2025, 2, 1, tzinfo=UTC).timestamp()) * 1_000_000
WINTER_END = int(datetime(2025, 3, 1, tzinfo=UTC).timestamp()) * 1_000_000
SPRING_APR = int(datetime(2025, 4, 1, tzinfo=UTC).timestamp()) * 1_000_000
SPRING_MAY = int(datetime(2025, 5, 1, tzinfo=UTC).timestamp()) * 1_000_000
SPRING_JUN = int(datetime(2025, 6, 1, tzinfo=UTC).timestamp()) * 1_000_000
SPRING_END = int(datetime(2025, 7, 1, tzinfo=UTC).timestamp()) * 1_000_000
COMPONENT = 'reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json'
COMPONENT_SHA = '8a2ae22bd5bbf60763df352abb50d380763ba1fe19ac6545cc398f8d45d3ce96'
# This is the bucket configured by the official public-data index. The metadata
# run also preserves the index HTML and verifies that exact bucket declaration.
INDEX = 'https://data.binance.vision/'
BUCKET = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
PREFIX = 'data/futures/um/monthly/klines/'
RULES = dict(score_start='2024-09-01', score_end_exclusive='2024-10-01',
    ranking_month='2024-07', selection_decision_us=START, desired_assets=10,
    minimum_observed_age_days=200, warmup_completed_days=200,
    past_return_days=31, tie_break='SYMBOL_ASCENDING',
    ranking='JULY_OFFICIAL_USDM_DAILY_QUOTE_VOLUME_SUM',
    listing='EARLIEST_OBSERVED_DAILY_BAR_PROXY_NOT_EXCHANGE_LISTING_CERTIFICATE',
    unknown_above_cutoff='DO_NOT_CERTIFY_GLOBAL_TOP10',
    no_current_exchange_info=True, score_returns_used_for_selection=False,
    publication='CLOSED_BAR_PROXY; JULY_MONTHLY_AVAILABLE_BEFORE_SEPTEMBER',
    native_Bybit_certified=False, funding_unit_certified=False,
    missing='RETAIN_REASON; NO_IMPUTATION_OR_RETURN_BASED_REPLACEMENT')
DEFAULT_BUDGETS = dict(inventory_pages=4, inventory_page_bytes=512_000,
    inventory_owned_bytes=3_000_000, inventory_wall_seconds=120,
    max_candidates=1200, max_qualification_candidates=60,
    daily_zip_bytes=64_000, daily_csv_bytes=128_000,
    market_zip_bytes=16_000_000, market_csv_bytes=128_000_000,
    pool_owned_bytes=150_000_000, market_owned_bytes=300_000_000,
    request_seconds=20, source_file_seconds=30, source_wall_seconds=3600)
OCTOBER_RULES = dict(RULES, score_start='2024-10-01', score_end_exclusive='2024-11-01',
    selection='SAME_FROZEN_JULY_POOL_NO_RESELECTION',
    warmup='ACCEPTED_FEB_AUG_1D_PLUS_ACCEPTED_SEPTEMBER_1M_CAUSAL_DAILY_REDUCTION',
    new_market_files=24, reused_market_files=6)
OCTOBER_BUDGETS = dict(DEFAULT_BUDGETS, market_owned_bytes=300_000_000,
    input_owned_bytes=200_000_000, temporary_owned_bytes=100_000_000,
    source_wall_seconds=1800)
NOVEMBER_RULES = dict(OCTOBER_RULES, score_start='2024-11-01', score_end_exclusive='2024-12-01',
    warmup='ACCEPTED_FEB_AUG_1D_PLUS_ACCEPTED_SEPTEMBER_OCTOBER_1M_CAUSAL_DAILY_REDUCTION')
NOVEMBER_BUDGETS = dict(OCTOBER_BUDGETS, peak_RSS_bytes=1_000_000_000)
NOVEMBER_CONTRACT = 'D054_FIXED_JULY_POOL_NOVEMBER_SOURCE_V1'
NOVEMBER_SOURCE_STATUS = 'COMPLETE_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_PENDING_ACCEPTANCE'
NOVEMBER_MANIFEST_STATUS = 'PASS_D054_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'
WINTER_CONTRACT = 'D056_FIXED_JULY_POOL_WINTER_SOURCE_V1'
WINTER_SOURCE_STATUS = 'COMPLETE_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_PENDING_ACCEPTANCE'
WINTER_ACCEPTANCE_STATUS = 'PASS_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ONLY'
WINTER_MANIFEST_STATUS = 'PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS'
WINTER_SCOPES = (('2024-12', NOV_END, WINTER_JAN),
                 ('2025-01', WINTER_JAN, WINTER_FEB), ('2025-02', WINTER_FEB, WINTER_END))
WINTER_RULES = dict(NOVEMBER_RULES, score_start='2024-12-01', score_end_exclusive='2025-03-01',
    score_months=[r[0] for r in WINTER_SCOPES], new_market_files=72, reused_market_files=18,
    warmup='ACCEPTED_FEB_AUG_1D_PLUS_ACCEPTED_SEP_NOV_1M_CAUSAL_DAILY_REDUCTION')
WINTER_BUDGETS = dict(NOVEMBER_BUDGETS)
SPRING_CONTRACT = 'D062_FIXED_JULY_POOL_SPRING_SOURCE_V1'
SPRING_SOURCE_STATUS = 'COMPLETE_D062_FIXED_POOL_SPRING_SOURCE_FORMAT_PENDING_ACCEPTANCE'
SPRING_ACCEPTANCE_STATUS = 'PASS_D062_FIXED_POOL_SPRING_SOURCE_FORMAT_ONLY'
SPRING_MANIFEST_STATUS = 'PASS_D062_SELECTED_PORTFOLIO_SPRING_SOURCE_BINDING_NOT_ECONOMICS'
SPRING_SCOPES = (('2025-03', WINTER_END, SPRING_APR), ('2025-04', SPRING_APR, SPRING_MAY),
                 ('2025-05', SPRING_MAY, SPRING_JUN), ('2025-06', SPRING_JUN, SPRING_END))
SPRING_RULES = dict(WINTER_RULES, score_start='2025-03-01', score_end_exclusive='2025-07-01',
    score_months=[r[0] for r in SPRING_SCOPES], new_market_files=96, reused_market_files=24,
    warmup='ACCEPTED_FEB_AUG_1D_PLUS_ACCEPTED_SEP_FEB_1M_CAUSAL_DAILY_REDUCTION')
SPRING_BUDGETS = dict(WINTER_BUDGETS, market_owned_bytes=400_000_000,
    temporary_owned_bytes=200_000_000)
SPRING_WARMUP_MANIFEST = dict(
    path=str(STATE/'d056-multiasset-winter-source-acceptance-20261004-v2/INPUT_MANIFEST.json'),
    sha256='56f1eb1b768e14d4c67198156732c1d4a22e6a901e980c24ebee9f20bbf86193',
    required_status=WINTER_MANIFEST_STATUS)
CONTINUOUS_MANIFEST_STATUS = 'PASS_D055_CONTINUOUS_91D_ACCEPTED_SOURCE_BINDING_NOT_ECONOMICS'
CONTINUOUS_SCOPES = (('2024-09', START, END), ('2024-10', END, OCT_END),
                     ('2024-11', OCT_END, NOV_END))
CONTINUOUS_MANIFEST_REFS = (
    dict(path=str(STATE/'d050-multiasset-source-acceptance-20261004-v2/INPUT_MANIFEST.json'),
         sha256='48ff8dcd72cc247a1c341dffb0d683d1fcedd27ade639fd935dbfdcd8de78f93',
         required_status='PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'),
    dict(path=str(STATE/'d051-multiasset-october-source-acceptance-20261004-v1/INPUT_MANIFEST.json'),
         sha256='cbd4d7517aa914c6de87885f94a38072b0af8c8d08daa3391efe7c3913929fd0',
         required_status='PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'),
    dict(path=str(STATE/'d054-multiasset-november-source-acceptance-20261004-v2/INPUT_MANIFEST.json'),
         sha256='77881c6e61aaf9d23a8e369493bc58e51c5846034e5171b0f0ea1c06d78bc87d',
         required_status=NOVEMBER_MANIFEST_STATUS))
WINTER_WARMUP_MANIFEST = dict(
    path=str(STATE/'d055-continuous-input-binding-20261004-v1/INPUT_MANIFEST.json'),
    sha256='847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50',
    required_status=CONTINUOUS_MANIFEST_STATUS)


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    return data.sha256_file(Path(path))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def owned(run):
    paths = list(Path(run).rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Owned source symlink')
    return sum(p.stat().st_size for p in paths if p.is_file())


def symbol_ok(symbol):
    return isinstance(symbol, str) and re.fullmatch(r'[A-Z0-9]{2,24}USDT', symbol) is not None


def period_scope(start_us, end_us):
    require(type(start_us) is int and type(end_us) is int and
        (start_us, end_us) in ((START, END), (END, OCT_END), (OCT_END, NOV_END),
        *((a, b) for _, a, b in (*WINTER_SCOPES, *SPRING_SCOPES))), 'Explicit complete authorized source month only')
    return {START: '2024-09', END: '2024-10', OCT_END: '2024-11',
            NOV_END: '2024-12', WINTER_JAN: '2025-01', WINTER_FEB: '2025-02',
            WINTER_END: '2025-03', SPRING_APR: '2025-04', SPRING_MAY: '2025-05', SPRING_JUN: '2025-06'}[start_us]


def entry(symbol, kind, interval, month):
    require(symbol_ok(symbol), 'Explicit uppercase USDT historical symbol')
    require((kind == 'klines' and interval in ('1d', '1m')) or
        (kind == 'markPriceKlines' and interval == '1m') or
        (kind == 'fundingRate' and interval is None), 'Required USD-M product')
    require(month in ('2024-01', '2024-02', '2024-03', '2024-04', '2024-05',
        '2024-06', '2024-07', '2024-08', '2024-09', '2024-10', '2024-11',
        '2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06') and not (interval == '1d' and
        month in ('2024-11', '2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06')) and
        (month != '2024-01' or (kind == 'klines' and interval == '1d')),
        'Explicit unlocked source months; no new late-quarter daily source')
    suffix = (f'{symbol}-fundingRate-{month}.zip' if interval is None else
        f'{interval}/{symbol}-{interval}-{month}.zip')
    url = f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{suffix}'
    return dict(symbol=symbol, kind=kind, interval=interval, month=month,
        url=url, checksum_url=url+'.CHECKSUM')


def metadata_bytes(client, url, *, params=None, limit=512_000):
    require(url in (INDEX, BUCKET) or url.startswith(INDEX+'data/futures/um/monthly/'),
        'Only fixed official metadata/archive host')
    if isinstance(client, WindowsMetadataTransport):
        return client.fetch(url, params=params, limit=limit)
    with client.stream('GET', url, params=params) as response:
        if response.status_code in (403, 451, 418, 429):
            raise PermissionError(f'Official HTTP {response.status_code}; stop, no alternate route')
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            require(len(content) <= limit, 'Bounded metadata response')
        return bytes(content)


class WindowsMetadataTransport:
    """Same metadata URLs over the existing default Windows HTTPS stack."""
    def __init__(self, script, run):
        self.script, self.run, self.requests = Path(script).resolve(), run, []
        require(self.script.is_relative_to(ROOT/'.cache') and self.script.is_file(), 'Explicit local metadata script')
        self.script_sha256 = sha(self.script)

    def fetch(self, url, *, params, limit):
        require(url in (INDEX, BUCKET) and limit <= 512_000, 'Metadata only; no price endpoint')
        require(len(self.requests) < 5, 'Index plus at most four folder pages')
        require(resources.status()['ram_current_bytes']+250_000_000 < 5_000_000_000,
            'Shared WSL plus reserved native transport RAM')
        require(sha(self.script) == self.script_sha256, 'Transport bytes unchanged')
        url = url+('?' + urlencode(params) if params else '')
        destination = self.run/('official-index.html' if not params else f'inventory-{len(self.requests)}.xml')
        native_script = subprocess.check_output(['wslpath', '-w', str(self.script)], text=True).strip()
        native_output = subprocess.check_output(['wslpath', '-w', str(destination)], text=True).strip()
        quoted = lambda value: "'"+value.replace("'", "''")+"'"
        expression = ('& ([ScriptBlock]::Create([IO.File]::ReadAllText('+quoted(native_script)+')))'
            +' -Url '+quoted(url)+' -OutputPath '+quoted(native_output))
        command = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
            '-NoProfile', '-NonInteractive', '-Command', expression]
        peak_shared = resources.status()['ram_current_bytes']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace')
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    peak_shared = max(peak_shared, resources.status()['ram_current_bytes'])
            info = json.loads(stdout.strip().lstrip('\ufeff'))
            info.update(native_exit_code=process.returncode, sampled_shared_WSL_peak_bytes=peak_shared,
                combined_conservative_peak_bound_bytes=peak_shared+int(info['WindowsPeakWorkingSet64']),
                combined_memory_scope='SUM_OF_NATIVE_PEAK_AND_SHARED_WSL_SAMPLES_UPPER_BOUND_NOT_SIMULTANEOUS_MEASUREMENT')
            if destination.exists():
                info.update(path=str(destination), sha256=sha(destination), bytes=destination.stat().st_size)
            self.requests.append(info); save(destination.with_suffix(destination.suffix+'.http.json'), info)
            if info.get('http_status') in (403, 451, 418, 429):
                raise PermissionError(f"Official HTTP {info['http_status']}; STOP without another host or retry")
            require(process.returncode == 0 and info['status'] == 'RETRIEVED', str(info.get('reason', 'Official metadata HTTP failure')))
            require(info['WindowsPeakWorkingSet64'] <= 250_000_000 and
                info['combined_conservative_peak_bound_bytes'] <= 5_000_000_000, 'Combined native/WSL RAM bound')
            require(destination.stat().st_size <= limit, 'Fixed metadata byte bound')
            return destination.read_bytes()
        finally:
            if process.poll() is None:
                process.kill(); process.communicate()


def inventory(client, run, budgets=DEFAULT_BUDGETS, progress=None):
    """Only index HTML and paginated S3 folder metadata; no price payload."""
    started = time.monotonic()
    html = metadata_bytes(client, INDEX, limit=128_000)
    require(BUCKET.encode() in html, 'Official index must identify the exact S3 bucket')
    (run/'official-index.html').write_bytes(html)
    symbols, marker, pages = set(), None, []
    for number in range(budgets['inventory_pages']):
        require(time.monotonic()-started < budgets['inventory_wall_seconds'], 'Inventory wall budget')
        params = dict(prefix=PREFIX, delimiter='/', **{'max-keys': '1000'})
        if marker is not None:
            params['marker'] = marker
        body = metadata_bytes(client, BUCKET, params=params, limit=budgets['inventory_page_bytes'])
        path = run/f'inventory-{number+1}.xml'; path.write_bytes(body)
        require(b'<!DOCTYPE' not in body.upper() and b'<!ENTITY' not in body.upper(), 'Plain S3 XML only')
        root = ET.fromstring(body); ns = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
        require(root.tag == '{'+ns['s']+'}ListBucketResult' and
            root.findtext('s:Name', namespaces=ns) == 'data.binance.vision' and
            root.findtext('s:Prefix', namespaces=ns) == PREFIX, 'Exact official listing identity')
        prefixes = [node.findtext('s:Prefix', namespaces=ns) for node in root.findall('s:CommonPrefixes', ns)]
        require(all(p and p.startswith(PREFIX) and p.endswith('/') for p in prefixes), 'Historical folder names')
        for prefix in prefixes:
            symbol = prefix[len(PREFIX):-1]
            if symbol_ok(symbol):
                symbols.add(symbol)
        truncated = root.findtext('s:IsTruncated', namespaces=ns)
        require(truncated in ('true', 'false'), 'Explicit S3 pagination status')
        pages.append(dict(path=str(path), sha256=sha(path), bytes=len(body), prefix_count=len(prefixes)))
        if progress:
            progress.update('历史目录，未读取价格', number+1, None, '页', symbols=len(symbols))
        if truncated == 'false':
            require(len(symbols) <= budgets['max_candidates'], 'Too many candidates; do not truncate into Top10')
            return dict(status='COMPLETE_HISTORICAL_FOLDER_INVENTORY_NOT_POOL_OR_PRICE_ACCEPTANCE',
                symbols=sorted(symbols), pages=pages, full_listing=True,
                price_payloads_read=0, current_exchange_info_used=False)
        next_marker = root.findtext('s:NextMarker', namespaces=ns)
        require(next_marker and (marker is None or next_marker > marker), 'Strictly advancing S3 marker')
        marker = next_marker
    raise RuntimeError('Inventory page bound reached; full historical universe UNKNOWN')


def official_downloader():
    require(sha(ROOT/COMPONENT) == COMPONENT_SHA, 'Pinned official staging receipt')
    receipt = json.loads((ROOT/COMPONENT).read_bytes())
    require(receipt['status'] == 'PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGED_NO_MARKET_DATA',
        'Actual official component stage')
    return formats.official_module(receipt)


class WindowsSourceTransport:
    """Two bounded official GETs per archive, then unchanged WSL parsers."""
    def __init__(self, script, run):
        self.script, self.run = Path(script).resolve(), run
        require(self.script == (ROOT/'scripts/investment/multi_asset_official_transport.ps1').resolve()
            and self.script.is_file(), 'Exact normal official-source transport path')
        self.script_sha256 = sha(self.script)
        self.requests = 0; self.http_status_counts = {}; self.native_peak = 0; self.combined_peak = 0

    def download(self, url, destination, maximum):
        require(sha(self.script) == self.script_sha256 and destination.resolve().is_relative_to(self.run), 'Frozen transport/own destination')
        require(resources.status()['ram_current_bytes']+250_000_000 < 5_000_000_000, 'WSL plus native transport RAM')
        native_script = subprocess.check_output(['wslpath', '-w', str(self.script)], text=True).strip()
        native_output = subprocess.check_output(['wslpath', '-w', str(destination)], text=True).strip()
        quoted = lambda value: "'"+value.replace("'", "''")+"'"
        expression = ('& ([ScriptBlock]::Create([IO.File]::ReadAllText('+quoted(native_script)+')))'
            +' -Url '+quoted(url)+' -OutputPath '+quoted(native_output)+' -MaximumBytes '+str(maximum))
        process = subprocess.Popen(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
            '-NoProfile', '-NonInteractive', '-Command', expression], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        peak_shared = resources.status()['ram_current_bytes']
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=1); break
                except subprocess.TimeoutExpired:
                    peak_shared = max(peak_shared, resources.status()['ram_current_bytes'])
            info = json.loads(stdout.strip().lstrip('\ufeff'))
            info.update(native_exit_code=process.returncode, sampled_shared_WSL_peak_bytes=peak_shared,
                combined_conservative_peak_bound_bytes=peak_shared+int(info['WindowsPeakWorkingSet64']),
                memory_scope='SEPARATE_PEAKS_SUM_IS_CONSERVATIVE_BOUND_NOT_SIMULTANEOUS_MEASUREMENT')
            if destination.exists():
                info.update(path=str(destination), sha256=sha(destination), bytes=destination.stat().st_size)
            save(destination.with_suffix(destination.suffix+'.http.json'), info)
            self.requests += 1
            status = str(info.get('http_status', 'UNKNOWN'))
            self.http_status_counts[status] = self.http_status_counts.get(status, 0)+1
            self.native_peak = max(self.native_peak, int(info['WindowsPeakWorkingSet64']))
            self.combined_peak = max(self.combined_peak, info['combined_conservative_peak_bound_bytes'])
            if info.get('http_status') in (403, 451, 418, 429):
                raise PermissionError(f"Official HTTP {info['http_status']}; STOP no alternate route/retry")
            if info.get('http_status') == 404:
                raise FileNotFoundError('OFFICIAL_HTTP404_NO_ARCHIVE; historical listing/publication UNKNOWN')
            require(process.returncode == 0 and info['status'] == 'RETRIEVED', str(info.get('reason', 'Official source HTTP failure')))
            require(self.native_peak <= 250_000_000 and self.combined_peak <= 5_000_000_000, 'Combined native/WSL memory bound')
            require(0 < destination.stat().st_size <= maximum, 'Fixed delivered file bound')
            return info
        finally:
            if process.poll() is None:
                process.kill(); process.communicate()


@contextlib.contextmanager
def deadline(seconds):
    require(seconds > 0, 'Positive remaining source wall budget')
    prior = signal.getsignal(signal.SIGALRM); prior_timer = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    def expired(_signal, _frame):
        raise TimeoutError('Fixed source deadline; partial bytes preserved, no retry')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, min(seconds, prior_timer[0]) if prior_timer[0] else seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, prior)
        if prior_timer[0]:
            remaining = prior_timer[0]-(time.monotonic()-started)
            require(remaining > 0, 'Outer source deadline expired; do not reset it per file')
            signal.setitimer(signal.ITIMER_REAL, remaining, prior_timer[1])


def acquire(item, run, client, *, authorization, reuse_catalog=None, budgets=DEFAULT_BUDGETS):
    """One explicit archive via unchanged official utility.download_file.

    POOL_DAILY reads February-August only. A selected-source phase requires
    a frozen pool and its exact score month/symbols in the caller protocol.
    """
    require(item == entry(item['symbol'], item['kind'], item['interval'], item['month']), 'Canonical entry')
    phase = authorization['phase']
    require(authorization.get('ready_for_execution') is True and
        authorization.get('capacity_registered') is True, 'Root registered source and capacity first')
    if phase == 'POOL_DAILY':
        require(item['kind'] == 'klines' and item['interval'] == '1d' and item['month'] in
            ('2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08'),
            'Pool phase only pre-score daily sources')
    else:
        proof = authorization['pool_receipt']
        pool_path = Path(proof['path']).resolve()
        require(pool_path.is_relative_to(ROOT) and pool_path.stat().st_size <= 2_000_000 and
            sha(pool_path) == proof['sha256'], 'Actual frozen selected-pool receipt')
        selected_pool = json.loads(pool_path.read_bytes())
        require(selected_pool['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and
            len(selected_pool['symbols']) == 10 and authorization['symbols'] ==
            sorted(set(selected_pool['symbols']) | {'BTCUSDT', 'ETHUSDT'}), 'Selected symbols and controls match pool')
        if phase == 'WARMUP_DAILY':
            require(item['month'] == '2024-01' and item['kind'] == 'klines' and
                item['interval'] == '1d' and item['symbol'] in authorization['symbols'] and
                proof['sha256'] == authorization['pool_receipt_sha256'],
                'Only same selected July pool January daily indicator warmup')
        else:
            month = {'SEPTEMBER_SOURCE': '2024-09', 'OCTOBER_SOURCE': '2024-10',
                 'NOVEMBER_SOURCE': '2024-11'}.get(phase)
            authorized_months = (tuple(r[0] for r in SPRING_SCOPES) if phase == 'SPRING_SOURCE' else
                tuple(r[0] for r in WINTER_SCOPES) if phase == 'WINTER_SOURCE' else (month,))
            require(None not in authorized_months and item['month'] in authorized_months and
                item['interval'] != '1d' and item['symbol'] in authorization['symbols'] and
                proof['sha256'] == authorization['pool_receipt_sha256'], 'Frozen July pool bound before explicit score-month IO')
    key = (item['kind'], item['symbol'], item['interval'], item['month'])
    if reuse_catalog and key in reuse_catalog:
        old = dict(reuse_catalog[key]); p = Path(old['normalized_path'])
        require(p.resolve().is_relative_to(STATE.resolve()) and not p.is_symlink() and
            p.stat().st_size == old['normalized_bytes'] and sha(p) == old['normalized_sha256'], 'Exact previously written source')
        scope = ('REUSED_FAILED_STAGE_COMPLETED_ROW_PENDING_INDEPENDENT_QA' if old.get('partial_source_proof')
                 else 'REUSED_ACCEPTED_BYTES_NO_REPEAT_QA_OR_DOWNLOAD')
        return dict(old, acquisition=scope)
    limit = budgets['daily_zip_bytes'] if item['interval'] == '1d' else budgets['market_zip_bytes']
    name = item['url'].rsplit('/', 1)[1]
    job = run/(item['kind']+'-'+item['symbol']+'-'+str(item['interval'] or 'events')+'-'+item['month'])
    job.mkdir(exist_ok=False)
    if isinstance(client, WindowsSourceTransport):
        archive, checksum = job/name, job/(name+'.CHECKSUM')
        saved = authorization.get('saved_archive_reuse', {}).get(item['url'])
        if saved:
            require(phase == 'SPRING_SOURCE', 'Saved archive recovery only in explicit spring scope')
            for target, label, maximum in ((archive, 'zip', limit), (checksum, 'checksum', 4096)):
                original = Path(saved[label+'_path'])
                require(original.is_file() and not original.is_symlink() and
                    original.resolve().is_relative_to(STATE.resolve()) and
                    0 < original.stat().st_size <= maximum and sha(original) == saved[label+'_sha256'],
                    'Exact retained official archive recovery')
                with original.open('rb') as source, target.open('xb') as destination:
                    import shutil
                    shutil.copyfileobj(source, destination, 1024*1024)
            check = checksum.read_text(encoding='ascii').split()
            require(len(check) == 2 and check[1].lstrip('*') == name and
                re.fullmatch('[0-9a-fA-F]{64}', check[0]), 'Retained official CHECKSUM identity')
        else:
            with deadline(budgets['source_file_seconds']):
                client.download(item['checksum_url'], checksum, 4096)
                check = checksum.read_text(encoding='ascii').split()
                require(len(check) == 2 and re.fullmatch('[0-9a-fA-F]{64}', check[0]) and
                    check[1].lstrip('*') == name, 'Official exact CHECKSUM identity before ZIP')
                client.download(item['url'], archive, limit)
    else:
        with client.stream('HEAD', item['url']) as response:
            if response.status_code in (403, 451, 418, 429):
                raise PermissionError(f'Official HTTP {response.status_code}; stop')
            response.raise_for_status(); length = response.headers.get('content-length')
            require(length and length.isascii() and length.isdecimal() and 0 < int(length) <= limit, 'Announced bounded ZIP')
        check = metadata_bytes(client, item['checksum_url'], limit=4096).decode('ascii').split()
        require(len(check) == 2 and re.fullmatch('[0-9a-fA-F]{64}', check[0]) and
            check[1].lstrip('*') == name, 'Official exact CHECKSUM identity')
        upstream = official_downloader(); relative = item['url'].removeprefix(INDEX)
        base = relative.rsplit('/', 1)[0]+'/'
        with deadline(budgets['source_file_seconds']):
            prior = resource.getrlimit(resource.RLIMIT_FSIZE); handler = signal.getsignal(signal.SIGXFSZ)
            def too_large(_signal, _frame):
                raise RuntimeError('Official archive crossed file bound; partial bytes retained')
            signal.signal(signal.SIGXFSZ, too_large); resource.setrlimit(resource.RLIMIT_FSIZE, (limit, prior[1]))
            try:
                upstream.download_file(base, name+'.CHECKSUM', folder=str(job))
                upstream.download_file(base, name, folder=str(job))
            finally:
                resource.setrlimit(resource.RLIMIT_FSIZE, prior); signal.signal(signal.SIGXFSZ, handler)
        archive = job/relative; checksum = archive.with_name(name+'.CHECKSUM')
        require(archive.stat().st_size == int(length), 'Announced official bytes')
    require(archive.is_file() and checksum.is_file() and sha(archive) == check[0].lower() and
        checksum.read_text().split() == check, 'Delivered official bytes/checksum')
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        csv_limit = budgets['daily_csv_bytes'] if item['interval'] == '1d' else budgets['market_csv_bytes']
        require(len(members) == 1 and members[0].filename == name[:-4]+'.csv' and
            not members[0].flag_bits & 1 and 0 < members[0].file_size <= csv_limit, 'Single bounded official CSV')
        require(zipped.testzip() is None, 'Full archive CRC')
    normalized = job/'source.parquet'
    if item['kind'] == 'klines':
        # These are the existing accepted 1m and 1d format parsers, not a new
        # parser or a new AST transformation. February may begin after listing.
        _, parsers, _ = trade.adapted_functions()
        with zipfile.ZipFile(archive) as zipped:
            raw = zipped.read(members[0])
        first = raw.split(b'\n', 1)[0].decode('utf-8-sig').rstrip('\r')
        require(list(next(csv.reader([first]))) == trade.HEADER, 'Actual USD-M trade header')
        frame, quality = parsers[item['interval']](raw.split(b'\n', 1)[1], item['symbol'])
        require(quality['timestamp_unit'] == 'milliseconds' and sum(frame.null_count().row(0)) == 0 and
            all(quality[k] == 0 for k in ('duplicate_rows', 'bad_timestamps', 'bad_values', 'gaps')) and
            not quality['incomplete_days'] and not quality['nonstandard_closes'], 'Existing parser full row guards')
        start, end = formats.month_range(item['month']); step = DAY if item['interval'] == '1d' else MINUTE
        opens = frame['open_us'].to_numpy()
        require(len(opens) > 0 and np.all(opens >= start*1000) and np.all(opens < end*1000), 'Fixed archive month')
        if not (item['interval'] == '1d' and item['month'] in ('2024-01', '2024-02')):
            require(np.array_equal(opens, np.arange(start*1000, end*1000, step, dtype=np.int64)), 'Complete fixed month, no fill/drop')
        frame.write_parquet(normalized, compression='zstd'); rows = frame.height
        quality.update(market='USD_M_TRADE_KLINES', interval=item['interval'],
            availability='EXCLUSIVE_CLOSED_BAR_PROXY_NOT_PUBLICATION_CERTIFICATE',
            first_open_us=int(opens[0]), last_open_us=int(opens[-1]), no_fill_or_drop=True)
    else:
        format_spec = json.loads((ROOT/'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json').read_bytes())
        quality = formats.convert_source(archive, item, format_spec, normalized); rows = quality['rows']
    result = dict(item, normalized_path=str(normalized), normalized_sha256=sha(normalized),
        normalized_bytes=normalized.stat().st_size, rows=rows, quality=quality,
        zip_path=str(archive), zip_sha256=sha(archive), checksum_path=str(checksum), checksum_sha256=sha(checksum),
        acquisition='NEW_OFFICIAL_BYTES_FORMAT_QA_PENDING_INDEPENDENT_ACCEPTANCE',
        native_Bybit_certified=False, funding_unit_certified=False)
    receipt = job/'receipt.json'; save(receipt, result)
    result.update(receipt_path=str(receipt), receipt_sha256=sha(receipt))
    require(owned(run) <= budgets['pool_owned_bytes' if phase == 'POOL_DAILY' else 'market_owned_bytes'], 'Owned source byte budget')
    return result


def reuse_catalog(manifest):
    require(manifest['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS', 'Accepted existing BTCETH source metadata')
    result = {}
    for value in manifest['source_files'].values():
        key = (value['kind'], value['symbol'], value.get('interval'), value['month'])
        require(key not in result, 'Distinct existing source identities'); result[key] = value
    return result


def daily_frame(records):
    frames = []
    for item in records:
        require(item['kind'] == 'klines' and item['interval'] == '1d' and item['month'] in
            ('2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08'), 'Pre-pool daily prices only')
        path = Path(item['normalized_path'])
        require(sha(path) == item['normalized_sha256'], 'Exact bound daily bytes')
        # Ingestion metadata can be an Int32 zero UNKNOWN in new archives;
        # widen only this column for concatenation with accepted Int64 metadata.
        frames.append(pl.read_parquet(path).with_columns(pl.col('ingested_us').cast(pl.Int64)))
    require(frames, 'Actual daily records')
    result = pl.concat(frames).sort(['symbol', 'open_us'])
    require(result.select(pl.struct('symbol', 'open_us').n_unique()).item() == result.height, 'Unique daily identity')
    return result


def qualify_daily(symbol, daily, *, start_us=START):
    """Pure eligibility using only real daily bars completed by entry."""
    require(type(start_us) is int and start_us in (START, END, OCT_END, NOV_END, WINTER_END), 'Explicit entry boundary')
    require(symbol_ok(symbol) and daily['symbol'].unique().to_list() == [symbol], 'One candidate')
    one = daily.sort('open_us')
    require(one.null_count().select(pl.sum_horizontal(pl.all())).item() == 0, 'Unknown daily values')
    require(one['open_us'].max() < start_us and one['close_us'].eq(one['open_us']+DAY).all()
        and one['available_us'].eq(one['close_us']).all(), 'No score prices in qualification')
    warm = one.filter(pl.col('open_us') >= start_us-200*DAY)
    complete = np.array_equal(warm['open_us'].to_numpy(), np.arange(start_us-200*DAY, start_us, DAY, dtype=np.int64))
    oldest = int(one['open_us'].min()); age = (start_us-oldest)//DAY
    if age < 200 or not complete:
        return dict(status='INELIGIBLE_WARMUP_OR_OBSERVED_AGE', observed_age_days=age,
            full_200_completed_daily_warmup=complete, reason='No imputation or intersection calendar')
    values = warm['close'].tail(32).to_numpy()
    require(np.isfinite(values).all() and np.all(values > 0), 'Past31 returns finite actual prices')
    return dict(status='ELIGIBLE_PRE_SCORE_ONLY', observed_age_days=age,
        earliest_observed_open_us=oldest, warmup_start_us=start_us-200*DAY,
        warmup_rows=200, past31_returns=(np.diff(values)/values[:-1]).tolist(),
        latest_observed_close_us=int(warm['close_us'][-1]), publication_proxy=True)


def select_pool(symbols, fetch_daily, *, exclusions=None, budgets=DEFAULT_BUDGETS, progress=None):
    """July rank first; fetch_daily(symbol, month) must be POOL_DAILY only.

    All attempted candidates, failures and eligibility states are retained.
    UNKNOWN candidates with unknown rank or rank above cutoff prevent an
    all-market Top10 claim. A finite provided universe is always labelled.
    """
    require(len(symbols) == len(set(symbols)) and len(symbols) <= budgets['max_candidates'] and
        all(symbol_ok(s) for s in symbols), 'Explicit historical candidate universe')
    exclusions = exclusions or {}; ranks = []; unknown = []; notes = []; records = {}
    for index, symbol in enumerate(sorted(symbols)):
        if symbol in exclusions:
            notes.append(dict(symbol=symbol, status='EXPLICIT_PREDECLARED_EXCLUSION', reason=exclusions[symbol])); continue
        try:
            item = fetch_daily(symbol, '2024-07'); records[(symbol, '2024-07')] = item
            one = daily_frame([item])
            require(np.array_equal(one['open_us'].to_numpy(), np.arange(START-62*DAY, START-31*DAY, DAY)), 'Full July ranking month')
            amount = math.fsum(one['quote_volume'].to_list())
            require(math.isfinite(amount) and amount >= 0, 'July USDT trade amount')
            ranks.append(dict(symbol=symbol, july_quote_volume_USDT=amount))
        except PermissionError:
            raise
        except Exception as error:
            unknown.append(dict(symbol=symbol, phase='JULY_RANK', status='UNKNOWN', reason=f'{type(error).__name__}: {error}'))
        if progress:
            progress.update('仅July历史流动性排名', index+1, len(symbols), '候选')
    ranks.sort(key=lambda r: (-r['july_quote_volume_USDT'], r['symbol']))
    selected = []; cutoff = None
    for index, candidate in enumerate(ranks):
        if index >= budgets['max_qualification_candidates']:
            break
        symbol = candidate['symbol']
        try:
            items = []
            for month in ('2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08'):
                item = records.get((symbol, month)) or fetch_daily(symbol, month)
                records[(symbol, month)] = item; items.append(item)
            eligibility = qualify_daily(symbol, daily_frame(items))
        except PermissionError:
            raise
        except Exception as error:
            eligibility = dict(status='UNKNOWN', reason=f'{type(error).__name__}: {error}')
            unknown.append(dict(symbol=symbol, phase='QUALIFICATION', **eligibility))
        notes.append(dict(candidate, historical_rank=index+1, eligibility=eligibility))
        if eligibility['status'] == 'ELIGIBLE_PRE_SCORE_ONLY':
            selected.append(symbol)
        if progress:
            progress.update('过去200日资格，未读September', index+1, None, '候选', eligible=len(selected))
        if len(selected) == RULES['desired_assets']:
            cutoff = index+1; break
    complete = len(selected) == 10 and not unknown
    return dict(status='POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' if len(selected) == 10 else 'POOL_NOT_READY',
        rules=RULES, symbols=selected, july_ranked_candidates=ranks, eligibility_checks=notes,
        unknown_candidates=unknown, selection_complete_within_supplied_universe=complete,
        full_historical_universe_certified=False, cutoff_historical_rank=cutoff,
        score_payloads_read=0, source_records=list(records.values()),
        source_format_acceptance_separate=True, candidate_status='NO_QUALIFIED_CANDIDATE')


def daily_from_minutes(item, start_us, end_us):
    """Small closed-day reduction of an already accepted exact minute source."""
    month = period_scope(start_us, end_us)
    require(item['kind'] == 'klines' and item['interval'] == '1m' and item['month'] == month,
        'Exact accepted trade-minute reduction month')
    path = Path(item['normalized_path'])
    require(path.resolve().is_relative_to(STATE.resolve()) and not path.is_symlink() and
        path.stat().st_size == item['normalized_bytes'] and sha(path) == item['normalized_sha256'], 'Accepted reduction bytes')
    one = pl.scan_parquet(path).sort('open_us').with_columns(
        (pl.col('open_us')//DAY*DAY).alias('day')).group_by('day').agg(
            pl.col('open').first(), pl.col('high').max(), pl.col('low').min(), pl.col('close').last(),
            pl.col('volume').sum(), pl.col('quote_volume').sum(), pl.len().alias('minute_rows'),
            pl.col('open_us').first().alias('first_open'), pl.col('open_us').last().alias('last_open'),
            pl.col('available_us').max().alias('last_available')).sort('day').collect(engine='streaming')
    require(np.array_equal(one['day'].to_numpy(), np.arange(start_us, end_us, DAY)) and
        one['minute_rows'].eq(1440).all() and one['first_open'].eq(one['day']).all() and
        one['last_open'].eq(one['day']+DAY-MINUTE).all() and
        one['last_available'].eq(one['day']+DAY).all(), 'Complete causal accepted minute-to-day reduction')
    return one.select('open', 'high', 'low', 'close', 'volume', 'quote_volume').with_columns(
        pl.Series('open_us', one['day']), pl.Series('close_us', one['day']+DAY),
        pl.Series('available_us', one['day']+DAY), pl.lit(item['symbol']).alias('symbol'), pl.lit('1d').alias('interval'))


def window(pool, market_records, *, pool_receipt_sha256, control_daily_records=(), requested_symbols=None,
           warmup_minute_records=(), start_us=START, end_us=END):
    """Metadata first; each call to minute_blocks yields one complete UTC day."""
    require(type(start_us) is int and type(end_us) is int, 'Explicit integer scoring boundaries')
    continuous = (start_us, end_us) == (START, NOV_END)
    winter = (start_us, end_us) == (NOV_END, WINTER_END)
    spring = (start_us, end_us) == (WINTER_END, SPRING_END)
    scopes = SPRING_SCOPES if spring else WINTER_SCOPES if winter else CONTINUOUS_SCOPES if continuous else (
        (period_scope(start_us, end_us), start_us, end_us),)
    months = tuple(r[0] for r in scopes)
    month = months[0]
    require(pool is None or (pool['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and
        len(pool['symbols']) == 10 and bool(pool_receipt_sha256)), 'Actual selected pool binding')
    selected = pool['symbols'] if pool is not None else ['BTCUSDT', 'ETHUSDT']
    all_symbols = sorted(set(selected) | {'BTCUSDT', 'ETHUSDT'})
    symbols = all_symbols if requested_symbols is None else list(requested_symbols)
    require(symbols and len(symbols) == len(set(symbols)) and set(symbols) in
        (set(selected), {'BTCUSDT', 'ETHUSDT'}, set(all_symbols)), 'Frozen pool or original control only')
    table = {(r['kind'], r['symbol'], r['month']): r for r in market_records}
    require(len(table) == len(market_records) and set(table) ==
        {(k, s, m) for k in ('klines', 'markPriceKlines', 'fundingRate')
        for s in all_symbols for m in months}, 'Selected assets and controls, three real roles per authorized month')
    for item in market_records:
        require(item['month'] in months and item.get('interval') == (None if item['kind'] == 'fundingRate' else '1m'), 'Only explicit score-month source roles')
        p = Path(item['normalized_path']); resolved = p.resolve()
        require(resolved.is_relative_to(STATE.resolve()) and not p.is_symlink() and
            p.stat().st_size == item['normalized_bytes'] and sha(p) == item['normalized_sha256'], 'Exact selected market bytes')
    daily_records = {(r['symbol'], r['month']): r for r in
        [*(pool['source_records'] if pool is not None else []), *control_daily_records] if r['symbol'] in symbols}
    daily = daily_frame(list(daily_records.values()))
    if winter or spring:
        warm_scopes = (*CONTINUOUS_SCOPES, *WINTER_SCOPES) if spring else CONTINUOUS_SCOPES
        warm_table = {(r['symbol'], r['month']): r for r in warmup_minute_records}
        require(len(warm_table) == len(warmup_minute_records) and set(warm_table) ==
            {(s, m) for s in all_symbols for m, _, _ in warm_scopes},
            'Every already accepted trade-minute warmup month per pool/control asset')
        reductions = [daily_from_minutes(warm_table[(s, m)], a, b)
            for m, a, b in warm_scopes for s in symbols]
        daily = pl.concat([daily.select(reductions[0].columns), *reductions]).sort(['symbol', 'open_us'])
    elif month == '2024-10':
        warm_table = {r['symbol']: r for r in warmup_minute_records}
        require(len(warm_table) == len(warmup_minute_records) and set(warm_table) == set(all_symbols),
            'One accepted September trade source per pool/control asset')
        september = [daily_from_minutes(warm_table[s], START, END) for s in symbols]
        daily = pl.concat([daily.select(september[0].columns), *september]).sort(['symbol', 'open_us'])
    elif month == '2024-11':
        warm_table = {(r['symbol'], r['month']): r for r in warmup_minute_records}
        require(len(warm_table) == len(warmup_minute_records) and set(warm_table) ==
            {(s, m) for s in all_symbols for m in ('2024-09', '2024-10')},
            'Two already accepted trade-minute months per pool/control asset')
        reductions = [daily_from_minutes(warm_table[(s, m)], a, b)
            for m, a, b in (('2024-09', START, END), ('2024-10', END, OCT_END)) for s in symbols]
        daily = pl.concat([daily.select(reductions[0].columns), *reductions]).sort(['symbol', 'open_us'])
    else:
        require(not warmup_minute_records, 'No extra warmup price scope for September')
    for symbol in symbols:
        require(qualify_daily(symbol, daily.filter(pl.col('symbol') == symbol), start_us=start_us)['status'] ==
            'ELIGIBLE_PRE_SCORE_ONLY', 'Selected/control warmup remains complete')
    # Score minutes are reduced only after selection/acceptance, never ranked.
    score_daily = [daily_from_minutes(table[('klines', s, m)], a, b)
                   for m, a, b in scopes for s in symbols]
    daily = pl.concat([daily.select(score_daily[0].columns), *score_daily]).sort(['symbol', 'open_us'])
    events = []
    for m, a, b in scopes:
        for symbol in symbols:
            item = table[('fundingRate', symbol, m)]; rates = pl.read_parquet(item['normalized_path'])
            for row in rates.iter_rows(named=True):
                event = int(row['calc_time_ms'])*1000; rate = float(row['last_funding_rate'])
                require(a <= event < b and math.isfinite(rate), 'Actual event, no forward filling')
                events.append(dict(symbol=symbol, event_us=event, raw_rate=rate,
                    reported_interval_hours=float(row['funding_interval_hours'])))
    events.sort(key=lambda r: (r['event_us'], r['symbol']))
    require(len(events) == len({(r['symbol'], r['event_us']) for r in events}), 'Funding identity exactly once')
    def minute_blocks():
        for day in range(start_us, end_us, DAY):
            times = np.arange(day, day+DAY, MINUTE, dtype=np.int64); market = {}
            source_month = next(m for m, a, b in scopes if a <= day < b)
            for symbol in symbols:
                t = pl.scan_parquet(table[('klines', symbol, source_month)]['normalized_path']).filter(
                    (pl.col('open_us') >= day) & (pl.col('open_us') < day+DAY)).sort('open_us').collect(engine='streaming')
                m = pl.scan_parquet(table[('markPriceKlines', symbol, source_month)]['normalized_path']).filter(
                    (pl.col('timestamp_ms')*1000 >= day) & (pl.col('timestamp_ms')*1000 < day+DAY)).sort('timestamp_ms').collect(engine='streaming')
                require(np.array_equal(t['open_us'].to_numpy(), times) and
                    np.array_equal(m['timestamp_ms'].to_numpy()*1000, times), 'Complete independent asset day; never inner-join away gaps')
                values = t.select('open', 'close', 'quote_volume').to_numpy(); marks = m['close'].to_numpy()
                require(np.isfinite(values).all() and np.all(values[:, :2] > 0) and np.all(values[:, 2] >= 0)
                    and np.isfinite(marks).all() and np.all(marks > 0), 'Finite observed day, no zero prices')
                market[symbol] = dict(open=values[:, 0], close=values[:, 1], quote_volume=values[:, 2], mark=marks)
            yield dict(times=times, market=market)
    return dict(start=start_us, end=end_us, symbols=symbols, selected_symbols=list(selected),
        control_symbols=['BTCUSDT', 'ETHUSDT'], daily=daily, events=events,
        input_proofs=[*market_records, *warmup_minute_records], pool_receipt_sha256=pool_receipt_sha256, minute_blocks=minute_blocks,
        boundary='CALLER_CARRIES_LAST_REAL_QUOTE_AND_MARK_ACROSS_DAY_BLOCKS_NO_RESET',
        missing='FAIL_DAY_WITH_REASON_NEVER_REPLACE_SELECTED_ASSET_USING_SCORE_RESULT')


def small_proof(proof, required_status=None):
    path = Path(proof['path']); path = path if path.is_absolute() else ROOT/path
    require(path.resolve().is_relative_to(ROOT) or path.resolve().is_relative_to(STATE.resolve()), 'Bound metadata location')
    require(path.stat().st_size <= 2_000_000 and sha(path) == proof['sha256'], 'Exact small source/pool proof')
    value = json.loads(path.read_bytes())
    status = required_status or proof.get('required_status')
    require(status is not None and value['status'] == status, 'Explicit accepted metadata status')
    return value


def extend_daily_warmup(window, proof, symbols):
    """Add separately accepted January bars for indicators, not pool selection.

    Existing scoring manifest, prices, funding, execution blocks and dates stay
    identical. Every extension record has an actual closed source acceptance.
    No decision becomes eligible without its own contiguous available warmup.
    """
    accepted = small_proof(proof, 'PASS_D058_JANUARY_DAILY_WARMUP_SOURCE_FORMAT_ONLY')
    require(accepted['source_only'] is True and accepted['actual_exit_code'] == 0 and
        accepted['pool_receipt']['sha256'] == window['pool_receipt_sha256'] and
        set(accepted['symbols']) == set(symbols), 'Same selected pool, warmup only')
    task_id = accepted['binding']['task_id']
    require(re.fullmatch('[a-f0-9]{32}', task_id) is not None, 'Real acceptance task')
    task = json.loads((STATE/'task-progress'/f'task-{task_id}.json').read_bytes())
    require(task['id'] == task_id and task['status'] == 'completed' and task['exit_code'] == 0,
        'Independent warm source task actually completed before simulation')
    records = accepted['sources']
    require(len(records) == len(symbols) and {r['symbol'] for r in records} == set(symbols),
        'One exact January source per configured asset')
    frames = []
    for row in records:
        require(row['kind'] == 'klines' and row['interval'] == '1d' and row['month'] == '2024-01',
            'Only January daily indicator context, no new scoring source')
        p = Path(row['normalized_path'])
        require(p.resolve().is_relative_to(STATE.resolve()) and not p.is_symlink() and
            p.stat().st_size == row['normalized_bytes'] and sha(p) == row['normalized_sha256'] and
            accepted['normalized_source_hashes'][str(p)] == row['normalized_sha256'],
            'Exact independently accepted new/reused warm bytes')
        frame = pl.read_parquet(p).select(window['daily'].columns)
        require(0 < frame.height <= 31 and frame['symbol'].unique().to_list() == [row['symbol']] and
            frame['available_us'].max() <= window['start'], 'Complete pre-score January only')
        frames.append(frame)
    daily = pl.concat([*frames, window['daily']]).sort(['symbol', 'open_us'])
    require(daily.select(pl.struct('symbol', 'open_us').n_unique()).item() == daily.height,
        'No duplicated warm/scoring identity')
    window.update(daily=daily, daily_warmup_extension=proof,
        input_proofs=[*window['input_proofs'], *records])
    return window


def november_warmup_metadata(proofs, pool):
    """Reuse Oct10 and its accepted Sep10/daily70 chain; no payload QA here."""
    prior = small_proof(proofs['warmup_source_acceptance'], 'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY')
    manifest = small_proof(proofs['warmup_manifest'], 'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS')
    pool_sha = proofs['pool_receipt']['sha256']
    require(prior['source_only'] is True and prior['pool_receipt_sha256'] == pool_sha and
        manifest['pool_receipt']['sha256'] == pool_sha and
        manifest['source_acceptance']['sha256'] == proofs['warmup_source_acceptance']['sha256'] and
        (manifest['start_us'], manifest['end_us']) == (END, OCT_END) and
        (prior['start_us'], prior['end_us']) == (END, OCT_END) and
        (ROOT/Path(manifest['source_acceptance']['path'])).resolve() ==
        (ROOT/Path(proofs['warmup_source_acceptance']['path'])).resolve(),
        'Same accepted July pool/October warmup metadata')
    base = small_proof(manifest['warmup_source_acceptance'], 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY')
    base_manifest = small_proof(manifest['warmup_manifest'], 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS')
    require(base['source_only'] is True and base['pool_receipt_sha256'] == pool_sha and
        base_manifest['pool_receipt']['sha256'] == pool_sha and
        base_manifest['source_acceptance']['sha256'] == manifest['warmup_source_acceptance']['sha256'] and
        prior['prior_acceptance']['sha256'] == manifest['warmup_source_acceptance']['sha256'] and
        prior['prior_manifest']['sha256'] == manifest['warmup_manifest']['sha256'] and
        (ROOT/Path(prior['prior_acceptance']['path'])).resolve() ==
        (ROOT/Path(manifest['warmup_source_acceptance']['path'])).resolve() and
        (ROOT/Path(prior['prior_manifest']['path'])).resolve() ==
        (ROOT/Path(manifest['warmup_manifest']['path'])).resolve() and
        (base_manifest['start_us'], base_manifest['end_us']) == (START, END),
        'Original accepted September and February-August proof chain remains explicit')
    identity = lambda r: (r['symbol'], r['kind'], r['interval'], r['month'], r['normalized_path'],
                          r['normalized_sha256'], r['normalized_bytes'], r['rows'])
    september = manifest['warmup_minute_records']
    expected = [r for r in base_manifest['market_records'] if r['kind'] == 'klines']
    require(sorted(map(identity, september)) == sorted(map(identity, expected)), 'Exact accepted September ten identities')
    october = [r for r in manifest['market_records'] if r['kind'] == 'klines']
    members = set(pool['symbols']) | {'BTCUSDT', 'ETHUSDT'}
    for month, records, pins in (('2024-09', september, base['normalized_source_hashes']),
                                 ('2024-10', october, prior['normalized_source_hashes'])):
        require(len(records) == len(members) and {r['symbol'] for r in records} == members and
            all(r['kind'] == 'klines' and r['interval'] == '1m' and r['month'] == month and
                pins.get(r['normalized_path']) == r['normalized_sha256'] for r in records),
            'Each accepted warmup month retains source identity and byte SHA')
    daily = [*manifest['control_daily_records'],
        *(r for r in pool['source_records'] if r['symbol'] in members)]
    require({(r['symbol'], r['month']) for r in daily} ==
        {(s, '2024-'+m) for s in members for m in ('02', '03', '04', '05', '06', '07', '08')} and
        all(r['kind'] == 'klines' and r['interval'] == '1d' and
            base['normalized_source_hashes'].get(r['normalized_path']) == r['normalized_sha256']
            for r in daily), 'Selected daily70 warmup remains bound to original acceptance; not new QA')
    return [*september, *october], base['normalized_source_hashes']


def compose_continuous_manifest(monthly_manifest_proofs):
    """Bind three accepted calendars using small metadata, without source QA.

    The three original manifest/acceptance files remain unchanged. Their source
    descriptors are retained; normalized byte SHA values are prior capabilities,
    not a claim that this composition reread prices, rows, archives or CRCs.
    """
    require(isinstance(monthly_manifest_proofs, (tuple, list)) and
        len(monthly_manifest_proofs) == 3, 'Exactly three ordered accepted months')
    same = lambda a, b: ((ROOT/Path(a['path'])).resolve(), a['sha256']) == (
        (ROOT/Path(b['path'])).resolve(), b['sha256'])
    identity = lambda r: tuple(r[k] for k in ('symbol', 'kind', 'interval', 'month',
        'normalized_path', 'normalized_sha256', 'normalized_bytes', 'rows'))
    statuses = ('PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY',
        'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY',
        'PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY')
    manifests, acceptances, tasks, market = [], [], [], []
    pins = {}; pool = None; pool_ref = None; source_symbols = None
    for ref, expected, scope, status in zip(monthly_manifest_proofs,
            CONTINUOUS_MANIFEST_REFS, CONTINUOUS_SCOPES, statuses, strict=True):
        require(same(ref, expected), 'Exact accepted month and original manifest SHA/order')
        manifest = small_proof(ref, expected['required_status'])
        month, first, last = scope
        require(manifest['checksummed_source_format_verified'] is True and
            (manifest['start_us'], manifest['end_us']) == (first, last), 'Complete accepted calendar metadata')
        current_pool = small_proof(manifest['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
        acceptance_ref = manifest['source_acceptance']
        cap = small_proof(acceptance_ref, status)
        require(cap['source_only'] is True and cap['actual_exit_code'] == 0 and
            cap['symbols'] == manifest['symbols'] and len(manifest['symbols']) == len(set(manifest['symbols'])) and
            set(manifest['symbols']) == set(current_pool['symbols']) ==
            (set(current_pool['symbols']) | {'BTCUSDT', 'ETHUSDT'}) and
            cap['pool_receipt_sha256'] == manifest['pool_receipt']['sha256'] and
            cap['funding_unit_certified'] is False and cap['native_Bybit_certified'] is False,
            'Accepted fixed July pool and source-only unqualified capability')
        task_id = cap['binding']['task_id']
        require(isinstance(task_id, str) and re.fullmatch(r'[a-f0-9]{32}', task_id), 'Actual capability task identity')
        task_path = STATE/'task-progress'/f'task-{task_id}.json'
        require(not task_path.is_symlink() and task_path.stat().st_size <= 2_000_000, 'Small closed task metadata')
        task = json.loads(task_path.read_bytes())
        require(task['id'] == task_id and task['status'] == 'completed' and task['exit_code'] == 0,
            'Every prior independent source capability actually closed0')
        tasks.append(dict(path=str(task_path), sha256=sha(task_path), task_id=task_id,
            status=task['status'], exit_code=task['exit_code'], pid=task['pid'], start_ticks=task['start_ticks']))
        if pool is None:
            pool, pool_ref, source_symbols = current_pool, manifest['pool_receipt'], manifest['symbols']
        else:
            require(same(manifest['pool_receipt'], pool_ref) and current_pool['symbols'] == pool['symbols'] and
                manifest['symbols'] == source_symbols and
                manifest['control_daily_records'] == manifests[0]['control_daily_records'],
                'Unchanged ordered pool, source catalogue and original daily controls')
        rows = manifest['market_records']
        keys = [(r['kind'], r['symbol'], r.get('interval'), r['month']) for r in rows]
        require(len(keys) == len(set(keys)) == 30 and set(keys) ==
            {(k, s, None if k == 'fundingRate' else '1m', month) for s in source_symbols
             for k in ('klines', 'markPriceKlines', 'fundingRate')}, 'Thirty exact roles in each accepted scoring month')
        for row in rows:
            require(cap['normalized_source_hashes'].get(row['normalized_path']) == row['normalized_sha256'],
                'Every monthly role retains its accepted normalized SHA')
            require(row['normalized_path'] not in pins, 'Distinct physical source ownership across months')
            pins[row['normalized_path']] = row['normalized_sha256']
        manifests.append(manifest); acceptances.append(acceptance_ref); market.extend(rows)
    base, october, november = manifests
    september_trade = [r for r in base['market_records'] if r['kind'] == 'klines']
    october_trade = [r for r in october['market_records'] if r['kind'] == 'klines']
    require(same(october['warmup_manifest'], CONTINUOUS_MANIFEST_REFS[0]) and
        same(october['warmup_source_acceptance'], acceptances[0]) and
        same(november['warmup_manifest'], CONTINUOUS_MANIFEST_REFS[1]) and
        same(november['warmup_source_acceptance'], acceptances[1]) and
        list(map(identity, october['warmup_minute_records'])) == list(map(identity, september_trade)) and
        list(map(identity, november['warmup_minute_records'])) ==
        list(map(identity, [*september_trade, *october_trade])), 'Exact original cross-month warmup aliases and order')
    _, base_pins = november_warmup_metadata(november, pool)
    daily = {}
    for row in [*(r for r in pool['source_records'] if r['symbol'] in source_symbols),
                *base['control_daily_records']]:
        key = row['symbol'], row['month']
        require(key not in daily or identity(daily[key]) == identity(row), 'Duplicate daily alias must retain exact identity')
        require(row['kind'] == 'klines' and row['interval'] == '1d' and
            base_pins.get(row['normalized_path']) == row['normalized_sha256'], 'Warm daily source bound to original independent capability')
        daily[key] = row
    require(len(daily) == 70 and set(daily) == {(s, '2024-'+m) for s in source_symbols
        for m in ('02', '03', '04', '05', '06', '07', '08')}, 'Seventy unique February-August warmup sources read once')
    for row in daily.values():
        require(row['normalized_path'] not in pins, 'Warmup and scoring source identities cannot overlap')
        pins[row['normalized_path']] = row['normalized_sha256']
    return dict(status=CONTINUOUS_MANIFEST_STATUS, source_only=True, checksummed_source_format_verified=True,
        start_us=START, end_us=NOV_END, days=91, score_months=[r[0] for r in CONTINUOUS_SCOPES],
        symbols=list(source_symbols), selected_symbols=list(pool['symbols']), pool_receipt=pool_ref,
        monthly_manifests=[dict(r) for r in CONTINUOUS_MANIFEST_REFS], monthly_acceptances=acceptances,
        accepted_closed_tasks=tasks, market_records=market, daily_records=list(daily.values()),
        control_daily_records=base['control_daily_records'], normalized_source_hashes=pins,
        prior_format_QA_reused=True, new_source_QA_performed=False, price_payloads_read=0,
        raw_archives_or_CRC_reread=False, monthly_account_reset=False, models_fit=0, orders_sent=0,
        locked_consumed=False, funding_unit_certified=False, native_Bybit_certified=False,
        publication_certified=False, boundary_events='PRESERVE_EVERY_RECORDED_EVENT_START_LE_EVENT_LT_END',
        scope='ACCEPTED_SOURCE_METADATA_COMPOSITION_NOT_ROWS_QA_ACCOUNT_NAV_OR_INVESTMENT_QUALIFICATION')


def load_continuous_portfolio_window(manifest_path, symbols, start_us=START, end_us=NOV_END):
    """One 91-day market window; the caller creates and simulates one wallet."""
    require(type(start_us) is int and type(end_us) is int and
        (start_us, end_us) == (START, NOV_END), 'Only fixed September-November continuous91D')
    require(isinstance(symbols, (tuple, list)) and symbols and len(symbols) == len(set(symbols)) and
        all(symbol_ok(s) for s in symbols), 'Explicit configured account symbol order')
    path = Path(manifest_path)
    require(path.resolve().is_relative_to(STATE.resolve()) and not path.is_symlink() and
        path.stat().st_size <= 2_000_000, 'Small exclusive continuous source manifest')
    manifest = json.loads(path.read_bytes())
    require(manifest == compose_continuous_manifest(manifest['monthly_manifests']),
        'Exact accepted metadata composition; no changed source or capability scope')
    pool = small_proof(manifest['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
    require(list(symbols) == pool['symbols'] or tuple(symbols) == ('BTCUSDT', 'ETHUSDT'),
        'Original ordered July pool or original two-asset control')
    result = window(pool, manifest['market_records'], pool_receipt_sha256=manifest['pool_receipt']['sha256'],
        control_daily_records=manifest['control_daily_records'], requested_symbols=symbols,
        start_us=start_us, end_us=end_us)
    result.update(manifest_path=str(path), manifest_sha256=sha(path), continuous_wallet_required=True,
        account_path='CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D', score_months=manifest['score_months'],
        input_proofs=[*manifest['market_records'], *manifest['daily_records']],
        daily_source_scope='FEB_AUG_DAILY_ONCE_PLUS_CONTINUOUS_SEP_NOV_SCORE_MINUTE_REDUCTIONS_NO_MONTHLY_RESET')
    return result


def winter_warmup_metadata(proofs, pool):
    """Reuse accepted D055 descriptors and three original capabilities, without price IO or QA."""
    ref = proofs['warmup_manifest']
    require(Path(ref['path']).resolve() == Path(WINTER_WARMUP_MANIFEST['path']).resolve() and
        ref['sha256'] == WINTER_WARMUP_MANIFEST['sha256'] and
        ref.get('required_status') == CONTINUOUS_MANIFEST_STATUS, 'Exact original D055 warmup manifest')
    previous = small_proof(ref, CONTINUOUS_MANIFEST_STATUS)
    require(previous == compose_continuous_manifest(previous['monthly_manifests']),
        'Three original source capabilities and byte identities remain accepted')
    require(previous['selected_symbols'] == pool['symbols'] and
        previous['pool_receipt']['sha256'] == proofs['pool_receipt']['sha256'] and
        previous['monthly_acceptances'] == proofs['warmup_source_acceptances'],
        'Same ordered July pool and original three warmup capabilities')
    warm = [r for r in previous['market_records'] if r['kind'] == 'klines']
    daily = previous['daily_records']
    require(len(warm) == 30 and len(daily) == 70, 'Thirty minute warmup and seventy original daily descriptors')
    pins = {r['normalized_path']: r['normalized_sha256'] for r in [*daily, *warm]}
    require(len(pins) == 100 and all(previous['normalized_source_hashes'].get(p) == h
        for p, h in pins.items()), 'Every reused warm source retains original accepted identity')
    return warm, daily, pins


def accepted_quarter_metadata(manifest, pool, *, spring=False):
    """Finite quarter capability/identity checks only; no Parquet, CRC or rows QA."""
    scopes = SPRING_SCOPES if spring else WINTER_SCOPES
    days, files = (122, 120) if spring else (90, 90)
    manifest_status = SPRING_MANIFEST_STATUS if spring else WINTER_MANIFEST_STATUS
    acceptance_status = SPRING_ACCEPTANCE_STATUS if spring else WINTER_ACCEPTANCE_STATUS
    require(manifest['status'] == manifest_status and manifest['source_only'] is True and
        manifest['checksummed_source_format_verified'] is True and manifest['days'] == days and
        manifest['score_months'] == [r[0] for r in scopes] and
        (manifest['start_us'], manifest['end_us']) == (scopes[0][1], scopes[-1][2]), 'Accepted fixed quarter source role')
    cap = small_proof(manifest['source_acceptance'], acceptance_status)
    require(cap['actual_exit_code'] == 0 and cap['source_only'] is True and
        cap['completed_files'] == len(cap['sources']) == files and
        cap['symbols'] == manifest['symbols'] == sorted(pool['symbols']) and
        cap['pool_receipt_sha256'] == manifest['pool_receipt']['sha256'] and
        cap['funding_unit_certified'] is False and cap['native_Bybit_certified'] is False,
        'One actually completed source-only quarter acceptance, without native or unit qualification')
    task_id = cap['binding']['task_id']
    require(isinstance(task_id, str) and re.fullmatch('[a-f0-9]{32}', task_id), 'Real independent capability identity')
    task_path = STATE/'task-progress'/f'task-{task_id}.json'
    require(not task_path.is_symlink() and task_path.stat().st_size <= 2_000_000, 'Small closed capability task')
    task = json.loads(task_path.read_bytes())
    require(task['id'] == task_id and task['status'] == 'completed' and task['exit_code'] == 0,
        'Quarter source acceptance truly closed0 before economics')
    warm, daily, warm_pins = (spring_warmup_metadata(manifest, pool) if spring else
        winter_warmup_metadata(manifest, pool))
    require(manifest['warmup_minute_records'] == warm and manifest['daily_records'] == daily,
        'Warm descriptors exactly retain their original owners and order')
    prior = small_proof(manifest['warmup_manifest'], WINTER_MANIFEST_STATUS if spring else CONTINUOUS_MANIFEST_STATUS)
    require(manifest['control_daily_records'] == prior['control_daily_records'], 'Original fourteen control daily aliases')
    market = manifest['market_records']
    identities = lambda rows: [tuple(r[k] for k in ('symbol', 'kind', 'interval', 'month',
        'normalized_path', 'normalized_sha256', 'normalized_bytes', 'rows')) for r in rows]
    require(len(market) == files and identities(market) == identities(cap['sources']),
        'Every scoring descriptor exactly matches the new independent acceptance')
    score_pins = {r['normalized_path']: r['normalized_sha256'] for r in market}
    require(len(score_pins) == files and cap['normalized_source_hashes'] == score_pins and
        not set(score_pins).intersection(warm_pins) and
        manifest['normalized_source_hashes'] == {**warm_pins, **score_pins},
        'Directly accepted score files and exact referenced warm source identities')
    return warm, daily, {**warm_pins, **score_pins}


def spring_warmup_metadata(proofs, pool):
    """Prior winter plus its accepted Sep-Nov chain; all prices remain unread here."""
    ref = proofs['warmup_manifest']
    require(Path(ref['path']).resolve() == Path(SPRING_WARMUP_MANIFEST['path']).resolve() and
        ref['sha256'] == SPRING_WARMUP_MANIFEST['sha256'] and
        ref.get('required_status') == WINTER_MANIFEST_STATUS, 'Exact accepted D056 winter warmup manifest')
    previous = small_proof(ref, WINTER_MANIFEST_STATUS)
    current = proofs['warmup_source_acceptance']
    prior_cap = previous['source_acceptance']
    require((ROOT/Path(current['path'])).resolve() == (ROOT/Path(prior_cap['path'])).resolve() and
        current['sha256'] == prior_cap['sha256'] and
        current.get('required_status') == WINTER_ACCEPTANCE_STATUS and
        previous['pool_receipt']['sha256'] == proofs['pool_receipt']['sha256'] and
        previous['selected_symbols'] == pool['symbols'], 'Same ordered July pool and exact winter capability')
    old_warm, daily, previous_pins = accepted_quarter_metadata(previous, pool)
    warm = [*old_warm, *(r for r in previous['market_records'] if r['kind'] == 'klines')]
    keys = [(r['symbol'], r['kind'], r['interval'], r['month']) for r in warm]
    require(len(keys) == len(set(keys)) == 60 and set(keys) ==
        {(s, 'klines', '1m', m) for s in pool['symbols']
         for m, _, _ in (*CONTINUOUS_SCOPES, *WINTER_SCOPES)} and len(daily) == 70,
        'Six accepted trade-minute warm months and seventy daily sources, no reranking')
    pins = {r['normalized_path']: r['normalized_sha256'] for r in [*daily, *warm]}
    require(len(pins) == 130 and all(previous_pins.get(p) == h for p, h in pins.items()),
        'Every inherited warm source keeps its original accepted byte identity')
    return warm, daily, pins


def load_quarter_portfolio_window(manifest_path, symbols, start_us, end_us):
    """One explicitly authorized complete quarter; one caller-owned wallet."""
    spring = (start_us, end_us) == (WINTER_END, SPRING_END)
    require(type(start_us) is int and type(end_us) is int and
        ((start_us, end_us) == (NOV_END, WINTER_END) or spring), 'Only fixed winter90D or spring122D')
    path = Path(manifest_path)
    require(path.resolve().is_relative_to(STATE.resolve()) and not path.is_symlink() and
        path.stat().st_size <= 2_000_000, 'Small accepted quarter STATE manifest')
    manifest = json.loads(path.read_bytes())
    pool = small_proof(manifest['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
    require(isinstance(symbols, (tuple, list)) and (list(symbols) == pool['symbols'] or
        tuple(symbols) == ('BTCUSDT', 'ETHUSDT')), 'Original ordered July pool or original two-asset control')
    warm, daily, _ = accepted_quarter_metadata(manifest, pool, spring=spring)
    market = manifest['market_records']
    result = window(pool, market, pool_receipt_sha256=manifest['pool_receipt']['sha256'],
        control_daily_records=manifest['control_daily_records'], requested_symbols=symbols,
        warmup_minute_records=warm, start_us=start_us, end_us=end_us)
    result.update(manifest_path=str(path), manifest_sha256=sha(path), continuous_wallet_required=True,
        account_path='CONTINUOUS_SHARED_ACCOUNT_MAR_JUN_122D' if spring else 'CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D',
        score_months=manifest['score_months'],
        input_proofs=[*market, *daily, *warm],
        daily_source_scope=('FEB_AUG_DAILY_ONCE_PLUS_SEP_FEB_WARM_AND_MAR_JUN_SCORE_CAUSAL_MINUTE_REDUCTIONS_NO_MONTHLY_RESET'
            if spring else 'FEB_AUG_DAILY_ONCE_PLUS_SEP_NOV_WARM_AND_DEC_FEB_SCORE_CAUSAL_MINUTE_REDUCTIONS_NO_MONTHLY_RESET'))
    return result


def load_winter_portfolio_window(manifest_path, symbols, start_us=NOV_END, end_us=WINTER_END):
    """Original fixed winter90D interface; its source and financial scope stay unchanged."""
    require((start_us, end_us) == (NOV_END, WINTER_END), 'Only fixed winter90D')
    return load_quarter_portfolio_window(manifest_path, symbols, start_us, end_us)


def load_spring_portfolio_window(manifest_path, symbols, start_us=WINTER_END, end_us=SPRING_END):
    """Fixed March-June122D, with Sep-Feb accepted minute-derived warmup."""
    require((start_us, end_us) == (WINTER_END, SPRING_END), 'Only fixed spring122D')
    return load_quarter_portfolio_window(manifest_path, symbols, start_us, end_us)


def load_portfolio_window(manifest_path, symbols, start_us, end_us):
    """Public runner API; manifest SHA is bound by the portfolio protocol.

    Root accepts checksums/format evidence into this manifest after pool and
    source finish separately. No manifest self-awards native or unit semantics.
    """
    if (start_us, end_us) == (START, NOV_END):
        return load_continuous_portfolio_window(manifest_path, symbols, start_us, end_us)
    if (start_us, end_us) == (NOV_END, WINTER_END):
        return load_winter_portfolio_window(manifest_path, symbols, start_us, end_us)
    if (start_us, end_us) == (WINTER_END, SPRING_END):
        return load_spring_portfolio_window(manifest_path, symbols, start_us, end_us)
    month = period_scope(start_us, end_us)
    require(isinstance(symbols, (tuple, list)) and symbols and len(symbols) == len(set(symbols)) and
        all(symbol_ok(s) for s in symbols), 'Explicit unique selected assets')
    path = Path(manifest_path)
    require(path.resolve().is_relative_to(STATE.resolve()) and not path.is_symlink() and
        path.stat().st_size <= 2_000_000, 'Small accepted STATE manifest, no general loader')
    manifest = json.loads(path.read_bytes())
    status = {'2024-09': 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        '2024-10': 'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        '2024-11': NOVEMBER_MANIFEST_STATUS}[month]
    require(manifest['status'] == status and manifest['checksummed_source_format_verified'] is True and
        manifest['start_us'] == start_us and manifest['end_us'] == end_us, 'Accepted checksummed explicit-window source role')
    pool = small_proof(manifest['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
    require(set(symbols) in (set(pool['symbols']), {'BTCUSDT', 'ETHUSDT'}), 'Predeclared pool/control, no score-based asset replacement')
    acceptance = small_proof(manifest['source_acceptance'])
    require(acceptance['source_only'] is True and acceptance['symbols'] == manifest['symbols'], 'Explicit source-format acceptance scope')
    require(acceptance['pool_receipt_sha256'] == manifest['pool_receipt']['sha256'], 'Source acceptance after identical frozen pool')
    market_records = manifest['market_records']
    pins = acceptance['normalized_source_hashes']
    prior_daily = [*manifest['control_daily_records'],
        *(r for r in pool['source_records'] if r['symbol'] in pool['symbols'])]
    warm = manifest.get('warmup_minute_records', [])
    require(all(pins.get(r['normalized_path']) == r['normalized_sha256'] for r in market_records), 'Each score row bound in current source proof')
    if month == '2024-10':
        prior = small_proof(manifest['warmup_source_acceptance'], 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY')
        prior_manifest = small_proof(manifest['warmup_manifest'], 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS')
        require(prior['source_only'] is True and prior['pool_receipt_sha256'] == manifest['pool_receipt']['sha256'] and
            prior_manifest['source_acceptance']['sha256'] == manifest['warmup_source_acceptance']['sha256'] and
            prior_manifest['pool_receipt']['sha256'] == manifest['pool_receipt']['sha256'], 'Same already accepted frozen-pool warmup scope')
        expected = [r for r in prior_manifest['market_records'] if r['kind'] == 'klines']
        identity = lambda r: (r['symbol'], r['kind'], r['interval'], r['month'], r['normalized_path'], r['normalized_sha256'], r['normalized_bytes'], r['rows'])
        require(sorted(map(identity, warm)) == sorted(map(identity, expected)) and
            all(prior['normalized_source_hashes'].get(r['normalized_path']) == r['normalized_sha256']
                for r in [*prior_daily, *warm]), 'Each pre-entry daily/minute row keeps accepted identity')
    elif month == '2024-11':
        expected, base_pins = november_warmup_metadata(manifest, pool)
        identity = lambda r: (r['symbol'], r['kind'], r['interval'], r['month'], r['normalized_path'],
                              r['normalized_sha256'], r['normalized_bytes'], r['rows'])
        require(sorted(map(identity, warm)) == sorted(map(identity, expected)) and
            all(base_pins.get(r['normalized_path']) == r['normalized_sha256'] for r in prior_daily),
            'Twenty accepted minute warmups and original daily inputs retain exact identity')
    else:
        require(all(pins.get(r['normalized_path']) == r['normalized_sha256'] for r in prior_daily), 'Each prior daily row bound in accepted source proof')
    result = window(pool, market_records, pool_receipt_sha256=manifest['pool_receipt']['sha256'],
        control_daily_records=manifest['control_daily_records'], requested_symbols=symbols,
        warmup_minute_records=warm, start_us=start_us, end_us=end_us)
    result.update(manifest_path=str(path), manifest_sha256=sha(path),
        daily_source_scope='PRE_SCORE_OFFICIAL_1D_PLUS_CAUSAL_SCORE_DAY_REDUCTIONS_OF_ACCEPTED_1M_TRADE_SOURCE')
    return result


def load_accepted_two_asset_control(symbols=('BTCUSDT', 'ETHUSDT'), start_us=START, end_us=END):
    """Original control needs no hypothetical new pool or repeated source QA."""
    month = period_scope(start_us, end_us)
    require(len(symbols) == 2 and set(symbols) == {'BTCUSDT', 'ETHUSDT'}, 'Original BTCETH control')
    proof = dict(path='reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json',
        sha256='8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa')
    accepted = small_proof(proof, 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS')
    catalog = reuse_catalog(accepted); market = []; daily = []; warm = []
    for symbol in symbols:
        for kind, interval in (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None)):
            market.append(catalog[(kind, symbol, interval, month)])
        if month == '2024-10':
            warm.append(catalog[('klines', symbol, '1m', '2024-09')])
        elif month == '2024-11':
            warm.extend(catalog[('klines', symbol, '1m', m)] for m in ('2024-09', '2024-10'))
        for control_month in ('2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08'):
            daily.append(catalog[('klines', symbol, '1d', control_month)])
    result = window(None, market, pool_receipt_sha256=None, control_daily_records=daily, requested_symbols=symbols,
        warmup_minute_records=warm, start_us=start_us, end_us=end_us)
    result.update(accepted_source_receipt=proof, source_reuse='EXACT_ACCEPTED_BYTES_NO_REPEAT_QA',
        daily_source_scope='OLD_PRE_SCORE_1D_PLUS_CAUSAL_ACCEPTED_1M_DAILY_REDUCTIONS',
        input_proofs=[*market, *daily, *warm])
    return result


def source_stage(args):
    """Past-only pool or one explicitly authorized selected-source month."""
    from scripts.research_v8.registry import FIELDS, append_event
    require(args.protocol is not None, 'Source phase requires pre-bound protocol')
    spec_path = args.protocol.resolve(); spec = json.loads(spec_path.read_bytes())
    run, output = Path(args.run_dir).resolve(), Path(args.output).resolve()
    phase = 'POOL_DAILY' if args.mode == 'pool' else spec['phase']
    require(phase in ('POOL_DAILY', 'SEPTEMBER_SOURCE', 'OCTOBER_SOURCE', 'NOVEMBER_SOURCE',
        'WINTER_SOURCE', 'SPRING_SOURCE'), 'Explicit source phase')
    require((args.mode == 'pool') == (phase == 'POOL_DAILY'), 'Separate pool/source execution mode')
    october = phase == 'OCTOBER_SOURCE'
    november = phase == 'NOVEMBER_SOURCE'
    winter = phase == 'WINTER_SOURCE'
    spring = phase == 'SPRING_SOURCE'
    quarter = winter or spring
    followup = october or november or quarter
    rules = SPRING_RULES if spring else WINTER_RULES if winter else NOVEMBER_RULES if november else OCTOBER_RULES if october else RULES
    budgets = SPRING_BUDGETS if spring else WINTER_BUDGETS if winter else NOVEMBER_BUDGETS if november else OCTOBER_BUDGETS if october else DEFAULT_BUDGETS
    start_us, end_us = ((WINTER_END, SPRING_END) if spring else (NOV_END, WINTER_END) if winter else
        (OCT_END, NOV_END) if november else (END, OCT_END) if october else (START, END))
    months = tuple(r[0] for r in (SPRING_SCOPES if spring else WINTER_SCOPES)) if quarter else (period_scope(start_us, end_us),)
    month = '2025-03..2025-06' if spring else '2024-12..2025-02' if winter else months[0]
    require(spec['phase'] == phase and spec['ready_for_execution'] is True and
        spec['capacity_registered'] is True and spec['rules'] == rules and
        spec['budgets'] == budgets and (not followup or
        (spec['start_us'], spec['end_us']) == (start_us, end_us)), 'Exact prospective phase/rules/budget')
    require(not november or (spec['contract_id'] == NOVEMBER_CONTRACT and spec['days'] == 30),
        'One prospective complete November source contract')
    require(not winter or (spec['contract_id'] == WINTER_CONTRACT and spec['days'] == 90 and
        spec['score_months'] == list(months) and spec['new_market_files'] == 72 and
        spec['reused_market_files'] == 18 and spec['joint_disk_reservation_bytes'] == 1_000_000_000),
        'One prospective complete winter source contract and joint capacity')
    require(not spring or (spec['contract_id'] == SPRING_CONTRACT and spec['days'] == 122 and
        spec['score_months'] == list(months) and spec['new_market_files'] == 96 and
        spec['reused_market_files'] == 24 and spec['joint_disk_reservation_bytes'] == 1_500_000_000),
        'One prospective complete spring source contract and joint capacity')
    require(run == Path(spec['run_dir']).resolve() and not run.exists() and run.is_relative_to(STATE.resolve()) and
        output == (ROOT/spec['output_path']).resolve() and not output.exists(), 'New exclusive source phase')
    require(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE/'v8-clean-env-20261002-v2'), 'Bounded clean/progress invocation')
    for p, h in spec['source_hashes'].items():
        require(p != 'state/dataset_lock.json' and (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p) == h, 'Source freeze '+p)
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    require(spec['source_hashes'].get(own) == sha(__file__), 'Current normal source identity')
    require(sha(ROOT/'state/dataset_lock.json') == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d', 'Hash-only locked policy guard')
    require(args.transport == 'windows' and args.transport_script is not None and
        spec['source_hashes'].get(args.transport_script.as_posix()) == sha(args.transport_script), 'Explicit default native source transport')
    old = small_proof(spec['reuse_manifest'], 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS')
    catalog = reuse_catalog(old); official_downloader(); warm = []; warm_daily = []
    if quarter:
        require(spec['reuse_manifest']['sha256'] ==
            '8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa',
            'Exact D045 accepted control source catalogue')
    if october:
        prior = small_proof(spec['warmup_source_acceptance'], 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY')
        prior_manifest = small_proof(spec['warmup_manifest'], 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS')
        require(prior['source_only'] is True and prior['pool_receipt_sha256'] == spec['pool_receipt_sha256'] and
            prior_manifest['source_acceptance']['sha256'] == spec['warmup_source_acceptance']['sha256'] and
            prior_manifest['pool_receipt']['sha256'] == spec['pool_receipt_sha256'], 'Previously accepted frozen-pool warmup metadata')
        warm = [r for r in prior_manifest['market_records'] if r['kind'] == 'klines']
        require(len(warm) == 10 and {r['symbol'] for r in warm} == set(spec['symbols']) and
            all(r['month'] == '2024-09' and r['interval'] == '1m' and
                prior['normalized_source_hashes'].get(r['normalized_path']) == r['normalized_sha256'] for r in warm),
            'Ten already accepted September trade-minute warmup records; no payload IO')
    elif november:
        pool = small_proof(spec['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
        warm, _ = november_warmup_metadata(spec, pool)
    elif winter:
        pool = small_proof(spec['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
        warm, warm_daily, _ = winter_warmup_metadata(spec, pool)
    elif spring:
        pool = small_proof(spec['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
        warm, warm_daily, _ = spring_warmup_metadata(spec, pool)
    if spec.get('partial_source_reuse'):
        prior = small_proof(spec['partial_source_reuse'], 'FAIL_D062_SOURCE_STAGE' if spring else 'FAIL_D050_SOURCE_STAGE')
        require(phase in ('SEPTEMBER_SOURCE', 'SPRING_SOURCE') and prior['actual_exit_code'] == 1 and
            prior['source_bytes_unchanged'] is True and prior['binding']['phase'] == phase and
            prior['binding']['source_sha256'] == spec['partial_source_reuse_source_sha256'] and
            prior['binding']['protocol_sha256'] == spec['partial_source_reuse_protocol_sha256'], 'Truthful failed-stage partial reuse')
        for row in prior['completed_sources']:
            key = (row['kind'], row['symbol'], row['interval'], row['month'])
            if spring and row['symbol'] in ('BTCUSDT', 'ETHUSDT'):
                require(key in catalog and row['normalized_sha256'] == catalog[key]['normalized_sha256'], 'Old accepted control unchanged')
                continue
            require(key not in catalog and row['month'] in months and row['symbol'] in spec['symbols'], 'One distinct bounded partial source')
            for field in ('zip', 'checksum', 'receipt'):
                path = Path(row[field+'_path'])
                require(path.resolve().is_relative_to(STATE.resolve()) and not path.is_symlink() and
                    sha(path) == row[field+'_sha256'], 'Exact completed partial source '+field)
            catalog[key] = dict(row, partial_source_proof=spec['partial_source_reuse'])
    run.mkdir(); began = time.monotonic(); client = WindowsSourceTransport(args.transport_script, run)
    binding = dict(task_id=os.environ['COIN_TASK_ID'], source_sha256=sha(__file__), source_hashes=spec['source_hashes'],
        protocol_path=str(spec_path), protocol_sha256=sha(spec_path), phase=phase, command=[sys.executable, *sys.argv],
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment=dict(sys_prefix=sys.prefix, uv_lock_sha256=sha(ROOT/'environments/v8/uv.lock')),
        transport='DEFAULT_WINDOWS_HTTPS_SAME_OFFICIAL_URLS_WSL_PARSE',
        compatibility_reason='WSL_NETWORK_ERRNO101; UNCHANGED_OFFICIAL_FORMATS_CHECKSUM_CRC',
        official_component_sha256=COMPONENT_SHA)
    save(run/'RUN_BINDING.json', binding)
    event = dict.fromkeys(FIELDS)
    event.update(event_id=spec['experiment_id']+':START', event_type='OPERATIONAL_SOURCE_START',
        experiment_id=spec['experiment_id'], git_commit=binding['git_commit'], protocol_hash=sha(spec_path),
        data_manifest_hash=spec['inventory_report']['sha256'] if args.mode == 'pool' else spec['pool_receipt']['sha256'],
        feature_set='PIT_JULY_QUOTE_VOLUME_POOL' if args.mode == 'pool' else 'SELECTED_SOURCE_FORMAT_ONLY',
        labels='NONE', model_family='NONE', hyperparameters=dict(protocol_path=str(spec_path)), seed=None,
        thresholds='FROZEN_PROTOCOL', cost_assumptions='NOT_EVALUATED_SOURCE_ONLY',
        all_folds='PRE_SCORE_SELECTION' if args.mode == 'pool' else month+'_SEEN_DEVELOPMENT_SOURCE_ONLY',
        success_failure='START_BEFORE_NEW_PRICE_IO', reason_for_next_experiment='Historical shared-account pool comparison',
        result_influenced_later_choice='NO_SCORE_RESULTS', task_id=binding['task_id'], fits=0)
    registration = append_event(ROOT/'reports/experiment_registry.jsonl', event)
    failure_status = 'FAIL_D062_SOURCE_STAGE' if spring else 'FAIL_D056_SOURCE_STAGE' if winter else 'FAIL_D054_SOURCE_STAGE' if november else 'FAIL_D051_SOURCE_STAGE' if october else 'FAIL_D050_SOURCE_STAGE'
    report = dict(status=failure_status, binding=binding, run_dir=str(run), source_only=True,
        registration_start=registration, run_binding_sha256=sha(run/'RUN_BINDING.json'),
        source_records=[], score_payloads_read=0, model_fits=0, orders_sent=0, GPU=0, locked_consumed=False,
        resources_before=resources.status(), native_Bybit_certified=False, funding_unit_certified=False)
    progress = formats.progress_writer(None); code = 1; completed = []
    reserve = budgets['pool_owned_bytes' if args.mode == 'pool' else 'market_owned_bytes']
    try:
        progress.update('实际磁盘扫描，扫描总量未知', None, None, '扫描')
        capacity_reserve = 1_500_000_000 if spring else 1_000_000_000 if november or winter else 700_000_000
        before = datetime.now(UTC).isoformat(); measured = disk.check(capacity_reserve)
        measured.update(scan_started_utc=before, scan_finished_utc=datetime.now(UTC).isoformat())
        report['disk_before'] = measured
        require(measured['total_bytes']+capacity_reserve < 32_000_000_000, 'Expected source plus research warning budget')
        last_disk = STATE/'task-progress'/'last-disk.json'; temporary = last_disk.with_suffix('.source.tmp')
        temporary.write_text(json.dumps(dict(ledger=measured, measured_at=time.time()), allow_nan=False), encoding='utf-8')
        os.replace(temporary, last_disk)
        with deadline(budgets['source_wall_seconds']-int(time.monotonic()-began)):
            def fetch(symbol, month):
                require(owned(run) < reserve, 'Before-source owned byte budget')
                value = acquire(entry(symbol, 'klines', '1d', month), run, client,
                    authorization=spec, reuse_catalog=catalog, budgets=budgets)
                completed.append(value); return value
            if args.mode == 'pool':
                inv = small_proof(spec['inventory_report'], 'COMPLETE_HISTORICAL_FOLDER_INVENTORY_NOT_POOL_OR_PRICE_ACCEPTANCE')
                require(inv['actual_exit_code'] == 0 and inv['full_listing'] is True and inv['price_payloads_read'] == 0,
                    'Real complete historical folder inventory before ranking')
                report.update(select_pool(inv['symbols'], fetch, exclusions=spec.get('exclusions'), progress=progress))
                require(report['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS', 'Ten eligible historical candidates not established')
            else:
                pool = small_proof(spec['pool_receipt'], 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
                require(spec['pool_receipt_sha256'] == spec['pool_receipt']['sha256'] and
                    spec['symbols'] == sorted(set(pool['symbols']) | {'BTCUSDT', 'ETHUSDT'}), 'Frozen pool precedes score prices')
                market = []; controls = []
                for symbol in ('BTCUSDT', 'ETHUSDT'):
                    for control_month in ('2024-02', '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08'):
                        key = ('klines', symbol, '1d', control_month)
                        require(key in catalog, 'Control warmup already accepted, no repeat download')
                        controls.append(catalog[key])
                plans = [entry(symbol, kind, interval, source_month) for source_month in months
                    for symbol in spec['symbols'] for kind, interval in
                    (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))]
                for planned in plans:
                    require(owned(run) < reserve, 'Before-score-source owned budget')
                    item = acquire(planned, run, client,
                        authorization=spec, reuse_catalog=catalog, budgets=budgets)
                    market.append(item); completed.append(item)
                    if followup:
                        normalized = sum(r['normalized_bytes'] for r in market)
                        owned_normalized = sum(r['normalized_bytes'] for r in market if Path(r['normalized_path']).is_relative_to(run))
                        require(normalized <= budgets['input_owned_bytes'] and
                            owned(run)-owned_normalized <= budgets['temporary_owned_bytes'], 'Actual input and temporary byte subbudgets')
                    require(not quarter or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <=
                        budgets['peak_RSS_bytes'], 'Actual quarter source RSS budget')
                    progress.update('选中币来源，选池已冻结', len(market), len(plans), '档', symbol=planned['symbol'], month=planned['month'])
                report.update(status=(SPRING_SOURCE_STATUS if spring else WINTER_SOURCE_STATUS if winter else NOVEMBER_SOURCE_STATUS if november else 'COMPLETE_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_PENDING_ACCEPTANCE' if october
                    else 'COMPLETE_D050_SELECTED_MARKET_SOURCE_FORMAT_PENDING_ACCEPTANCE'), market_records=market,
                    control_daily_records=controls, pool_receipt=spec['pool_receipt'], symbols=spec['symbols'],
                    start_us=start_us, end_us=end_us, score_payloads_read=len(market), checksummed_source_format_verified=True)
                if followup:
                    new_count = sum(r['acquisition'] in ('NEW_OFFICIAL_BYTES_FORMAT_QA_PENDING_INDEPENDENT_ACCEPTANCE',
                        'REUSED_FAILED_STAGE_COMPLETED_ROW_PENDING_INDEPENDENT_QA') for r in market)
                    old_count = sum(r['acquisition'] == 'REUSED_ACCEPTED_BYTES_NO_REPEAT_QA_OR_DOWNLOAD' for r in market)
                    require(new_count == (96 if spring else 72 if winter else 24) and old_count == (24 if spring else 18 if winter else 6) and
                        (not quarter or all((r['symbol'] in ('BTCUSDT', 'ETHUSDT')) ==
                        (r['acquisition'] == 'REUSED_ACCEPTED_BYTES_NO_REPEAT_QA_OR_DOWNLOAD') for r in market)),
                        'Exact new and independently accepted control source roles')
                    report.update(warmup_minute_records=warm, warmup_manifest=spec['warmup_manifest'],
                        prior_source_format_reused_without_QA=True, selected_pool_unchanged=True,
                        normalized_input_bytes=sum(r['normalized_bytes'] for r in market),
                        temporary_owned_bytes=owned(run)-sum(r['normalized_bytes'] for r in market if Path(r['normalized_path']).is_relative_to(run)))
                    if quarter:
                        previous = small_proof(spec['warmup_manifest'], WINTER_MANIFEST_STATUS if spring else CONTINUOUS_MANIFEST_STATUS)
                        require(controls == previous['control_daily_records'], 'Original control aliases preserved')
                        warm_caps = (dict(warmup_source_acceptance=spec['warmup_source_acceptance']) if spring else
                            dict(warmup_source_acceptances=spec['warmup_source_acceptances']))
                        report.update(**warm_caps, daily_records=warm_daily, score_months=list(months), days=122 if spring else 90,
                            new_market_files=new_count, reused_market_files=old_count,
                            monthly_account_reset=False, models_fit=0)
                    else:
                        report['warmup_source_acceptance'] = spec['warmup_source_acceptance']
        require(owned(run) <= reserve, 'Actual owned source budget')
        require(not (november or quarter) or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <=
            budgets['peak_RSS_bytes'], 'Actual registered source RSS budget')
        code = 0
    except Exception as error:
        report.update(status=failure_status, error_type=type(error).__name__, reason=str(error))
    finally:
        report.update(actual_exit_code=code, completed_source_files=len(completed),
            completed_sources=completed, source_bytes_unchanged=sha(__file__) == binding['source_sha256'],
            owned_bytes=owned(run), elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            WindowsPeakWorkingSet64_max=client.native_peak, combined_conservative_peak_bound_bytes=client.combined_peak,
            http_status_counts=client.http_status_counts, native_requests=client.requests, resources_after=resources.status())
        save(output, report)
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event, event_id=spec['experiment_id']+':RESULT',
            event_type='OPERATIONAL_SOURCE_RESULT', success_failure=report['status'],
            actual_exit_code=code, report_path=str(output), report_sha256=sha(output),
            reason_for_next_experiment=report.get('reason', 'Separate accepted pool/source precedes economic replay')))
        progress.update('来源阶段实际退出', len(completed), None, '档', actual_exit_code=code); progress.stop.set()
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('inventory', 'pool', 'acquire'), required=True)
    parser.add_argument('--run-dir', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--transport', choices=('wsl', 'windows'), default='wsl')
    parser.add_argument('--transport-script', type=Path)
    parser.add_argument('--protocol', type=Path)
    args = parser.parse_args()
    if args.mode != 'inventory':
        return source_stage(args)
    run = Path(args.run_dir).resolve(); output = Path(args.output).resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists(), 'Exclusive D-hosted inventory run')
    require(output.is_relative_to(ROOT) and not output.exists(), 'Exclusive small report')
    run.mkdir(); started = time.monotonic(); binding = dict(task_id=os.environ.get('COIN_TASK_ID'),
        source_sha256=sha(__file__), git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        command=[sys.executable, *sys.argv], phase='METADATA_INVENTORY_ONLY', official_index=INDEX,
        official_bucket=BUCKET, prefix=PREFIX, budgets=DEFAULT_BUDGETS,
        environment=dict(executable=sys.executable, sys_prefix=sys.prefix),
        source_hashes={p: sha(ROOT/p) for p in ('scripts/investment/multi_asset_data.py',
            'src/quant/data.py', 'src/quant/resources.py',
            'scripts/research_v8/funding_price_source_v2.py',
            'scripts/research_v7/oracle_flow_ceiling.py')})
    native = None
    if args.transport == 'windows':
        require(args.transport_script is not None and run.name == 'd050-multiasset-inventory-20261004-v2', 'Exclusive authorized Windows metadata recovery')
        native = WindowsMetadataTransport(args.transport_script, run)
        binding.update(transport='WINDOWS_DEFAULT_SYSTEM_HTTPS_METADATA_ONLY',
            transport_script=str(native.script), transport_sha256=native.script_sha256,
            compatibility_reason='WSL_ERRNO101_NO_ROUTE; SAME_OFFICIAL_METADATA_DEFAULT_WINDOWS_HTTPS')
    save(run/'RUN_BINDING.json', binding); progress = formats.progress_writer(None)
    report = dict(binding=binding, run_binding_sha256=sha(run/'RUN_BINDING.json'), run_dir=str(run),
        price_payloads_read=0, score_payloads_read=0, models_fit=0, orders_sent=0, GPU=0, locked_consumed=False)
    code = 1
    try:
        report['resources_before'] = resources.status()
        with deadline(DEFAULT_BUDGETS['inventory_wall_seconds']):
            if native is not None:
                report.update(inventory(native, run, progress=progress))
            else:
                with httpx.Client(timeout=20, follow_redirects=False) as client:
                    report.update(inventory(client, run, progress=progress))
        require(owned(run) <= DEFAULT_BUDGETS['inventory_owned_bytes'], 'Inventory owned bytes')
        code = 0
    except Exception as error:
        report.update(status='FAIL_D050_HISTORICAL_INVENTORY', error_type=type(error).__name__, reason=str(error))
    finally:
        if native is not None:
            report['requests'] = native.requests
            report['WindowsPeakWorkingSet64_max'] = max((r.get('WindowsPeakWorkingSet64', 0) for r in native.requests), default=0)
            report['combined_conservative_peak_bound_bytes'] = max((r.get('combined_conservative_peak_bound_bytes', 0) for r in native.requests), default=0)
        report.update(actual_exit_code=code, source_bytes_unchanged=sha(__file__)==binding['source_sha256'],
            elapsed_seconds=time.monotonic()-started, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=owned(run), resources_after=resources.status()); save(output, report)
        progress.update('历史目录已退出，未读价格', len(report.get('pages', [])), None, '页', actual_exit_code=code)
        progress.stop.set()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
