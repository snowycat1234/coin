"""Small standalone source parser. No strategy, provider, account, or wallet code."""
import csv,datetime,hashlib,io,json,zipfile
import numpy as np
import pandas as pd
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
MINUTE=60000000;DAY=86400000000;START=1609459200000000;END=1640995200000000
COLS=['timestamp_ms','open','high','low','close','volume','close_time_ms','quote_volume','trades','taker_buy_volume','taker_buy_quote_volume','ignore']
ALIASES=[{'open_time','open_timestamp'},{'open'},{'high'},{'low'},{'close'},{'volume'},{'close_time','close_timestamp','close_time_ms'},{'quote_volume','quote_asset_volume'},{'count','trades','number_of_trades'},{'taker_buy_volume','taker_buy_base_asset_volume'},{'taker_buy_quote_volume','taker_buy_quote_asset_volume'},{'ignore'}]
def sha(b):return hashlib.sha256(b).hexdigest()
def limits(year,month):
    left=int(datetime.datetime(year,month,1,tzinfo=datetime.UTC).timestamp()*1e6);right=int(datetime.datetime(year+(month==12),month%12+1,1,tzinfo=datetime.UTC).timestamp()*1e6);return left,right
def utc(t):return datetime.datetime.fromtimestamp(int(t)/1e6,datetime.UTC).isoformat()
def parse_zip(body,family,left_us,right_us):
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        assert z.testzip() is None
        assert len(z.namelist())==1,'Expected one original CSV member'
        csv_name=z.namelist()[0];raw=z.read(csv_name)
    f=pd.read_csv(io.BytesIO(raw),header=None,dtype=str,keep_default_na=False,encoding='utf-8-sig')
    assert f.shape[1]==12 and not f.empty,'Expected twelve original price columns'
    first=str(f.iloc[0,0]).strip().lower().replace(' ','_');header_present=first in ALIASES[0]
    if header_present:
        names=[str(v).strip().lower().replace(' ','_') for v in f.iloc[0]]
        assert all(v in a for v,a in zip(names,ALIASES)),'Unsupported/reordered source schema'
        f=f.iloc[1:].copy()
    assert not f.empty
    f=f.apply(pd.to_numeric,errors='raise');f.columns=COLS
    assert np.isfinite(f.to_numpy(dtype=float)).all(),'Nonfinite source row'
    # Identical repeated source rows are harmless; conflicting clocks stop.
    before=len(f);f=f.drop_duplicates();assert not f.timestamp_ms.duplicated().any(),'Conflicting duplicate timestamp'
    f=f.sort_values('timestamp_ms').reset_index(drop=True)
    t=f.timestamp_ms.to_numpy(dtype=float);ct=f.close_time_ms.to_numpy(dtype=float)
    assert ((t==np.floor(t))&(t>=left_us//1000)&(t<right_us//1000)&(t%60000==0)).all(),'Original timestamp must be epoch milliseconds'
    assert (ct==t+59999).all(),'Original close_time must be open+59999ms'
    assert (f[['open','high','low','close']]>0).all().all(),'Nonpositive actual price'
    assert ((f.low<=f[['open','close']].min(axis=1))&(f.high>=f[['open','close']].max(axis=1))&(f.low<=f.high)).all(),'Invalid OHLC envelope'
    if family=='klines':
        assert (f[['volume','quote_volume','trades','taker_buy_volume','taker_buy_quote_volume']]>=0).all().all()
        assert (f.trades==np.floor(f.trades)).all(),'Nonintegral trade count'
    else:assert family=='markPriceKlines'
    f['timestamp_ms']=f.timestamp_ms.astype(np.int64);f['close_time_ms']=f.close_time_ms.astype(np.int64)
    return f,dict(CSV_member=csv_name,CSV_SHA256=sha(raw),CSV_bytes=len(raw),numeric_rows=len(f),identical_duplicates_removed=before-len(f),header_present=header_present)
def union_exact(month,daily):
    common=np.intersect1d(month.timestamp_ms.to_numpy(),daily.timestamp_ms.to_numpy())
    m=month.set_index('timestamp_ms').loc[common];d=daily.set_index('timestamp_ms').loc[common]
    assert np.array_equal(m.to_numpy(),d.to_numpy()),'Official monthly/daily overlap disagrees'
    merged=pd.concat([month,daily],ignore_index=True).drop_duplicates();assert not merged.timestamp_ms.duplicated().any()
    merged=merged.sort_values('timestamp_ms').reset_index(drop=True)
    return merged,dict(actual_daily_common_rows_verified=len(common),actual_daily_new_rows_added=len(merged)-len(month))
def complete_grid(f,left_us,right_us):
    t=f.timestamp_ms.to_numpy(np.int64)*1000;expected=np.arange(left_us,right_us,MINUTE,dtype=np.int64)
    missing=np.setdiff1d(expected,t)
    assert np.array_equal(t,expected),f'Actual minute grid incomplete: {len(missing)} absent minutes'
    return t
def aggregate_daily(f,left_us,right_us):
    complete_grid(f,left_us,right_us);days=(right_us-left_us)//DAY;assert days*1440==len(f)
    return dict(available_us=np.arange(left_us+DAY,right_us+DAY,DAY,dtype=np.int64),open=f.open.to_numpy(float)[::1440],high=f.high.to_numpy(float).reshape(days,1440).max(axis=1),low=f.low.to_numpy(float).reshape(days,1440).min(axis=1),close=f.close.to_numpy(float)[1439::1440],volume=f.volume.to_numpy(float).reshape(days,1440).sum(axis=1),quote_volume=f.quote_volume.to_numpy(float).reshape(days,1440).sum(axis=1))
def strict_prior(event_us,mark_open_us,mark_close):
    available=mark_open_us+MINUTE;pos=int(np.searchsorted(available,event_us,side='left')-1)
    if pos<0:return None
    age=int(event_us-available[pos])
    if not 0<age<=MINUTE:return None
    return dict(mark_open_us=int(mark_open_us[pos]),mark_available_us=int(available[pos]),mark_close=float(mark_close[pos]),strict_prior_age_us=age)
