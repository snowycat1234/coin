import numpy as np

def past_risk_prices(clocks,close,t,own,day):
    clocks=np.asarray(clocks,np.int64);k=int(np.searchsorted(clocks,t))
    if k<30 or k>=len(clocks) or clocks[k]!=t:raise ValueError('Exact decision date and 30 past days required')
    window=clocks[k-30:k+1]
    if not np.all(np.diff(window)==day) or np.any(window>t):raise ValueError('Continuous past-only risk clocks required')
    prices=np.asarray(close)[k-30:k+1][:,own]
    if prices.shape!=(31,len(own)) or not np.isfinite(prices).all() or np.any(prices<=0):raise ValueError('Finite positive past-only risk prices required')
    return prices

def sleeve_targets(pool,budgets,retention):
    pool=np.asarray(pool,float);budgets=np.asarray(budgets,float);retention=np.asarray(retention,float)
    if pool.ndim!=3 or pool.shape[1:]!=(3,5) or budgets.shape!=pool.shape[:2] or retention.shape!=(len(pool),2):raise ValueError('Exact original pool/CORE5 shapes')
    if not np.isfinite(retention).all() or np.any((retention<0)|(retention>1)):raise ValueError('No sleeve leverage')
    long=np.maximum(pool[:,2],0);short=np.minimum(pool[:,2],0);gross=np.column_stack([long.sum(1),-short.sum(1)])
    total=gross.sum(1);mean=np.divide((gross*retention).sum(1),total,out=np.zeros(len(pool)),where=total>0)
    allocated=budgets[:,2,None]*(long*retention[:,0,None]+short*retention[:,1,None])
    matched=budgets[:,2,None]*pool[:,2]*mean[:,None]
    np.testing.assert_allclose(np.abs(allocated).sum(1),np.abs(matched).sum(1),rtol=1e-12,atol=1e-14)
    vol=budgets[:,1,None]*pool[:,1]
    return dict(UNBOUND=vol+allocated,GROSS_MATCHED_COUPLED=vol+matched),dict(allocated_CS_gross=np.abs(allocated).sum(1),mean_retention=mean)

def checkpoint_prediction(x,models):
    z=(x-models['mean'])/models['scale']
    return np.einsum('nf,of->no',z,models['coef'],optimize=False)+models['intercept']
