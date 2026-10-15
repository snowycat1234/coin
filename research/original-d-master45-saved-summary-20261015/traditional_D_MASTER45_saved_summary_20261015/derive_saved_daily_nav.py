#!/usr/bin/env python3
"""Descriptive saved-NAV aggregation only. No financial model imports or replay."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','POLARS_MAX_THREADS'):
    os.environ[name]='1'
import argparse, hashlib, json, math, pathlib, tempfile, zipfile
import numpy as np
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):h.update(chunk)
    return h.hexdigest()

def derive():
    os.sched_setaffinity(0,{0})
    result={'schema':'MASTER45_SAVED_DAILY_NAV_DERIVATION_V1','formula':'std(ddof=1, daily_close_NAV / previous_daily_close_NAV - 1, initial previous NAV=10000) * sqrt(365)','return_annualization':False,'financial_replay':False,'account_construction':False,'source_or_target_reads':False,'CPU_affinity':sorted(os.sched_getaffinity(0)),'numerical_pools':1,'cells':[]}
    for year in (2022,2025):
        reviewdir=ROOT/f'traditional_D_full{year}_saved_results_independent_review_20261015'
        actualdir=ROOT/('traditional_D_full2022_20261015_v2_financial_attempt001' if year==2022 else 'traditional_D_full2025_20261015_financial_attempt001')
        for strategy in ('STATIC50','VOL_MANAGED_HOLD'):
            for tier in ('LOW','MID','HIGH'):
                cell=f'{year}_{strategy}_{tier}_JAN1_DEC31_D'
                rp=reviewdir/f'{cell}_REVIEW.json';review=json.loads(rp.read_text())
                p=actualdir/cell/'MINUTE.npz';expected=review['evidence']['MINUTE.npz']
                assert sha(p)==expected['SHA256'] and p.stat().st_size==expected['bytes'], cell
                with tempfile.TemporaryDirectory(prefix='master45_saved_nav_') as tmp:
                    with zipfile.ZipFile(p) as z:
                        assert set(z.namelist())=={'values.npy','columns.npy'},cell
                        target=pathlib.Path(tmp)/'values.npy'
                        with z.open('values.npy') as src, open(target,'wb') as dst:
                            for chunk in iter(lambda:src.read(1024*1024),b''):dst.write(chunk)
                        with z.open('columns.npy') as f: cols=np.load(f,allow_pickle=False)
                    values=np.load(target,mmap_mode='r',allow_pickle=False)
                    names=cols.tolist(); assert len(names)==len(set(names))
                    assert values.shape==(525600,len(names)) and values.dtype==np.dtype('float64'),cell
                    ci=names.index('close_us'); ni=names.index('nav'); start,end=review['calendar']
                    assert values[0,ci]==start+60000000 and values[-1,ci]==end,cell
                    assert np.all(np.diff(values[:,ci])==60000000),cell
                    nav=np.array(values[1439::1440,ni]);assert nav.shape==(365,) and np.all(np.isfinite(nav)) and np.all(nav>0),cell
                    prev=np.r_[10000.0,nav[:-1]]; returns=nav/prev-1.0
                    row={'cell_id':cell,'year':year,'strategy':strategy,'tier':tier,'calendar':review['calendar'],'complete_days':365,'original_MINUTE':{'path':str(p.relative_to(ROOT)),'SHA256':expected['SHA256'],'bytes':expected['bytes']},'bound_review':{'path':str(rp.relative_to(ROOT)),'SHA256':sha(rp)},'original_values_shape':list(values.shape),'original_values_dtype':values.dtype.str,'original_columns':names,'nav_column_raw_C_order_SHA256':hashlib.sha256(np.ascontiguousarray(values[:,ni]).tobytes()).hexdigest(),'daily_close_NAV_float64':nav.tolist(),'daily_simple_returns_float64':returns.tolist(),'daily_endpoints_raw_C_order_SHA256':hashlib.sha256(nav.tobytes()).hexdigest(),'daily_returns_raw_C_order_SHA256':hashlib.sha256(returns.tobytes()).hexdigest(),'realized_daily_annualized_volatility':float(np.std(returns,ddof=1)*math.sqrt(365))}
                    result['cells'].append(row)
                    del values
                print(cell,row['realized_daily_annualized_volatility'],flush=True)
    out=HERE/'SAVED_DAILY_NAV_DERIVATION.json';out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(out,sha(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rederive-from-pinned-saved-arrays',action='store_true',required=True);p.parse_args();derive()
