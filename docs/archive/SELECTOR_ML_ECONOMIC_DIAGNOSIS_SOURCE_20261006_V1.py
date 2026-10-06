import json,os,hashlib,math
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
from quant.paths import ROOT,STATE
from scripts.research.selector_jobs import atomic
r=json.loads((ROOT/'reports/SELECTOR_ML_RESULTS.json').read_bytes());c=r['config'];run=Path(c['run_dir']);champ=r['champion_by_preregistered_rank'];h=int(champ.rsplit('_H',1)[1]);rows={v['id']:v for v in r['rows']};out=[]
for unit in c['units']:
    s=rows[champ+'_'+unit];hold=rows['HOLD_'+unit];sma=rows['SMA200_SIGNED_'+unit]
    wp=np.load(run/'weights'/(champ+'_'+unit+'.npz'));f=__import__('polars').read_parquet(run/'features.parquet');times=f['decision_us'].to_numpy()
    ix=np.searchsorted(times,wp['decisions']);common=wp['decisions']<=times[0]+(730-90)*86400000000
    labels=np.load(run/f'labels_{unit}_{h}.npz')['utility'][ix[common]];ranks=np.array([(rankdata(v)-1)/2 for v in labels]);weights=wp['weights'][common]
    scores=dict(SMA200_SIGNED=float(ranks[:,0].mean()),HOLD=float(ranks[:,1].mean()),CASH=float(ranks[:,2].mean()),STATIC=float((ranks*np.array([.5,.25,.25])).sum(axis=1).mean()),LINEAR_H60=float((ranks*weights).sum(axis=1).mean()))
    fits=[v for v in r['fit_records'] if v['placebo'] is None and v['model']=='LINEAR' and v['horizon']==h and v['unit']==unit]
    placebo={kind:dict(n=len(vs),exceedances=sum(v['net_PnL']>=s['net_PnL'] for v in vs),finite_upper_tail=(1+sum(v['net_PnL']>=s['net_PnL'] for v in vs))/(len(vs)+1),selection_adjusted=False) for kind in ('LABEL_SHUFFLE','FEATURE_SHUFFLE','RANDOM') for vs in [[v for v in r['rows'] if v['unit']==unit and v['id'].startswith(kind)]]}
    delta=lambda base:dict(net=s['net_PnL']-base['net_PnL'],gross=s['gross_PnL']-base['gross_PnL'],negative_fees_execution=-(s['fees']+s['execution']-base['fees']-base['execution']),funding=s['funding']-base['funding'],vol_difference=s['volatility']-base['volatility'],MDD_difference=s['MDD']-base['MDD'],Sharpe_difference=s['Sharpe']-base['Sharpe'])
    out.append(dict(unit=unit,utility_rank_same_horizon_common_dates=scores,common_mature_rows=int(common.sum()),relative_HOLD=delta(hold),relative_SMA=delta(sma),placebo_finite_tail=placebo,
        H60_R2_train_median=float(np.median([v['train_R2'] for v in fits])),H60_R2_validation_median=float(np.median([v['validation_mature_R2'] for v in fits])),
        primary_failure='2023 SHORT loss plus foregone LONG participation; price PnL deficit, not costs',next_action='NO_ADDITIONAL_ML_FITS; frozen experts cross-window opportunity/conditional-ranking transfer on accepted seen213d data'))
payload=dict(status='COMPLETE_FROZEN_SELECTOR_ECONOMIC_FAILURE_DIAGNOSIS',task_id=os.environ['COIN_TASK_ID'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results_sha256=hashlib.sha256((ROOT/'reports/SELECTOR_ML_RESULTS.json').read_bytes()).hexdigest(),units=out,new_models_fit=0,new_accounts=0,success_thresholds_changed=False,seed_search=False,independent_OOS_claim=False)
atomic(ROOT/'reports/SELECTOR_ML_DIAGNOSIS_20261006_V1.json',payload)
print(json.dumps(out,indent=2))