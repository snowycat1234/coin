"""Exact publication of one real compact native account; recovery advances no wallet."""
import argparse, hashlib, importlib.util, json, sys, time, zipfile
from pathlib import Path
from driver import HERE, ROOT, native, b, sha, save, proto, verify, source_window, restore_snapshot, Closing, profile_sha, ARMS, SYMBOLS
spec=importlib.util.spec_from_file_location('existing_budget_codec',ROOT/'research/cs-dual-speed-ranking-20261012/archive.py');codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)

def identity(binding,result,key,arm):
    assert key in proto()['windows'] and arm in ARMS
    assert binding['window']==result['window']==key and binding['arm']==result['arm']==arm
    assert binding['account_class']==result['summary']['version']==Closing.VERSION and binding['contract_from_initial_capital'] is True
    assert binding['annual_risk_budget']==proto()['annual_risk_budget']==.10
    assert binding['target_archive_SHA256']==sha(HERE/'input'/(key+'.npz')) and binding['risk_proof_SHA256']==sha(HERE/'input'/(key+'_RISK.json'))
    assert binding['component_targets_SHA256']==proto()['targets']['SHA256']
    assert binding['quantity_profile_SHA256']==result['summary']['contract']['quantity_profile_SHA256']==proto()['quantity_profile']['SHA256']==profile_sha()
    assert result['summary']['contract']['closing_min_notional_exempt'] is True

def expected_identity(key,arm):
    return dict(window=key,arm=arm,account_class=Closing.VERSION,contract_from_initial_capital=True,annual_risk_budget=.10,publication_path=str((HERE/'result'/key/arm).relative_to(ROOT)),target_archive_SHA256=sha(HERE/'input'/(key+'.npz')),risk_proof_SHA256=sha(HERE/'input'/(key+'_RISK.json')),quantity_profile_SHA256=profile_sha())

