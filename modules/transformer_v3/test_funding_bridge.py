import numpy as np,pytest
from .funding_bridge import formula_1minute,scenario_rates,SCENARIOS,premium_period
import pandas as pd

def test_formula_uses_ordinal_weights_and_registered_four_hour_formula():
    average,rate=formula_1minute(np.full(240,.0002))
    assert np.isclose(average,.0002) and np.isclose(rate,.00005)
    first=np.zeros(240);last=first.copy();first[0]=.001;last[-1]=.001
    assert formula_1minute(last)[0]>formula_1minute(first)[0]
    with pytest.raises(ValueError):formula_1minute(np.full(240,np.nan))
    with pytest.raises(ValueError):formula_1minute(np.zeros(241))

def test_formula_fraction_is_not_accidentally_percent_scaled_and_every_bridge_retained():
    a=scenario_rates(.02,.04,np.full(240,.0002),1.)
    b=scenario_rates(.02,.04,np.full(240,.0002),.01)
    assert tuple(r['scenario'] for r in a)==SCENARIOS
    assert a[1]['engine_raw_rate']==.03 and b[1]['normalized_rate_fraction']==.0003
    assert np.isclose(a[-1]['normalized_rate_fraction'],b[-1]['normalized_rate_fraction'])
    assert not any(r['exact_Binance_settlement'] for r in a+b)

def test_real_premium_schema_and_exclusive_funding_boundary():
    clock=np.arange(1782259200000,1782273600000+60000,60000)
    frame=pd.DataFrame(dict(timestamp_ms=clock,available_us=(clock+60000)*1000,close=np.r_[np.full(240,.0002),99.]))
    assert np.allclose(premium_period(frame),.0002)
    with pytest.raises(ValueError):premium_period(frame.drop(index=3))
