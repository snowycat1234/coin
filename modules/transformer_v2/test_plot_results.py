import numpy as np
from .plot_results import matrix

def test_figure_never_substitutes_winner_seed_or_partial_wallet():
    row=dict(family='CROSS_ASSET_UTILITY',mapping='NEUTRAL',funding_scale=1.,window='w',noncausal=False,full_calendar_and_paid_cash=True)
    dev=dict(rows=[dict(row,seed=20261006,net_return_percent=99.),dict(row,seed='ENSEMBLE',net_return_percent=-2.)])
    keys,values=matrix(dev,[],1.,['w','LOCKED'])
    assert values[keys.index(('CROSS_ASSET_UTILITY','NEUTRAL')),0]==-2.
    dev['rows'][-1]['full_calendar_and_paid_cash']=False
    assert np.isnan(matrix(dev,[],1.,['w','LOCKED'])[1]).all()
