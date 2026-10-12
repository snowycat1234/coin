"""Publish/restore exact real journals and split scheduler states, no wallet advance."""
import argparse,gc,hashlib,json,sys,time,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from reference import save,sha
from core import SYMBOLS
from native_pair import native,b,window,ARMS
from state_io import restore_snapshot

def minute_fingerprint(frame):
    return [dict(name=c,dtype=frame[c].to_numpy().dtype.str,rows=frame.height,raw_SHA256=hashlib.sha256(frame[c].to_numpy().tobytes()).hexdigest()) for c in frame.columns]

def pack(state,destination):
    for line in (HERE/'PERSISTENCE_SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
    assert (state/'RESULT.json').is_file() and not destination.exists();destination.mkdir();packet=state/'PUBLIC_ACCOUNTS.zip';members=[];minute_info={}
    for arm in ARMS:
        p=state/arm/'account/minute_nav_inventory.parquet';f=native.pl.read_parquet(p)
        info=dict(columns=minute_fingerprint(f),original_Parquet_SHA256=sha(p),original_Parquet_bytes=p.stat().st_size,scope='ALL37_NUMERIC_MINUTE_COLUMNS_PRESERVED_BY_EXACT_ORIGINAL_SCHEDULER_CHUNKS;PARQUET_CONTAINER_NOT_REPUBLISHED')
        save(state/arm/'MINUTE_NUMERIC.json',info);minute_info[arm]=info;del f;gc.collect()
    with zipfile.ZipFile(packet,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        def add(name,p):
            raw=p.read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
        for name in ('RESULT.json','BINDINGS.json','TIMING.json'):add(name,state/name)
        for arm in ARMS:
            root=state/arm;pointer=json.loads((root/'recovery/POINTER.json').read_text())
            for name in ('ACCOUNT.json','RESULT.json','DAILY.csv','MINUTE_NUMERIC.json','recovery/POINTER.json','recovery/'+pointer['snapshot_path']):add(arm+'/'+name,root/name)
            for r in pointer['chunks']:add(arm+'/recovery/'+r['path'],root/'recovery'/r['path'])
            for p in sorted((root/'account').iterdir()):
                if p.is_file() and p.name!='minute_nav_inventory.parquet':add(arm+'/account/'+p.name,p)
    assert packet.stat().st_size<250_000_000,'Frozen complete-publication budget; do not drop failed arm or minute data'
    parts=[]
    with packet.open('rb') as f:
        i=0
        while raw:=f.read(786432):
            p=destination/f'ACCOUNTS.zip.part{i:04d}';p.write_bytes(raw);parts.append(dict(file=p.name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()));i+=1
    save(destination/'INDEX.json',dict(schema='EXACT_JOURNALS_GENUINE_SPLIT_SCHEDULER_ALL_MINUTE_VALUES_V1',packet_bytes=packet.stat().st_size,packet_SHA256=sha(packet),parts=parts,members=members,arms=list(ARMS),native_wallets_in_bundle=2,supervised_fits=0,old_wallet_reruns=0,source_index_path='research/cs-continuous-economics-20261012/source-result/SOURCE_INDEX.json',original_PQ_container_recovery_claim=False))
    print('PUBLISHED_PACKET',packet.stat().st_size,'parts',len(parts),flush=True)

def restore(state,artifact,source_science,source_artifact):
    assert not state.exists() and not b.git('status','--porcelain');state.mkdir();started=time.monotonic();blocked=[]
    for line in (HERE/'PERSISTENCE_SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).absolute()
            for old in ('SOURCE_OBSERVED','SOURCE_RECOVERED','NATIVE_OBSERVED'):
                if p.is_relative_to(Path('/workspace/cs-continuous-state')/old) and not p.is_relative_to(state):blocked.append(str(p));raise RuntimeError('Original observed STATE forbidden during public restore')
    sys.addaudithook(audit)
    base='research/cs-continuous-economics-20261012/native-result/'
    index=json.loads(b.git('show',artifact+':'+base+'INDEX.json'));assert index['schema']=='EXACT_JOURNALS_GENUINE_SPLIT_SCHEDULER_ALL_MINUTE_VALUES_V1' and index['arms']==list(ARMS)
    packet=state/'PUBLIC_ACCOUNTS.zip'
    with packet.open('xb') as f:
        for r in index['parts']:
            raw=b.git('show',artifact+':'+base+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];f.write(raw)
    assert packet.stat().st_size==index['packet_bytes'] and sha(packet)==index['packet_SHA256'];expected={r['name']:r for r in index['members']};dest=state/'accounts';dest.mkdir()
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
        for name in z.namelist():
            p=dest/name;assert p.resolve().is_relative_to(dest.resolve());raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    from source_prepare import build
    build(state/'source',source_science,expected=source_artifact);win=window(state/'source');bindings=json.loads((dest/'BINDINGS.json').read_text());proof=[]
    for arm in ARMS:
        case=dest/arm;body=json.loads((case/'ACCOUNT.json').read_text());snapshot,pointer=restore_snapshot(case/'recovery',bindings[arm])
        sim=native.NativeDailySimulator.from_snapshot(snapshot,win)
        assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==pointer['completed_minutes']
        restored=sim.result();original_summary=body['summary'];directory=state/(arm+'_REBUILT_NUMERIC');rebuilt=native.save_case(restored,directory)
        assert rebuilt['summary']==original_summary,'Exact restored scientific summary including costs/risk/stops'
        assert minute_fingerprint(restored['minute'])==json.loads((case/'MINUTE_NUMERIC.json').read_text())['columns'],'All actual 37 minute columns exact'
        assert restored['trades']==body['trades'] and restored['funding']==body['funding'] and restored['rejections']==body['rejections'] and restored['breaches']==body['breaches']
        episodes,q=native.episodes(restored['trades'],SYMBOLS)
        for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(restored['trades'],restored['funding'],q,original_summary['terminal_mark_prices'],sim.account.nav())
        proof.append(dict(arm=arm,rows=sim.rows_written,original_state_hash=pointer['state_hash'],all37minute_columns='EXACT_VALUES_BITS_AND_COORDINATES',journals_summary='EXACT',independent_decimal_NAV_bridge=finance,account_advances=0,restored_scheduler_objects=1))
        del sim,restored,rebuilt,snapshot,pointer;gc.collect();print('PUBLIC_COLD_ACCOUNT_RESTORED_NO_ADVANCE',arm,flush=True)
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_EXACT_CONTINUOUS_SOURCE_AND_TWO_SCHEDULERS',artifact_commit=artifact,science_source_commit=source_science,source_artifact_commit=source_artifact,cases=proof,new_native_wallets=0,account_advances=0,restored_scheduler_objects=2,new_supervised_fits=0,provider_downloads=0,original_observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-started))
    print('PUBLIC_RESTORE_PASS_ZERO_ADVANCE',time.monotonic()-started,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('pack');a.add_argument('--state',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a=s.add_parser('restore');a.add_argument('--state',type=Path,required=True);a.add_argument('--artifact-commit',required=True);a.add_argument('--source-science-commit',required=True);a.add_argument('--source-artifact-commit',required=True);args=p.parse_args()
    if args.command=='pack':pack(args.state,args.destination)
    else:restore(args.state,args.artifact_commit,args.source_science_commit,args.source_artifact_commit)