def pack(state,key,arm,dest):
    assert dest.resolve()==(HERE/'result'/key/arm).resolve() and not dest.exists()
    identity(json.loads((state/'BINDING.json').read_text()),json.loads((state/'RESULT.json').read_text()),key,arm);verify();dest.mkdir(parents=True)
    packet=state/'PUBLIC.zip';members=[];pointer=json.loads((state/'recovery/POINTER.json').read_text())
    with zipfile.ZipFile(packet,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        def add(name):
            p=state/name;raw=p.read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
        for name in ('BINDING.json','RESULT.json','ACCOUNT.json','DAILY.csv','MINUTE_NUMERIC.json','TIMING.json','recovery/POINTER.json','recovery/'+pointer['snapshot_path']):add(name)
        for r in pointer['chunks']:add('recovery/'+r['path'])
    total=packet.stat().st_size+sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/*/INDEX.json'));assert total<proto()['budget']['published_total_bytes']
    parts=[]
    with packet.open('rb') as f:
        while raw:=f.read(786432):
            p=dest/f'PUBLIC.zip.part{len(parts):04d}';p.write_bytes(raw);parts.append(dict(file=p.name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
    index=dict(expected_identity(key,arm),packet_bytes=packet.stat().st_size,packet_SHA256=sha(packet),parts=parts,members=members,BINDING_SHA256=sha(state/'BINDING.json'),storage='ORIGINAL_REAL_NATIVE_SNAPSHOT_ALL37_MINUTE_BITS_COLUMN_CODEC_ORIGINAL_NPZ_BYTES_REPRODUCIBLE')
    save(dest/'INDEX.json',index);print('PORTFOLIO_RISK_PACKET',key,arm,packet.stat().st_size,len(parts),flush=True)

def restore(state,key,arm,artifact):
    assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir(parents=True);began=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).absolute()
            for forbidden in ('/workspace/portfolio-risk-budget-state/OBSERVED_P1','/workspace/portfolio-risk-budget-state/OBSERVED_P2','/workspace/quantity-grid-state/OBSERVED_P1','/workspace/quantity-grid-state/OBSERVED_P2','/workspace/unified-exit-economics-state/OBSERVED_P1','/workspace/unified-exit-economics-state/OBSERVED_P2','/workspace/cs-hold-assembly-state/OBSERVED_P1','/workspace/cs-hold-assembly-state/OBSERVED_P2','/workspace/cs-continuous-state/SOURCE_RECOVERED','/workspace/cs-2023-state/SOURCE_OBSERVED','/workspace/cs-dual-speed-state/OBSERVED_P1','/workspace/cs-dual-speed-state/OBSERVED_P2'):
                if p.is_relative_to(Path(forbidden)) and not p.is_relative_to(state):blocked.append(str(p));raise RuntimeError('Observed STATE forbidden during public restore')
    sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/'+key+'/'+arm+'/';index=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'))
    for field,value in expected_identity(key,arm).items():assert index[field]==value,'Exact public identity '+field
    packet=state/'PUBLIC.zip'
    with packet.open('xb') as f:
        for r in index['parts']:
            raw=b.git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];f.write(raw)
    assert packet.stat().st_size==index['packet_bytes'] and sha(packet)==index['packet_SHA256'];dest=state/'account_source';dest.mkdir();expected={r['name']:r for r in index['members']}
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
        for name in z.namelist():
            p=dest/name;assert p.resolve().is_relative_to(dest.resolve());raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    packet.unlink();W=proto()['windows'][key];prepared=state/'source'
    if key=='P1':codec.prep1.build(prepared,W['source_science'],expected=W['source_artifact'])
    else:
        old=json.loads(b.git('show',W['source_artifact']+':research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json'));q=old['quarter_artifacts'];codec.prep2.build(prepared,W['source_science'],q['Q1'],q['Q2'],W['source_artifact'])
    win=source_window(key,prepared)
    for p in prepared.rglob('*.zip'):p.unlink()
    binding=json.loads((dest/'BINDING.json').read_text());assert sha(dest/'BINDING.json')==index['BINDING_SHA256'];identity(binding,json.loads((dest/'RESULT.json').read_text()),key,arm);body=json.loads((dest/'ACCOUNT.json').read_text());snapshot,ptr=restore_snapshot(dest/'recovery',binding)
    sim=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing);assert sim.state_hash()==ptr['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==ptr['completed_minutes'];case=sim.result();assert case['summary']==body['summary']
    assert codec.minute_fingerprint(case['minute'])==json.loads((dest/'MINUTE_NUMERIC.json').read_text())['columns']
    for field in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[field]==body[field]
    assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations']
    _,q=native.episodes(case['trades'],SYMBOLS)
    for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
    finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav())
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_PORTFOLIO_RISK_ZERO_ACCOUNT_ADVANCE',window=key,arm=arm,artifact_commit=artifact,state_hash=ptr['state_hash'],rows=sim.rows_written,all37minutevalues='EXACT_BITS_AND_COORDINATES',original_NPZ_chunks='EXACT_BYTE_SHA256_REPRODUCIBLE',account_journals_summary='EXACT',independent_decimal_NAV_bridge=finance,source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),observed_STATE_open_attempts=len(blocked),new_wallets=0,new_fits=0,account_advances=0,provider_downloads=0,seconds=time.monotonic()-began));print('PORTFOLIO_RISK_PUBLIC_RESTORE_PASS',key,arm,time.monotonic()-began,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('pack');q.add_argument('--state',type=Path,required=True);q.add_argument('--window',choices=['P1','P2'],required=True);q.add_argument('--arm',choices=ARMS,required=True);q.add_argument('--destination',type=Path,required=True)
    q=s.add_parser('restore');q.add_argument('--state',type=Path,required=True);q.add_argument('--window',choices=['P1','P2'],required=True);q.add_argument('--arm',choices=ARMS,required=True);q.add_argument('--artifact-commit',required=True)
    a=p.parse_args()
    if a.command=='pack':pack(a.state,a.window,a.arm,a.destination)
    else:restore(a.state,a.window,a.arm,a.artifact_commit)
