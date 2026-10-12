import pytest
from driver import native,Closing,SYMBOLS,DAY,checkpoint,restore_snapshot,profile_sha

def test_factory_and_genuine_snapshot_do_not_change_financial_methods(tmp_path):
 daily=native.pl.DataFrame(dict(symbol=list(SYMBOLS),close_us=[0]*5,close=[100.]*5));win=dict(start=0,end=DAY,symbols=SYMBOLS,daily=daily,blocks=lambda:iter(()))
 sim=native.NativeDailySimulator(win,'LONG_SHORT',native.COSTS[0],native.UNITS[0],account_factory=Closing)
 assert sim.account.nav()==10000 and sim.account.closing_min_notional_exempt and profile_sha()=='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf'
 import grid_account
 assert Closing.execute_fill is grid_account.Fine.execute_fill and Closing.apply_funding is grid_account.Fine.apply_funding
 binding={'arm':'SYNTHETIC_FACTORY_NO_HISTORICAL_WALLET'};checkpoint(tmp_path,sim,binding);snapshot,p=restore_snapshot(tmp_path,binding);again=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing)
 assert again.state_hash()==sim.state_hash()==p['state_hash'] and again.account.snapshot()==sim.account.snapshot()
 with pytest.raises(ValueError,match='version'):native.NativeDailySimulator.from_snapshot(snapshot,win)

def test_publication_identity_and_full365_targets_reject_wrong_arm_contract_or_calendar():
 import public_source
 from driver import intents,proto
 from archive import expected,identity
 d,w=intents();assert len(d)==365 and d[-1]+DAY==native.utc('2026-01-01')
 for a in w:
  binding=expected(a);result=dict(window='Y2025',arm=a,calendar=proto()['calendar'],summary=dict(version=Closing.VERSION,contract=dict(quantity_profile_SHA256=profile_sha(),closing_min_notional_exempt=True)));identity(binding,result,a)
  for changed in ({'arm':'wrong'},{'window':'P2'},{'annual_risk_budget':.2},{'account_class':'default'},{'calendar':['2025-01-01','2025-12-31']},{'quantity_profile_SHA256':'wrong'}):
   with pytest.raises(AssertionError):identity(dict(binding,**changed),result,a)

def test_actual_consumed_target_and_risk_must_bind_to_source(tmp_path):
 import json
 from driver import HERE,bind_intents
 index=json.loads((HERE/'input/SOURCE_INDEX.json').read_text())
 for name in ('Y2025.npz','Y2025_RISK.json'):(tmp_path/name).write_bytes((HERE/'input'/name).read_bytes())
 bind_intents(tmp_path,index)
 (tmp_path/'Y2025.npz').write_bytes(b'another same-calendar target')
 with pytest.raises(AssertionError):bind_intents(tmp_path,index)
 fake=json.loads(json.dumps(index));fake['files']['Y2025_RISK.json']['SHA256']='wrong'
 with pytest.raises(AssertionError):bind_intents(tmp_path,fake)
