"""One saved-metadata residual-inventory fixture; no account or market replay."""
from copy import deepcopy

import pytest

from scripts.investment import compare_multi_asset_portfolios as compare
from scripts.investment import multi_asset_portfolio as portfolio


def test_residual_marked_bridge_and_closed_account_scope(monkeypatch):
    # Shared 10k: one long remains q=1 at entry100, mark90. Execution2 is
    # already included in the fill entry. Net=-10-1+fund3=-8; gross=-10+2=-8.
    summary = dict(net_PnL=-8.0, gross_PnL_same_quantities=-8.0,
        completed_minutes=12, required_minutes=12,
        unrealized_PnL=-10.0, terminal_marked_notional=90.0,
        terminal_cash_realized=False,
        positions={
            'BTCUSDT': dict(quantity=99.0, entry_price=999.0,
                decimal_strings=dict(quantity='1', entry_price='100')),
            'ETHUSDT': dict(quantity=0.0, entry_price=0.0,
                decimal_strings=dict(quantity='0', entry_price='0'))},
        terminal_mark_prices=dict(BTCUSDT=90.0, ETHUSDT=None),
        net_return_on_full_initial_capital_percent=-0.08,
        fees_USDT=1.0, execution_cost_USDT=2.0, funding_USDT=3.0,
        normalized_total_turnover=0.01, daily_metrics=dict(annual_volatility=0.1),
        minute_max_drawdown=0.01, realized_exposure={}, daily_net_gain_concentration={})
    case = dict(symbols=['BTCUSDT', 'ETHUSDT'], summary=summary,
        artifacts={'trades.json': dict(path='synthetic-trades', sha256='synthetic'),
                   'funding.json': dict(path='synthetic-funding', sha256='synthetic')})
    trades = [dict(symbol='BTCUSDT', realized_PnL=0.0, fee_USDT_mid=1.0,
        execution_cost=2.0, quantity=99.0, fill_price=999.0,
        decimal_strings=dict(realized_PnL='0', fee_USDT_mid='1',
            execution_cost='2', quantity='1', fill_price='100'))]
    funding = [dict(symbol='BTCUSDT', signed_funding_USDT=3.0,
        decimal_strings=dict(signed_funding_USDT='3'))]
    original = deepcopy((case, trades, funding))
    monkeypatch.setattr(compare, 'read', lambda path, digest: (
        trades if path=='synthetic-trades' else funding))
    marked = compare.measures(case)
    asset = marked['asset_contributions']['BTCUSDT']
    assert asset['gross_USDT'] == -8.0
    assert asset['net_USDT'] == -11.0 + 3.0
    assert asset['terminal_quantity'] == 1.0
    assert asset['terminal_entry_price'] == 100.0
    assert asset['terminal_marked_notional_USDT'] == 90.0
    assert asset['terminal_unrealized_PnL_USDT'] == -10.0
    assert asset['net_contribution_full_capital_percent'] == -0.08
    assert marked['terminal_quantities'] == {'BTCUSDT': '1', 'ETHUSDT': '0'}
    assert marked['liquidated_return'] == 'NOT_EVALUABLE'
    assert marked['liquidated_return_full_capital_percent'] is None
    assert not marked['terminal_cash_realized']
    assert marked['asset_contributions']['ETHUSDT']['net_USDT'] == 0.0
    marked_scope = portfolio.terminal_evaluation_scope([case])
    assert marked_scope == dict(calendar_complete_cases=1, terminal_cash_realized_cases=0,
        liquidated_portfolio_return='NOT_EVALUABLE', marked_NAV_includes_unrealized=True)
    assert (case, trades, funding) == original

    # Same saved quantities subsequently closed at entry100 with zero added
    # synthetic charges: realized0, unrealized0, net2, gross2. Closed semantics
    # remain evaluable, and the residual must not silently disappear beforehand.
    closed = deepcopy(case)
    closed['summary'].update(net_PnL=2.0, gross_PnL_same_quantities=2.0,
        unrealized_PnL=0.0, terminal_marked_notional=0.0,
        terminal_cash_realized=True, net_return_on_full_initial_capital_percent=0.02)
    closed['summary']['positions']['BTCUSDT'] = dict(quantity=0.0, entry_price=0.0,
        decimal_strings=dict(quantity='0', entry_price='0'))
    closed_trades = [*trades, dict(symbol='BTCUSDT', realized_PnL=0.0,
        fee_USDT_mid=0.0, execution_cost=0.0, quantity=1.0, fill_price=100.0)]
    monkeypatch.setattr(compare, 'read', lambda path, digest: (
        closed_trades if path=='synthetic-trades' else funding))
    result = compare.measures(closed)
    assert result['net_USDT'] == result['asset_contributions']['BTCUSDT']['net_USDT'] == 2.0
    assert result['gross_USDT'] == result['asset_contributions']['BTCUSDT']['gross_USDT'] == 2.0
    assert result['liquidated_return'] == 'EVALUABLE_SAVED_CLOSED_ACCOUNT'
    assert result['liquidated_return_full_capital_percent'] == 0.02
    closed_scope = portfolio.terminal_evaluation_scope([closed])
    assert closed_scope == dict(calendar_complete_cases=1, terminal_cash_realized_cases=1,
        liquidated_portfolio_return='COMPLETE_CONDITIONAL_CASH_RETURN_NOT_NATIVE_OR_APR',
        marked_NAV_includes_unrealized=True)
    inconsistent = deepcopy(case)
    inconsistent['summary']['terminal_cash_realized'] = True
    with pytest.raises(ValueError, match='Terminal cash identity'):
        compare.asset_contributions_from_rows(inconsistent, trades, funding)
    wrong_bridge = deepcopy(case)
    wrong_bridge['summary']['net_PnL'] += 0.000001
    with pytest.raises(ValueError, match='full account net bridge'):
        compare.asset_contributions_from_rows(wrong_bridge, trades, funding)
