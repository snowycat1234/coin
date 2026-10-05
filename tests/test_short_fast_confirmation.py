"""Actual causal short exits, independent indicators and unchanged default."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import polars as pl
from scripts.investment import short_fast_confirmation as fast
from scripts.investment import perpetual_directional as engine
from scripts.investment import cta_classics as cta, audit_cta_classics as reference

START=1_754_006_400_000_000
SYMBOLS=('BTCUSDT','ETHUSDT')
MINUTE=60_000_000


def test_fast_original_kernel_reference_future_and_order():
    rows=[]
    for s in SYMBOLS:
        for i in range(90):
            price=150-i if i<50 else 100+2*(i-50)
            t=START+(i+1)*fast.FOUR_HOURS
            rows.append(dict(symbol=s,open_us=t-fast.FOUR_HOURS,close_us=t,available_us=t,
                open=float(price),close=float(price),high=price+.1,low=price-.1,volume=100.))
    b=pl.DataFrame(rows);f=fast.signals(b,SYMBOLS)
    fast.verify_signals(f,b,SYMBOLS)
    assert {-1,0,1}<=set(f['fast_state'].drop_nulls())
    cutoff=START+60*fast.FOUR_HOURS
    changed=b.with_columns(*[pl.when(pl.col('close_us')>cutoff).then(pl.col(k)*3).otherwise(pl.col(k)).alias(k) for k in ('open','high','low','close')])
    future=fast.signals(changed,SYMBOLS)
    assert f.filter(pl.col('close_us')<=cutoff).equals(future.filter(pl.col('close_us')<=cutoff))
    assert f.equals(fast.signals(b,SYMBOLS[::-1]))


def small_window():
    n=275
    daily=pl.DataFrame([dict(symbol=s,open_us=START-cta.DAY,close_us=START,available_us=START,
        open=100.,close=100.,high=101.,low=99.,volume=1000.) for s in SYMBOLS])
    market={s:dict(open=np.full(n,100.),close=np.full(n,100.),mark=np.full(n,100.),
        high=np.full(n,101.),low=np.full(n,99.),volume=np.full(n,1000.),quote_volume=np.full(n,1e6)) for s in SYMBOLS}
    # Exit is observed at completed4h, then a capacity shortage delays paid fills.
    for k in ('open','close','mark','high','low'):market['BTCUSDT'][k][241:]=108.
    market['BTCUSDT']['quote_volume'][240:247]=0.
    market['BTCUSDT']['quote_volume'][247]=108000.
    return dict(symbols=SYMBOLS,start=START,end=START+n*MINUTE,daily=daily,market=market,events=[])


def contexts():
    f=pl.DataFrame([dict(symbol=s,close_us=t,available_us=t,fast_state=(-1 if t==START or s=='ETHUSDT' else 0))
        for t in (START,START+fast.FOUR_HOURS) for s in SYMBOLS])
    slow=pl.DataFrame([dict(symbol=s,close_us=START,available_us=START,DC_CONFIRMED_SHORT=(-1. if s=='BTCUSDT' else 1.)) for s in SYMBOLS])
    return f,slow


def target(b,d,m):
    return pl.DataFrame([dict(symbol=s,available_us=int(t),target_weight=(-.1 if s=='BTCUSDT' else .1)) for t in d for s in SYMBOLS]),{}


def test_actual_delayed_partial_short_close_long_unchanged_and_default_golden():
    f,slow=contexts();w=small_window()
    plain=engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=target,persist_cash_close=True)
    permit=f.with_columns(pl.lit(-1).alias('fast_state'))
    same=engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=target,
        position_protection=fast.FastShortConfirmation(permit,slow),persist_cash_close=True)
    assert same['minute'].equals(plain['minute']) and same['trades']==plain['trades']
    case=engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=target,
        position_protection=fast.FastShortConfirmation(f,slow),persist_cash_close=True)
    trigger=START+fast.FOUR_HOURS
    exits=[r for r in case['trades'] if r['signal_us']==trigger]
    assert exits and all(r['symbol']=='BTCUSDT' and r['leg']=='CLOSE' and r['side']=='BUY' and r['fee_USDT_mid']>0 and r['execution_cost']>0 for r in exits)
    assert [r['event_us'] for r in exits]==[START+i*MINUTE+1 for i in (248,249)]
    assert exits[-1]['quantity_after']==0 and len(exits)==2
    # Extra BTC orders legitimately change global order IDs and shared cash.
    keys=('symbol','side','leg','event_us','signal_us','quantity','fill_price','fee_USDT_mid','execution_cost')
    def own_fills(c):return [{k:r[k] for k in keys} for r in c['trades'] if r['symbol']=='ETHUSDT']
    assert own_fills(plain)==own_fills(case)
    assert not any(r.get('kind')=='PROTECTIVE_STOP' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' for r in case['rejections'])
    changed=deepcopy(w)
    for k in ('open','close','mark','high','low'):changed['market']['BTCUSDT'][k][260:]*=1.03
    future=engine.simulate(changed,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=target,
        position_protection=fast.FastShortConfirmation(f,slow),persist_cash_close=True)
    assert case['minute'].filter(pl.col('close_us')<=START+260*MINUTE).equals(future['minute'].filter(pl.col('close_us')<=START+260*MINUTE))
    p=fast.FastShortConfirmation(f,slow);p.prepare(w['daily'],SYMBOLS,START,w['end'])
    q={s:SimpleNamespace(quantity=-1) for s in SYMBOLS}
    p.observe(trigger,w['market'],q);assert p.blocked('BTCUSDT') and not p.blocked('ETHUSDT')
    # Fast state turning down cannot reopen intraday. Only the daily scheduler can add.
    assert p.observe(trigger+MINUTE,w['market'],q)==[]


def test_mask_before_signed_covariance_preserves_long_forecast_and_risk_priority():
    rows=[]
    for s,m in [('BTCUSDT',1),('ETHUSDT',2)]:
        for i in range(32):
            t=START-(31-i)*cta.DAY;price=(100+i+np.sin(i))*m
            rows.append(dict(symbol=s,open_us=t-cta.DAY,close_us=t,available_us=t,open=price,close=price,high=price+1,low=price-1,volume=100.))
    bars=pl.DataFrame(rows);f,slow=contexts()
    blocked=f.with_columns(pl.lit(0).alias('fast_state'))
    gated=fast.mask_daily(slow,blocked)
    assert gated['DC_CONFIRMED_SHORT'].to_list()==[0.,1.]
    t,_=cta.targets(gated,bars,[START],'LONG_SHORT',SYMBOLS,'DC_CONFIRMED_SHORT')
    reference.verify_targets(t,gated,bars,SYMBOLS,'DC_CONFIRMED_SHORT','LONG_SHORT')
    assert t.filter(pl.col('symbol')=='BTCUSDT')['target_weight'][0]==0
    # A hard cap breach with no liquidity must halt, despite active fast exit.
    w=small_window();w['market']['BTCUSDT']['mark'][240:]=110.;w['market']['BTCUSDT']['quote_volume'][240:]=0.
    def heavy(b,d,m):
        t,meta=target(b,d,m)
        return t.with_columns(pl.when(pl.col('symbol')=='BTCUSDT').then(-.299).otherwise(0.).alias('target_weight')),meta
    halted=engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=heavy,
        position_protection=fast.FastShortConfirmation(f,slow),persist_cash_close=True)
    assert halted['summary']['completion']=='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION'
