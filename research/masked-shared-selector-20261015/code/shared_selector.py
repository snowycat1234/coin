"""Frozen two-origin shared utility diagnostic. No full-fixture fit operation exists."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
import json, datetime as dt, time, platform, signal
from pathlib import Path
import numpy as np
DAY=86400000000
ORIGINS=('2023-11-12','2023-12-10')
ENDS=('2023-12-10','2023-12-18')
EXPECTED=((456,64,2042,28),(484,68,2182,8))
ROOT=Path(__file__).resolve().parents[1]
def us(s):return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()*1e6)
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def disjoint(rows):
    end=-1; result=[]
    for r in rows:
        if r['decision_us']>=end:result.append(r['date']);end=r['label_available_us']
    return result

def prefix(rows,origin,pool_clock):
    t=us(origin)
    if pool_clock>t:raise ValueError('Expert pool selection occurs after the first validation start')
    if origin not in ORIGINS:raise ValueError('Only the two frozen legal origins are authorized')
    return [r for r in rows if r['decision_us']<t and r['label_available_us']<t-7*DAY]

def validate(rows,cash):
    last=-1
    for r in rows:
        t=r['decision_us'];assert t>last;last=t
        assert r['label_available_us']==t+7*DAY+120000001
        a=r['available_mask'];m=r['supervised_mask']
        assert len(a)==len(m)==6 and m[cash] and sum(m)>=2
        for j in range(6):
            assert not m[j] or a[j]
            if a[j]:
                assert np.shape(r['x'][j])==(10,) and np.isfinite(r['x'][j]).all()
                c=r['clocks'][j]
                assert c['target_available_us']<=t and c['latest_feedback_available_us']<t
                assert c['feedback_count']==30 and c['feedback_last_decision_us']<t
                assert c['feedback_last_decision_us']-c['feedback_first_decision_us']==29*DAY
            else:assert r['x'][j] is None and r['clocks'][j] is None
            assert (r['utility'][j] is not None)==bool(m[j])
            if m[j]:assert np.isfinite(r['utility'][j])
        assert r['utility'][cash]==0

def design(rows,cash):
    noncash=[j for j in range(6) if j!=cash];features=[];labels=[];weights=[];ids=[]
    for r in rows:
        eligible=[j for j in noncash if r['supervised_mask'][j]]
        assert eligible
        for j in eligible:
            assert r['available_mask'][j] and r['x'][j] is not None
            features.append(r['x'][j]);labels.append(r['utility'][j]);ids.append(noncash.index(j))
            weights.append(1/(len(rows)*len(eligible)))
    x=np.asarray(features,dtype=np.float64); y=np.asarray(labels,dtype=np.float64);q=np.asarray(weights)
    mu=np.sum(x*q[:,None],axis=0);var=np.sum((x-mu)**2*q[:,None],axis=0)
    zero=var==0;scale=np.where(zero,1,np.sqrt(var));z=(x-mu)/scale;z[:,zero]=0
    X=np.zeros((len(y),15));X[:,:10]=z;X[np.arange(len(y)),10+np.asarray(ids)]=1
    return X,y,q,dict(mean=mu.tolist(),variance=var.tolist(),scale=scale.tolist(),zero_variance_mask=zero.tolist())

def objective(theta,X,y,q):return float(.5*np.sum(q*(X@theta-y)**2)+.5*np.sum(theta**2))
def gradient(theta,X,y,q):return X.T@(q*(X@theta-y))+theta

def solve(X,y,q):
    theta=np.linalg.solve(X.T@(q[:,None]*X)+np.eye(15),X.T@(q*y))
    loss=objective(theta,X,y,q);g=float(np.max(np.abs(gradient(theta,X,y,q))))
    assert np.isfinite(theta).all() and np.isfinite(loss) and g<=1e-8
    return theta,loss,g

def scores(row,model,cash):
    # Deliberately does not read any label, utility, or supervised-mask field.
    theta=np.asarray(model['theta']);s=[None]*6;s[cash]=0.0
    mu=np.asarray(model['scaler']['mean']);scale=np.asarray(model['scaler']['scale']);zero=np.asarray(model['scaler']['zero_variance_mask'])
    for b,j in enumerate(j for j in range(6) if j!=cash):
        if row['available_mask'][j]:
            z=(np.asarray(row['x'][j])-mu)/scale;z[zero]=0
            s[j]=float(z@theta[:10]+theta[10+b])
    return s

def choose(s,cash):
    best=cash
    for j,v in enumerate(s):
        if j!=cash and v is not None and v>s[best]:best=j
    return best

def summarize(results,experts):
    out={}
    for group in ['pooled',*ORIGINS]:
        r=[x for x in results if group=='pooled' or x['origin']==group];n=len(r)
        out[group]={'dates':n,'mean_chosen_utility':float(np.mean([x['chosen_utility'] for x in r])),
                    'mean_oracle_utility':float(np.mean([x['oracle_utility'] for x in r])),
                    'mean_regret':float(np.mean([x['regret'] for x in r])),
                    'choice_counts':{e:sum(x['choice']==e for x in r) for e in experts},'controls':{}}
        for j,e in enumerate(experts):
            out[group]['controls'][e]={'mean_utility':float(np.mean([x['controls'][e]['utility'] for x in r])),
                'mean_paired_chosen_minus_control':float(np.mean([x['chosen_utility']-x['controls'][e]['utility'] for x in r])),
                'available_dates':sum(x['available_mask'][j] for x in r),
                'cash_fallback_dates':sum(not x['available_mask'][j] for x in r)}
    return out

def main():
    assert (ROOT/'tests/PASS.json').exists(),'Structural tests must pass before fits'
    assert not any((ROOT/'models').iterdir()),'Never restart/re-fit after any model is sealed'
    if hasattr(os,'sched_getaffinity'):
        cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    p=json.loads((ROOT/'inputs/raw_fixture.json').read_text());rows=p['rows'];experts=p['experts'];cash=experts.index('CASH')
    forecasts=[];receipts=[]
    # Each fit is sealed before its forecast labels are read. No evaluation inputs enter design().
    for origin,end,expected in zip(ORIGINS,ENDS,EXPECTED):
        train=prefix(rows,origin,p['pool_selection_available_us'])
        validate(train,cash)
        forecast=[r for r in rows if us(origin)<=r['decision_us']<us(end)]
        count=(len(train),len(disjoint(train)),sum(sum(r['supervised_mask'])-1 for r in train),len(forecast))
        assert count==expected and count[1]>=40 and all(all(r['available_mask']) for r in forecast)
        started=now();tick=time.perf_counter();print('FIT_START '+origin+' '+started,flush=True)
        def timeout(signum,frame):raise TimeoutError('120 second per-fold limit')
        signal.signal(signal.SIGALRM,timeout);signal.alarm(120)
        X,y,q,scaler=design(train,cash);theta,loss,g=solve(X,y,q)
        elapsed=time.perf_counter()-tick;ended=now();signal.alarm(0)
        assert elapsed<=120
        receipt={'origin':origin,'actual_compute_start_utc':started,'actual_compute_end_utc':ended,'elapsed_seconds':elapsed,
            'solver':'numpy.linalg.solve','numpy_version':np.__version__,'python_version':platform.python_version(),
            'one_cpu_affinity':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
            'blas_threads':1,'fit_number_for_origin':1,'training_dates':len(train),'training_first_date':train[0]['date'],
            'training_last_date':train[-1]['date'],'training_disjoint_admissions':len(disjoint(train)),
            'training_disjoint_dates':disjoint(train),'training_noncash_observations':len(y),
            'training_per_expert':{e:sum(r['supervised_mask'][j] for r in train) for j,e in enumerate(experts)},
            'training_dates_by_year':{year:sum(r['date'].startswith(year) for r in train) for year in ['2022','2023']},
            'training_label_strict_cutoff_us':us(origin)-7*DAY,'maximum_training_label_available_us':max(r['label_available_us'] for r in train),
            'pool_selection_available_us':p['pool_selection_available_us'],'objective':loss,'gradient_infinity_norm':g,
            'historical_issuance_claim':False}
        model={'origin':origin,'experts':experts,'feature_names':p['feature_names'],'theta':theta.tolist(),'scaler':scaler,
               'lambda':1.0,'parameters':15,'cash_score':0.0,'receipt':receipt}
        write(ROOT/'models'/f'{origin}.json',model);receipts.append(receipt)
        print('FIT_SEALED '+origin+' '+ended,flush=True)
        # Freeze choices independently of utility fields, then evaluate after sealing model.
        frozen=[]
        for r in forecast:
            state={k:r[k] for k in ['x','available_mask']};s=scores(state,model,cash);j=choose(s,cash)
            frozen.append({'date':r['date'],'origin':origin,'scores':s,'choice':experts[j]})
        write(ROOT/'results'/f'{origin}_frozen_choices.json',frozen)
        for r,f in zip(forecast,frozen):
            eligible=[j for j in range(6) if r['available_mask'][j]]
            assert all(r['utility'][j] is not None for j in eligible)
            j=experts.index(f['choice']);oracle=max(r['utility'][k] for k in eligible)
            f.update(decision_us=r['decision_us'],label_available_us=r['label_available_us'],available_mask=r['available_mask'],
                     chosen_utility=r['utility'][j],oracle_utility=oracle,regret=oracle-r['utility'][j],
                     controls={e:{'choice':e if r['available_mask'][k] else 'CASH','utility':r['utility'][k] if r['available_mask'][k] else 0.0} for k,e in enumerate(experts)})
            forecasts.append(f)
    primary_dates=disjoint(forecasts)
    assert primary_dates==['2023-11-12','2023-11-20','2023-11-28','2023-12-06','2023-12-14']
    for r in forecasts:r['primary']=r['date'] in primary_dates
    write(ROOT/'results/all_36_dates.json',forecasts)
    write(ROOT/'results/summary.json',{'primary_5':summarize([r for r in forecasts if r['primary']],experts),
          'secondary_36':summarize(forecasts,experts),'primary_dates':primary_dates,
          'interpretation':'Tiny conditional known-development source-utility diagnostic. No advantage, independence, return, APR, significance, deployment or fresh-OOS claim.'})
    write(ROOT/'receipts/fit_receipts.json',receipts)
    print('COMPLETE: two sealed fits, 36 secondary dates, 5 globally selected primary dates',flush=True)
if __name__=='__main__':main()
