"""Exact ten-day Git-source repair and training-only refreeze; no new recipe.

Only historical trade closes are admitted. The blocked predecessor, its causal
mask rule, and all published evidence remain unchanged. Minute validation and
daily aggregation reuse the collector's existing pure functions.
"""
import argparse
import io
import json
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from modules.collector_research.pipeline.download import parse_checksum
from modules.collector_research.pipeline.normalize import numeric_csv, validate_price, aggregate_price
from .core import DAY_US, SYMBOLS, FrozenGP, Scaler, sample_index, trend_features
from .diagnose_training import read_training_close
from .run import ROOT, sha, utc_us, write_json, load_close
from .cost_training import ARCHIVE, build_episode, episode_identity

EXPERIMENT = ROOT / 'research/slow-momentum-cpd-cost-data-repair-20261011'
RECOVERY_COMMIT = '49017d88b75498a53f90857fe0d01a622e812a2f'
RECOVERY_BASE = 'research/cached-history-repair-20261010/'
RECOVERY_SHA = '42e59bf2200034f433816fc70b8a2da43eb36363810ba356d8ffdc3ddb7be929'
MANIFEST_SHA = '8191e0e26287ded3c02302b63f9c7f1f90b2396ff04e09385d9bbcf9b2b18ad6'
DAYS = ('2022-02-26', '2022-02-27', '2022-02-28', '2022-04-01', '2022-04-02')


def git_bytes(name):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', RECOVERY_COMMIT + ':' + RECOVERY_BASE + name])


def recovery():
    raw = git_bytes('RECOVERY.zip')
    manifest_raw = git_bytes('MANIFEST.json')
    if sha(raw) != RECOVERY_SHA or len(raw) != 2484855 or sha(manifest_raw) != MANIFEST_SHA:
        raise ValueError('Published recovery identity differs')
    manifest = json.loads(manifest_raw)
    identities = {v['path']: v['SHA256'] for v in manifest['members']}
    z = zipfile.ZipFile(io.BytesIO(raw))
    if len(z.namelist()) != len(set(z.namelist())):
        raise ValueError('Duplicate recovery members')
    return z, identities


def member(z, identities, name):
    raw = z.read(name)
    if sha(raw) != identities[name]:
        raise ValueError('Recovered member identity differs: ' + name)
    return raw


def pre2023_table(raw):
    """Predicate-bound projection; no validation/holdout rows returned."""
    dtype = pq.read_schema(io.BytesIO(raw)).field('dt').type
    if dtype.tz not in (None, 'UTC'):
        raise ValueError('Non-UTC source')
    tz = timezone.utc if dtype.tz else None
    table = pq.read_table(io.BytesIO(raw), columns=['dt', 'close', 'complete_kline', 'symbol'],
        filters=[('dt', '>=', pa.scalar(datetime(2020, 1, 1, tzinfo=tz), type=dtype)),
                 ('dt', '<', pa.scalar(datetime(2022, 12, 31, tzinfo=tz), type=dtype))]).sort_by([('dt', 'ascending')])
    stamps = table['dt'].to_numpy().astype('datetime64[us]').astype('int64')
    if len(stamps) != len(np.unique(stamps)) or np.any(stamps % DAY_US) or np.any(stamps + DAY_US >= utc_us('2023-01-01')):
        raise ValueError('Source clock outside training')
    return table, stamps


def apply_patch(available, close, records):
    result = close.copy()
    if len(records) != 10 or {(r['symbol'], r['bar_start']) for r in records} != {(s, d) for s in ('SOLUSDT', 'XRPUSDT') for d in DAYS}:
        raise ValueError('Repair scope differs')
    for r in records:
        clock = utc_us(r['bar_start']) + DAY_US
        t = np.flatnonzero(available == clock)
        a = SYMBOLS.index(r['symbol'])
        if len(t) != 1 or np.isfinite(result[t[0], a]) or not np.isfinite(r['close']) or r['close'] <= 0:
            raise ValueError('Repair must fill exactly one truly missing training close')
        result[t[0], a] = r['close']
    return result


