"""Retrieve only pre-frozen missing original small inputs, after serial parts end."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
import hashlib,json,resource,time,urllib.request,urllib.error,zipfile
from pathlib import Path
os.sched_setaffinity(0,{7})
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RuntimeError('Redirect refused')
def main():
    stop=ROOT/'TRANSFER_STOP.json';assert not stop.exists()
    ledger=json.loads((ROOT/'PUBLIC_GIT_RESTORE_LEDGER.json').read_text());assert ledger['status']=='ALL_PARTS_VERIFIED' and len(ledger['parts'])==222
    raw=(ROOT/'FROZEN_SMALL_INPUT_ALLOWLIST.json').read_bytes();assert sha(raw)=='e12dff8b543830321431faad25c47069941d4ec0c4ff118a6cd2b21b599dba8c'
    plan=json.loads(raw);done=[];net=0;opener=urllib.request.build_opener(NoRedirect())
    assert len(plan['parts'])==4 and sum(r['bytes'] for r in plan['parts'])==plan['total_network_cap']==2635847
    for rec in plan['parts']:
        assert not stop.exists()
        p=ROOT/rec['local_path'];p.parent.mkdir(parents=True,exist_ok=True)
        mode='REUSED_VERIFIED_CACHE'
        if p.exists():b=p.read_bytes()
        else:
            url='https://raw.githubusercontent.com/snowycat1234/coin/'+rec['commit']+'/'+rec['git_path']
            try:
                with opener.open(urllib.request.Request(url,headers={'User-Agent':'pinned-small-source-only-input'}),timeout=120) as response:
                    assert response.status==200;b=response.read(rec['bytes']+1)
            except Exception as e:
                save(stop,dict(status='SMALL_INPUT_TRANSFER_STOP_NO_RETRY_NO_FALLBACK',path=rec['git_path'],url=url,error_type=type(e).__name__,error=str(e),HTTP_status=getattr(e,'code',None)));raise
            mode='PINNED_PUBLIC_GIT_READ'
        assert len(b)==rec['bytes'] and sha(b)==rec['SHA256']
        gs=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();assert not rec.get('GitBlobSHA1') or gs==rec['GitBlobSHA1']
        if not p.exists():p.write_bytes(b);net+=len(b)
        done.append(dict(rec,GitBlobSHA1=gs,transport=mode))
    assert net<=plan['total_network_cap']==2635847
    packet=ROOT/'small_inputs/PACKET.zip'
    with zipfile.ZipFile(packet) as z:
        rec=plan['cube_member'];info=z.getinfo(rec['name']);assert info.file_size==rec['bytes'];body=z.read(rec['name']);assert len(body)==rec['bytes'] and sha(body)==rec['SHA256']
        (ROOT/'small_inputs/Y2023.npz').write_bytes(body)
    features=ROOT/'small_inputs/features.zip';body=b''.join((ROOT/r['local_path']).read_bytes() for r in plan['parts'][1:]);assert len(body)==plan['features_bytes'] and sha(body)==plan['features_SHA256'];features.write_bytes(body)
    members=[]
    with zipfile.ZipFile(features) as z:
        index=json.loads(z.read('MEMBERS.json'))['files']
        for rec in plan['feature_member_allowlist']:
            if rec['name']=='MEMBERS.json':continue
            b=z.read(rec['name']);assert sha(b)==rec['SHA256']==index[rec['name']]['SHA256'];members.append(dict(name=rec['name'],bytes=len(b),SHA256=sha(b),CRC='PASS'))
    save(ROOT/'SMALL_INPUT_RESTORE_RECEIPT.json',dict(status='PASS_EXACT_SMALL_INPUTS',parts=done,new_network_bytes=net,network_cap=plan['total_network_cap'],cube=dict(path='small_inputs/Y2023.npz',**plan['cube_member'],CRC='PASS'),daily_feature_members=members,other_packet_members_opened=False,other_feature_data_members_opened=False,funding_sources_redownloaded_separately=False,targets=0,wallets=0,provider_downloads=0,CPU_affinity=list(os.sched_getaffinity(0)),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    print('PASS_EXACT_SMALL_INPUTS',net,flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        stop=ROOT/'TRANSFER_STOP.json'
        if not stop.exists():save(stop,dict(status='SMALL_INPUT_IDENTITY_OR_PRECONDITION_STOP_NO_RETRY_NO_FALLBACK',error_type=type(e).__name__,error=str(e)))
        raise
