"""Three-arm lossless packet adapter using original split-state and numeric APIs."""
import argparse,gc,hashlib,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from experiment import native,b,save,sha,proto,verify,source_window,restore_snapshot,ARMS,SYMBOLS
sys.path.insert(0,str(ROOT/'research/cs-continuous-economics-20261012'));from persistence import minute_fingerprint
import source_prepare as prep1
prep2=sys.modules['source']
assert Path(prep2.__file__).resolve()==ROOT/'research/cs-2023-continuous-economics-20261012/source.py'
def encode_chunk(path):
    with np.load(path,allow_pickle=False) as z:a=z['minute_chunk']
    assert a.dtype==np.float64 and a.ndim==2 and a.shape[1]==37 and np.isfinite(a).all()
    f=io.BytesIO();np.savez_compressed(f,column_chunk=np.ascontiguousarray(a.T));return f.getvalue()
def decode_chunk(raw,path,expected_sha):
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:a=np.ascontiguousarray(z['column_chunk'].T)
    assert a.dtype==np.float64 and a.ndim==2 and a.shape[1]==37 and np.isfinite(a).all()
    np.savez_compressed(path,minute_chunk=a);assert sha(path)==expected_sha,'Original NPZ bytes must reproduce exactly'
def pack(state,key,dest):
    verify();assert not dest.exists();dest.mkdir();packet=state/'PUBLIC.zip';members=[];chunks=[]
    for arm in ARMS:
        p=state/arm/'account/minute_nav_inventory.parquet';f=native.pl.read_parquet(p);save(state/arm/'MINUTE_NUMERIC.json',dict(columns=minute_fingerprint(f),original_Parquet_SHA256=sha(p),original_Parquet_bytes=p.stat().st_size));del f;gc.collect()
    with zipfile.ZipFile(packet,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        def add_raw(name,raw):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
        def add(name,p):add_raw(name,p.read_bytes())
        for name in ('RESULT.json','BINDINGS.json','TIMING.json'):add(name,state/name)
        for arm in ARMS:
            root=state/arm;ptr=json.loads((root/'recovery/POINTER.json').read_text())
            for name in ('ACCOUNT.json','RESULT.json','DAILY.csv','MINUTE_NUMERIC.json','recovery/POINTER.json','recovery/'+ptr['snapshot_path']):add(arm+'/'+name,root/name)
            for r in ptr['chunks']:
                original=arm+'/recovery/'+r['path'];encoded=original+'.COLUMNS.npz';add_raw(encoded,encode_chunk(root/'recovery'/r['path']));chunks.append(dict(original=original,encoded=encoded,original_SHA256=r['SHA256']))
            for p in sorted((root/'account').iterdir()):
                if p.is_file() and p.name!='minute_nav_inventory.parquet':add(arm+'/account/'+p.name,p)
    assert packet.stat().st_size<250000000;parts=[]
    with packet.open('rb') as f:
        i=0
        while raw:=f.read(786432):
            p=dest/f'PUBLIC.zip.part{i:04d}';p.write_bytes(raw);parts.append(dict(file=p.name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()));i+=1
    save(dest/'INDEX.json',dict(window=key,arms=list(ARMS),packet_bytes=packet.stat().st_size,packet_SHA256=sha(packet),parts=parts,members=members,lossless_chunks=chunks,codec='FLOAT64_COLUMNS_COPY_TRANSPOSE_NO_ARITHMETIC_OR_QUANTIZATION_OR_NPZ_METADATA_CHANGE_AFTER_DECODE',scope='GENUINE3SCHEDULERS_ALL37MINUTEVALUES_AND_ORIGINAL_NPZ_BYTES_EXACT_PQCONTAINER_NOT_REPUBLISHED'));print('DUAL_SPEED_PACKET',key,packet.stat().st_size,len(parts),flush=True)
def restore(state,key,artifact):
    assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir();started=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).absolute()
            for forbidden in ('/workspace/cs-dual-speed-state/OBSERVED_P1','/workspace/cs-dual-speed-state/OBSERVED_P2','/workspace/cs-continuous-state/SOURCE_RECOVERED','/workspace/cs-2023-state/SOURCE_OBSERVED'):
                if p.is_relative_to(Path(forbidden)) and not p.is_relative_to(state):blocked.append(str(p));raise RuntimeError('OriginalobservedSTATE forbidden forpublicrestore')
    sys.addaudithook(audit);base=str(HERE.relative_to(ROOT))+'/result/'+key+'/';index=json.loads(b.git('show',artifact+':'+base+'INDEX.json'));assert index['arms']==list(ARMS) and index['window']==key;packet=state/'PUBLIC.zip'
    with packet.open('xb') as f:
        for r in index['parts']:
            raw=b.git('show',artifact+':'+base+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];f.write(raw)
    assert packet.stat().st_size==index['packet_bytes'] and sha(packet)==index['packet_SHA256'];dest=state/'accounts';dest.mkdir();expected={r['name']:r for r in index['members']}
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
        for name in z.namelist():
            p=dest/name;assert p.resolve().is_relative_to(dest.resolve());raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    for r in index['lossless_chunks']:
        p=dest/r['original'];assert p.resolve().is_relative_to(dest.resolve()) and not p.exists();decode_chunk((dest/r['encoded']).read_bytes(),p,r['original_SHA256'])
    W=proto()['windows'][key];prepared=state/'source'
    if key=='P1':prep1.build(prepared,W['source_science'],expected=W['source_artifact'])
    else:
        source_index=json.loads(b.git('show',W['source_artifact']+':research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json'));q=source_index['quarter_artifacts'];prep2.build(prepared,W['source_science'],q['Q1'],q['Q2'],W['source_artifact'])
    win=source_window(key,prepared);bindings=json.loads((dest/'BINDINGS.json').read_text());proof=[]
    for arm in ARMS:
        root=dest/arm;body=json.loads((root/'ACCOUNT.json').read_text());snapshot,ptr=restore_snapshot(root/'recovery',bindings[arm]);sim=native.NativeDailySimulator.from_snapshot(snapshot,win);assert sim.state_hash()==ptr['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==ptr['completed_minutes'];result=sim.result();rebuilt=native.save_case(result,state/(arm+'_REBUILT'));assert rebuilt['summary']==body['summary'];assert minute_fingerprint(result['minute'])==json.loads((root/'MINUTE_NUMERIC.json').read_text())['columns']
        for k in ('trades','funding','rejections','breaches'):assert result[k]==body[k]
        _,q=native.episodes(result['trades'],SYMBOLS)
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(result['trades'],result['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav());proof.append(dict(arm=arm,rows=sim.rows_written,state_hash=ptr['state_hash'],all37minutevalues='EXACT_BITS_AND_COORDINATES',journals_summary='EXACT',independent_decimal_NAV_bridge=finance,account_advances=0));del sim,result,rebuilt,snapshot,ptr;gc.collect();print('PUBLIC_DUAL_SPEED_RESTORED_ZERO_ADVANCE',key,arm,flush=True)
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC3ARM_DUAL_SPEED_ZERO_ADVANCE',window=key,artifact_commit=artifact,cases=proof,new_wallets=0,account_advances=0,new_fits=0,provider_downloads=0,observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-started));print('PUBLIC_DUAL_SPEED_WINDOW_PASS',key,time.monotonic()-started,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('pack');a.add_argument('--state',type=Path,required=True);a.add_argument('--window',choices=['P1','P2'],required=True);a.add_argument('--destination',type=Path,required=True);a=s.add_parser('restore');a.add_argument('--state',type=Path,required=True);a.add_argument('--window',choices=['P1','P2'],required=True);a.add_argument('--artifact-commit',required=True);a=p.parse_args()
    if a.command=='pack':pack(a.state,a.window,a.destination)
    else:restore(a.state,a.window,a.artifact_commit)
