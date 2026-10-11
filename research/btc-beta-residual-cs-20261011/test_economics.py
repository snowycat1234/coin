"""Thin financial adapter counterexamples; mature finance source is untouched."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import economics as e


def test_saved_target_calendar_order_and_no_refit():
    saved = {'symbol_order': np.asarray(e.SYMBOLS),
             'decision_us': np.arange(e.START, e.END, e.DAY),
             'ready': np.ones(63, dtype=bool), 'raw': np.zeros((63, 5))}
    saved['raw'][:, 0] = -.02
    saved['raw'][:, 1] = .02
    factory = e.saved_factory(saved, 'raw')
    frame, meta = factory(None, saved['decision_us'], 'LONG_SHORT')
    assert frame.height == 315 and meta['signal_fit_in_wallet'] is False
    assert frame.filter(pl.col('symbol') == 'BTCUSDT')['target_weight'].to_list() == [-.02] * 63
    bad = {**saved, 'symbol_order': saved['symbol_order'][::-1]}
    with pytest.raises(ValueError, match='coordinates'):
        e.saved_factory(bad, 'raw')
    with pytest.raises(ValueError, match='window'):
        factory(None, saved['decision_us'][:-1], 'LONG_SHORT')


def test_joint_bootstrap_units_identical_indices():
    a = np.arange(63, dtype=float) - 27
    interval = e.paired_bootstrap(np.column_stack([a, 3 * a]))
    assert np.allclose(interval[1], 3 * interval[0])
    assert np.array_equal(interval, e.paired_bootstrap(np.column_stack([a, 3 * a])))


def test_price_cash_attribution_retains_short_hedge_cost_and_funding():
    trades = [dict(symbol='BTCUSDT', position_delta=-2., mid_price=10., fee_USDT_mid=.2, execution_cost=.1),
              dict(symbol='BTCUSDT', position_delta=2., mid_price=12., fee_USDT_mid=.24, execution_cost=.12),
              dict(symbol='ETHUSDT', position_delta=1., mid_price=10., fee_USDT_mid=.1, execution_cost=.05),
              dict(symbol='ETHUSDT', position_delta=-1., mid_price=15., fee_USDT_mid=.15, execution_cost=.075)]
    funds = [dict(symbol='BTCUSDT', signed_funding_USDT=.3), dict(symbol='ETHUSDT', signed_funding_USDT=-.1)]
    expected = -4 - .44 - .22 + .3 + 5 - .25 - .125 - .1
    summary = dict(terminal_signed_marked_notional=dict.fromkeys(e.SYMBOLS, 0.), net_PnL=expected)
    result = e.asset_attribution(trades, funds, summary)
    assert result['BTC_hedge_gross_price_USDT'] == -4
    assert result['alt_gross_price_USDT'] == 5
    assert result['assets']['BTCUSDT']['net_contribution_USDT'] == pytest.approx(-4.36)
    assert result['full_wallet_bridge_error_USDT'] < 1e-12
    with pytest.raises(ValueError, match='disagree'):
        e.asset_attribution(trades, funds, {**summary, 'net_PnL': expected + .01})


def test_missing_saved_decision_cannot_delete_future_label_or_fill():
    saved = {'symbol_order': np.asarray(e.SYMBOLS), 'decision_us': np.arange(e.START, e.END, e.DAY),
             'ready': np.ones(63, dtype=bool), 'raw': np.zeros((63, 5))}
    saved['ready'][31] = False
    with pytest.raises(ValueError, match='Complete causal'):
        e.saved_factory(saved, 'raw')


def test_bybit_shared_cash_hedge_cost_owned_funding_and_charged_terminal(tmp_path):
    from scripts.investment import perpetual_directional as kernel
    from quant.bybit_isolated_account import BybitIsolatedAccount
    from modules.transformer_v3.isolated_audit import verify
    n = 12
    start = e.START - n * e.MINUTE  # Include an actual UTC day endpoint for save_case.
    market = {s: dict(open=np.full(n, 100.), close=np.full(n, 100.),
                      mark=np.full(n, 100.), quote_volume=np.full(n, 100000000.)) for s in e.SYMBOLS}
    daily = pl.DataFrame([dict(symbol=s, close_us=start, close=100.) for s in e.SYMBOLS])

    def factory(_daily, decisions, mode):
        rows = [dict(symbol=s, available_us=int(t), target_weight=(-.1 if s == 'BTCUSDT' else
                .1 if s == 'ETHUSDT' else 0.)) for t in decisions for s in e.SYMBOLS]
        return pl.DataFrame(rows), dict(scope='SYNTHETIC_COST_AND_HEDGE_COUNTEREXAMPLE')

    events = [dict(symbol=s, event_us=start + 3 * e.MINUTE + 1000,
                   raw_rate=.001, reported_interval_hours=8.) for s in e.SYMBOLS[:2]]
    window = dict(symbols=e.SYMBOLS, start=start, end=start + n * e.MINUTE,
                  daily=daily, market=market, events=events)
    case = kernel.simulate(window, 'LONG_SHORT', kernel.COSTS[0], kernel.UNITS[0],
                           target_factory=factory, account_factory=BybitIsolatedAccount,
                           persist_cash_close=True)
    directory = tmp_path / 'case'
    summary = kernel.save_case(case, directory)['summary']
    e.save(directory / 'summary.json', summary)
    audit = verify(directory, e.SYMBOLS, 1.)
    assert audit['status'].startswith('PASS') and summary['terminal_cash_realized']
    assert summary['liquidation_count'] == 0 and len(case['trades']) == 4
    assert summary['net_PnL'] == pytest.approx(-5.346, abs=1e-10)
    assert summary['funding_USDT'] == pytest.approx(0.)
    assert case['funding'][0]['quantity'] < 0 and case['funding'][1]['quantity'] > 0
    result = e.asset_attribution(case['trades'], case['funding'], summary)
    assert result['assets']['BTCUSDT']['fees_USDT'] > 0
    assert result['assets']['BTCUSDT']['execution_USDT'] > 0
    terminal = [r for r in case['trades'] if r['signal_us'] == start + 6 * e.MINUTE]
    assert len(terminal) == 2 and all(r['leg'] == 'CLOSE' for r in terminal)
