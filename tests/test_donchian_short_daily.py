"""Independent prior-window/state and causal risk checks; no wallets."""
from pathlib import Path
import sys
import numpy as np
import polars as pl

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'), str(Path(__file__).resolve().parents[1])]
from scripts.investment import donchian_short_daily_pool_target as variant

DAY=86_400_000_000


def bars():
    # A smooth downward close path exercises shorts even above its lagged
    # long-term mean; later isolated rising shocks test strict exits.
    close=np.r_[np.linspace(60.,150.,200), np.linspace(140.,90.,20), [90.,170.,169.,80.,79.]]
    high=close+1;low=close-1
    rows=[dict(symbol=s,open_us=i*DAY,close_us=(i+1)*DAY,available_us=(i+1)*DAY,
        open=float(c),high=float(h),low=float(l),close=float(c),volume=100.)
        for s in ('BTCUSDT','ETHUSDT') for i,(c,h,l) in enumerate(zip(close,high,low,strict=True))]
    return pl.DataFrame(rows),close,high,low


def test_prior_windows_state_and_equal_allocation():
    b,c,h,l=bars();decisions=np.arange(200*DAY,len(c)*DAY+1,DAY,dtype=np.int64)
    frame,meta=variant.fixed_targets(b,decisions,symbols=('BTCUSDT','ETHUSDT'))
    held=False;expected=[]
    for j in range(199,len(c)):
        if held:
            if c[j]>h[j-10:j].max():held=False
        elif c[j]<l[j-20:j].min():held=True
        expected.append(-.3 if held else 0.)
    raw=frame['raw_signed_target'].to_numpy().reshape(-1,2)
    np.testing.assert_array_equal(raw,np.array(expected)[:,None]*np.ones((1,2)))
    assert meta['rules']['trend_filter'] is False
    assert all(x<=0 for x in frame['target_weight'])
    # First short breakout occurs while close remains above its200-bar SMA.
    first=np.flatnonzero(np.array(expected)<0)[0]+199
    assert c[first]>c[first-199:first+1].mean()


def test_strict_equality_exclusion_and_exit_before_entry():
    factory=variant.direction_factory();hook=factory();c=np.zeros((200,6));c[:,2]=100;c[:,3]=110;c[:,4]=90
    c[-1,3]=1000;c[-1,4]=1;hook.candles=c
    hook.price=90.;assert not hook.should_short()
    hook.price=89.;assert hook.should_short()
    out=[];hook.liquidate=lambda:out.append(True)
    hook.price=110.;hook.update_position();assert not out
    hook.price=111.;hook.update_position();assert out==[True]
    # Shared adapter's held branch exits without evaluating new entry.
    b,c,h,l=bars();a,_=variant.fixed_targets(b,np.arange(200*DAY,len(c)*DAY+1,DAY,dtype=np.int64),symbols=('BTCUSDT','ETHUSDT'))
    row=a.filter(pl.col('available_us')==222*DAY)
    assert row['raw_signed_target'].eq(0).all()


def test_future_perturbation_and_real200_warmup():
    b,c,_,_=bars();tt=np.arange(199*DAY,len(c)*DAY+1,DAY,dtype=np.int64)
    a,_=variant.fixed_targets(b,tt,symbols=('BTCUSDT','ETHUSDT'))
    assert a.filter(pl.col('available_us')==tt[0])['eligibility_reason'].eq('WARMUP_OR_DATA_GAP').all()
    cut=212*DAY
    changed=b.with_columns([pl.when(pl.col('close_us')>cut).then(pl.col(k)*2).otherwise(pl.col(k)).alias(k) for k in ('open','high','low','close')])
    z,_=variant.fixed_targets(changed,tt,symbols=('BTCUSDT','ETHUSDT'))
    assert a.filter(pl.col('available_us')<=cut).equals(z.filter(pl.col('available_us')<=cut))
