"""Synthetic account identity checks, with no economic advance or source reads."""
import numpy as np
import pytest
import importlib.util
from driver import native,Closing,SYMBOLS,DAY,targets

def test_exact_reused_targets_and_static_half():
    for key,days in (('P1',456),('P2',365)):
        d,w=targets(key);assert len(d)==days
        np.testing.assert_array_equal(w['STATIC50'],.5*w['CS_MATCHED']+.5*w['VOL_MATCHED'])

def test_native_factory_and_snapshot_contract_cannot_mix():
    daily=native.pl.DataFrame(dict(symbol=list(SYMBOLS),close_us=[0]*5,close=[100.]*5))
    win=dict(start=0,end=DAY,symbols=SYMBOLS,daily=daily,blocks=lambda:iter(()))
    sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],account_factory=Closing)
    assert type(sim.account) is Closing and sim.account.closing_min_notional_exempt
    snap=sim.snapshot();again=native.NativeDailySimulator.from_snapshot(snap,win,account_class=Closing)
    assert again.state_hash()==sim.state_hash() and again.account.snapshot()==snap['account']
    with pytest.raises(ValueError,match='version'):
        native.NativeDailySimulator.from_snapshot(snap,win)
    default=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0])
    assert not default.account.closing_min_notional_exempt
    with pytest.raises(ValueError,match='version'):
        native.NativeDailySimulator.from_snapshot(default.snapshot(),win,account_class=Closing)

def test_publication_rejects_wrong_arm_window_and_contract():
    from driver import HERE
    spec=importlib.util.spec_from_file_location('unified_publication',HERE/'archive.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    binding=dict(window='P1',arm='CS_MATCHED',account_class=Closing.VERSION,contract_from_initial_capital=True)
    result=dict(window='P1',arm='CS_MATCHED');m.identity(binding,result,'P1','CS_MATCHED')
    for key,arm in [('P2','CS_MATCHED'),('P1','VOL_MATCHED')]:
        with pytest.raises(AssertionError):m.identity(binding,result,key,arm)
    for field,value in [('account_class','default'),('contract_from_initial_capital',False)]:
        with pytest.raises(AssertionError):m.identity(dict(binding,**{field:value}),result,'P1','CS_MATCHED')
