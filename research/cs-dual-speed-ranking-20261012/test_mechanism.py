import importlib.util
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('mechanism',Path(__file__).with_name('mechanism.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def data():
    rng=np.random.default_rng(811710);t=np.arange(100,dtype=np.int64)*m.DAY;p=100*np.exp(np.cumsum(rng.normal(0,.02,(100,5)),axis=0));return t,p,t[31:]
def test_future_suffix_never_changes_past_targets_and_active_risk_is_matched():
    t,p,d=data();w,s,proof=m.targets(t,p,d);q=p.copy();q[70:]*=np.arange(1,6);v,_,_=m.targets(t,q,d)
    for a in m.ARMS:np.testing.assert_array_equal(w[a][d<t[70]],v[a][d<t[70]])
    for i,r in enumerate(proof):
        if r['exact_matched_when_all_active']:
            k=np.searchsorted(t,d[i]);ret=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];c=np.cov(ret,rowvar=False,ddof=1)*365
            for a in m.ARMS:assert abs(np.sqrt(max(0,w[a][i]@c@w[a][i]))-r['common_sigma'])<1e-12
def test_dual_is_not_skip_and_cash_does_not_zero_other_controls():
    t,p,d=data();w,s,_=m.targets(t,p,d);assert np.any(np.argsort(s['DUAL'],axis=1)!=np.argsort(s['SKIP'],axis=1))
    # Identical one-day/slow rankorder creates DUALcash; trendcontrol remains active.
    p=np.exp(np.arange(100)[:,None]*np.array([.001,.002,.003,.004,.005])[None,:]);w,s,proof=m.targets(t,p,t[50:51]);assert not w['DUAL'].any() and w['SLOW'].any() and 'DUAL' in proof[0]['cash']
