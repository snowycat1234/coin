"""Frozen arithmetic mix of two already-sized saved CORE5 target matrices."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np

DAY = 86_400_000_000
YEARS = (2023, 2025)
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
ARMS = ('STATIC50', 'SMA200', 'COMBINED')
SOURCE_HASHES = {
    'STATIC50_Y2023.npz': 'e81bf92d3599a6d3059ab462ac984ed9cc066647b1ea839d6147d2e10c40359f',
    'STATIC50_Y2025.npz': '5e525cf65a5519a739d7ce2baf9c83809af44a1b9722f37fcf9891ede79bbf4e',
    'SMA200_Y2023.npz': '2047463e7be0ea4f086de744018d65924568dbd2e37f5960e75951c32746abf7',
    'SMA200_Y2025.npz': '595425c86df274c6c6105d058d478d772c75ae75cb9c6d2c3ca8c5b9b4c1d968',
}
INDEX_SHA256 = '8be37f83514967123e1548a68e4266bd83d4da7ca51eb9950e70cf0848bfbaa1'
INPUT_HASHES = {2023: '1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f',
                2025: '88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')


def save_npz(path, **arrays):
    """Deterministic archive with no object or executable payload."""
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for key in sorted(arrays):
            a = np.asarray(arrays[key])
            if a.dtype.hasobject:
                raise ValueError('Object arrays prohibited')
            buf = io.BytesIO()
            np.lib.format.write_array(buf, a, allow_pickle=False)
            item = zipfile.ZipInfo(key + '.npy', date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o600 << 16
            archive.writestr(item, buf.getvalue())


def calendar(year):
    first = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1_000_000)
    return first + np.arange(365, dtype=np.int64) * DAY


def check_packet(packet, year, names):
    if set(packet) != set(names):
        raise ValueError('Source packet schema differs')
    if not np.array_equal(packet['decision_us'], calendar(year)):
        raise ValueError('Missing or misordered UTC decision calendar')
    if tuple(packet['symbol_order']) != SYMBOLS:
        raise ValueError('CORE5 symbol order differs')


def check_weights(w):
    w = np.asarray(w)
    if w.shape != (365, 5) or w.dtype != np.float64 or not np.isfinite(w).all():
        raise ValueError('Finite 365xCORE5 float64 weights required')
    if np.max(np.abs(w)) > .30 + 1e-12 or np.max(np.sum(np.abs(w), axis=1)) > .60 + 1e-12:
        raise ValueError('Original single-asset/gross cap violated')


def mix_day(static, sma, covariance):
    a, b, c = map(lambda x: np.asarray(x, dtype=np.float64), (static, sma, covariance))
    if a.shape != (5,) or b.shape != (5,) or c.shape != (5, 5) or not all(np.isfinite(x).all() for x in (a, b, c)):
        raise ValueError('Finite ordered CORE5 day required')
    if not np.allclose(c, c.T, rtol=0, atol=1e-12) or np.linalg.eigvalsh(c).min() < -1e-10:
        raise ValueError('PSD symmetric annual covariance required')
    for w in (a, b):
        if np.abs(w).max() > .30 + 1e-12 or np.abs(w).sum() > .60 + 1e-12:
            raise ValueError('Original component cap violated')
    w = .5*a + .5*b
    if not np.array_equal(w, .5*a + .5*b):
        raise AssertionError('Literal half-sum changed')
    if np.abs(w).max() > .30 + 1e-12 or np.abs(w).sum() > .60 + 1e-12:
        raise AssertionError('Convex caps changed')
    def sigma(x):
        v = float(x @ c @ x)
        if v < -1e-10:
            raise ValueError('Negative annual variance')
        return float(np.sqrt(max(0., v)))
    sa, sb, sw = sigma(a), sigma(b), sigma(w)
    if sw > .5*(sa+sb) + 1e-10 or sw > max(sa, sb) + 1e-10:
        raise AssertionError('PSD triangle inequality failed')
    return w, dict(static_annual_sigma=sa, sma_annual_sigma=sb, mix_annual_sigma=sw,
                   static_gross=float(np.abs(a).sum()), sma_gross=float(np.abs(b).sum()),
                   mix_gross=float(np.abs(w).sum()), signed_cancellation_gross=float(.5*(np.abs(a).sum()+np.abs(b).sum())-np.abs(w).sum()),
                   mix_cash=bool(np.abs(w).sum() == 0))


def mix_arrays(static, sma, covariance):
    a, b, c = map(np.asarray, (static, sma, covariance))
    if a.shape != (365, 5) or b.shape != a.shape or c.shape != (365, 5, 5):
        raise ValueError('Full matching source arrays required')
    rows = [mix_day(a[i], b[i], c[i]) for i in range(365)]
    w = np.stack([row[0] for row in rows])
    return w, [row[1] for row in rows]


def load_originals(source_root, year):
    root = Path(source_root)
    if sha256(root / 'INDEX.json') != INDEX_SHA256:
        raise ValueError('Immutable four-source index identity mismatch')
    index = json.loads((root / 'INDEX.json').read_text())
    packets = {}
    for kind in ('STATIC50', 'SMA200'):
        name = f'{kind}_Y{year}.npz'
        expected = SOURCE_HASHES[name]
        if index['files'][name]['SHA256'] != expected or sha256(root / name) != expected:
            raise ValueError('Original NPZ byte identity mismatch: ' + name)
        packets[kind] = read_npz(root / name)
    check_packet(packets['STATIC50'], year,
                 ('decision_us','symbol_order','annual_covariance','CS_MATCHED','VOL_MATCHED','STATIC50'))
    check_packet(packets['SMA200'], year,
                 ('decision_us','symbol_order','SMA200_10PCT','direction','mean200','completed_close'))
    for key in ('STATIC50','CS_MATCHED','VOL_MATCHED'):
        check_weights(packets['STATIC50'][key])
    check_weights(packets['SMA200']['SMA200_10PCT'])
    c = packets['STATIC50']['annual_covariance']
    if c.shape != (365, 5, 5) or not np.isfinite(c).all():
        raise ValueError('Finite full annual covariance required')
    return packets
