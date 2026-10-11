import json
from pathlib import Path
import numpy as np
from modules.slow_momentum_cpd.cost_training import ARCHIVE
from modules.slow_momentum_cpd.diagnose_training import read_training_close
from modules.slow_momentum_cpd.core import DAY_US,SYMBOLS,trend_features,FrozenGP,Scaler,sample_index
from modules.slow_momentum_cpd.run import ROOT,sha,utc_us,write_json
from modules.slow_momentum_cpd.sharpe import decision_mask,calendar_axis

available,close=read_training_close(ARCHIVE)
trend,returns,vol=trend_features(close)
f=json.loads((ROOT/'research/slow-momentum-cpd-20261011/results/FROZEN_TRAINING.json').read_text())
gp=FrozenGP(f['mean'],f['scale'],np.asarray(f['stationary_log_parameters']),np.asarray(f['change_log_parameters']),np.asarray(f['locations']),21,f['fit'])
features=np.concatenate((trend,gp.transform(returns)),axis=2)
times=calendar_axis(available,utc_us('2021-01-01'),utc_us('2023-01-01'))
mask=decision_mask(features,vol)[times]
future=returns[times+1]
missing=np.argwhere(mask & (~np.isfinite(future) | (future<=-1)))
def date(us):return str(np.datetime64(int(us),'us'))+'Z'
records=[]
for local,a in missing:
    t=times[local]
    history=[]
    for k in range(t-2,t+3):
        history.append(dict(available=date(available[k]),close=None if not np.isfinite(close[k,a]) else float(close[k,a]),return_=None if not np.isfinite(returns[k,a]) else float(returns[k,a])))
    records.append(dict(symbol=SYMBOLS[a],decision_available=date(available[t]),label_end=date(available[t+1]),finite63_input=True,current_vol=float(vol[t,a]),next_return=None if not np.isfinite(future[local,a]) else float(future[local,a]),history=history))
rows=sample_index(trend,returns,vol,available,utc_us('2021-01-01'),utc_us('2023-01-01'))
causal=np.argwhere(mask);causal[:,0]=times[causal[:,0]]
value=dict(status='CAUSAL_ELIGIBLE_OUTCOME_FAILURE_STOP_BEFORE_FIT',training_calendar_days=len(times),causal_eligible_endpoints=len(causal),original_mature_endpoints=len(rows),original_rows_sha256=sha(rows.astype('<i8').tobytes()),original_expected_rows_sha256='983baa27d9c0105c48b7c7debfea24089c28bff277014e1e43e2b27721d9e50f',original_samples_exclude_missing_future=not np.array_equal(causal,rows),missing_count=len(records),missing=records,archive_sha256=sha(ARCHIVE.read_bytes()),new_fits=0,new_updates=0,new_model_predictions=0,not_allowed='No future-derived mask, zero substitution, forward-fill, changed endpoint axis or policy rescue; source/economic recipe immutable.')
write_json(Path('/workspace/slow-momentum-cost-training-state/CALENDAR_FAILURE_DIAGNOSTIC.json'),value)
print(json.dumps(value))
