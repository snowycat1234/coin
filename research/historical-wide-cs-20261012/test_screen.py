import importlib.util
import numpy as np
from screen import targets,quantity_proxy,risk,ROOT,DAY
from scripts.research.public_cross_section_momentum import public_targets

def test_N_risk_projection_and_future_mask_causality():
 rng=np.random.default_rng(711);t=1661990400000000+np.arange(100)*DAY;p=np.exp(np.cumsum(rng.normal(0,.02,(100,20)),axis=0))*10;d=t[40:80];names=tuple('C'+str(i)+'USDT' for i in range(20));w,_,_=targets(t,p,d,names,names);raw,_=public_targets(p,t,d,names,names)
 for i,at in enumerate(d):
  k=np.searchsorted(t,at);r=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];cov=np.cov(r,rowvar=False,ddof=1)*365;sig=np.sqrt(raw[i]@cov@raw[i]);gross=np.abs(raw[i]).sum();largest=np.abs(raw[i]).max();factor=min(.10/sig,.6/gross,.3/largest);np.testing.assert_allclose(w[i],raw[i]*factor,rtol=0,atol=1e-14)
 future=p.copy();future[t>d[20]]*=np.arange(2,22);a,_,_=targets(t,future,d,names,names);np.testing.assert_array_equal(a[d<=d[20]],w[d<=d[20]])
def test_original_CORE5_quantity_proxy_golden():
 spec=importlib.util.spec_from_file_location('unchanged_CORE5_reference_for_wide',ROOT/'research/cs-continuous-economics-20261012/core.py');original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
 d=1661990400000000+np.arange(5)*DAY;w=np.tile([.1,.1,-.1,-.1,0],(5,1));p0=np.arange(25).reshape(5,5)+30.;p1=p0+1;r,rows=quantity_proxy(d,w,p0,p1);q,old=original.quantity_reference(d,w,p0,p1,np.zeros_like(p0),np.ones_like(p0,bool),np.ones(5,bool));assert r['last_marked_NAV']==q['last_known_NAV'] and r['terminal_cost_proxy_USDT']==q['terminal_cost_USDT'];assert [a['nav_after'] for a in rows]==[a['nav_after'] for a in old]
def test_owned_missing_price_stops_without_free_flat_or_restart():
 d=1661990400000000+np.arange(3)*DAY;w=np.array([[.2,-.2],[0,0],[.2,-.2]]);p0=np.ones((3,2))*10;p1=p0.copy();p0[1,0]=np.nan;r,rows=quantity_proxy(d,w,p0,p1);assert r['completed_days']==1 and not r['hypothetical_cost_terminal'] and r['price_only_net_trading_cost_proxy_USDT'] is None and r['positions'][0]!=0 and r['stop'] is not None
