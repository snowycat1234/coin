import json
from pathlib import Path
import numpy as np
import polars as pl
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as engine,audit_shared_direction as auditor
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as LegacyClosingAccount

START=1_754_006_400_000_000
SYMBOLS=('BTCUSDT','ETHUSDT')

def targets(_bars,decisions,mode):
    return pl.DataFrame([dict(symbol=s,available_us=int(t),target_weight=(-.1 if s=='BTCUSDT' else .1)) for t in decisions for s in SYMBOLS]),dict(role='SYNTHETIC_FROZEN_TARGET_NOT_MODEL_ALPHA')

def observed_window(jump):
    n=3*1440;market={}
    for s in SYMBOLS:
        price=np.full(n,100.)
        if jump and s=='BTCUSDT':price[120:]=250.
        market[s]=dict(open=price,close=price.copy(),mark=price.copy(),quote_volume=np.full(n,10_000_000.))
    daily=pl.DataFrame([dict(symbol=s,close_us=START+i*engine.DAY,close=250. if jump and s=='BTCUSDT' and i else 100.) for i in range(4) for s in SYMBOLS])
    return dict(symbols=SYMBOLS,start=START,end=START+n*engine.MINUTE,daily=daily,market=market,events=[])

def test_full_engine_survives_takeover_reenters_and_independent_wallet_reconciles(tmp_path):
    case=engine.simulate(observed_window(True),'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    summary=case['summary']
    assert summary['completed_minutes']==4320 and summary['terminal_cash_realized'] and summary['liquidation_count']==1
    assert summary['reentry_after_liquidation']['BTCUSDT']==1
    takeover=next(r for r in case['trades'] if r.get('liquidation_takeover'))
    assert takeover['fill_price']==199.84 and takeover['execution_cost']==takeover['fee_amount']==0
    assert not any(r['leg']=='OPEN' and r['symbol']=='BTCUSDT' and takeover['event_us']<r['event_us']<START+engine.DAY for r in case['trades'])
    saved=engine.save_case(case,tmp_path/'account');(tmp_path/'account/summary.json').write_text(json.dumps(saved['summary']))
    proof=auditor.verify(tmp_path/'account',SYMBOLS,1.)
    assert proof['maximum_NAV_error_USDT']<1e-7 and proof['terminal_cash_realized']
    assert 'liquidations.json' in saved['artifacts']

def test_normal_engine_path_matches_legacy_closing_account_without_liquidation():
    old=engine.simulate(observed_window(False),'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=LegacyClosingAccount,persist_cash_close=True)
    new=engine.simulate(observed_window(False),'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    assert old['minute'].equals(new['minute']) and old['trades']==new['trades'] and old['funding']==new['funding']
    assert old['summary']['net_PnL']==new['summary']['net_PnL'] and old['breaches']==new['breaches']
