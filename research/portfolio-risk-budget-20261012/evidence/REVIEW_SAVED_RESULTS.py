"""Read genuine saved data; no simulator/account construction or financial advances."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012'
prep=json.loads((here/'input/PREPARATION.json').read_text());rows=[];windows={}
for key in ('P1','P2'):
 risk=json.loads((here/'input'/(key+'_RISK.json')).read_text())
 windows[key]=dict(days=len(risk),equal_forecast_sigma_days=sum(max(r['arms'][a]['post_sigma'] for a in r['arms'])-min(r['arms'][a]['post_sigma'] for a in r['arms'])<=1e-12 for r in risk),all_three_nominal_target_met_days=sum(all(r['arms'][a]['risk_target_met'] for a in r['arms']) for r in risk),all_three_intrinsic_cash_days=sum(all(r['arms'][a]['reason']=='INTRINSIC_CASH' for a in r['arms']) for r in risk),execution_quantity_multiplier=.99,scope='TARGET_VECTOR_FORECAST_ONLY_BEFORE_NATIVE99PERCENT_BUFFER_GRIDS_CAPACITY_FEES_FUNDING_DRIFT')
 for arm in ('CS_MATCHED','VOL_MATCHED','STATIC50'):
  path=here/'summary'/key/arm/'RESULT.json'
  if not path.exists():continue
  report=json.loads(path.read_text());s=report['summary'];reused=(path.parent/'REUSE.json').exists();state=Path('/workspace/quantity-grid-state' if reused else '/workspace/portfolio-risk-budget-state')/('OBSERVED_'+key)/arm
  assert path.read_bytes()==(state/'RESULT.json').read_bytes()
  pointer=json.loads((state/'recovery/POINTER.json').read_text());sums=np.zeros(36);counts=0;largest=np.full(36,-np.inf);smallest=np.full(36,np.inf)
  for c in pointer['chunks']:
   chunk=state/'recovery'/c['path'];assert hashlib.sha256(chunk.read_bytes()).hexdigest()==c['SHA256']
   with np.load(chunk,allow_pickle=False) as z:a=z['minute_chunk'] if reused else np.ascontiguousarray(z['column_chunk'].T)
   assert a.shape==(c['rows'],36) and a.dtype==np.float64 and np.isfinite(a).all();sums+=a.sum(0);counts+=len(a);largest=np.maximum(largest,a.max(0));smallest=np.minimum(smallest,a.min(0))
  assert counts==s['completed_minutes']
  cold=json.loads((path.parent/'PUBLIC_RESTORE.json').read_text()) if (path.parent/'PUBLIC_RESTORE.json').exists() else None
  row=dict(window=key,arm=arm,role='REUSED_ORIGINAL_CS_EXACT_TARGET_POLICY' if reused else 'NEW_CAUSAL_RISK_TARGET',full_calendar=counts==prep['windows'][key]['days']*1440,marked_net_USDT=s['net_PnL'],paid_flat=s['terminal_cash_realized'],paid_net_USDT=s['net_PnL'] if s['terminal_cash_realized'] else None,residual_notional_USDT=s['terminal_marked_notional'],annual_realized_daily_vol=report['metrics']['actual_daily_annual_vol'],minute_DD=s['all_observation_max_drawdown'],worst30=report['metrics']['worst30'],mean_actual_gross=float(sums[34]/counts),mean_actual_signed_net=float(sums[35]/counts),max_actual_gross=float(largest[34]),min_actual_net=float(smallest[35]),max_actual_net=float(largest[35]),actual_risk_reduction_signals=s['risk_reduction_signal_count'],target_risk=prep['windows'][key]['arms'][arm],public_recovery_pass=bool(cold and cold['account_advances']==0),state_hash=pointer['state_hash'],all_history_seen=True)
  rows.append(row)
report=dict(status='READONLY_SCOPE_AND_REALIZED_EXPOSURE_REVIEW',cases=rows,windows=windows,new_wallets_completed=sum(r['role']=='NEW_CAUSAL_RISK_TARGET' for r in rows),CS_cases_REUSED=2,financial_advances=0,new_fits=0,downloads=0)
(here/'evidence/RESULT_REVIEWED.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,indent=2))
