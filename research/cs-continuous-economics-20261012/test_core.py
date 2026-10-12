import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import match,quantity_reference,DAY,ARMS

def fixture():
    t=np.arange(100,dtype=np.int64)*DAY;rng=np.random.default_rng(811710);p=100*np.exp(np.cumsum(rng.normal(0,.02,(100,5)),axis=0));d=t[65:90];v=np.full((25,5),.06);a=np.ones_like(v,bool);return t,p,d,v,a

def test_original_cs_suffix_invariant_and_same_risk_preserves_direction_and_caps():
    t,p,d,v,a=fixture();w,proof,_,diag=match(t,p,d,v,a);p2=p.copy();p2[t>d[9]]*=np.linspace(1.2,3.,int((t>d[9]).sum()))[:,None];other,_,_,_=match(t,p2,d,v,a)
    for arm in ARMS:np.testing.assert_array_equal(w[arm][:10],other[arm][:10]);assert np.abs(w[arm]).sum(1).max()<=.6+1e-12
    assert all(x['last_price_available_us']<=x['decision_us'] for x in proof)
    assert np.all(w['CS_MATCHED']*w['CS_ORIGINAL']>=0) and np.all(np.abs(w['CS_MATCHED'])<=np.abs(w['CS_ORIGINAL'])+1e-12)
    for j in range(len(d)):
        k=np.searchsorted(t,d[j]);r=np.diff(p[k-30:k+1],axis=0)/p[k-30:k];c=np.cov(r,rowvar=False)*365
        assert abs(w['CS_MATCHED'][j]@c@w['CS_MATCHED'][j]-w['VOL_MATCHED'][j]@c@w['VOL_MATCHED'][j])<1e-12

def test_current_missing_member_and_clock_are_cash_without_future_substitution():
    t,p,d,v,a=fixture();a[5,4]=False;w,proof,_,_=match(t,p,d,v,a)
    assert proof[5]['status']=='CURRENT_MEMBER_OR_PAST_RISK_UNREADY' and (w['CS_MATCHED'][5]==0).all() and (w['VOL_MATCHED'][5]==0).all()
    keep=t!=d[8];w,proof,_,_=match(t[keep],p[keep],d,v,a);assert proof[8]['status']=='MISSING_CURRENT_OR_PAST_CLOCK'

def test_owned_source_hole_stops_with_position_and_no_free_close_or_restart():
    d=np.arange(3)*DAY;w=np.zeros((3,5));w[:,0]=.1;p0=np.full((3,5),100.);p1=np.full((3,5),101.);fp=np.zeros((3,5));good=np.ones((3,5),bool);complete=np.array([True,False,True])
    report,rows=quantity_reference(d,w,p0,p1,fp,good,complete)
    assert len(rows)==1 and report['completed_days']==1 and not report['paid_terminal'] and report['positions'][0]==10. and report['net_USDT'] is None and report['terminal_cost_USDT']==0

def test_same_price_long_short_actual_funding_sign_and_paid_terminal_cost():
    d=np.array([0]);p=np.full((1,5),100.);fp=np.ones((1,5));w=np.zeros((1,5));w[0,0]=.1;w[0,1]=-.1
    report,rows=quantity_reference(d,w,p,p,fp,np.ones((1,5),bool),np.array([True]))
    assert report['paid_terminal'] and report['positions']==[0.]*5 and rows[0]['funding_cash']==0.
    assert abs(report['net_USDT']+5.4)<1e-9 # 2000 turnover entry plus charged exit

def test_terminal_cost_exhaustion_preserves_short_and_last_genuine_nav():
    d=np.array([0]);p0=np.full((1,5),100.);p1=p0.copy();p1[0,0]=433.19;w=np.zeros((1,5));w[0,0]=-.3
    report,rows=quantity_reference(d,w,p0,p1,np.zeros((1,5)),np.ones((1,5),bool),np.array([True]))
    assert report['stop']['reason']=='TERMINAL_COST_EXHAUSTS_NAV' and not report['paid_terminal']
    assert report['positions'][0]==-30. and report['last_known_NAV']>0 and report['terminal_cost_USDT']==0 and report['net_USDT'] is None
