"""Counterexample for simultaneous published Mark liquidation and settlement.

The d8 replay kernel is frozen while its jobs run. This test records the old
auditor's missing exchange-event priority separately from correct wallet cash.
"""
import json
import pytest
from .test_liquidation_engine import observed_window,targets,START,SYMBOLS
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as engine,audit_shared_direction as auditor
from .isolated_audit import verify as isolated_verify

def test_mark_takeover_at_same_clock_as_settlement_exposes_legacy_audit_order(tmp_path):
    window=observed_window(False)
    window['market']['BTCUSDT']['open'][479:]=250.
    window['market']['BTCUSDT']['close'][479:]=250.
    window['market']['BTCUSDT']['mark'][479:]=250.
    event=START+480*engine.MINUTE
    window['events']=[dict(symbol=s,event_us=event,raw_rate=.01,reported_interval_hours=8) for s in SYMBOLS]
    case=engine.simulate(window,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    takeover=case['liquidations'][0]
    assert takeover['event_us']==event and takeover['phase']=='MARK_OBSERVATION'
    funding=next(r for r in case['funding'] if r['symbol']=='BTCUSDT')
    assert funding['quantity']==0 and funding['signed_funding_USDT']==0
    saved=engine.save_case(case,tmp_path/'account');(tmp_path/'account/summary.json').write_text(json.dumps(saved['summary']))
    with pytest.raises(ValueError,match='Funding ownership'):auditor.verify(tmp_path/'account',SYMBOLS,1.)
    proof=isolated_verify(tmp_path/'account',SYMBOLS,1.)
    assert proof['maximum_NAV_error_USDT']<1e-7 and proof['mark_phase_priority_trade_count']==1
    assert proof['terminal_cash_realized']
    witnesses=tmp_path/'account/liquidations.json';value=json.loads(witnesses.read_text());value[0]['bankruptcy_price']='1'
    witnesses.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='Bankruptcy'):isolated_verify(tmp_path/'account',SYMBOLS,1.)

def test_isolated_adapter_keeps_default_normal_cash_audit_exactly_equal(tmp_path):
    case=engine.simulate(observed_window(False),'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    directory=tmp_path/'account';saved=engine.save_case(case,directory);(directory/'summary.json').write_text(json.dumps(saved['summary']))
    old=auditor.verify(directory,SYMBOLS,1.);new=isolated_verify(directory,SYMBOLS,1.)
    assert all(new[k]==v for k,v in old.items()) and new['mark_phase_priority_trade_count']==0
