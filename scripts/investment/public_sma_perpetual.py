"""Original MIT daily SMA hooks with ordered, configurable portfolio targets.

The strategy supplies direction; shared past-only covariance and absolute
caps supply sizing. These are research targets, not native exchange orders.
"""
from __future__ import annotations
import numpy as np
import polars as pl
from scripts.investment import public_sma_daily as public

MODES = ('LONG_ONLY', 'SHORT_ONLY', 'LONG_SHORT', 'CASH')
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
DAY_US = 86_400_000_000
ALLOCATIONS = ('EQUAL', 'INVERSE_VOL_30D')


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def symbol_order(symbols):
    names = tuple(symbols)
    require(bool(names) and len(names) == len(set(names)) and all(
        isinstance(s, str) and s.isascii() and s.isalnum() and s.endswith('USDT')
        for s in names), 'Unique explicit ordered USDT symbols required')
    return names


def signed_risk_weights(raw, past_returns, annual_vol_target=.10):
    """N ordered assets; zero net exposure still has gross and covariance risk."""
    w = np.asarray(raw, dtype=np.float64).copy()
    r = np.asarray(past_returns, dtype=np.float64)
    require(w.ndim == 1 and len(w) > 0 and np.isfinite(w).all()
        and r.ndim == 2 and r.shape[1] == len(w) and r.shape[0] >= 30
        and np.isfinite(r).all(), 'Ordered assets and complete 30 past returns')
    require(0 < annual_vol_target <= .10, 'Existing volatility target cannot increase')
    w = np.clip(w, -.3, .3)
    gross = float(np.abs(w).sum())
    if gross > .6:
        w *= .6 / gross
    covariance = np.atleast_2d(np.cov(r[-30:], rowvar=False, ddof=1)) * 365
    variance = float(w @ covariance @ w)
    require(variance >= -1e-15, 'Nonnegative covariance risk required')
    sigma = float(np.sqrt(max(variance, 0.)))
    if sigma > annual_vol_target:
        w *= annual_vol_target / sigma
    return w, dict(unscaled_signed_covariance_annual_vol=sigma,
        net_target_weight=float(w.sum()), gross_target_weight=float(np.abs(w).sum()),
        covariance_observations=30, covariance_assets=len(w), past_only=True)


