"""Fixed completed-day risk measurements; no forecasting labels or fitting."""
import numpy as np

SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT")
DAY_MS=86400000


def measure(frame,previous_close):
    if len(frame)%1440 or not len(frame):
        raise ValueError('ActualcompleteUTCdays required')
    time=frame.timestamp_ms.to_numpy(dtype=np.int64)
    if time[0]%DAY_MS or not np.array_equal(time,np.arange(time[0],time[0]+len(time)*60000,60000,dtype=np.int64)):
        raise ValueError('Missing/conflictingminutes cannot be filled')
    close=frame.close.to_numpy(dtype=float)
    prior=np.nan if previous_close is None else float(previous_close)
    if previous_close is not None and (not np.isfinite(prior) or prior<=0):
        raise ValueError('Truepositivepastboundary required')
    nd=len(frame)//1440
    r1=np.diff(np.log(np.r_[prior,close])).reshape(nd,1440)
    five=close[4::5]
    r5=np.diff(np.log(np.r_[prior,five])).reshape(nd,288)
    result={}
    for suffix,r in (('1m',r1),('5m',r5)):
        square=np.square(r)
        result['RV_'+suffix]=square.sum(1)
        result['RSplus_'+suffix]=np.where(r>=0,square,0).sum(1)
        result['RSminus_'+suffix]=np.where(r<0,square,0).sum(1)
        if previous_close is None:
            result['RSplus_'+suffix][0]=result['RSminus_'+suffix][0]=np.nan
        np.testing.assert_allclose(result['RV_'+suffix],result['RSplus_'+suffix]+result['RSminus_'+suffix],rtol=2e-15,atol=1e-16,equal_nan=True)
    result['open']=frame.open.to_numpy(dtype=float).reshape(nd,1440)[:,0]
    result['close']=close.reshape(nd,1440)[:,-1]
    result['high']=frame.high.to_numpy(dtype=float).reshape(nd,1440).max(1)
    result['low']=frame.low.to_numpy(dtype=float).reshape(nd,1440).min(1)
    previous=np.r_[prior,result['close'][:-1]]
    result['max_log_up']=np.maximum(0,np.log(result['high']/previous))
    result['max_log_down']=np.maximum(0,-np.log(result['low']/previous))
    for name in ('volume','quote_volume','trades'):
        result[name]=frame[name].to_numpy(dtype=float).reshape(nd,1440).sum(1)
    result['zero_quote_minutes']=(frame.quote_volume.to_numpy().reshape(nd,1440)==0).sum(1)
    result['zero_trade_minutes']=(frame.trades.to_numpy().reshape(nd,1440)==0).sum(1)
    result['observed_minutes']=np.full(nd,1440,dtype=np.int64)
    available=(time[::1440]+DAY_MS)*1000
    return result,available,five
