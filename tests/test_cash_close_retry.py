"""Capacity-constrained zero-target retry; synthetic execution, not alpha."""
import hashlib
import json
from copy import deepcopy
import numpy as np
import polars as pl
from quant.paths import ROOT
from scripts.investment import perpetual_directional as engine

START=1_754_006_400_000_000
SYMBOLS=('BTCUSDT','ETHUSDT')
DAY=engine.DAY
MINUTE=engine.MINUTE

def retry_window():
    n=1440+24
    market={}
    for s in SYMBOLS:
        prices=np.full(n,100.)
        if s=='BTCUSDT': prices[1450:]=103.
        capacity=np.full(n,1_000_000.)
        capacity[1439:1447]=0.
        # Sixth retry can partially close; seventh can complete, always paid.
        capacity[1446]=100_000.
        market[s]=dict(open=prices,close=prices.copy(),mark=prices.copy(),quote_volume=capacity)
    daily=pl.DataFrame([dict(symbol=s,close_us=t,close=100.) for t in (START,START+DAY) for s in SYMBOLS])
    events=[dict(symbol='BTCUSDT',event_us=START+DAY+offset*MINUTE+1000,
        raw_rate=.001,reported_interval_hours=8.) for offset in (7,12)]
    return dict(symbols=SYMBOLS,start=START,end=START+n*MINUTE,daily=daily,market=market,events=events)

def retry_targets(bars,decisions,mode):
    return pl.DataFrame([dict(symbol=s,available_us=int(t),target_weight=(-.1 if s=='BTCUSDT' and t==START else 0.))
        for t in decisions for s in SYMBOLS]),dict(scope='SYNTHETIC_FIXED_SHORT_THEN_CASH')

def receipt(case):
    data={k:case[k] for k in ('summary','trades','funding','rejections','breaches','target_meta')}
    data['targets']=case['targets'].to_dicts()
    data['minute']=case['minute'].to_dicts()
    return hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def run(window,**kwargs):
    return engine.simulate(window,'SHORT_ONLY',engine.COSTS[0],engine.UNITS[0],target_factory=retry_targets,**kwargs)

def test_default_account_matches_prechange_golden():
    golden=json.loads((ROOT/'reports/CASH_CLOSE_DEFAULT_GOLDEN_20261005_V1.json').read_bytes())
    a=run(retry_window())
    b=run(retry_window(),persist_cash_close=False)
    assert receipt(a)==receipt(b)==golden['receipt_sha256']
    assert any(r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' and r.get('kind')=='DAILY_TARGET' and r['remaining_signed_quantity']>0 for r in a['rejections'])

def test_persistent_close_partial_fill_fees_funding_and_future_prefix():
    w=retry_window();old=run(w);new=run(w,persist_cash_close=True)
    closes=[r for r in new['trades'] if r['signal_us']==START+DAY]
    assert len(closes)==2 and all(r['leg']=='CLOSE' and r['side']=='BUY' for r in closes)
    assert [r['event_us'] for r in closes]==[START+DAY+i*MINUTE+1 for i in (7,8)]
    assert [r['quantity'] for r in closes]==[1.,8.9]
    assert closes[-1]['quantity_after']==0
    assert all(r['fee_USDT_mid']>0 and r['execution_cost']>0 for r in closes)
    assert not any(r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' and r.get('kind')=='DAILY_TARGET' and r.get('remaining_signed_quantity',0)>0 for r in new['rejections'])
    assert new['summary']['terminal_cash_realized'] and new['summary']['terminal_marked_notional']==0
    assert new['funding'][0]['quantity']==-8.9 and new['funding'][1]['quantity']==0
    assert old['funding'][1]['quantity']==-9.9
    # New rule may never open from a zero target or use future capacity.
    assert all(v<=0 for v in new['minute']['BTCUSDT_quantity'])
    for r in closes:
        i=(r['event_us']-START-1)//MINUTE
        assert r['quantity']*r['mid_price']<=w['market']['BTCUSDT']['quote_volume'][i-1]*.001+1e-9
    changed=deepcopy(w);changed['market']['BTCUSDT']['open'][1451:]*=1.01
    changed['market']['BTCUSDT']['mark'][1451:]*=1.01
    future=run(changed,persist_cash_close=True)
    cut=START+1451*MINUTE
    assert new['minute'].filter(pl.col('close_us')<=cut).equals(future['minute'].filter(pl.col('close_us')<=cut))
    assert [r for r in new['trades'] if r['event_us']<cut]==[r for r in future['trades'] if r['event_us']<cut]

def test_persistent_cash_does_not_rescue_unexecutable_risk_reduction():
    w=retry_window()
    w['market']['BTCUSDT']['mark'][3:]=110.
    w['market']['BTCUSDT']['quote_volume'][4:]=0.
    def risk_targets(bars,decisions,mode):
        targets,meta=retry_targets(bars,decisions,mode)
        return targets.with_columns(pl.when(pl.col('target_weight')<0).then(-.299).otherwise(0.).alias('target_weight')),meta
    def risk_run(**kw):
        return engine.simulate(w,'SHORT_ONLY',engine.COSTS[0],engine.UNITS[0],target_factory=risk_targets,**kw)
    a=risk_run();b=risk_run(persist_cash_close=True)
    assert a['summary']['completion']==b['summary']['completion']=='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION'
    assert a['summary']['stop_us']==b['summary']['stop_us']
    assert a['trades']==b['trades'] and not b['summary']['terminal_cash_realized']
