"""A fractional official volume after the schema inference prefix is retained."""
import csv
import io
from decimal import Decimal

import polars as pl
import pytest
from quant.data import parse_csv


def test_decimal_volume_after_integer_prefix_and_strict_count():
    start = 1743465600000
    lines = []
    for i in range(1440):
        opened = start + i * 60000
        volume = '6701.80' if i == 110 else '6701'
        lines.append(f'{opened},100,101,99,100,{volume},{opened+59999},670180,3,100,10000,0')
    raw = ('\n'.join(lines)+'\n').encode()
    frame, quality = parse_csv(raw, 'SOLUSDT')
    reference = list(csv.reader(io.StringIO(raw.decode())))
    assert frame.height == len(reference) == 1440
    assert frame['volume'].dtype == pl.Float64
    assert frame['volume'].to_list() == [float(Decimal(r[5])) for r in reference]
    assert quality['bad_values'] == quality['bad_timestamps'] == quality['gaps'] == 0
    assert quality['incomplete_days'] == []
    invalid = lines.copy()
    invalid[110] = invalid[110].replace(',3,100,', ',3.5,100,')
    with pytest.raises(pl.exceptions.ComputeError):
        parse_csv(('\n'.join(invalid)+'\n').encode(), 'SOLUSDT')
