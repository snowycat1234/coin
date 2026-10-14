"""Bound synthetic tests/toy/code checks; fixed commands, no history options."""
from __future__ import annotations
import json
import argparse
import os
from pathlib import Path
import resource
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
RSS_LIMIT=2_000_000_000
AS_LIMIT=4_000_000_000
WALL=120


def child_limits():
    resource.setrlimit(resource.RLIMIT_AS,(AS_LIMIT,AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    if hasattr(os,'sched_getaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})


def rss(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):return int(line.split()[1])*1024
    except FileNotFoundError:pass
    return 0


def main():
    parser=argparse.ArgumentParser(description='Only fixed synthetic/source-code commands')
    parser.add_argument('--receipt-dir',default='toy_receipts')
    args=parser.parse_args()
    if not re.fullmatch(r'toy_receipts(?:_attempt[0-9]{3})?',args.receipt_dir):
        parser.error('Receipt directory must be an owned toy_receipts basename')
    output=HERE/args.receipt_dir
    output.mkdir(exist_ok=False)
    commands=[('source_preflight',[sys.executable,'preflight.py']),
              ('unit_tests',[sys.executable,'-m','unittest','-v','test_paired_buffer']),
              ('toy',[sys.executable,'run_toy.py']),
              ('toy_scaling',[sys.executable,'benchmark_toy.py'])]
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
             NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    records=[]
    for label,command in commands:
        began=time.monotonic();peak=0;stop=None
        with (output/(label+'.txt')).open('x') as log:
            process=subprocess.Popen(command,cwd=HERE,env=env,stdout=log,stderr=subprocess.STDOUT,
                                     preexec_fn=child_limits)
            while process.poll() is None:
                peak=max(peak,rss(process.pid))
                if peak>RSS_LIMIT:stop='RSS_LIMIT'
                elif time.monotonic()-began>WALL:stop='WALL_LIMIT'
                if stop:process.kill();break
                time.sleep(.02)
            code=process.wait()
        record={'stage':label,'command':command,'exit_code':code,'stop_reason':stop,
                'elapsed_seconds':time.monotonic()-began,'sampled_peak_RSS_bytes':peak,
                'RSS_stop_bytes':RSS_LIMIT,'AS_limit_bytes':AS_LIMIT,'CPU_limit_seconds':60,
                'wall_limit_seconds':WALL,'CPU_affinity_count':1,'threads':1,
                'synthetic_only':True,'historical_array_reads':0,'historical_wallets':0,
                'financial_advances':0,'fits':0,'market_requests':0}
        records.append(record)
        print(json.dumps(record,sort_keys=True))
        if code or stop:break
    result={'status':'PASS_BOUNDED_SYNTHETIC_SOURCE_CHECKS' if len(records)==4 and all(r['exit_code']==0 and r['stop_reason'] is None for r in records) else 'FAIL_BOUNDED_SYNTHETIC_SOURCE_CHECKS',
            'records':records,'historical_GO':False}
    (output/'RESOURCE_RECEIPT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    if result['status'].startswith('FAIL'):raise SystemExit(1)


if __name__=='__main__':main()
