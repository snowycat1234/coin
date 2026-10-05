"""Causal maturity and directed cost labels, with independent intent oracle."""
import numpy as np
import polars as pl
from scripts.investment import shared_signal_meta as meta
DAY=meta.common.DAY

def bars():
    rows=[]
    for s,flip in [('BTCUSDT',False),('ETHUSDT',True)]:
        values=np.r_[np.linspace(80,120,230),np.linspace(120,60,65),np.linspace(60,90,15)]
        if flip: values=200-values
        for i,c in enumerate(values):
            rows.append(dict(symbol=s,open_us=i*DAY,close_us=(i+1)*DAY,available_us=(i+1)*DAY,
                open=float(c),close=float(c),high=float(c)+1,low=float(c)-1,volume=float(100+i%5)))
    return pl.DataFrame(rows)

def test_fixed_intent_future_prefix_and_scalar_reference():
    b=bars();symbols=('BTCUSDT','ETHUSDT');start=200*DAY;end=310*DAY
    _,intent,_=meta.public_intents(b,symbols,start,end)
    assert meta.verify_public_intents(b,intent,symbols,start,end)['rows']==220
    changed=b.with_columns(pl.when(pl.col('close_us')>280*DAY).then(pl.col('close')*1.04).otherwise(pl.col('close')).alias('close'))
    _,future,_=meta.public_intents(changed,symbols,start,end)
    assert intent.filter(pl.col('close_us')<=280*DAY).equals(future.filter(pl.col('close_us')<=280*DAY))
    assert set(intent['intent'])=={-1,0,1}

def test_label_maturity_cost_once_and_gate_never_inverts():
    b=bars();symbols=('BTCUSDT','ETHUSDT')
    _,intent,_=meta.public_intents(b,symbols,200*DAY,310*DAY)
    f,columns=meta.common.feature_table(b,symbols)
    table=meta.meta_table(f,b,intent)
    columns+=['signal_direction']
    train=meta.matured_train(table,columns,200*DAY,280*DAY)
    assert train['label_available_us'].max()<280*DAY and train['close_us'].max()<=274*DAY
    for r in table.iter_rows(named=True):
        expected=None if r['intent']==0 or r['future_price_return'] is None else int(r['intent']*r['future_price_return']>.0037)
        assert r['execute_label']==expected
    tail=table.filter(pl.col('close_us')>=305*DAY)['execute_label']
    assert len(tail)==10 and tail.null_count()==len(tail)
    p=np.full(table.height,.51);p[::2]=.5
    predictions=meta.direction_predictions(table,p)
    for i,r in enumerate(predictions.iter_rows(named=True)):
        assert r['prediction']-1==(table['intent'][i] if i%2 else 0)
