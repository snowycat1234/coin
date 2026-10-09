"""Validate original monthly bytes with the existing pinned normalizer; no fills."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

SOURCE_COMMIT = '0090a7182c75a655197afd85f4db2c66db6456f6'
SOURCE_SHA = {
    'normalize.py': 'ee394086066c96bc23e83b45bf0bc2777264ab4eb57128886394fee47fecd4ff',
    'common.py': '0f24665c50c21fecef4e06f74230bbb113d210d014077068377c67f34fa57390',
    'storage.py': '60384e783bb853fa3c14599f8d863a7fe69efba08889a577c3be3b3d06b8995b',
}
FOLDS = {'JULY2023': ('2023-07-03', '2023-09-04'),
         'OCTOBER2023': ('2023-10-02', '2023-12-04')}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def validate(root, source_root, fold):
    # Bind the actual imported implementation, rather than copy its validation logic.
    pipeline = source_root / 'modules/collector_research/pipeline'
    for name, expected in SOURCE_SHA.items():
        if sha(pipeline / name) != expected:
            raise ValueError(f'Pinned normalizer source mismatch: {name}')
    sys.path.insert(0, str(source_root))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    from modules.collector_research.pipeline.normalize import numeric_csv, validate_price, canonical, month_limits
    import modules.collector_research.pipeline.normalize as imported
    if Path(imported.__file__).resolve() != (pipeline / 'normalize.py').resolve():
        raise ValueError('Unexpected module import path')
    folder = root / fold
    raw_manifest = json.loads((folder / 'RAW_MANIFEST.json').read_text())
    start, end = FOLDS[fold]
    left = pd.Timestamp(start, tz='UTC').value // 1_000_000
    right = pd.Timestamp(end, tz='UTC').value // 1_000_000
    grid = np.arange(left, right, 60000, dtype=np.int64)
    expected_rows = len(grid)
    observed = {}
    receipts = []
    began = time.monotonic()
    for record in raw_manifest['records']:
        path = folder / record['relative_raw_path']
        if path.stat().st_size != record['size'] or sha(path) != record['SHA256']:
            raise ValueError(f'Original checksum failed: {path}')
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Original ZIP CRC failed')
        y, m = map(int, record['month'].split('-'))
        month_left, month_right = month_limits(y, m)
        d, duplicates = validate_price(numeric_csv(path), record['family'], month_left, month_right)
        times = d.timestamp_ms.to_numpy(dtype=np.int64)
        # Independent full-grid comparison: the existing validator permits observed gaps.
        month_grid = np.arange(month_left, month_right, 60000, dtype=np.int64)
        missing = np.setdiff1d(month_grid, times)
        q = canonical(d, record['family'], record['symbol'])
        if not np.array_equal(q.timestamp_ms.to_numpy(), times):
            raise ValueError('Canonical timestamp changed')
        if not np.array_equal(q.available_us.to_numpy(), (times + 60000) * 1000):
            raise ValueError('Invalid completed-minute availability')
        if record['family'] == 'klines':
            if not np.array_equal(q.open_us.to_numpy(), times * 1000):
                raise ValueError('Invalid trade open units')
            if not np.array_equal(q.close_us.to_numpy(), (times + 60000) * 1000):
                raise ValueError('Invalid exclusive trade close')
        if not np.array_equal(q.quote_volume.to_numpy(), d.quote_volume.to_numpy()):
            raise ValueError('Canonical quote volume changed')
        relative = Path('data/normalized/minute') / record['symbol'] / record['family'] / (record['month'] + '.parquet')
        output = folder / 'normalized' / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(q, preserve_index=False), output, compression='zstd')
        roundtrip = pq.read_table(output, use_threads=False).to_pandas(use_threads=False)
        if not q.equals(roundtrip):
            raise ValueError('Parquet values/types differ from canonical frame')
        key = (record['symbol'], record['family'])
        observed.setdefault(key, []).append(times.copy())
        quote = np.asarray(q.quote_volume.to_numpy(), dtype='<f8')
        receipt = dict(symbol=record['symbol'], family=record['family'], month=record['month'],
            original_SHA256=record['SHA256'], rows=len(q), expected_month_rows=len(month_grid),
            missing_month_minutes=len(missing), missing_month_sample_ms=missing[:10].tolist(),
            identical_duplicates_removed=duplicates, first_open_ms=int(times[0]), last_open_ms=int(times[-1]),
            full_month_grid_complete=bool(np.array_equal(times, month_grid)),
            available_us='(original timestamp_ms + 60000) * 1000', quote_volume_unit='USDT',
            quote_volume_preserved_exactly=True, canonical_Parquet_roundtrip_equal=True,
            quote_volume_float64_SHA256=hashlib.sha256(quote.tobytes()).hexdigest(),
            quote_volume_sum=float(quote.sum()), quote_volume_zero_minutes=int((quote == 0).sum()),
            normalized_relative_path=str(relative), normalized_bytes=output.stat().st_size,
            normalized_SHA256=sha(output))
        receipts.append(receipt)
        print(json.dumps({k:receipt[k] for k in ('symbol','family','month','rows','missing_month_minutes')}), flush=True)
        del d, q, roundtrip, quote
        gc.collect()
    folds = []
    for symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'):
        sets = {}
        for family in ('klines', 'markPriceKlines'):
            times = np.concatenate(observed[(symbol, family)])
            selected = times[(times >= left) & (times < right)]
            sets[family] = selected
            missing = np.setdiff1d(grid, selected)
            folds.append(dict(symbol=symbol, family=family, rows=len(selected), expected_rows=expected_rows,
                missing_minutes=len(missing), missing_sample_ms=missing[:10].tolist(),
                complete=bool(np.array_equal(selected, grid)), prior_boundary_minute_present=bool(left-60000 in times)))
        if not np.array_equal(sets['klines'], sets['markPriceKlines']):
            print(json.dumps(dict(symbol=symbol, trade_mark_grids_match=False)), flush=True)
    complete = all(x['complete'] and x['prior_boundary_minute_present'] for x in folds)
    result = dict(schema='CORE5_ORIGINAL_NATIVE_MINUTE_COVERAGE_V1', fold=fold,
        status='VERIFIED_COMPLETE_TRADE_MARK_MINUTE_INPUTS' if complete else 'VALIDATED_OBSERVED_GAPS_REQUIRE_CONSUMER_REVIEW',
        interval_UTC_start_inclusive=start, interval_UTC_end_exclusive=end,
        expected_minutes_per_asset_per_family=expected_rows, symbols_order=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'],
        families=['klines','markPriceKlines'], original_archive_count=len(receipts),
        original_compressed_bytes=raw_manifest['total_original_compressed_bytes'],
        normalization_source_commit=SOURCE_COMMIT, normalization_source_SHA256=SOURCE_SHA,
        no_fill_forward=True, no_synthetic_zero_volume=True, no_funding_or_daily_context_download=True,
        marks_are_original_exchange_mark_prices=True, quote_capacity_source='original klines.quote_volume, USDT; unchanged',
        daily_and_funding_contexts='Must bind existing source-verified contexts separately; this is only minute trade/mark input.',
        normalized_Parquet_files_local_only=True, elapsed_seconds=time.monotonic()-began,
        monthly_receipts=receipts, fold_coverage=folds, model_fits=0, backtests=0)
    dump(folder / 'VALIDATION.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('monthly_receipts','fold_coverage')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--fold', choices=FOLDS, required=True)
    args = parser.parse_args()
    validate(args.root, args.source_root, args.fold)
