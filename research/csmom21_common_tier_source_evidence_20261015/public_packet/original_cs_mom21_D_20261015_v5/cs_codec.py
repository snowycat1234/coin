"""Shared pure generated/actual source codecs; no filename/provider API."""
from io import BytesIO
import ast
import importlib.util
from pathlib import Path
import stat
from types import MappingProxyType
import zipfile

import numpy as np

import cs_common as c
from cs_config import period_named, DAY
from cs_signal import SYMBOLS as S

MINUTE = 60_000_000
FIELDS = ('open', 'close', 'quote_volume', 'mark')
_MARK2024 = None


def frozen_array(a):
    a = np.asarray(a)
    if a.dtype.hasobject:
        raise ValueError('NO_OBJECT_ARRAYS')
    return np.frombuffer(a.tobytes(order='C'), dtype=a.dtype).reshape(a.shape)


def npz(raw, specs, *, allow_unselected=False):
    """Bound and validate selected NPY headers before allocating a payload."""
    if type(raw) is not bytes or type(allow_unselected) is not bool:
        raise ValueError('EXACT_NUMERIC_CONTAINER_BYTES_REQUIRED')
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            infos = archive.infolist(); names = [row.filename for row in infos]
            selected = {key + '.npy' for key in specs}
            if (len(names) != len(set(names)) or not selected <= set(names)
                    or not allow_unselected and selected != set(names)):
                raise ValueError('EXACT_ARRAY_MEMBER_NAMESPACE_REQUIRED')
            for info in infos:
                if (info.is_dir() or info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16)
                        or '/' in info.filename or '\\' in info.filename or not info.filename.endswith('.npy')):
                    raise ValueError('ORDINARY_FLAT_NUMERIC_MEMBERS_REQUIRED')
                if info.filename not in selected:
                    continue  # Never decompress unrelated stored DEV members.
                key = info.filename[:-4]; shape, dtype_spec = specs[key]
                if info.file_size > 8 * 1024 * 1024:
                    raise ValueError('BOUNDED_NUMERIC_MEMBER_REQUIRED')
                with archive.open(info) as stream:
                    version = np.lib.format.read_magic(stream)
                    if version not in ((1, 0), (2, 0)):
                        raise ValueError('SUPPORTED_NPY_HEADER_REQUIRED')
                    reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
                    actual_shape, fortran, dtype = reader(stream, max_header_size=4096)
                    valid_dtype = (dtype.kind == 'U' and 0 < dtype.itemsize <= 128
                                   if dtype_spec == 'SYMBOLS' else dtype == np.dtype(dtype_spec))
                    if actual_shape != shape or dtype.hasobject or fortran or not valid_dtype:
                        raise ValueError('EXACT_NUMERIC_HEADER_SCHEMA_REQUIRED')
                    if stream.tell() + int(np.prod(shape)) * dtype.itemsize != info.file_size:
                        raise ValueError('EXACT_NUMERIC_PAYLOAD_LENGTH_REQUIRED')
        with np.load(BytesIO(raw), allow_pickle=False) as arrays:
            return {key: frozen_array(arrays[key]) for key in specs}
    except (zipfile.BadZipFile, EOFError, OSError) as exc:
        raise ValueError('VALID_NUMERIC_ARCHIVE_REQUIRED') from exc


STORED_DAILY = {
    2021: (1463, 1577923200000000, 1704240000000000),
    2022: (564, 1623801600000000, 1672444800000000),
    2023: (565, 1655337600000000, 1704067200000000),
    2024: (566, 1686873600000000, 1735689600000000),
    2025: (200, 1718496000000000, 1735689600000000),
}


