"""Separate owned-interval overlap from true reward completeness/availability."""
import numpy as np


def owned_indices(decisions,starts,ends,maturity,eligible,cutoff):
    d,s,e,a=[np.asarray(x) for x in (decisions,starts,ends,maturity)];ok=np.asarray(eligible)
    if (any(x.ndim!=1 or x.dtype.kind not in 'iu' or x.shape!=d.shape for x in (d,s,e,a))
        or ok.shape!=d.shape or ok.dtype!=bool or np.any(np.diff(d)<=0)
        or np.any(s<d) or np.any(e<=s) or np.any(a<e)):
        raise ValueError('Exactunique decisions/ownedintervals/complete maturity andBoolean eligibility required')
    if np.any(ok&(a>=cutoff)):raise ValueError('Fullrewardandexitcost mustmature beforecutoff')
    selected=[];last=-1
    for i in np.flatnonzero(ok):
        if int(s[i])>=last:selected.append(int(i));last=int(e[i])
    return np.asarray(selected,np.int64)


def interval_events(times,start,end):
    t=np.asarray(times)
    return np.flatnonzero((t>start)&(t<=end))
