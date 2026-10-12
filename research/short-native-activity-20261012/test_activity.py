import importlib.util
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('a',Path(__file__).with_name('activity.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fill(i,b,a,mid='10',fee='0',cost='0'):
    return dict(symbol='X',event_us=i,fill_id=str(i),decimal_strings=dict(quantity_before=str(b),quantity_after=str(a),position_delta=str(a-b),mid_price=mid,fee_amount=fee,execution_cost=cost))

def test_future_model_and_missing_date_cannot_be_native_causal_targets():
    d=np.arange(3)*86400000000;w=np.zeros((3,5))
    with pytest.raises(ValueError):m.targets(d,w,0,3*86400000000,1)
    with pytest.raises(ValueError):m.targets(d[[0,2]],w[[0,2]],0,3*86400000000,0)

def test_partial_short_adds_are_one_event_and_reopen_is_separate():
    t=[fill(1,0,-1),fill(2,-1,-2),fill(3,-2,0),fill(4,0,-1)]
    e,q=m.episodes(t,['X']);assert len(e)==2 and e[0]['fill_legs']==3 and e[1]['exit_us'] is None

def test_short_sale_proceeds_are_not_profit_and_paid_cost_is_once():
    t=[fill(1,0,-2,fee='1',cost='1')];e,q=m.episodes(t,['X'])
    p=m.nav_bridge(t,[],q,dict(X=10),'9998');assert p['gross_price_USDT']=='0' and p['fees_USDT']=='1'
    with pytest.raises(ValueError):m.nav_bridge(t,[],q,dict(X=10),'10018')