def daily_inputs(year, warm_raw, daily_raw=None):
    period = period_named(year); rows, first, last = STORED_DAILY[year]
    specs = {'close_available_us': ((rows,), 'int64'), 'close': ((rows, 5), 'float64')}
    if year in (2021, 2022):
        specs['symbol_order'] = ((5,), 'SYMBOLS')
    a = npz(warm_raw, specs, allow_unselected=year == 2021)
    times, close = a['close_available_us'], a['close']
    if (times[0] != first or times[-1] != last
            or not np.array_equal(times, np.arange(first, last + DAY, DAY, dtype=np.int64))
            or 'symbol_order' in a and tuple(a['symbol_order']) != S):
        raise ValueError('EXACT_ORIGINAL_YEAR_DAILY_CLOCK_AND_SYMBOL_NAMESPACE_REQUIRED')
    if year == 2021:
        permitted = (times >= 1592265600000000) & (times <= period['end'])
        # This mask occurs before any numeric source/strategy statistic.
        times, close = times[permitted], close[permitted]
    if year == 2025:
        if daily_raw is None:
            raise ValueError('EXACT_2025_DAILY_GRID_REQUIRED')
        daily = c.object_json(daily_raw)
        if type(daily) is not list or len(daily) != period['days'] * 5:
            raise ValueError('EXACT_DAILY_CORE5_ROW_COUNT_REQUIRED')
        by = {}
        for row in daily:
            if (type(row) is not dict or set(row) != {'symbol', 'close_us', 'close'}
                    or row['symbol'] not in S or type(row['close_us']) is not int
                    or type(row['close']) not in (int, float) or not np.isfinite(row['close']) or row['close'] <= 0
                    or not period['start'] <= row['close_us'] < period['end'] or row['close_us'] % DAY):
                raise ValueError('EXACT_DAILY_CORE5_ROW_SCHEMA_REQUIRED')
            key = row['close_us'], row['symbol']
            if key in by:
                raise ValueError('DUPLICATE_DAILY_SOURCE_CELL')
            by[key] = float(row['close'])
        d = np.arange(period['start'], period['end'], DAY, dtype=np.int64)
        if set(by) != {(int(at), symbol) for at in d for symbol in S}:
            raise ValueError('COMPLETE_DAILY_CORE5_GRID_REQUIRED')
        values = np.asarray([[by[int(at), symbol] for symbol in S] for at in d], dtype=np.float64)
        if close[-1].tobytes() != values[0].tobytes():
            raise ValueError('EXACT_WARMUP_FIRST_DECISION_NATIVE_CLOSE_PARITY_REQUIRED')
        times, close = np.concatenate((times[:-1], d)), np.vstack((close[:-1], values))
    use = (times >= period['warmup_start']) & (times < period['end'])
    times, close = times[use], close[use]
    expected = np.arange(period['warmup_start'], period['end'], DAY, dtype=np.int64)
    if (not np.array_equal(times, expected) or close.shape != (period['days'] + 199, 5)
            or not np.isfinite(close).all() or (close <= 0).any()):
        raise ValueError('EXACT_COMPLETE_PAST_ONLY_200_CLOSE_UNION_REQUIRED')
    decisions = np.arange(period['start'], period['end'], DAY, dtype=np.int64)
    return tuple(frozen_array(a) for a in (times, close, decisions))


def mark2024():
    global _MARK2024
    path = c.ROOT / 'traditional_three_tier_freeze_20261015/missing_mark_adapter_2024.py'
    raw = c.exact(path, '31da772b753ff331562d0ddc789d8b62cd86eb57f02a25a19ee6f78e7d88ff08')
    if _MARK2024 is None:
        from types import SimpleNamespace
        tree = ast.parse(raw); namespace = dict(np=np, MappingProxyType=MappingProxyType)
        selected = [node for node in tree.body if isinstance(node, (ast.Assign, ast.FunctionDef))]
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
        _MARK2024 = SimpleNamespace(**{name: namespace[name] for name in ('qualification', 'project_month')})
    return _MARK2024


def month_arrays(year, raw, start, count, quality_cells=()):
    period_named(year)
    if type(start) is not int or type(count) is not int or not 0 < count <= 44640:
        raise ValueError('BOUNDED_NATIVE_MONTH_CLOCK_REQUIRED')
    specs = {'times': ((count,), 'int64')}
    specs.update({symbol + '_' + field: ((count,), 'float64') for symbol in S for field in FIELDS})
    if year in (2021, 2022):
        specs['available_us'] = ((count,), 'int64')
    a = npz(raw, specs, allow_unselected=year == 2021)
    if (not np.array_equal(a['times'], np.arange(start, start + count * MINUTE, MINUTE, dtype=np.int64))
            or 'available_us' in a and not np.array_equal(a['available_us'], a['times'] + MINUTE)):
        raise ValueError('EXACT_NATIVE_OPEN_AND_COMPLETION_CLOCKS_REQUIRED')
    projected = {'times': a['times']}; replaced = []
    lookup = {(cell.symbol, cell.minute_open_us): cell for cell in quality_cells}
    if quality_cells and year != 2022:
        raise ValueError('ONLY_2022_TYPED27_CARRY_CELLS_ALLOWED')
    for symbol in S:
        for field in FIELDS:
            value = a[symbol + '_' + field]
            if field == 'mark' and year == 2022:
                holes = np.flatnonzero(np.isnan(value)); value = value.copy()
                for off in holes:
                    key = (symbol, start + int(off) * MINUTE)
                    if key not in lookup:
                        raise ValueError('EXACT_ORIGINAL27_MARK_ABSENCE_REQUIRED')
                    value[off] = float(lookup[key].price_text); replaced.append(key)
                expected = {key for key in lookup if key[0] == symbol and start <= key[1] < start + count * MINUTE}
                if expected != {(symbol, start + int(off) * MINUTE) for off in holes}:
                    raise ValueError('GENUINE_MARK_MAY_NOT_BE_OVERWRITTEN')
            if (not np.isfinite(value).all() or (value < 0).any()
                    or field != 'quote_volume' and (value <= 0).any()):
                raise ValueError('POSITIVE_GENUINE_OR_DECLARED_CAUSAL_MARK_REQUIRED')
            projected[symbol + '_' + field] = frozen_array(value)
    if year == 2024:
        projected, _ = mark2024().project_month(projected)
        projected = {key: frozen_array(value) for key, value in projected.items()}
    return MappingProxyType(projected), tuple(replaced)
