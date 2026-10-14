"""Fixed generated-only finite checks under bounded local subprocess resources."""
from pathlib import Path
import argparse,hashlib,json,os,resource,subprocess,sys,time
HERE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    cpus=sorted(os.sched_getaffinity(0))
    if cpus:os.sched_setaffinity(0,{cpus[0]})

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-sha',required=True);p.add_argument('--receipt-dir',required=True)
    a=p.parse_args();destination=Path(a.receipt_dir)
    if sha(HERE/'SOURCE_FREEZE.json')!=a.freeze_sha:raise ValueError('EXTERNAL_FINITE_FREEZE_REQUIRED')
    frozen=json.loads((HERE/'SOURCE_FREEZE.json').read_text())
    for name,want in frozen['files_SHA256'].items():
        path=HERE/name
        if path.is_symlink() or not path.is_file() or sha(path)!=want:raise ValueError('FINITE_FREEZE_MISMATCH:'+name)
    destination.mkdir(parents=False,exist_ok=False)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    prefix=[sys.executable,'run_finite_verified.py','--freeze-sha',a.freeze_sha]
    commands=[prefix+['tests'],prefix+['demo','--receipt-dir',str(destination/'demo')],
        prefix+['witnesses','--receipt-dir',str(destination/'owner_boundaries')]]
    receipts=[]
    for i,command in enumerate(commands,1):
        started=time.monotonic();failure=None
        try:
            result=subprocess.run(command,cwd=HERE,env=env,preexec_fn=limits,stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,text=True,timeout=120)
            output=result.stdout;code=result.returncode
        except subprocess.TimeoutExpired as error:
            output=error.stdout or ''
            if isinstance(output,bytes):output=output.decode(errors='replace')
            failure='WALL_TIMEOUT';code=124
        path=destination/f'command_{i}.txt';path.write_text(output)
        receipts.append({'command':command,'returncode':code,'wall_seconds':time.monotonic()-started,
            'output_SHA256':sha(path),'failure':failure})
        if code:break
    passed=len(receipts)==len(commands) and all(row['returncode']==0 for row in receipts)
    report={'schema':'H090_FINITE_NATIVE_BOUNDED_GENERATED_RECEIPT_V1',
        'status':'PASS_GENERATED_ONLY' if passed else 'FAIL_GENERATED_ONLY',
        'source_freeze_SHA256':a.freeze_sha,'immutable_CONTROL_freeze_SHA256':frozen['immutable_control_freeze_SHA256'],
        'historical_wallets':0,'historical_array_parses':0,'live_trades':0,'historical_status':'NO_GO',
        'checksum_only_already_public_target_archives':2,'checksum_only_target_bytes':50586,
        'full_recovery':'NO_GO_NOT_IMPLEMENTED',
        'resources':{'CPU_affinity_count':1,'math_threads':1,'address_space_bytes':4*1024**3,
            'CPU_seconds_per_command':60,'wall_seconds_per_command':120},'commands':receipts,
        'evidence_files_SHA256':{str(p.relative_to(destination)):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()}}
    (destination/'RECEIPT.json').write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False));return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
