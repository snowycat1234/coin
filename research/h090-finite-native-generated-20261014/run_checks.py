"""Fixed offline generated checks with bounded subprocesses and immutable receipts."""
from pathlib import Path
import argparse,hashlib,json,os,resource,subprocess,sys,time
HERE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_freeze():
    freeze=json.loads((HERE/'SOURCE_FREEZE.json').read_text())
    for name,want in freeze['files_SHA256'].items():
        path=HERE/name
        if path.is_symlink() or not path.is_file() or sha(path)!=want:
            raise ValueError('NEW_H090_FREEZE_MISMATCH:'+name)
    return freeze

def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    available=sorted(os.sched_getaffinity(0))
    if available:os.sched_setaffinity(0,{available[0]})

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--receipt-dir',required=True)
    p.add_argument('--freeze-sha',required=True)
    a=p.parse_args();destination=Path(a.receipt_dir)
    destination.mkdir(parents=False,exist_ok=False)
    if sha(HERE/'SOURCE_FREEZE.json')!=a.freeze_sha:raise ValueError('EXTERNAL_FREEZE_HASH_REQUIRED')
    verify_freeze()
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    tests=['test_source_normalization','test_native_control','test_capital_edges']
    if (HERE/'test_review_native_boundary.py').exists():tests.append('test_review_native_boundary')
    commands=[[sys.executable,'run_verified.py','--freeze-sha',a.freeze_sha,'tests'],
              [sys.executable,'run_verified.py','--freeze-sha',a.freeze_sha,'generated','--receipt-dir',str(destination/'generated')]]
    receipts=[]
    for index,command in enumerate(commands,1):
        started=time.monotonic()
        result=subprocess.run(command,cwd=HERE,env=env,preexec_fn=limits,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
        output=destination/f'command_{index}.txt';output.write_text(result.stdout)
        receipts.append({'command':command,'returncode':result.returncode,
            'wall_seconds':time.monotonic()-started,'output_SHA256':sha(output)})
        if result.returncode:break
    passed=len(receipts)==len(commands) and all(r['returncode']==0 for r in receipts)
    report={'schema':'H090_NATIVE_CONTROL_BOUNDED_GENERATED_RECEIPT_V1',
        'status':'PASS_GENERATED_ONLY' if passed else 'FAIL_GENERATED_ONLY',
        'source_freeze_SHA256':sha(HERE/'SOURCE_FREEZE.json'),
        'historical_wallets':0,'live_trades':0,'historical_status':'NO_GO',
        'restore_status':'NOT_IMPLEMENTED_NOT_CERTIFIED',
        'resources':{'cpu_affinity':1,'math_threads':1,'address_space_bytes':4*1024**3,
            'cpu_seconds_per_command':60,'wall_seconds_per_command':120},'commands':receipts}
    (destination/'RECEIPT.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
