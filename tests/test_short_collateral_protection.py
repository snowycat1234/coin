"""Mark-based tail stops reuse delayed paid fills and cannot rescue a gap."""
from copy import deepcopy
from decimal import Decimal as D
import hashlib,json
from types import SimpleNamespace
import numpy as np
import polars as pl
from test_cta_atr_protection import window,targets,START,DAY,MINUTE,SYMBOLS,engine
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment.short_collateral_protection import ShortCollateralProtection


def run(w,protected=True):
    fixed,_=targets(w['daily'],np.array([START]),'LONG_SHORT')
    opts={'position_protection':ShortCollateralProtection(fixed)} if protected else {}
    return engine.simulate(w,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,
        account_factory=BybitIsolatedAccount,persist_cash_close=True,**opts)


def fingerprint(c):
    v={k:c[k].to_dicts() if hasattr(c[k],'to_dicts') else c[k] for k in ('targets','trades','funding','minute','rejections','breaches')}
    return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def test_default_golden_and_no_trigger_exact_with_four_column_block_schema():
    w=window();base=run(w,False)
    assert fingerprint(base)=='ec67a87c5c57602e2f5fb262d42f0d4b5b476e0c262a0b6a5461bb7f38062887'
    for s in SYMBOLS:
        for k in ('high','low','volume'):w['market'][s].pop(k)
    # No OHLCV dependency; also exercise streamed schema, not only arrays.
    n=len(w['market']['BTCUSDT']['open']);market=w.pop('market')
    w['minute_blocks']=lambda:iter([dict(times=np.arange(START,START+n*MINUTE,MINUTE),market=market)])
    case=run(w)
    assert fingerprint(case)==fingerprint(base)
    assert not case['protection_journal']


def test_paid_delayed_partial_exit_persists_and_future_does_not_change_prefix():
    w=window();w['market']['BTCUSDT']['mark'][3:]=160.
    for k in ('open','close'):w['market']['BTCUSDT'][k][5:]=162.
    # Existing zero capacity until minute12, then partial and remaining fill.
    case=run(w);j=case['protection_journal'];trigger=next(x for x in j if x['kind']=='OBSERVED_SHORT_COLLATERAL_FLOOR')
    assert trigger['event_us']==START+4*MINUTE
    fills=[x for x in case['trades'] if x['signal_us']==trigger['event_us']]
    assert [x['event_us'] for x in fills]==[START+k*MINUTE+1 for k in (12,13,14)]
    assert all(x['side']=='BUY' and x['leg']=='CLOSE' and x['fee_amount']>0 and x['execution_cost']>0 for x in fills)
    assert fills[-1]['quantity_after']==0 and len([x for x in case['trades'] if x['leg']=='OPEN'])==1
    assert not case['liquidations']
    changed=deepcopy(w);changed['market']['BTCUSDT']['mark'][20:]*=1.02
    later=run(changed);cut=START+20*MINUTE
    assert case['minute'].filter(pl.col('close_us')<=cut).equals(later['minute'].filter(pl.col('close_us')<=cut))
    assert [x for x in case['trades'] if x['event_us']<cut]==[x for x in later['trades'] if x['event_us']<cut]


def test_membership_reset_requires_original_signal_and_actual_flat():
    frame=pl.DataFrame([dict(symbol=s,available_us=t,target_weight=(-.1 if t<START+2*DAY else .1))
        for t in (START,START+DAY,START+2*DAY,START+3*DAY) for s in SYMBOLS])
    p=ShortCollateralProtection(frame);p.prepare(None,SYMBOLS,START,START+4*DAY)
    positions={s:SimpleNamespace(quantity=D('-1'),isolated_balance=D('100'),entry_price=D('100')) for s in SYMBOLS}
    assert p.observe(START+MINUTE,{s:dict(mark=150.) for s in SYMBOLS},positions)==list(SYMBOLS)
    for s in SYMBOLS:positions[s].quantity=D(0)
    p.on_decision(START+DAY,positions);assert all(p.blocked(s) for s in SYMBOLS)
    positions['BTCUSDT'].quantity=D('-1');p.on_decision(START+2*DAY,positions)
    assert p.blocked('BTCUSDT') and not p.blocked('ETHUSDT')
    positions['BTCUSDT'].quantity=D(0);p.on_decision(START+3*DAY,positions);assert not p.blocked('BTCUSDT')


def test_long_not_stopped_and_liquidation_gap_not_retroactively_rescued():
    frame,_=targets(window()['daily'],np.array([START]),'LONG_SHORT')
    p=ShortCollateralProtection(frame);p.prepare(None,SYMBOLS,START,START+DAY)
    long={s:SimpleNamespace(quantity=D('1'),isolated_balance=D('100'),entry_price=D('100')) for s in SYMBOLS}
    assert p.observe(START+MINUTE,{s:dict(mark=40.) for s in SYMBOLS},long)==[]
    w=window();w['market']['BTCUSDT']['mark'][3:]=210.
    case=run(w)
    assert case['liquidations'] and not case['protection_journal']
    assert case['trades'][1]['liquidation_takeover']
