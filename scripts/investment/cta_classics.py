"""Frozen literature rules; public indicator reuse and owned portfolio sizing.

These are daily close adapters, not whole Turtle or original MOP replication.
No fitting, forecast scalar search, future regimes, or independent wallets.
"""
import ast
import calendar
import hashlib
from collections import namedtuple
from datetime import datetime, UTC
import numpy as np
import polars as pl
from quant.paths import ROOT
from scripts.investment.public_sma_perpetual import signed_risk_weights, symbol_order
from scripts.investment.donchian_daily_pool_target import VENDOR, PINNED_HASHES

DAY = 86_400_000_000
FAMILIES = ('TSMOM12M', 'SMA200_SIGNED', 'DONCHIAN20_10', 'DC_TSMOM_ENSEMBLE')
MODES = ('LONG_ONLY', 'SHORT_ONLY', 'LONG_SHORT', 'CASH')

def channel_kernel():
    # Same unchanged MIT nonsequential function already used in this project.
    # Selecting external source nodes avoids importing the full Jesse engine.
    for name, digest in PINNED_HASHES.items():
        assert hashlib.sha256((VENDOR/name).read_bytes()).hexdigest() == digest
    nodes = [n for n in ast.parse((VENDOR/'donchian_indicator_original.py').read_bytes()).body
             if isinstance(n, ast.FunctionDef) and n.name == 'donchian']
    assert len(nodes) == 1
    ns = dict(np=np, slice_candles=lambda c, sequential:c,
              DonchianChannel=namedtuple('DonchianChannel','upperband middleband lowerband'))
    exec(compile(ast.Module(nodes,type_ignores=[]),str(VENDOR/'donchian_indicator_original.py'),'exec'),ns)
    return ns['donchian']

def year_ago(t):
    d=datetime.fromtimestamp(int(t)/1e6,UTC)
    return int(d.replace(year=d.year-1,day=min(d.day,calendar.monthrange(d.year-1,d.month)[1])).timestamp())*1_000_000

def signals(bars, decisions, symbols):
    """Virtual deterministic signal states are independent of account fills.

    Channel entries/exit use prior bars only. Signal exits are cash for that
    close; a new entry can occur on the following close. TSMOM is recomputed
    at each UTC calendar month boundary and held throughout that month.
    """
    symbols=symbol_order(symbols);times=np.asarray(decisions,dtype=np.int64)
    assert len(times)>0 and np.all(np.diff(times)==DAY) and np.all(times%DAY==0)
    kernel=channel_kernel();rows=[];availability=[]
    for symbol in symbols:
        b=bars.filter(pl.col('symbol')==symbol).sort('close_us')
        stamps=b['close_us'].to_numpy();available=b['available_us'].to_numpy()
        c=b.select('open','close','high','low','volume').to_numpy()
        assert np.all(np.diff(stamps)==DAY) and np.all(available>=stamps)
        assert np.isfinite(c).all() and np.all(c[:,:4]>0)
        candles=np.column_stack((b['open_us'].to_numpy()/1000,c))
        states={(20,10):0,(55,20):0};mom=None;month=None
        for t in times:
            j=int(np.searchsorted(stamps,t,side='right')-1)
            valid=j>=199 and stamps[j]==t and np.all(available[:j+1]<=t)
            now=datetime.fromtimestamp(int(t)/1e6,UTC);key=(now.year,now.month)
            prior=year_ago(t);k=int(np.searchsorted(stamps,prior,side='left'))
            valid_mom=k<len(stamps) and stamps[k]==prior and k<=j and available[k]<=t
            if key!=month:
                mom=float(np.sign(c[j,1]/c[k,1]-1)) if valid and valid_mom else None
                month=key
            dc={}
            if not valid:
                states=dict.fromkeys(states,0)
            for pair,state in states.items():
                n,x=pair
                if valid:
                    entry=kernel(candles[:j],period=n)
                    exit_=kernel(candles[:j],period=x)
                    close=c[j,1]
                    if state==1 and close<exit_.lowerband or state==-1 and close>exit_.upperband:state=0
                    elif state==0:
                        state=1 if close>entry.upperband else (-1 if close<entry.lowerband else 0)
                states[pair]=state;dc[pair]=float(state)
            sma=float(np.sign(c[j,1]-np.mean(c[j-199:j+1,1]))) if valid else None
            values=dict(TSMOM12M=mom,SMA200_SIGNED=sma,DONCHIAN20_10=dc[(20,10)] if valid else None,
                DC_TSMOM_ENSEMBLE=(dc[(20,10)]+dc[(55,20)]+mom)/3 if valid and mom is not None else None)
            availability.append(dict(symbol=symbol,decision_us=int(t),warmup_valid=valid,
                twelve_month_anchor_us=int(prior),twelve_month_valid=valid_mom,month_boundary=key))
            rows.append(dict(close_us=int(t),available_us=int(t),symbol=symbol,**values))
    return pl.DataFrame(rows,infer_schema_length=None).sort(['close_us','symbol']),availability

def targets(signal, bars, decisions, mode, symbols, family):
    assert mode in MODES and family in (*FAMILIES,'HOLD')
    symbols=symbol_order(symbols);out=[];risks=[]
    lookup={(r['close_us'],r['symbol']):r for r in signal.iter_rows(named=True)}
    histories={s:bars.filter(pl.col('symbol')==s).sort('close_us') for s in symbols}
    for t in decisions:
        past=[];direction=[];invalid=[]
        for s in symbols:
            v=1. if family=='HOLD' else lookup[(int(t),s)][family]
            if v is None:invalid.append(s);v=0.
            if mode=='CASH' or mode=='LONG_ONLY' and v<0 or mode=='SHORT_ONLY' and v>0:v=0.
            direction.append(v)
            b=histories[s].filter((pl.col('close_us')<=t)&(pl.col('available_us')<=t)).tail(31)
            if b.height!=31 or not np.all(np.diff(b['close_us'].to_numpy())==DAY):
                raise ValueError('Missing ordered past30 daily returns; no zero imputation')
            c=b['close'].to_numpy();past.append(c[1:]/c[:-1]-1)
        matrix=np.column_stack(past);sigma=matrix.std(axis=0,ddof=1)
        if np.any(~np.isfinite(sigma)) or np.any(sigma<=0):
            raise ValueError('Unknown member volatility; no redistribution')
        allocation=.6*(sigma.min()/sigma)/np.sum(sigma.min()/sigma)
        raw=np.minimum(.3,allocation)*np.asarray(direction)
        w,risk=signed_risk_weights(raw,matrix)
        risks.append(dict(available_us=int(t),symbol_order=list(symbols),
            covariance_symbol_order=list(symbols),unknown_signal_symbols=invalid,**risk))
        for i,s in enumerate(symbols):out.append(dict(available_us=int(t),symbol=s,
            target_weight=float(w[i]),raw_signed_target=float(raw[i]),mode=mode,
            eligibility_reason='UNKNOWN_WARMUP_FLAT' if s in invalid else 'ELIGIBLE'))
    return pl.DataFrame(out),dict(strategy_id='FROZEN_CLASSIC_CTA_'+family,mode=mode,symbols=list(symbols),risk=risks,
        volatility='PAST30_SAMPLE_INVERSE_VOL_PLUS_SIGNED_COV_SCALE_DOWN_10PCT',
        no_cash_budget_redistribution=True,signal_state='VIRTUAL_INTENT_NOT_ACCOUNT_INVENTORY',models_fit=0)
