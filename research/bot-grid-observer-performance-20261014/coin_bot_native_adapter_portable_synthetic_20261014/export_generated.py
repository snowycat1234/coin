"""Serial from-start generated controls and full native/owner journal export."""
from pathlib import Path
from decimal import Decimal
import json,numpy as np
from generated_fixtures import new_sim,finish,NAMES
HERE=Path(__file__).resolve().parent

def safe(value):
 if isinstance(value,Decimal):return str(value)
 if isinstance(value,np.generic):return value.item()
 if isinstance(value,np.ndarray):return value.tolist()
 if isinstance(value,dict):return {str(k):safe(v) for k,v in value.items()}
 if isinstance(value,(tuple,list,set)):return [safe(v) for v in value]
 return value

def export():
 out=HERE/'generated_journals';out.mkdir(exist_ok=True);summary=[]
 for name in NAMES:
  for arm in ('CONTROL','CASH','GRID'):
   sim=finish(new_sim(arm,name));minute=np.concatenate(sim.minute_chunks)
   account=sim.account.snapshot()
   # Native final state and ALL real fills/funding plus exact owner allocations;
   # ownership journals observe native debits, they never fund another wallet.
   journal=dict(fixture=name,arm=arm,evidence_origin='GENERATED_ONLY_NO_MARKET_PERFORMANCE',
     account_final=account,native_trades=sim.account.trades,native_funding=sim.account.funding,
     scheduler_funding=sim.funding_journal,rejections=sim.rejections,breaches=sim.breaches,
     ownership_allocations=sim.allocations,funding_allocations=sim.funding_allocations,
     policy_events=sim.policy_events,original_target_rows=sim.target_rows,
     adapter_state_final=sim.snapshot()['adapter_state'])
   file=out/f'{name}_{arm}.json';file.write_text(json.dumps(safe(journal),indent=2,allow_nan=False)+'\n')
   summary.append(dict(fixture=name,arm=arm,final_NAV=str(sim.account.nav()),
    native_fee=str(sim.account.fees),native_friction=str(sim.account.execution_cost),
    funding_cash=str(sim.account.funding_cash),minute_mdd=sim.mdd,max_gross=sim.max_gross,
    max_asset=max(sim.max_asset.values()),mean_close_gross=float(minute[:,-2].mean()),
    max_close_abs_net=float(np.abs(minute[:,-1]).max()),completed_minutes=sim.rows_written,
    terminal_paid_flat=sim.result()['summary']['terminal_cash_realized'],
    grid_owned_fill_legs=sum(a['owner']=='GRID' for a in sim.allocations),
    journal=str(file.relative_to(HERE))))
 result=dict(status='NOT_CERTIFIED_GENERATED_ONLY',runs=summary,
  interpretation='Fixed toy fixtures validate mechanics only. No historical/AI performance or risk-parity inference.',
  historical_GO=False,restore_supported=False)
 (HERE/'GENERATED_SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print('Exported',len(summary),'serial generated arms with complete native/ownership journals.')

if __name__=='__main__':export()
