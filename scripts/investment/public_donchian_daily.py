"""Fixed original Jesse Donchian hooks on official closed UTC daily candles.

Signal-only adapter. Daily closes are availability proxies, not executable
prices or certified exchange publication times. No warmup position is opened.
"""
from __future__ import annotations

import numpy as np
import polars as pl
from scripts.research_v8 import public_donchian_adapter as public
from scripts.research_v8 import benchmark_targets as original
from scripts.research_v8 import benchmark_targets_v2 as common

STRATEGY_ID = 'COIN_JESSE_DONCHIAN_1D_SPOT_ADAPTER'
DAY_US, MINUTE_US = common.DAY_US, common.MINUTE_US
SOURCE_BEGIN_US, LOCKED_US = 1685577600000000, 1772323200000000
SCORE_BEGIN_US = 1704067200000000
WARMUP_BARS = 200
RULES = dict(timeframe_minutes=1440, channel_period=20, SMA_period=200,
    channel_excludes_current=True, SMA_includes_current_completed_day=True,
    long_only=True, per_symbol_target=.3, fresh_flat_each_scoring_period=True,
    warmup_positions=False, day_close_equals_decision_permitted=True,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED',
    missing_policy='WHOLE_PAIRED_PERIOD_NOT_EVALUABLE_NO_RETROACTIVE_TARGET_ZEROING')


def calendar_array(calendar):
    values = np.asarray(calendar)
    common.require(values.ndim == 1 and values.dtype.kind in 'iu' and len(values) >= 2,
        'Original integer minute decision calendar required')
    common.require(np.all((values >= SCORE_BEGIN_US) & (values < LOCKED_US))
        and np.all(values % MINUTE_US == 0) and np.all(np.diff(values) == MINUTE_US),
        'Complete aligned development minute calendar; no locked input')
    return values.astype(np.int64, copy=False)


def daily_view(frame):
    """Keep rows; invalid OHLC/availability become ineligible, never fill/drop."""
    required = {'symbol','interval','open_us','close_us','available_us','open','high','low','close','volume'}
    common.require(required <= set(frame.columns), 'Original official daily normalized schema required')
    common.require(frame.height and not frame['symbol'].null_count() and not frame['interval'].null_count()
        and frame['symbol'].is_in(common.SYMBOLS).all()
        and frame['interval'].eq('1d').all()
        and frame.height == frame.unique(['symbol','open_us']).height,
        'Only BTC/ETH official1d rows, no duplicate symbol-day')
    for name in ('open_us','close_us','available_us'):
        common.require(frame.schema[name] == pl.Int64, 'Original integer daily timestamps required')
    common.require(not frame['open_us'].null_count() and not frame['close_us'].null_count(),
        'Unknown daily candle boundaries are not a calendar')
    stamps = frame['open_us'].to_numpy()
    common.require(np.all((stamps >= SOURCE_BEGIN_US) & (stamps < LOCKED_US))
        and np.all(stamps % DAY_US == 0)
        and frame['close_us'].eq(frame['open_us'] + DAY_US).all(),
        'Exact complete UTC1d boundaries; March physical rows forbidden')
    valid = (pl.col('available_us') >= pl.col('close_us'))
    valid &= pl.all_horizontal([pl.col(name).is_finite() & (pl.col(name) > 0)
        for name in ('open','high','low','close')])
    valid &= (pl.col('low') <= pl.min_horizontal('open','close'))
    valid &= (pl.col('high') >= pl.max_horizontal('open','close'))
    valid &= pl.col('volume').is_finite() & (pl.col('volume') >= 0)
    if 'valid_day' in frame.columns:
        valid &= pl.col('valid_day')
    return frame.with_columns(valid.fill_null(False).alias('daily_valid')).sort(['symbol','close_us'])


