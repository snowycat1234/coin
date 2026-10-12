"""Thin fixed-year adapter over the prior exact account packet/state APIs."""
import argparse,gc,hashlib,json,sys,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from source import sha,git,save,build
from native_run import native,window,ARMS,restore_snapshot
sys.path.insert(0,str(ROOT/'research/cs-continuous-economics-20261012'))
import persistence as legacy
def verify():
    for line in (HERE/'PERSISTENCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def pack(state,destination):
    verify();legacy.pack(state,destination);index=json.loads((destination/'INDEX.json').read_text());index['source_index_path']=str(HERE.relative_to(ROOT))+'/source-result/SOURCE_INDEX.json';index['calendar']=['2023-01-01','2024-01-01'];index['initialization']='TWO_FRESH10K_NOT_STITCHED2022';index['protocol_SHA256']=sha(HERE/'PROTOCOL.json');save(destination/'INDEX.json',index)
def restore(state,artifact,science,source_artifact):
    assert not state.exists() and not git('status','--porcelain');verify();state.mkdir();started=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).absolute()
            for root,names in [('/workspace/cs-2023-state',('Q1_OBSERVED','Q2_OBSERVED','SOURCE_OBSERVED','NATIVE_OBSERVED','FUNDING_OBSERVED')),('/workspace/cs-continuous-state',('SOURCE_OBSERVED','SOURCE_RECOVERED','NATIVE_OBSERVED'))]:
                for old in names:
                    if p.is_relative_to(Path(root)/old) and not p.is_relative_to(state):blocked.append(str(p));raise RuntimeError('Observed STATE forbidden for public restore')
    sys.addaudithook(audit);base=str(HERE.relative_to(ROOT))+'/native-result/';index=json.loads(git('show',artifact+':'+base+'INDEX.json'));assert index['arms']==list(ARMS) and index['protocol_SHA256']==sha(HERE/'PROTOCOL.json')
    packet=state/'PUBLIC_ACCOUNTS.zip'
    with packet.open('xb') as f:
        for r in index['parts']:
            raw=git('show',artifact+':'+base+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];f.write(raw)
    assert packet.stat().st_size==index['packet_bytes'] and sha(packet)==index['packet_SHA256'];expected={r['name']:r for r in index['members']};dest=state/'accounts';dest.mkdir()
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
        for name in z.namelist():
            p=dest/name;assert p.resolve().is_relative_to(dest.resolve());raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    source_index=json.loads(git('show',source_artifact+':'+index['source_index_path']));q=source_index['quarter_artifacts'];build(state/'source',science,q['Q1'],q['Q2'],source_artifact);win=window(state/'source');bindings=json.loads((dest/'BINDINGS.json').read_text());proof=[]
    for arm in ARMS:
        case=dest/arm;body=json.loads((case/'ACCOUNT.json').read_text());snapshot,pointer=restore_snapshot(case/'recovery',bindings[arm]);sim=native.NativeDailySimulator.from_snapshot(snapshot,win)
        assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==pointer['completed_minutes']
        result=sim.result();rebuilt=native.save_case(result,state/(arm+'_REBUILT_NUMERIC'));assert rebuilt['summary']==body['summary'];assert legacy.minute_fingerprint(result['minute'])==json.loads((case/'MINUTE_NUMERIC.json').read_text())['columns']
        assert result['trades']==body['trades'] and result['funding']==body['funding'] and result['rejections']==body['rejections'] and result['breaches']==body['breaches']
        _,q=native.episodes(result['trades'],win['symbols'])
        for s in win['symbols']:assert q[s]==sim.account.positions[s].quantity
        finance=native.nav_bridge(result['trades'],result['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav());proof.append(dict(arm=arm,rows=sim.rows_written,state_hash=pointer['state_hash'],all37minute_columns='EXACT_VALUES_BITS_AND_COORDINATES',journals_summary='EXACT',independent_decimal_NAV_bridge=finance,account_advances=0,restored_scheduler_objects=1));del sim,result,rebuilt,snapshot,pointer;gc.collect();print('PUBLIC2023_ACCOUNT_RESTORED_NO_ADVANCE',arm,flush=True)
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_EXACT2023_SOURCE_TWO_SCHEDULERS_ZERO_ADVANCE',artifact_commit=artifact,science_source_commit=science,source_artifact_commit=source_artifact,cases=proof,new_native_wallets=0,account_advances=0,restored_scheduler_objects=2,new_supervised_fits=0,provider_downloads=0,original_observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-started));print('PUBLIC2023_RESTORE_PASS_ZERO_ADVANCE',time.monotonic()-started,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);a=s.add_parser('pack');a.add_argument('--state',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a=s.add_parser('restore');a.add_argument('--state',type=Path,required=True);a.add_argument('--artifact-commit',required=True);a.add_argument('--source-science-commit',required=True);a.add_argument('--source-artifact-commit',required=True);a=p.parse_args()
    if a.command=='pack':pack(a.state,a.destination)
    else:restore(a.state,a.artifact_commit,a.source_science_commit,a.source_artifact_commit)
