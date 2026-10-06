"""Past-only features, mature expert utility labels and explicit time folds."""
import json
from pathlib import Path
import numpy as np
import polars as pl
from scipy.special import softmax
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
from scripts.investment.cta_cycle_window import load_window,DAY
from scripts.investment.chandelier_short_levels import runtime

EXPERTS=('SMA200_SIGNED','HOLD','CASH')
def stamp(value):
    from datetime import datetime,UTC
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())*1_000_000

def library(config):
    from scripts.investment.oracle_expert_opportunity import CORE
    ref=config['data']['oracle_library'];assert sha(ROOT/ref['path'])==ref['sha256'];r=json.loads((ROOT/ref['path']).read_bytes())
    cases={}
    for item in r['producers']:
        assert sha(ROOT/item['path'])==item['sha256'];producer=json.loads((ROOT/item['path']).read_bytes())
        for name in CORE:assert producer['binding']['source_hashes'][name]==sha(ROOT/name),'Unchanged financial/data core required: '+name
        task=json.loads((STATE/'task-progress'/('task-'+producer['binding']['task_id']+'.json')).read_bytes());assert task['status']=='completed' and task['exit_code']==0
        for case in producer['cases']:
            mode='CASH' if case['strategy']=='CASH' else 'LONG_ONLY' if case['strategy']=='HOLD' else 'LONG_SHORT'
            if case['strategy'] in EXPERTS and case['mode']==mode:cases[case['strategy'],case['unit']]=case
    assert len(cases)==6;result={}
    for (expert,unit),case in cases.items():
        summary=case['summary'];assert summary['completed_minutes']==1051200 and summary['terminal_cash_realized']
        assert case['independent']['maximum_NAV_error_USDT']<1e-7 and case['independent']['maximum_wallet_error_USDT']<1e-7
        loaded={}
        for key in ('daily_nav.parquet','targets.parquet'):
            p=case['artifacts'][key];assert Path(p['path']).is_relative_to(STATE) and sha(p['path'])==p['sha256'];loaded[key]=pl.read_parquet(p['path'])
        result[expert,unit]=loaded
    return result

def window(config):
    m=config['data']['manifest'];assert sha(m['path'])==m['sha256']
    return load_window(m['path'],('BTCUSDT',),stamp('2021-08-01'),stamp('2024-01-01'))

def features(bars,names):
    b=bars.filter(pl.col('symbol')=='BTCUSDT').sort('close_us');assert np.all(np.diff(b['close_us'])==DAY) and b['available_us'].eq(b['close_us']).all()
    b=b.with_columns((pl.col('close')/pl.col('close').shift(1)-1).alias('r'))
    expr=[]
    for n in (20,50,100,200):expr.append(pl.col('close').rolling_mean(n).alias('sma'+str(n)))
    for n in (10,30,60,200):expr.append(pl.col('r').rolling_std(n,ddof=1).alias('rv'+str(n)))
    b=b.with_columns(expr);expr=[]
    for n in (20,50,100,200):expr.append((pl.col('close')/pl.col('sma'+str(n))-1).alias('distance'+str(n)))
    for n in (50,100,200):expr.append((pl.col('sma'+str(n))/pl.col('sma'+str(n)).shift(5)-1).alias('slope'+str(n)))
    for n in (5,20,60,120,200):expr.append((pl.col('close')/pl.col('close').shift(n)-1).alias('momentum'+str(n)))
    for n in (20,60,200):expr.append((pl.col('close')/pl.col('high').rolling_max(n)-1).alias('drawdown'+str(n)))
    expr += [pl.col('rv30').rolling_std(20,ddof=1).alias('vol_of_vol'),
        ((pl.col('close')/pl.col('close').shift(5)-1)-(pl.col('close').shift(5)/pl.col('close').shift(10)-1)).alias('rebound_velocity'),
        (pl.col('volume')/pl.col('volume').shift(20)-1).alias('volume_momentum'),
        ((pl.col('volume')-pl.col('volume').rolling_mean(30))/pl.col('volume').rolling_std(30,ddof=1)).alias('volume_zscore')]
    b=b.with_columns(expr);ta=runtime();p=b.select('high','low','close').to_pandas()
    atr=ta.atr(p.high,p.low,p.close,length=14,mamode='rma',talib=False)
    rsi=ta.rsi(p.close,length=14,talib=False)
    dc=ta.donchian(p.high,p.low,lower_length=20,upper_length=20)
    assert list(dc.columns)==['DCL_20_20','DCM_20_20','DCU_20_20']
    position=(p.close-dc['DCL_20_20'])/(dc['DCU_20_20']-dc['DCL_20_20'])
    b=b.with_columns(pl.Series('atr_normalized',(atr/p.close).to_numpy()),pl.Series('rsi',rsi.to_numpy()/100),pl.Series('donchian_position',position.to_numpy()))
    b=b.filter((pl.col('close_us')>=stamp('2022-01-01'))&(pl.col('close_us')<stamp('2024-01-01')))
    assert b.height==730 and b.select(names).null_count().sum_horizontal().sum()==0
    assert np.isfinite(b.select(names).to_numpy()).all()
    return b.select(pl.col('close_us').alias('decision_us'),pl.col('available_us').alias('feature_available_us'),*names)

def labels(lib,unit,h):
    returns=[];times=None
    for expert in EXPERTS:
        frame=lib[expert,unit]['daily_nav.parquet'].sort('day_end_us');nav=np.r_[10000.,frame['nav'].to_numpy()]
        clock=frame['day_end_us'].to_numpy()-DAY
        if times is None:times=clock
        else:assert np.array_equal(times,clock)
        y=np.full(730,np.nan);y[:-h]=nav[h:-1]/nav[:-(h+1)]-1
        # Include the last exactly mature label ending at the dataset boundary.
        y[730-h]=nav[-1]/nav[730-h]-1
        returns.append(y)
    utility=np.array(returns).T;relative=utility-utility.mean(axis=1,keepdims=True)
    return times,relative,utility,times+h*DAY

def fold_indices(times,label_ends,h,start,end,min_train):
    valid=(times>=start)&(times<end)
    # Purge train labels touching validation; then H more days of embargo.
    train=(times<start)&(label_ends<=start-h*DAY)
    ti=np.flatnonzero(train);vi=np.flatnonzero(valid)
    assert len(ti)>=min_train and len(vi)>0 and label_ends[ti].max()<=start-h*DAY
    assert times[ti].max()+h*DAY<=start-h*DAY
    return ti,vi

def soft_path(predictions,temperature,max_l1,initial=None):
    from scripts.investment.regime_ranking_screen import bounded_path
    assert temperature>0 and np.isfinite(predictions).all()
    desired=softmax(predictions/temperature,axis=1)
    return bounded_path(desired,np.array([0.,0.,1.]) if initial is None else initial,max_l1)

def targets(lib,unit,decisions,weights):
    from scripts.investment.frozen_expert_mixture import combine
    frames={expert:lib[expert,unit]['targets.parquet'] for expert in EXPERTS}
    clipped={name:frame.filter(pl.col('available_us').is_in(decisions.tolist())) for name,frame in frames.items()}
    return combine(clipped,list(EXPERTS),decisions,('BTCUSDT',),weights)
