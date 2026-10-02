"""One synthetic hybrid target -> received-asset fee -> shared ledger case.

No market files, fit, prior green suite, or alternative strategy recipe is used.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import polars as pl

from scripts.investment import bybit_spot_adapter as native
from scripts.investment import compare_simple_strategies as common
from scripts.investment import public_donchian_hybrid as hybrid


def synthetic_minutes():
    """31 full past days, then the fixed entry/exit event shape from target tests."""
    origin = common.day_us(date(2025, 8, 1))
    hours = 32 * 24
    warmup_hours = 31 * 24
    hourly = np.full(hours, 100.)
    hourly[warmup_hours:warmup_hours + 6] = [103., 103., 90., 106., 80., 107.]
    hourly[warmup_hours + 6:] = np.repeat(
        np.arange(108., 108. + (hours - warmup_hours - 6) // 2), 2)
    close = np.repeat(hourly, 60)
    stamps = origin + np.arange(len(close), dtype=np.int64) * common.MINUTE_US
    frames = []
    for symbol, factor in zip(common.SYMBOLS, (1., .5), strict=True):
        price = close * factor
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(stamps), open_us=stamps,
            close_us=stamps + common.MINUTE_US, available_us=stamps + common.MINUTE_US,
            open=price, high=price + .1 * factor, low=price - .1 * factor,
            close=price, quote_volume=np.full(len(stamps), 100_000_000.),
            valid_day=np.ones(len(stamps), dtype=bool), minute_valid=np.ones(len(stamps), dtype=bool),
            missing_reason=[None] * len(stamps))))
    start = origin + 31 * common.DAY_US
    end = start + common.DAY_US
    return pl.concat(frames).sort(['open_us', 'symbol']), start, end


def test_hybrid_targets_native_settlement_and_shared_minute_ledger(tmp_path):
    minutes, start, end = synthetic_minutes()
    calendar = np.arange(start, end, common.MINUTE_US, dtype=np.int64)
    plan = hybrid.fixed_targets(minutes, calendar)
    assert plan.strategy_id == hybrid.STRATEGY_ID
    assert plan.receipt['paired_comparison_allowed'] and not plan.receipt['warmup_failed']
    assert plan.receipt['signal_hooks_reused_unmodified'] and plan.receipt['model_fits'] == 0
    assert plan.receipt['source_hashes']['scripts/investment/public_donchian_hybrid.py'] == (
        '80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68')

    # Complete minute intent calendar; only initial/changed weights reach execution.
    assert plan.calendar_ledger.height == 2 * len(calendar)
    for symbol in common.SYMBOLS:
        intent = plan.calendar_ledger.filter(pl.col('symbol') == symbol).sort('decision_us')
        weights = intent['target_weight'].to_numpy()
        changed = np.r_[True, weights[1:] != weights[:-1]]
        emitted = plan.targets.filter(pl.col('symbol') == symbol).sort('available_us')
        assert np.array_equal(emitted['available_us'].to_numpy(), calendar[changed])
        assert np.array_equal(emitted['target_weight'].to_numpy(), weights[changed])
        for hours, expected in ((0, 0.), (2, .3), (3, 0.), (4, .3), (5, 0.), (6, .3)):
            assert weights[hours * 60] == expected
        assert weights[-1] == 0.
    assert plan.targets.height < plan.calendar_ledger.height

    # Future minute prices do not alter any previously available target intent.
    boundary = start + 6 * hybrid.public.HOUR_US
    future = minutes.with_columns([pl.when(pl.col('open_us') >= boundary)
        .then(pl.col(field) * 3).otherwise(pl.col(field)).alias(field)
        for field in ('open', 'high', 'low', 'close')])
    future_plan = hybrid.fixed_targets(future, calendar)
    assert plan.calendar_ledger.filter(pl.col('decision_us') <= boundary).equals(
        future_plan.calendar_ledger.filter(pl.col('decision_us') <= boundary))
    assert plan.targets.filter(pl.col('available_us') <= boundary).equals(
        future_plan.targets.filter(pl.col('available_us') <= boundary))

    # Use the real common risk/cost setup, including 30-day/min20 past-only vol.
    config = common.comparison_config(start, end, 2)
    result = native.run_backtest(minutes.select('symbol', 'close_us', 'available_us'),
        minutes, plan.targets, config)
    ledger = common.write_ledger(tmp_path / 'hybrid-native-shared-ledger', result, minutes)
    inventory = pl.read_parquet(Path(ledger['directory']) / 'minute_nav_inventory.parquet')
    assert inventory.height == len(calendar)
    assert np.array_equal(inventory['close_us'].to_numpy(), calendar + common.MINUTE_US)
    trades = result.trades.sort('execution_us', maintain_order=True).to_dicts()
    assert any(fill['side'] == 'buy' for fill in trades)
    assert any(fill['side'] == 'sell' for fill in trades)
    for symbol in common.SYMBOLS:
        first_buy = next(fill for fill in trades if fill['symbol'] == symbol and fill['side'] == 'buy')
        first_sell = next(fill for fill in trades if fill['symbol'] == symbol and fill['side'] == 'sell')
        assert first_buy['signal_us'] == start + 2 * hybrid.public.HOUR_US
        assert first_sell['signal_us'] == start + 3 * hybrid.public.HOUR_US
    for fill in trades:
        assert fill['execution_us'] >= fill['signal_us'] + common.MINUTE_US + 1
        assert fill['capacity_open_us'] == fill['execution_us'] // common.MINUTE_US * common.MINUTE_US - common.MINUTE_US

    # Reconstruct cash/net received inventory without using saved delta columns.
    cash = Decimal(str(config.initial_cash))
    holdings = dict.fromkeys(common.SYMBOLS, Decimal(0))
    fee, execution = Decimal(0), Decimal(0)
    peak, maximum_drawdown = cash, Decimal(0)
    expected_nav, expected_cash = [], []
    expected_quantity = {symbol: [] for symbol in common.SYMBOLS}
    marks = {symbol: minutes.filter((pl.col('symbol') == symbol) &
        pl.col('open_us').is_between(start, end, closed='left'))['close'].to_list()
        for symbol in common.SYMBOLS}
    next_fill = 0
    for row, close_us in enumerate(inventory['close_us'].to_list()):
        while next_fill < len(trades) and trades[next_fill]['execution_us'] <= close_us:
            fill = trades[next_fill]
            symbol = fill['symbol']
            q, price, mid = (Decimal(str(fill[key])) for key in ('quantity', 'fill_price', 'mid_price'))
            rate = Decimal('0.001')
            if fill['side'] == 'buy':
                cash -= q * price
                holdings[symbol] += q * (1 - rate)
                fee += q * rate * mid
                assert fill['fee_asset'] == symbol[:-4]
            else:
                assert q <= holdings[symbol] + Decimal('1e-12')
                holdings[symbol] -= q
                cash += q * price * (1 - rate)
                fee += q * price * rate
                assert fill['fee_asset'] == 'USDT'
            execution += q * abs(price - mid)
            assert abs(float(cash) - fill['cash_after']) < 1e-7
            next_fill += 1
        nav = cash + sum(holdings[symbol] * Decimal(str(marks[symbol][row])) for symbol in common.SYMBOLS)
        peak = max(peak, nav)
        maximum_drawdown = max(maximum_drawdown, 1 - nav / peak)
        expected_nav.append(float(nav)); expected_cash.append(float(cash))
        for symbol in common.SYMBOLS:
            expected_quantity[symbol].append(float(holdings[symbol]))
    assert next_fill == len(trades)
    assert np.allclose(inventory['nav'].to_numpy(), expected_nav, rtol=0, atol=1e-7)
    assert np.allclose(inventory['cash'].to_numpy(), expected_cash, rtol=0, atol=1e-7)
    for symbol in common.SYMBOLS:
        assert np.allclose(inventory[symbol + '_quantity'].to_numpy(), expected_quantity[symbol], rtol=0, atol=1e-10)
    summary = ledger['summary']
    assert abs(summary['max_observed_minute_MDD'] - float(maximum_drawdown)) < 1e-12
    assert abs(summary['fees'] - float(fee)) < 1e-7
    assert abs(summary['execution_costs'] - float(execution)) < 1e-7
    assert abs(summary['final_nav'] - expected_nav[-1]) < 1e-7
    assert summary['same_quantity_gross_minus_cost_equals_net']
    assert summary['gross_reference_quantity_semantics'].startswith('NET_RECEIVED')
    assert summary['fee_cash_and_inventory_changes_native_rule']
    assert not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven']
