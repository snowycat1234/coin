import numpy as np
from core import DAY,daily_rates,directions,reference,risk

def test_day_gap_is_unknown_and_actual_zero_is_known():
    t=np.arange(0,3*DAY,DAY//3,dtype=np.int64)+8000;r=np.zeros(9);h=np.full(9,8.)
    v,_=daily_rates(t,r,h,np.arange(0,3*DAY,DAY));assert np.array_equal(v,np.zeros(3))
    v,_=daily_rates(np.delete(t,4),np.delete(r,4),np.delete(h,4),np.arange(0,3*DAY,DAY));assert np.isnan(v[1]) and v[0]==v[2]==0

def test_one_full_day_lag_and_future_unknown_suffix():
    days=np.arange(50)*DAY;v=np.full((50,5),.0003);d=np.arange(22,45)*DAY
    base,means,known=directions(days,v,d);assert (base==-1).all() and known.all()
    v[21:,0]=np.nan;alt,_,_=directions(days,v,d);np.testing.assert_array_equal(alt[0],base[0]);assert alt[1,0]==0
    v=np.full((50,5),.0003);v[22:]=-10;alt,_,_=directions(days,v,d);np.testing.assert_array_equal(alt[:2],base[:2])

def test_raw_rate_sign_cost_terminal_and_held_unknown_failure():
    days=np.arange(45)*DAY;v=np.full((45,5),.0003);v[:,1]=-.0003;v[:,2]=0
    intent,_,_=directions(days,v,np.array([22*DAY]));np.testing.assert_array_equal(intent[0],[-1,1,0,-1,-1])
    w=np.zeros((2,5));w[:,0]=-.12;p=np.ones((2,5))*100;fp=np.ones((2,5))*.02
    result,rows=reference(np.array([0,DAY]),w,p,p,fp,np.ones((2,5),bool));assert result['hypothetical_cost_terminal'] and result['funding_cash']>0 and result['trading_cost']>0
    fp[0,0]=np.nan;result,_=reference(np.array([0,DAY]),w,p,p,fp,np.ones((2,5),bool));assert result['days']==0 and result['net_USDT'] is None

def test_same_controller_golden_and_intrinsic_cash():
    c=np.eye(5)*.04;short=np.full(5,-.12);scaled,q=risk.scale(short,c);assert np.abs(scaled).sum()<=.6+1e-12 and q['post_sigma']<=.10+1e-12
    cash,q=risk.scale(np.zeros(5),c);assert not cash.any() and q['reason']=='INTRINSIC_CASH'
