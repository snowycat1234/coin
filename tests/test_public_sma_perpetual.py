"""New dual-direction public hook and signed covariance causality boundaries."""
import numpy as np
import polars as pl
import pytest
from scripts.investment import public_sma_perpetual as strategy
from scripts.investment.audit_cta_classics import verify_public_sma_targets

def test_public_signed_signal_covariance_and_future_prefix():
    day=strategy.DAY_US;first=1_735_689_600_000_000
    closes=first+np.arange(1,241,dtype=np.int64)*day
    price=np.r_[np.full(200,100.),np.linspace(99.,60.,40)]
    rows=[]
    for symbol in ('BTCUSDT','ETHUSDT'):
        for i,close in enumerate(closes):
            rows.append(dict(symbol=symbol,open_us=int(close-day),close_us=int(close),available_us=int(close),
                open=float(price[i]),high=float(price[i]+1),low=float(price[i]-1),close=float(price[i]),volume=1000.))
    bars=pl.DataFrame(rows);decisions=closes[199:205]
    outputs={m:strategy.fixed_targets(bars,decisions,m)[0] for m in strategy.MODES}
    assert outputs['CASH']['target_weight'].abs().sum()==0
    assert outputs['LONG_ONLY']['target_weight'].abs().sum()==0
    assert outputs['SHORT_ONLY'].filter(pl.col('target_weight')<0).height>0
    assert outputs['LONG_SHORT'].equals(outputs['SHORT_ONLY'].with_columns(pl.lit('LONG_SHORT').alias('mode')))
    # Finite future prices are perturbed after the prefix being compared.
    cut=int(decisions[2]);changed=bars.with_columns(*[
        pl.when(pl.col('close_us')>cut).then(pl.col(k)*7).otherwise(pl.col(k)).alias(k)
        for k in ('open','high','low','close')])
    before=outputs['LONG_SHORT'].filter(pl.col('available_us')<=cut)
    after=strategy.fixed_targets(changed,decisions,'LONG_SHORT')[0].filter(pl.col('available_us')<=cut)
    assert before.equals(after)
    # Offset weights still carry risk when the assets are anticorrelated.
    changes=np.linspace(-.05,.05,30);w,proof=strategy.signed_risk_weights([1.,-1.],np.column_stack((changes,-changes)))
    assert abs(w.sum())<1e-15 and np.abs(w).sum()<.6
    assert proof['unscaled_signed_covariance_annual_vol']>.10
    assert proof['gross_target_weight']>0 and proof['past_only']
    # A prohibited short must not delay a subsequently allowed long entry.
    rebound=bars.with_columns(*[
        pl.when(pl.col('close_us')==int(closes[201])).then(pl.lit(10000.+offset))
        .otherwise(pl.col(k)).alias(k)
        for k,offset in (('open',0),('close',0),('high',1),('low',-1))])
    long=strategy.fixed_targets(rebound,closes[199:202],'LONG_ONLY')[0]
    assert long.filter(pl.col('available_us')==int(closes[200]))['target_weight'].abs().sum()==0
    assert long.filter(pl.col('available_us')==int(closes[201]))['target_weight'].min()>0
    with pytest.raises(ValueError):
        strategy.fixed_targets(bars,decisions.astype(float)+.5,'LONG_SHORT')

def test_public_full_hooks_inverse_vol_order_exit_and_causality():
    day=strategy.DAY_US;first=1_735_689_600_000_000
    closes=first+np.arange(1,701,dtype=np.int64)*day
    price=np.r_[np.linspace(70.,150.,240),np.linspace(149.,60.,230),np.linspace(61.,170.,230)]
    rows=[];symbols=('ETHUSDT','BTCUSDT')
    for symbol,scale in zip(symbols,(.6,1.)):
        for t,p in zip(closes,price*scale):
            rows.append(dict(symbol=symbol,open_us=int(t-day),close_us=int(t),available_us=int(t),
                open=float(p),high=float(p+1),low=float(p-1),close=float(p),volume=1000.))
    bars=pl.DataFrame(rows);decisions=closes[199:]
    outputs={}
    for mode in strategy.MODES:
        targets,meta=strategy.fixed_targets(bars,decisions,mode,symbols=symbols,allocation='INVERSE_VOL_30D')
        proof=verify_public_sma_targets(targets,bars,decisions,symbols,mode)
        assert proof['maximum_error']<1e-10 and meta['original_long_and_short_and_exit_hooks_reused']
        assert targets.head(2)['symbol'].to_list()==list(symbols)
        outputs[mode]=targets
    one=outputs['LONG_SHORT'].filter(pl.col('symbol')=='BTCUSDT')
    values=one['raw_signed_target'].to_list()
    assert any(v<0 for v in values) and any(v>0 for v in values)
    # A change of direction closes first; it cannot instantaneously reverse.
    changes=[i for i in range(1,len(values)) if values[i]==0 and values[i-1]!=0]
    assert len(changes)==2
    assert all(values[i-1]*values[i+1]<0 for i in changes)
    assert outputs['LONG_ONLY']['raw_signed_target'].min()>=0
    assert outputs['SHORT_ONLY']['raw_signed_target'].max()<=0
    cut=int(decisions[250]);changed=bars.with_columns(*[
        pl.when(pl.col('close_us')>cut).then(pl.col(k)*3).otherwise(pl.col(k)).alias(k)
        for k in ('open','high','low','close')])
    later,_=strategy.fixed_targets(changed,decisions,'LONG_SHORT',symbols=symbols,allocation='INVERSE_VOL_30D')
    assert later.filter(pl.col('available_us')<=cut).equals(outputs['LONG_SHORT'].filter(pl.col('available_us')<=cut))
    wrong=outputs['LONG_SHORT'].with_columns((pl.col('target_weight')*.9).alias('target_weight'))
    with pytest.raises(AssertionError):verify_public_sma_targets(wrong,bars,decisions,symbols,'LONG_SHORT')
