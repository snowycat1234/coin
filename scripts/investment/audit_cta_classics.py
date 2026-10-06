"""Independent scalar signal and ordered target reference, never an account."""
import calendar
from datetime import datetime, UTC
import math
import numpy as np
import polars as pl
DAY=86_400_000_000

def verify_signals(frame,bars,decisions,symbols):
    observed={(v['close_us'],v['symbol']):v for v in frame.iter_rows(named=True)};error=0.
    for s in symbols:
        records=list(bars.filter(pl.col('symbol')==s).sort('close_us').iter_rows(named=True))
        lookup={r['close_us']:i for i,r in enumerate(records)};states=[0,0];mom=None;month=None
        for t in decisions:
            j=lookup[int(t)];d=datetime.fromtimestamp(int(t)/1e6,UTC);key=(d.year,d.month)
            anchor=datetime(d.year-1,d.month,min(d.day,calendar.monthrange(d.year-1,d.month)[1]),tzinfo=UTC)
            prior=int(anchor.timestamp())*1_000_000;price=records[j]['close']
            valid=j>=199 and all(r['available_us']<=t for r in records[:j+1])
            if key!=month:
                k=lookup.get(prior);mom=None if k is None or not valid else float(np.sign(price/records[k]['close']-1));month=key
            for i,(n,x) in enumerate(((20,10),(55,20))):
                if not valid:states[i]=0;continue
                hi=max(r['high'] for r in records[j-n:j]);lo=min(r['low'] for r in records[j-n:j])
                exit_hi=max(r['high'] for r in records[j-x:j]);exit_lo=min(r['low'] for r in records[j-x:j])
                old=states[i]
                if old==1 and price<exit_lo or old==-1 and price>exit_hi:states[i]=0
                elif old==0:states[i]=1 if price>hi else (-1 if price<lo else 0)
            values=dict(TSMOM12M=mom,SMA200_SIGNED=float(np.sign(price-sum(r['close'] for r in records[j-199:j+1])/200)) if valid else None,
                DONCHIAN20_10=float(states[0]) if valid else None,
                DC_TSMOM_ENSEMBLE=(sum(states)+mom)/3 if valid and mom is not None else None)
            if 'DC_TWO_SPEED' in frame.columns:
                values.update(DONCHIAN55_20=float(states[1]) if valid else None,
                    DC_TWO_SPEED=sum(states)/2 if valid else None)
            if 'DC_CONFIRMED_SHORT' in frame.columns:
                average=sum(states)/2
                values['DC_CONFIRMED_SHORT']=(None if not valid else
                    -1. if states==[-1,-1] else max(0.,average))
            if 'SMA200_SHORT50' in frame.columns:
                slow=values['SMA200_SIGNED']
                fast_mean=sum(r['close'] for r in records[j-49:j+1])/50 if valid else None
                values['SMA200_SHORT50']=(None if slow is None else
                    1. if slow>0 else -1. if slow<0 and price<fast_mean else 0.)
            for f,v in values.items():
                actual=observed[(int(t),s)][f]
                assert (actual is None)==(v is None),(s,t,f)
                if v is not None:error=max(error,abs(actual-v))
    assert error<1e-12
    return dict(status='PASS_INDEPENDENT_SCALAR_PRIOR_CHANNEL_MONTHLY_12M_SMA200_SIGNALS',rows=frame.height,maximum_error=error)

def verify_targets(frame,signal,bars,symbols,family,mode):
    lookup={(r['close_us'],r['symbol']):r for r in signal.iter_rows(named=True)};error=0.
    for t in sorted(frame['available_us'].unique()):
        actual={r['symbol']:r for r in frame.filter(pl.col('available_us')==t).iter_rows(named=True)}
        assert set(actual)==set(symbols)
        returns=[];directions=[]
        for s in symbols:
            close=bars.filter((pl.col('symbol')==s)&(pl.col('close_us')<=t)&(pl.col('available_us')<=t)).sort('close_us').tail(31)['close'].to_list()
            assert len(close)==31
            returns.append([close[k+1]/close[k]-1 for k in range(30)])
            sign=1. if family=='HOLD' else lookup[(t,s)][family]
            sign=0. if sign is None else sign
            if mode=='CASH' or mode=='LONG_ONLY' and sign<0 or mode=='SHORT_ONLY' and sign>0:sign=0.
            directions.append(sign)
        means=[sum(v)/30 for v in returns]
        sigmas=[math.sqrt(sum((x-m)**2 for x in v)/29) for v,m in zip(returns,means)]
        inv=[1/v for v in sigmas];raw=[min(.3,.6*v/sum(inv))*d for v,d in zip(inv,directions)]
        covariance=np.array([[sum((x-means[i])*(y-means[j]) for x,y in zip(returns[i],returns[j]))/29*365
                              for j in range(len(symbols))] for i in range(len(symbols))])
        w=np.array(raw);sigma=math.sqrt(max(0,float(w@covariance@w)))
        if sigma>.1:w*=.1/sigma
        for i,s in enumerate(symbols):
            error=max(error,abs(actual[s]['target_weight']-w[i]),abs(actual[s]['raw_signed_target']-raw[i]))
        assert sum(abs(float(x)) for x in w)<=.6+1e-12 and max(abs(float(x)) for x in w)<=.3+1e-12
    assert error<1e-10,error
    return dict(status='PASS_INDEPENDENT_ORDERED_INVERSE_VOL_SIGNED_COV_TARGETS',rows=frame.height,maximum_error=error)

def verify_public_sma_targets(frame,bars,decisions,symbols,mode):
    """Scalar reference for the pinned hooks, not a production indicator.

    Each permitted direction has its own fresh-flat state. Opposite mean
    ordering closes an existing state; entry waits for a later decision.
    """
    rows=[]
    for symbol in symbols:
        records=list(bars.filter(pl.col('symbol')==symbol).sort('close_us').iter_rows(named=True))
        lookup={r['close_us']:i for i,r in enumerate(records)};state=0
        for t in decisions:
            j=lookup[int(t)];history=records[j-199:j+1]
            assert len(history)==200 and all(r['available_us']<=t for r in history)
            assert all(history[i+1]['close_us']-history[i]['close_us']==DAY for i in range(199))
            fast=sum(r['close'] for r in history[-50:])/50
            slow=sum(r['close'] for r in history)/200
            if mode=='CASH':state=0
            elif state:
                if state==1 and fast<slow or state==-1 and fast>slow:state=0
            elif mode in ('LONG_ONLY','LONG_SHORT') and fast>slow:state=1
            elif mode in ('SHORT_ONLY','LONG_SHORT') and fast<slow:state=-1
            rows.append(dict(close_us=int(t),symbol=symbol,PUBLIC_SMA50_200=float(state)))
    proof=verify_targets(frame,pl.DataFrame(rows),bars,symbols,'PUBLIC_SMA50_200',mode)
    proof.update(status='PASS_SCALAR_FULL_PUBLIC_SMA50_200_HOOK_STATE_AND_ORDERED_TARGETS',
        equality_holds_state=True,exit_before_later_entry=True,forbidden_directions_do_not_create_state=True)
    return proof
