"""One-account publication; reuse original state/codecs, never replay a wallet."""
import argparse,gc,hashlib,importlib.util,json,shutil,sys,time,zipfile
from pathlib import Path
from driver import HERE,ROOT,native,b,sha,save,proto,verify,source_window,restore_snapshot,SYMBOLS
spec=importlib.util.spec_from_file_location('ranking_lossless_codec',ROOT/'research/cs-dual-speed-ranking-20261012/archive.py');codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
def pack(state,key,dest):
    verify();assert not dest.exists();dest.mkdir(parents=True);packet=state/'PUBLIC.zip';members=[];chunks=[];p=state/'account/minute_nav_inventory.parquet';frame=native.pl.read_parquet(p);save(state/'MINUTE_NUMERIC.json',dict(columns=codec.minute_fingerprint(frame),original_Parquet_SHA256=sha(p),original_Parquet_bytes=p.stat().st_size));del frame;gc.collect()
    with zipfile.ZipFile(packet,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        def add_raw(name,raw):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
        def add(name,p):add_raw(name,p.read_bytes())
        ptr=json.loads((state/'recovery/POINTER.json').read_text())
        for name in ('RESULT.json','ACCOUNT.json','BINDING.json','TIMING.json','DAILY.csv','MINUTE_NUMERIC.json','recovery/POINTER.json','recovery/'+ptr['snapshot_path']):add(name,state/name)
        for r in ptr['chunks']:
            original='recovery/'+r['path'];encoded=original+'.COLUMNS.npz';add_raw(encoded,codec.encode_chunk(state/original));chunks.append(dict(original=original,encoded=encoded,original_SHA256=r['SHA256']))
        for p in sorted((state/'account').iterdir()):
            if p.is_file() and p.name!='minute_nav_inventory.parquet':add('account/'+p.name,p)
    total=packet.stat().st_size
    for other in ('P1','P2'):
        p=HERE/'result'/other/'INDEX.json'
        if other!=key and p.exists():total+=json.loads(p.read_text())['packet_bytes']
    assert total<proto()['budget']['published_total_bytes'];parts=[]
    with packet.open('rb') as f:
        i=0
        while raw:=f.read(786432):
            p=dest/f'PUBLIC.zip.part{i:04d}';p.write_bytes(raw);parts.append(dict(file=p.name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()));i+=1
    save(dest/'INDEX.json',dict(window=key,packet_bytes=packet.stat().st_size,packet_SHA256=sha(packet),parts=parts,members=members,lossless_chunks=chunks,scope='ORIGINAL_ONE_ACCOUNT_SCHEDULER_NPZ_BYTE_SHA_ALL37NUMERIC_MINUTES_EXACT_NOT_PQ_CONTAINER'));print('STATIC50_PACKET',key,packet.stat().st_size,len(parts),flush=True)
def restore(state,key,artifact):
    assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir();began=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).absolute()
            for forbidden in ('/workspace/cs-hold-assembly-state/OBSERVED_P1','/workspace/cs-hold-assembly-state/OBSERVED_P2','/workspace/cs-continuous-state/SOURCE_RECOVERED','/workspace/cs-2023-state/SOURCE_OBSERVED','/workspace/cs-dual-speed-state/OBSERVED_P1','/workspace/cs-dual-speed-state/OBSERVED_P2'):
                if p.is_relative_to(Path(forbidden)) and not p.is_relative_to(state):blocked.append(str(p));raise RuntimeError('ObservedSTATE is forbidden forpublicrestore')
    sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/'+key+'/';index=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'));assert index['window']==key;packet=state/'PUBLIC.zip'
    with packet.open('xb') as f:
        for r in index['parts']:
            raw=b.git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];f.write(raw)
    assert packet.stat().st_size==index['packet_bytes'] and sha(packet)==index['packet_SHA256'];dest=state/'account_source';dest.mkdir();expected={r['name']:r for r in index['members']}
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
        for name in z.namelist():
            p=dest/name;assert p.resolve().is_relative_to(dest.resolve());raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    for r in index['lossless_chunks']:
        p=dest/r['original'];encoded=dest/r['encoded'];assert not p.exists() and p.resolve().is_relative_to(dest.resolve());codec.decode_chunk(encoded.read_bytes(),p,r['original_SHA256']);encoded.unlink()
    packet.unlink() # Verified transport duplicate; alloriginal NPZ bytes retained.
    W=proto()['windows'][key];prepared=state/'source'
    if key=='P1':codec.prep1.build(prepared,W['source_science'],expected=W['source_artifact'])
    else:
        old=json.loads(b.git('show',W['source_artifact']+':research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json'));q=old['quarter_artifacts'];codec.prep2.build(prepared,W['source_science'],q['Q1'],q['Q2'],W['source_artifact'])
    win=source_window(key,prepared)
    # Original source builder has validated each raw body and exactpublic index;
    # tape recovery needs retained months/EVENTS/DAILY, not duplicate ZIP wrappers.
    reclaimed=sum(p.stat().st_size for p in prepared.rglob('*.zip'))
    for p in prepared.rglob('*.zip'):p.unlink()
    binding=json.loads((dest/'BINDING.json').read_text());body=json.loads((dest/'ACCOUNT.json').read_text());snapshot,ptr=restore_snapshot(dest/'recovery',binding);sim=native.NativeDailySimulator.from_snapshot(snapshot,win);assert sim.state_hash()==ptr['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==ptr['completed_minutes'];case=sim.result();rebuilt=native.save_case(case,state/'REBUILT');assert rebuilt['summary']==body['summary'] and codec.minute_fingerprint(case['minute'])==json.loads((dest/'MINUTE_NUMERIC.json').read_text())['columns']
    for k in ('trades','funding','rejections','breaches'):assert case[k]==body[k]
    _,q=native.episodes(case['trades'],SYMBOLS)
    for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
    finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav());save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_STATIC50_ZERO_ACCOUNT_ADVANCE',window=key,artifact_commit=artifact,state_hash=ptr['state_hash'],rows=sim.rows_written,all37minutevalues='EXACT_BITS_AND_COORDINATES',original_NPZ_chunks='EXACT_BYTE_SHA256',account_journals_summary='EXACT',independent_decimal_NAV_bridge=finance,source_index_SHA256=sha(prepared/'SOURCE_INDEX.json'),duplicate_raw_source_ZIP_reclaimed_bytes=reclaimed,observed_STATE_open_attempts=len(blocked),new_wallets=0,new_fits=0,account_advances=0,provider_downloads=0,seconds=time.monotonic()-began));print('STATIC50_PUBLIC_RESTORE_PASS',key,time.monotonic()-began,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('pack');a.add_argument('--state',type=Path,required=True);a.add_argument('--window',choices=['P1','P2'],required=True);a.add_argument('--destination',type=Path,required=True);a=s.add_parser('restore');a.add_argument('--state',type=Path,required=True);a.add_argument('--window',choices=['P1','P2'],required=True);a.add_argument('--artifact-commit',required=True);a=p.parse_args()
    if a.command=='pack':pack(a.state,a.window,a.destination)
    else:restore(a.state,a.window,a.artifact_commit)
