import numpy as np

def partition(positive,full_best,rank_best,desired_short,path_short,risk_short):
    """Mutually exclusive causal stage diagnosis conditioned on hindsight opportunity."""
    a=np.asarray([positive,full_best,rank_best,desired_short,path_short,risk_short],bool)
    if a.ndim!=2:raise ValueError('Aligned Boolean date vectors required')
    out=np.full(a.shape[1],'NO_POSITIVE_SHORT_REFERENCE',dtype='U48')
    active=a[0].copy()
    for test,name in zip(a[1:],('COUPLED_ACTION_OR_NONSHORT_BETTER','RANK_MISS','SOFTMAX_NETTING_MISS','L1_PATH_MISS','PAST_RISK_ZERO')):
        own=active&~test;out[own]=name;active&=test
    out[active]='NEGATIVE_TARGET_PRESENT_NATIVE_FILL_UNKNOWN'
    return out

def runs(d,mask,day=86400000000):
    d=np.asarray(d,np.int64);mask=np.asarray(mask,bool)
    if d.ndim!=1 or mask.shape!=d.shape or np.any(np.diff(d)<=0):raise ValueError('Unique ordered decision dates')
    selected=np.flatnonzero(mask);out=[]
    for i in selected:
        if out and d[i]==out[-1]['last_decision_us']+day:
            out[-1]['last_decision_us']=int(d[i]);out[-1]['dates']+=1
        else:out.append(dict(first_decision_us=int(d[i]),last_decision_us=int(d[i]),dates=1))
    return out

def reliability(budget,winner,mask):
    budget=np.asarray(budget,float);winner=np.asarray(winner,bool);mask=np.asarray(mask,bool)
    out=[]
    for i in range(5):
        own=mask&(budget>=i/5)&(budget<(i+1)/5 if i<4 else budget<=1)
        out.append(dict(left=i/5,right=(i+1)/5,dates=int(own.sum()),mean_allocation=float(budget[own].mean()) if own.any() else None,
                        realized_conditional_win_frequency=float(winner[own].mean()) if own.any() else None))
    return out
