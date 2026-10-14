"""Fixed original four-arm target arithmetic; never creates or advances wallets."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from original_functions import DAY, SYMBOLS, load_originals

ARMS = ('STATIC50', 'SMA200_10PCT', 'EXACTHALF', 'VOL_MATCHED')

def us(year):
    return int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1_000_000)

def asset_masks(t,p,d):
    masks = np.zeros((len(d),5),dtype=bool)
    for i,at in enumerate(d):
        k = int(np.searchsorted(t,at))
        if k < 199 or k >= len(t) or t[k] != at:
            raise ValueError('TARGET_STOP: original 200-row calendar unavailable')
        history=p[k-199:k+1]
        masks[i]=np.all(np.isfinite(history)&(history>0),axis=0)
    return masks

def build(t,p,d, *, original_hold=None, original_hold_mask=None):
    t=np.asarray(t,dtype=np.int64);p=np.asarray(p,dtype=np.float64);d=np.asarray(d,dtype=np.int64)
    if (p.shape != (len(t),5) or len(d)<1 or np.any(np.diff(t)!=DAY)
            or np.any(np.diff(d)!=DAY)):
        raise ValueError('TARGET_STOP: exact CORE5 ordered contiguous daily clocks required')
    first=int(np.searchsorted(t,d[0]))
    if first<199 or t[first]!=d[0] or first<63+(int((d[0]-1_704_067_200_000_000)%(7*DAY))//DAY):
        raise ValueError('TARGET_STOP: original prior weekly rank/SMA/risk context missing')
    functions=load_originals()
    mean=pd.DataFrame(p).rolling(200,min_periods=200).mean().to_numpy()
    direction=np.sign(p-mean)
    intents=functions.signed_intents(p,direction,t,SYMBOLS)
    ids=np.searchsorted(t,d)
    if (ids>=len(t)).any() or not np.array_equal(t[ids],d):
        raise ValueError('TARGET_STOP: absent output decision close')
    mask=asset_masks(t,p,d)
    if original_hold is None:
        raise ValueError('TARGET_STOP: explicit original HOLD target bytes required')
    hold=np.asarray(original_hold,dtype=np.float64).copy()
    hm=mask if original_hold_mask is None else np.asarray(original_hold_mask,dtype=bool)
    if hold.shape!=(len(d),5) or hm.shape!=mask.shape or not np.array_equal(hm,mask):
        raise ValueError('TARGET_STOP: original HOLD mask differs from real 200-close readiness')
    if not np.isfinite(hold).all() or np.any(hold[~hm]!=0):
        raise ValueError('TARGET_STOP: invalid original HOLD target')
    matched,match_proof,state,cs_diag=functions.match(t,p,d,hold,hm)
    missing_clock=[r for r in match_proof if r['status']=='MISSING_CURRENT_OR_PAST_CLOCK']
    if missing_clock:
        raise ValueError('TARGET_STOP: original match/rank covariance calendar unavailable')
    cs_mask=np.asarray(cs_diag['current_eligible'],dtype=bool)
    if not cs_mask.all():
        raise ValueError('TARGET_STOP: expected real fullfive 31-close CS/risk source unavailable')
    raw={k:matched[k] for k in ('CS_MATCHED','VOL_MATCHED')}
    raw['STATIC50']=.5*raw['CS_MATCHED']+.5*raw['VOL_MATCHED']
    sized,cov,risk_proof=functions.allocate(t,p,d,raw)
    sma=intents[ids,0].copy()
    out=dict(STATIC50=sized['STATIC50'],SMA200_10PCT=sma,
             EXACTHALF=.5*sized['STATIC50']+.5*sma,VOL_MATCHED=sized['VOL_MATCHED'])
    for name,row in out.items():
        if (not np.isfinite(row).all() or np.abs(row).max()>.3+1e-12
                or np.abs(row).sum(1).max()>.6+1e-12 or np.any(row[~mask]!=0) and name=='SMA200_10PCT'):
            raise ValueError('TARGET_STOP: original caps, finite values or mask failed: '+name)
    np.testing.assert_array_equal(out['EXACTHALF'],.5*out['STATIC50']+.5*out['SMA200_10PCT'])
    return out,cov,dict(hold_mask=hm,sma_mask=mask,cs_mask=cs_mask,
        CS_ORIGINAL=matched['CS_ORIGINAL'],VOL_ORIGINAL=hold,
        CS_MATCHED=sized['CS_MATCHED'],sma_direction=direction[ids],mean200=mean[ids],
        match_proof=match_proof,risk_proof=risk_proof,rank_diagnostic=cs_diag,state=state)

def load_cube(path):
    with np.load(path,allow_pickle=False) as z:
        if tuple(z['symbol_order'])!=SYMBOLS:
            raise ValueError('TARGET_STOP: symbol order')
        return z['close_available_us'].copy(),z['close'].copy()
