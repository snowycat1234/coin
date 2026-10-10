"""Public byte recovery, independent actual-input audit and original state restore. No rollout."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,urllib.request,zipfile
from pathlib import Path
import q4_native92 as run


def verify(state,arm,commit):
    assert len(commit)==40 and set(commit)<=set('0123456789abcdef');prefix=run.PUBLIC.relative_to(run.REPO).as_posix()+'/results/'+arm;root=state/'public-q4-native92-readback'/arm/commit;root.mkdir(parents=True,exist_ok=True);digest=lambda raw:hashlib.sha256(raw).hexdigest()
    def fetch(name,limit=786433):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+prefix+'/'+name,timeout=30).read(limit))
        return p.read_bytes()
    artifact=json.loads(fetch('ARTIFACT.json'));raw_manifest=fetch('RESULT_MEMBER_HASHES.json');manifest=json.loads(raw_manifest);assert digest(raw_manifest)==artifact['member_manifest_sha256']
    def part(v):
        raw=fetch(v['path'],v['bytes']+1);assert len(raw)==v['bytes'] and digest(raw)==v['sha256'];return raw
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:chunks=list(ex.map(part,artifact['parts']))
    raw=b''.join(chunks);assert len(raw)==artifact['bytes'] and digest(raw)==artifact['sha256'];archive=root/artifact['filename'];archive.write_bytes(raw);extracted=root/'extracted';extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())=={v['path'] for v in manifest['files']}|{'RESULT_MEMBER_HASHES.json'} and z.read('RESULT_MEMBER_HASHES.json')==raw_manifest
        for v in manifest['files']:
            data=z.read(v['path']);assert len(data)==v['bytes'] and digest(data)==v['sha256'];p=extracted/v['path'];assert p.resolve().is_relative_to(extracted.resolve());p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():assert p.read_bytes()==data
            else:p.write_bytes(data)
    result=json.loads(fetch('RESULT.json'));assert result==json.loads((extracted/'RESULT.json').read_bytes());original=state/'q4-native92'/arm;count=0
    for v in manifest['files']:
        if v['path'].startswith('accounts/'+arm+'/'):
            p=original/v['path'][len('accounts/'+arm+'/'):];assert p.stat().st_size==v['bytes'] and digest(p.read_bytes())==v['sha256'];count+=1
        if v['path'].startswith('repo/'):
            p=run.REPO/v['path'][5:];assert p.stat().st_size==v['bytes'] and digest(p.read_bytes())==v['sha256']
    account=extracted/'accounts'/arm
    code="""import json
from pathlib import Path
import q4_native92 as run
import finalize_q4_native92 as auditor
state=Path(STATE);account=Path(ACCOUNT)
run.source_check(state);run.base.frozen.modules(state)
audit=auditor.verify(account,state)
sim,pointer=run.restore(account/'recovery',run.read(account/'BINDING.json'),run.window(state))
summary=run.read(account/'account/summary.json')
assert pointer['completed_decisions']==92 and sim.rows_written==131046 and all(p.quantity==0 for p in sim.account.positions.values()) and abs(float(sim.account.nav())-summary['NAV'])<1e-8
assert sim.account.trades==run.read(account/'account/trades.json') and sim.funding_journal==run.read(account/'account/funding.json')
print(json.dumps(dict(audit=audit,state_hash=sim.state_hash(),NAV=float(sim.account.nav()),original_account_journal_exact=True)))
""".replace('STATE',repr(str(state))).replace('ACCOUNT',repr(str(account)))
    env=os.environ.copy();env.update(PYTHONPATH=str(state/'deps'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1');portable=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=extracted/'repo'/run.HERE.relative_to(run.REPO),env=env))
    receipt=dict(status='PASS_PUBLIC_ORIGINAL_Q4_JOURNALS_CHECKPOINT_RESTORE_AND_ACTUAL_INPUT_AUDIT',arm=arm,artifact_commit=commit,archive_SHA256=artifact['sha256'],archive_bytes=artifact['bytes'],parts=len(chunks),members=len(manifest['files']),original_account_files_byte_identical=count,engine_SHA256=run.ENGINE_SHA,final_checkpoint_state_hash=portable['state_hash'],completed_minutes=131046,terminal_paid_flat=True,account_journal_exact=True,restored_account_NAV=portable['NAV'],portable_actual_input_audit=portable['audit'],wallet_advanced_after_restore=False,wallets_run=0,completed_wallet_reruns=0,fits=0,model_inference=0,provider_downloads=0)
    (root/'PUBLIC_READBACK.json').write_bytes(run.encoded(receipt));print(json.dumps({k:v for k,v in receipt.items() if k!='portable_actual_input_audit'}),flush=True);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--arm',choices=tuple(run.ARMS),required=True);p.add_argument('--commit',required=True);a=p.parse_args();verify(a.state,a.arm,a.commit)
