"""Read-only full-calendar conditional comparisons; no accounts or financial advances."""
import argparse,json
from pathlib import Path
import numpy as np
from driver import HERE,ROOT,native,b,sha,save,proto,SYMBOLS,DAY,MINUTE,targets,load,window,Closing,restore_snapshot
CONTROLS={'Y2023':('2c551f8606ac0b9328c52115c761836099517439','research/portfolio-risk-budget-20261012/summary/P2'),'Y2025':('af6d8e1426c663f3d5afb2da311755487681c232','research/portfolio-risk-2025-native-20261012/summary')}
def compare(state):
 assert not state.exists();out={}
 for key,(commit,prefix) in CONTROLS.items():
  new=json.loads((HERE/'summary'/key/'RESULT.json').read_text());binding=json.loads((HERE/'summary'/key/'BINDING.json').read_text());s=new['summary'];rows={}
  for arm in ('CS_MATCHED','STATIC50'):
   base=ROOT/prefix/arm;data={}
   for name in ('RESULT.json','BINDING.json'):
    raw=(base/name).read_bytes();assert raw==b.git('show',commit+':'+str((base/name).relative_to(ROOT)));data[name]=json.loads(raw)
   old=data['RESULT.json'];ob=data['BINDING.json'];os=old['summary'];kernel={}
   for name in ('scripts/investment/resumable_perpetual.py','scripts/investment/perpetual_closing_exempt_account.py','research/quantity-grid-sensitivity-20261012/grid_account.py'):
    kernel[name]=(ROOT/name).read_bytes()==b.git('show',ob['science_source_commit']+':'+name)
   checks=dict(same_calendar=old['calendar']==new['calendar'],same_full_minutes=s['completed_minutes']==os['completed_minutes']==525600,same_source_index=binding['source_index_SHA256']==ob['source_index_SHA256'],same_account_class=binding['account_class']==ob['account_class']==s['version']==os['version'],same_coarse_profile=binding['quantity_profile_SHA256']==ob['quantity_profile_SHA256'],same_contract_metadata=s['contract']==os['contract'],same_cost_scenario=s['cost_scenario']==os['cost_scenario'],same_unit_assumption=s['funding_rate_unit']==os['funding_rate_unit'],same_total_source_funding_events=s['funding_original_events']==os['funding_original_events']==5475,kernel_code_bytes_equal=all(kernel.values()))
   compatible=all(checks.values());paid=compatible and s['terminal_cash_realized'] and os['terminal_cash_realized'];metrics=old['metrics'];vol=next((metrics[f] for f in ('annual_daily_vol','actual_daily_annual_vol','realized_annual_daily_vol') if f in metrics),None)
   rows[arm]=dict(status='SAME_FULL_CALENDAR_CONDITIONAL_CONTRACT_DESCRIPTIVE' if compatible else 'NOT_COMPARABLE_CONTRACT_OR_CALENDAR',checks=checks,kernel_code=kernel,control_commit=commit,control_RESULT_SHA256=sha(base/'RESULT.json'),control_BINDING_SHA256=sha(base/'BINDING.json'),control_marked_net_USDT=os['net_PnL'],control_paid_flat=os['terminal_cash_realized'],control_annual_daily_vol=vol,control_DD=os['all_observation_max_drawdown'],paid_cash_net_difference_USDT=s['net_PnL']-os['net_PnL'] if paid else None,marked_net_difference_USDT=s['net_PnL']-os['net_PnL'] if compatible else None,risk='DIFFERENT_TARGETS_ACTIVITY_GROSS_FORECAST_AND_REALIZED_RISK_NOT_EQUAL_RISK_ALPHA',control_replayed=False)
  out[key]=dict(FOLLOW_marked_net_USDT=s['net_PnL'],FOLLOW_paid_flat=s['terminal_cash_realized'],comparisons=rows)
 save(state,dict(status='READONLY_CONDITIONAL_COMPARISON_COMPLETE',years=out,old_financial_replays=0,new_fits=0,new_wallets=0,provider_downloads=0,annual_or_tail_stitching=False,posthoc_selected_candidate=True,selection_adjusted_or_new_OOS_inference=False));print('ACTUAL_FOLLOW_READONLY_COMPARISON',[(k,{a:r['status'] for a,r in v['comparisons'].items()}) for k,v in out.items()],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);a=p.parse_args();compare(a.destination)
