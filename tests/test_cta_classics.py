import numpy as np
import polars as pl
from scripts.investment import cta_classics as cta
from scripts.investment import audit_cta_classics as ref
from datetime import datetime, UTC

def fixture():
    start=int(datetime(2024,1,1,tzinfo=UTC).timestamp())*1_000_000
    times=np.arange(start+cta.DAY,start+cta.DAY*501,cta.DAY,dtype=np.int64)
    rows=[]
    for s,m in [('BTCUSDT',1),('ETHUSDT',2)]:
        for i,t in enumerate(times):
            price=(100+i*.1+5*np.sin(i/15))*m
            rows.append(dict(symbol=s,open_us=int(t-cta.DAY),close_us=int(t),available_us=int(t),
                open=price,close=price,high=price+1,low=price-1,volume=10.))
    return pl.DataFrame(rows),times[220:]

def test_frozen_rules_reference_causality_and_warmup():
    b,t=fixture();symbols=('BTCUSDT','ETHUSDT');f,_=cta.signals(b,t,symbols)
    ref.verify_signals(f,b,t,symbols)
    # Exact calendar anchor and missing 12m remain unknown, never shortened.
    assert cta.year_ago(int(datetime(2024,2,29,tzinfo=UTC).timestamp())*1_000_000)==int(datetime(2023,2,28,tzinfo=UTC).timestamp())*1_000_000
    assert f.filter(pl.col('close_us')==int(t[0]))['TSMOM12M'].null_count()==2
    cutoff=int(t[200]);changed=b.with_columns(*[
        pl.when(pl.col('close_us')>cutoff).then(pl.col(k)*3).otherwise(pl.col(k)).alias(k)
        for k in ('open','close','high','low')])
    future,_=cta.signals(changed,t,symbols)
    assert f.filter(pl.col('close_us')<=cutoff).equals(future.filter(pl.col('close_us')<=cutoff))

def test_modes_order_covariance_and_cash_budget():
    b,t=fixture();t=t[180:];symbols=('BTCUSDT','ETHUSDT');f,_=cta.signals(b,t,symbols)
    for family in (*cta.FAMILIES,'HOLD'):
        for mode in cta.MODES:
            target,_=cta.targets(f,b,t,mode,symbols,family)
            ref.verify_targets(target,f,b,symbols,family,mode)
            if mode=='LONG_ONLY':assert target['target_weight'].min()>=0
            if mode=='SHORT_ONLY':assert target['target_weight'].max()<=0
            if mode=='CASH':assert target['target_weight'].abs().sum()==0
            reversed_,_=cta.targets(f,b,t,mode,symbols[::-1],family)
            assert np.allclose(target.sort(['available_us','symbol'])['target_weight'],
                reversed_.sort(['available_us','symbol'])['target_weight'],rtol=0,atol=1e-12)
