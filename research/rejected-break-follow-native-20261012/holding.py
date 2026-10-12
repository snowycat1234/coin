"""Count saved CASH-intent inventory after the unchanged five-attempt deadline."""
import argparse,json
from pathlib import Path
import numpy as np
from driver import HERE,sha,save,targets,SYMBOLS
def diagnose(key,account,destination):
 assert not destination.exists();d,w=targets(key);body=json.loads((account/'ACCOUNT.json').read_text());pointer=json.loads((account/'recovery/POINTER.json').read_text());assert body['summary']['completed_minutes']==pointer['completed_minutes']==525600 and len(pointer['chunks'])==365
 fields=[r['name'] for r in json.loads((account/'MINUTE_NUMERIC.json').read_text())['columns']];ix=[fields.index(s+'_quantity') for s in SYMBOLS];assert len(fields)==37 and fields[-1]=='close_us';per_asset=np.zeros(5,np.int64);rows=[];portfolio_minutes=0
 for i,r in enumerate(pointer['chunks']):
  p=account/'recovery'/r['path'];assert sha(p)==r['SHA256']
  with np.load(p,allow_pickle=False) as z:a=z['column_chunk'].T;assert a.shape==(1440,36) and np.isfinite(a).all();q=a[:,ix]
  # Original earliest fill00:01+1us, attempts01..05, lastattempt minuteclose00:06.
  late=(np.arange(1440)+1)>6;spill=(q!=0)&(w[i]==0)[None,:]&late[:,None];counts=spill.sum(0);per_asset+=counts
  portfolio_cash=bool(np.all(w[i]==0));pm=int(np.any(spill,axis=1).sum()) if portfolio_cash else 0;portfolio_minutes+=pm
  if counts.any():rows.append(dict(decision_us=int(d[i]),portfolio_CASH_intent=portfolio_cash,after_deadline_held_minutes_by_asset=dict(zip(SYMBOLS,counts.tolist(),strict=True)),maximum_abs_quantity_by_asset=dict(zip(SYMBOLS,np.abs(q[late]).max(0).tolist(),strict=True))))
 out=dict(status='READONLY_SAVED_INVENTORY_CLOCK_DIAGNOSTIC',window=key,complete_calendar_days=365,portfolio_CASH_intent_days=int(np.all(w==0,axis=1).sum()),natural_days_with_any_asset_CASH_late_inventory=len(rows),portfolio_CASH_days_with_late_inventory=sum(r['portfolio_CASH_intent'] for r in rows),portfolio_CASH_intent_late_inventory_minutes=portfolio_minutes,asset_CASH_intent_late_inventory_minutes=dict(zip(SYMBOLS,per_asset.tolist(),strict=True)),rows=rows,deadline='ONLY_COUNT_MINUTE_CLOSE_AFTER00:06_AFTER_ORIGINAL_FIVE_EXECUTION_TRIES',scope='TARGET24H_INTENT_IS_NOT_GUARANTEED_ACTUAL24H_HOLDING; residuals and PnL retained, no fixes or deletion',account_advances=0,new_fits=0,provider_downloads=0)
 save(destination,out);print('ACTUAL_FOLLOW_CASH_HOLDING_DIAGNOSTIC',key,int(per_asset.sum()),portfolio_minutes,len(rows),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--window',choices=['Y2023','Y2025'],required=True);p.add_argument('--account',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();diagnose(a.window,a.account,a.destination)
