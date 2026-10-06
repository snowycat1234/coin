"""Ordered target intent combinations; no independent-wallet return blending."""
import numpy as np
import polars as pl
import pytest
from scripts.investment.frozen_expert_mixture import weights,combine,verify,DAY

def fixture():
    first=1_735_689_600_000_000;times=first+np.arange(1,161,dtype=np.int64)*DAY
    symbols=('ETHUSDT','BTCUSDT');decisions=times[40:]
    bars=pl.DataFrame([dict(symbol=s,close_us=int(t),available_us=int(t),close=100+5*np.sin(i/10))
        for s in symbols for i,t in enumerate(times)])
    names=['CASH','HOLD','SMA200_SIGNED']
    frames={}
    for name in names:
        rows=[]
        for t in decisions:
            for s in symbols:
                w=0. if name=='CASH' else .12 if name=='HOLD' else (-.2 if s=='ETHUSDT' else .2)
                rows.append(dict(available_us=int(t),symbol=s,target_weight=w,raw_signed_target=w,mode='LONG_SHORT',eligibility_reason='ELIGIBLE'))
        # Different source row orders must preserve explicit account identity.
        frames[name]=pl.DataFrame(rows[::-1])
    return names,frames,decisions,symbols,bars

def test_static_soft_targets_order_caps_independent_covariance_and_future_prefix():
    names,frames,times,symbols,bars=fixture();w=weights(names,len(times),'STATIC_DIRECTION3')
    result=combine(frames,names,times,symbols,w);proof=verify(result,frames,names,times,symbols,w,bars)
    assert proof['maximum_error']<1e-10 and result.head(2)['symbol'].to_list()==list(symbols)
    assert abs(result.head(2)['target_weight'][0]+.07)<1e-15
    assert abs(result.head(2)['target_weight'][1]-.13)<1e-15
    assert np.array_equal(w[:,names.index('CASH')],np.full(len(times),.25))
    cut=int(times[59]);changed={n:f.with_columns(pl.when(pl.col('available_us')>cut).then(pl.col('target_weight')*.5).otherwise(pl.col('target_weight')).alias('target_weight')) for n,f in frames.items()}
    later=combine(changed,names,times,symbols,w)
    assert result.filter(pl.col('available_us')<=cut).equals(later.filter(pl.col('available_us')<=cut))
    bad=result.with_columns((pl.col('target_weight')*.9).alias('target_weight'))
    with pytest.raises(AssertionError):verify(bad,frames,names,times,symbols,w,bars)

def test_oracle_selection_at_boundary_and_static_not_influenced_by_future_winner():
    names,frames,times,symbols,bars=fixture()
    segments=[dict(begin_day=0,end_day=60,expert='HOLD'),dict(begin_day=60,end_day=120,expert='SMA200_SIGNED')]
    w=weights(names,len(times),'ORACLE60D',segments);result=combine(frames,names,times,symbols,w)
    verify(result,frames,names,times,symbols,w,bars)
    assert result.filter(pl.col('available_us')==int(times[59]))['target_weight'].to_list()==[.12,.12]
    assert result.filter(pl.col('available_us')==int(times[60]))['target_weight'].to_list()==[-.2,.2]
    other=[dict(begin_day=0,end_day=60,expert='CASH'),dict(begin_day=60,end_day=120,expert='HOLD')]
    assert np.array_equal(weights(names,len(times),'EQUAL_EXPERTS',segments),weights(names,len(times),'EQUAL_EXPERTS',other))
    broken=[dict(begin_day=0,end_day=59,expert='HOLD'),dict(begin_day=60,end_day=120,expert='SMA200_SIGNED')]
    with pytest.raises(AssertionError):weights(names,len(times),'ORACLE60D',broken)

def test_missing_identity_duplicate_and_negative_meta_weight_are_rejected():
    names,frames,times,symbols,bars=fixture();w=weights(names,len(times),'EQUAL_EXPERTS')
    missing=dict(frames,HOLD=frames['HOLD'].head(frames['HOLD'].height-1))
    with pytest.raises(AssertionError):combine(missing,names,times,symbols,w)
    duplicate=dict(frames,HOLD=pl.concat([frames['HOLD'],frames['HOLD'].head(1)]))
    with pytest.raises(AssertionError):combine(duplicate,names,times,symbols,w)
    negative=w.copy();negative[0]=[-.1,.6,.5]
    with pytest.raises(AssertionError):combine(frames,names,times,symbols,negative)
