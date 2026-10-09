"""Independent30-day direction/state, equality and causal target checks."""
from pathlib import Path
import sys
import numpy as np
import polars as pl
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1])]
from scripts.investment import momentum_short_pool_target as short
DAY=86400000000


def bars():
    c=np.r_[np.linspace(60.,150.,200),np.linspace(100.,80.,20),[150.,150.,75.,75.]]
    return pl.DataFrame([dict(symbol=s,open_us=i*DAY,close_us=(i+1)*DAY,available_us=(i+1)*DAY,open=float(p),high=float(p+1),low=float(p-1),close=float(p),volume=100.) for s in ('BTCUSDT','ETHUSDT') for i,p in enumerate(c)]),c


def test_exact_existing_horizon_and_state():
    b,c=bars();tt=np.arange(200*DAY,(len(c)+1)*DAY,DAY,dtype=np.int64);f,_=short.fixed_targets(b,tt,symbols=('BTCUSDT','ETHUSDT'))
    held=False;expected=[]
    for i in range(199,len(c)):
        if held:
            if c[i]>=c[i-30]:held=False
        elif c[i]<c[i-30]:held=True
        expected.append(-.3 if held else 0.)
    np.testing.assert_array_equal(f['raw_signed_target'].to_numpy().reshape(-1,2),np.array(expected)[:,None]*np.ones((1,2)))
    assert f['target_weight'].le(0).all()


def test_equality_exits_held_and_blocks_new_entry():
    d=short._MomentumShortDirection();d.candles=np.zeros((200,6));d.candles[-31,2]=100;d.candles[-1,2]=100;d.is_short=True
    closed=[];d.liquidate=lambda:closed.append(True)
    assert not d.should_short();d.update_position();assert closed==[True]
    assert not d.should_long();d.candles[-1,2]=99;assert d.should_short()


def test_future_and_genuine_warmup():
    b,c=bars();tt=np.arange(199*DAY,(len(c)+1)*DAY,DAY,dtype=np.int64);f,_=short.fixed_targets(b,tt,symbols=('BTCUSDT','ETHUSDT'))
    assert f.filter(pl.col('available_us')==tt[0])['eligibility_reason'].eq('WARMUP_OR_DATA_GAP').all()
    cut=210*DAY;changed=b.with_columns([pl.when(pl.col('close_us')>cut).then(pl.col(k)*2).otherwise(pl.col(k)).alias(k) for k in ('open','high','low','close')])
    g,_=short.fixed_targets(changed,tt,symbols=('BTCUSDT','ETHUSDT'))
    assert f.filter(pl.col('available_us')<=cut).equals(g.filter(pl.col('available_us')<=cut))
