"""Native flag compatibility, causal paid fills and complete snapshot recovery."""
import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import driver as m
def fixture():
 start=m.native.utc('2023-01-01');n=2880;market={}
 for s in m.SYMBOLS:
  p=np.full(n,100.);volume=np.full(n,1000000.);volume[1439:1447]=0.;volume[1446]=100000.;market[s]=dict(open=p,close=p.copy(),mark=p.copy(),quote_volume=volume)
 daily=m.native.pl.DataFrame([dict(symbol=s,close_us=t,close=100.) for t in (start,start+m.DAY) for s in m.SYMBOLS]);events=[dict(symbol='BTCUSDT',event_us=start+m.DAY+i*m.MINUTE+1000,raw_rate=.001,reported_interval_hours=8.) for i in (7,12)];win=dict(symbols=m.SYMBOLS,start=start,end=start+n*m.MINUTE,daily=daily,market=market,events=events);d=np.array([start,start+m.DAY]);w=np.zeros((2,5));w[0,0]=-.1;return win,d,w
def test_native_paid_late_cash_and_exact_complete_recovery():
 win,d,w=fixture();a=m.make(win,d,w,{},False);b=m.make(win,d,w,{},True)
 for sim in (a,b):
  while sim.cursor<win['end'] and sim.stop is None:sim.advance_day()
 x,y=a.result(),b.result();closes=[r for r in y['trades'] if r['signal_us']==d[1]];assert len(closes)==2 and all(r['leg']=='CLOSE' and r['side']=='BUY' and r['fee_USDT_mid']>0 for r in closes);assert [r['event_us'] for r in closes]==[d[1]+i*m.MINUTE+1 for i in (7,8)];assert y['funding'][1]['quantity']==0 and x['funding'][1]['quantity']<0;assert y['summary']['terminal_cash_realized'];assert np.any(x['minute']['BTCUSDT_quantity'].to_numpy()[1448:2000]!=0) and np.all(y['minute']['BTCUSDT_quantity'].to_numpy()[1448:2000]==0);np.testing.assert_array_equal(y['targets']['target_weight'].to_numpy().reshape(-1,5),w)
 snap=b.snapshot();r=m.native.NativeDailySimulator.from_snapshot(snap,win,account_class=m.Closing);assert r.persist_cash_close and not r.final_day_target_zero and r.state_hash()==b.state_hash() and r.account.snapshot()==b.account.snapshot();z=r.result()
 for k in ('trades','funding','rejections','breaches','extrema','summary','target_meta'):assert z[k]==y[k]
 assert z['minute'].equals(y['minute'])
def test_nonboolean_policy_rejected_and_financial_methods_unchanged():
 win,d,w=fixture()
 with pytest.raises(AssertionError):m.make(win,d,w,{},1)
 from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Original
 assert m.Closing.execute_fill is Original.execute_fill and m.Closing.apply_funding is Original.apply_funding and m.Closing._floor is Original._floor
