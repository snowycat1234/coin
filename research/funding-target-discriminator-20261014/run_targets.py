"""One reviewed four-calendar TARGET-ONLY pass; exact parent GO required."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import time
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[name]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import numpy as np
from target_core import HERE,DAY,SYMBOLS,paired_targets
from inputs import load,frozen_funding_provider


def sha(raw):return hashlib.sha256(raw).hexdigest()


def clean(value):
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,np.generic):return clean(value.item())
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,float) and not np.isfinite(value):return None
    return value


def write(path,value):path.write_text(json.dumps(clean(value),indent=2,allow_nan=False)+'\n')


def runtime_guard(begun):
    assert time.monotonic()-begun<120,'WALL_TIME_STOP'
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=2_000_000_000,'RSS_STOP'


def preserve_failure(output,preexisting,error):
    if not preexisting and output.exists() and not (output/'SUMMARY.json').exists():
        write(output/'ATTEMPT_FAILURE.json',{'status':'FAILED_ATTEMPT_PRESERVED','error_type':type(error).__name__,'automatic_retry':False,'details':'Detailed exception log retained locally; public receipt contains no absolute paths.'})


def run(go,output):
    assert not output.exists(),'Preserve every attempt; no overwrite'
    manifest_raw=(HERE/'PREPARATION_MANIFEST.json').read_bytes();manifest=json.loads(manifest_raw)
    permission=json.loads(go.read_bytes())
    assert permission['action']=='ONE_FOUR_YEAR_CSH_TARGET_IDENTITY_PASS_2021_2023_2024_2025'
    assert permission['manifest_sha256']==sha(manifest_raw)
    review_raw=(HERE/'PREPARATION_REVIEW_RECEIPT.json').read_bytes();review=json.loads(review_raw)
    assert sha(review_raw)==permission['review_receipt_sha256']
    assert review['manifest_sha256']==sha(manifest_raw) and review['status']=='PASS_EXACT_TARGET_PREPARATION_NO_ECONOMICS'
    assert permission['wallets']==permission['fits']==permission['economic_outcome_arrays_read']==0
    assert permission['funding_scale']=='CONDITIONAL_RAW_FRACTION1'
    for n,pin in manifest['files'].items():
        raw=(HERE/n).read_bytes();assert sha(raw)==pin['sha256'] and len(raw)==pin['bytes'],n
    assert os.environ.get('FUNDING_TARGET_OUTER_TIMEOUT_SECONDS')=='120','Mandatory whole-process timeout'
    resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000))
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    assert shutil.disk_usage(HERE).free>=16_106_127_360,'DISK_RESERVE_STOP'
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if ':' in l and l.split()[1].isdigit()}
    assert mem['SwapTotal']==0 and mem['MemTotal']-mem['MemAvailable']<=8_000_000_000,'MEMORY_OR_SWAP_STOP'
    output.mkdir();write(output/'ATTEMPT_START.json',{'action':permission['action'],'manifest_sha256':sha(manifest_raw),'review_receipt_sha256':sha(review_raw),'parent_go_sha256':sha(go.read_bytes()),'wallets':0,'economic_outcome_arrays_read':0})
    begun=time.monotonic();years={};rank_lines=[];daily_lines=[]
    for year,(t,p,d,hold,mask,streams,_,_) in load().items():
        runtime_guard(begun)
        targets,cov,proof=paired_targets(t,p,d,hold,mask,frozen_funding_provider(t,p,streams))
        runtime_guard(begun)
        a,b=targets['PRICE_ONLY'],targets['FUNDING_ADJUSTED'];unknown=proof['daily_required_source_not_ready'];ready=~unknown
        different=ready&np.any(a!=b,axis=1)
        for w in (a,b):
            assert np.isfinite(w[ready]).all() and np.abs(w[ready]).max()<=.3+1e-12 and np.abs(w[ready]).sum(1).max()<=.6+1e-12
        np.savez_compressed(output/f'Y{year}_TARGETS.npz',decision_us=d,symbol_order=np.asarray(SYMBOLS),
            PRICE_ONLY_CSH=a,FUNDING_ADJUSTED_CSH=b,annual_covariance=cov,
            original_daily_admission=proof['daily_original_admission'],required_source_not_ready=unknown,
            owning_rank_us=np.asarray(proof['CS']['owning_rank_us'],np.int64),owning_rank_source_known=np.asarray(proof['CS']['owning_rank_source_known'],bool))
        for record in proof['CS']['rank_records']:rank_lines.append(dict(year=year,**record))
        for i,at in enumerate(d):
            daily_lines.append({'year':year,'decision_us':int(at),'owning_rank_us':proof['CS']['owning_rank_us'][i],
                'original_daily_admission':bool(proof['daily_original_admission'][i]),'source_not_ready':bool(unknown[i]),
                'target_changed':bool(different[i]),'sized':{arm:proof['risk'][arm]['risk'][i]['arms']['STATIC50'] for arm in targets}})
        intervals=[]
        for i in np.flatnonzero(different):
            if not intervals or int(d[i])!=intervals[-1][1]:intervals.append([int(d[i]),int(d[i]+DAY)])
            else:intervals[-1][1]=int(d[i]+DAY)
        years[str(year)]={'calendar_days':len(d),'paired_source_ready_days':int(ready.sum()),
            'original_daily_admitted_days':int(proof['daily_original_admission'].sum()),
            'required_source_not_ready_days':int(unknown.sum()),'exact_CSH_target_changed_days':int(different.sum()),
            'exact_CSH_target_unchanged_days':int((ready&~different).sum()),'changed_intervals_us':intervals,
            'changed_asset_days':int(np.sum((a[ready]!=b[ready]))),
            'max_absolute_target_difference':float(np.max(np.abs(a[ready]-b[ready]),initial=0)),
            'unready_owning_rank_days_that_never_feed_admitted_output':int((~np.asarray(proof['CS']['owning_rank_source_known'],bool)&~proof['daily_original_admission']).sum()),
            'conclusion':'INCONCLUSIVE_REQUIRED_OWNING_RANK_SOURCE' if unknown.any() else ('TARGETS_DIFFER_CONDITIONAL' if different.any() else 'EXACT_TARGET_NOOP_VS_SAME_LAG_CONTROL_CONDITIONAL')}
    for name,records in [('RAW_CS_RANKS.jsonl',rank_lines),('DAILY_TARGET_PROOF.jsonl',daily_lines)]:
        raw=b''.join((json.dumps(clean(r),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode() for r in records)
        (output/name).write_bytes(raw)
    runtime_guard(begun)
    summary={'status':'COMPLETED_ONE_FULL_FOUR_YEAR_EXACT_TARGET_ONLY_PASS','years':years,
        'source_manifest_sha256':sha(manifest_raw),'review_receipt_sha256':sha(review_raw),'parent_go_sha256':sha(go.read_bytes()),
        'funding_scale':'CONDITIONAL_RAW_FRACTION1','completeness_authority':'PINNED_PROJECT_ARCHIVE_OBSERVATION_SET_ONLY_PROVIDER_UNCERTIFIED',
        'elapsed_seconds':time.monotonic()-begun,'historical_target_passes':1,'wallets':0,'fits':0,'economic_outcome_arrays_read':0,
        'interpretation':'Same-lag exact CSH target identity only. No future returns, funding cash, costs, turnover, profitability, wallet identity or original-unlagged improvement evaluated.'}
    summary_raw=(json.dumps(clean(summary),indent=2,allow_nan=False)+'\n').encode()
    assert sum(p.stat().st_size for p in output.iterdir())+len(summary_raw)<=10_000_000,'OUTPUT_BUDGET_STOP'
    (output/'SUMMARY.json').write_bytes(summary_raw)
    print(summary_raw.decode())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parent-go',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    preexisting=args.output.exists()
    try:run(args.parent_go,args.output)
    except Exception as e:
        preserve_failure(args.output,preexisting,e)
        raise
