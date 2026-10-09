"""Public GitHub byte readback and independent reconciliation; no wallet rerun."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,urllib.request,zipfile
from pathlib import Path


def verify(state,commit):
    assert len(commit)==40 and set(commit)<=set('0123456789abcdef');prefix='research/recover-frozen-runner-20261009/fresh-initialization-native61';root=state/'public-fresh-init-native61-readback'/commit;root.mkdir(parents=True,exist_ok=True)
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    def fetch(name,limit=786433):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+prefix+'/'+name,timeout=30).read(limit))
        return p.read_bytes()
    artifact=json.loads(fetch('results/ARTIFACT.json'));manifest_raw=fetch('results/RESULT_MEMBER_HASHES.json');manifest=json.loads(manifest_raw);assert sha(manifest_raw)==artifact['member_manifest_sha256']
    def part(v):
        raw=fetch('results/'+v['path'],v['bytes']+1);assert len(raw)==v['bytes'] and sha(raw)==v['sha256'];return raw
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:parts=list(ex.map(part,artifact['parts']))
    raw=b''.join(parts);assert len(raw)==artifact['bytes'] and sha(raw)==artifact['sha256'];archive=root/artifact['filename'];archive.write_bytes(raw);extracted=root/'extracted';extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())=={v['path'] for v in manifest['files']}|{'RESULT_MEMBER_HASHES.json'} and z.read('RESULT_MEMBER_HASHES.json')==manifest_raw
        for v in manifest['files']:
            data=z.read(v['path']);assert len(data)==v['bytes'] and sha(data)==v['sha256'];p=extracted/v['path'];assert p.resolve().is_relative_to(extracted.resolve());p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():assert p.read_bytes()==data
            else:p.write_bytes(data)
    result=json.loads((extracted/'RESULTS.json').read_bytes());arm='EXP_FRESH_DATE_512';original=state/'temporal-fresh-init-native61'/arm;unchanged=0;public=[]
    for v in manifest['files']:
        prefix_account='accounts/'+arm+'/'
        if v['path'].startswith(prefix_account):
            p=original/v['path'][len(prefix_account):];assert p.stat().st_size==v['bytes'] and sha(p.read_bytes())==v['sha256'];unchanged+=1
    for name in ('results/RESULTS.json','results/README.md','ADAPTER_CONTRACT.json','EXP_FRESH_DATE_512.json','MANIFEST.json','READINESS.json','RECOVERY.json','PUBLIC_PLAN_READBACK.json'):
        data=fetch(name);local=extracted/name.removeprefix('results/') if name.startswith('results/') else extracted/'plans'/name;assert data==local.read_bytes();public.append(dict(path=name,bytes=len(data),SHA256=sha(data)))
    for name in ('summary.json','INDEPENDENT_AUDIT.json','REQUEST_GATE.json'):
        data=fetch('results/'+arm+'/'+name);p=extracted/'accounts'/arm/('account/summary.json' if name=='summary.json' else name);assert data==p.read_bytes();public.append(dict(path='results/'+arm+'/'+name,bytes=len(data),SHA256=sha(data)))
    data=fetch('results/'+arm+'/RESULT.json');assert json.loads(data)==result['accounts'][arm];public.append(dict(path='results/'+arm+'/RESULT.json',bytes=len(data),SHA256=sha(data)))
    warm=state/'temporal-weighting512-native61/EXP_GRU64_WEIGHT_DATE'
    for name,key in [('account/summary.json','summary_SHA256'),('INDEPENDENT_AUDIT.json','audit_SHA256'),('EXECUTION.json','execution_SHA256')]:assert sha((warm/name).read_bytes())==result['reused_warm_journal_hashes'][key]
    code="import json;from pathlib import Path;import verify_native61;print(json.dumps(verify_native61.verify(Path('accounts/EXP_FRESH_DATE_512'),state=Path("+repr(str(state))+"))))"
    env=os.environ.copy();env.update(PYTHONPATH=str(state/'deps'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1');audit=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=extracted,env=env));assert audit['status'].startswith('PASS_') and audit['minutes']==87840 and audit['terminal_paid_flat'] and audit['actual_input_check']['status']=='PASS_ACTUAL_FILLS_CAPACITY_FEES_MARKS_AND_FUNDING'
    receipt=dict(status='PASS_PUBLIC_PART_MEMBER_PLAN_AND_ORIGINAL_FRESH_JOURNAL_BYTES_AND_FINANCIAL_ACTUAL_INPUT_AUDIT',artifact_commit=commit,archive_SHA256=artifact['sha256'],archive_bytes=artifact['bytes'],parts=len(parts),ZIP_members=len(manifest['files'])+1,original_fresh_account_files_byte_identical=unchanged,retained_warm_journal_hashes_unchanged=True,public_small_files=public,portable_actual_input_financial_audit=audit,wallets_run=0,fits=0,model_inference=0,provider_downloads=0);(root/'PUBLIC_READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ('public_small_files','portable_actual_input_financial_audit')}),flush=True);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--commit',required=True);a=p.parse_args();verify(a.state,a.commit)
