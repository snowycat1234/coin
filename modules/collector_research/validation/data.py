"""Frozen target and observed-market adapters; no financial engine reimplementation."""
import json,re,os,sys
from pathlib import Path
from .runtime import ROOT,WORK,REPO,STATE,DAY,MINUTE,atomic,progress,sha
import numpy as np
import polars as pl
from scripts.investment import perpetual_directional as engine
from scripts.investment import audit_shared_direction as independent
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
MODELS=('PER_ASSET_XGB','TCN_SHARED','GRU_SHARED','TRANSFORMER_SHARED')
CONTROLS=('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3','BASE_CASH')
def split_observed_minutes(times,observations):
    """Preserve every clock tick and omit an asset only at its actual gaps."""
    masks={};boundaries={0,len(times)}
    for symbol,values in observations.items():
        stamps=values['times']
        if np.any(np.diff(stamps)<=0) or not np.isin(stamps,times).all():
            raise ValueError('Off-grid or duplicate actual minute inputs')
        mask=np.isin(times,stamps,assume_unique=True);masks[symbol]=mask
        boundaries.update((np.flatnonzero(mask[1:]!=mask[:-1])+1).tolist())
    cuts=sorted(boundaries)
    for left,right in zip(cuts,cuts[1:]):
        market={}
        for symbol,values in observations.items():
            if not masks[symbol][left]:continue
            a=np.searchsorted(values['times'],times[left]);b=a+right-left
            market[symbol]={key:array[a:b] for key,array in values.items() if key!='times'}
        yield dict(times=times[left:right],market=market)

class Reporter:
    def __init__(self,path,name):self.path=Path(path);self.name=name
    def update(self,phase,current,total,unit='',**details):
        progress(self.path,phase,current,total,self.name,unit=unit,**details)

def target_series(study,name,symbols):
    manifest=json.loads((study/'TARGETS_MANIFEST.json').read_text())
    expected={r['name']:r['sha256'] for r in manifest['files']}
    files=sorted(study.glob(f'fold*_{name}_targets.npz'),key=lambda p:int(re.match(r'fold(\d+)_',p.name)[1]))
    if not files:raise ValueError('Missing actual model targets: '+name)
    dates=[];weights=[]
    for path in files:
        if sha(path)!=expected[path.name]:raise ValueError('Target artifact changed: '+path.name)
        with np.load(path,allow_pickle=False) as data:
            if data['symbol_order'].tolist()!=symbols:raise ValueError('Target symbol order changed')
            dates.append(data['decision_us'].copy());weights.append(data['weights'].copy())
    dates=np.concatenate(dates);weights=np.concatenate(weights)
    if dates.dtype.kind not in 'iu' or np.any(np.diff(dates)!=DAY) or np.any(dates%DAY):
        raise ValueError('Model decisions must cover one complete chronological UTC-day calendar')
    if weights.shape!=(len(dates),len(symbols)) or not np.isfinite(weights).all():raise ValueError('Invalid target shape/values')
    if (np.abs(weights)>.3+1e-9).any() or (np.abs(weights).sum(1)>.6+1e-9).any():raise ValueError('Target risk caps exceeded')
    end=int(dates[-1])+DAY
    if end>1772323200000000:raise ValueError('Locked 2026-03-01 boundary would be crossed')
    return dates,weights

def market_window(symbols,start,end):
    base=WORK/'data/normalized'
    daily=[];events=[]
    for symbol in symbols:
        frame=pl.read_parquet(base/(symbol+'_daily.parquet'))
        daily.append(frame.select('symbol','open_us','close_us','available_us','open','high','low','close','volume','quote_volume'))
        funding=pl.read_parquet(base/(symbol+'_funding_events.parquet'))
        for row in funding.filter((pl.col('calc_time_ms')*1000>=start)&(pl.col('calc_time_ms')*1000<end)).iter_rows(named=True):
            events.append(dict(symbol=symbol,event_us=int(row['calc_time_ms'])*1000,
                               raw_rate=float(row['last_funding_rate']),
                               reported_interval_hours=float(row['funding_interval_hours'])))
    events.sort(key=lambda r:(r['event_us'],r['symbol']))
    if len({(r['symbol'],r['event_us']) for r in events})!=len(events):raise ValueError('Duplicate funding events')

    def blocks():
        from datetime import datetime,UTC
        month=None;cache={}
        for day in range(start,end,DAY):
            key=datetime.fromtimestamp(day/1e6,UTC).strftime('%Y-%m')
            if key!=month:
                cache={};month=key
                for symbol in symbols:
                    for family in ('klines','markPriceKlines'):
                        p=base/'minute'/symbol/family/(key+'.parquet')
                        cache[symbol,family]=pl.read_parquet(p) if p.is_file() else None
            times=np.arange(day,day+DAY,MINUTE,dtype=np.int64);observations={}
            for symbol in symbols:
                trade,marks=cache[symbol,'klines'],cache[symbol,'markPriceKlines']
                if trade is None or marks is None:continue
                t=trade.filter((pl.col('open_us')>=day)&(pl.col('open_us')<day+DAY)).sort('open_us')
                m=marks.filter((pl.col('timestamp_ms')*1000>=day)&(pl.col('timestamp_ms')*1000<day+DAY)).sort('timestamp_ms')
                if not t['available_us'].eq(t['open_us']+MINUTE).all() or not m['close_time_ms'].eq(m['timestamp_ms']+59999).all():
                    raise ValueError('Minute availability/closure contract changed')
                joined=t.join(m.select((pl.col('timestamp_ms')*1000).alias('open_us'),pl.col('close').alias('mark')),
                              on='open_us',how='inner',validate='1:1').sort('open_us')
                if joined.is_empty():continue
                observations[symbol]=dict(times=joined['open_us'].to_numpy(),open=joined['open'].to_numpy(),
                    close=joined['close'].to_numpy(),quote_volume=joined['quote_volume'].to_numpy(),mark=joined['mark'].to_numpy())
            yield from split_observed_minutes(times,observations)
    return dict(start=start,end=end,symbols=tuple(symbols),daily=pl.concat(daily).sort(['symbol','close_us']),
                events=events,minute_blocks=blocks)

def saved_case_valid(value,binding):
    if value.get('binding')!=binding:raise ValueError('Resume refuses changed source/data/model bindings')
    for record in value['artifacts'].values():
        if not Path(record['path']).is_file() or sha(record['path'])!=record['sha256']:raise ValueError('Completed account artifact changed')
    if sha(value['summary_path'])!=value['summary_sha256']:raise ValueError('Completed account summary changed')
    if sha(value['independent_audit_path'])!=value['independent_audit_sha256']:raise ValueError('Completed independent audit changed')
    return True
