"""One new2h public hook/causal/risk-input boundary case, no market account run."""
import json
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_donchian_perpetual as strategy
from scripts.research_v8 import public_donchian_adapter as original


def test_original_2h_long_only_hooks_complete_warmup_and_future_prefix(tmp_path):
    bar, day, first = strategy.BAR_US, strategy.DAY_US, strategy.SCORE_BEGIN_US
    stamps = first + (np.arange(205, dtype=np.int64) - 199) * bar
    prices = np.r_[np.full(179, 150.), np.full(20, 100.), 151., 101., 99., 152., 153., 154.]

    def rows(symbol, closes, values, interval, duration):
        return [dict(symbol=symbol, interval=interval, open_us=int(close-duration),
            close_us=int(close), available_us=int(close), open=float(price),
            close=float(price), high=float(price+.1), low=float(price-.1), volume=1000.)
            for close, price in zip(closes, values, strict=True)]

    bars = pl.DataFrame(rows('BTCUSDT', stamps, prices, '2h', bar)
        + rows('ETHUSDT', stamps, np.full(len(stamps), 100.), '2h', bar))
    daily_stamps = first + (np.arange(34, dtype=np.int64)-30)*day
    daily = pl.DataFrame([row for symbol in ('BTCUSDT', 'ETHUSDT')
        for row in rows(symbol, daily_stamps, np.full(34, 100.), '1d', day)])
    decisions = stamps[199:203]
    targets, receipt = strategy.fixed_targets(bars, decisions, risk_daily_bars=daily)
    btc = targets.filter(pl.col('symbol') == 'BTCUSDT')
    assert btc['raw_signed_target'].to_list() == [.3, .3, 0., .3]
    assert btc['target_weight'].to_list() == [.3, .3, 0., .3]  # buffer belongs to controller
    assert targets.filter(pl.col('symbol') == 'ETHUSDT')['target_weight'].sum() == 0
    assert targets['target_weight'].min() >= 0 and not receipt['strategy_rules']['can_short']
    assert receipt['candidate_status'] == 'NO_QUALIFIED_CANDIDATE'

    # Independent scalar20/SMA200 and the unchanged upstream hook agree. The
    # second decision is below SMA200 but above the lower channel: stay long.
    Public = original._load_public_hooks()
    held = False
    candles = np.column_stack(((stamps-bar)/1000, prices, prices, prices+.1, prices-.1,
                               np.full(len(prices), 1000.)))
    scalar_states = []
    for index in range(199, 203):
        upper = max(prices[index-20:index]+.1)
        lower = min(prices[index-20:index]-.1)
        mean = math.fsum(float(v) for v in prices[index-199:index+1])/200
        hook = Public()
        hook.candles = candles[max(0, index-200):index+1]
        hook.close = float(prices[index]);hook.is_long = held;hook.is_short = False
        assert hook.should_short() is False
        assert hook.should_long() == (prices[index] > upper)
        assert all(filter_() for filter_ in hook.filters()) == (prices[index] > mean)
        closed = [False];hook.liquidate = lambda: closed.__setitem__(0, True)
        if held:
            hook.update_position()
            assert closed[0] == (prices[index] < lower)
            held = not closed[0]
        else:
            held = prices[index] > upper and prices[index] > mean
        scalar_states.append(.3 if held else 0.)
    assert scalar_states == btc['raw_signed_target'].to_list()
    assert prices[200] < math.fsum(float(v) for v in prices[1:201])/200
    for proof in receipt['risk']:
        assert proof['covariance_observations'] == 30 and proof['past_only']
        for witness in proof['signal_witnesses']:
            assert witness['maximum_signal_available_us'] <= proof['decision_us']
            assert witness['maximum_risk_available_us'] <= proof['decision_us']
            assert witness['signal_warmup_first_close_us'] == proof['decision_us']-199*bar
            assert witness['risk_last_day_close_us'] == proof['decision_us']//day*day

    # A finite poison after the comparison prefix changes no earlier target or
    # risk receipt, including when it changes only future daily risk prices.
    cut = int(decisions[1])
    def poison(frame, factor):
        return frame.with_columns(*[pl.when(pl.col('close_us') > cut)
            .then(pl.col(key)*factor).otherwise(pl.col(key)).alias(key)
            for key in ('open', 'high', 'low', 'close')])
    future, future_receipt = strategy.fixed_targets(poison(bars, 3), decisions,
        risk_daily_bars=poison(daily, 7))
    assert targets.filter(pl.col('available_us') <= cut).equals(
        future.filter(pl.col('available_us') <= cut))
    assert receipt['risk'][:2] == future_receipt['risk'][:2]

    # Fresh flat despite a genuine, fully warmed up bullish warmup breakout.
    extra = [row for symbol in ('BTCUSDT', 'ETHUSDT') for row in rows(symbol,
        np.array([first-201*bar, first-200*bar]), np.array([150., 150.]), '2h', bar)]
    fresh = pl.concat([pl.DataFrame(extra), bars]).with_columns(*[
        pl.when((pl.col('symbol') == 'BTCUSDT') & (pl.col('close_us') == first-2*bar))
        .then(151.+offset).when((pl.col('symbol') == 'BTCUSDT')
        & pl.col('close_us').is_in([first-bar, first]))
        .then(101.+offset).otherwise(pl.col(key)).alias(key)
        for key, offset in (('open', 0), ('close', 0), ('high', .1), ('low', -.1))])
    warm = fresh.filter((pl.col('symbol') == 'BTCUSDT') & (pl.col('close_us') <= first-2*bar)).sort('close_us')
    assert warm.height == 200 and warm['close'][-1] > warm['high'][-21:-1].max()
    assert warm['close'][-1] > math.fsum(warm['close'].to_list())/200
    fresh_targets, _ = strategy.fixed_targets(fresh, decisions[:1], risk_daily_bars=daily)
    assert fresh_targets['target_weight'].sum() == 0

    # Each rejected boundary has a distinct causal reason; no future row can
    # make an incomplete first decision mature by substituting another bar.
    with pytest.raises(ValueError, match='200'):
        strategy.fixed_targets(bars.filter(~((pl.col('symbol') == 'BTCUSDT')
            & (pl.col('close_us') == int(stamps[0])))), decisions, risk_daily_bars=daily)
    with pytest.raises(ValueError, match='Complete aligned'):
        strategy.fixed_targets(bars.filter(pl.col('close_us') != first-10*bar), decisions, risk_daily_bars=daily)
    delayed = bars.with_columns(pl.when(pl.col('close_us') == first)
        .then(first+1).otherwise(pl.col('available_us')).alias('available_us'))
    with pytest.raises(ValueError, match='available2h'):
        strategy.fixed_targets(delayed, decisions, risk_daily_bars=daily)
    late_daily = daily.with_columns(pl.when(pl.col('close_us') == first)
        .then(first+1).otherwise(pl.col('available_us')).alias('available_us'))
    with pytest.raises(ValueError, match='daily returns'):
        strategy.fixed_targets(bars, decisions, risk_daily_bars=late_daily)
    with pytest.raises(ValueError, match='integer'):
        strategy.fixed_targets(bars, decisions.astype(float)+.5, risk_daily_bars=daily)
    with pytest.raises(ValueError, match='UTC2h'):
        strategy.fixed_targets(bars, decisions+1, risk_daily_bars=daily)
    with pytest.raises(ValueError, match='LONG_ONLY'):
        strategy.fixed_targets(bars, decisions, 'SHORT_ONLY', risk_daily_bars=daily)
    (tmp_path/'donchian_perpetual_target_evidence.json').write_text(json.dumps(dict(
        scope='SYNTHETIC_2H_PUBLIC_HOOK_CAUSALITY_NOT_MARKET_OR_ACCOUNT_RESULT',
        targets=targets.to_dicts(), target_receipt=receipt,
        scalar_original_hook_states=scalar_states, fresh_flat_targets=fresh_targets.to_dicts()),
        ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