def recover_prices(state):
    started = time.monotonic()
    z, identities = recovery()
    available, old = read_training_close(ARCHIVE)
    records, overlaps, raw_bytes = [], [], 0
    rawdir = state / 'source' / 'ten-days'
    rawdir.mkdir(parents=True, exist_ok=False)
    try:
        for symbol in ('SOLUSDT', 'XRPUSDT'):
            for day in DAYS:
                base = f'gap-repair/{symbol}_klines_{day}'
                raw = member(z, identities, base + '.zip')
                receipt = json.loads(member(z, identities, base + '.json'))
                name = f'{symbol}-1m-{day}.zip'
                url = f'https://data.binance.vision/data/futures/um/daily/klines/{symbol}/1m/{name}'
                if receipt['url'] != url or receipt['symbol'] != symbol or receipt['day'] != day or receipt['family'] != 'klines' or receipt['status'] != 'CHECKSUM_CRC_VERIFIED':
                    raise ValueError('Recovered official source receipt differs')
                digest = parse_checksum(receipt['checksum_text'], name)
                if digest != sha(raw) or digest != receipt['SHA256'] or len(raw) != receipt['bytes']:
                    raise ValueError('Official checksum differs')
                path = rawdir / name
                path.write_bytes(raw)
                Path(str(path) + '.CHECKSUM').write_text(receipt['checksum_text'])
                with zipfile.ZipFile(path) as minute_zip:
                    if minute_zip.namelist() != [name[:-4] + '.csv'] or minute_zip.testzip() is not None:
                        raise ValueError('Minute ZIP name/CRC differs')
                    csv_hash = sha(minute_zip.read(minute_zip.namelist()[0]))
                lo = utc_us(day) // 1000
                frame, duplicates = validate_price(numeric_csv(path), 'klines', lo, lo + 86400000)
                if duplicates or len(frame) != 1440 or not np.array_equal(frame.timestamp_ms.to_numpy(), np.arange(lo, lo + 86400000, 60000)):
                    raise ValueError('Expected complete unique 1440-minute source grid')
                daily = aggregate_price(frame, 'klines')
                if len(daily) != 1 or not bool(daily.complete.iloc[0]):
                    raise ValueError('Incomplete daily aggregation')
                records.append(dict(symbol=symbol, bar_start=day, close=float(daily.close.iloc[0]),
                    minutes=1440, zip_sha256=digest, zip_bytes=len(raw), csv_sha256=csv_hash,
                    official_url=url, checksum_url=url + '.CHECKSUM', checksum_text=receipt['checksum_text'],
                    checksum_evidence='Recovered exact published official-response receipt; no new HTTP recertification',
                    recovery_member=base + '.zip', recovery_receipt_member=base + '.json'))
                raw_bytes += len(raw)
                print(f'RECOVERED {symbol} {day} 1440/1440 checksum/CRC/grid verified', flush=True)
        patched = apply_patch(available, old, records)
        # Recovered prior derived prices provide exact overlap checks on existing
        # training days, including both sides of each hole. No forward data used.
        for symbol in ('SOLUSDT', 'XRPUSDT'):
            name = f'gap-repair/repaired/economics/{symbol}_daily.parquet'
            table, stamps = pre2023_table(member(z, identities, name))
            if set(table['symbol'].to_pylist()) != {symbol}:
                raise ValueError('Recovered derived symbol differs')
            values = table['close'].to_numpy().astype(float)
            complete = np.asarray(table['complete_kline'].to_pylist(), dtype=bool)
            values[~complete | ~np.isfinite(values) | (values <= 0)] = np.nan
            t = np.searchsorted(available, stamps + DAY_US)
            if np.any(t >= len(available)) or not np.array_equal(available[t], stamps + DAY_US):
                raise ValueError('Recovered daily clock differs')
            a = SYMBOLS.index(symbol)
            good = np.isfinite(old[t, a])
            if not np.array_equal(values[good], old[t[good], a]):
                raise ValueError('Existing observed training daily overlap conflicts')
            if not np.array_equal(values, patched[t, a], equal_nan=True):
                raise ValueError('Ten-day patch does not reproduce prior repaired source')
            adjacent = []
            for day in ('2022-02-25', '2022-03-01', '2022-03-31', '2022-04-03'):
                k = np.flatnonzero(stamps == utc_us(day))
                if len(k) != 1 or not good[k[0]]:
                    raise ValueError('Missing adjacent existing observed overlap')
                adjacent.append(dict(bar_start=day, old_close=float(old[t[k[0]], a]), recovered_close=float(values[k[0]]), exact_equal=True))
            overlaps.append(dict(symbol=symbol, source_member=name, member_sha256=identities[name],
                existing_daily_overlaps=int(good.sum()), exact_equal=True, adjacent=adjacent,
                original_missing_day_minute_overlap='NONE: original source has no complete trade close on declared days; no synthetic overlap'))
        change = ~(np.equal(old, patched) | (np.isnan(old) & np.isnan(patched)))
        if int(change.sum()) != 10:
            raise ValueError('Undeclared price change')
        value = dict(schema='TEN_OBSERVED_TRAINING_CLOSE_REPAIR_V1', status='PASS',
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip(),
            recovery_commit=RECOVERY_COMMIT, recovery_archive_sha256=RECOVERY_SHA,
            recovery_manifest_sha256=MANIFEST_SHA, original_archive_sha256=sha(ARCHIVE.read_bytes()),
            records=records, overlaps=overlaps, old_training_close_sha256=sha(old.astype('<f8').tobytes()),
            repaired_training_close_sha256=sha(patched.astype('<f8').tobytes()),
            changed_prices=10, recovered_raw_zip_bytes=raw_bytes, provider_downloads=0,
            validation_rows_read=0, locked_consumed=False, original_experiment='PRESERVED_BLOCKED_NOT_RUN',
            causal_mask_rule='UNCHANGED; naturally recomputed on restored observations', seconds=time.monotonic()-started)
        write_json(state / 'DATA_REPAIR.json', value)
        return value
    finally:
        z.close()


