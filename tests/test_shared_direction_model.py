import numpy as np
import polars as pl
import pytest
from scripts.investment import shared_direction_model as m

SYMS=('BTCUSDT','ETHUSDT')

def bars():
    rows=[]
    for j,s in enumerate(SYMS):
        for i in range(300):
            price=100*np.exp(.001*i+.02*np.sin(i/7+j))
            rows.append(dict(symbol=s,open_us=i*m.DAY,close_us=(i+1)*m.DAY,
                available_us=(i+1)*m.DAY,open=price,close=price+.1,high=price+1,
                low=price-1,volume=100+i))
    return pl.DataFrame(rows)

def test_future_price_volume_cannot_change_current_features_targets():
    b=bars(); t=260*m.DAY
    disturbed=b.with_columns(*[pl.when(pl.col('open_us')>=t).then(pl.col(c)*3)
        .otherwise(pl.col(c)).alias(c) for c in ('open','close','high','low','volume')])
    a,cols=m.feature_table(b,SYMS); z,_=m.feature_table(disturbed,SYMS)
    assert a.filter(pl.col('close_us')<=t).select(cols).equals(z.filter(pl.col('close_us')<=t).select(cols))
    preds=pl.DataFrame(dict(close_us=[t,t],symbol=list(SYMS),prediction=[2,0]))
    x,_=m.targets(preds,b,np.array([t]),'LONG_SHORT',SYMS)
    y,_=m.targets(preds,disturbed,np.array([t]),'LONG_SHORT',SYMS)
    assert x.equals(y)
    assert x['target_weight'][0]>0 and x['target_weight'][1]<0

def test_label_cost_band_and_missing_future_not_cash():
    b=bars(); f,_=m.feature_table(b,SYMS)
    x=m.label_table(f,b)
    for row in x.filter(pl.col('label').is_not_null()).iter_rows(named=True):
        raw=row['exit_proxy']/row['entry_proxy']-1
        assert row['label']==(2 if raw>.0037 else 0 if raw<-.0037 else 1)
        assert row['label_available_us']==row['close_us']+5*m.DAY+1
    assert x.filter(pl.col('close_us')>=295*m.DAY)['label'].null_count()>0
    train=x.filter(pl.col('label_available_us')<260*m.DAY)
    assert train['close_us'].max()<255*m.DAY

def test_order_covariance_mapping_and_long_only_is_mask_not_inversion():
    b=bars(); t=260*m.DAY
    p=pl.DataFrame(dict(close_us=[t,t],symbol=list(SYMS),prediction=[2,0]))
    a,_=m.targets(p,b,np.array([t]),'LONG_SHORT',SYMS)
    r,_=m.targets(p,b,np.array([t]),'LONG_SHORT',SYMS[::-1])
    assert np.allclose(a['target_weight'],r['target_weight'][::-1],atol=1e-15)
    z,_=m.targets(p,b,np.array([t]),'LONG_ONLY',SYMS)
    assert z['target_weight'][1]==0 and z['target_weight'][0]>0
    c,_=m.targets(p,b,np.array([t]),'CASH',SYMS)
    assert c['target_weight'].abs().sum()==0

def test_unavailable_bar_fails_instead_of_backdating():
    b=bars().with_columns((pl.col('available_us')+1).alias('available_us'))
    with pytest.raises(ValueError,match='causal'):
        m.feature_table(b,SYMS)

@pytest.mark.parametrize('closed',[True,False])
@pytest.mark.parametrize('exit_price',[90.,110.])
@pytest.mark.parametrize('rate',[0.,.01,-.01])
def test_independent_short_wallet_and_real_residual(tmp_path,closed,exit_price,rate):
    import json
    from scripts.investment.audit_shared_direction import verify
    trades=[dict(symbol='BTCUSDT',event_us=1,leg='OPEN',quantity_before=0.,quantity_after=-1.,
        decimal_strings=dict(position_delta='-1',fill_price='100',fee_amount='.055',execution_cost='0'))]
    times=[60_000_000,120_000_000,180_000_000]
    funding_cash=100*rate
    funds=[] if not rate else [dict(symbol='BTCUSDT',event_us=120_000_000,quantity=-1.,
        mark_close_us=60_000_000,mark_price=100.,raw_rate=rate,signed_funding_USDT=funding_cash)]
    if closed:
        trades.append(dict(symbol='BTCUSDT',event_us=120_000_001,leg='CLOSE',quantity_before=-1.,quantity_after=0.,
            decimal_strings=dict(position_delta='1',fill_price=str(exit_price),fee_amount=str(exit_price*.00055),execution_cost='0')))
    gross=100-exit_price
    final=10000+gross-.055+funding_cash-(exit_price*.00055 if closed else 0)
    minute=pl.DataFrame(dict(close_us=times,nav=[9999.945,10000+gross-.055+funding_cash,final],
        BTCUSDT_quantity=[-1.,-1.,0. if closed else -1.],
        BTCUSDT_signed_marked_notional=[-100.,-exit_price,0. if closed else -exit_price],
        cumulative_fees=[.055,.055,.055+exit_price*.00055 if closed else .055],cumulative_execution_costs=[0.,0.,0.],
        cumulative_funding=[0.,funding_cash,funding_cash],free_cash=[9899.945,9899.945+funding_cash,final if closed else 9899.945+funding_cash],
        isolated_balance=[100.,100.,0. if closed else 100.]))
    minute.write_parquet(tmp_path/'minute_nav_inventory.parquet')
    for name,value in [('trades',trades),('funding',funds),('summary',dict(NAV=final,net_PnL=final-10000,
        terminal_cash_realized=closed,long_short_marked_contribution=dict(LONG=dict(net_contribution=0.),
            SHORT=dict(net_contribution=final-10000))))]:
        (tmp_path/(name+'.json')).write_text(json.dumps(value))
    checked=verify(tmp_path,['BTCUSDT'],1)
    assert checked['actual_short_open_legs']==1
    assert checked['terminal_cash_realized']==closed
    assert checked['maximum_wallet_error_USDT']<1e-7
    assert checked['liquidated_return_scope']==('EVALUABLE' if closed else 'NOT_EVALUABLE_RETAIN_REAL_RESIDUAL')
