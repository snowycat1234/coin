import copy
from .report import compare,BASELINES,compact_case

def test_rank_uses_worst_funding_and_retains_all_seed_evidence():
    rows=[];protocol=dict(models=['A','B'],seeds=[1,2,3])
    for scale in (1.,.01):
      for i in range(6):
        window=f'w{i}'
        for baseline in (*BASELINES,'OLD_FROZEN_TRANSFORMER_SHARED'):
            rows.append(dict(family=baseline,seed='FROZEN_LEGACY',mapping='DIRECTIONAL',funding_scale=scale,window=window,net_return_percent=0,full_calendar_and_paid_cash=True))
        for family in protocol['models']:
          for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
            value=(10 if scale==1 else -1) if family=='A' else 1+i*.01
            for seed in (1,2,3,'ENSEMBLE'):
                rows.append(dict(family=family,seed=seed,mapping=mapping,funding_scale=scale,window=window,net_return_percent=value,full_calendar_and_paid_cash=True))
    before=copy.deepcopy(rows);summaries,paired,chosen=compare(rows,protocol)
    assert chosen['family']=='B' and chosen['development_gate_pass']
    assert rows==before and len(paired)==72

def test_signed_funding_is_an_expense_when_negative_and_credit_when_positive():
    s=dict(net_PnL=85.,net_return_on_full_initial_capital_percent=.85,fees_USDT=10.,execution_cost_USDT=2.,spread_cost_USDT=1.,slippage_cost_USDT=1.,
           funding_USDT=-3.,gross_fill_turnover_USDT=1000.,long_short_marked_contribution=dict(LONG=dict(gross=100.,net_contribution=85.),SHORT=dict(gross=0.,net_contribution=0.)))
    case=dict(summary=s,task=dict(family='A',seed='ENSEMBLE',mapping='DIRECTIONAL',funding_scale=1.,window=dict(id='test',days=1)),
              economic_calendar_complete=True,terminal_cash_realized=True,independent_audit=dict(maximum_NAV_error_USDT=0.),summary_sha256='test')
    row=compact_case(case)
    assert row['gross_price_return_percent']==1. and row['cost_share_of_positive_gross']==.12 and row['cost_plus_net_funding_share_of_positive_gross']==.15
    s.update(funding_USDT=3.,net_PnL=91.);s['long_short_marked_contribution']['LONG']['net_contribution']=91.
    assert compact_case(case)['cost_plus_net_funding_share_of_positive_gross']==.09
