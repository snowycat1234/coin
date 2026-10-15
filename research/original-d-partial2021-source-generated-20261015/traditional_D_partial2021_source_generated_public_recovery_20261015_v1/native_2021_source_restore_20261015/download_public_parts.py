"""Bounded serial source-only adaptation of original restore_public_sources.py.

Immutable part allowlist and byte cap; local identity verification; no retry,
redirect, fallback host, provider route, or concurrent request after a denial.
"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):
    os.environ[k]='1'
import hashlib,json,resource,time,urllib.request,urllib.error
from pathlib import Path
os.sched_setaffinity(0,{7})
resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
ROOT=Path(__file__).resolve().parent
ALLOW_SHA='66ee94dd8800b9999db85a32a522d7a449445f6dc69ac1899e62ab13a3600642'
raw=(ROOT/'FROZEN_SOURCE_ALLOWLIST.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==ALLOW_SHA
plan=json.loads(raw);parts=plan['parts']
assert len(parts)==222 and sum(x['bytes'] for x in parts)==171932044
STOP=ROOT/'TRANSFER_STOP.json';LEDGER=ROOT/'PUBLIC_GIT_RESTORE_LEDGER.json'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise RuntimeError('Redirect refused; immutable original host only')
opener=urllib.request.build_opener(NoRedirect())
def save(p,d):
    q=Path(str(p)+'.new');q.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n');q.replace(p)
def check(rec,b):
    assert len(b)==rec['bytes'],('SIZE',rec['git_path'],len(b))
    assert hashlib.sha256(b).hexdigest()==rec['SHA256'],('SHA256',rec['git_path'])
    got=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    assert not rec.get('GitBlobSHA1') or got==rec['GitBlobSHA1'],('GIT_BLOB',rec['git_path'])
    return got
def main():
    assert not STOP.exists(),'Persistent transfer stop exists; no automatic retry'
    begun=time.monotonic()
    ledger=json.loads(LEDGER.read_text()) if LEDGER.exists() else dict(status='RESTORING',started_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),parts=[],new_network_bytes=0,provider_downloads=0,targets=0,wallets=0)
    for i,rec in enumerate(parts):
        assert not STOP.exists()
        path=ROOT/'source'/rec['local_path'];path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():b=path.read_bytes();mode='EXISTING_VERIFIED_LOCAL_FILE'
        else:
            url='https://raw.githubusercontent.com/'+plan['repository']+'/'+rec['commit']+'/'+rec['git_path']
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'pinned-public-source-only-byte-recovery'})
                with opener.open(req,timeout=120) as response:
                    assert response.status==200
                    b=response.read(rec['bytes']+1)
                mode='PINNED_PUBLIC_GIT_READ'
            except Exception as e:
                save(STOP,dict(status='TRANSFER_STOP_NO_RETRY_NO_FALLBACK',part=i,path=rec['git_path'],url=url,error_type=type(e).__name__,error=str(e),HTTP_status=getattr(e,'code',None),verified_parts=len(ledger['parts']),verified_bytes=sum(x['bytes'] for x in ledger['parts']),provider_downloads=0,targets=0,wallets=0))
                raise
        try:gitsha=check(rec,b)
        except Exception as e:
            save(STOP,dict(status='IDENTITY_STOP',path=rec['git_path'],error=str(e)));raise
        if not path.exists():
            path.write_bytes(b);ledger['new_network_bytes']+=len(b)
        record=dict(index=i,local_path=rec['local_path'],path=rec['git_path'],bytes=len(b),SHA256=rec['SHA256'],GitBlobSHA1=gitsha,transport=mode)
        ledger['parts']=[x for x in ledger['parts'] if x['index']!=i]+[record]
        ledger['parts'].sort(key=lambda x:x['index'])
        ledger.update(verified_bytes=sum(x['bytes'] for x in ledger['parts']),elapsed_seconds=time.monotonic()-begun,manifest_SHA256=ALLOW_SHA,CPU_affinity=list(os.sched_getaffinity(0)),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        assert ledger['new_network_bytes']<=171932044
        if len(ledger['parts'])==222:ledger['status']='ALL_PARTS_VERIFIED'
        save(LEDGER,ledger)
        print(json.dumps(dict(parts=len(ledger['parts']),total=222,verified_bytes=ledger['verified_bytes'],new_network_bytes=ledger['new_network_bytes'],elapsed_seconds=round(ledger['elapsed_seconds'],2))),flush=True)
if __name__=='__main__':main()
