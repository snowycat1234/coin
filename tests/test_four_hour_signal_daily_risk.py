"""4h signal candles require a separate causal daily covariance context."""
import numpy as np
import polars as pl
import pytest

from scripts.investment import public_sma_perpetual as shared

DAY = 86_400_000_000
FOUR = DAY // 6
AT = 240 * DAY


class AlwaysLong:
    def should_long(self):
        return True

    def should_short(self):
        return False

    def update_position(self):
        return None


def bars(interval, count, end=AT, symbols=('BTCUSDT', 'ETHUSDT')):
    frames = []
    for i, symbol in enumerate(symbols):
        clocks = end - np.arange(count - 1, -1, -1, dtype=np.int64) * interval
        prices = 100 * np.cumprod(1 + .025 * np.sin(np.arange(count) * .7 + i))
        frames.append(pl.DataFrame({'symbol': [symbol] * count,
            'open_us': clocks - interval, 'close_us': clocks, 'available_us': clocks,
            'open': prices, 'close': prices, 'high': prices * 1.01,
            'low': prices * .99, 'volume': np.ones(count)}))
    return pl.concat(frames)


def run(signal, risk, decisions=None, symbols=('BTCUSDT', 'ETHUSDT')):
    if decisions is None:
        decisions = np.arange(AT, AT + DAY, FOUR, dtype=np.int64)
    return shared.fixed_targets(signal, decisions, 'LONG_ONLY', symbols=symbols,
        direction_factory=AlwaysLong, signal_interval_minutes=240, risk_bars=risk)


def test_three_assets_and_reversed_identity_keep_daily_covariance_order():
    symbols = ('SOLUSDT', 'ETHUSDT', 'BTCUSDT')
    signal, risk = bars(FOUR, 206, AT + 5 * FOUR, symbols), bars(DAY, 200, symbols=symbols)
    normal, meta = run(signal, risk, symbols=symbols)
    reverse, reversed_meta = run(signal, risk, symbols=tuple(reversed(symbols)))
    assert normal['symbol'].to_list() == list(symbols) * 6
    for row in meta['risk']:
        assert row['covariance_symbol_order'] == list(symbols)
    for row in reversed_meta['risk']:
        assert row['covariance_symbol_order'] == list(reversed(symbols))
    assert normal.sort(['available_us', 'symbol'])['target_weight'].to_list() == pytest.approx(
        reverse.sort(['available_us', 'symbol'])['target_weight'].to_list(), abs=1e-12)
    assert max(normal['target_weight']) <= .3
    assert max(normal.group_by('available_us').agg(pl.col('target_weight').sum())['target_weight']) <= .6


def test_daily_risk_is_constant_intraday_and_matches_centered_past30_covariance():
    signal, risk = bars(FOUR, 205, AT + 5 * FOUR), bars(DAY, 200)
    frame, meta = run(signal, risk)
    returns = []
    for s in ('BTCUSDT', 'ETHUSDT'):
        p = risk.filter(pl.col('symbol') == s).tail(31)['close'].to_numpy()
        returns.append(np.diff(p) / p[:-1])
    matrix = np.column_stack(returns)
    centered = matrix - matrix.mean(axis=0)
    covariance = centered.T @ centered / 29 * 365
    raw = np.array([.3, .3])
    sigma = np.sqrt(raw @ covariance @ raw)
    expected = raw * min(1, .1 / sigma)
    for row in meta['risk']:
        assert row['covariance_observations'] == 30
        assert row['unscaled_signed_covariance_annual_vol'] == pytest.approx(sigma, abs=1e-12)
    assert frame['target_weight'].to_list() == pytest.approx(list(expected) * 6, abs=1e-12)


@pytest.mark.parametrize('signal_count,risk_count', [(199, 200), (200, 199)])
def test_both_two_hundred_signal_and_daily_risk_warmup_required(signal_count, risk_count):
    frame, _ = run(bars(FOUR, signal_count), bars(DAY, risk_count), np.array([AT], dtype=np.int64))
    assert frame['target_weight'].to_list() == [0., 0.]
    assert frame['raw_signed_target'].to_list() == [0., 0.]


def test_future_daily_prices_are_unavailable_until_next_complete_daily_close():
    signal = bars(FOUR, 206, AT + 5 * FOUR)
    risk = bars(DAY, 201, AT + DAY)
    a, _ = run(signal, risk)
    changed = risk.with_columns([
        pl.when(pl.col('close_us') > AT).then(pl.col(c) * 3).otherwise(pl.col(c)).alias(c)
        for c in ('open', 'close', 'high', 'low')])
    b, _ = run(signal, changed)
    assert a.equals(b)
    delayed = risk.with_columns(pl.when(pl.col('close_us') == AT)
        .then(pl.col('available_us') + FOUR).otherwise(pl.col('available_us')).alias('available_us'))
    at = run(signal, delayed, np.array([AT], dtype=np.int64))[0]
    assert at['target_weight'].to_list() == [0., 0.]


def test_missing_signal_bar_resets_state_and_daily_gap_is_not_imputed():
    instances = []
    class CountReset(AlwaysLong):
        def __init__(self):
            self.resets = 0
            instances.append(self)
        def reset_signal_state(self):
            self.resets += 1
    signal = bars(FOUR, 201, AT + FOUR, symbols=('BTCUSDT',))
    risk = bars(DAY, 200, symbols=('BTCUSDT',))
    missing = signal.filter(pl.col('close_us') != AT + FOUR)
    frame, _ = shared.fixed_targets(missing, np.array([AT, AT + FOUR], dtype=np.int64),
        'LONG_ONLY', symbols=('BTCUSDT',), direction_factory=CountReset,
        signal_interval_minutes=240, risk_bars=risk)
    assert frame['target_weight'][0] > 0 and frame['target_weight'][1] == 0
    assert instances[0].resets == 1
    gaprisk = risk.filter(pl.col('close_us') != AT - 10 * DAY)
    gap, _ = run(bars(FOUR, 200, symbols=('BTCUSDT',)), gaprisk,
        np.array([AT], dtype=np.int64), symbols=('BTCUSDT',))
    assert gap['target_weight'][0] == 0


def test_four_hour_requires_separate_daily_risk_bars():
    with pytest.raises(ValueError):
        shared.fixed_targets(bars(FOUR, 200), np.array([AT], dtype=np.int64),
            'LONG_ONLY', direction_factory=AlwaysLong, signal_interval_minutes=240)
