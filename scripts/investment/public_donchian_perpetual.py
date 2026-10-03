"""Original MIT Donchian long-only hooks on closed UTC2h perpetual bars.

Signal and past daily covariance only. The account/controller own sizing buffer,
fills, funding, margin, capacity, drift reductions and terminal accounting.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from scripts.investment.public_sma_perpetual import signed_risk_weights
from scripts.research_v8 import public_donchian_adapter as public

STRATEGY_ID = 'COIN_JESSE_DONCHIAN_2H_USDT_PERPETUAL_ADAPTER'
MODES = ('LONG_ONLY',)
DAY_US = 86_400_000_000
BAR_US = 7_200_000_000
SOURCE_BEGIN_US = 1_751_328_000_000_000  # 2025-07-01, original2h warmup
DAILY_BEGIN_US = 1_735_689_600_000_000  # accepted USD-M daily trade source
SCORE_BEGIN_US = 1_754_006_400_000_000
LOCKED_US = 1_772_323_200_000_000
PINNED_HASHES = public.PINNED_HASHES
RULES = dict(timeframe_minutes=120, donchian_period=20, trend_SMA_period=200,
    channel_excludes_current=True, SMA_includes_current_completed_bar=True,
    entry='CLOSE_GT_PREVIOUS20_UPPER_AND_CLOSE_GT_SMA200',
    held_exit='CLOSE_LT_PREVIOUS20_LOWER', SMA_filter_applies_only_to_entry=True,
    can_short=False, additional_percentage_stop_loss=False,
    fresh_flat_each_window=True, warmup_positions=False,
    exit_then_wait_next_2h_decision_to_reenter=True,
    past_covariance_completed_days=30, annual_vol_target=.10,
    asset_abs_cap=.3, gross_cap=.6, controller_sizing_buffer=.99,
    availability='COMPLETED_TRADE_BAR_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED',
    funding_rates_used_for_signal=False, whole_balance_sizing_transplanted=False)


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def _contexts(frame, duration, interval, lower, minimum):
    required = {'symbol', 'interval', 'open_us', 'close_us', 'available_us',
                'open', 'high', 'low', 'close', 'volume'}
    require(required <= set(frame.columns), 'Actual trade-bar schema required')
    require(frame.height and not frame.select(sorted(required)).null_count()
        .select(pl.sum_horizontal(pl.all())).item(), 'No unknown bar values or availability')
    require(set(frame['symbol'].unique().to_list()) == {'BTCUSDT', 'ETHUSDT'}
        and frame['interval'].eq(interval).all(), 'Exactly BTC/ETH with the fixed interval')
    require(all(frame.schema[k] == pl.Int64 for k in ('open_us', 'close_us', 'available_us')),
        'Exact integer microsecond clocks; no floating timestamp conversion')
    require(frame.height == frame.unique(['symbol', 'open_us']).height,
        'Duplicate symbol-bar is not a complete calendar')
    contexts = []
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        one = frame.filter(pl.col('symbol') == symbol).sort('close_us')
        opens = one['open_us'].to_numpy()
        closes = one['close_us'].to_numpy()
        available = one['available_us'].to_numpy()
        require(len(closes) >= minimum and np.all((opens >= lower) & (opens < LOCKED_US))
            and np.all(opens % duration == 0) and np.all(closes == opens + duration)
            and np.all(np.diff(closes) == duration) and np.all(available >= closes),
            'Complete aligned development bars with known closure; no missing/widened window')
        values = one.select('open', 'close', 'high', 'low', 'volume').to_numpy()
        require(np.isfinite(values).all() and np.all(values[:, :4] > 0)
            and np.all(values[:, 4] >= 0)
            and np.all(values[:, 3] <= np.minimum(values[:, 0], values[:, 1]))
            and np.all(values[:, 2] >= np.maximum(values[:, 0], values[:, 1])),
            'Finite positive coherent trade OHLC and nonnegative volume')
        contexts.append(dict(stamps=closes, available=available,
            candles=np.column_stack((opens / 1000, values))))
    return contexts


def fixed_targets(two_hour_bars, decisions, mode='LONG_ONLY', *, risk_daily_bars):
    """Return controller-schema targets and receipts; raw0/.3, never a short.

    UTC2h signal history and UTC1d risk history are separate inputs. Both must be
    complete and available at each decision. Neither prices nor rates are fills.
    """
    require(mode in MODES, 'Original public Donchian supports LONG_ONLY only')
    supplied = np.asarray(decisions)
    require(supplied.ndim == 1 and supplied.dtype.kind in 'iu' and len(supplied) > 0
        and np.all(supplied <= np.iinfo(np.int64).max), 'Nonempty integer decision microseconds')
    times = supplied.astype(np.int64, copy=False)
    require(np.all((times >= SCORE_BEGIN_US) & (times < LOCKED_US))
        and np.all(times % BAR_US == 0) and np.all(np.diff(times) == BAR_US),
        'Complete UTC2h scoring decisions before the locked boundary')
    signals = _contexts(two_hour_bars, BAR_US, '2h', SOURCE_BEGIN_US, 200)
    daily = _contexts(risk_daily_bars, DAY_US, '1d', DAILY_BEGIN_US, 31)
    hooks = public._load_public_hooks()
    state = [False, False]
    instances = [hooks(), hooks()]
    targets, risk_receipts = [], []
    for decision in times:
        raw, returns, witnesses = [], [], []
        for asset, symbol in enumerate(('BTCUSDT', 'ETHUSDT')):
            c, d = signals[asset], daily[asset]
            index = int(np.searchsorted(c['stamps'], decision, side='right') - 1)
            require(index >= 199 and c['stamps'][index] == decision
                and np.all(c['available'][index-199:index+1] <= decision),
                'Exactly200 contiguous completed available2h bars at each decision')
            day_close = int(decision) // DAY_US * DAY_US
            day_index = int(np.searchsorted(d['stamps'], day_close, side='right') - 1)
            require(day_index >= 30 and d['stamps'][day_index] == day_close
                and np.all(d['available'][day_index-30:day_index+1] <= decision),
                'Thirty complete past UTC daily returns, independent of2h signal history')
            rules = instances[asset]
            rules.candles = c['candles'][max(0, index-200):index+1]
            rules.close = float(c['candles'][index, 2])
            rules.is_long, rules.is_short = state[asset], False
            require(rules.should_short() is False, 'Unmodified public strategy has no short entry')
            closed = [False]
            rules.liquidate = lambda: closed.__setitem__(0, True)
            before = state[asset]
            if state[asset]:
                rules.update_position()
                if closed[0]:
                    state[asset] = False
            elif rules.should_long() and all(filter_() for filter_ in rules.filters()):
                state[asset] = True
            raw.append(.3 if state[asset] else 0.)
            prices = d['candles'][day_index-30:day_index+1, 2]
            returns.append(np.diff(prices) / prices[:-1])
            witnesses.append(dict(symbol=symbol, signal_close_us=int(decision),
                maximum_signal_available_us=int(c['available'][index-199:index+1].max()),
                signal_warmup_first_close_us=int(c['stamps'][index-199]),
                risk_last_day_close_us=int(day_close),
                maximum_risk_available_us=int(d['available'][day_index-30:day_index+1].max()),
                held_before=before, held_after=state[asset], channel_exit=closed[0]))
        weights, receipt = signed_risk_weights(raw, np.column_stack(returns))
        for symbol, weight, direction in zip(('BTCUSDT', 'ETHUSDT'), weights, raw, strict=True):
            targets.append(dict(available_us=int(decision), symbol=symbol,
                target_weight=float(weight), raw_signed_target=float(direction), mode=mode))
        risk_receipts.append(dict(decision_us=int(decision), **receipt, signal_witnesses=witnesses))
    return pl.DataFrame(targets), dict(strategy_id=STRATEGY_ID, mode=mode,
        strategy_rules=RULES, risk=risk_receipts, source=PINNED_HASHES,
        original_entry_filters_and_held_channel_exit_hooks_reused=True,
        native_Jesse_or_Bybit_execution_replicated=False,
        price_source='BINANCE_USDM_TRADE_BARS_EXECUTION_IS_SEPARATE',
        model_fits=0, candidate_status='NO_QUALIFIED_CANDIDATE')
