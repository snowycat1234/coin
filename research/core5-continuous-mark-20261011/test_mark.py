"""Domain, source-overlap, missing-grid and boundary counterexamples."""
import json
import numpy as np
import pandas as pd
import pytest
from mark_source import HERE,SYMBOLS,identity,union,grid_gaps,measure
from publish_mark import walk
import cold_mark


def row(family='markPriceKlines',symbol='BTCUSDT',period='2022-01'):
    return dict(family=family,symbol=symbol,month=period[:7],source_period=period,
        frequency='daily' if len(period)==10 else 'monthly',
        official_URL=f'https://data.binance.vision/data/futures/um/{"daily" if len(period)==10 else "monthly"}/{family}/{symbol}/1m/{symbol}-1m-{period}.zip')


def frame(n=1440):
    t=1640995200000+np.arange(n,dtype=np.int64)*60000
    return pd.DataFrame(dict(timestamp_ms=t,open=np.full(n,100.),high=np.full(n,110.),low=np.full(n,90.),
        close=np.full(n,101.),volume=np.zeros(n),close_time_ms=t+59999,quote_volume=np.zeros(n),trades=np.zeros(n),
        taker_buy_volume=np.zeros(n),taker_buy_quote_volume=np.zeros(n),ignore=np.zeros(n)))


def test_trade_and_wrong_source_domain_refused():
    identity(row())
    with pytest.raises(ValueError,match='Independent'):identity(row('klines'))
    wrong=row();wrong['official_URL']=wrong['official_URL'].replace('/um/','/cm/')
    with pytest.raises(ValueError,match='domain'):identity(wrong)
    wrong=row();wrong['symbol']='ETHUSDT'
    with pytest.raises(ValueError,match='identity'):identity(wrong)
    with pytest.raises(ValueError,match='union'):
        identity(dict(kind='DAILY_UNION',family='markPriceKlines',symbol='BTCUSDT',month='2022-01',daily_sources=[row(symbol='ETHUSDT',period='2022-01-01')]))


def test_missing_minutes_never_imputed_and_exact_source_union():
    d=frame();month=d.drop(index=[9,17]).reset_index(drop=True)
    missing,days=grid_gaps(month,1640995200000,1641081600000)
    assert missing.tolist()==[1640995740000,1640996220000] and days==['2022-01-01']
    actual,e=union(month,d,1640995200000,1641081600000)
    np.testing.assert_array_equal(actual.to_numpy(),d.to_numpy())
    assert e['common_rows']==1438 and e['added_actual_rows']==2
    bad=d.copy();bad.loc[20,'high']=120
    with pytest.raises(ValueError,match='Conflicting'):union(month,bad,1640995200000,1641081600000)


def test_actual_mark_previous_boundary_and_missing_first_preserved():
    d=frame();v,t,c=measure(d,None)
    assert np.isnan(v['RV_1m'][0]) and np.isnan(v['max_log_up'][0])
    known,_,_=measure(d,105.)
    assert known['max_log_up'][0]==np.log(110/105)
    assert known['max_log_down'][0]==-np.log(90/105)
    assert t.tolist()==[1641081600000000] and len(c)==288
    with pytest.raises(ValueError,match='Actualcomplete'):measure(d.drop(index=9),105.)
    with pytest.raises(ValueError,match='Truepositive'):measure(d,0)


def test_new_daily_dependencies_not_lost_by_source_packing():
    daily=dict(kind='NEW_OFFICIAL_RAW',ZIP_SHA256='daily')
    monthly=dict(kind='NEW_OFFICIAL_RAW',ZIP_SHA256='month',new_daily_repairs=[daily])
    assert [r['ZIP_SHA256'] for r in walk(dict(sources=[monthly],end_boundary=monthly))]==['month','daily','month','daily']


def test_frozen_no_native_funding_certification_or_locked_access():
    p=json.loads((HERE/'PROTOCOL.json').read_text())
    assert p['order']==list(SYMBOLS) and len(p['phases'])==6
    assert 'charge-mark' in p['unchanged'] and 'HTTP_RETRIES0' in p['source_transport']
