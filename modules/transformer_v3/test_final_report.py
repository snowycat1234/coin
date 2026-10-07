from .final_report import bridge_ranges,bridge_votes,choose_decision,DECISIONS
from .funding_bridge import SCENARIOS

def fixtures():
    rows=[]
    for n,scenario in enumerate(SCENARIOS):
        for scale in (1.,.01):
            for family in ('MODEL','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3'):
                net=(10.+n if family=='MODEL' else 2.)
                r=dict(family=family,mapping='DIRECTIONAL',profile='FULL',funding_scale=scale,scenario=scenario,
                    full_calendar_and_paid_cash=True,net_USDT=net,net_return_percent=net/100.,funding_USDT=0.,gross_price_USDT=net+1.,
                    fees_USDT=1.,execution_cost_USDT=0.,long_net_USDT=net,short_net_USDT=0.,liquidation_loss_USDT=0.,
                    liquidation_count=0,MDD=.01,realized_vol=.02,Sharpe=.5,mean_gross=.2)
                rows.append(r)
    return rows,dict(family='MODEL',mapping='DIRECTIONAL',profile='FULL')

def test_all_bridges_range_and_vote_are_economic_not_constant_qualification():
    rows,chosen=fixtures();group=next(g for g in bridge_ranges(rows) if g['family']=='MODEL' and g['funding_scale']==1.)
    assert group['statistics']['net_USDT']==dict(min=10.,median=12.,max=14.,observations=5)
    assert group['missing_funding_total_economic_range_USDT']==4.
    votes=bridge_votes(rows,chosen);assert all(v['economic_vote']=='PASS' for v in votes)
    rows[0]['net_return_percent']=-1.
    votes=bridge_votes(rows,chosen)
    assert votes[0]['economic_vote']=='FAIL' and len({v['economic_vote'] for v in votes})==2

def test_incomplete_bridge_keeps_ne_and_prohibits_unknown_true_rate_bound():
    rows,chosen=fixtures();rows[0].update(full_calendar_and_paid_cash=False,net_USDT=None,net_return_percent=None)
    group=next(g for g in bridge_ranges(rows) if g['family']=='MODEL' and g['funding_scale']==1.)
    assert not group['complete_all_five'] and group['missing_funding_total_economic_range_USDT'] is None
    assert group['statistics']['net_USDT']['observations']==4
    assert bridge_votes(rows,chosen)[0]['economic_vote']=='NOT_EVALUABLE'

def test_fixed_final_decision_does_not_promote_on_profit_or_certification_alone():
    rows,chosen=fixtures();votes=bridge_votes(rows,chosen)
    dev=dict(development_gate_pass=True)
    assert choose_decision(dev,dict(actionable_descriptive_signal=True),votes,False)==DECISIONS[1]
    assert choose_decision(dev,dict(actionable_descriptive_signal=True),votes,True)==DECISIONS[0]
    assert choose_decision(dict(development_gate_pass=False),dict(actionable_descriptive_signal=False),votes,True)==DECISIONS[2]
