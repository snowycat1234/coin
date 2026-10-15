"""Continue this authorized source restoration to source-qualified completion."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
import hashlib,json,resource,subprocess,sys,time
from pathlib import Path
os.sched_setaffinity(0,{7})
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
ROOT=Path(__file__).resolve().parent;BEGIN=time.monotonic()
def save(path,data):
    temp=Path(str(path)+'.new');temp.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');temp.replace(path)
def main():
    stop=ROOT/'TRANSFER_STOP.json';ledger=ROOT/'PUBLIC_GIT_RESTORE_LEDGER.json'
    while True:
        assert not stop.exists(),'Transfer stop: no retry or fallback'
        state=json.loads(ledger.read_text())
        if state['status']=='ALL_PARTS_VERIFIED':break
        time.sleep(15)
    assert len(state['parts'])==222 and state['verified_bytes']==171932044
    pins=json.loads((ROOT/'SOURCE_ADAPTER_CODE_PINS.json').read_text())
    for rec in pins:
        p=ROOT/rec['path'];assert p.stat().st_size==rec['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==rec['SHA256'],rec['path']
    env=dict(os.environ,COIN_CUBE_PATH=str(ROOT/'small_inputs/Y2023.npz'),COIN_FEATURES_PATH=str(ROOT/'small_inputs/features.zip'),COIN_2021_SOURCE_OUT=str(ROOT/'prepared_2021'),COIN_SOURCE_READER_LEDGER_PATH=str(ROOT/'ACTUAL_SOURCE_READ_PROJECTIONS.jsonl'))
    stages=['restore_small_public_inputs.py','assemble_offline.py','audit_warmup.py','audit_funding.py','prepare_full_2021.py','verify_few_boundaries.py','qualify_apr_dec_candidate.py'];records=[]
    for name in stages:
        assert not stop.exists()
        print('SOURCE_STAGE_START',name,flush=True);started=time.monotonic();log=ROOT/(name.removesuffix('.py')+'.log');peak=0;observed=set();samples=0
        with log.open('wb') as out:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/name)],env=env,stdout=out,stderr=subprocess.STDOUT)
            while child.poll() is None:
                try:
                    status=Path('/proc')/str(child.pid)/'status'
                    for line in status.read_text().splitlines():
                        if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024)
                    for t in (Path('/proc')/str(child.pid)/'task').iterdir():
                        aff=tuple(sorted(os.sched_getaffinity(int(t.name))));observed.add(aff)
                        if aff!=(7,):child.kill();raise RuntimeError('Unexpected source helper affinity:'+str(aff))
                    samples+=1
                    if peak>2*1024**3:child.kill();raise RuntimeError('Source RSS budget exceeded')
                except (FileNotFoundError,ProcessLookupError):pass
                time.sleep(.25)
            rc=child.wait()
        rec=dict(stage=name,returncode=rc,log=log.name,elapsed_seconds=time.monotonic()-started,peak_sampled_RSS_bytes=peak,thread_affinities=[list(a) for a in sorted(observed)],resource_samples=samples)
        records.append(rec);save(ROOT/'SOURCE_PIPELINE_RECEIPT.json',dict(status='RUNNING' if rc==0 else 'SOURCE_STAGE_STOP',stages=records,source_only=True,targets=0,wallets=0,historical_runs=0,provider_downloads=0))
        print('SOURCE_STAGE_FINISH',name,'returncode',rc,'elapsed',round(rec['elapsed_seconds'],2),'RSS',peak,flush=True)
        if rc!=0:raise RuntimeError('Source stage stopped; inspect '+str(log))
    save(ROOT/'SOURCE_PIPELINE_RECEIPT.json',dict(status='PASS_SOURCE_PIPELINE_2021_ONLY',stages=records,total_elapsed_seconds=time.monotonic()-BEGIN,source_only=True,targets=0,wallets=0,historical_runs=0,provider_downloads=0,CPU_affinity=[7],numerical_pools=1,max_RSS_bytes=2*1024**3,max_AS_bytes=4*1024**3))
    print('PASS_SOURCE_PIPELINE_2021_ONLY',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        save(ROOT/'PIPELINE_STOP.json',dict(status='SOURCE_PIPELINE_STOP',error_type=type(e).__name__,error=str(e),targets=0,wallets=0,historical_runs=0))
        raise
