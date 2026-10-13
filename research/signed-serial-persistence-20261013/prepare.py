"""Source-only preparation from already saved archives; no network or fitting."""
from __future__ import annotations
import argparse
import io
import json
import subprocess
import time
import zipfile
from pathlib import Path
import numpy as np
import core
from run import HERE, frozen, save, sha

WORKSPACE = HERE.parent
PACKET_SHA = '285528c6c0e204e5d69632a4fdc7dd5ee5f17aeeeaffc2292a5fcea90e10a9ac'
PACKET_BLOB = 'f30e971175325bb2082ed3afaffec7defdf7dd2c'
MEMBERS = {
    'TRAIN.npz': '5716e965d625da08727771906d3a9f998005db7a8bca1795a49d835759b95df6',
    'Y2023.npz': 'f17f2ca6c750df2fd2769ef1eb190a8186e27db6d58b4d6aa573e13f4a672bc4',
    'Y2025.npz': '7a1edfc2dc1f3bad1051f4593f7b0e0dd78369c88574281e74e6e1cccf077646',
}
CERTIFICATE_SHA = 'b8d8d2f471e64a4fd05c307a722dd8c64921fe16989b607da2d24423dd46f46c'
MPS = WORKSPACE / 'coin_native_half_mix_20261013/repo/research/monetary-policy-information-20261012/input/INPUTS.npz'
MPS_SHA = 'e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
YEAR_ROOTS = {
    2023: ('coin_native_half_mix_20261013/prepared_2023', '5c88d0022fe185f966266b54c9962b1e632048817d369e00112f72b2071c7251'),
    2024: ('coin_expanded_coverage_20261013/prepared_2024_cold', '0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69'),
    2025: ('coin_native_half_mix_20261013/prepared_2025', '8a0235e428902f7a0ea4ec1893343abae6ccc23715080771796b54fb58f1f3c4'),
}


def bytes_sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def npz(data, names):
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        return {name: z[name].copy() for name in names}


