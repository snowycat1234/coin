"""Thin shared execute/reject adapter; original daily SMA intent, owned sizing.

The external intent state is independent of fills/meta decisions. This is a
COIN intent filter, not a reproduction of Jesse whole-balance execution.
"""
import numpy as np
import polars as pl
from scripts.investment import public_sma_perpetual as public
from scripts.investment import shared_direction_model as common

MODEL={k:v for k,v in common.MODEL.items() if k not in ('objective','num_class','eval_metric')}
MODEL.update(objective='binary:logistic',eval_metric='logloss')

def public_intents(bars,symbols,start,end):
    decisions=np.arange(start,end,common.DAY,dtype=np.int64)
    targets,receipt=public.fixed_targets(bars,decisions,'LONG_SHORT',symbols=symbols)
    intents=targets.select('symbol',pl.col('available_us').alias('close_us'),
        pl.col('raw_signed_target').sign().cast(pl.Int32).alias('intent'))
    return targets,intents,receipt

def meta_table(features,bars,intents):
    frame=common.label_table(features,bars).join(intents,on=['symbol','close_us'],how='inner',validate='1:1')
    return frame.with_columns((pl.col('future_price_return')*pl.col('intent')).alias('directed_future_return'),
        pl.col('intent').cast(pl.Float32).alias('signal_direction')).with_columns(
        pl.when(pl.col('intent')==0).then(None)
        .when(pl.col('directed_future_return').is_null()).then(None)
        .otherwise((pl.col('directed_future_return')>.0037).cast(pl.Int32)).alias('execute_label'))

def matured_train(frame,columns,start,cutoff):
    return frame.filter((pl.col('close_us')>=start)&(pl.col('label_available_us')<cutoff)&
        pl.col('execute_label').is_not_null()&pl.all_horizontal([pl.col(f).is_not_null() for f in columns]))

def direction_predictions(frame,probability=None):
    if probability is None: approved=np.ones(frame.height,dtype=bool)
    else:
        p=np.asarray(probability)
        if p.shape!=(frame.height,) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
            raise ValueError('One finite bounded execute probability per ordered row')
        approved=p>.5  # Tie rejects; fixed before economic results.
    direction=np.where(approved,frame['intent'].to_numpy(),0)
    return frame.select('symbol','close_us','available_us').with_columns(
        pl.Series('prediction',direction+1),pl.Series('P_execute',probability if probability is not None else np.ones(frame.height)))

def verify_public_intents(bars,intents,symbols,start,end):
    """Independent scalar SMA/state reference, no vendor or production hooks."""
    observed={(r['close_us'],r['symbol']):r['intent'] for r in intents.iter_rows(named=True)}
    for s in symbols:
        b=bars.filter(pl.col('symbol')==s).sort('close_us')
        clocks=b['close_us'].to_numpy();closes=b['close'].to_numpy();available=b['available_us'].to_numpy()
        state=0
        for t in range(start,end,common.DAY):
            i=int(np.searchsorted(clocks,t,side='right')-1)
            if i<199 or clocks[i]!=t or np.any(available[i-199:i+1]>t) or np.any(np.diff(clocks[i-199:i+1])!=common.DAY):
                state=0
            else:
                fast=sum(float(v) for v in closes[i-49:i+1])/50
                slow=sum(float(v) for v in closes[i-199:i+1])/200
                if state==1 and fast<slow or state==-1 and fast>slow: state=0
                elif state==0: state=1 if fast>slow else -1 if fast<slow else 0
            if observed[(t,s)]!=state: raise ValueError('Independent original SMA intent/state discrepancy')
    return dict(status='PASS_SCALAR_PUBLIC_LONG_SHORT_EXIT_EQUALITY_AND_ORDERED_INTENTS',rows=len(observed))
