"""Observed stops must produce paid delayed fills and causal cooldowns."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import polars as pl
from scripts.investment import perpetual_directional as engine
from scripts.investment.cta_atr_protection import InitialATRProtection,DAY,MINUTE,next_month

START=1_754_006_400_000_000
SYMBOLS=('BTCUSDT','ETHUSDT')

def window():
    daily=pl.DataFrame([dict(symbol=s,open_us=t-DAY,close_us=t,available_us=t,
        open=100.,close=100.,high=101.,low=99.,volume=1000.)
        for s in SYMBOLS for t in range(START-240*DAY,START+DAY,DAY)])
    n=35;market={s:dict(open=np.full(n,100.),close=np.full(n,100.),mark=np.full(n,100.),
        high=np.full(n,101.),low=np.full(n,99.),volume=np.full(n,1000.),quote_volume=np.full(n,1e6)) for s in SYMBOLS}
    # A stop cannot infer ordering in the entry minute. A later completed
    # minute crosses the short stop, then execution gaps beyond that stop.
    market['BTCUSDT']['high'][1]=110.
    market['BTCUSDT']['high'][3]=106.
    for k in ('open','close','mark','high','low'):market['BTCUSDT'][k][5:]=108.
    market['BTCUSDT']['quote_volume'][4:11]=0.
    market['BTCUSDT']['quote_volume'][11]=108000.
    return dict(symbols=SYMBOLS,start=START,end=START+n*MINUTE,daily=daily,market=market,events=[])

def targets(b,d,m):return pl.DataFrame([dict(symbol=s,available_us=int(t),target_weight=-.1 if s=='BTCUSDT' else 0.) for t in d for s in SYMBOLS]),{}

def run(w,**kw):return engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,
    position_protection=InitialATRProtection(),persist_cash_close=True,**kw)

def test_original_atr_formula_partial_stop_cooldown_and_future_prefix():
    w=window();case=run(w);j=case['protection_journal']
    arm=next(r for r in j if r['kind']=='ARM')
    assert abs(arm['atr']-2.)<1e-12 and abs(arm['stop_price']-arm['entry_fill_price']-4.)<1e-12
    trigger=next(r for r in j if r['kind']=='OBSERVED_STOP_TRIGGER')
    assert trigger['event_us']==START+4*MINUTE and trigger['armed_us']<trigger['minute_open_us']
    fills=[r for r in case['trades'] if r['signal_us']==trigger['event_us']]
    assert [r['event_us'] for r in fills]==[START+k*MINUTE+1 for k in (12,13)]
    assert [r['quantity'] for r in fills]==[1.,8.9] and fills[-1]['quantity_after']==0
    assert all(r['leg']=='CLOSE' and r['side']=='BUY' and r['mid_price']==108. and r['fee_USDT_mid']>0 and r['execution_cost']>0 for r in fills)
    assert len([r for r in case['trades'] if r['leg']=='OPEN'])==1
    assert not any(r.get('kind')=='PROTECTIVE_STOP' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' for r in case['rejections'])
    p=InitialATRProtection();p.prepare(w['daily'],SYMBOLS,START,START+DAY);p.blocks['BTCUSDT']=next_month(START)
    tiny=w['daily'].with_columns(*(pl.col(k)*1e-7 for k in ('open','close','high','low')))
    small=InitialATRProtection();small.prepare(tiny,SYMBOLS,START,START+DAY)
    assert abs(small.values[('BTCUSDT',START)]['distance']/4e-7-1)<1e-12
    flat={s:SimpleNamespace(quantity=0) for s in SYMBOLS}
    p.on_decision(START+DAY,flat);assert p.blocked('BTCUSDT')
    flat['BTCUSDT'].quantity=-1;p.on_decision(next_month(START),flat);assert p.blocked('BTCUSDT')
    flat['BTCUSDT'].quantity=0;p.on_decision(next_month(START)+DAY,flat);assert not p.blocked('BTCUSDT')
    changed=deepcopy(w)
    for k in ('open','close','mark','high','low'):changed['market']['BTCUSDT'][k][20:]*=1.03
    future=run(changed);cut=START+20*MINUTE
    assert case['minute'].filter(pl.col('close_us')<=cut).equals(future['minute'].filter(pl.col('close_us')<=cut))
    assert [r for r in case['trades'] if r['event_us']<cut]==[r for r in future['trades'] if r['event_us']<cut]

def test_long_stop_is_symmetric_and_gap_halt_not_rescued():
    w=window()
    for k in ('open','close','mark','high','low'):w['market']['BTCUSDT'][k][5:]=100.
    w['market']['BTCUSDT']['high'][:]=101.;w['market']['BTCUSDT']['low'][:]=99.
    w['market']['BTCUSDT']['low'][3]=94.
    def longs(b,d,m):
        t,meta=targets(b,d,m);return t.with_columns((-pl.col('target_weight')).alias('target_weight')),meta
    case=engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=longs,position_protection=InitialATRProtection())
    arm=next(r for r in case['protection_journal'] if r['kind']=='ARM')
    assert abs(arm['entry_fill_price']-arm['stop_price']-4.)<1e-12
    assert any(r['side']=='SELL' and r['leg']=='CLOSE' for r in case['trades'])
    gap=window();gap['market']['BTCUSDT']['mark'][3:]=210.
    halted=run(gap)
    assert halted['summary']['completion']=='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED'
    assert not halted['summary']['terminal_cash_realized']
    assert not any(r['leg']=='CLOSE' for r in halted['trades'])

def test_protection_does_not_replace_hard_risk_halt_with_unlimited_retries():
    w=window();w['market']['BTCUSDT']['mark'][3:]=110.
    w['market']['BTCUSDT']['quote_volume'][4:]=0.
    def heavy(b,d,m):
        t,meta=targets(b,d,m)
        return t.with_columns(pl.when(pl.col('target_weight')<0).then(-.299).otherwise(0.).alias('target_weight')),meta
    case=engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=heavy,position_protection=InitialATRProtection())
    assert case['summary']['completion']=='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION'
    assert any(r['kind']=='OBSERVED_STOP_TRIGGER' for r in case['protection_journal'])
    assert not case['summary']['terminal_cash_realized']
