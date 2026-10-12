import json
from pathlib import Path
here=Path('/workspace/coin-tail-risk/research/quantity-grid-sensitivity-20261012')
for key in ('P1','P2'):
 rows={}
 for arm in ('CS_MATCHED','VOL_MATCHED','STATIC50'):
  r=json.loads((here/'summary'/key/arm/'RESULT.json').read_text());s=r['summary'];f=r['fine_step_comparison'];paid=s['terminal_cash_realized'];ci=r['bootstrap_actual_daily_cash95CI']
  rows[arm]=dict(marked_net_USDT=s['net_PnL'],paid_flat=paid,terminal_marked_notional=s['terminal_marked_notional'],positions=s['positions'],fine_net_USDT=f['old_net_USDT'],marked_NAV_difference_USDT=f['net_increment_USDT'],paid_net_difference_USDT=f['net_increment_USDT'] if paid else None,difference_scope='SAME_FULL_CALENDAR_MARKED_VALUE_ONLY_RESIDUAL_RETAINED' if not paid else 'BOTH_PAID_FLAT_CHANGED_REALIZED_RISK',annual_daily_vol=r['metrics']['actual_daily_annual_vol'],DD=s['all_observation_max_drawdown'],original_marked_path_CI=ci,paid_cash_CI=ci if paid else None,CI_scope='MARKED_PATH_NOT_PAID_CASH_WHEN_TERMINAL_NOT_FLAT',status=r['status'])
 (here/'summary'/key/'RESULT_REVIEWED.json').write_text(json.dumps(dict(window=key,arms=rows,scope='REPORTING_ONLY_NO_ACCOUNT_ADVANCE_OR_ORIGINAL_RESULT_OVERWRITE',new_wallets=0,account_advances=0),sort_keys=True,indent=2)+'\n')
print('REVIEWED_MARKED_VS_PAID_AND_CI_SCOPES_ORIGINAL_RESULTS_PRESERVED')
