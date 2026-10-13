"""Diagnose existing saved daily input availability without producing targets."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import datetime,hashlib,io,json,time,zipfile
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86400000000;START=1609459200000000;END=1640995200000000
CUBE=Path(os.environ.get('COIN_CUBE_PATH',str(BASE/'coin_cs_sma_recovery_20261013/inputs/Y2023.npz')))
FEATURES=Path(os.environ.get('COIN_FEATURES_PATH',str(BASE/'coin_native_half_mix_20261013/source/2023_FUND/features.zip')))
def sha(b):return hashlib.sha256(b).hexdigest()
def utc(t):return datetime.datetime.fromtimestamp(int(t)/1e6,datetime.UTC).isoformat()
def main():
    begin=time.monotonic();yi=json.loads((ROOT/'evidence/Y2021_INDEX.json').read_text());bindings={r['member']:r['SHA256'] for r in yi['cached_inputs']['source_member_bindings']}
    assert sha(CUBE.read_bytes())=='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
    assert sha(FEATURES.read_bytes())=='bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'
    with np.load(CUBE,allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==S;all_t=z['close_available_us'];scope=(all_t>=START-199*DAY)&(all_t<=END);t=all_t[scope].copy();p=z['close'][scope].copy()
    assert np.array_equal(t,np.arange(t[0],t[-1]+DAY,DAY))
    decisions=np.arange(START,END,DAY,dtype=np.int64);masks={};rec=[]
    with zipfile.ZipFile(FEATURES) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for j,s in enumerate(S):
            name='source_tables_not_model_inputs/daily_features/'+s+'.parquet';body=z.read(name);assert sha(body)==bindings[name]==members[name]['SHA256']
            f=pq.read_table(io.BytesIO(body),columns=['dt','open','high','low','close','complete_kline']).to_pandas();a=f.dt.astype('int64').to_numpy()//1000+DAY;c=f.close.to_numpy();valid=f.complete_kline.to_numpy()&np.isfinite(c)&(c>0)
            assert np.array_equal(a,np.arange(a[0],a[-1]+DAY,DAY));k=np.searchsorted(a,t);assert (k<len(a)).all() and np.array_equal(a[k],t)
            expected=np.where(valid[k],c[k],np.nan);np.testing.assert_array_equal(expected,p[:,j]);finite=np.isfinite(expected);assert expected[finite].tobytes()==p[finite,j].tobytes()
            first=int(a[np.flatnonzero(valid)[0]]);windows={}
            for n in (21,31,200):
                ready=np.asarray([ix>=n-1 and a[ix]==at and valid[ix-n+1:ix+1].all() for at in decisions for ix in [int(np.searchsorted(a,at))]],dtype=bool)
                masks[s+'_'+str(n)+'close']=ready
                windows[str(n)+'close']=dict(ready_decisions=int(ready.sum()),first_ready_decision_UTC=utc(decisions[np.flatnonzero(ready)[0]]) if ready.any() else None,unready_decisions=int((~ready).sum()))
            at=int(np.searchsorted(a,START));prefix=a[at-199:at+1];prefix_valid=valid[at-199:at+1]
            rec.append(dict(symbol=s,daily_features_member_SHA256=sha(body),cube_close_exact_parity_cells=len(t),first_complete_daily_close_available_UTC=utc(first),first_2021_200close_window_available_UTC=[utc(prefix[0]),utc(prefix[-1])],first_2021_200close_missing_count=int((~prefix_valid).sum()),first_2021_200close_missing_available_UTC=[utc(x) for x in prefix[~prefix_valid]],windows=windows))
    masks['decision_us']=decisions;masks['symbol_order']=np.asarray(S);masks['CORE5_21close']=np.logical_and.reduce([masks[s+'_21close'] for s in S]);masks['CORE5_31close']=np.logical_and.reduce([masks[s+'_31close'] for s in S]);masks['CORE5_200close']=np.logical_and.reduce([masks[s+'_200close'] for s in S])
    path=ROOT/'CORE5_WARMUP_MASKS.npz';np.savez_compressed(path,**masks)
    result=dict(status='PASS_EXISTING_SHA_BOUND_DAILY_CUBE_WARMUP_DIAGNOSTIC',calendar_UTC=['2021-01-01T00:00:00+00:00','2022-01-01T00:00:00+00:00'],symbol_order=list(S),cube=dict(path=os.path.relpath(CUBE,BASE),SHA256=sha(CUBE.read_bytes()),days=len(t),availability_UTC=[utc(t[0]),utc(t[-1])]),saved_source_features=dict(path=os.path.relpath(FEATURES,BASE),SHA256=sha(FEATURES.read_bytes())),symbols=rec,CORE5_21close_ready_decisions=int(masks['CORE5_21close'].sum()),CORE5_31close_ready_decisions=int(masks['CORE5_31close'].sum()),CORE5_200close_ready_decisions=int(masks['CORE5_200close'].sum()),CORE5_200close_first_ready_UTC=utc(decisions[np.flatnonzero(masks['CORE5_200close'])[0]]),mask_file=dict(path=path.name,bytes=path.stat().st_size,SHA256=sha(path.read_bytes())),warmup_authority='Exact saved public daily_features close/complete_kline parity with the existing cube. Pre2021 minute ZIPs were not reacquired or independently minute-revalidated. Full2021 minute-to-cube parity remains a separate gate.',fixed_fullfive_200close_on_Jan1_admitted=False,original_dynamic_masks_preserved=True,targets_generated=0,wallets_created=0,historical_runs=0,provider_downloads=0,Library_calls=0,retained_2026_opened=0,elapsed_seconds=time.monotonic()-begin,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,CPU_affinity=list(os.sched_getaffinity(0)),AS_limit_bytes=2*1024**3)
    (ROOT/'WARMUP_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n');print(json.dumps({k:result[k] for k in ('status','CORE5_21close_ready_decisions','CORE5_31close_ready_decisions','CORE5_200close_ready_decisions','CORE5_200close_first_ready_UTC','peak_RSS_bytes','elapsed_seconds')}),flush=True)
if __name__=='__main__':main()
