"""One independent inverse-vol allocation fixture; no market/account replay."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import vol_managed_perpetual_target as hold


def test_inverse_vol_hand_weights_and_past_only_order_and_unknown_scope():
    symbols = ('AAAUSDT', 'BBBUSDT', 'CCCUSDT')
    day = shared.DAY_US
    frames = []
    # Thirty alternating returns have mean0 and sample sigma=a*sqrt(30/29).
    # All three streams are perfectly positively correlated, with sigma1:2:4.
    for symbol, factor in zip(symbols, (1., 2., 4.), strict=True):
        prices = [100.] * 170
        for sign in (-1., 1.) * 15:
            prices.append(prices[-1] * (1. + sign * factor * .02))
        prices.extend([prices[-1] * 1.01] * 4)
        close = np.asarray(prices)
        opened = np.arange(len(close), dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(close), open_us=opened,
            close_us=opened + day, available_us=opened + day, open=close,
            high=close * 1.01, low=close * .99, close=close, volume=np.ones(len(close)))))
    bars = pl.concat(frames)
    decision = np.asarray([200 * day], dtype=np.int64)
    result, meta = hold.fixed_targets(bars, decision, symbols=symbols, allocation='INVERSE_VOL_30D')
    indexed = {row['symbol']: row for row in result.iter_rows(named=True)}
    # .6*(4/7,2/7,1/7) clips the first asset; the lost budget stays unused.
    raw = (.3, 6/35, 3/35)
    sample_sigma = .02 * math.sqrt(30/29)
    sigma = sample_sigma * math.sqrt(365) * (raw[0] + 2*raw[1] + 4*raw[2])
    scale = .10 / sigma
    assert sum(raw) < .6 and scale < 1
    for symbol, wanted in zip(symbols, raw, strict=True):
        assert indexed[symbol]['raw_signed_target'] == pytest.approx(wanted, abs=1e-13, rel=0)
        assert indexed[symbol]['target_weight'] == pytest.approx(wanted * scale, abs=1e-13, rel=0)
    assert meta['strategy_id'] == hold.INVERSE_STRATEGY_ID != hold.STRATEGY_ID
    assert meta['rules'] == hold.INVERSE_VOL_RULES
    assert meta['allocation'] == 'INVERSE_VOL_30D'
    risk = meta['risk'][0]
    assert risk['allocation_std_ddof'] == 1
    assert risk['covariance_observations'] == 30
    assert risk['covariance_symbol_order'] == list(symbols)
    assert risk['unscaled_signed_covariance_annual_vol'] == pytest.approx(sigma, abs=1e-13, rel=0)
    assert risk['allocation_invalid_symbols'] == {}

    reordered, reordered_meta = hold.fixed_targets(bars.reverse(), decision,
        symbols=tuple(reversed(symbols)), allocation='INVERSE_VOL_30D')
    assert reordered_meta['symbols'] == list(reversed(symbols))
    assert reordered_meta['risk'][0]['covariance_symbol_order'] == list(reversed(symbols))
    left, right = reordered.sort('symbol'), result.sort('symbol')
    assert left.select('available_us','symbol','mode','eligibility_reason').equals(
        right.select('available_us','symbol','mode','eligibility_reason'))
    assert np.allclose(left.select('target_weight','raw_signed_target').to_numpy(),
        right.select('target_weight','raw_signed_target').to_numpy(), rtol=0, atol=1e-13)
    future = bars.with_columns([
        pl.when(pl.col('close_us') > decision[0]).then(pl.col(column) * 1000)
          .otherwise(pl.col(column)).alias(column) for column in ('open', 'high', 'low', 'close')])
    poisoned, poisoned_meta = hold.fixed_targets(future, decision, symbols=symbols, allocation='INVERSE_VOL_30D')
    assert poisoned.equals(result) and poisoned_meta == meta

    equal, equal_meta = hold.fixed_targets(bars, decision, symbols=symbols)
    explicit_equal, explicit_meta = hold.fixed_targets(bars, decision, symbols=symbols, allocation='EQUAL')
    assert equal.equals(explicit_equal) and equal_meta == explicit_meta
    assert equal_meta['strategy_id'] == hold.STRATEGY_ID and equal_meta['rules'] == hold.RULES
    assert equal['raw_signed_target'].to_list() == [.2, .2, .2]
    equal_scale = .10 / (sample_sigma * math.sqrt(365) * .2 * (1+2+4))
    assert np.allclose(equal['target_weight'].to_numpy(), [.2 * equal_scale] * 3, rtol=0, atol=1e-13)

    zero = bars.with_columns([
        pl.when(pl.col('symbol') == symbols[1]).then(pl.lit(price))
          .otherwise(pl.col(column)).alias(column)
        for column, price in (('open',100.),('high',101.),('low',99.),('close',100.))])
    missing = bars.filter(~((pl.col('symbol') == symbols[1]) & (pl.col('close_us') == 199*day)))
    for bad in (zero, missing):
        flat, flat_meta = hold.fixed_targets(bad, decision, symbols=symbols, allocation='INVERSE_VOL_30D')
        assert flat['raw_signed_target'].to_list() == flat['target_weight'].to_list() == [0.,0.,0.]
        assert flat_meta['risk'][0]['allocation_status'] == 'UNKNOWN_FLAT_NO_BUDGET_REDISTRIBUTION'
        assert symbols[1] in flat_meta['risk'][0]['allocation_invalid_symbols']
    default_missing, _ = hold.fixed_targets(missing, decision, symbols=symbols)
    assert default_missing['raw_signed_target'].to_list() == [.2, 0., .2]

    # Finite OHLC inputs can still make a simple return overflow. No volatility
    # floor, exclusion or renormalization gives other members more budget.
    enormous = bars.with_columns([
        pl.when((pl.col('symbol') == symbols[1]) & (pl.col('close_us') == 171*day)).then(pl.lit(1e-300))
          .when((pl.col('symbol') == symbols[1]) & (pl.col('close_us') == 172*day)).then(pl.lit(1e300))
          .otherwise(pl.col(column)).alias(column) for column in ('open','high','low','close')])
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        flat, bad_meta = hold.fixed_targets(enormous, decision, symbols=symbols, allocation='INVERSE_VOL_30D')
    assert flat['target_weight'].to_list() == [0.,0.,0.]
    assert bad_meta['risk'][0]['allocation_sample_daily_volatility'][symbols[1]] is None
    with pytest.raises(ValueError, match='allocation'):
        hold.fixed_targets(bars, decision, symbols=symbols, allocation='FIT_BEST_WEIGHTS')
