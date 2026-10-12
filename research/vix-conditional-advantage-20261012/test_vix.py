import numpy as np
import pytest
from vix import START,END,DAY,parse,feature
def test_actual_missing_holiday_preserved_and_denied_future_date_rejected_before_values():
 t,v=parse(b'observation_date,VIXCLS\n2021-03-01,20\n2021-03-02,.\n2021-03-03,22\n');assert np.isnan(v[1]) and len(t)==3
 with pytest.raises(AssertionError,match='outside'):parse(b'DATE,VIXCLS\n2026-03-01,not-read\n')
 with pytest.raises(AssertionError,match='Unique'):parse(b'DATE,VIXCLS\n2021-03-01,20\n2021-03-01,21\n')
def test_conservative_clock_holiday_carry_age_and_future_observation_do_not_leak():
 t=np.array([START,START+DAY,START+7*DAY]);v=np.array([20.,np.nan,99.]);d=START+np.arange(1,11)*DAY;x,p=feature(d,t,v)
 assert np.isnan(x[0]) and x[1]==20 and x[5]==20 and np.isnan(x[6]) and x[8]==99
 assert all(r.get('available_proxy_us',0)<=r['decision_us'] for r in p)
 alt=v.copy();alt[-1]=10000;other,_=feature(d,t,alt);np.testing.assert_array_equal(x[:8],other[:8])
