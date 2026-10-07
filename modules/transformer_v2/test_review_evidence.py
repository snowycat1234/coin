from .review_evidence import completion_counts,worst_windows

def test_completion_counts_keep_halted_accounts_and_both_units():
    rows=[dict(funding_scale=1.,native_completion='HALTED'),dict(funding_scale=.01,native_completion='COMPLETE')]
    assert sum(r['count'] for r in completion_counts(rows))==2
    assert {r['completion'] for r in completion_counts(rows)}=={'HALTED','COMPLETE'}

def test_worst_window_excludes_partial_account_and_other_seed():
    base=dict(family='A',seed='ENSEMBLE',mapping='DIRECTIONAL',funding_scale=1.,full_calendar_and_paid_cash=True,
              window='past',net_USDT=-3.,net_return_percent=-.03,long_net_USDT=-4.,short_net_USDT=1.,gross_price_USDT=-2.,
              fees_USDT=1.,spread_USDT=0.,slippage_USDT=0.,funding_USDT=0.,mean_gross=.3,mean_signed_exposure=.2)
    rows=[base,dict(base,window='partial',full_calendar_and_paid_cash=False,net_USDT=-999.),dict(base,seed='BEST_SEED',net_USDT=-888.)]
    answer=worst_windows(rows,dict(family='A',mapping='DIRECTIONAL'))
    assert len(answer)==1 and answer[0]['window']=='past' and answer[0]['short_net_USDT']==1.
