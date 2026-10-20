"""Generated-only cost/account checks; no historical data or missing-run recovery."""
import sys,os,json,hashlib,importlib.util
from pathlib import Path
from decimal import Decimal as D,localcontext
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
os.environ['QUANT_ROOT']=str(ROOT)
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from quant.perpetual_account import PerpetualConfig
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Account

def need(x,msg):
 if not x:raise RuntimeError(msg)
def mark(a,t,p):a.update_marks(t,{'BTCUSDT':dict(price=p,close_us=t,available_us=t)})
def checkpins():
 pins=json.loads((ROOT/'SOURCE_PINS.json').read_text())
 for name,pin in pins['files'].items():
  b=(ROOT/name).read_bytes();need(len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'],'SOURCE_CHANGED:'+name)
 return pins
pins=checkpins()
cases=[]
with localcontext() as ctx:
 ctx.prec=40
 for direction in (D(1),D(-1)):
  for price in (D(100),D(137)):
   for quantity in (D(1),D(3),D(10)):
    for bps in (D(4),D(8),D(16)):
     for rate in (D('-.001'),D(0),D('.001')):
      a=Account(PerpetualConfig(half_spread_bps=bps,slippage_bps=bps),symbols=('BTCUSDT',))
      mark(a,0,price)
      opening=dict(symbol='BTCUSDT',side='BUY' if direction>0 else 'SELL',quantity=quantity,event_us=60000001,signal_us=0,fill_id='open',execution_mid_price=price,quote_available_us=0)
      receipt=a.execute_fill(**opening);need(receipt['status']=='FILLED','OPEN_NOT_FILLED')
      snap=a.snapshot();r=Account.from_snapshot(snap);need(r.snapshot()==snap,'RESTORE_STATE_CHANGED')
      need(r.execute_fill(**opening)==receipt and r.snapshot()==snap,'RESTORED_FILL_NOT_IDEMPOTENT')
      for account in (a,r):
       account.apply_funding('BTCUSDT','funding',120000000,rate,0)
       fs=account.snapshot();account.apply_funding('BTCUSDT','funding',120000000,rate,0);need(account.snapshot()==fs,'FUNDING_NOT_IDEMPOTENT')
       mark(account,180000000,price)
       account.execute_fill('BTCUSDT','SELL' if direction>0 else 'BUY',quantity,240000001,180000000,'close',execution_mid_price=price,quote_available_us=180000000,reduce_only=True)
      need(a.snapshot()==r.snapshot(),'RESTORED_PATH_DIFFERS')
      fees=2*quantity*price*D('.00055');execution=2*quantity*price*(bps+bps)/10000;funding=-direction*quantity*price*rate
      need(a.fees==fees and a.execution_cost==execution and a.funding_cash==funding,'HAND_COST_IDENTITY_FAILED')
      need(a.positions['BTCUSDT'].quantity==0 and a.nav()==D(10000)-fees-execution+funding,'NET_CASH_IDENTITY_FAILED')
      cases.append(dict(direction=str(direction),mid=str(price),quantity=str(quantity),spread_bps=str(bps),slip_bps=str(bps),rate=str(rate),fee=str(fees),execution=str(execution),funding=str(funding),terminal=str(a.nav())))
checkpins()
result=dict(status='PASS',historical_replays=0,lost_checkpoint_reconstructed=False,source_commit=pins['commit'],original_existing_test_count=0,new_generated_grid_cases=len(cases),assertions_active_under_optimized=True,scope='Generated accounting only; no historical profit or lost-run recovery claim.',cases=cases)
out=ROOT/('RESULT_OPTIMIZED.json' if sys.flags.optimize else 'RESULT.json')
with out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