def packet(path, gitdir):
    if path is not None:
        raw = path.read_bytes()
    else:
        import os
        # Explicitly refuses missing objects; never lazy-fetches or calls providers.
        raw = subprocess.check_output(['git', '--git-dir=' + str(gitdir), 'cat-file', 'blob', PACKET_BLOB],
                                      env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    if len(raw) != 16_834_324 or bytes_sha(raw) != PACKET_SHA:
        raise ValueError('Original public trade-path packet bytes differ')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError('Source packet CRC failure')
        certificate_raw = z.read('PREPARATION.json')
        if bytes_sha(certificate_raw) != CERTIFICATE_SHA:
            raise ValueError('Independent existing real trade-path certification differs')
        certificate = json.loads(certificate_raw)
        if certificate['status'] != 'PASS_REAL_PATH_RV_BV_SOURCE_AND_COMMON_MATURITY':
            raise ValueError('Old packet is not certified genuine trade-path evidence')
        if not certificate['validation']['2023']['warm_previous_endpoint_known'] or not certificate['validation']['2025']['warm_previous_endpoint_known']:
            raise ValueError('Actual genuine validation leading endpoints not certified')
        if certificate['December2022_trade']['status'] != 'PASS_REAL_DECEMBER2022_TRADE_ONLY':
            raise ValueError('Original December training trade-source certification missing')
        selected = {}
        for name, expected in MEMBERS.items():
            data = z.read(name)
            if bytes_sha(data) != expected:
                raise ValueError('Original trade-path member differs: ' + name)
            # No old models, teacher utility, future RV, or previous admission indices.
            selected[name] = npz(data, ('five_close', 'previous_close', 'panel_available_us', 'RV_1m'))
    return selected


def owned_labels(decisions, source):
    clocks = source['decision_us']
    indices = np.searchsorted(clocks, decisions)
    if np.any(indices >= len(clocks)) or not np.array_equal(clocks[indices], decisions):
        raise ValueError('Actual owned OPEN labels missing decision coordinates')
    p0, p1 = source['p0'][indices], source['p1'][indices]
    valid = np.isfinite(p0) & np.isfinite(p1) & (p0 > 0) & (p1 > 0)
    y = np.full(p0.shape, np.nan)
    np.divide(p1, p0, out=y, where=valid)
    y[valid] -= 1
    return y


def verified_month(year, month):
    root_name, expected = YEAR_ROOTS[year]
    root = WORKSPACE / root_name
    if sha(root / 'SOURCE_INDEX.json') != expected:
        raise ValueError('Fixed original source index changed')
    index = json.loads((root / 'SOURCE_INDEX.json').read_text())
    if tuple(index.get('symbol_order', index.get('symbols'))) != core.SYMBOLS:
        raise ValueError('Exact source symbol order required')
    rec = next(row for row in index['months'] if row['month'] == month)
    path = root / 'months' / (month + '.npz')
    if sha(path) != rec['source_NPZ_SHA256'] or path.stat().st_size != rec['source_NPZ_bytes']:
        raise ValueError('Real monthly trade source changed: ' + month)
    with np.load(path, allow_pickle=False) as z:
        times = z['times'].copy()
        close = np.column_stack([z[s + '_close'] for s in core.SYMBOLS])
        opens = np.column_stack([z[s + '_open'] for s in core.SYMBOLS])
    if not (times.dtype.kind in 'iu' and times[0] % core.DAY == 0 and len(times) % 1440 == 0 and
            np.all(np.diff(times) == 60_000_000) and np.isfinite(close).all() and
            np.isfinite(opens).all() and (close > 0).all() and (opens > 0).all()):
        raise ValueError('Exact genuine real trade-minute grid/OHLC required')
    if index.get('original_trade_minute_missing', 0) != 0:
        raise ValueError('Conditional/filled trade prices are not real source')
    return times, close, opens, {'path': str(path.relative_to(WORKSPACE)), 'SHA256': rec['source_NPZ_SHA256']}


def prepare2024():
    _, leading, _, proof0 = verified_month(2023, '2023-11')
    previous = leading[-1]
    months = [verified_month(2023, '2023-12')]
    months += [verified_month(2024, f'2024-{month:02}') for month in range(1, 13)]
    times = np.concatenate([row[0] for row in months])
    close = np.vstack([row[1] for row in months])
    opens = np.vstack([row[2] for row in months])
    if np.any(np.diff(times) != 60_000_000):
        raise ValueError('Warmup/year source continuity failure')
    returns = np.diff(np.log(np.vstack([previous, close])), axis=0)
    rv = np.square(returns).reshape(-1, 1440, 5).sum(1)
    panel = close[4::5].reshape(-1, 288, 5)
    available = times[1439::1440] + 60_000_000
    left = int(np.datetime64('2024-01-01', 'us').astype(np.int64))
    right = int(np.datetime64('2025-01-01', 'us').astype(np.int64))
    d = np.arange(left, right, core.DAY, dtype=np.int64)
    keys = np.searchsorted(times, d + 60_000_000)
    np.testing.assert_array_equal(times[keys], d + 60_000_000)
    p0 = opens[keys]
    _, _, next_open, next_proof = verified_month(2025, '2025-01')
    p1 = np.vstack([p0[1:], next_open[1]])
    y = p1 / p0 - 1
    return dict(five_close=panel, previous_close=previous, panel_available_us=available, RV_1m=rv), d, y, [proof0, *[row[3] for row in months], next_proof]


def main():
    q = argparse.ArgumentParser()
    q.add_argument('--output', type=Path, required=True)
    q.add_argument('--jump-packet', type=Path)
    q.add_argument('--git-dir', type=Path, default=WORKSPACE / 'coin_2022_mark_source_search_20261013/git-metadata')
    args = q.parse_args(); frozen()
    if args.output.exists():
        raise FileExistsError('Fresh source-preparation namespace required')
    began = time.monotonic()
    a = packet(args.jump_packet, args.git_dir)
    if sha(MPS) != MPS_SHA:
        raise ValueError('Actual OPEN training source changed')
    with np.load(MPS, allow_pickle=False) as z:
        labels = {name: z[name].copy() for name in ('decision_us', 'p0', 'p1')}
    econ_path = WORKSPACE / 'coin_cs_sma_recovery_20261013/INPUTS_FINAL/PACKET.zip'
    if sha(econ_path) != '0d2cf51769f2c9444c83b1715c5a6fd730d282e96cc4e84d1feaecf482ffdcd2':
        raise ValueError('Original full-year OPEN packet changed')
    with zipfile.ZipFile(econ_path) as z:
        economic = {year: npz(z.read(f'Y{year}.npz'), ('decision_us', 'p0', 'p1')) for year in (2023, 2025)}
    arrays, reports = {}, {}
    train_d = np.arange(core.START, core.FIT_AT, core.DAY, dtype=np.int64)
    sources = {'TRAIN': (a['TRAIN.npz'], train_d, owned_labels(train_d, labels))}
    for year in (2023, 2025):
        np.testing.assert_array_equal(economic[year]['decision_us'], core.annual_grid(year))
        sources[f'Y{year}'] = (a[f'Y{year}.npz'], economic[year]['decision_us'], owned_labels(economic[year]['decision_us'], economic[year]))
    source24, d24, y24, proofs = prepare2024()
    sources['Y2024'] = (source24, d24, y24)
    for name in ('TRAIN', 'Y2023', 'Y2024', 'Y2025'):
        source, d, y = sources[name]
        p, prev, t = source['five_close'], source['previous_close'], source['panel_available_us']
        real = np.isfinite(p) & (p > 0)
        # Packet projections carry certified genuine trade paths, not interpolated marks.
        x, reason = core.make_features(p, prev, t, real, source['RV_1m'], d, np.isfinite(prev) & (prev > 0))
        mature = d + 2 * core.DAY
        arrays[name] = dict(decision_us=d, features=x, target_return=y, label_mature_us=mature, readiness_reason=reason)
        common = np.isfinite(x).all((1, 2)) & np.isfinite(y).all(1)
        reports[name] = dict(natural_dates=len(d), input_ready_dates=int(np.isfinite(x).all((1, 2)).sum()),
                             common_price_label_dates=int(common.sum()), input_unknown_decisions=d[~np.isfinite(x).all((1, 2))].tolist(),
                             price_label_unknown_decisions=d[~np.isfinite(y).all(1)].tolist())
        if name == 'TRAIN':
            mask = core.training_mask(d, x, y, mature)
            reports[name].update(actual_mature_train_dates=int(mask.sum()), mature_train_decisions=d[mask].tolist(),
                                 maximum_train_maturity_us=int(mature[mask].max()), purge_decisions=d[mature >= core.FIT_AT].tolist())
    if time.monotonic() - began > 120:
        raise RuntimeError('Source preparation exceeded frozen time budget')
    args.output.mkdir(parents=True)
    for name, values in arrays.items():
        np.savez_compressed(args.output / (name + '.npz'), **values)
    outputs = {name + '.npz': sha(args.output / (name + '.npz')) for name in arrays}
    save(args.output / 'PREPARATION.json', dict(status='SOURCE_ONLY_NO_FITS_SCORES_WALLETS', cohorts=reports,
         freeze_SHA256=sha(HERE / 'FROZEN.json'), outputs_SHA256=outputs, jump_packet_SHA256=PACKET_SHA,
         jump_members_SHA256=MEMBERS, actual_OPEN_training_SHA256=MPS_SHA, fullyear_OPEN_packet_SHA256=sha(econ_path),
         old_real_trade_path_certificate_SHA256=CERTIFICATE_SHA,
         real_source_authority='Pinned source-only jump preparation certificate and original canonical trade/ZIP SHA chains; finite prices alone do not certify reality',
         Y2024_source_proofs=proofs, seconds=time.monotonic()-began, providers=0, fits=0, wallets=0))
    print(json.dumps(reports), flush=True)


if __name__ == '__main__':
    main()
