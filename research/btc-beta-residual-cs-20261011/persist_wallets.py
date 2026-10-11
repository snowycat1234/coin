"""Lossless audit-column storage; original full producer files stay untouched."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import polars as pl

from restore_minutes import SYMBOLS, disk_budget, save, sha

AUDIT_COLUMNS = ['nav', 'free_cash', 'isolated_balance', 'cumulative_fees',
                 'cumulative_execution_costs', 'cumulative_funding',
                 *[s + '_quantity' for s in SYMBOLS],
                 *[s + '_signed_marked_notional' for s in SYMBOLS], 'close_us']


def encode_column(column):
    v = column.to_numpy()
    if v.dtype not in (np.dtype('float64'), np.dtype('int64')) or not np.isfinite(v).all():
        raise ValueError('Exact 64bit finite audit columns only')
    v = np.ascontiguousarray(v.astype(v.dtype.newbyteorder('<'), copy=False))
    raw = v.tobytes()
    planes = np.frombuffer(raw, dtype=np.uint8).reshape(len(v), 8).T.copy().tobytes()
    return dict(name=column.name, dtype=v.dtype.str, rows=len(v), raw_SHA256=sha(raw)), planes


def decode_column(spec, planes):
    if len(planes) != spec['rows'] * 8:
        raise ValueError('Audit column byte count')
    raw = np.frombuffer(planes, dtype=np.uint8).reshape(8, spec['rows']).T.copy().tobytes()
    if sha(raw) != spec['raw_SHA256']:
        raise ValueError('Lossless column SHA')
    return np.frombuffer(raw, dtype=np.dtype(spec['dtype'])).copy()


def pack(state, destination):
    source = state / 'economics'
    packet = state / 'AUDIT_WALLETS.zip'
    destination.mkdir()
    cases = [p for p in sorted(source.iterdir()) if p.is_dir()]
    if len(cases) != 4:
        raise ValueError('All four actual independent cases required')
    members = []
    views = []
    with zipfile.ZipFile(packet, 'x', compression=zipfile.ZIP_LZMA) as z:
        def add(name, raw):
            z.writestr(name, raw)
            members.append(dict(name=name, bytes=len(raw), SHA256=sha(raw)))
        for case in cases:
            full_path = case / 'minute_nav_inventory.parquet'
            full = pl.read_parquet(full_path)
            specs = []
            for column in AUDIT_COLUMNS:
                spec, planes = encode_column(full[column])
                specs.append(spec)
                add(case.name + '/minute_columns/' + column + '.planes', planes)
            scope = dict(case=case.name, rows=full.height, stored_columns=specs,
                         original_full_parquet_SHA256=sha(full_path.read_bytes()),
                         original_full_parquet_bytes=full_path.stat().st_size,
                         omitted_producer_columns=[c for c in full.columns if c not in AUDIT_COLUMNS],
                         scope='17 exact original audit columns, all original journals/summary/daily/targets; full37column Parquet not republished. No financial recompute/rounding, not original Parquet byte reconstruction')
            add(case.name + '/AUDIT_VIEW.json', json.dumps(scope, indent=2).encode())
            views.append(scope)
            for p in sorted(case.iterdir()):
                if p != full_path:
                    add(case.name + '/' + p.name, p.read_bytes())
            print('Saved lossless audit view and full journals', case.name, flush=True)
        for p in sorted(source.iterdir()):
            if p.is_file():
                add(p.name, p.read_bytes())
    raw = packet.read_bytes()
    public_bytes = sum(p.stat().st_size for p in destination.parent.rglob('*') if p.is_file())
    if len(raw) + public_bytes > 20000000:
        raise ValueError('Frozen public result20MB budget; original files retained, no partial publication')
    parts = []
    for k, offset in enumerate(range(0, len(raw), 786432)):
        piece = raw[offset:offset + 786432]
        name = f'AUDIT_WALLETS.zip.part{k:04}'
        with (destination / name).open('xb') as f:
            f.write(piece)
        parts.append(dict(name=name, bytes=len(piece), SHA256=sha(piece)))
    save(destination / 'INDEX.json', dict(schema='LOSSLESS_ORIGINAL_AUDIT_COLUMNS_AND_FULL_JOURNALS_V1',
                                        packet_bytes=len(raw), packet_SHA256=sha(raw), parts=parts, members=members,
                                        cases=[dict(case=v['case'], rows=v['rows'],
                                                    original_full_parquet_SHA256=v['original_full_parquet_SHA256'],
                                                    omitted_producer_columns=v['omitted_producer_columns']) for v in views],
                                        wallet_reruns=0, fits=0, original_state_untouched=True,
                                        projection_reason='Frozen public20MB budget; redundant exposure/equity columns retained only in original STATE. Exact signed NAV/cash/collateral/cost/funding/quantity/notional columns suffice for mature independent audit'))
    disk_budget(state)
    print('PACKET', len(raw), sha(raw), 'parts', len(parts), flush=True)


def restore(packet, output):
    output.mkdir()
    with zipfile.ZipFile(packet) as z:
        if z.testzip() is not None:
            raise ValueError('Artifact ZIP CRC')
        views = []
        for name in z.namelist():
            if name.endswith('/AUDIT_VIEW.json'):
                views.append(json.loads(z.read(name)))
            elif '/minute_columns/' not in name:
                path = output / name
                if not path.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Artifact path traversal')
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as f:
                    f.write(z.read(name))
        for view in views:
            columns = {}
            for spec in view['stored_columns']:
                name = view['case'] + '/minute_columns/' + spec['name'] + '.planes'
                columns[spec['name']] = decode_column(spec, z.read(name))
            pl.DataFrame(columns).write_parquet(output / view['case'] / 'minute_nav_inventory.parquet', compression='zstd')
            save(output / view['case'] / 'AUDIT_VIEW.json', view)
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    if not a.state.resolve().is_relative_to(Path('/workspace')) or not a.destination.resolve().is_relative_to(Path('/workspace')):
        raise ValueError('Authorized workspace only')
    pack(a.state.resolve(), a.destination.resolve())


if __name__ == '__main__':
    main()
