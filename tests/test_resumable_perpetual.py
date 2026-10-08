"""Native scheduler equivalence, recovery, boundary liquidity and fork isolation."""
import json
import numpy as np
import polars as pl
import pytest
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as old
from scripts.investment.resumable_perpetual import NativeDailySimulator

START=1_704_067_200_000_000
CORE5=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def synthetic(days=3, *, liquidation=False, dry=False):
    n=days*1440
    t=START+np.arange(n,dtype=np.int64)*old.MINUTE
    market={}
    for i,s in enumerate(CORE5):
        prices=np.full(n,100.+i)
        if s==CORE5[0]:
            prices[1438:]=103.
            if liquidation:prices[1450:]=220.
        quote=np.full(n,20_000_000.)
        if dry:quote[1438:]=0.
        market[s]=dict(open=prices.copy(),close=prices.copy(),mark=prices.copy(),quote_volume=quote)
    bars=pl.DataFrame([dict(symbol=s,close_us=int(d),close=100.+i)
        for d in range(START,START+days*old.DAY,old.DAY) for i,s in enumerate(CORE5)])
    events=[dict(symbol=s,event_us=START+d*old.DAY+offset,raw_rate=.001,
                 reported_interval_hours=8.) for d in range(days) for offset in (0,1000,8*60*old.MINUTE)
            for s in CORE5]
    return dict(symbols=CORE5,start=START,end=START+n*old.MINUTE,times=t,
                market=market,daily=bars,events=events,input_proofs=[])


def factory(mode='LONG_SHORT', cash_day=None):
    def make(_bars,dates,_mode):
        rows=[]
        for i,d in enumerate(dates):
            for j,s in enumerate(CORE5):
                w=(.3 if mode=='LONG_ONLY' else -.3) if j==0 else (.15 if j==1 else 0.)
                if cash_day is not None and i>=cash_day:w=0.
                rows.append(dict(available_us=int(d),symbol=s,target_weight=w))
        return pl.DataFrame(rows),dict(source='SYNTHETIC_EQUIVALENCE_ONLY')
    return make


@pytest.mark.parametrize('liquidation,dry,cash_day',[(False,False,None),(True,False,None),(False,True,1)])
def test_fixed_whole_window_equals_daily_and_recovered(liquidation,dry,cash_day,tmp_path):
    window=synthetic(liquidation=liquidation,dry=dry)
    targets=factory(cash_day=cash_day)
    kwargs=dict(target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    full=old.simulate(window,'LONG_SHORT',old.COSTS[0],old.UNITS[0],**kwargs)
    daily=NativeDailySimulator(window,'LONG_SHORT',old.COSTS[0],old.UNITS[0],**kwargs)
    daily.advance_day()
    assert daily.account.positions[CORE5[0]].quantity!=0  # No midnight terminal close.
    snapshot=json.loads(json.dumps(daily.snapshot(),allow_nan=False))
    restored=NativeDailySimulator.from_snapshot(snapshot,window,account_class=BybitIsolatedAccount)
    assert restored.state_hash()==daily.state_hash()
    while daily.cursor<daily.end and daily.stop is None:
        daily.advance_day()
        restored.advance_day()
    for case in (daily.result(),restored.result()):
        assert full['minute'].equals(case['minute'])
        for key in ('summary','trades','funding','rejections','breaches','extrema','liquidations'):
            assert full[key]==case[key],key
    evidence=dict(scope='SYNTHETIC_THREE_DAY_CORE5_NOT_MARKET_EXPERIMENT',
                  completed_minutes=daily.rows_written,liquidations=len(daily.account.liquidations),
                  NAV=str(daily.account.nav()),funding_events=daily.event_cursor,
                  exact_journals_and_minute_values=True)
    (tmp_path/'equivalence.json').write_text(json.dumps(evidence))


def test_fork_does_not_revalidate_history_or_share_mutable_state(monkeypatch):
    window=synthetic()
    sim=NativeDailySimulator(window,'LONG_SHORT',old.COSTS[0],old.UNITS[0],
                            target_factory=factory(),account_factory=BybitIsolatedAccount)
    sim.advance_day()
    before=sim.snapshot()
    monkeypatch.setattr(BybitIsolatedAccount,'from_snapshot',classmethod(lambda *a,**k:pytest.fail('history replay')))
    a,b=sim.fork(),sim.fork()
    assert a.tape is b.tape is sim.tape
    assert a.minute_chunks[0] is sim.minute_chunks[0]
    assert not a.minute_chunks[0].flags.writeable
    a.account.trades[0]['side']='CHANGED_ONLY_IN_A'
    a.pending.clear()
    a.advance_day(dict.fromkeys(CORE5,0.))
    assert sim.snapshot()==before
    assert b.account.trades[0]['side']==before['account']['trades'][0]['side']
    assert b.cursor==START+old.DAY
    assert a.account.liquidation_callback.__self__ is a
    assert b.account.liquidation_callback.__self__ is b
    with pytest.raises(TypeError):sim.tape.cache[0][1][CORE5[0]]['open']=0


def test_streamed_market_loaded_once_for_all_branches():
    window=synthetic()
    original=window.pop('market')
    consumed=[]
    def blocks():
        for d in range(3):
            consumed.append(d)
            sl=slice(d*1440,(d+1)*1440)
            yield dict(times=window['times'][sl],market={s:{k:v[sl] for k,v in data.items()}
                       for s,data in original.items()})
    window['minute_blocks']=blocks
    sim=NativeDailySimulator(window,'LONG_SHORT',old.COSTS[0],old.UNITS[0],
                            target_factory=factory(),account_factory=BybitIsolatedAccount)
    a,b=sim.fork(),sim.fork()
    a.advance_day();b.advance_day();sim.advance_day()
    assert consumed==[0]
    assert a.result()['minute'].equals(b.result()['minute'])


def test_capacity_and_pending_order_continue_across_midnight():
    window=synthetic(days=3)
    # A low-capacity CASH close persists all day and across the next midnight.
    window['market'][CORE5[0]]['mark'][:]=100.
    window['market'][CORE5[0]]['open'][:]=100.
    window['market'][CORE5[0]]['close'][:]=100.
    for data in window['market'].values():data['quote_volume'][1439:]=100.
    targets=factory(cash_day=1)
    kwargs=dict(target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    sim=NativeDailySimulator(window,'LONG_SHORT',old.COSTS[0],old.UNITS[0],**kwargs)
    sim.advance_day();sim.advance_day()
    assert sim.pending and any(o['attempts']>5 for o in sim.pending.values())
    assert sim.previous_quote[CORE5[0]]==100.
    sim.advance_day()
    full=old.simulate(window,'LONG_SHORT',old.COSTS[0],old.UNITS[0],**kwargs)
    assert sim.result()['minute'].equals(full['minute'])
    assert sim.account.trades==full['trades']
