"""Only the new feature/cadence/frozen-sizing adapter; old finance not retested."""
from types import SimpleNamespace
import json
import numpy as np
import polars as pl
import pytest
from scripts.investment import perpetual_public_benchmark as bench


def test_public_perpetual_two_hour_entry_sizing_and_complete_features(tmp_path):
    start=1_754_006_400_000_000;minute=60_000_000;bar=bench.BAR
    n=250;times=start+np.arange(n,dtype=np.int64)*minute
    decisions_seen=[];risk_marker=pl.DataFrame([dict(symbol=s,close_us=start,close=500.) for s in bench.reuse.SYMBOLS])
    signals=pl.DataFrame([dict(symbol=s,close_us=start+i*bar,close=100.+10*i)
        for s in bench.reuse.SYMBOLS for i in range(3)])
    def fixed(signal,decisions,mode,*,risk_daily_bars):
        assert signal.equals(signals) and risk_daily_bars.equals(risk_marker) and mode=='LONG_ONLY'
        decisions_seen.extend(map(int,decisions))
        return pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=.1 if s=='BTCUSDT' and t!=start+bar else 0.)
            for t in decisions for s in bench.reuse.SYMBOLS]),dict(scope='SYNTHETIC_NEW_SIGNAL_WIRING_ONLY')
    receipt=[];simulate=bench.adapted_simulate(receipt,SimpleNamespace(fixed_targets=fixed))
    markets={s:dict(open=np.full(n,100.),close=np.full(n,100.),mark=np.full(n,100.),quote_volume=np.full(n,2_000_000.))
        for s in bench.reuse.SYMBOLS}
    case=simulate(dict(start=start,end=start+n*minute,times=times,market=markets,daily=risk_marker,
        signal_bars=signals,events=[],input_proofs=[]),'LONG_ONLY',bench.reuse.COSTS[0],bench.reuse.UNITS[0])
    assert decisions_seen==[start,start+bar,start+2*bar]
    trades=case['trades'];assert trades[0]['side']=='BUY' and trades[0]['quantity']==9.9
    assert trades[0]['event_us']==start+minute+1 and trades[0]['signal_us']==start
    assert any(t['side']=='SELL' and t['signal_us']==start+bar for t in trades)
    reopening=next(t for t in trades if t['side']=='BUY' and t['signal_us']==start+2*bar)
    expected=(case['minute'].filter(pl.col('close_us')==start+2*bar)['nav'][0]*.1*.99/120.)
    assert abs(reopening['quantity']-expected)<1e-8 # signal close120, not daily500 or executable100
    assert case['summary']['terminal_cash_realized'] and case['summary']['completed_minutes']==n
    assert len(receipt)==1 and [c['matches'] for c in receipt[0]['changes']]==[1,1,1,1]
    # Full120 source minutes per bar; removal must fail, never silently drop dates.
    rows=[dict(symbol=s,open_us=start+i*minute,close_us=start+(i+1)*minute,available_us=start+(i+1)*minute,
        open=100.+i*.01,close=100.+i*.01,high=102.+i*.01,low=98.+i*.01,volume=float(i+1))
        for s in bench.reuse.SYMBOLS for i in range(240)]
    source=pl.DataFrame(rows);hours=bench.closed_two_hours(source)
    assert hours.height==4 and hours.filter(pl.col('symbol')=='BTCUSDT')['open'].to_list()==[100.,101.2]
    assert hours.filter(pl.col('symbol')=='BTCUSDT')['volume'][0]==sum(range(1,121))
    with pytest.raises(ValueError,match='Complete full2h'):
        bench.closed_two_hours(source.filter(~((pl.col('symbol')=='BTCUSDT')&(pl.col('open_us')==start+minute))))
    (tmp_path/'public_perpetual_controller_evidence.json').write_text(json.dumps(dict(scope='SYNTHETIC_NEW_ADAPTER_ONLY',
        derivation=receipt,trades=trades,decisions=decisions_seen,features=hours.to_dicts()),indent=2)+'\n')
