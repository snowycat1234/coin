"""Macro entry filter uses the actual completed daily context, not 4h SMA."""
import numpy as np
import polars as pl

from scripts.investment import donchian_daily_pool_target as donchian

DAY = 86_400_000_000
FOUR = DAY // 6
AT = 240 * DAY


def candles(interval, prices, *, end=AT, symbol='BTCUSDT'):
    values = np.asarray(prices, dtype=np.float64)
    close = end - np.arange(len(values) - 1, -1, -1, dtype=np.int64) * interval
    return pl.DataFrame({'symbol': [symbol] * len(values), 'open_us': close - interval,
        'close_us': close, 'available_us': close, 'open': values, 'close': values,
        'high': values + 1., 'low': values - 1., 'volume': np.ones(len(values))})


def signal(old_price=100., ending=(101.,)):
    # Prior20 must contain only the low regime: old high equals/exceeds101.
    values = [old_price] * 179 + [80.] * 20 + list(ending)
    return candles(FOUR, values, end=AT + (len(ending) - 1) * FOUR)


def targets(signal_bars, daily, decisions=None, *, macro=True, symbols=('BTCUSDT',)):
    if decisions is None:
        decisions = np.array([AT], dtype=np.int64)
    return donchian.fixed_targets(signal_bars, decisions, 'LONG_ONLY', symbols=symbols,
        allocation='ACTIVE_EQUAL', exit_period=10, reentry_period=20,
        signal_interval_minutes=240, risk_bars=daily,
        trend_filter_interval_minutes=1440 if macro else None)


def test_daily_macro_rejects_entry_that_four_hour_sma_would_accept():
    s, d = signal(), candles(DAY, [150.] * 200)
    original, _ = targets(s, d, macro=False)
    macro, _ = targets(s, d)
    assert original['raw_signed_target'][0] == .3
    assert macro['raw_signed_target'][0] == 0


def test_daily_macro_accepts_entry_that_four_hour_sma_would_reject():
    s, d = signal(old_price=200.), candles(DAY, [80.] * 200)
    original, _ = targets(s, d, macro=False)
    macro, _ = targets(s, d)
    assert original['raw_signed_target'][0] == 0
    assert macro['raw_signed_target'][0] == .3


def test_daily_sma_strict_equality_does_not_enter():
    frame, _ = targets(signal(), candles(DAY, [101.] * 200))
    assert frame['raw_signed_target'][0] == 0


def test_held_exit_ten_is_not_blocked_when_macro_filter_fails():
    frame, _ = targets(signal(ending=(101., 70.)), candles(DAY, [80.] * 200),
        np.array([AT, AT + FOUR], dtype=np.int64))
    assert frame['raw_signed_target'].to_list() == [.3, 0.]


def test_future_daily_candle_cannot_change_earlier_filter_and_missing_day_is_flat():
    s = signal()
    d = candles(DAY, [80.] * 200 + [500.], end=AT + DAY)
    early, _ = targets(s, d)
    altered = d.with_columns(pl.when(pl.col('close_us') > AT).then(10_000.)
        .otherwise(pl.col('close')).alias('close'))
    same, _ = targets(s, altered)
    assert early.equals(same)
    assert early['raw_signed_target'][0] == .3
    missing = d.filter(pl.col('close_us') != AT - 10 * DAY)
    flat, _ = targets(s, missing)
    assert flat['raw_signed_target'][0] == 0


def test_three_asset_order_does_not_reassign_macro_signal_or_daily_prices():
    symbols = ('SOLUSDT', 'ETHUSDT', 'BTCUSDT')
    s = pl.concat([signal().with_columns(pl.lit(name).alias('symbol')) for name in symbols])
    d = pl.concat([candles(DAY, [80. if name != 'ETHUSDT' else 150.] * 200, symbol=name)
        for name in symbols])
    a, _ = targets(s, d, symbols=symbols)
    b, _ = targets(s, d, symbols=tuple(reversed(symbols)))
    assert a['symbol'].to_list() == list(symbols)
    assert a.sort('symbol').select('symbol', 'target_weight', 'raw_signed_target').equals(
        b.sort('symbol').select('symbol', 'target_weight', 'raw_signed_target'))
    assert a.filter(pl.col('symbol') == 'ETHUSDT')['raw_signed_target'][0] == 0
    assert a.filter(pl.col('symbol') != 'ETHUSDT')['raw_signed_target'].to_list() == [.3, .3]
