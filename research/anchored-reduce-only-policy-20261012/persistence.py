"""Full genuine states with parent prefix references; recovery never advances."""
import argparse,gc,gzip,hashlib,json,sys,time,zipfile
from pathlib import Path
import numpy as np
from study import HERE,ROOT,native,b,sha,save,codec,parent,anchor,source_window,SYMBOLS,verify
SPECS=(('NOOP','DEFAULT',31,'DAY31.npz'),('NOOP','EXEMPT_PROXY_V1',31,'DAY31.npz'),('EXIT','DEFAULT',33,'DAY32.npz'),('EXIT','EXEMPT_PROXY_V1',33,'DAY32.npz'))
def pack(noop,exitstate,dest):
    verify();assert not dest.exists();dest.mkdir();packet=exitstate/'PUBLIC.zip';members=[]
    with zipfile.ZipFile(packet,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        def add(name,p):
            raw=p.read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
        add('NOOP/RESULT.json',noop/'RESULT.json');add('EXIT/RESULT.json',exitstate/'RESULT.json');add('EXIT/ANCHOR_RECOVERY.json',exitstate/'ANCHOR_RECOVERY.json')
        for stage,arm,rows,day in SPECS:
            root=(noop if stage=='NOOP' else exitstate)/arm
            for name in ('STATE.json.gz','ACTIVATION.json','ACCOUNT.json','RESULT.json','MINUTE_NUMERIC.json',day):add(stage+'/'+arm+'/'+name,root/name)
    assert packet.stat().st_size<30000000;parts=[]
    with packet.open('rb') as f:
        i=0
        while raw:=f.read(786432):
            p=dest/f'PUBLIC.zip.part{i:04d}';p.write_bytes(raw);parts.append(dict(file=p.name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()));i+=1
    save(dest/'INDEX.json',dict(packet_SHA256=sha(packet),packet_bytes=packet.stat().st_size,parts=parts,members=members,prefix_source='5191aeddd5d9fa1a68a29f1812a95692e3095cbd',scope='4GENUINE_STATES_PARENT_EXACT_PREFIX_ALL37MINUTES_NO_NEW_REPLAY'));print('ANCHORED_PUBLIC_PACKET',packet.stat().st_size,len(parts),flush=True)
def restore(state,artifact):
    assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir();began=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).absolute()
            for root in ('/workspace/anchored-exit-state/OBSERVED','/workspace/anchored-exit-state/REQUEST_DAY_OBSERVED','/workspace/cs-hold-assembly-state/OBSERVED_P1','/workspace/cs-continuous-state/SOURCE_RECOVERED'):
                if p.is_relative_to(Path(root)) and not p.is_relative_to(state):blocked.append(str(p));raise RuntimeError('OriginalobservedSTATE forbidden')
    sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/';index=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'));packet=state/'PUBLIC.zip'
    with packet.open('xb') as f:
        for r in index['parts']:
            raw=b.git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];f.write(raw)
    assert sha(packet)==index['packet_SHA256'];dest=state/'cases';dest.mkdir();expected={r['name']:r for r in index['members']}
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None and set(z.namelist())==set(expected) and len(z.namelist())==len(expected)
        for name in z.namelist():
            p=dest/name;assert p.resolve().is_relative_to(dest.resolve());raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    z,old=parent();prefixchunks=[]
    for r in old['lossless_chunks'][:32]:
        p=state/Path(r['original']).name;codec.decode_chunk(z.read(r['encoded']),p,r['original_SHA256'])
        with np.load(p,allow_pickle=False) as a:prefixchunks.append(a['minute_chunk'])
    prepared=state/'source';codec.prep1.build(prepared,'eefb67af42dcff3eeadaa6dc144483bdcdc7b038',expected='fd83183c363c14e8095a6a90c252b42e22cf6493');win=source_window('P1',prepared);proof=[]
    for stage,arm,days,day in SPECS:
        root=dest/stage/arm;snap=json.loads(gzip.decompress((root/'STATE.json.gz').read_bytes()))
        with np.load(root/day,allow_pickle=False) as a:suffix=a['minute_chunk']
        snap['minute_chunks']=prefixchunks[:days-1]+[suffix];body=json.loads((root/'ACCOUNT.json').read_text());sim=native.NativeDailySimulator.from_snapshot(snap,win);result=json.loads((root/'RESULT.json').read_text());assert sim.state_hash()==result['state_hash'] and sim.account.snapshot()==snap['account'];case=sim.result();rebuilt=native.save_case(case,state/(stage+'_'+arm+'_REBUILT'));assert rebuilt['summary']==body['summary'] and codec.minute_fingerprint(case['minute'])==json.loads((root/'MINUTE_NUMERIC.json').read_text())
        for k in ('trades','funding','rejections','breaches'):assert case[k]==body[k]
        _,q=native.episodes(case['trades'],SYMBOLS)
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav());proof.append(dict(stage=stage,arm=arm,state_hash=sim.state_hash(),rows=sim.rows_written,all37minute_values='EXACT_BITS_AND_COORDINATES',journals_summary='EXACT',independent_decimal_NAV_bridge=finance,account_advances=0));del sim,case,rebuilt,snap;gc.collect();print('ANCHORED_STATE_RESTORED_ZERO_ADVANCE',stage,arm,flush=True)
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_4GENUINE_ANCHORED_STATES_ZERO_ACCOUNT_ADVANCE',artifact_commit=artifact,cases=proof,account_advances=0,new_year_wallets=0,new_fits=0,market_provider_downloads=0,observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-began));print('ANCHORED_PUBLIC_RESTORE_PASS',time.monotonic()-began,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('pack');a.add_argument('--noop',type=Path,required=True);a.add_argument('--exit',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a=s.add_parser('restore');a.add_argument('--state',type=Path,required=True);a.add_argument('--artifact-commit',required=True);a=p.parse_args()
    if a.command=='pack':pack(a.noop,a.exit,a.destination)
    else:restore(a.state,a.artifact_commit)
