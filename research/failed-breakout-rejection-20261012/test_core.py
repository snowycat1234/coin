import numpy as np
from core import DAY,rejection,targets

def base():return np.full(21,110.),np.full(21,90.),np.full(21,100.),np.ones(21,bool)

def test_rejected_breach_differs_from_accepted_close_breakout():
    h,l,c,r=base();h[-1]=120;assert rejection(h,l,c,r)==(-1,'UPPER_BREAK_REJECTED')
    c[-1]=115;assert rejection(h,l,c,r)==(0,'NO_REJECTED_BREAK')
    h,l,c,r=base();l[-1]=80;assert rejection(h,l,c,r)==(1,'LOWER_BREAK_REJECTED')

def test_ambiguous_path_and_unknown_are_cash_not_fabricated_order():
    h,l,c,r=base();h[-1]=120;l[-1]=80;assert rejection(h,l,c,r)==(0,'BOTH_SIDES_ORDER_UNKNOWN')
    r[5]=False;assert rejection(h,l,c,r)==(0,'UNKNOWN_SOURCE')
    h,l,c,r=base();h[0]=np.nan;assert rejection(h,l,c,r)==(0,'UNKNOWN_SOURCE')

def test_channel_excludes_event_and_strict_boundary_has_no_threshold():
    h,l,c,r=base();h[-1]=111;c[-1]=110;assert rejection(h,l,c,r)==(0,'NO_REJECTED_BREAK')
    c[-1]=109.999;assert rejection(h,l,c,r)[0]==-1
    h[-1]=110;assert rejection(h,l,c,r)[0]==0

def test_future_ohlc_nan_prefix_and_exact_sign_opposite_risk():
    t=np.arange(100,dtype=np.int64)*DAY;h=np.full((100,5),110.);l=np.full_like(h,90.);c=np.full_like(h,100.);ready=np.ones_like(h,bool);h[35,0]=120;l[35,1]=80
    prices=np.exp(np.arange(100)[:,None]*.001+np.sin(np.arange(100)[:,None]*np.arange(1,6)*.2)*.03)*100;d=t[31:80]
    out,proof=targets(t,h,l,c,ready,t,prices,d);np.testing.assert_array_equal(out['FADE'],-out['FOLLOW']);assert (out['FADE'][4]!=0).sum()==2
    h[t>t[50]]=np.nan;l[t>t[50]]=np.nan;c[t>t[50]]=np.nan;ready[t>t[50]]=False;prices[t>t[50]]*=100
    alt,_=targets(t,h,l,c,ready,t,prices,d)
    for arm in out:np.testing.assert_array_equal(alt[arm][d<=t[50]],out[arm][d<=t[50]])
