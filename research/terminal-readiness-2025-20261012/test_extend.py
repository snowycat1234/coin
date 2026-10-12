import numpy as np
import pytest
from common import START,END,MINUTE,SYMBOLS,account_api
from extend import extend

def fixture():
 Closing,_=account_api();a=Closing();prices=dict(BTCUSDT='10000',ETHUSDT='1000',SOLUSDT='10',XRPUSDT='1',DOGEUSDT='.1')
 a.update_marks(START-3*MINUTE,{s:dict(price=p,close_us=START-3*MINUTE,available_us=START-3*MINUTE) for s,p in prices.items()})
 a.execute_fill('XRPUSDT','BUY','500',START-2*MINUTE+1,START-3*MINUTE,'ORIGINAL_SYNTHETIC_OPEN',execution_mid_price='1',quote_available_us=START-2*MINUTE,available_quantity='500')
 for at in (START-MINUTE,START):a.update_marks(at,{s:dict(price=p,close_us=at,available_us=at) for s,p in prices.items()})
 return a,prices
def tape(prices,quotes):
 return [(START+i*MINUTE,{s:dict(open=float(prices[s]),mark=float(prices[s]),quote_volume=float(quotes[i])) for s in SYMBOLS}) for i in range(60)]
def test_complete_dedup_snapshot_partial_paid_close_and_current_volume_not_used_early():
 a,p=fixture();old=a.snapshot();Closing,_=account_api();a=Closing.from_snapshot(old);assert a.snapshot()==old
 q=[50000,250000]+[250000]*58;r=extend(a,tape(p,q),[],dict.fromkeys(SYMBOLS,9999999),'TERMINAL60_2026JAN1_SYNTHETIC')
 assert r['paid_flat'] and r['minutes']==5 and r['requests'][0]['receipt']['executed_quantity']==0
 assert r['requests'][0]['event_us']==START+MINUTE+1 and r['requests'][1]['receipt']['executed_quantity']==200
 assert [x['quantity'] for x in r['new_trades']]==[200.,200.,100.] and all(x['leg']=='CLOSE' for x in r['new_trades'])
 assert a.fill_requests['ORIGINAL_SYNTHETIC_OPEN']==old['fill_requests']['ORIGINAL_SYNTHETIC_OPEN'] and r['fees_paid_USDT']>0
def test_max60_minutes_never_freeclears_one_lot_and_actual_boundary_funding_uses_past_mark():
 a,p=fixture();events=[dict(symbol='XRPUSDT',event_us=START,raw_rate=.0001),dict(symbol='XRPUSDT',event_us=END,raw_rate=.0002)]
 r=extend(a,tape(p,[50000]*60),events,dict.fromkeys(SYMBOLS,50000),'TERMINAL60_2026JAN1_SYNTHETIC')
 assert r['minutes']==60 and not r['paid_flat'] and len(r['requests'])==59 and a.positions['XRPUSDT'].quantity==500 and not r['new_trades']
 assert r['fees_paid_USDT']==0 and r['actual_funding_events_applied']==2 and r['funding_cash_USDT']==pytest.approx(-.15)
 assert r['new_funding'][0]['mark_close_us']==START-MINUTE and r['new_funding'][1]['mark_close_us']==END-MINUTE
def test_original_profile_methods_invalid_values_and_default_snapshot_rejected():
 a,p=fixture();from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Fine
 assert type(a).execute_fill is Fine.execute_fill and type(a).apply_funding is Fine.apply_funding
 with pytest.raises(ValueError,match='version'):Fine.from_snapshot(a.snapshot())
 rows=tape(p,[250000]*60);rows[0][1]['XRPUSDT']['mark']=np.nan
 with pytest.raises(AssertionError,match='Actual complete'):extend(a,rows,[],dict.fromkeys(SYMBOLS,250000),'TERMINAL60_2026JAN1_SYNTHETIC')

def test_actual_8ms_funding_preserves_eventtime_and_available_midnight_mark():
 a,p=fixture();r=extend(a,tape(p,[50000]*60),[dict(symbol='XRPUSDT',event_us=START+8000,raw_rate=.0001)],dict.fromkeys(SYMBOLS,50000),'TERMINAL60_2026JAN1_SYNTHETIC')
 assert r['new_funding'][0]['event_us']==START+8000 and r['new_funding'][0]['mark_close_us']==START and r['funding_cash_USDT']==pytest.approx(-.05)

def test_owed_funding_halt_keeps_debt_and_inventory_no_exit_or_freewriteoff():
 a,p=fixture();r=extend(a,tape(p,[9999999]*60),[dict(symbol='XRPUSDT',event_us=START,raw_rate=100)],dict.fromkeys(SYMBOLS,9999999),'TERMINAL60_2026JAN1_SYNTHETIC')
 assert r['status']=='STOP_ACCOUNT_HALT' and not r['paid_flat'] and not r['requests'] and a.positions['XRPUSDT'].quantity==500 and a.unpaid_liability>0

def test_public_restore_module_imports_without_running_accounts():
 import archive
 assert callable(archive.pack) and callable(archive.restore)
