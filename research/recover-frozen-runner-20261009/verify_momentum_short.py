"""Reuse mature unchanged independent financial and actual-source auditors."""
import argparse,json,os
from pathlib import Path
import resource,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--state',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000))
    e=json.loads((a.directory/'EXECUTION.json').read_bytes())
    if e['case']=='MAYJUN2024':
        from verify_native61 import verify
    else:
        from verify_short_regimes import verify
    r=verify(a.directory,a.state)
    if a.write:
        with (a.directory/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:r[k] for k in ('status','minutes','maximum_NAV_error_USDT','maximum_wallet_error_USDT','terminal_paid_flat','liquidations')}|dict(actual_input_check=r.get('actual_input_check'))),flush=True)
