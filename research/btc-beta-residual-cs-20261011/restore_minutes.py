"""Verify existing Git packet and recover one predeclared real execution window."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMIT = '94fe13c494c82bb6e6868e6614eb7298fb15b3c3'
PACKET_DIR = 'research/core5-2021-economic-data/Y2021/'
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
START = 1617580800000000
END = 1623024000000000
MINUTE = 60000000
DAY = 86400000000


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save(p, x):
    raw = json.dumps(x, indent=2, allow_nan=False)
    with p.open('x') as f:
        f.write(raw + '\n')


def disk_budget(state):
    size = sum(p.stat().st_size for p in state.rglob('*') if p.is_file())
    if size > 1000000000 or shutil.disk_usage(state).free < 16106127360:
        raise RuntimeError('Frozen STATE/disk budget exceeded')


def recover(state, features):
    os.environ['QUANT_ROOT'] = str(ROOT)
    os.environ['QUANT_STATE'] = str(state)
    from modules.collector_research.pipeline.normalize import numeric_csv, validate_price, month_limits
    index_raw = subprocess.check_output(['git', 'show', COMMIT + ':' + PACKET_DIR + 'INDEX.json'], cwd=ROOT)
    index = json.loads(index_raw)
    (state / 'minute-source').mkdir()
    source = state / 'minute-source'
    (source / 'INDEX.json').write_bytes(index_raw)
    packet = source / 'originals.zip'
    h = hashlib.sha256()
    with packet.open('xb') as out:
        for k, part in enumerate(index['parts']):
            raw = subprocess.check_output(['git', 'show', COMMIT + ':' + PACKET_DIR + part['name']], cwd=ROOT)
            if len(raw) != part['bytes'] or sha(raw) != part['SHA256']:
                raise ValueError('Existing Git part mismatch')
            out.write(raw)
            h.update(raw)
            if (k + 1) % 40 == 0:
                disk_budget(state)
                print('Verified Git packet parts', k + 1, '/', len(index['parts']), flush=True)
    if packet.stat().st_size != index['package_bytes'] or h.hexdigest() != index['package_SHA256']:
        raise ValueError('Outer Git packet mismatch')
    members = {r['name']: r for r in index['members']}
    expected = np.arange(START, END, MINUTE, dtype=np.int64)
    arrays = {'times': expected}
    proofs = []
    with zipfile.ZipFile(packet) as z:
        for symbol in SYMBOLS:
            values = {k: [] for k in ('open', 'close', 'quote_volume', 'mark')}
            for month in (4, 5, 6):
                for family in ('klines', 'markPriceKlines'):
                    name = f'raw/{family}/{symbol}/{symbol}-1m-2021-{month:02}.zip'
                    raw = z.read(name)
                    checksum = z.read(name + '.CHECKSUM')
                    for n, b in ((name, raw), (name + '.CHECKSUM', checksum)):
                        if len(b) != members[n]['bytes'] or sha(b) != members[n]['SHA256']:
                            raise ValueError('Official retained member mismatch')
                    fields = checksum.decode().strip().split()
                    if len(fields) != 2 or fields[0] != sha(raw) or fields[1].lstrip('*') != Path(name).name:
                        raise ValueError('Official CHECKSUM binding')
                    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
                        if inner.testzip() is not None:
                            raise ValueError('Original official ZIP CRC')
                    path = source / Path(name).name
                    # Trade/mark share basename; only one temporary original at a time.
                    with path.open('xb') as f:
                        f.write(raw)
                    left, right = month_limits(2021, month)
                    d, duplicates = validate_price(numeric_csv(path), family, left, right)
                    path.unlink()
                    kept = d.loc[(d.timestamp_ms * 1000 >= START) & (d.timestamp_ms * 1000 < END)]
                    grid = kept.timestamp_ms.to_numpy(dtype=np.int64) * 1000
                    required = expected[(expected >= left * 1000) & (expected < right * 1000)]
                    if not np.array_equal(grid, required):
                        raise ValueError('Complete real minutes required; no gap repair/imputation')
                    if family == 'klines':
                        for k in ('open', 'close', 'quote_volume'):
                            values[k].append(kept[k].to_numpy(dtype=np.float64))
                    else:
                        values['mark'].append(kept['close'].to_numpy(dtype=np.float64))
                    proofs.append(dict(name=name, SHA256=sha(raw), official_checksum_verified=True,
                                       CRC_verified=True, observed_rows=len(d), window_rows=len(kept), duplicates=duplicates))
            for k, blocks in values.items():
                arrays[symbol + '_' + k] = np.concatenate(blocks)
                if len(arrays[symbol + '_' + k]) != len(expected):
                    raise ValueError('Minute vector size')
            print('Recovered actual trade/mark minutes', symbol, len(expected), flush=True)
    np.savez_compressed(source / 'WINDOW_MARKET.npz', **arrays)
    # Only settled historical rate/time/interval columns, no future feature or price columns.
    if sha(features.read_bytes()) != 'bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30':
        raise ValueError('Frozen feature archive mismatch')
    events = []
    with zipfile.ZipFile(features) as z:
        manifest = json.loads(z.read('MEMBERS.json'))['files']
        names = z.namelist()
        for symbol in SYMBOLS:
            candidates = [n for n in names if symbol in n and n.endswith('_funding_events.parquet')]
            if len(candidates) != 1:
                raise ValueError('Unique original settled funding table required: ' + symbol + str(candidates))
            name = candidates[0]
            raw = z.read(name)
            if sha(raw) != manifest[name]['SHA256']:
                raise ValueError('Funding table source mismatch')
            schema = pq.read_schema(io.BytesIO(raw))
            print('Funding source schema', name, schema.names, flush=True)
            # Archive canonical event columns are explicitly mapped, never inferred units.
            columns = ['calc_time_ms', 'last_funding_rate', 'funding_interval_hours']
            tab = pq.read_table(io.BytesIO(raw), columns=columns,
                                filters=[('calc_time_ms', '>=', START // 1000), ('calc_time_ms', '<', END // 1000)])
            rows = tab.to_pylist()
            clocks = [int(r['calc_time_ms']) * 1000 for r in rows]
            if len(set(clocks)) != len(clocks) or not clocks:
                raise ValueError('Unique observed funding events')
            for r, t in zip(rows, clocks):
                rate = float(r['last_funding_rate'])
                if not np.isfinite(rate):
                    raise ValueError('Observed finite signed funding')
                events.append(dict(symbol=symbol, event_us=t, raw_rate=rate,
                                   reported_interval_hours=float(r['funding_interval_hours'])))
            proofs.append(dict(name=name, SHA256=sha(raw), window_events=len(rows),
                               projected_columns=columns, exact_charge_mark_certified=False))
    events.sort(key=lambda r: (r['event_us'], SYMBOLS.index(r['symbol'])))
    save(source / 'FUNDING_EVENTS.json', events)
    save(source / 'RECOVERY.json', dict(status='PASS_REAL_GIT_WINDOW_RESTORATION', source_commit=COMMIT,
                                       packet_sha256=h.hexdigest(), packet_bytes=packet.stat().st_size,
                                       parts_verified=len(index['parts']), proofs=proofs,
                                       window=[START, END], required_minutes=len(expected), symbols=SYMBOLS,
                                       funding_events=len(events), provider_downloads=0, imputed_rows=0,
                                       wallet_runs=0, development_reads=0))
    save(source / 'DERIVED_BINDING.json', dict(
        recovery_sha256=sha((source / 'RECOVERY.json').read_bytes()),
        derived_file_sha256={n: sha((source / n).read_bytes()) for n in ('WINDOW_MARKET.npz', 'FUNDING_EVENTS.json')}))
    disk_budget(state)
    return source


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--features', type=Path, required=True)
    a = p.parse_args()
    if not a.state.resolve().is_relative_to(Path('/workspace')):
        raise ValueError('Task STATE only')
    recover(a.state.resolve(), a.features.resolve())


if __name__ == '__main__':
    main()
