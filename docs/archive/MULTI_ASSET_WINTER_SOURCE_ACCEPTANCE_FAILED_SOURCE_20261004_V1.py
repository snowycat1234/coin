"""Independent fixed-pool followup source QA; no account calculation.

New files are checked against their saved official CSV. Exact rows of the
accepted two-asset catalogue retain that acceptance without a second rows QA.
The output certificate and small STATE manifest do not certify units, venue
filters, publication clocks, a global Top10, or investment performance.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import gc
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import sys
import time
import zipfile

import numpy as np
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event
from scripts.research_v8.funding_price_source_v2 import progress_writer

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
DAY, MINUTE = 86_400_000_000, 60_000_000
START, END = 1727740800000000, 1730419200000000
MONTHS = ['2024-'+m for m in ('02', '03', '04', '05', '06', '07', '08')]
CONTRACT = 'D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ACCEPTANCE_V1'
STATUS = 'PASS_D051_FIXED_POOL_OCTOBER_SOURCE_FORMAT_ONLY'
MANIFEST_STATUS = 'PASS_D051_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'
SOURCE_SCOPES = {
    '2024-10': dict(start_us=START, end_us=END, prior_days=30, prior_files=100,
        contract=CONTRACT, status=STATUS, manifest_status=MANIFEST_STATUS,
        failure='FAIL_D051_FIXED_POOL_OCTOBER_SOURCE_ACCEPTANCE',
        prior_status='PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY',
        prior_manifest_status='PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'),
    '2024-11': dict(start_us=END, end_us=1733011200000000, prior_days=31, prior_files=30,
        contract='D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ACCEPTANCE_V1',
        status='PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY',
        manifest_status='PASS_D054_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS',
        failure='FAIL_D054_FIXED_POOL_NOVEMBER_SOURCE_ACCEPTANCE',
        prior_status=STATUS, prior_manifest_status=MANIFEST_STATUS),
    '2024-12_2025-02': dict(start_us=1733011200000000, end_us=1740787200000000,
        score_months=('2024-12', '2025-01', '2025-02'), days=90,
        files=90, new_files=72, reused_files=18,
        contract='D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ACCEPTANCE_V1',
        status='PASS_D056_FIXED_POOL_WINTER_SOURCE_FORMAT_ONLY',
        manifest_status='PASS_D056_SELECTED_PORTFOLIO_WINTER_SOURCE_BINDING_NOT_ECONOMICS',
        failure='FAIL_D056_FIXED_POOL_WINTER_SOURCE_ACCEPTANCE'),
}
WINTER_WARMUP_SHA = '847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50'
WINTER_WARMUP_STATUS = 'PASS_D055_CONTINUOUS_91D_ACCEPTED_SOURCE_BINDING_NOT_ECONOMICS'
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
FORMAT = 'scripts/research_v8/audit_funding_price_source.py'
FORMAT_SHA = 'edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c'
TRADE = 'scripts/investment/audit_perpetual_trade_source.py'
TRADE_SHA = '7770342534d216b121d42da3c541874bb7c175fcd3b10c9939337417760e8e92'
IDENTITY = ('normalized_path', 'normalized_sha256', 'normalized_bytes', 'rows')


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(name, digest):
    path = ROOT/name
    need(not path.is_symlink() and sha(path) == digest, 'Frozen reused independent source '+name)
    spec = importlib.util.spec_from_file_location('source_qa_'+path.stem, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def root_path(name):
    p = Path(name)
    p = p if p.is_absolute() else ROOT/p
    need(p.resolve().is_relative_to(ROOT), 'Bound ROOT metadata')
    return p


def project_source(name, guard):
    if name == 'tools/task_progress/task_progress_sample.py':
        return guard.ordinary(ROOT/name)
    return guard.project(name)


def source_report(proof):
    """The pool retains UNKNOWN candidate evidence, so it may exceed 2MB.

    This local normal reader allows at most 4MB only for the two actual source
    reports; the accepted small-file/disk guards are unchanged.
    """
    path = root_path(proof['path'])
    need(path.parent == ROOT/'reports/fast_research' and path.suffix == '.json'
         and path.is_file() and 0 < path.stat().st_size <= 4_000_000,
         'Bound actual source report at most4MB; larger needs preserved projection')
    for parent in (path, *path.parents):
        need(not parent.is_symlink(), 'No source report symlink')
        if parent == ROOT:
            break
    need(sha(path) == proof['sha256'], 'Exact actual pool/market receipt bytes')
    return json.loads(path.read_bytes())


def key(row):
    return row['kind'], row['symbol'], row.get('interval'), row['month']


def payload(name, owner, digest, limit, size=None):
    p = Path(name)
    need(p.is_absolute() and '..' not in p.parts and p.is_relative_to(owner)
         and p.is_file(), 'Exact authorized STATE payload')
    for parent in (p, *p.parents):
        need(not parent.is_symlink(), 'No source symlink')
        if parent == STATE:
            break
    need(0 < p.stat().st_size <= limit and (size is None or p.stat().st_size == size)
         and sha(p) == digest, 'Saved source bytes/bound/SHA')
    return p


def new_receipt(row, owner, guard):
    receipt, _ = guard.small(Path(row['receipt_path']), row['receipt_sha256'])
    need(Path(row['receipt_path']).parent == Path(row['normalized_path']).parent
         and all(receipt[k] == row[k] for k in (*IDENTITY, 'quality', 'zip_path',
             'zip_sha256', 'checksum_path', 'checksum_sha256')),
         'Producer per-file receipt matches row')
    # New producer uses a flat entry, unlike the older canonical receipts.
    need(all(receipt[k] == row[k] for k in ('kind', 'symbol', 'interval', 'month', 'url', 'checksum_url')),
         'Exact archive identity')
    suffix = (f"{row['symbol']}-fundingRate-{row['month']}.zip" if row['interval'] is None
              else f"{row['interval']}/{row['symbol']}-{row['interval']}-{row['month']}.zip")
    url = f"https://data.binance.vision/data/futures/um/monthly/{row['kind']}/{row['symbol']}/{suffix}"
    need(row['url'] == url and row['checksum_url'] == url+'.CHECKSUM', 'Official product URL')
    parquet = payload(row['normalized_path'], owner, row['normalized_sha256'], 32_000_000, row['normalized_bytes'])
    archive = payload(row['zip_path'], owner, row['zip_sha256'], 16_000_000)
    check = payload(row['checksum_path'], owner, row['checksum_sha256'], 4096)
    fields = check.read_text(encoding='ascii').split()
    need(len(fields) == 2 and fields[0].lower() == row['zip_sha256']
         and fields[1].lstrip('*') == archive.name == url.rsplit('/', 1)[1], 'Saved official CHECKSUM')
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        need(len(members) == 1 and not members[0].is_dir() and not members[0].flag_bits & 1
             and members[0].filename == archive.name[:-4]+'.csv'
             and 0 < members[0].file_size <= (128_000 if row['interval'] == '1d' else 128_000_000),
             'Single bounded original CSV; no extraction')
        csv_bytes = members[0].file_size
    return parquet, archive, csv_bytes


def audit_trade(row, parquet, archive, independent):
    frame = pl.read_parquet(parquet)
    need(frame.columns == independent.SCHEMA and frame.height == row['rows']
         and all(frame.schema[n] == pl.Float64 for n in independent.FLOATS)
         and all(frame.schema[n] == pl.Int64 for n in independent.INTS if n != 'ingested_us')
         and ((frame.schema['ingested_us'] == pl.Int32 and frame['ingested_us'].eq(0).all())
              or (frame.schema['ingested_us'] == pl.Int64 and frame['ingested_us'].gt(0).all()))
         and all(frame.schema[n] == pl.String for n in ('symbol', 'interval'))
         and sum(frame.null_count().row(0)) == 0, 'Typed original trade schema/no null')
    step = DAY if row['interval'] == '1d' else MINUTE
    first = independent.stamp(row['month']+'-01')
    year, month = map(int, row['month'].split('-'))
    last = first+calendar.monthrange(year, month)[1]*DAY
    opens = frame['open_us'].to_numpy()
    need(len(opens) and first <= opens[0] and opens[-1]+step == last
         and np.array_equal(opens, np.arange(opens[0], last, step, dtype=np.int64))
         and (opens[0] == first or (row['month'], row['interval']) == ('2024-02', '1d')),
         'Full month calendar; only pre-listing February daily prefix may be absent')
    need(np.array_equal(frame['close_us'].to_numpy(), opens+step)
         and np.array_equal(frame['available_us'].to_numpy(), opens+step)
         and np.array_equal(frame['source_close_us'].to_numpy(), opens+step-1000)
         and frame['symbol'].unique().to_list() == [row['symbol']]
         and frame['interval'].unique().to_list() == [row['interval']]
         and frame['ingested_us'].n_unique() == 1,
         'Raw epoch-ms to UTC-us; exclusive close availability proxy')
    need(frame.select(pl.all_horizontal(pl.col(independent.FLOATS).is_finite()).all()).item()
         and frame.filter((pl.col('low') <= 0) | (pl.col('high') < pl.max_horizontal('open', 'close', 'low'))
             | (pl.col('low') > pl.min_horizontal('open', 'close', 'high'))
             | pl.any_horizontal(pl.col(['volume', 'quote_volume', 'trade_count', 'taker_buy_base', 'taker_buy_quote']) < 0)
             | (pl.col('taker_buy_base') > pl.col('volume')*(1+1e-8))).height == 0,
         'Finite positive OHLC/nonnegative true volume/count/taker fields')
    rows = frame.iter_rows(named=True); count = 0
    with zipfile.ZipFile(archive) as z:
        with z.open(z.infolist()[0]) as stream, io.TextIOWrapper(stream, encoding='utf-8-sig', newline='') as text:
            raw_rows = csv.reader(text)
            need(next(raw_rows) == independent.HEADER, 'Actual official USD-M trade header')
            for raw in raw_rows:
                need(len(raw) == 12 and count < frame.height, 'CSV width/EOF count')
                value = next(rows)
                need(int(raw[0])*1000 == value['open_us'] and int(raw[6])*1000 == value['source_close_us']
                     and int(raw[8]) == value['trade_count'] and all(
                         independent.finite(raw[i]) == value[n] for i, n in independent.RAW_FLOATS.items()),
                     'Every raw integer and OHLCV value equals normalized value')
                independent.finite(raw[11]); count += 1
        need(count == frame.height and z.testzip() is None, 'Full original CSV and independent CRC')
    need(row['quality']['timestamp_unit'] == 'milliseconds', 'Producer declared raw trade ms')
    result = dict(rows=count, first_open_us=int(opens[0]), last_close_us=int(opens[-1]+step),
                  timestamp_unit='RAW_EPOCH_MS_NORMALIZED_UTC_US', no_fill_or_drop=True,
                  ingestion_metadata=('PRODUCER_DEFAULT_INT32_ZERO_UNKNOWN_NOT_PUBLICATION'
                      if frame.schema['ingested_us'] == pl.Int32 else 'POSITIVE_INT64_INGESTION_NOT_PUBLICATION'))
    daily = opens.tolist() if row['interval'] == '1d' else None
    del frame
    return result, daily


def audit_proxy(row, parquet, archive, csv_bytes, independent, format_spec):
    # Only translate existing receipt keys; the original independent format and
    # raw CSV comparison function is unchanged and does not trust these labels.
    entry = dict(kind=row['kind'], symbol=row['symbol'], month=row['month'],
                 checksum={'announced_zip_sha256': row['zip_sha256']},
                 announced_zip_bytes=archive.stat().st_size)
    receipt = dict(status='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA', entry=entry,
        zip_path=str(archive), zip_sha256=row['zip_sha256'], checksum_path=row['checksum_path'],
        checksum_sha256=row['checksum_sha256'], parquet_path=str(parquet),
        parquet_sha256=row['normalized_sha256'], parquet_bytes=row['normalized_bytes'],
        stats={'rows': row['rows']}, uncompressed_csv_bytes=csv_bytes)
    return independent.audit_one(receipt, format_spec)


def november_warmup(previous, prior, pool, selected, symbols, spec, g, pins):
    """Bind 90 old inputs through both certificates; read bytes, never rows/CRC."""
    accepted_ref = previous['warmup_source_acceptance']
    manifest_ref = previous['warmup_manifest']
    need(root_path(accepted_ref['path']).resolve() == root_path(prior['prior_acceptance']['path']).resolve()
         and accepted_ref['sha256'] == prior['prior_acceptance']['sha256']
         and Path(manifest_ref['path']).resolve() == Path(prior['prior_manifest']['path']).resolve()
         and manifest_ref['sha256'] == prior['prior_manifest']['sha256'],
         'October certificate and manifest retain the same September proof chain')
    historical, _ = g.small(root_path(accepted_ref['path']), accepted_ref['sha256'])
    initial, _ = g.small(Path(manifest_ref['path']), manifest_ref['sha256'])
    need(historical['status'] == accepted_ref['required_status']
         == 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY'
         and historical['actual_exit_code'] == 0 and historical['source_only'] is True
         and historical['completed_files'] == len(historical['sources']) == 100
         and len(historical['normalized_source_hashes']) == 100
         and initial['status'] == manifest_ref['required_status']
         == 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'
         and initial['checksummed_source_format_verified'] is True
         and (initial['start_us'], initial['end_us']) == (START-30*DAY, START)
         and initial['source_acceptance']['sha256'] == accepted_ref['sha256']
         and initial['pool_receipt']['sha256'] == historical['pool_receipt_sha256']
         == spec['pool_receipt']['sha256']
         and historical['symbols'] == symbols and historical['selected_symbols'] == selected
         and previous['control_daily_records'] == initial['control_daily_records']
         and pins.get(root_path(accepted_ref['path']).relative_to(ROOT).as_posix()) == accepted_ref['sha256'],
         'Exact accepted September certificate and original daily catalogue')
    historical_task = g.closed(historical['binding']['task_id'])
    september = [r for r in initial['market_records'] if r['kind'] == 'klines']
    october = [r for r in previous['market_records'] if r['kind'] == 'klines']
    need(previous['warmup_minute_records'] == september and len(september) == len(october) == 10,
         'Original September trade warmup and accepted October trade subset')
    warm_minutes = [*september, *october]
    rows = [*previous['control_daily_records'],
            *(r for r in pool['source_records'] if r['symbol'] in selected), *warm_minutes]
    catalog = {}
    for row in rows:
        identity = key(row)
        if identity in catalog:
            need(all(catalog[identity][k] == row[k] for k in IDENTITY), 'Identical daily reuse aliases')
        catalog[identity] = row
    expected = {('klines', s, '1d', m) for s in symbols for m in MONTHS}
    expected |= {('klines', s, '1m', m) for s in symbols for m in ('2024-09', '2024-10')}
    old_catalog = {key(r): r for r in historical['sources']}
    current_catalog = {key(r): r for r in prior['sources']}
    expected_old = {('klines', s, '1d', m) for s in symbols for m in MONTHS}
    expected_old |= {(k, s, i, '2024-09') for s in symbols for k, i in
                     (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
    expected_current = {(k, s, i, '2024-10') for s in symbols for k, i in
                        (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
    need(set(catalog) == expected and len(catalog) == 90
         and set(old_catalog) == expected_old and set(current_catalog) == expected_current
         and len(prior['normalized_source_hashes']) == 30,
         'Warmup90: daily70 + September trade10 + October trade10; certificate scopes exact')
    for identity, row in catalog.items():
        certificate = prior if identity[-1] == '2024-10' else historical
        accepted = (current_catalog if certificate is prior else old_catalog)[identity]
        need(all(accepted[k] == row[k] for k in IDENTITY)
             and certificate['normalized_source_hashes'].get(row['normalized_path']) == row['normalized_sha256'],
             'Each warmup row bound to its actual certificate')
        payload(row['normalized_path'], STATE, row['normalized_sha256'], 32_000_000, row['normalized_bytes'])
    warm_acceptance = dict(path=spec['prior_acceptance']['path'], sha256=spec['prior_acceptance']['sha256'],
                           required_status=STATUS)
    warm_manifest = dict(path=spec['prior_manifest']['path'], sha256=spec['prior_manifest']['sha256'],
                         required_status=MANIFEST_STATUS)
    return warm_minutes, warm_acceptance, warm_manifest, dict(
        prior_certificate_files_referenced=130, prior_warmup_files_reused=90,
        prior_market_warmup_files_reused=20, prior_daily_files_reused=70,
        warmup_historical_acceptance=accepted_ref, warmup_historical_manifest=manifest_ref,
        warmup_historical_acceptance_task=historical_task,
        warmup_derivation='LOADER_DAILY_UTC_AGGREGATION_OF_ACCEPTED_SEPTEMBER_AND_OCTOBER_TRADE_1M_NOT_NEW_SOURCE')


def winter_warmup(previous, pool, selected, symbols, spec, g, pins):
    """Reuse daily70/trade30 through the three original source capabilities."""
    need(spec['prior_manifest']['sha256'] == WINTER_WARMUP_SHA
         and Path(spec['prior_manifest']['path']) == STATE/'d055-continuous-input-binding-20261004-v1/INPUT_MANIFEST.json'
         and spec['prior_manifest']['required_status'] == previous['status'] == WINTER_WARMUP_STATUS
         and previous['source_only'] is True and previous['checksummed_source_format_verified'] is True
         and (previous['start_us'], previous['end_us'], previous['days']) == (START-30*DAY, 1733011200000000, 91)
         and previous['score_months'] == ['2024-09', '2024-10', '2024-11']
         and previous['symbols'] == symbols and previous['selected_symbols'] == selected
         and previous['pool_receipt']['sha256'] == spec['pool_receipt']['sha256']
         and previous['monthly_acceptances'] == spec['prior_acceptances']
         and len(previous['monthly_manifests']) == len(spec['prior_acceptances']) == len(previous['accepted_closed_tasks']) == 3,
         'Exact accepted D055 composite; three original warm capabilities, not one new QA')
    statuses = ('PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY', STATUS,
                'PASS_D054_FIXED_POOL_NOVEMBER_SOURCE_FORMAT_ONLY')
    certificates = []; catalogs = []; monthly_rows = []; tasks = []
    for index, (manifest_ref, cap_ref, status, month) in enumerate(zip(
            previous['monthly_manifests'], spec['prior_acceptances'], statuses,
            previous['score_months'], strict=True)):
        need(pins.get(root_path(cap_ref['path']).relative_to(ROOT).as_posix()) == cap_ref['sha256'],
             'Original warm capability included in frozen metadata')
        manifest, _ = g.small(Path(manifest_ref['path']), manifest_ref['sha256'])
        cap, _ = g.small(root_path(cap_ref['path']), cap_ref['sha256'])
        need(manifest['status'] == manifest_ref['required_status']
             and manifest['checksummed_source_format_verified'] is True
             and root_path(manifest['source_acceptance']['path']).resolve() == root_path(cap_ref['path']).resolve()
             and manifest['source_acceptance']['sha256'] == cap_ref['sha256']
             and cap['status'] == cap_ref['required_status'] == status
             and cap['actual_exit_code'] == 0 and cap['source_only'] is True
             and cap['funding_unit_certified'] is False and cap['native_Bybit_certified'] is False
             and cap['symbols'] == manifest['symbols'] == symbols and cap['selected_symbols'] == selected
             and cap['pool_receipt_sha256'] == manifest['pool_receipt']['sha256'] == spec['pool_receipt']['sha256']
             and manifest['control_daily_records'] == previous['control_daily_records'],
             'Original source-only warm capability and same controls/pool')
        catalog = {key(r): r for r in cap['sources']}
        expected = {(k, s, i, month) for s in symbols for k, i in
                    (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
        if index == 0:
            expected |= {('klines', s, '1d', m) for s in symbols for m in MONTHS}
        need(set(catalog) == expected and len(catalog) == len(cap['sources']) == cap['completed_files']
             == len(cap['normalized_source_hashes']) == (100 if index == 0 else 30)
             and len(manifest['market_records']) == 30
             and {key(r) for r in manifest['market_records']} == {r for r in expected if r[-1] == month},
             'Exact original monthly/daily certificate universe, with no lost rows')
        task = g.closed(cap['binding']['task_id']); saved = previous['accepted_closed_tasks'][index]
        need(saved['task_id'] == task['task']['id'] and saved['sha256'] == task['sha256']
             and Path(saved['path']).resolve() == Path(task['path']).resolve(), 'Same actually closed warm capability task')
        tasks.append(task); certificates.append(cap); catalogs.append(catalog)
        for row in manifest['market_records']:
            accepted = catalog[key(row)]
            need(all(row[k] == accepted[k] for k in IDENTITY)
                 and cap['normalized_source_hashes'].get(row['normalized_path']) == row['normalized_sha256'],
                 'Each composed monthly row retains its original independent identity')
        monthly_rows.extend(manifest['market_records'])
    daily = previous['daily_records']; warm_minutes = [r for r in monthly_rows if r['kind'] == 'klines']
    need(previous['market_records'] == monthly_rows and len(daily) == 70 and len(warm_minutes) == 30
         and len({key(r) for r in daily}) == 70
         and {key(r) for r in daily} == {('klines', s, '1d', m) for s in symbols for m in MONTHS}
         and len(previous['control_daily_records']) == 14
         and {key(r) for r in previous['control_daily_records']}
         == {('klines', s, '1d', m) for s in ('BTCUSDT', 'ETHUSDT') for m in MONTHS},
         'Winter warm100: daily70 and accepted September-November trade30 only')
    all_pins = {r['normalized_path']: r['normalized_sha256'] for r in [*daily, *monthly_rows]}
    need(len(all_pins) == 160 and previous['normalized_source_hashes'] == all_pins,
         'Original D055 full source map remains exact')
    for row in [*daily, *warm_minutes]:
        index = previous['score_months'].index(row['month']) if row['interval'] == '1m' else 0
        accepted = catalogs[index][key(row)]
        need(all(row[k] == accepted[k] for k in IDENTITY)
             and certificates[index]['normalized_source_hashes'].get(row['normalized_path']) == row['normalized_sha256'],
             'Every warm source bound to the certificate that actually checked it')
        payload(row['normalized_path'], STATE, row['normalized_sha256'], 32_000_000, row['normalized_bytes'])
    warm_pins = {r['normalized_path']: r['normalized_sha256'] for r in [*daily, *warm_minutes]}
    return warm_minutes, list(spec['prior_acceptances']), dict(spec['prior_manifest']), dict(
        prior_certificate_files_referenced=160, prior_warmup_files_reused=100,
        prior_market_warmup_files_reused=30, prior_daily_files_reused=70, warmup_acceptance_tasks=tasks,
        warmup_derivation='LOADER_CAUSAL_DAILY_REDUCTION_OF_ACCEPTED_SEP_NOV_TRADE_1M_NOT_NEW_SOURCE'), daily, warm_pins


def winter_accepted_market(records, old, old_catalog, g, pins):
    """Reference the 18 old identities and their saved independent QA results."""
    references = {}; catalogs = {}; results = {}
    for row in records:
        if row['symbol'] not in ('BTCUSDT', 'ETHUSDT'):
            continue
        accepted = old_catalog[key(row)]
        need(all(row[k] == accepted[k] for k in (*IDENTITY, 'receipt_path', 'receipt_sha256')),
             'Exact accepted quarter control source identity')
        name, digest = accepted['independent_QA_report_path'], accepted['independent_QA_report_sha256']
        need(old['accepted_source_roles'].get(name) == digest and pins.get(name) == digest,
             'Old accepted control capability frozen, without repeating its QA')
        if name not in catalogs:
            cap, _ = g.small(root_path(name), digest)
            need(cap['status'] == 'PASS_D045_94_SOURCE_COVERAGE_70_FIRST_QA_24_ACCEPTED_REUSE_NOT_UNIT_OR_ECONOMICS'
                 and cap['funding_unit_certified'] is False and cap['locked_consumed'] is False,
                 'Actual old source capability; no unit promotion')
            catalogs[name] = {key(r): r for r in cap['sources']}
            references[name] = dict(path=name, sha256=digest, required_status=cap['status'])
        proof = catalogs[name][key(row)]
        need(all(proof[k] == row[k] for k in ('normalized_path', 'normalized_sha256', 'rows',
                                            'receipt_path', 'receipt_sha256')),
             'Saved original independent result matches each reused source')
        result = dict(status='REUSED_ACCEPTED_EXACT_METADATA_NO_RAW_OR_ROWS_REREAD', rows=row['rows'],
                      original_independent_status=proof['status'], acceptance=references[name])
        if row['kind'] == 'fundingRate':
            result.update({k: proof[k] for k in ('first_timestamp_ms', 'last_timestamp_ms',
                'first_interval_hours', 'last_interval_hours', 'observed_interval_hours', 'actual_delta_hours')})
        results[key(row)] = result
    need(len(results) == 18, 'Exactly eighteen reused quarter controls; no reconstructed source task')
    return results, list(references.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    g = load(GUARD, GUARD_SHA)
    spec, protocol_sha = g.small(args.protocol.resolve())
    month = spec['source_month']
    need(month in SOURCE_SCOPES, 'Explicit accepted followup source scope')
    scope = SOURCE_SCOPES[month]
    winter = month == '2024-12_2025-02'
    score_months = list(scope.get('score_months', (month,)))
    files, new_files, reused_files = (scope.get(k, v) for k, v in
                                    (('files', 30), ('new_files', 24), ('reused_files', 6)))
    start_us, end_us = scope['start_us'], scope['end_us']
    run, output = args.run_dir.resolve(), args.output.resolve()
    need(spec['ready_to_execute'] is True and spec['contract_id'] == scope['contract']
         and (spec['start_us'], spec['end_us']) == (start_us, end_us)
         and run == Path(spec['run_dir']) and run.parent == STATE and not run.exists()
         and output == root_path(spec['output_path']) and output.parent == ROOT/'reports/fast_research'
         and not output.exists(), 'Exclusive prospective fixed '+month+' source scope')
    if winter:
        need(spec['score_months'] == score_months, 'Exactly December-February quarter; no missing month')
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE/'v8-clean-env-20261002-v2')
         and pl.thread_pool_size() <= 2, 'Actual bounded clean CPU2 task')
    budgets = spec['budgets']
    need(all(type(budgets[k]) is int and 0 < budgets[k] <= v for k, v in
             {'new_owned_bytes': 5_000_000, 'peak_RSS_bytes': 1_000_000_000, 'wall_seconds': 1200}.items()),
         'Small independent QA budget')
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    pins = spec['frozen_sources']
    for name, digest in pins.items():
        need(name != 'state/dataset_lock.json' and sha(project_source(name, g)) == digest, 'Frozen source '+name)
    need(pins.get(own) == sha(__file__) and pins.get(GUARD) == GUARD_SHA
         and pins.get(FORMAT) == FORMAT_SHA and pins.get(TRADE) == TRADE_SHA,
         'Own and original independent functions pinned')
    need(sha(ROOT/'state/dataset_lock.json') == g.LOCK_SHA, 'Private policy streaming SHA only')
    manifest_path = Path(spec['manifest_path'])
    need(manifest_path == run/'INPUT_MANIFEST.json', 'Single exclusive small STATE manifest')
    run.mkdir(); started = time.monotonic(); before = resources.status(); g.bounded(before)
    binding = dict(task_id=os.environ['COIN_TASK_ID'], checker_sha256=sha(__file__),
        source_hashes=dict(pins), protocol_path=str(args.protocol.resolve()), protocol_sha256=protocol_sha,
        command=[sys.executable, *sys.argv], environment={'sys_prefix': sys.prefix})
    g.write(run/'RUN_BINDING.json', binding)
    report = dict(status=scope['failure'], binding=binding,
        run_dir=str(run), run_binding_sha256=sha(run/'RUN_BINDING.json'), source_only=True,
        normalized_source_hashes={}, sources=[], resources_before=before, funding_rate_unit='UNCONFIRMED',
        funding_unit_certified=False, native_Bybit_certified=False, publication_time_certified=False,
        global_Top10_certified=False, economics='NOT_EVALUATED', models_fit=0, orders_sent=0,
        GPU=0, locked_consumed=False, candidate='NONE', APR='NOT_EVALUATED',
        own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=spec['experiment_id'], git_commit=None,
        data_manifest_hash=spec['market_receipt']['sha256'], protocol_hash=protocol_sha,
        feature_set='FIXED_POOL_FOLLOWUP_SOURCE_FORMAT_ONLY', labels='NONE', model_family='NONE',
        hyperparameters={}, seed=None, thresholds='FROZEN_PROTOCOL', cost_assumptions='NOT_EVALUATED',
        all_folds=month+'_SOURCE_ONLY', result_influenced_later_choice='NO_ECONOMICS',
        reason_for_next_experiment='Independent new '+month+' format gate; accepted warmup bytes reused',
        task_id=binding['task_id'], source_hashes={args.protocol.resolve().relative_to(ROOT).as_posix(): protocol_sha})
    progress = None; code = 1; market = previous = None
    try:
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event, event_id=spec['experiment_id']+':START',
            event_type='OPERATIONAL_SOURCE_AUDIT_START', success_failure='START_BEFORE_NEW_SOURCE_ROWS'))
        market = source_report(spec['market_receipt'])
        need(market['status'] == spec['market_receipt']['required_status']
             and market['actual_exit_code'] == 0 and market['source_bytes_unchanged'] is True
             and market['source_only'] is True and market['model_fits'] == market['orders_sent'] == market['GPU'] == 0
             and market['locked_consumed'] is False, 'Actual completed source-only '+month+' producer')
        producer_task = g.closed(market['binding']['task_id'])
        need(market['binding']['task_id'] != binding['task_id'], 'Independent QA task differs from producer')
        report['market_receipt_task'] = producer_task
        market_spec, _ = g.small(root_path(market['binding']['protocol_path']), market['binding']['protocol_sha256'])
        need(market['binding']['source_hashes'] == market_spec['source_hashes'], 'Actual producer protocol source map')
        for name, digest in market_spec['source_hashes'].items():
            need(pins.get(name) == digest, 'Current producer source included in freeze '+name)
        pool = source_report(spec['pool_receipt'])
        need(pool['status'] == 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS' and pool['actual_exit_code'] == 0
             and pool['score_payloads_read'] == 0 and pool['source_only'] is True,
             'Fixed original July pool; no score-based reselection')
        report['pool_receipt_task'] = g.closed(pool['binding']['task_id'])
        previous, _ = g.small(Path(spec['prior_manifest']['path']), spec['prior_manifest']['sha256'])
        if not winter:
            prior, _ = g.small(root_path(spec['prior_acceptance']['path']), spec['prior_acceptance']['sha256'])
            need(prior['status'] == scope['prior_status']
                 and prior['actual_exit_code'] == 0 and prior['source_only'] is True
                 and prior['completed_files'] == len(prior['sources']) == scope['prior_files']
                 and previous['status'] == scope['prior_manifest_status']
                 and previous['checksummed_source_format_verified'] is True
                 and (previous['start_us'], previous['end_us']) == (start_us-scope['prior_days']*DAY, start_us)
                 and previous['source_acceptance']['sha256'] == spec['prior_acceptance']['sha256']
                 and previous['pool_receipt']['sha256'] == prior['pool_receipt_sha256'] == spec['pool_receipt']['sha256'],
                 'Exact accepted preceding source/manifest and unchanged pool')
            report['prior_acceptance_task'] = g.closed(prior['binding']['task_id'])
        old, _ = g.small(root_path(spec['reuse_manifest']['path']), spec['reuse_manifest']['sha256'])
        need(old['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS',
             'Accepted old BTCETH source catalogue')
        old_catalog = {key(r): r for r in old['source_files'].values()}
        selected = pool['symbols']; symbols = sorted(set(selected) | {'BTCUSDT', 'ETHUSDT'})
        prior_pool = previous if winter else prior
        need(len(selected) == len(set(selected)) == 10 and market['symbols'] == prior_pool['symbols'] == symbols
             and prior_pool['selected_symbols'] == selected and market['pool_receipt']['sha256'] == spec['pool_receipt']['sha256']
             and (market['start_us'], market['end_us']) == (start_us, end_us),
             'Same ten frozen members and complete '+month+' window')
        if winter:
            warm_minutes, warm_acceptances, warm_manifest, warm_stats, warm_daily, warm_pins = winter_warmup(
                previous, pool, selected, symbols, spec, g, pins)
            need(market['days'] == 90 and market['score_months'] == score_months
                 and market['warmup_minute_records'] == warm_minutes and market['daily_records'] == warm_daily
                 and market['warmup_source_acceptances'] == warm_acceptances and market['warmup_manifest'] == warm_manifest,
                 'Exact quarter scoring scope and unchanged one hundred warm descriptors')
        elif month == '2024-11':
            warm_minutes, warm_acceptance, warm_manifest, warm_stats = november_warmup(
                previous, prior, pool, selected, symbols, spec, g, pins)
        else:
            warm_rows = [*previous['market_records'], *previous['control_daily_records'],
                         *(r for r in pool['source_records'] if r['symbol'] in selected)]
            warm_catalog = {}
            for row in warm_rows:
                identity = key(row)
                if identity in warm_catalog:
                    need(all(warm_catalog[identity][k] == row[k] for k in IDENTITY), 'Duplicate warmup aliases identical')
                warm_catalog[identity] = row
            prior_catalog = {key(r): r for r in prior['sources']}
            expected_warm = {(k, s, i, '2024-09') for s in symbols for k, i in
                             (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
            expected_warm |= {('klines', s, '1d', m) for s in symbols for m in MONTHS}
            need(set(warm_catalog) == set(prior_catalog) == expected_warm
                 and len(warm_catalog) == 100 and len(prior['normalized_source_hashes']) == 100,
                 'Accepted warmup scope: September30 plus February-August daily70')
            warm_minutes = [r for r in previous['market_records'] if r['kind'] == 'klines']
            warm_acceptance = dict(path=spec['prior_acceptance']['path'], sha256=spec['prior_acceptance']['sha256'],
                required_status='PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY')
            warm_manifest = dict(path=spec['prior_manifest']['path'], sha256=spec['prior_manifest']['sha256'],
                required_status='PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS')
            need(len(warm_minutes) == 10 and market['warmup_minute_records'] == warm_minutes
                 and market['warmup_source_acceptance'] == warm_acceptance and market['warmup_manifest'] == warm_manifest,
                 'Exact accepted September trade warmup proof')
            for row in warm_catalog.values():
                accepted = prior_catalog[key(row)]
                need(all(accepted[k] == row[k] for k in IDENTITY)
                     and prior['normalized_source_hashes'].get(row['normalized_path']) == row['normalized_sha256'],
                     'Prior complete independent row identity')
                if row['interval'] == '1d' or row in warm_minutes:
                    payload(row['normalized_path'], STATE, row['normalized_sha256'], 32_000_000, row['normalized_bytes'])
            warm_stats = dict(prior_certificate_files_referenced=100, prior_warmup_files_reused=80,
                prior_market_warmup_files_reused=10, prior_daily_files_reused=70,
                warmup_derivation='LOADER_DAILY_UTC_AGGREGATION_OF_ACCEPTED_SEPTEMBER_TRADE_1M_NOT_NEW_SOURCE')
        if not winter:
            need(market['warmup_minute_records'] == warm_minutes
                 and market['warmup_source_acceptance'] == warm_acceptance and market['warmup_manifest'] == warm_manifest,
                 'Exact accepted trade warmup and certificate chain')
        need(market['control_daily_records'] == previous['control_daily_records'], 'Old controls daily unchanged')
        records = market['market_records']
        need(len(records) == files and len({key(r) for r in records}) == files
             and {key(r) for r in records} == {(k, s, i, m) for m in score_months for s in symbols for k, i in
                 (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))},
             'Exact '+month+' source identities; no fill/drop/replacement')
        if winter:
            accepted_market, accepted_refs = winter_accepted_market(records, old, old_catalog, g, pins)
            report.update(reused_market_manifest=spec['reuse_manifest'], reused_market_acceptances=accepted_refs,
                prior_manifest=spec['prior_manifest'], prior_acceptances=spec['prior_acceptances'])
        independent = load(TRADE, TRADE_SHA); proxy = load(FORMAT, FORMAT_SHA)
        format_spec, _ = g.small(ROOT/'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json',
                                pins['protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json'])
        owner = Path(market['run_dir']); need(owner.parent == STATE, 'Exact new actual source owner')
        progress = progress_writer(files); fresh = reused = 0
        for index, row in enumerate(records):
            need(time.monotonic()-started < budgets['wall_seconds'], 'Independent wall bound')
            if row['symbol'] in ('BTCUSDT', 'ETHUSDT'):
                accepted = old_catalog[key(row)]
                need(all(row[k] == accepted[k] for k in (*IDENTITY, 'receipt_path', 'receipt_sha256')),
                     'Exact accepted '+month+' control rows')
                payload(row['normalized_path'], STATE, row['normalized_sha256'], 32_000_000, row['normalized_bytes'])
                result = accepted_market[key(row)] if winter else dict(
                    status='REUSED_ACCEPTED_EXACT_METADATA_NO_RAW_OR_ROWS_REREAD', rows=row['rows'])
                reused += 1
            else:
                parquet, archive, csv_bytes = new_receipt(row, owner, g)
                result = audit_trade(row, parquet, archive, independent)[0] if row['kind'] == 'klines' else audit_proxy(
                    row, parquet, archive, csv_bytes, proxy, format_spec)
                need(sha(parquet) == row['normalized_sha256'] and sha(archive) == row['zip_sha256'],
                     'New source bytes unchanged during independent QA')
                fresh += 1; gc.collect()
            report['normalized_source_hashes'][row['normalized_path']] = row['normalized_sha256']
            report['sources'].append(dict(kind=row['kind'], symbol=row['symbol'], interval=row.get('interval'),
                month=row['month'], **{k: row[k] for k in IDENTITY}, independent_QA=result))
            progress.update(str(new_files)+'新增'+month+'核验/'+str(reused_files)+'旧接受档复用',
                            index+1, files, '档', newly_verified=fresh, accepted_reused=reused)
            need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= budgets['peak_RSS_bytes'], 'RSS bound')
        need(fresh == new_files and reused == reused_files and len(report['normalized_source_hashes']) == files
             and all(sha(project_source(n, g)) == d for n, d in pins.items()), 'Final new/reused counts and accepted warmup binding')
        if winter:
            joins = []; tolerance = format_spec['funding_nominal_interval_tolerance_ms']
            need(0 <= tolerance <= 1000, 'Original nominal funding interval jitter bound')
            for symbol in symbols:
                funding = sorted((r for r in report['sources'] if r['symbol'] == symbol
                                  and r['kind'] == 'fundingRate'), key=lambda r: r['month'])
                for left, right in zip(funding, funding[1:]):
                    a, b = left['independent_QA'], right['independent_QA']
                    delta = b['first_timestamp_ms']-a['last_timestamp_ms']
                    hours = (a['last_interval_hours'], b['first_interval_hours'])
                    need(delta > 0 and any(abs(delta-h*3_600_000) <= tolerance for h in hours),
                         'Actual recorded cross-month funding gap versus its reported intervals')
                    joins.append(dict(symbol=symbol, left_month=left['month'], right_month=right['month'],
                        actual_delta_ms=delta, boundary_reported_interval_hours=list(hours)))
            need(len(joins) == 20, 'Twenty December-January-February funding boundary joins')
            report.update(days=90, score_months=score_months, crossmonth_funding=joins,
                funding_event_count=sum(r['rows'] for r in report['sources'] if r['kind'] == 'fundingRate'),
                warmup_manifest=warm_manifest, warmup_source_acceptances=warm_acceptances,
                source_capability_scope='72_FIRST_QA_18_ACCEPTED_SCORE_METADATA_100_ACCEPTED_WARM_HASHES')
        report.update(status=scope['status'], symbols=symbols, selected_symbols=selected,
            pool_receipt_sha256=spec['pool_receipt']['sha256'], start_us=start_us, end_us=end_us,
            completed_files=files, newly_verified_files=fresh, reused_accepted_files=reused,
            **warm_stats,
            prior_warmup_rows_QA_repeated=False, prior_warmup_CRC_repeated=False,
            raw_units='TRADE_RAW_MS_TO_US; MARK_AND_FUNDING_RAW_MS; FUNDING_RATE_UNCONFIRMED',
            availability='EXCLUSIVE_CLOSED_PRICE_BAR_PROXY_NOT_PUBLICATION_OR_RATE_AVAILABILITY_CERTIFICATE')
        if not winter:
            report.update(prior_acceptance=spec['prior_acceptance'], prior_manifest=spec['prior_manifest'])
        code = 0
    except Exception as error:
        report.update(status=scope['failure'], reason=str(error), error_type=type(error).__name__)
    finally:
        report.update(actual_exit_code=code, elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_after=resources.status())
        try:
            g.bounded(report['resources_after'])
            need(report['peak_RSS_bytes'] <= budgets['peak_RSS_bytes']
                 and report['elapsed_seconds'] < budgets['wall_seconds'], 'Final RSS/wall bound')
            pending = None
            if code == 0:
                pending = dict(status=scope['manifest_status'], checksummed_source_format_verified=True,
                    start_us=start_us, end_us=end_us, symbols=report.get('symbols', []),
                    market_records=market['market_records'], control_daily_records=previous['control_daily_records'],
                    warmup_minute_records=warm_minutes, warmup_manifest=warm_manifest,
                    pool_receipt=spec['pool_receipt'], source_acceptance={'path': str(output), 'sha256': '0'*64,
                        'required_status': scope['status']})
                if winter:
                    score_pins = report['normalized_source_hashes']
                    need(not set(score_pins).intersection(warm_pins), 'Score and warm sources are distinct')
                    pending.update(source_only=True, days=90, score_months=score_months,
                        selected_symbols=selected, daily_records=warm_daily,
                        warmup_source_acceptances=warm_acceptances,
                        normalized_source_hashes={**warm_pins, **score_pins},
                        reused_market_manifest=spec['reuse_manifest'], reused_market_acceptances=accepted_refs)
                    need(len(pending['normalized_source_hashes']) == 190, 'Ninety score plus one hundred warm SHA identities')
                else:
                    pending['warmup_source_acceptance'] = warm_acceptance
            projected = len(json.dumps(report, ensure_ascii=False, allow_nan=False).encode())
            if pending is not None:
                projected += len(json.dumps(pending, ensure_ascii=False, allow_nan=False).encode())
            need(sum(p.stat().st_size for p in run.rglob('*') if p.is_file())+projected+100_000
                 <= budgets['new_owned_bytes'], 'Small owned outputs with serialization reserve')
        except Exception as error:
            code = 1
            report.update(status=scope['failure'], actual_exit_code=1,
                          reason=str(error), error_type=type(error).__name__)
        g.write(output, report)
        if code == 0:
            pending['source_acceptance']['sha256'] = sha(output)
            g.write(manifest_path, pending)
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event, event_id=spec['experiment_id']+':RESULT',
            event_type='OPERATIONAL_SOURCE_AUDIT_RESULT', success_failure=report['status'], actual_exit_code=code,
            report_path=str(output), report_sha256=sha(output)))
        if progress is not None:
            progress.update('独立'+month+'来源验收退出', len(report['sources']), files, '档', actual_exit_code=code)
            progress.stop.set()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
