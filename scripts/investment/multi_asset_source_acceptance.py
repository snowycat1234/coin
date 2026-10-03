"""Independent D050 selected-source format QA; no portfolio/account calculation.

New files are checked against their saved official CSV. Exact rows of the
accepted two-asset catalogue retain that acceptance without a second rows QA.
The output certificate and small STATE manifest do not certify units, venue
filters, publication clocks, a global Top10, or investment performance.
"""
from __future__ import annotations

import argparse
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
START, END = 1725148800000000, 1727740800000000
MONTHS = ['2024-'+m for m in ('02', '03', '04', '05', '06', '07', '08')]
CONTRACT = 'D050_SELECTED_SOURCE_INDEPENDENT_FORMAT_ACCEPTANCE_V1'
STATUS = 'PASS_D050_SELECTED_MARKET_AND_DAILY_SOURCE_FORMAT_ONLY'
MANIFEST_STATUS = 'PASS_D050_SELECTED_PORTFOLIO_SOURCE_BINDING_NOT_ECONOMICS'
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
    last = independent.stamp('2024-03-01') if row['month'] == '2024-02' else first+(
        31 if row['month'] in ('2024-03', '2024-05', '2024-07', '2024-08') else 30)*DAY
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    g = load(GUARD, GUARD_SHA)
    spec, protocol_sha = g.small(args.protocol.resolve())
    run, output = args.run_dir.resolve(), args.output.resolve()
    need(spec['ready_to_execute'] is True and spec['contract_id'] == CONTRACT
         and run == Path(spec['run_dir']) and run.parent == STATE and not run.exists()
         and output == root_path(spec['output_path']) and output.parent == ROOT/'reports/fast_research'
         and not output.exists(), 'Exclusive prospective independent scope')
    need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE/'v8-clean-env-20261002-v2')
         and pl.thread_pool_size() <= 2, 'Actual bounded clean CPU2 task')
    budgets = spec['budgets']
    need(all(type(budgets[k]) is int and 0 < budgets[k] <= v for k, v in
             {'new_owned_bytes': 5_000_000, 'peak_RSS_bytes': 1_000_000_000, 'wall_seconds': 1200}.items()), 'Small independent QA budget')
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    pins = spec['frozen_sources']
    for name, digest in pins.items():
        need(name != 'state/dataset_lock.json' and sha(g.project(name)) == digest, 'Frozen source '+name)
    need(pins.get(own) == sha(__file__) and pins.get(GUARD) == GUARD_SHA
         and pins.get(FORMAT) == FORMAT_SHA and pins.get(TRADE) == TRADE_SHA, 'Own and original independent functions pinned')
    need(sha(ROOT/'state/dataset_lock.json') == g.LOCK_SHA, 'Private policy SHA only')
    manifest_path = Path(spec['manifest_path'])
    need(manifest_path == run/'INPUT_MANIFEST.json', 'Single exclusive small STATE manifest')
    run.mkdir(); started = time.monotonic(); before = resources.status(); g.bounded(before)
    binding = dict(task_id=os.environ['COIN_TASK_ID'], checker_sha256=sha(__file__),
        source_hashes=dict(pins), protocol_path=str(args.protocol.resolve()), protocol_sha256=protocol_sha,
        command=[sys.executable, *sys.argv], environment={'sys_prefix': sys.prefix})
    g.write(run/'RUN_BINDING.json', binding)
    report = dict(status='FAIL_D050_SELECTED_SOURCE_ACCEPTANCE', binding=binding,
        run_dir=str(run), run_binding_sha256=sha(run/'RUN_BINDING.json'), source_only=True,
        normalized_source_hashes={}, sources=[], resources_before=before, funding_rate_unit='UNCONFIRMED',
        funding_unit_certified=False, native_Bybit_certified=False, publication_time_certified=False,
        global_Top10_certified=False, economics='NOT_EVALUATED', models_fit=0, orders_sent=0,
        GPU=0, locked_consumed=False, candidate='NONE', APR='NOT_EVALUATED',
        own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=spec['experiment_id'], git_commit=None, data_manifest_hash=spec['market_receipt']['sha256'],
        protocol_hash=protocol_sha, feature_set='SELECTED_SOURCE_FORMAT_ONLY', labels='NONE', model_family='NONE',
        hyperparameters={}, seed=None, thresholds='FROZEN_PROTOCOL', cost_assumptions='NOT_EVALUATED',
        all_folds='SEPT2024_SOURCE_ONLY', result_influenced_later_choice='NO_ECONOMICS',
        reason_for_next_experiment='Independent format gate for configured portfolio', task_id=binding['task_id'],
        source_hashes={args.protocol.resolve().relative_to(ROOT).as_posix(): protocol_sha})
    progress = None; code = 1
    try:
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event, event_id=spec['experiment_id']+':START',
            event_type='OPERATIONAL_SOURCE_AUDIT_START', success_failure='START_BEFORE_SOURCE_ROWS'))
        def proof(role, status):
            item = spec[role]; value = source_report(item)
            need(value['status'] == status and value['actual_exit_code'] == 0
                 and value['source_bytes_unchanged'] is True and value['source_only'] is True
                 and value['model_fits'] == value['orders_sent'] == value['GPU'] == 0
                 and value['locked_consumed'] is False, 'Actual '+role+' source-only status')
            source_spec, _ = g.small(root_path(value['binding']['protocol_path']), value['binding']['protocol_sha256'])
            need(value['binding']['source_hashes'] == source_spec['source_hashes'], 'Actual producer protocol source map')
            for name, digest in source_spec['source_hashes'].items():
                if role == 'pool_receipt' and name == 'scripts/investment/multi_asset_data.py' and pins.get(name) != digest:
                    archive = spec['pool_source_archive']
                    need(archive['sha256'] == digest and pins.get(archive['path']) == digest,
                         'Exact pool-executed source preserved before normal market job-path repair')
                else:
                    need(pins.get(name) == digest, 'Actual source included in independent freeze '+name)
            identity = value['binding']['task_id']; closed = g.closed(identity)
            need(identity != binding['task_id'], 'Producer and independent task differ')
            report[role+'_task'] = closed
            return value
        pool = proof('pool_receipt', 'POOL_SELECTED_PRE_SCORE_WITH_SCOPE_LIMITATIONS')
        market = proof('market_receipt', 'COMPLETE_D050_SELECTED_MARKET_SOURCE_FORMAT_PENDING_ACCEPTANCE')
        market_spec, _ = g.small(root_path(market['binding']['protocol_path']), market['binding']['protocol_sha256'])
        partial_catalog = {}; partial_owner = None
        if market_spec.get('partial_source_reuse'):
            item = market_spec['partial_source_reuse']
            failed, _ = g.small(root_path(item['path']), item['sha256'])
            need(failed['status'] == 'FAIL_D050_SOURCE_STAGE' and failed['actual_exit_code'] == 1
                 and failed['completed_source_files'] == len(failed['completed_sources']) == 1
                 and failed['binding']['source_sha256'] == market_spec['partial_source_reuse_source_sha256']
                 == spec['pool_source_archive']['sha256']
                 and failed['binding']['protocol_sha256'] == market_spec['partial_source_reuse_protocol_sha256'],
                 'Exactly one preserved completed file from failed market initialization')
            failed_task = g.closed(failed['binding']['task_id'], 1)
            partial_owner = Path(failed['run_dir'])
            need(partial_owner.parent == STATE, 'Exact failed-stage source owner')
            partial_catalog = {key(r): r for r in failed['completed_sources']}
            report['preserved_failed_market_source'] = dict(report_path=item['path'], report_sha256=item['sha256'],
                status=failed['status'], actual_exit_code=1, task=failed_task,
                scope='FIRST_NEW_FILE_QA_ONLY_NOT_PARENT_SOURCE_ACCEPTANCE')
        old, _ = g.small(root_path(spec['reuse_manifest']['path']), spec['reuse_manifest']['sha256'])
        need(old['status'] == 'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS', 'Accepted old catalogue')
        old_catalog = {key(r): r for r in old['source_files'].values()}
        selected = pool['symbols']; symbols = sorted(set(selected) | {'BTCUSDT', 'ETHUSDT'})
        need(len(selected) == len(set(selected)) == 10 and market['symbols'] == symbols
             and market['pool_receipt']['sha256'] == spec['pool_receipt']['sha256']
             and pool['score_payloads_read'] == 0 and market['source_only'] is True
             and (market['start_us'], market['end_us']) == (START, END), 'Same prospective pool and complete September')
        rows = [*market['market_records'], *market['control_daily_records'],
                *(r for r in pool['source_records'] if r['symbol'] in selected)]
        catalog = {}
        for row in rows:
            identity = key(row)
            if identity in catalog:
                need(all(catalog[identity][k] == row[k] for k in IDENTITY), 'Duplicate aliases must be identical')
            catalog[identity] = row
        expected = {(k, s, i, '2024-09') for s in symbols for k, i in
                    (('klines', '1m'), ('markPriceKlines', '1m'), ('fundingRate', None))}
        expected |= {('klines', s, '1d', m) for s in symbols for m in MONTHS}
        need(set(catalog) == expected, 'Exact selected+controls source roles/months; no locked data')
        prefix = {}
        if spec.get('completed_audit_prefix'):
            item = spec['completed_audit_prefix']
            previous, _ = g.small(root_path(item['path']), item['sha256'])
            need(previous['status'] == 'FAIL_D050_SELECTED_SOURCE_ACCEPTANCE' and previous['actual_exit_code'] == 1
                 and previous['reason'] == 'Typed original trade schema/no null'
                 and previous['binding']['checker_sha256'] == item['source_sha256']
                 and pins.get(item['source_archive']) == item['source_sha256']
                 and previous['binding']['protocol_sha256'] == item['protocol_sha256']
                 and previous['binding']['source_hashes'][spec['market_receipt']['path']] == spec['market_receipt']['sha256']
                 and len(previous['sources']) == 10, 'Exact failed-schema task with completed ten-file prefix')
            g.small(root_path(item['protocol_path']), item['protocol_sha256'])
            failed_task = g.closed(previous['binding']['task_id'], 1)
            prefix = {key(r): r for r in previous['sources']}
            need(len(prefix) == 10 and set(prefix) == {('fundingRate', s, None, '2024-09') for s in symbols},
                 'Only the ten already-completed funding identities may be reused')
            report['completed_audit_prefix_reference'] = dict(report_path=item['path'], report_sha256=item['sha256'],
                task=failed_task, source_archive=item['source_archive'], source_sha256=item['source_sha256'],
                scope='EIGHT_COMPLETED_NEW_FILE_QA_PLUS_TWO_OLD_METADATA_REUSES_NOT_PARENT_PASS')
        independent = load(TRADE, TRADE_SHA); proxy = load(FORMAT, FORMAT_SHA)
        format_spec, _ = g.small(ROOT/'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json', pins['protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json'])
        owners = {Path(pool['run_dir']), Path(market['run_dir'])}
        need(all(p.parent == STATE for p in owners), 'Explicit two actual source owners')
        progress = progress_writer(len(catalog)); fresh = reused = prefix_new = 0; daily = {s: [] for s in symbols}
        for index, (identity, row) in enumerate(sorted(catalog.items(), key=lambda x: str(x[0]))):
            need(time.monotonic()-started < budgets['wall_seconds'], 'Independent wall limit')
            if identity in prefix and identity not in old_catalog:
                prior = prefix[identity]
                need(all(prior[k] == row[k] for k in IDENTITY)
                     and prior['independent_QA']['status'] == 'PASS_SOURCE_FORMAT_ONLY'
                     and prior['independent_QA']['all_published_values_equal_raw'] is True
                     and prior['independent_QA']['zip_crc_full_read'] is True, 'Completed independent file proof exact identity')
                owner = next((o for o in owners if Path(row['normalized_path']).is_relative_to(o)), None)
                need(owner is not None, 'Exact source owner of already-verified new funding file')
                for kind, maximum in (('normalized', 32_000_000), ('zip', 16_000_000), ('checksum', 4096)):
                    payload(row[kind+'_path'], owner, row[kind+'_sha256'], maximum)
                g.small(Path(row['receipt_path']), row['receipt_sha256'])
                result = dict(prior['independent_QA'], evidence_role='REUSED_COMPLETED_INDEPENDENT_FILE_QA_FROM_FAILED_PARENT_NO_ROWS_OR_CRC_REPEAT')
                fresh += 1; prefix_new += 1
            elif identity in old_catalog:
                prior = old_catalog[identity]
                need(all(row[k] == prior[k] for k in IDENTITY)
                     and row['receipt_sha256'] == prior['receipt_sha256'], 'Exact old accepted bytes/receipt identity')
                result = dict(status='REUSED_ACCEPTED_EXACT_METADATA_NO_RAW_OR_ROWS_REREAD', rows=row['rows'])
                reused += 1
            else:
                owner = next((o for o in owners if Path(row['normalized_path']).is_relative_to(o)), None)
                if identity in partial_catalog:
                    prior = partial_catalog[identity]
                    need(row.get('partial_source_proof') == market_spec['partial_source_reuse']
                         and all(row[k] == prior[k] for k in (*IDENTITY, 'receipt_path', 'receipt_sha256',
                             'zip_path', 'zip_sha256', 'checksum_path', 'checksum_sha256')),
                         'Explicit single failed-owner completed row identity; first independent QA')
                    owner = partial_owner
                need(owner is not None, 'New source belongs to actual pool/market task')
                parquet, archive, csv_bytes = new_receipt(row, owner, g)
                if row['kind'] == 'klines':
                    result, clocks = audit_trade(row, parquet, archive, independent)
                    if clocks is not None:
                        daily[row['symbol']].extend(clocks)
                else:
                    result = audit_proxy(row, parquet, archive, csv_bytes, proxy, format_spec)
                need(sha(parquet) == row['normalized_sha256'] and sha(archive) == row['zip_sha256'], 'New bytes unchanged during QA')
                fresh += 1; gc.collect()
            report['normalized_source_hashes'][row['normalized_path']] = row['normalized_sha256']
            report['sources'].append(dict(kind=row['kind'], symbol=row['symbol'], interval=row.get('interval'),
                month=row['month'], **{k: row[k] for k in IDENTITY}, independent_QA=result))
            progress.update('新增格式独立核验/旧接受来源复用', index+1, len(catalog), '档', newly_verified=fresh, accepted_reused=reused)
            need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= budgets['peak_RSS_bytes'], 'Independent RSS bound')
        for symbol in selected:
            if symbol in ('BTCUSDT', 'ETHUSDT'):
                continue  # Exact complete pre-score days already accepted by D045.
            clock = sorted(daily[symbol]); tail = [t for t in clock if START-200*DAY <= t < START]
            need(tail == list(range(START-200*DAY, START, DAY)), 'Last200 complete UTC days without fill/drop '+symbol)
        need(time.monotonic()-started < budgets['wall_seconds'] and all(
            sha(g.project(name)) == digest for name, digest in pins.items()), 'Final wall/source binding')
        report.update(status=STATUS, symbols=symbols, selected_symbols=selected,
            pool_receipt_sha256=spec['pool_receipt']['sha256'], completed_files=len(catalog),
            newly_verified_files=fresh, reused_accepted_files=reused, warmup_days_per_selected_symbol=200,
            completed_new_QA_prefix_reused=prefix_new, newly_verified_this_invocation=fresh-prefix_new,
            pool_scope_limitations=dict(global_historical_universe_certified=False,
                unknown_candidate_count=len(pool.get('unknown_candidates', [])),
                selection_complete_within_supplied_universe=pool['selection_complete_within_supplied_universe'],
                original_unknowns_retained_in_pool_receipt=True),
            raw_units='TRADE_RAW_MS_TO_US; MARK_AND_FUNDING_RAW_MS; FUNDING_RATE_UNCONFIRMED',
            availability='EXCLUSIVE_CLOSED_PRICE_BAR_PROXY_NOT_PUBLICATION_OR_RATE_AVAILABILITY_CERTIFICATE')
        code = 0
    except Exception as error:
        report.update(status='FAIL_D050_SELECTED_SOURCE_ACCEPTANCE', reason=str(error), error_type=type(error).__name__)
    finally:
        report.update(actual_exit_code=code, elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_after=resources.status())
        try:
            g.bounded(report['resources_after'])
            need(report['peak_RSS_bytes'] <= budgets['peak_RSS_bytes']
                 and report['elapsed_seconds'] < budgets['wall_seconds'], 'Final RSS/wall bound')
            # Project both JSON outputs before writing a success certificate.
            pending = dict(status=MANIFEST_STATUS, checksummed_source_format_verified=True,
                start_us=START, end_us=END, symbols=report.get('symbols', []),
                market_records=market['market_records'], control_daily_records=market['control_daily_records'],
                pool_receipt=spec['pool_receipt'], source_acceptance={'path': str(output),
                    'sha256': '0'*64, 'required_status': STATUS}) if code == 0 else None
            projected = len(json.dumps(report, ensure_ascii=False, allow_nan=False).encode())
            if pending is not None:
                projected += len(json.dumps(pending, ensure_ascii=False, allow_nan=False).encode())
            need(sum(p.stat().st_size for p in run.rglob('*') if p.is_file())+projected+100_000
                 <= budgets['new_owned_bytes'], 'Small owned output budget with serialization reserve')
        except Exception as error:
            code = 1
            report.update(status='FAIL_D050_SELECTED_SOURCE_ACCEPTANCE', actual_exit_code=1,
                          reason=str(error), error_type=type(error).__name__)
        g.write(output, report)
        if code == 0:
            manifest = dict(status=MANIFEST_STATUS, checksummed_source_format_verified=True,
                start_us=START, end_us=END, symbols=symbols, market_records=market['market_records'],
                control_daily_records=market['control_daily_records'], pool_receipt=spec['pool_receipt'],
                source_acceptance=dict(path=str(output), sha256=sha(output), required_status=STATUS))
            g.write(manifest_path, manifest)
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event, event_id=spec['experiment_id']+':RESULT',
            event_type='OPERATIONAL_SOURCE_AUDIT_RESULT', success_failure=report['status'], actual_exit_code=code,
            report_path=str(output), report_sha256=sha(output)))
        if progress is not None:
            progress.update('独立来源验收退出', len(report['sources']), report.get('completed_files'), '档', actual_exit_code=code)
            progress.stop.set()
    return code


if __name__ == '__main__':
    raise SystemExit(main())
