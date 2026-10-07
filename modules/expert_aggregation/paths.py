from pathlib import Path
import numpy as np
import polars as pl
from .common import DAY,atomic,read,sha
from .allocator import NAMES,paths

def prepare(state):
    from scripts.investment.frozen_expert_mixture import combine,verify
    cache=state/'cache';proof=read(cache/'INPUT_BINDING.json')
    if tuple(proof['names'])!=tuple(NAMES):raise ValueError('Canonical expert order mismatch')
    decisions=np.arange(1640995200000000,1704067200000000,DAY,dtype=np.int64)
    visible=decisions+DAY+1;eval_mask=decisions>=proof['start'];eval_days=decisions[eval_mask]
    bars=pl.read_parquet(cache/'daily.parquet');directory=state/'targets';directory.mkdir(exist_ok=True)
    records=[];diagnostics=[]
    for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
        feedback=np.load(cache/(unit+'-feedback.npy'),allow_pickle=False)
        weights,meta=paths(feedback,visible,decisions,unit)
        frames={name:pl.read_parquet(cache/(unit+'-'+name+'-targets.parquet')).filter(pl.col('available_us')>=proof['start']) for name in NAMES}
        z=np.column_stack([frames[name]['target_weight'].to_numpy() for name in NAMES])
        for name,w in weights.items():
            f=directory/(unit+'-'+name+'-weights.npy');np.save(f,w[eval_mask],allow_pickle=False)
            target=combine(frames,NAMES,eval_days,('BTCUSDT',),w[eval_mask])
            scalar=verify(target,frames,NAMES,eval_days,('BTCUSDT',),w[eval_mask],bars)
            p=directory/(unit+'-'+name+'.parquet');target.write_parquet(p,compression='zstd')
            # Exact signed decomposition, reported as intention changes, not actual traded turnover.
            ew=w[eval_mask];expert_change=(ew[:-1]*(z[1:]-z[:-1])).sum(1)
            allocation_change=((ew[1:]-ew[:-1])*z[1:]).sum(1)
            combined=(ew[1:]*z[1:]).sum(1)-(ew[:-1]*z[:-1]).sum(1)
            if not np.allclose(combined,expert_change+allocation_change,rtol=0,atol=1e-14):raise ValueError('Exact target turnover decomposition')
            records.append(dict(algorithm=name,unit=unit,weights_path=str(f),weights_sha256=sha(f),target_path=str(p),target_sha256=sha(p),independent_target=scalar))
            diagnostics.append(dict(algorithm=name,unit=unit,
                expert_intention_change_absolute_sum=float(np.abs(expert_change).sum()),allocator_intention_change_absolute_sum=float(np.abs(allocation_change).sum()),
                combined_intention_change_absolute_sum=float(np.abs(combined).sum()),cash_mean_weight=float(ew[:,NAMES.index('CASH')].mean()),
                shadow_return_proxy_logwealth=float(np.log1p((ew*feedback[eval_mask]).sum(1)).sum()),
                proxy_role='NONLINEAR_SINGLE_WALLET_AND_SWITCH_COST_NOT_REPRESENTED_NOT_AN_EXECUTABLE_NAV',metadata=meta))
    result=dict(status='PASS_FROZEN_CAUSAL_PATHS_AND_INDEPENDENT_SCALAR_COVARIANCE',records=records,diagnostics=diagnostics,
        ewma='WEIGHT_DIAGNOSTIC_ONLY_NOT_THIRD_DYNAMIC_WALLET',feedback_visibility='DAY_END_PLUS_1US',training_static_domain='FINITE_REGISTERED_ONE_HOT')
    atomic(state/'PATHS.json',result)
    return result
