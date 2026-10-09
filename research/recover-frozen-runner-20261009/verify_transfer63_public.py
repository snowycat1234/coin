"""Read back public GitHub result bytes and reconcile unchanged journals offline."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,urllib.request,zipfile
from pathlib import Path


def verify(state,fold,commit):
    assert len(commit)==40 and set(commit)<=set('0123456789abcdef')
    public='research/recover-frozen-runner-20261009/prequential2023/'+fold;root=state/'public-prequential2023-readback'/fold/commit;root.mkdir(parents=True,exist_ok=True)
    def sha(raw):return hashlib.sha256(raw).hexdigest()
    def fetch(name,limit=786433):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+public+'/'+name,timeout=30).read(limit))
        return p.read_bytes()
    artifact=json.loads(fetch('results/ARTIFACT.json'));manifest_raw=fetch('results/RESULT_MEMBER_HASHES.json');manifest=json.loads(manifest_raw);assert sha(manifest_raw)==artifact['member_manifest_sha256']
    def part(v):
        raw=fetch('results/'+v['path'],v['bytes']+1);assert len(raw)==v['bytes'] and sha(raw)==v['sha256'];return raw
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:chunks=list(ex.map(part,artifact['parts']))
    raw=b''.join(chunks);assert len(raw)==artifact['bytes'] and sha(raw)==artifact['sha256'];archive=root/artifact['filename'];archive.write_bytes(raw);extracted=root/'extracted';extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())=={v['path'] for v in manifest['files']}|{'RESULT_MEMBER_HASHES.json'}
        assert z.read('RESULT_MEMBER_HASHES.json')==manifest_raw
        for v in manifest['files']:
            data=z.read(v['path']);assert len(data)==v['bytes'] and sha(data)==v['sha256'];p=extracted/v['path'];assert p.resolve().is_relative_to(extracted.resolve());p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():assert p.read_bytes()==data
            else:p.write_bytes(data)
    result=json.loads((extracted/'RESULTS.json').read_bytes());contract=json.loads(fetch('ADAPTER_CONTRACT.json'));assert fetch('CANONICAL_CONTEXTS63.npz')==(extracted/'CANONICAL_CONTEXTS63.npz').read_bytes()
    files=[]
    for name in ('ADAPTER_CONTRACT.json','CONTEXT_READY.json','results/README.md','results/RESULTS.json'):
        data=fetch(name);local=extracted/(name.removeprefix('results/'));assert data==local.read_bytes();files.append(dict(path=name,bytes=len(data),SHA256=sha(data)))
    audits={};originals=0
    for arm,r in result['accounts'].items():
        for name in ('RESULT.json','summary.json','INDEPENDENT_AUDIT.json','REQUEST_GATE.json'):
            data=fetch('results/'+arm+'/'+name)
            local=(extracted/'accounts'/arm/'account/summary.json') if name=='summary.json' else (extracted/'accounts'/arm/name)
            if name=='RESULT.json':assert json.loads(data)==r
            else:assert data==local.read_bytes()
            files.append(dict(path='results/'+arm+'/'+name,bytes=len(data),SHA256=sha(data)))
        for name in (arm+'.json','MANIFEST_'+arm+'.json'):
            data=fetch('plans/'+name);assert data==(extracted/'plans'/name).read_bytes();files.append(dict(path='plans/'+name,bytes=len(data),SHA256=sha(data)))
        code="import json;from pathlib import Path;import verify_native61;print(json.dumps(verify_native61.verify(Path("+repr('accounts/'+arm)+"),calendar="+repr(contract['calendar'])+")))"
        env=os.environ.copy();env.update(PYTHONPATH=str(state/'deps'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1')
        audit=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=extracted,env=env));assert audit['status'].startswith('PASS_') and audit['minutes']==90720 and audit['terminal_paid_flat'];audits[arm]=audit
        original=state/'prequential2023-native'/fold/arm
        for v in manifest['files']:
            prefix='accounts/'+arm+'/'
            if v['path'].startswith(prefix):
                p=original/v['path'][len(prefix):];assert p.stat().st_size==v['bytes'] and sha(p.read_bytes())==v['sha256'];originals+=1
    receipt=dict(status='PASS_PUBLIC_PART_MEMBER_PLAN_CONTEXT_AND_ORIGINAL_JOURNAL_BYTES_AND_PORTABLE_FINANCIAL_AUDITS',fold=fold,artifact_commit=commit,archive_SHA256=artifact['sha256'],archive_bytes=artifact['bytes'],parts=len(chunks),ZIP_members=len(manifest['files'])+1,original_account_files_byte_identical=originals,public_small_files=files,portable_financial_audits=audits,wallets_run=0,fits=0,provider_downloads=0)
    (root/'PUBLIC_READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ('public_small_files','portable_financial_audits')}),flush=True);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--fold',choices=('FOLD_20230703','FOLD_20231002'),required=True);p.add_argument('--commit',required=True);a=p.parse_args();verify(a.state,a.fold,a.commit)
