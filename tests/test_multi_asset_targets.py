"""Relevant N-asset covariance, order mapping, eligibility and causal checks."""
import numpy as np
import polars as pl
import pytest
from scripts.investment import public_sma_perpetual as target
from scripts.investment import vol_managed_perpetual_target as hold


def bars(symbols,days=205):
    frames=[]
    for i,symbol in enumerate(symbols):
        close=100*np.exp(np.arange(days)*.0001+(i+1)*.004*np.sin(np.arange(days)/(3+i)))
        opened=np.arange(days,dtype=np.int64)*target.DAY_US
        frames.append(pl.DataFrame(dict(symbol=[symbol]*days,open_us=opened,
            close_us=opened+target.DAY_US,available_us=opened+target.DAY_US,
            open=close,high=close*1.01,low=close*.99,close=close,volume=np.ones(days))))
    return pl.concat(frames)


def test_ordered_N_covariance_and_zero_net_and_causal_pool_eligibility():
    symbols=('SOLUSDT','BTCUSDT','ADAUSDT')
    daily=bars(symbols)
    decisions=np.arange(200,203,dtype=np.int64)*target.DAY_US
    frame,meta=hold.fixed_targets(daily,decisions,symbols=symbols)
    assert frame.height==len(symbols)*len(decisions)
    assert meta['symbols']==list(symbols)
    for t,risk in zip(decisions,meta['risk'],strict=True):
        returns=[]
        for symbol in symbols:
            prices=daily.filter(pl.col('symbol')==symbol).filter(pl.col('close_us')<=t)['close'].to_numpy()[-31:]
            returns.append(np.diff(prices)/prices[:-1])
        wanted,_=target.signed_risk_weights([.2]*3,np.column_stack(returns))
        by_symbol={r['symbol']:r['target_weight'] for r in frame.filter(pl.col('available_us')==t).iter_rows(named=True)}
        assert np.allclose([by_symbol[s] for s in symbols],wanted,rtol=0,atol=1e-14)
        assert risk['covariance_symbol_order']==list(symbols)
    future=daily.with_columns(pl.when(pl.col('close_us')>decisions[0]).then(pl.col('close')*20)
                              .otherwise(pl.col('close')).alias('close'))
    poisoned,_=hold.fixed_targets(future,decisions[:1],symbols=symbols)
    assert poisoned.equals(frame.filter(pl.col('available_us')==decisions[0]))
    rng=np.random.default_rng(123)
    returns=rng.normal(0,.04,size=(30,1))*np.array([1.,-1.,.5])
    w,proof=target.signed_risk_weights([.3,-.3,0],returns)
    assert abs(sum(w))<1e-14 and 0<np.abs(w).sum()<.6
    assert proof['unscaled_signed_covariance_annual_vol']>.1
    one,proof=target.signed_risk_weights([.3],returns[:,:1])
    assert one.shape==(1,) and proof['covariance_assets']==1
    with pytest.raises(ValueError):
        target.signed_risk_weights([.1]*3,returns[:,:2])
    missing=daily.filter(~((pl.col('symbol')==symbols[1]) & (pl.col('close_us')==199*target.DAY_US)))
    result,proof=hold.fixed_targets(missing,decisions[:1],symbols=symbols)
    assert result.filter(pl.col('symbol')==symbols[1])['target_weight'][0]==0
    assert proof['risk'][0]['covariance_symbol_order']==[symbols[0],symbols[2]]
    membership={int(decisions[0]):symbols,int(decisions[1]):symbols[:1]}
    result,proof=hold.fixed_targets(daily,decisions[:2],symbols=symbols,eligible_by_decision=membership)
    exited=result.filter((pl.col('available_us')==decisions[1]) & (pl.col('symbol')!=symbols[0]))
    assert exited['target_weight'].to_list()==[0,0]
    assert exited['eligibility_reason'].to_list()==['POOL_EXIT','POOL_EXIT']
    ten=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','BNBUSDT','ADAUSDT','DOGEUSDT','LINKUSDT','LTCUSDT','DOTUSDT')
    result,proof=hold.fixed_targets(bars(ten),decisions[:1],symbols=ten)
    assert result.height==10 and abs(result['target_weight']).sum()<=.6+1e-15
    assert result['target_weight'].max()<=.3
    assert proof['risk'][0]['covariance_symbol_order']==list(ten)
