#!/usr/bin/env python3
"""Independent bounded-memory streaming check of saved NAV descriptive arithmetic."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','POLARS_MAX_THREADS'):
    os.environ[k]='1'
os.sched_setaffinity(0,{1})
import hashlib,json,math,pathlib,time,zipfile
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent.parent
HERE=pathlib.Path(__file__).resolve().parent

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()

def read_exact(f,n):
    parts=[]
    while n:
        b=f.read(n)
        if not b:raise AssertionError('SHORT_ARRAY')
        parts.append(b);n-=len(b)
    return b''.join(parts)

def run():
    t=time.monotonic()
    dp=ROOT/'traditional_D_MASTER45_saved_summary_20261015/SAVED_DAILY_NAV_DERIVATION.json'
    before=sha(dp);d=json.loads(dp.read_text());assert len(d['cells'])==12
    out={'schema':'INDEPENDENT_MASTER45_SAVED_NAV_STREAM_REVIEW_V1','CPU_affinity':sorted(os.sched_getaffinity(0)),'numerical_pools':1,'account_constructions':0,'financial_replays':0,'network_calls':0,'saved_derivation_SHA256':before,'cells':[]}
    for row in d['cells']:
        cell=row['cell_id'];p=ROOT/row['original_MINUTE']['path'];rp=ROOT/row['bound_review']['path']
        review=json.loads(rp.read_text());assert sha(rp)==row['bound_review']['SHA256']
        assert review['cell_id']==cell and review['year']==row['year'] and review['strategy']==row['strategy'] and review['tier']==row['tier']
        assert review['calendar']==row['calendar']
        pin=review['evidence']['MINUTE.npz'];original=sha(p)
        assert original==row['original_MINUTE']['SHA256']==pin['SHA256'] and p.stat().st_size==row['original_MINUTE']['bytes']==pin['bytes']
        navhash=hashlib.sha256();daily=[];total=0
        with zipfile.ZipFile(p) as z:
            assert sorted(z.namelist())==['columns.npy','values.npy']
            with z.open('columns.npy') as f:names=np.load(f,allow_pickle=False).tolist()
            assert names==row['original_columns'] and len(names)==len(set(names))
            ni=names.index('nav');ci=names.index('close_us');cols=len(names)
            with z.open('values.npy') as f:
                version=np.lib.format.read_magic(f); assert version in ((1,0),(2,0)); shape,order,dtype=(np.lib.format.read_array_header_1_0(f) if version==(1,0) else np.lib.format.read_array_header_2_0(f))
                assert tuple(shape)==tuple(row['original_values_shape'])==(525600,cols) and order and dtype==np.dtype('<f8')
                for column in range(cols):
                    total=0
                    while total<shape[0]:
                        n=min(4096,shape[0]-total);b=read_exact(f,n*8)
                        if column in (ni,ci):
                            v=np.frombuffer(b,dtype=dtype)
                            if column==ci:
                                assert np.array_equal(v,review['calendar'][0]+np.arange(total+1,total+n+1,dtype=np.int64)*60000000)
                            if column==ni:
                                navhash.update(b);first=(-total-1)%1440
                                daily.extend(float(x) for x in v[first::1440])
                        total+=n
                assert not f.read(1)
        nav=np.asarray(daily,dtype=np.float64);assert len(nav)==365 and np.array_equal(nav,np.asarray(row['daily_close_NAV_float64']))
        assert np.all(np.isfinite(nav)) and np.all(nav>0) and navhash.hexdigest()==row['nav_column_raw_C_order_SHA256']
        returns=np.empty(365);returns[0]=nav[0]/10000-1;returns[1:]=nav[1:]/nav[:-1]-1
        assert np.array_equal(returns,np.asarray(row['daily_simple_returns_float64']))
        assert hashlib.sha256(nav.tobytes()).hexdigest()==row['daily_endpoints_raw_C_order_SHA256']
        assert hashlib.sha256(returns.tobytes()).hexdigest()==row['daily_returns_raw_C_order_SHA256']
        volatility=float(np.std(returns,ddof=1)*math.sqrt(365));assert volatility==row['realized_daily_annualized_volatility']
        assert sha(p)==original and sha(rp)==row['bound_review']['SHA256']
        out['cells'].append({'cell_id':cell,'MINUTE_SHA256':original,'review_SHA256':row['bound_review']['SHA256'],'streamed_rows':total,'daily_endpoints':len(nav),'daily_endpoints_SHA256':hashlib.sha256(nav.tobytes()).hexdigest(),'annualized_daily_simple_return_volatility':volatility,'original_saved_array_and_review_unchanged':True})
        print(cell,'PASS',volatility,flush=True)
    assert sha(dp)==before
    out.update({'status':'PASS','wall_seconds':time.monotonic()-t,'formula':'Sample standard deviation (ddof=1) of all complete UTC daily-close simple returns, first previous NAV=10000, multiplied by sqrt(365). No return annualization.','source_or_target_arrays_read':False,'full_array_copies_or_extraction':False})
    p=HERE/'INDEPENDENT_DAILY_NAV_STREAM_REVIEW.json';p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(p.name,sha(p),flush=True)
if __name__=='__main__':run()
