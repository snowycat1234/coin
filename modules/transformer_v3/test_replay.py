from .replay import same_complete_economics

def test_parity_requires_costs_funding_and_real_cash_not_just_same_terminal_net():
    a=dict(NAV=10001.,net_PnL=1.,fees_USDT=2.,execution_cost_USDT=3.,funding_USDT=-4.,gross_fill_turnover_USDT=1000.,completed_minutes=10,required_minutes=10,terminal_cash_realized=True)
    assert same_complete_economics(a,a)
    assert not same_complete_economics(a,dict(a,funding_USDT=-5.))
    assert not same_complete_economics(a,dict(a,terminal_cash_realized=False))
