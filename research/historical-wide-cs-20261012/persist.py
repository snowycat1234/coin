"""Exact source/target/result publication and saved-path zero-replay audit."""
import argparse,hashlib,io,json,time,zipfile,sys
from pathlib import Path
import numpy as np
from source import HERE,ROOT,sha,save,frame,DAY
def git(*a):return __import__('subprocess').check_output(['git',*a],cwd=ROOT)
def pack(state,kind):
 dest=HERE/'public'/kind;assert not dest.exists();dest.mkdir(parents=True);members=[];f=io.BytesIO()
 with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(state.rglob('*')):
   if not p.is_file():continue
   name=str(p.relative_to(state));raw=p.read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
 raw=f.getvalue();assert len(raw)<16000000;parts=[]
 for n,at in enumerate(range(0,len(raw),786432)):
  name=f'PUBLIC.zip.part{n:04d}';piece=raw[at:at+786432];(dest/name).write_bytes(piece);parts.append(dict(file=name,bytes=len(piece),SHA256=hashlib.sha256(piece).hexdigest()))
 save(dest/'INDEX.json',dict(kind=kind,packet_bytes=len(raw),packet_SHA256=hashlib.sha256(raw).hexdigest(),members=members,parts=parts,original_bytes_exact=True));print('ACTUAL_HISTORICAL_WIDE_PUBLIC_PACKET',kind,len(raw),len(members),flush=True)
def restore(state,artifact,kinds):
 assert not state.exists() and not git('status','--porcelain');state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path('/workspace/historical-wide-cs-state')/k) for k in ('SELECTION','EVALUATION_SOURCE','PREPARED','SCORED')):blocked.append(str(p));raise RuntimeError('Original STATE forbidden during public recovery')
 sys.addaudithook(audit);reports={}
 for kind in kinds:
  prefix=str(HERE.relative_to(ROOT))+'/public/'+kind+'/';ix=json.loads(git('show',artifact+':'+prefix+'INDEX.json'));pieces=[]
  for r in ix['parts']:
   raw=git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];pieces.append(raw)
  raw=b''.join(pieces);assert len(raw)==ix['packet_bytes'] and hashlib.sha256(raw).hexdigest()==ix['packet_SHA256'];dest=state/kind;dest.mkdir();members={r['name']:r for r in ix['members']}
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   assert z.testzip() is None and set(z.namelist())==set(members) and len(z.namelist())==len(members)
   for name in z.namelist():
    raw=z.read(name);r=members[name];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['SHA256'];p=dest/name;assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  verified=0
  for p in dest.rglob('*.SOURCE.json'):
   r=json.loads(p.read_text())
   if 'path' in r:
    q=dest/r['path'];assert sha(q)==r['ZIP_SHA256'] and sha(Path(str(q)+'.CHECKSUM'))==r['CHECKSUM_SHA256'];f,complete=frame(q,r['period'],r['daily']);assert len(f)==r['rows'] and complete==r['full_period'];verified+=1
  reports[kind]=dict(bytes=ix['packet_bytes'],members=len(members),original_1d_ZIPs_CRC_parser_rechecked=verified)
 if 'TARGETS' in kinds and 'SCORES' in kinds:
  prep=json.loads((state/'TARGETS/PREPARATION.json').read_text());assert sha(state/'TARGETS/TARGETS.npz')==prep['TARGETS_SHA256'] and sha(state/'TARGETS/PROOF.json')==prep['PROOF_SHA256'] and all(prep['machine_promotion_checks'].values())
  with np.load(state/'TARGETS/TARGETS.npz',allow_pickle=False) as z:signals=z['signal_available_us'];execs=z['execution_us'];assert len(execs)==365 and np.all(execs>signals) and np.all(execs-signals==DAY)
  for arm in ('CORE5','WIDE20'):
   body=json.loads((state/'SCORES'/(arm+'_ACCOUNT.json')).read_text());rows=body['rows'];nav=10000.;maximum=0.
   for row in rows:
    assert row['signal_available_us']<row['execution_open_boundary_us']<row['next_open_boundary_us']<row['conservative_open_label_mature_us'];maximum=max(maximum,abs(row['nav_before']-nav),abs(row['daily_return']-(row['nav_after']/row['nav_before']-1)));nav=row['nav_after']
   assert nav==body['summary']['last_marked_NAV'] and maximum<=1e-12
   reports[arm]=dict(saved_rows=len(rows),NAV_continuity_maximum_error=maximum,strict_time_bounds=True,no_new_proxy_replay=True)
 save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_HISTORICAL_WIDE_SAVED_SOURCE_TARGET_PRICE_PROXY_ZERO_REPLAY',artifact_commit=artifact,kinds=reports,original_STATE_open_attempts=len(blocked),new_provider_GETs=0,new_fits=0,new_price_proxy_calls=0,new_native_wallets=0,seconds=time.monotonic()-began));print('ACTUAL_HISTORICAL_WIDE_PUBLIC_RECOVERY_PASS',time.monotonic()-began,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='phase',required=True);q=s.add_parser('pack');q.add_argument('--state',type=Path,required=True);q.add_argument('--kind',choices=['SELECTION','EVAL_SOURCE','TARGETS','SCORES'],required=True);q=s.add_parser('restore');q.add_argument('--state',type=Path,required=True);q.add_argument('--artifact-commit',required=True);q.add_argument('--kinds',nargs='+',required=True);a=p.parse_args()
 if a.phase=='pack':pack(a.state,a.kind)
 else:restore(a.state,a.artifact_commit,a.kinds)
