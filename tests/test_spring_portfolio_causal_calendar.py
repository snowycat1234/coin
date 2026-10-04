"""Only the newly wired four-month calendar and past200 eligibility boundary."""
from datetime import UTC,datetime,timedelta
import numpy as np
import polars as pl
import pytest
from scripts.investment import multi_asset_data as data
from scripts.investment import multi_asset_financial_audit as independent

def test_spring_complete_calendar_requires_200_past_days_and_rejects_future():
    start=datetime(2025,3,1,tzinfo=UTC);end=datetime(2025,7,1,tzinfo=UTC)
    spec=dict(start=start.isoformat(),end_exclusive=end.isoformat(),period_days=122,
        account_path='CONTINUOUS_SHARED_ACCOUNT_MAR_JUN_122D',
        data_role='SEEN_DEVELOPMENT_CONTINUOUS_THIRD_WINDOW_MANIFEST')
    scope=independent.calendar_scope(spec)
    assert (end-start).days==31+30+31+30==scope['period_days']==122
    assert scope['required_minutes']==122*24*60 and scope['calendar_months']==4
    assert scope['score_months']==['2025-03','2025-04','2025-05','2025-06']
    first=start;counts=[]
    while first<end:
        last=independent.next_month(first)
        counts.append((last-first).days)
        assert data.period_scope(int(first.timestamp())*1_000_000,int(last.timestamp())*1_000_000)==first.strftime('%Y-%m')
        first=last
    assert counts==[31,30,31,30]
    for wrong in (dict(period_days=121),dict(account_path='CONTINUOUS_SHARED_ACCOUNT_DEC_FEB_90D'),
                  dict(end_exclusive=(end+timedelta(days=1)).isoformat()),dict(data_role='UNSEEN')):
        with pytest.raises(ValueError):independent.calendar_scope(dict(spec,**wrong))
    start_us=int(start.timestamp())*1_000_000
    opens=np.arange(start_us-200*data.DAY,start_us,data.DAY,dtype=np.int64)
    bars=pl.DataFrame(dict(symbol=['BTCUSDT']*200,open_us=opens,close_us=opens+data.DAY,
        available_us=opens+data.DAY,close=np.linspace(90.,100.,200)))
    one=data.qualify_daily('BTCUSDT',bars,start_us=start_us)
    assert one['status']=='ELIGIBLE_PRE_SCORE_ONLY' and one['warmup_rows']==200
    assert one['latest_observed_close_us']==start_us
    # Sep-Feb has only181 days: earlier accepted daily sources are necessary.
    assert data.qualify_daily('BTCUSDT',bars.tail(181),start_us=start_us)['status']=='INELIGIBLE_WARMUP_OR_OBSERVED_AGE'
    assert data.qualify_daily('BTCUSDT',bars.filter(pl.col('open_us')!=int(opens[25])),start_us=start_us)['status']=='INELIGIBLE_WARMUP_OR_OBSERVED_AGE'
    future=pl.DataFrame(dict(symbol=['BTCUSDT'],open_us=[start_us],close_us=[start_us+data.DAY],
        available_us=[start_us+data.DAY],close=[999999.]))
    with pytest.raises(ValueError,match='No score prices'):
        data.qualify_daily('BTCUSDT',pl.concat([bars,future]),start_us=start_us)
    with pytest.raises(ValueError):data.entry('BTCUSDT','klines','1m','2026-03')
