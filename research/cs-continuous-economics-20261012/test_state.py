import sys
from pathlib import Path
import numpy as np
import polars as pl
sys.path.insert(0,str(Path(__file__).resolve().parent))
from state_io import split_snapshot,checkpoint,restore_snapshot
from core import DAY,SYMBOLS
from scripts.investment.resumable_perpetual import NativeDailySimulator
from scripts.investment.perpetual_directional import COSTS,UNITS

def test_funding_body_tamper_and_wrong_calendar_stop_before_wallet(tmp_path):
    import hashlib,json,pytest
    from native_pair import window,native
    # Synthetic negative metadata fixture only; no genuine source certificate.
    (tmp_path/'EVENTS.json').write_text('[]');(tmp_path/'DAILY.json').write_text('[]')
    index=dict(fixture='SYNTHETIC_NEGATIVE_BINDING',status='PASS_EXACT_FIXED456DAY_CONTINUOUS_SOURCE',symbol_order=list(SYMBOLS),calendar=[native.utc('2021-04-01'),native.utc('2022-07-01')],days=456,files={n:dict(SHA256=hashlib.sha256((tmp_path/n).read_bytes()).hexdigest(),bytes=2) for n in ('EVENTS.json','DAILY.json')})
    (tmp_path/'SOURCE_INDEX.json').write_text(json.dumps(index));(tmp_path/'EVENTS.json').write_text('[{"raw_rate":0}]')
    with pytest.raises(AssertionError):window(tmp_path)
    index['calendar'][0]+=DAY;(tmp_path/'SOURCE_INDEX.json').write_text(json.dumps(index))
    with pytest.raises(AssertionError):window(tmp_path)

def test_real_default_kernel_split_snapshot_restores_all_scheduler_account_and_minutes(tmp_path):
    window=dict(start=0,end=DAY,symbols=SYMBOLS,daily=pl.DataFrame([dict(symbol=s,close_us=0,close=100.) for s in SYMBOLS]),events=[],market={s:dict(open=np.full(1440,100.),close=np.full(1440,100.),quote_volume=np.full(1440,1000000.),mark=np.full(1440,100.)) for s in SYMBOLS})
    def factory(daily,clocks,mode):return pl.DataFrame([dict(available_us=0,symbol=s,target_weight=.02) for s in SYMBOLS]),dict(authority='SYNTHETIC')
    sim=NativeDailySimulator(window,'LONG_SHORT',COSTS[0],UNITS[0],target_factory=factory);sim.advance_day();old_chunks=sim.minute_chunks
    snap=split_snapshot(sim);assert snap['minute_chunks']==[] and sim.minute_chunks is old_chunks and len(old_chunks)==1
    checkpoint(tmp_path/'recovery',sim,'SYNTHETIC_BINDING');snap,p=restore_snapshot(tmp_path/'recovery','SYNTHETIC_BINDING');restored=NativeDailySimulator.from_snapshot(snap,window)
    assert restored.account.snapshot()==sim.account.snapshot() and restored.state_hash()==sim.state_hash()==p['state_hash']
    np.testing.assert_array_equal(restored.minute_chunks[0],sim.minute_chunks[0])
    assert restored.result()['minute'].equals(sim.result()['minute']) and restored.result()['summary']['terminal_cash_realized']