def fixed_targets(daily_bars, calendar):
    """Official1d inputs -> unchanged common minute target/intent schemas."""
    calendar = calendar_array(calendar)
    days = daily_view(daily_bars)
    # A terminal day closing at end is kept in source storage/valuation, but is
    # never a signal input to the final end-minus-one-minute decision.
    days = days.filter(pl.col('close_us') <= int(calendar[-1]))
    weights = np.zeros((len(calendar), 2), dtype=np.float64)
    reasons = [['PUBLIC_DAILY_FLAT' for _ in common.SYMBOLS] for _ in calendar]
    failed = False
    hooks = public._load_public_hooks()
    for asset, symbol in enumerate(common.SYMBOLS):
        rows = days.filter(pl.col('symbol') == symbol)
        if rows.is_empty():
            failed = True
            for reason in reasons: reason[asset] = 'MISSING_OR_UNAVAILABLE_200_CONTIGUOUS_COMPLETED_DAILY_BARS'
            continue
        stamps = rows['close_us'].to_numpy()
        candles = np.zeros((rows.height, 6), dtype=np.float64)
        candles[:, 0] = stamps // 1000
        candles[:, 1] = rows['open'].to_numpy()
        candles[:, 2] = rows['close'].to_numpy()
        candles[:, 3] = rows['high'].to_numpy()
        candles[:, 4] = rows['low'].to_numpy()
        candles[:, 5] = rows['volume'].to_numpy()
        # Official Polars rolling metadata checks, independent of signal state.
        rolling = rows.select(pl.col('daily_valid').cast(pl.Int64).rolling_sum(WARMUP_BARS).alias('valid'),
            pl.col('available_us').fill_null(LOCKED_US + DAY_US).rolling_max(WARMUP_BARS).alias('available'))
        valid_count = rolling['valid'].fill_null(0).to_numpy()
        maximum_available = rolling['available'].fill_null(LOCKED_US + DAY_US).to_numpy()
        latest = np.searchsorted(stamps, calendar, side='right') - 1
        held, evaluated = False, None
        rules = hooks()
        rules.vars = {}
        rules.liquidate = lambda: None
        for row, decision in enumerate(calendar):
            index = int(latest[row])
            known = (index >= WARMUP_BARS - 1
                and stamps[index] == int(decision) // DAY_US * DAY_US
                and stamps[index] - stamps[index-WARMUP_BARS+1] == (WARMUP_BARS-1)*DAY_US
                and valid_count[index] == WARMUP_BARS
                and maximum_available[index] <= decision)
            if not known:
                failed = True
                reasons[row][asset] = 'MISSING_OR_UNAVAILABLE_200_CONTIGUOUS_COMPLETED_DAILY_BARS'
                continue
            if evaluated != index:
                rules.candles = candles[max(0,index-WARMUP_BARS):index+1]
                rules.close = float(candles[index,2])
                if held:
                    liquidated = [False]
                    rules.liquidate = lambda: liquidated.__setitem__(0,True)
                    rules.update_position()
                    if liquidated[0]: held = False
                elif rules.should_long() and all(filter_() for filter_ in rules.filters()):
                    held = True
                evaluated = index
            weights[row,asset] = .3 if held else 0.
            reasons[row][asset] = 'PUBLIC_DAILY_LONG_HOLD' if held else 'PUBLIC_DAILY_FLAT'
    weights[-1,:] = 0.
    reasons[-1] = ['COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL' for _ in common.SYMBOLS]
    return common._version(original._plan(STRATEGY_ID,calendar,weights,reasons,warmup_failed=failed,
        metadata={'public_upstream_sha256':public.PINNED_HASHES,'original_public_hook_reused':True,
            'original_native_Jesse_engine_replicated':False,'strategy_rules':RULES,
            'timeframe_minutes':1440,'daily_prices_used_for_execution_or_risk':False,
            'source_scope':'OFFICIAL_SPOT1D_SIGNAL_PLUS_ACCEPTED_SPOT1M_EXECUTION_PROXY',
            'terminal_future_day_close_used':False,'past_targets_rewritten_after_late_invalid':False,
            'model_fits':0,'native_Bybit_market_or_publication_certified':False}))
