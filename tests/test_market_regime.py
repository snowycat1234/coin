import numpy as np
import polars as pl
import pytest
from scripts.investment import market_regime as reg
from scripts.investment import shared_direction_model as direction
from test_shared_direction_model import bars, SYMS

def test_training_model_unaffected_by_future_features():
    features=[]
    for i in range(220):
        features.append(dict(symbol='BTCUSDT',close_us=i*direction.DAY,
            return_20d=.1*np.sin(i/17),ma200_distance=.2*np.sin(i/29),
            vol_30d=.02+.01*np.cos(i/11),market_breadth=.5+.3*np.sin(i/23),
            return_1d=.01*np.sin(i/7)))
    frame=pl.DataFrame(features)
    a,pa,sa,ga=reg.fit_predict(frame,0,181*direction.DAY,181*direction.DAY,220*direction.DAY)
    changed=frame.with_columns(*[pl.when(pl.col('close_us')>=200*direction.DAY).then(pl.col(c)*10)
        .otherwise(pl.col(c)).alias(c) for c in reg.FEATURES])
    b,pb,sb,gb=reg.fit_predict(changed,0,181*direction.DAY,181*direction.DAY,220*direction.DAY)
    assert np.array_equal(sa.mean_,sb.mean_) and np.array_equal(ga.means_,gb.means_)
    assert a.filter(pl.col('available_us')<200*direction.DAY).equals(b.filter(pl.col('available_us')<200*direction.DAY))
    assert pa==pb and pa['training_max_close_us']<181*direction.DAY

def test_gate_cash_is_not_opposite_and_risk_recomputed():
    b=bars();t=260*direction.DAY
    p=pl.DataFrame(dict(symbol=list(SYMS),close_us=[t,t],prediction=[2,0]))
    for state,expected in [('BULL',[.3,0.]),('BEAR',[0.,-.3]),('SIDEWAYS',[0.,0.]),('HIGH_VOL_CRASH',[0.,0.])]:
        result,_=direction.targets(p,b,np.asarray([t]),'LONG_SHORT',SYMS,regimes={t:state})
        assert result['raw_signed_target'].to_list()==expected
        assert result['target_weight'].abs().sum()<=.6
        assert all(v==0 for v,raw in zip(result['target_weight'],expected) if raw==0)
    with pytest.raises(ValueError,match='Unknown regime'):
        direction.targets(p,b,np.asarray([t]),'LONG_SHORT',SYMS,regimes={t:'UNKNOWN'})

def test_missing_regime_fails_instead_of_free_direction():
    t=260*direction.DAY;p=pl.DataFrame(dict(symbol=list(SYMS),close_us=[t,t],prediction=[2,0]))
    with pytest.raises(KeyError):
        direction.targets(p,bars(),np.asarray([t]),'LONG_SHORT',SYMS,regimes={})

def test_past_trend_boundaries_crash_and_unknown():
    row=dict(return_1d=0.,vol_30d=.02,ma200_distance=.1,return_20d=.1)
    assert reg.past_state(row)=='BULL'
    assert reg.past_state(dict(row,ma200_distance=-.1,return_20d=-.1))=='BEAR'
    assert reg.past_state(dict(row,return_20d=0.))=='SIDEWAYS'
    assert reg.past_state(dict(row,ma200_distance=-.1))=='SIDEWAYS'
    assert reg.past_state(dict(row,return_1d=-.051,vol_30d=.05))=='HIGH_VOL_CRASH'
    with pytest.raises(ValueError,match='Finite'):
        reg.past_state(dict(row,return_20d=float('nan')))

def test_past_trend_rule_rejects_future_availability_and_preserves_prefix():
    rows=[dict(symbol='BTCUSDT',close_us=i*direction.DAY,available_us=i*direction.DAY,
        return_1d=.01,vol_30d=.02,ma200_distance=.1,return_20d=.1) for i in range(4)]
    frame=pl.DataFrame(rows)
    before=reg.rule_states(frame,0,4*direction.DAY)
    changed=frame.with_columns(pl.when(pl.col('close_us')>=2*direction.DAY).then(-.1)
        .otherwise(pl.col('return_20d')).alias('return_20d'))
    after=reg.rule_states(changed,0,4*direction.DAY)
    assert before.head(2).equals(after.head(2))
    with pytest.raises(ValueError,match='availability'):
        reg.rule_states(frame.with_columns((pl.col('available_us')+1).alias('available_us')),0,4*direction.DAY)
    with pytest.raises(ValueError,match='Complete'):
        reg.rule_states(frame.head(3),0,4*direction.DAY)
