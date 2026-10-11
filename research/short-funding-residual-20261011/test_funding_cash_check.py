"""Independent hand examples for funding cash and conservative enclosure."""
from decimal import Decimal
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('cash_check', Path(__file__).with_name('funding_cash_check.py'))
cash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cash)


def test_decimal_fixed_quantity_receipts_and_short_sign():
    # 1,200 USDT at price100 =>12 coins; mark changes don't rebalance units.
    q = Decimal('1200') / Decimal('100')
    expected = q * (Decimal('.0001') * Decimal('110') - Decimal('.0002') * Decimal('90'))
    assert expected == Decimal('-.0840')
    assert cash.signed_cash(-12, [.0001, -.0002], [110, 90]) == pytest.approx(float(expected), abs=1e-15)
    assert cash.signed_cash(12, [.0001, -.0002], [110, 90]) == pytest.approx(-float(expected), abs=1e-15)
    assert cash.signed_cash(-12, [.0001, -.0002], [110, 90], .01) == pytest.approx(-.00084)


def test_missing_charge_mark_does_not_become_zero():
    with pytest.raises(ValueError):
        cash.signed_cash(-1, [.0001], [np.nan])


def test_signed_mark_bounds_and_optional_ownership_enclose_extremes():
    # mandatory positive, optional negative, optional positive: all 8 corners.
    coefficients = [.001, -.002, .003]
    bounds = cash.enclosure(coefficients, [90, 90, 90], [110, 110, 110], [False, True, True])
    assert bounds == pytest.approx([-.13, .44])
    for own1 in (0, 1):
        for own2 in (0, 1):
            for m0 in (90, 110):
                for m1 in (90, 110):
                    for m2 in (90, 110):
                        value = coefficients[0] * m0 + own1 * coefficients[1] * m1 + own2 * coefficients[2] * m2
                        assert bounds[0] - 1e-15 <= value <= bounds[1] + 1e-15


def test_actual_entry_exit_boundaries_are_explicit_and_missing_event_stops():
    hour = 3_600_000_000
    t = np.arange(0, 73, 8, dtype=np.int64) * hour
    start, end = 8 * hour, 64 * hour
    idx, center, optional = cash.event_window(t, np.full(len(t), 8.), start, end)
    assert t[idx[center]].tolist() == [int(h * hour) for h in range(16, 65, 8)]
    assert t[idx[optional]].tolist() == [start, end]
    with pytest.raises(ValueError):
        cash.event_window(np.delete(t, 4), np.full(len(t) - 1, 8.), start, end)


def test_malformed_arrays_or_nan_unit_scale_hard_stop():
    with pytest.raises(ValueError):
        cash.enclosure([1., 2.], [90.], [110.], [False])
    with pytest.raises(ValueError):
        cash.signed_cash(-1., [.0001], [100.], np.nan)
