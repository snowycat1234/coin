"""Bounded stdlib synthetic runner; exclusive receipts, no historical interface."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent


def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(10*1024*1024,10*1024*1024))
    if hasattr(os,'sched_getaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})


def main():
    if len(sys.argv)!=1:raise SystemExit('synthetic checks accept no arguments')
    index=1
    while (HERE/f'CHECK_RECEIPT_RUN_{index:04d}.json').exists():index+=1
    out=HERE/f'CHECK_RECEIPT_RUN_{index:04d}.json'
    source_sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}
    rows=[]
    for args in (['-m','unittest','-v','test_synthetic'],['toy_demo.py']):
        start=time.monotonic()
        p=subprocess.run([sys.executable,*args],cwd=HERE,preexec_fn=limits,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'},
            text=True,capture_output=True,timeout=60)
        rows.append({'command':[sys.executable,*args],'exit_code':p.returncode,
            'elapsed_seconds':time.monotonic()-start,'stdout':p.stdout,'stderr':p.stderr})
        if p.returncode:break
    receipt={'stage':'GENERATED_SYNTHETIC_ONLY','historical_wallets':0,'downloads':0,
        'native_financial_advances':0,'source_SHA256':source_sha,'fixed_commands':rows,'one_cpu':True,
        'wall_seconds_per_command':60,'address_space_bytes':512*1024*1024,
        'max_child_RSS_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'code_tests_only_not_investment_certification':True}
    with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({'receipt':out.name,'passed':all(x['exit_code']==0 for x in rows)},indent=2))
    return 0 if all(x['exit_code']==0 for x in rows) else 1


if __name__=='__main__':raise SystemExit(main())
