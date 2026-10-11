"""Scope/clock/conflict counterexamples; historical repair checked separately."""
import io

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from .core import DAY_US, SYMBOLS
from .run import utc_us
from .repaired_data import DAYS, apply_patch, pre2023_table


def fixture():
    available = np.arange(utc_us('2022-02-01'), utc_us('2022-05-01'), DAY_US)
    values = np.full((len(available), 5), 100.)
    records = []
    for symbol in ('SOLUSDT', 'XRPUSDT'):
        for day in DAYS:
            t = np.flatnonzero(available == utc_us(day) + DAY_US)[0]
            values[t, SYMBOLS.index(symbol)] = np.nan
            records.append(dict(symbol=symbol, bar_start=day, close=101.))
    return available, values, records


def test_only_ten_missing_observed_closes_change():
    clock, old, records = fixture(); saved = old.copy()
    result = apply_patch(clock, old, records)
    np.testing.assert_array_equal(old, saved)
    np.testing.assert_array_equal(result[np.isfinite(old)], old[np.isfinite(old)])
    assert np.isfinite(result).all() and np.isnan(old).sum() == 10


@pytest.mark.parametrize('corrupt', ['present','duplicate','scope','clock','negative','nonfinite'])
def test_repair_conflict_or_scope_stops(corrupt):
    clock, old, records = fixture()
    if corrupt == 'present': old[np.flatnonzero(clock == utc_us(DAYS[0])+DAY_US)[0], 2] = 99.
    if corrupt == 'duplicate': records[-1] = records[0].copy()
    if corrupt == 'scope': records[0]['bar_start'] = '2023-01-01'
    if corrupt == 'clock': clock = clock + 1
    if corrupt == 'negative': records[0]['close'] = -1.
    if corrupt == 'nonfinite': records[0]['close'] = np.nan
    with pytest.raises(ValueError): apply_patch(clock, old, records)


def test_pre2023_projection_excludes_boundary_validation_and_fields():
    stamps = np.array(['2022-12-30','2022-12-31','2023-01-01'], dtype='datetime64[us]')
    table = pa.table(dict(dt=pa.array(stamps, type=pa.timestamp('us')), close=[100.,9999.,8888.], complete_kline=[True]*3, symbol=['SOLUSDT']*3, forbidden_outcome=[1.,2.,3.]))
    sink = io.BytesIO(); pq.write_table(table, sink)
    restored, times = pre2023_table(sink.getvalue())
    assert restored.column_names == ['dt','close','complete_kline','symbol']
    assert times.tolist() == [utc_us('2022-12-30')]
    assert restored['close'].to_pylist() == [100.]


def test_pre2023_rejects_non_midnight_or_duplicate():
    for stamps in ([utc_us('2022-12-29')+1], [utc_us('2022-12-29')]*2):
        table = pa.table(dict(dt=pa.array(stamps, type=pa.timestamp('us')), close=[100.]*len(stamps), complete_kline=[True]*len(stamps), symbol=['SOLUSDT']*len(stamps)))
        sink=io.BytesIO();pq.write_table(table,sink)
        with pytest.raises(ValueError): pre2023_table(sink.getvalue())
