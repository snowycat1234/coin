from datetime import UTC,datetime
import numpy as np
import polars as pl
import pytest
from scripts.investment.cta_cycle_window import minute_blocks,daily_from_minutes,DAY,MINUTE

def inputs(tmp_path):
    start=int(datetime(2022,1,1,tzinfo=UTC).timestamp())*1000000
    times=np.arange(start,start+2*DAY,MINUTE,dtype=np.int64);records=[];expected={}
    for s,offset in [('BTCUSDT',100.),('ETHUSDT',10.)]:
        opens=offset+np.arange(len(times))*.001
        trade=pl.DataFrame(dict(open_us=times,available_us=times+MINUTE,open=opens,close=opens+.0005,
            high=opens+.001,low=opens-.001,volume=np.ones(len(times)),quote_volume=opens*2))
        mark=pl.DataFrame(dict(timestamp_ms=times//1000,close_time_ms=times//1000+59999,close=opens+.0002))
        for kind,frame in [('klines',trade),('markPriceKlines',mark)]:
            p=tmp_path/(s+kind+'.parquet');frame.write_parquet(p)
            records.append(dict(kind=kind,symbol=s,month='2022-01',normalized_path=str(p)))
        expected[s]=opens
    return start,records,expected

def test_ordered_blocks_and_scalar_closed_daily(tmp_path):
    start,records,expected=inputs(tmp_path)
    blocks=list(minute_blocks(records,('ETHUSDT','BTCUSDT'),start,start+2*DAY,trade_ranges=True))
    assert len(blocks)==2
    for i,block in enumerate(blocks):
        assert list(block['market'])==['ETHUSDT','BTCUSDT']
        for s in expected:
            np.testing.assert_array_equal(block['market'][s]['open'],expected[s][i*1440:(i+1)*1440])
    r=next(v for v in records if v['kind']=='klines' and v['symbol']=='BTCUSDT')
    daily=daily_from_minutes(r)
    assert daily['available_us'].to_list()==[start+DAY,start+2*DAY]
    for i,v in enumerate(daily.iter_rows(named=True)):
        raw=expected['BTCUSDT'][i*1440:(i+1)*1440]
        assert v['open']==raw[0] and v['close']==raw[-1]+.0005
        assert v['high']==max(raw)+.001 and v['low']==min(raw)-.001 and v['volume']==1440

def test_missing_or_future_availability_fails(tmp_path):
    start,records,_=inputs(tmp_path);r=records[0];p=r['normalized_path'];original=pl.read_parquet(p)
    original.slice(1).write_parquet(p)
    with pytest.raises(AssertionError):list(minute_blocks(records,('BTCUSDT','ETHUSDT'),start,start+DAY))
    with pytest.raises(AssertionError):daily_from_minutes(r)
    original.with_columns((pl.col('available_us')+MINUTE).alias('available_us')).write_parquet(p)
    with pytest.raises(AssertionError):list(minute_blocks(records,('BTCUSDT','ETHUSDT'),start,start+DAY))
    with pytest.raises(AssertionError):daily_from_minutes(r)
