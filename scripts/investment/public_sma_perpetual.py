"""Original MIT SMA entry/exit hooks, signed USDT-perpetual research targets.

COIN capped sizing/daily cadence are adaptations, not native Jesse execution.
The original Spot adapter and all of its evidence remain independent.
"""
from __future__ import annotations
import numpy as np
import polars as pl
from quant.paths import ROOT
from scripts.investment import public_sma_daily as public

MODES=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH')
DAY_US=86_400_000_000
def require(ok,message):
    if not ok:raise ValueError(message)

def signed_risk_weights(raw, past_returns, annual_vol_target=.10):
    """Past-only covariance; a zero net exposure never bypasses gross/vol risk."""
    w=np.asarray(raw,dtype=np.float64).copy();r=np.asarray(past_returns,dtype=np.float64)
    require(w.shape==(2,) and np.isfinite(w).all() and r.ndim==2 and r.shape[1]==2
        and r.shape[0]>=30 and np.isfinite(r).all(),'Two assets, complete30 past daily returns')
    require(0<annual_vol_target<=.10,'No increase of existing annual volatility target')
    w=np.clip(w,-.3,.3);gross=float(np.abs(w).sum())
    if gross>.6:w*=.6/gross
    covariance=np.cov(r[-30:],rowvar=False,ddof=1)*365
    variance=float(w@covariance@w)
    require(variance>=-1e-15,'Covariance risk must be nonnegative')
    sigma=float(np.sqrt(max(variance,0.)))
    if sigma>annual_vol_target:w*=annual_vol_target/sigma
    return w,dict(unscaled_signed_covariance_annual_vol=sigma,
        net_target_weight=float(w.sum()),gross_target_weight=float(np.abs(w).sum()),
        covariance_observations=30,past_only=True)

def fixed_targets(bars, decisions, mode):
    """Closed daily trade prices only; strict 200-day causal warmup, fresh flat."""
    require(mode in MODES,'One of four preselected directions')
    supplied=np.asarray(decisions)
    require(supplied.dtype.kind in ('i','u') and supplied.ndim==1
        and np.all(supplied>=0) and np.all(supplied<=np.iinfo(np.int64).max),
        'Integer nonnegative decision microseconds; never truncate floats')
    times=supplied.astype(np.int64)
    require(len(times)>0 and np.all(np.diff(times)==DAY_US) and np.all(times%DAY_US==0),
        'Complete independent scoring-day decisions')
    symbols=('BTCUSDT','ETHUSDT');context=[]
    expected={'symbol','open_us','close_us','available_us','open','high','low','close','volume'}
    require(expected.issubset(bars.columns),'Actual perpetual daily trade-price columns')
    require(set(bars['symbol'].unique().to_list())==set(symbols)
        and all(bars.schema[k]==pl.Int64 for k in ('open_us','close_us','available_us')),
        'Exactly two instruments with integer microsecond clocks')
    for symbol in symbols:
        one=bars.filter(pl.col('symbol')==symbol)
        require(one.height>=200 and one.null_count().select(pl.sum_horizontal(pl.all())).item()==0,
            'Complete actual daily values, no imputation')
        stamps=one['close_us'].to_numpy();available=one['available_us'].to_numpy()
        require(np.all(one['open_us'].to_numpy()+DAY_US==stamps)
            and np.all(np.diff(stamps)==DAY_US) and np.all(stamps%DAY_US==0)
            and np.all(available>=stamps),'Contiguous daily availability and close clock')
        values=one.select('open','close','high','low','volume').to_numpy()
        require(np.isfinite(values).all() and np.all(values[:,:4]>0) and np.all(values[:,4]>=0),
            'Finite positive trade OHLC and actual nonnegative volume')
        candles=np.column_stack((one['open_us'].to_numpy()/1000,values))
        context.append(dict(stamps=stamps,available=available,candles=candles,
            hooks=public._load_public_hooks()(),state=0))
    targets=[];risk=[]
    for decision in times:
        raw=[];returns=[]
        for symbol,c in zip(symbols,context,strict=True):
            index=int(np.searchsorted(c['stamps'],decision,side='right')-1)
            require(index>=199 and c['stamps'][index]==decision
                and np.all(c['available'][index-199:index+1]<=decision),
                'Exactly200 completed available days; no future publication assumption')
            hook=c['hooks'];hook.candles=c['candles'][index-199:index+1]
            hook.is_long=c['state']==1;hook.is_short=c['state']==-1
            closed=[False];hook.liquidate=lambda:closed.__setitem__(0,True)
            if mode=='CASH':
                c['state']=0
            elif c['state']:
                hook.update_position()
                if closed[0]:c['state']=0
            else:
                if mode in ('LONG_ONLY','LONG_SHORT') and hook.should_long():c['state']=1
                elif mode in ('SHORT_ONLY','LONG_SHORT') and hook.should_short():c['state']=-1
            direction=c['state']
            raw.append(.3*direction)
            close=c['candles'][index-30:index+1,2]
            returns.append(np.diff(close)/close[:-1])
        weights,details=signed_risk_weights(raw,np.column_stack(returns))
        for symbol,weight,direction in zip(symbols,weights,raw,strict=True):
            targets.append(dict(available_us=int(decision),symbol=symbol,target_weight=float(weight),
                raw_signed_target=float(direction),mode=mode))
        risk.append(dict(decision_us=int(decision),**details))
    return pl.DataFrame(targets),dict(mode=mode,risk=risk,
        original_long_and_short_and_exit_hooks_reused=True,whole_balance_sizing_replaced_by_capped_COINSizing=True,
        close_then_wait_next_daily_decision_to_reenter=True,equality_holds_current_position=True,
        forbidden_directions_never_create_internal_positions=True,
        source=public.PINNED_HASHES,timeframe_minutes=1440,fast_period=50,slow_period=200,
        native_Jesse_or_Bybit_execution_replicated=False,fresh_flat_each_window=True,
        funding_rates_used_for_signal=False,candidate_status='NO_QUALIFIED_CANDIDATE')
