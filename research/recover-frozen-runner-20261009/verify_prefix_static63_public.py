"""Read public new-result bytes, audit original journals and restore final state; no wallet advances."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,sys,urllib.request,zipfile
from pathlib import Path
import prefix_static_native63 as runner


def verify(state,fold,commit):
    assert len(commit)==40 and set(commit)<=set('0123456789abcdef');prefix=runner.PUBLIC.relative_to(runner.REPO).as_posix()+'/'+fold;root=state/'public-prefix-static63-readback'/fold/commit;root.mkdir(parents=True,exist_ok=True);sha=lambda raw:hashlib.sha256(raw).hexdigest()
    def fetch(name,limit=786433):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+prefix+'/'+name,timeout=30).read(limit))
        return p.read_bytes()
    artifact=json.loads(fetch('results/ARTIFACT.json'));manifest_raw=fetch('results/RESULT_MEMBER_HASHES.json');manifest=json.loads(manifest_raw);assert sha(manifest_raw)==artifact['member_manifest_sha256']
    def part(v):
        raw=fetch('results/'+v['path'],v['bytes']+1);assert len(raw)==v['bytes'] and sha(raw)==v['sha256'];return raw
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:chunks=list(ex.map(part,artifact['parts']))
    raw=b''.join(chunks);assert len(raw)==artifact['bytes'] and sha(raw)==artifact['sha256'];archive=root/artifact['filename'];archive.write_bytes(raw);extracted=root/'extracted';extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())=={v['path'] for v in manifest['files']}|{'RESULT_MEMBER_HASHES.json'} and z.read('RESULT_MEMBER_HASHES.json')==manifest_raw
        for v in manifest['files']:
            data=z.read(v['path']);assert len(data)==v['bytes'] and sha(data)==v['sha256'];p=extracted/v['path'];assert p.resolve().is_relative_to(extracted.resolve());p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():assert p.read_bytes()==data
            else:p.write_bytes(data)
    result=json.loads(fetch('results/RESULT.json'));assert result==json.loads((extracted/'RESULT.json').read_bytes());original=state/'prefix-static63-native'/fold;count=0
    for v in manifest['files']:
        if v['path'].startswith('accounts/'+fold+'/'):
            p=original/v['path'][len('accounts/'+fold+'/'):];assert p.stat().st_size==v['bytes'] and sha(p.read_bytes())==v['sha256'];count+=1
        if v['path'].startswith('repo/'):
            p=runner.REPO/v['path'][5:];assert p.stat().st_size==v['bytes'] and sha(p.read_bytes())==v['sha256']
    account=extracted/'accounts'/fold;contract=runner.read(runner.PUBLIC/fold/'ADAPTER_CONTRACT.json');cal=contract['calendar'];work=runner.base.member(state,contract['market_work_relative'])
    code="import json;from pathlib import Path;import verify_native61;print(json.dumps(verify_native61.verify(Path("+repr(str(account))+"),state=Path("+repr(str(state))+"),calendar="+repr(cal)+",market_work=Path("+repr(str(work))+"))))"
    env=os.environ.copy();env.update(PYTHONPATH=str(state/'deps'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',POLARS_MAX_THREADS='1');audit=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=extracted/'repo'/runner.HERE.relative_to(runner.REPO),env=env));assert audit['minutes']==90720 and audit['terminal_paid_flat'] and audit['actual_input_check']['funding_events']==945
    runner.base.frozen.modules(state)
    import durable_native_checkpoint as durable
    sim,pointer=durable.restore(account/'recovery',runner.read(account/'BINDING.json'),runner.base.market(state,cal,work));summary=runner.read(account/'account/summary.json');assert pointer['completed_days']==63 and sim.rows_written==90720 and all(p.quantity==0 for p in sim.account.positions.values()) and abs(float(sim.account.nav())-summary['NAV'])<1e-8
    assert sim.account.trades==runner.read(account/'account/trades.json') and sim.funding_journal==runner.read(account/'account/funding.json')
    receipt=dict(status='PASS_PUBLIC_ORIGINAL_JOURNALS_CHECKPOINT_RESTORE_AND_ACTUAL_INPUT_AUDIT',fold=fold,artifact_commit=commit,archive_SHA256=artifact['sha256'],archive_bytes=artifact['bytes'],parts=len(chunks),members=len(manifest['files']),original_account_files_byte_identical=count,engine_SHA256=runner.ENGINE_SHA,final_checkpoint_state_hash=sim.state_hash(),completed_minutes=90720,terminal_paid_flat=True,account_journal_exact=True,restored_account_NAV= float(sim.account.nav()),portable_actual_input_audit=audit,wallet_advanced_after_restore=False,wallets_run=0,completed_wallet_reruns=0,fits=0,model_inference=0,provider_downloads=0)
    (root/'PUBLIC_READBACK.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='portable_actual_input_audit'}),flush=True);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--fold',choices=tuple(runner.FOLDS),required=True);p.add_argument('--commit',required=True);a=p.parse_args();verify(a.state,a.fold,a.commit)
