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

def test_two_speed_reuses_channels_preserves_default_and_is_causal():
    b,t=fixture();symbols=('BTCUSDT','ETHUSDT')
    b=b.with_columns((pl.col('close')+.01).alias('high'),(pl.col('close')-.01).alias('low'))
    old,_=cta.signals(b,t,symbols);extended,_=cta.signals(b,t,symbols,include_components=True)
    assert extended.select(old.columns).equals(old)
    ref.verify_signals(extended,b,t,symbols)
    assert extended['DC_TWO_SPEED'].equals((extended['DONCHIAN20_10']+extended['DONCHIAN55_20'])/2)
    assert set(extended['DC_TWO_SPEED'].drop_nulls().to_list())<= {-1.,-.5,0.,.5,1.}
    assert any(abs(x)==.5 for x in extended['DC_TWO_SPEED'].drop_nulls().to_list())
    cutoff=int(t[150]);changed=b.with_columns(*[
        pl.when(pl.col('close_us')>cutoff).then(pl.col(k)*3).otherwise(pl.col(k)).alias(k)
        for k in ('open','close','high','low')])
    future,_=cta.signals(changed,t,symbols,include_components=True)
    assert extended.filter(pl.col('close_us')<=cutoff).equals(future.filter(pl.col('close_us')<=cutoff))
    for mode in cta.MODES:
        target,_=cta.targets(extended,b,t,mode,symbols,'DC_TWO_SPEED')
        ref.verify_targets(target,extended,b,symbols,'DC_TWO_SPEED',mode)
        reversed_,_=cta.targets(extended,b,t,mode,symbols[::-1],'DC_TWO_SPEED')
        assert np.allclose(target.sort(['available_us','symbol'])['target_weight'],
            reversed_.sort(['available_us','symbol'])['target_weight'],rtol=0,atol=1e-12)


def test_confirmed_short_keeps_downtrends_vetoes_divergence_and_preserves_long():
    b,t=fixture();symbols=('BTCUSDT','ETHUSDT')
    # Rise, sustained decline, then rebound: actual entry and exit states.
    days=(pl.col('close_us')-b['close_us'].min())/cta.DAY
    price=pl.when(days<200).then(100+days*.3).when(days<350).then(160-(days-200)*.5).otherwise(85+(days-350)*.7)
    b=b.with_columns(price.alias('close'),price.alias('open'),(price+.01).alias('high'),(price-.01).alias('low'))
    old,_=cta.signals(b,t,symbols);f,_=cta.signals(b,t,symbols,include_components=True)
    assert f.select(old.columns).equals(old)
    ref.verify_signals(f,b,t,symbols)
    both=f.filter((pl.col('DONCHIAN20_10')<0)&(pl.col('DONCHIAN55_20')<0))
    disagreement=f.filter((pl.col('DC_TWO_SPEED')<0)&~((pl.col('DONCHIAN20_10')<0)&(pl.col('DONCHIAN55_20')<0)))
    assert both.height>0 and both['DC_CONFIRMED_SHORT'].max()==-1
    assert disagreement.height>0 and disagreement['DC_CONFIRMED_SHORT'].abs().sum()==0
    pos=f.filter(pl.col('DC_TWO_SPEED')>=0)
    assert pos['DC_CONFIRMED_SHORT'].equals(pos['DC_TWO_SPEED'])
    cutoff=int(t[100]);changed=b.with_columns(*[
        pl.when(pl.col('close_us')>cutoff).then(pl.col(k)*2).otherwise(pl.col(k)).alias(k)
        for k in ('open','close','high','low')])
    future,_=cta.signals(changed,t,symbols,include_components=True)
    assert f.filter(pl.col('close_us')<=cutoff).equals(future.filter(pl.col('close_us')<=cutoff))
    for mode in cta.MODES:
        target,_=cta.targets(f,b,t,mode,symbols,'DC_CONFIRMED_SHORT')
        ref.verify_targets(target,f,b,symbols,'DC_CONFIRMED_SHORT',mode)
        swapped,_=cta.targets(f,b,t,mode,symbols[::-1],'DC_CONFIRMED_SHORT')
        assert np.allclose(target.sort(['available_us','symbol'])['target_weight'],
                           swapped.sort(['available_us','symbol'])['target_weight'],rtol=0,atol=1e-12)


def test_short50_rebound_exit_long_identity_and_future_causality():
    b,t=fixture();symbols=('BTCUSDT','ETHUSDT')
    days=(pl.col('close_us')-b['close_us'].min())/cta.DAY
    price=pl.when(days<200).then(100+days*.3).when(days<350).then(160-(days-200)*.5).otherwise(85+(days-350)*.7)
    b=b.with_columns(price.alias('close'),price.alias('open'),(price+.01).alias('high'),(price-.01).alias('low'))
    f,_=cta.signals(b,t,symbols,include_components=True)
    ref.verify_signals(f,b,t,symbols)
    assert f.filter(pl.col('SMA200_SHORT50')<0).height>0
    rebound=f.filter((pl.col('SMA200_SIGNED')<0)&(pl.col('SMA200_SHORT50')==0))
    assert rebound.height>0
    positive=f.filter(pl.col('SMA200_SIGNED')>=0)
    assert positive['SMA200_SHORT50'].equals(positive['SMA200_SIGNED'])
    cutoff=int(t[160]);future=b.with_columns(*[
        pl.when(pl.col('close_us')>cutoff).then(pl.col(k)*4).otherwise(pl.col(k)).alias(k)
        for k in ('open','close','high','low')])
    changed,_=cta.signals(future,t,symbols,include_components=True)
    assert f.filter(pl.col('close_us')<=cutoff).equals(changed.filter(pl.col('close_us')<=cutoff))
    old,_=cta.targets(f,b,t,'LONG_ONLY',symbols,'SMA200_SIGNED')
    new,_=cta.targets(f,b,t,'LONG_ONLY',symbols,'SMA200_SHORT50')
    assert old.equals(new)
    for mode in cta.MODES:
        target,_=cta.targets(f,b,t,mode,symbols,'SMA200_SHORT50')
        ref.verify_targets(target,f,b,symbols,'SMA200_SHORT50',mode)
        swapped,_=cta.targets(f,b,t,mode,symbols[::-1],'SMA200_SHORT50')
        assert np.allclose(target.sort(['available_us','symbol'])['target_weight'],
                           swapped.sort(['available_us','symbol'])['target_weight'],rtol=0,atol=1e-12)
