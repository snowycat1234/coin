import numpy as np

def split(d,maturity,complete,cutoff,end):
    d=np.asarray(d,np.int64);maturity=np.asarray(maturity,np.int64);complete=np.asarray(complete,bool)
    if maturity.shape!=d.shape or complete.shape!=d.shape or np.any(np.diff(d)<=0):raise ValueError('Unique aligned clocks')
    return complete&(d<cutoff)&(maturity<cutoff),complete&(d>=cutoff)&(d<end)&(maturity<end)

def omission(positive,full_best,rank_best,ideal_short,path_short,risk_short):
    a=np.asarray([positive,full_best,rank_best,ideal_short,path_short,risk_short],bool)
    if a.ndim!=2:raise ValueError('Aligned date flags')
    out=np.full(a.shape[1],'NO_POSITIVE_SHORT_REFERENCE',dtype='U48')
    out[a[0]&a[5]]='NEGATIVE_TARGET_PRESENT_NATIVE_FILL_UNKNOWN'
    absent=a[0]&~a[5]
    for test,name in zip(a[1:5],('COUPLED_ACTION_OR_NONSHORT_BETTER','RANK_NOT_BEST_WITH_NO_NEGATIVE_TARGET','SOFTMAX_NETTING_MISS','L1_PATH_MISS')):
        out[absent&~test]=name;absent&=test
    out[absent]='PAST_RISK_ZERO'
    return out

def utility_scores(original,advantage):
    original=np.asarray(original,float);advantage=np.asarray(advantage,float)
    if original.ndim!=2 or original.shape[1]!=3 or advantage.shape!=(len(original),):raise ValueError('Aligned3action utilities')
    out=original.copy();out[:,2]=original[:,:2].max(1)+advantage;return out
