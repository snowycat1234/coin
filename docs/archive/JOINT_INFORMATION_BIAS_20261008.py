"""Diagnose saved Ridge coefficients and legal train support; never fit."""
from pathlib import Path
from datetime import datetime, timezone
import time, json
import numpy as np
import polars as pl

began=time.monotonic()
state=Path('/home/ubuntu/coin/execution-state/joint-information-20261008-v1')
r=json.loads((state/'RESULTS.json').read_text());pred=json.loads((state/'PREDICTIONS.json').read_text())
def date(us):return datetime.fromtimestamp(int(us)/1e6,timezone.utc).strftime('%Y-%m-%d')
def first(d,mask):return date(d[np.flatnonzero(mask)[0]]) if np.any(mask) else None
f=r['protocol']['features'];names=['BTC_'+v for v in f]+['CORE5_mean_'+v for v in f]+['breadth_mom20','breadth_mom200']
names += [e+'_'+kind for kind in ['gross','net','short_abs'] for e in r['protocol']['experts']]
fbnames=[e+'_last'+str(w)+'weeks' for w in [1,4,12] for e in r['protocol']['experts']]
out=dict(method='Saved coefficients + training means/population variances reconstruct predictions; no sklearn estimator fit/transform calls; no label or wallet rerun',new_fits=0,new_wallets=0,cases=[],past_source_support=[])
with np.load(state/'PAST_INTENTS.npz',allow_pickle=False) as a:
    market=a['market'].copy()
for c,p in zip(r['cases'],pred):
    if c['input']!='COMBINED':continue
    with np.load(state/f'REFERENCE_PANEL_{c["funding_scale"]}.npz',allow_pickle=False) as a:
        d=a['decision_us'];av=a['label_available_us'];y=a['labels'];x=np.column_stack([market,a['feedback']]);complete=a['common']&np.isfinite(y).all(1)
        w=next(w for w in r['protocol']['windows'] if w['id']==c['window'])
        train=complete&(d<w['start'])&(av<w['start']-7*86400000000)
        val=np.searchsorted(d,p['decision_us']);assert np.array_equal(d[val],p['decision_us'])
        mean=x[train].mean(0);scale=x[train].std(0);scale[scale==0]=1
        z=(x[val]-mean)/scale;coef=np.array(c['scaled_coefficients']);intercept=y[train].mean(0)
        reconstructed=intercept+z@coef.T;reconstructed[:,3]=0
        error=float(np.max(np.abs(reconstructed-np.array(p['predicted_reference_utility']))));assert error<1e-8,error
        # CSMOM minus HOLD predicted differential, additive mean decomposition.
        diff=coef[1]-coef[2];pieces=z*diff;avg=pieces.mean(0);order=np.argsort(-np.abs(avg))[:6]
        maxz=np.abs(z).max(0);zorder=np.argsort(-maxz)[:4];allnames=names+fbnames
        out['cases'].append(dict(window=c['window'],scale=c['funding_scale'],prediction_reconstruction_max_error=error,training_mean_CSMOM_minus_HOLD_bp=float((intercept[1]-intercept[2])*1e4),predicted_mean_CSMOM_minus_HOLD_bp=float((reconstructed[:,1]-reconstructed[:,2]).mean()*1e4),actual_mean_CSMOM_minus_HOLD_bp=float((y[val,1]-y[val,2]).mean()*1e4),largest_mean_feature_contributions=[dict(feature=allnames[k],mean_contribution_bp=float(avg[k]*1e4),max_validation_train_z=float(maxz[k]),train_min=float(x[train,k].min()),train_max=float(x[train,k].max()),validation_min=float(x[val,k].min()),validation_max=float(x[val,k].max())) for k in order],largest_validation_extrapolations=[dict(feature=allnames[k],max_z=float(maxz[k])) for k in zorder]))
cutoff=max(w['end'] for w in r['protocol']['windows'])
for ref in r['input_refs']:
    a=pl.read_parquet(ref['past_path'],columns=['decision_available_at',*f]).filter(pl.col('decision_available_at').dt.epoch('us')<=cutoff)
    d=a['decision_available_at'].dt.epoch('us').to_numpy();v=a.select(f).to_numpy()
    out['past_source_support'].append(dict(symbol=ref['symbol'],first_source_decision=date(d[0]),first_complete_eight=first(d,np.isfinite(v).all(1)),first_finite_by_feature={name:first(d,np.isfinite(v[:,j])) for j,name in enumerate(f)}))
out['elapsed_seconds']=time.monotonic()-began
(state/'RELATIVE_BIAS_DIAGNOSIS.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
