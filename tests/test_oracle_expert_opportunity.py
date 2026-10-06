"""Independent finite enumeration and full-capital shadow attribution checks."""
import itertools
import numpy as np
from scripts.investment.oracle_expert_opportunity import optimal_path,shadow_replay

def test_dp_matches_independent_enumeration_with_switch_cost_and_end_targets():
    growth=np.array([[1.02,.99,1.],[.98,1.03,1.],[1.02,.99,1.]])
    starts=np.array([[[.3],[-.3],[0.]]]*3)
    ends=starts*.9;rate=.00135;values=[]
    for path in itertools.product(range(3),repeat=3):
        wealth=1.
        for k,j in enumerate(path):
            if k and j!=path[k-1]:wealth*=1-abs(float(starts[k,j,0]-ends[k-1,path[k-1],0]))*rate
            wealth*=growth[k,j]
        values.append((wealth,path))
    expected=max(values,key=lambda v:v[0]);path,value=optimal_path(growth,starts,ends,rate)
    assert tuple(path)==expected[1] and abs(value-expected[0])<1e-14
    no_cost_path,no_cost=optimal_path(growth,starts,ends,0.)
    assert no_cost>=value and no_cost_path==[0,1,0]

def test_shadow_uses_single_capital_cost_and_signed_contribution():
    returns=np.array([[.02,-.01],[-.01,.03],[0.,0.]])
    directions=np.zeros((3,2,2));directions[0,:,0]=returns[0];directions[1,:,1]=returns[1]
    starts=np.array([[[.3],[-.3],[0.]]]*2);ends=starts.copy();bounds=[(0,1),(1,2)]
    costs=np.zeros((3,2,3));costs[0,0]=[.001,.002,.1];costs[1,1]=[.001,.002,.1]
    v=shadow_replay([0,1],returns,directions,starts,ends,bounds,.00135,costs)
    expected=10000*1.02*(1-.6*.00135)*1.03
    assert abs(v['terminal_shadow_wealth_USDT']-expected)<1e-10
    assert v['switches']==1 and abs(v['extra_switch_cost_USDT']-10200*.6*.00135)<1e-10
    assert abs(v['LONG']+v['SHORT']-v['extra_switch_cost_USDT']-v['net_shadow_USDT'])<1e-10
    # These costs are already inside the source returns; attribution only.
    assert abs(v['within_selected_expert_fees_shadow_USDT']-(10+10200*(1-.6*.00135)*.001))<1e-10
