"""Four frozen full-calendar references; no financial engine or model fitting."""
import argparse,json,time,subprocess
from pathlib import Path
import numpy as np
from core import DAY,EXEC,SYMBOLS,reference,paired_ci
from prepare import sha,save,HERE,ROOT
def run(state,prepared,source_commit):
 assert not state.exists() and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==source_commit
 state.mkdir(parents=True);start=time.monotonic();prep=json.loads((prepared/'PREPARATION.json').read_text());assert prep['protocol_SHA256']==sha((HERE/'PROTOCOL.json').read_bytes());reports={}
 for year,seed in [(2023,811742),(2025,811743)]:
  proof=prep['years'][str(year)];path=prepared/f'Y{year}.npz';assert sha(path.read_bytes())==proof['INPUTS_SHA256'];arms={};rows={}
  with np.load(path,allow_pickle=False) as z:
   d=z['decision_us'];assert tuple(z['symbol_order'])==SYMBOLS and len(d)==365 and np.all(np.diff(d)==DAY)
   for arm in ('SHORT','CARRY'):
    arms[arm],rows[arm]=reference(d,z[arm],z['p0'],z['p1'],z['funding_per_unit'],z['owned_interval_valid']);save(state/f'Y{year}_{arm}.json',dict(summary=arms[arm],rows=rows[arm],symbol_order=SYMBOLS,source_commit=source_commit));print('ACTUAL_FINANCING_REFERENCE',year,arm,arms[arm]['status'],arms[arm]['days'],arms[arm]['net_USDT'],flush=True)
  full=all(arms[a]['hypothetical_cost_terminal'] and arms[a]['days']==365 for a in arms);increment=None;ci=None
  if full:
   increment=arms['CARRY']['net_USDT']-arms['SHORT']['net_USDT'];delta=np.array([r['daily_return'] for r in rows['CARRY']])-np.array([r['daily_return'] for r in rows['SHORT']]);ci=paired_ci(delta,seed)
  a=arms['CARRY'];gates=dict(full_pair=full,candidate_net_positive=bool(full and a['net_USDT']>0),increment_positive=bool(increment is not None and increment>0),paired95CI_lower_positive=bool(ci is not None and ci[0]>0),risk=bool(full and a['annual_vol']<=.12 and a['drawdown']<=.12 and a['worst30']>=-.10))
  exante={arm:dict(cap_bound_days=sum(r['arms'][arm]['cap_bound'] for r in proof['risk']),mean_post_sigma=float(np.mean([r['arms'][arm]['post_sigma'] for r in proof['risk']])),mean_shortfall=float(np.mean([r['arms'][arm]['shortfall'] for r in proof['risk']])),maximum_shortfall=max(r['arms'][arm]['shortfall'] for r in proof['risk'])) for arm in arms}
  reports[str(year)]=dict(arms=arms,gates=gates,increment_USDT=increment,paired_daily_increment95CI=ci,changed_target_days=proof['changed_target_days'],long_asset_days=proof['long_asset_days'],cash_asset_days=proof['cash_asset_days'],funding_unknown_asset_days=proof['funding_input_unknown_asset_days'],exante=exante,bootstrap_seed=seed);print('ACTUAL_FINANCING_GATE',year,gates,increment,ci,flush=True)
 out=dict(status='PASS_TWO_YEAR_FINANCING_DIRECTION_SCREEN_NATIVE_READINESS_NOT_GRANTED' if all(all(r['gates'].values()) for r in reports.values()) else 'STOP_FIXED_PERP_FINANCING_DIRECTION_SCREEN',years=reports,source_commit=source_commit,PREPARATION_SHA256=sha((prepared/'PREPARATION.json').read_bytes()),protocol_SHA256=prep['protocol_SHA256'],scientific_recipes=1,new_conditional_daily_references=4,new_native_wallets=0,old_financial_replays=0,new_fits=0,provider_GETs=0,authority='ACTUAL_HISTORICAL_PRICE_AND_FUNDING_CONDITIONAL_DAILY_QUANTITY_REFERENCE_NOT_NATIVE_NET_INCOME',label_maturity='decision+2UTCdays after actual owned_end decision+1day+60s+1us',risk_comparison='SAME_POLICY_DIFFERENT_REALIZED_RISK',years_role='SEEN_HISTORY_DEVELOPMENT_VALIDATION_NOT_UNSEEN',seconds=time.monotonic()-start);save(state/'RESULT.json',out);assert time.monotonic()-start<60;print('ACTUAL_FINANCING_TWO_YEAR_STOP',out['status'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.prepared,a.source_commit)
