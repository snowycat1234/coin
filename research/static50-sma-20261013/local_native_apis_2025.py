"""Transport-only local port of frozen native_apis for this partial checkout.

All financial kernel, account, checkpoint, and target files remain exact Git bytes.
The original repo's import chain assumes a full historical checkout and source
STATE; this port resolves the verified local source cache directly.
"""
import hashlib
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOCAL = ROOT.parent
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
DAY = 86400000000

os.environ.setdefault('QUANT_ROOT', str(ROOT))
os.environ.setdefault('QUANT_STATE', str(LOCAL))
os.environ.setdefault('CONFIG_FILE', '/dev/null')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# This is the exact symbol-order guard from public_sma_perpetual.py. No strategy
# default target factory is reachable: the frozen wallet supplies COMBINED.
strategy = types.ModuleType('scripts.investment.public_sma_perpetual')
strategy.SYMBOLS = ('BTCUSDT', 'ETHUSDT')
strategy.MODES = ('LONG_ONLY', 'SHORT_ONLY', 'LONG_SHORT', 'CASH')


def symbol_order(symbols):
    names = tuple(symbols)
    if not bool(names) or len(names) != len(set(names)) or not all(
        isinstance(s, str) and s.isascii() and s.isalnum() and s.endswith('USDT')
        for s in names
    ):
        raise ValueError('Unique explicit ordered USDT symbols required')
    return names


def no_default(*args, **kwargs):
    raise RuntimeError('Frozen COMBINED target factory required')


strategy.symbol_order = symbol_order
strategy.fixed_targets = no_default
sys.modules[strategy.__name__] = strategy

from scripts.investment import resumable_perpetual as scheduler
from scripts.investment import perpetual_directional as direction

grid = load('exact_quantity_grid_account', ROOT / 'research/quantity-grid-sensitivity-20261012/grid_account.py')
state_io = load('exact_continuous_state_io', ROOT / 'research/cs-continuous-economics-20261012/state_io.py')
activity = load('exact_short_activity_audit', ROOT / 'research/short-native-activity-20261012/activity.py')

Closing = grid.QuantityGridAccount
profile_sha = grid.profile_sha
checkpoint = state_io.checkpoint
restore_snapshot = state_io.restore_snapshot
native = types.SimpleNamespace(
    pl=pl,
    NativeDailySimulator=scheduler.NativeDailySimulator,
    COSTS=direction.COSTS,
    UNITS=direction.UNITS,
    episodes=activity.episodes,
    nav_bridge=activity.nav_bridge,
    rejection_counts=activity.rejection_counts,
)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def prepared(key):
    assert key in ('Y2023', 'Y2025')
    return LOCAL / ('prepared_2023' if key == 'Y2023' else 'prepared_2025')


def verify():
    manifest = json.loads((HERE / 'LOCAL_CODE_MANIFEST_2025.json').read_text())
    for path, expected in manifest['sha256'].items():
        assert file_sha(ROOT / path) == expected, path
    assert profile_sha() == '94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf'


def window(key):
    ready = json.loads((HERE / 'input/READINESS.json').read_text())
    path = prepared(key)
    index_path = path / 'SOURCE_INDEX.json'
    assert file_sha(index_path) == ready['years'][key]['source_index_SHA256']
    index = json.loads(index_path.read_text())
    assert index['calendar'] == ([1672531200000000, 1704067200000000] if key == 'Y2023'
                                 else [1735689600000000, 1767225600000000])
    assert index['days'] == 365 and index['symbol_order'] == list(SYMBOLS)
    assert index['funding_events'] == 5475
    assert sum(month['minutes'] for month in index['months']) == 525600
    if key == 'Y2023':
        assert index['minutes_per_asset'] == 525600
    else:
        assert 'minutes_per_asset' not in index  # Frozen 2025 index omits this aggregate.
    for name in ('EVENTS.json', 'DAILY.json'):
        record = index['files'][name]
        assert file_sha(path / name) == record['SHA256'] and (path / name).stat().st_size == record['bytes']
    events = json.loads((path / 'EVENTS.json').read_text())
    daily = pl.DataFrame(json.loads((path / 'DAILY.json').read_text()))
    assert len(events) == 5475 and daily.height == 1825

    def blocks():
        for record in index['months']:
            month_path = path / 'months' / (record['month'] + '.npz')
            assert file_sha(month_path) == record['source_NPZ_SHA256']
            assert month_path.stat().st_size == record['source_NPZ_bytes']
            with np.load(month_path, allow_pickle=False) as archive:
                times = archive['times']
                market = {symbol: {field: archive[symbol + '_' + field]
                    for field in ('open', 'close', 'quote_volume', 'mark')}
                    for symbol in SYMBOLS}
            for offset in range(0, len(times), 1440):
                yield dict(times=times[offset:offset + 1440],
                           market={symbol: {field: values[offset:offset + 1440]
                               for field, values in fields.items()}
                               for symbol, fields in market.items()})

    return dict(start=index['calendar'][0], end=index['calendar'][1], symbols=SYMBOLS,
                daily=daily, events=events, minute_blocks=blocks)


def fingerprint(frame):
    return [dict(name=column, dtype=frame[column].to_numpy().dtype.str,
                 rows=frame.height, raw_SHA256=hashlib.sha256(frame[column].to_numpy().tobytes()).hexdigest())
            for column in frame.columns]
