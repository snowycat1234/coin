import numpy as np
from expert import DAY,targets,same_match_and_mix
def prices(n=450):
 t=np.arange(n,dtype=np.int64)*DAY;p=np.exp(np.arange(n)[:,None]*np.linspace(.0001,.001,5));return t,p
def test_yearhigh_geometry_is_not_365day_return_or_21day_return_and_futureprefix_exact():
 t,p=prices();p[:]=100;p[300,0]=300;p[345:,0]=130;p[345:,1]=110;p[345:,2]=90;p[345:,3]=80;p[345:,4]=70
 d=t[380:430];w,proof=targets(t,p,d);assert proof[0]['reference_score'][0]==130/300 and proof[0]['reference_score'][1]==1.
 assert p[380,0]/p[15,0]>p[380,1]/p[15,1] and proof[0]['reference_score'][0]<proof[0]['reference_score'][1]
 changed=p.copy();changed[t>t[400]]*=np.arange(2,7);other,_=targets(t,changed,d);np.testing.assert_array_equal(w[d<=t[400]],other[d<=t[400]])
def test_unavailable_365close_history_stays_unavailable_and_never_futurefilled():
 t,p=prices();p[100,2]=np.nan;w,proof=targets(t,p,t[380:430]);assert all(not r['current_eligible'][2] for r in proof) and np.all(w[:,2]==0)
 w,_=targets(t,p,t[200:220]);assert np.all(w==0)
def test_netting_keeps_common_risk_and_does_not_sum_independent_wallet_income():
 import importlib.util
 from pathlib import Path
 path=Path(__file__).resolve().parents[1]/'portfolio-risk-budget-20261012/risk_budget.py';s=importlib.util.spec_from_file_location('existing_risk_controller',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 cs=np.array([[.15,.15,0,-.15,-.15]]);h=np.full((1,5),.05);c=np.eye(5)[None,:,:]*.04;w,proof=same_match_and_mix(cs,h,c,m.scale)
 assert np.abs(w).sum()<=.6+1e-12 and np.abs(w).max()<=.3+1e-12 and proof[0]['joint']['post_sigma']<=.10+1e-12
