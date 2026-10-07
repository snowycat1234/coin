import numpy as np
import pandas as pd
import pytest
from .locked_bridge_data import RECOVERY_DAY,EVENT_MS,merge_recovered_day,insert_estimated_event

def test_exact_recovered_price_day_merges_only_real_minutes_and_detects_conflict():
    times=np.arange(RECOVERY_DAY.value//1_000_000,(RECOVERY_DAY+pd.Timedelta(days=1)).value//1_000_000,60000)
    q=pd.DataFrame(dict(timestamp_ms=times,open=1.,high=1.,low=1.,close=1.))
    assert len(merge_recovered_day(q.iloc[:4],q))==1440
    with pytest.raises(ValueError,match='1440'):merge_recovered_day(q.iloc[:0],q.iloc[:-1])
    broken=q.iloc[:4].copy();broken.loc[0,'close']=2.
    with pytest.raises(ValueError,match='conflict'):merge_recovered_day(broken,q)

def test_estimated_funding_is_explicit_separate_event_and_never_overwrites_observation():
    events=pd.DataFrame(dict(symbol=['WIFUSDT']*2,calc_time_ms=[EVENT_MS-4*3600000,EVENT_MS+4*3600000],funding_interval_hours=[4,4],last_funding_rate=[.01,.03],raw_rate_unit=['UNCONFIRMED']*2))
    row=dict(symbol='WIFUSDT',event_us=EVENT_MS*1000,scenario='LINEAR_INTERPOLATION',exact_Binance_settlement=False,engine_raw_rate=.02,role='IMPUTED_UNCONFIRMED_EVENT_SENSITIVITY')
    result=insert_estimated_event(events,row)
    r=result.loc[result.calc_time_ms.eq(EVENT_MS)].iloc[0]
    assert r.last_funding_rate==.02 and not r.event_observed and 'IMPUTED' in r.event_source_role
    assert len(events)==2 and len(result)==3
    with pytest.raises(ValueError,match='actual exact'):insert_estimated_event(result,row)
    with pytest.raises(ValueError,match='frozen'):insert_estimated_event(events,dict(row,symbol='OTHER_EXCHANGE_BTC'))
