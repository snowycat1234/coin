import csv,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
s=Path('coin_single_state'); r=Path('coin_single_stream/research');out={}
for label,folder in [('July','temporal-july-frozen-transfer-20261010/results'),('Q4','temporal-selected-refit-q4-20261010/q4-results')]:
 p=s/'scaler-eval-once';rows=list(csv.DictReader((p/f'{label}_DAILY.csv').open()));req=np.load(p/f'{label}_REQUESTS.npz');path=np.load(p/f'{label}_PATH.npz');c=np.load(r/folder/'CURRENT_CONTEXT.npz');n=len(rows);active=n-1
 assert np.array_equal(req['decision_us'],c['decision_us']);assert len(rows)==len(req['request'])
 mom=np.prod(1+c['past_returns30'],axis=1)-1;market=np.mean(mom,axis=1);mask=market[:active]<0;weights=path['budget'][:active];short=5
 groups={}
 for name,m in [('all',np.ones(active,dtype=bool)),('prior30_equal_asset_return_negative',mask),('prior30_equal_asset_return_nonnegative',~mask)]:
  ix=np.flatnonzero(m);groups[name]={'days':len(ix),'mean_budget':weights[ix].mean(0).tolist() if len(ix) else None,'mean_prior30_return':float(market[ix].mean()) if len(ix) else None,'net_PnL':sum(float(rows[i]['end_nav'])-float(rows[i]['start_nav']) for i in ix),'short_eligible_days':int(c['expert_eligible'][:active,short][ix].sum()),'short_target_nonzero_days':int((np.abs(c['expert_targets'][:active,short]).sum(1)[ix]>0).sum())}
 months={}
 for i,row in enumerate(rows):
  month=datetime.fromtimestamp(int(row['decision_us'])/1e6,timezone.utc).strftime('%Y-%m');m=months.setdefault(month,{'rows':0,'net_PnL':0.,'price_PnL':0.,'funding_PnL':0.,'cost':0.});m['rows']+=1;m['net_PnL']+=float(row['end_nav'])-float(row['start_nav']);m['price_PnL']+=float(row['price_PnL']);m['funding_PnL']+=float(row['funding_PnL']);m['cost']+=sum(float(row[k]) for k in ['fees','spread','slippage','charged_reduction_cost'])
 out[label]={'groups':groups,'months':months,'short_request_min_max':[float(req['request'][:active,short].min()),float(req['request'][:active,short].max())],'short_budget_min_max':[float(weights[:,short].min()),float(weights[:,short].max())],'expert_order':['CASH','VOL','unavailable2','unavailable3','CS','SHORT'],'note':'Descriptive grouping using stored prior-only 30 day equal asset return, no thresholds tuned or policies replayed; overlapping observations, no conditional predictability inference.'}
(s/'SAVED_ALLOCATION_DIAGNOSTIC.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