def fixed_targets(bars, decisions, mode, *, symbols=SYMBOLS,
                  direction_factory=None, eligible_by_decision=None, allocation='EQUAL',
                  completed_bar_count=200):
    """Daily hooks, explicit completed-bar context and ordered membership.

    Missing/warming/exited assets have zero targets and retain their identity
    for actual portfolio liquidation. Missing executable prices are handled by
    the account runner, never by deleting scoring dates or zeroing PnL.
    """
    require(mode in MODES, 'Preselected direction required')
    require(allocation in ALLOCATIONS, 'Preselected allocation required')
    require(type(completed_bar_count) is int and completed_bar_count >= 200,
            'Explicit integer warmup must preserve at least the original 200 bars')
    symbols = symbol_order(symbols)
    supplied = np.asarray(decisions)
    require(supplied.dtype.kind in ('i', 'u') and supplied.ndim == 1
        and np.all(supplied >= 0) and np.all(supplied <= np.iinfo(np.int64).max),
        'Integer decision microseconds required')
    times = supplied.astype(np.int64)
    require(len(times) > 0 and np.all(np.diff(times) == DAY_US)
        and np.all(times % DAY_US == 0), 'Complete UTC daily decisions required')
    expected = {'symbol', 'open_us', 'close_us', 'available_us',
                'open', 'high', 'low', 'close', 'volume'}
    require(expected.issubset(bars.columns) and all(
        bars.schema[k] == pl.Int64 for k in ('open_us', 'close_us', 'available_us')),
        'Actual daily trade bars with integer clocks required')
    require(set(bars['symbol'].unique().to_list()) <= set(symbols), 'Unknown input symbol')
    factory = direction_factory or public._load_public_hooks()
    context = {}
    for symbol in symbols:
        one = bars.filter(pl.col('symbol') == symbol).sort('close_us')
        require(one.null_count().select(pl.sum_horizontal(pl.all())).item() == 0,
            'Null inputs must be recorded as missing rows, never imputed')
        stamps = one['close_us'].to_numpy()
        available = one['available_us'].to_numpy()
        values = one.select('open', 'close', 'high', 'low', 'volume').to_numpy()
        require(np.all(one['open_us'].to_numpy() + DAY_US == stamps)
            and np.all(np.diff(stamps) > 0) and np.all(stamps % DAY_US == 0)
            and np.all(available >= stamps), 'Daily closure, uniqueness and availability')
        require(np.isfinite(values).all() and np.all(values[:, :4] > 0)
            and np.all(values[:, 4] >= 0), 'Actual finite OHLCV required')
        context[symbol] = dict(stamps=stamps, available=available,
            candles=np.column_stack((one['open_us'].to_numpy() / 1000, values)),
            hooks=factory(), state=0)
    targets, risk = [], []
    for decision in times:
        membership = set(symbols) if eligible_by_decision is None else set(
            eligible_by_decision.get(int(decision), ()))
        require(membership <= set(symbols), 'Membership outside configured account universe')
        raw, covariance_symbols, returns, reasons = {}, [], [], {}
        for symbol in symbols:
            c = context[symbol]
            index = int(np.searchsorted(c['stamps'], decision, side='right') - 1)
            first = index - completed_bar_count + 1
            valid = (first >= 0 and c['stamps'][index] == decision
                and np.all(np.diff(c['stamps'][first:index+1]) == DAY_US)
                and np.all(c['available'][first:index+1] <= decision))
            if symbol not in membership or not valid:
                c['state'] = 0
                raw[symbol] = 0.
                reasons[symbol] = 'POOL_EXIT' if symbol not in membership else 'WARMUP_OR_DATA_GAP'
                continue
            hook = c['hooks']
            hook.candles = c['candles'][first:index+1]
            hook.price = float(hook.candles[-1, 2])
            hook.is_long, hook.is_short = c['state'] == 1, c['state'] == -1
            closed = [False]
            hook.liquidate = lambda: closed.__setitem__(0, True)
            if mode == 'CASH':
                c['state'] = 0
            elif c['state']:
                hook.update_position()
                if closed[0]:
                    c['state'] = 0
            elif mode in ('LONG_ONLY', 'LONG_SHORT') and hook.should_long():
                c['state'] = 1
            elif mode in ('SHORT_ONLY', 'LONG_SHORT') and hook.should_short():
                c['state'] = -1
            raw[symbol] = min(.3, .6 / len(membership)) * c['state']
            close = c['candles'][index-30:index+1, 2]
            returns.append(np.diff(close) / close[:-1])
            covariance_symbols.append(symbol)
            reasons[symbol] = 'ELIGIBLE'
        allocation_details = {}
        if allocation == 'INVERSE_VOL_30D':
            # Reuse exactly the completed past-return/eligibility pipeline.
            # Any invalid member makes this allocation unknown and flat;
            # its budget is never reassigned to the remaining members.
            volatility = dict.fromkeys((s for s in symbols if s in membership), None)
            failures = {s:reasons[s] for s in symbols
                        if s in membership and s not in covariance_symbols}
            if covariance_symbols:
                with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
                    sample = np.std(np.column_stack(returns)[-30:], axis=0, ddof=1)
                for s, sigma in zip(covariance_symbols, sample, strict=True):
                    volatility[s] = float(sigma) if np.isfinite(sigma) else None
                    if not np.isfinite(sigma) or sigma <= 0:
                        failures[s] = 'NONFINITE_OR_ZERO_PAST30_SAMPLE_VOLATILITY'
            if failures or not covariance_symbols:
                raw = dict.fromkeys(symbols, 0.)
                for s in covariance_symbols:
                    reasons[s] = 'INVERSE_VOLATILITY_UNKNOWN_FLAT'
                status = 'UNKNOWN_FLAT_NO_BUDGET_REDISTRIBUTION'
            else:
                # min(sigma)/sigma is proportional to 1/sigma and avoids
                # reciprocal overflow without a floor, band or fitted epsilon.
                inverse = sample.min() / sample
                sizes = np.minimum(.3, .6 * inverse / inverse.sum())
                raw.update((s, float(size) * context[s]['state'])
                           for s, size in zip(covariance_symbols, sizes, strict=True))
                status = 'COMPLETE_PAST30_INVERSE_VOLATILITY'
            allocation_details = dict(allocation=allocation, allocation_status=status,
                allocation_sample_daily_volatility=volatility,
                allocation_invalid_symbols=failures, allocation_std_ddof=1,
                clipped_budget_not_redistributed=True)
        weights = dict.fromkeys(symbols, 0.)
        if covariance_symbols and not (allocation_details and
                allocation_details['allocation_status'].startswith('UNKNOWN')):
            values, details = signed_risk_weights([raw[s] for s in covariance_symbols],
                                                  np.column_stack(returns))
            weights.update(zip(covariance_symbols, values, strict=True))
        else:
            details = dict(unscaled_signed_covariance_annual_vol=0., net_target_weight=0.,
                gross_target_weight=0., covariance_observations=0, covariance_assets=0, past_only=True)
        for symbol in symbols:
            targets.append(dict(available_us=int(decision), symbol=symbol,
                target_weight=float(weights[symbol]), raw_signed_target=float(raw[symbol]),
                mode=mode, eligibility_reason=reasons[symbol]))
        risk.append(dict(decision_us=int(decision), symbol_order=list(symbols),
            covariance_symbol_order=covariance_symbols, eligibility=reasons,
            **details, **allocation_details))
    return pl.DataFrame(targets), dict(mode=mode, symbols=list(symbols), risk=risk,
        original_long_and_short_and_exit_hooks_reused=direction_factory is None,
        whole_balance_sizing_replaced_by_capped_COINSizing=True,
        close_then_wait_next_daily_decision_to_reenter=True, equality_holds_current_position=True,
        forbidden_directions_never_create_internal_positions=True, source=public.PINNED_HASHES,
        timeframe_minutes=1440, fast_period=50, slow_period=200,
        complete_daily_warmup=completed_bar_count,
        native_Jesse_or_Bybit_execution_replicated=False, fresh_flat_each_window=True,
        funding_rates_used_for_signal=False, candidate_status='NO_QUALIFIED_CANDIDATE')
