"""Independent completed trade/mark bars and the existing MarketTape schema.

This adapter does not choose intraminute paths or invoke an account. Frame input
must come from the SHA/checksum-bound public decoder; tests use labelled fixtures.
"""
from dataclasses import dataclass
from types import MappingProxyType
import re
import numpy as np

MINUTE=60_000_000
DAY=86_400_000_000
PRICE_FIELDS=('open','high','low','close')


def need(condition,message):
    if not bool(condition):raise ValueError(message)


def frozen(a,dtype=None):
    a=np.array(a,dtype=dtype,copy=True);a.flags.writeable=False
    return a


@dataclass(frozen=True)
class DomainBars:
    symbol:str
    family:str
    source_sha256:str
    official_url:str
    open_us:np.ndarray
    close_us:np.ndarray
    available_us:np.ndarray
    values:object


def source_bars(frame,row,required_family,*,added_repair_rows=0):
    need(added_repair_rows==0 and row.get('kind')!='DAILY_UNION',
         'Single original CSV provenance only; added daily repairs require a composite source contract')
    need(required_family in ('klines','markPriceKlines') and row['family']==required_family,
         'Independent trade/mark source family required')
    symbol=row['symbol'];period=row.get('source_period',row['month'])
    frequency='daily' if len(period)==10 else 'monthly'
    wanted=f'https://data.binance.vision/data/futures/um/{frequency}/{required_family}/{symbol}/1m/{symbol}-1m-{period}.zip'
    need(row['official_URL']==wanted and re.fullmatch('[a-f0-9]{64}',row['ZIP_SHA256']),
         'Exact venue/product/symbol/period/source identity required')
    t=frame.timestamp_ms.to_numpy();need(t.dtype.kind in 'iu' and len(t)>0,'Actual integer minute clock')
    need(np.all(t%60000==0) and np.all(np.diff(t)>0),'Unique increasing source minutes')
    end=frame.close_time_ms.to_numpy()
    need(np.array_equal(end,t+59999),'Exact source minute close clock')
    fields=PRICE_FIELDS+(('quote_volume',) if required_family=='klines' else ())
    values={k:frozen(frame[k].to_numpy(),float) for k in fields}
    need(all(np.isfinite(a).all() for a in values.values()),'Finite observed source bars')
    need(all(np.all(values[k]>0) for k in PRICE_FIELDS),'Positive observed OHLC')
    need(np.all(values['high']>=np.maximum(values['open'],values['close'])) and
         np.all(values['low']<=np.minimum(values['open'],values['close'])) and
         np.all(values['low']<=values['high']),'Actual OHLC range identity')
    if required_family=='klines':need(np.all(values['quote_volume']>=0),'Nonnegative trade capacity input')
    return DomainBars(symbol,required_family,row['ZIP_SHA256'],wanted,frozen(t*1000,np.int64),
        frozen(end*1000,np.int64),frozen((t+60000)*1000,np.int64),MappingProxyType(values))


def exact_boundary(bars,left):
    found=np.flatnonzero(bars.open_us==left-MINUTE)
    need(len(found)==1 and bars.available_us[found[0]]==left,'True previous source minute required; no forward fill')
    i=int(found[0])
    return dict(price=float(bars.values['close'][i]),open_us=int(bars.open_us[i]),
                available_us=int(bars.available_us[i]),source_sha256=bars.source_sha256,family=bars.family)


def day_block(symbols,trade,mark,left):
    names=tuple(symbols)
    need(left%DAY==0 and len(names)>0 and len(names)==len(set(names)),'Fixed UTC day and unique asset order')
    need(tuple(trade)==tuple(mark)==names,'Exact source/target asset order; never silently reorder')
    times=frozen(np.arange(left,left+DAY,MINUTE),np.int64);market={};sidecars={}
    for s in names:
        t,m=trade[s],mark[s]
        need(t.symbol==m.symbol==s and t.family=='klines' and m.family=='markPriceKlines',
             'Independent asset-domain binding')
        ti=np.flatnonzero((t.open_us>=left)&(t.open_us<left+DAY))
        mi=np.flatnonzero((m.open_us>=left)&(m.open_us<left+DAY))
        need(np.array_equal(t.open_us[ti],times) and np.array_equal(m.open_us[mi],times),
             f'SOURCE_GAPPED:{s}:complete independent day required; no inner join or imputation')
        market[s]=dict(open=frozen(t.values['open'][ti]),close=frozen(t.values['close'][ti]),
                       quote_volume=frozen(t.values['quote_volume'][ti]),mark=frozen(m.values['close'][mi]))
        sidecars[s]=dict(open_us=frozen(m.open_us[mi]),close_us=frozen(m.close_us[mi]),
            available_us=frozen(m.available_us[mi]),source_sha256=m.source_sha256,family=m.family,
            arrival_clock='UNKNOWN; next-minute completion is only a conservative source-clock proxy',
            extreme_event_us='UNKNOWN',intraminute_order='UNKNOWN',
            mark_ohlc=MappingProxyType({k:frozen(m.values[k][mi]) for k in PRICE_FIELDS}),
            trade_ohlc=MappingProxyType({k:frozen(t.values[k][ti]) for k in PRICE_FIELDS}))
    # This exact four-field projection is accepted unchanged by MarketTape.
    return dict(times=times,market=market,mark_sidecars=sidecars)


def legacy_projection(block):
    return dict(times=block['times'],market=block['market'])


def range_witness(bars,index,*,side,threshold,known_at_us,owned_since_us,events_us=()):
    need(bars.family=='markPriceKlines','Trade high/low cannot witness mark risk')
    need(type(index) is int and 0<=index<len(bars.open_us),'Explicit valid source bar index')
    need(side in ('LONG','SHORT') and np.isfinite(threshold) and threshold>0,'Explicit side and positive threshold')
    need(known_at_us>=int(bars.available_us[index]),'Mark high/low unavailable before bar completion')
    left,right=int(bars.open_us[index]),int(bars.available_us[index])
    ambiguous=owned_since_us is None or owned_since_us>=left or any(left<=e<=right for e in events_us)
    extreme=float(bars.values['low' if side=='LONG' else 'high'][index])
    crossing=extreme<=threshold if side=='LONG' else extreme>=threshold
    return dict(status='AMBIGUOUS_INTRAMINUTE' if ambiguous else ('RANGE_WITNESS' if crossing else 'NO_RANGE_WITNESS'),
        observed_threshold_crossing=crossing,available_us=right,extreme_event_us='UNKNOWN',
        liquidation_event_created=False,fill_created=False,account_transition_created=False,
        scope='Completed mark range only; threshold held fixed, no liquidation price/time inference')