def prepared(available, close, frozen):
    cutoff = utc_us('2023-01-01')
    if max(frozen['latest_training_label_end_us'], frozen['scaler_latest_available_us']) >= cutoff or frozen['fit']['latest_fit_available_us'] >= cutoff - DAY_US:
        raise ValueError('Future-fitted repaired artifacts')
    gp = FrozenGP(frozen['mean'], frozen['scale'], np.asarray(frozen['stationary_log_parameters']), np.asarray(frozen['change_log_parameters']), np.asarray(frozen['locations']), 21, frozen['fit'])
    trend, returns, vol = trend_features(close)
    features = np.concatenate((trend, gp.transform(returns)), axis=2)
    inputs = Scaler(np.asarray(frozen['scaler_mean']), np.asarray(frozen['scaler_scale'])).transform(features)
    return features, inputs, returns, vol


def training_episode(repair, frozen):
    available, close = read_training_close(ARCHIVE)
    close = apply_patch(available, close, repair['records'])
    if sha(close.astype('<f8').tobytes()) != repair['repaired_training_close_sha256']:
        raise ValueError('Repaired training price identity differs')
    features, inputs, returns, vol = prepared(available, close, frozen)
    ep = build_episode(available, features, inputs, returns, vol, '2021-01-01', '2023-01-01')
    if not np.array_equal(ep['rows'], sample_index(features, returns, vol, available, utc_us('2021-01-01'), utc_us('2023-01-01'))):
        raise ValueError('Causal mask must match every mature finite outcome after actual repair')
    return ep


def refreeze(state):
    if (state / 'REFREEZE_STARTED.json').exists():
        raise FileExistsError('No implicit GP/scaler refit retry')
    write_json(state / 'REFREEZE_STARTED.json', dict(planned_gp_groups=1, planned_optimizer_calls=2, maxiter_each=60, per_asset_windows=64, validation_reads=0))
    repair = json.loads((state / 'DATA_REPAIR.json').read_text())
    if repair['status'] != 'PASS' or repair['recovery_commit'] != RECOVERY_COMMIT or repair['recovery_archive_sha256'] != RECOVERY_SHA or repair['original_archive_sha256'] != sha(ARCHIVE.read_bytes()):
        raise ValueError('Unverified repair source before GP fit')
    available, close = read_training_close(ARCHIVE)
    close = apply_patch(available, close, repair['records'])
    if sha(close.astype('<f8').tobytes()) != repair['repaired_training_close_sha256']:
        raise ValueError('Repaired training price identity differs before GP fit')
    trend, returns, vol = trend_features(close)
    start, end = utc_us('2021-01-01'), utc_us('2023-01-01')
    rows = sample_index(trend, returns, vol, available, start, end)
    gp = FrozenGP.fit(returns, available, start, end, window=21, maxiter=60, per_asset=64)
    features = np.concatenate((trend, gp.transform(returns)), axis=2)
    scaler, used = Scaler.fit(features, rows, sequence=63)
    frozen = dict(mean=gp.mean, scale=gp.scale, stationary_log_parameters=gp.stationary.tolist(),
        change_log_parameters=gp.change.tolist(), locations=gp.locations.tolist(), fit=gp.fit_info,
        scaler_mean=scaler.mean.tolist(), scaler_scale=scaler.scale.tolist(), scaler_unique_rows=int(used.sum()),
        scaler_latest_available_us=int(available[np.flatnonzero(used.any(1))[-1]]), training_samples=len(rows),
        latest_training_label_end_us=int(available[rows[:,0]+1].max()),
        data_repair_sha256=sha((state / 'DATA_REPAIR.json').read_bytes()),
        recipe='Same original capped training GP/scaler; refit because observed data changed; no parameter search')
    write_json(state / 'FROZEN_TRAINING.json', frozen)
    identity = episode_identity(training_episode(repair, frozen))
    identity['reader'] = 'Predicate-bound pre2023; repaired source and newly training-frozen GP/scaler; validation reads0'
    write_json(state / 'CALENDAR.json', identity)
    print(json.dumps(dict(status='REFROZEN', calendar=identity, gp_stationary=gp.fit_info['stationary'], gp_change=gp.fit_info['change'])), flush=True)


def evaluation_blocks(repair, frozen):
    protocol = json.loads((ROOT / 'research/slow-momentum-cpd-20261011/PROTOCOL.json').read_text())
    available, close, source = load_close(ARCHIVE, protocol)
    close = apply_patch(available, close, repair['records'])
    features, inputs, returns, vol = prepared(available, close, frozen)
    blocks = []
    for start, end in protocol['validation']:
        ep = build_episode(available, features, inputs, returns, vol, start, end)
        ep.update(dates=[start, end], position={'trend':[], 'trend_cpd':[]})
        blocks.append(ep)
    return available, returns, vol, blocks, source


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=('recover','refreeze')); p.add_argument('--state', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'recover': recover_prices(a.state)
    else: refreeze(a.state)
