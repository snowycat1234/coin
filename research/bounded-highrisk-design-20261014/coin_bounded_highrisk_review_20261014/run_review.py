"""Bounded independent generated-only checks with source-before/after identities."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parent/'coin_bounded_highrisk_design_20261014'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def limits():
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))


def main():
    name=sys.argv[1] if len(sys.argv)==2 else 'attempt001'
    if not name.startswith('attempt') or not name.isalnum(): raise SystemExit('Local unique attempt name required')
    out=HERE/name; out.mkdir(exist_ok=False)
    snapshot=json.loads((HERE/'SOURCE_SNAPSHOT.json').read_text())
    before={name:sha(DESIGN/name) for name in snapshot['files']}
    if before!=snapshot['files']: raise SystemExit('Source changed before independent review')
    receipt={'status':'RUNNING','scope':'GENERATED_ONLY_NOT_HISTORICAL_GO',
        'historical_runs':0,'market_reads':0,'downloads':0,'external_publication':0,
        'source_before':before,'commands':[],
        'bounds':{'cpus':1,'math_threads':1,'address_space_bytes':4*1024**3,
            'rss_stop_bytes':2*1024**3,'cpu_seconds_per_command':60,'wall_seconds_per_command':120}}
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    commands=(('designer_tests.txt',DESIGN,[sys.executable,'-m','unittest','-v','test_bounded_highrisk']),
        ('independent_tests.txt',HERE,[sys.executable,'-m','unittest','-v','test_adversarial']),
        ('fixed_toy.json',DESIGN,[sys.executable,'run_toy.py']))
    try:
        for output,cwd,command in commands:
            start=time.monotonic(); maxrss=0; stopped=None
            with (out/output).open('w') as stream:
                process=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,preexec_fn=limits)
                while process.poll() is None:
                    try:
                        status=Path(f'/proc/{process.pid}/status').read_text()
                        rss=int(next(row.split()[1] for row in status.splitlines() if row.startswith('VmRSS:')))*1024
                        maxrss=max(maxrss,rss)
                    except (FileNotFoundError,StopIteration,ProcessLookupError): pass
                    if time.monotonic()-start>120 or maxrss>2*1024**3:
                        stopped='WALL_LIMIT' if time.monotonic()-start>120 else 'RSS_LIMIT'; process.kill(); break
                    time.sleep(.02)
                code=process.wait()
            receipt['commands'].append({'command':command,'returncode':code,'stopped':stopped,
                'wall_seconds':time.monotonic()-start,'sampled_max_rss_bytes':maxrss,
                'output':output,'output_sha256':sha(out/output)})
            if code or stopped: raise RuntimeError('Synthetic check failed: '+output)
        receipt['status']='PASS_FIXED_SOURCE_SYNTHETIC_ONLY'
    except BaseException as error:
        receipt['status']='FAIL_FIXED_SOURCE_SYNTHETIC_ONLY'; receipt['failure']=str(error); raise
    finally:
        receipt['source_after']={name:sha(DESIGN/name) for name in snapshot['files']}
        receipt['source_unchanged']=receipt['source_after']==before
        if not receipt['source_unchanged']: receipt['status']='FAIL_SOURCE_CHANGED_DURING_REVIEW'
        receipt['reviewer_files']={p.name:sha(p) for p in (HERE/'test_adversarial.py',HERE/'run_review.py',HERE/'SOURCE_SNAPSHOT.json')}
        (out/'REVIEW_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,indent=2,sort_keys=True))
    if not receipt['source_unchanged']: raise SystemExit(1)

if __name__=='__main__': main()
