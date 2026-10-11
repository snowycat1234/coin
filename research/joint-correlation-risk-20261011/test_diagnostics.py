import numpy as np
from diagnostics import proportional_controls,portfolio_variance,turnover,economy,prediction


def test_static_train_control_cannot_see_diagnostic_variance():
    n=400;train=np.arange(n)<200
    b=np.tile(np.array([.1,.1,-.1,-.1,0]),(n,1));s=np.linspace(.4,1,n);j=b*s[:,None]
    c=np.tile(np.eye(5)*.001,(n,1,1))
    a,m=proportional_controls(b,j,s,train,c)
    changed=c.copy();changed[~train]*=1000
    aa,mm=proportional_controls(b,j,s,train,changed)
    assert m==mm;np.testing.assert_array_equal(a,aa)
    assert turnover(b)==.8 # Initial and terminal are each .4.
    np.testing.assert_allclose(portfolio_variance(b*.5,c),portfolio_variance(b,c)*.25)


def test_smaller_gross_alone_cannot_pass_normalized_tail_gate():
    rng=np.random.default_rng(33);r=rng.normal(0,.002,(120,288,5))
    b=np.tile([.1,.1,-.1,-.1,0],(120,1));targets=np.stack([b,b*.5,b*.5,b*.5],axis=1)
    roles=np.array(['A']*60+['B']*60)
    report=economy(targets,roles,r)
    assert not report['passed']
    for block in report['blocks'].values():
        assert np.isclose(block['ratios']['actual_variance_ratio'],.25)
        assert np.isclose(block['ratios']['risk_normalized_ES95_ratio'],1)
        assert not block['gates']['risk_normalized_tail_improvement_5pct']


def test_native_win_cannot_hide_failure_against_strong_reference():
    actual=np.tile(np.eye(5),(120,1,1))
    def common(x):return np.eye(5)*(1-x)+np.ones((5,5))*x
    predicted=np.tile(np.stack([common(.8),common(.2),common(.02),common(.7),common(.01)]),(120,1,1,1))
    roles=np.array(['A']*60+['B']*60)
    report,loss=prediction(predicted,actual,roles)
    assert not report['passed']
    for b in report['blocks'].values():
        assert b['gates']['native_improvement_2pct'] and b['gates']['native_CI_upper_negative']
        assert not b['gates']['pure_realized30_not_worse_2pct']
