"""Exact public short-tail accounts; restore and audit without any financial advance."""
import argparse,gzip,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
from decimal import Decimal as D,localcontext
from common import HERE,ROOT,ARMS,SYMBOLS,START,END,MINUTE,parent,account_api,git,sha,digest,save
def pack(state):
 dest=HERE/'result';assert not dest.exists();dest.mkdir();members=[];packet=io.BytesIO()
 with zipfile.ZipFile(packet,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in ['RESULT.json']+[a+'/'+n for a in ARMS for n in ('TAIL.json','FINAL_ACCOUNT.json.gz')]:
   raw=(state/name).read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=digest(raw)))
 raw=packet.getvalue();assert len(raw)<50000000;parts=[]
 for i,off in enumerate(range(0,len(raw),786432)):
  body=raw[off:off+786432];name=f'EXITS.zip.part{i:03d}';(dest/name).write_bytes(body);parts.append(dict(file=name,bytes=len(body),SHA256=digest(body)))
 save(dest/'INDEX.json',dict(arms=list(ARMS),calendar=[START,END],parent_commit='af6d8e1426c663f3d5afb2da311755487681c232',account_class='conditional_btc_anchored_quantity_grid_sensitivity_v1',packet_SHA256=digest(raw),packet_bytes=len(raw),parts=parts,members=members,new_short_tail_forks=3,original_annual_results_unchanged=True));print('THREE_SHORT_TAILS_PUBLIC_PACKET',len(raw),flush=True)
def restore(state,artifact):
 assert not state.exists() and not git('status','--porcelain');state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(x)) for x in ('/workspace/terminal-readiness-2025-state/OBSERVED','/workspace/terminal-readiness-2025-state/SOURCE_OBSERVED','/workspace/portfolio-risk-2025-state/OBSERVED_CS_MATCHED','/workspace/portfolio-risk-2025-state/OBSERVED_VOL_MATCHED','/workspace/portfolio-risk-2025-state/OBSERVED_STATIC50')):blocked.append(str(p));raise RuntimeError('Observed source/account forbidden during public restore')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/';index=json.loads(git('show',artifact+':'+prefix+'INDEX.json'));assert index['arms']==list(ARMS) and index['calendar']==[START,END] and index['new_short_tail_forks']==3
 pieces=[]
 for r in index['parts']:
  raw=git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];pieces.append(raw)
 raw=b''.join(pieces);assert len(raw)==index['packet_bytes'] and digest(raw)==index['packet_SHA256'];expected={r['name']:r for r in index['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and set(z.namelist())==set(expected) and len(z.namelist())==len(expected)
  for name in z.namelist():
   raw=z.read(name);r=expected[name];assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];p=state/name;assert p.resolve().is_relative_to(state.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 from source import build
 source=json.loads(git('show',artifact+':'+str(HERE.relative_to(ROOT))+'/source/SOURCE_INDEX.json'));source['artifact_commit']=artifact;build(state/'source',source['source_commit'],public=source)
 for name in ('INPUTS.npz','EVENTS.json'):assert (state/'source'/name).read_bytes()==git('show',artifact+':'+str(HERE.relative_to(ROOT))+'/source/'+name)
 with np.load(state/'source/INPUTS.npz',allow_pickle=False) as z:price={s:z[s+'_open'] for s in SYMBOLS};volume={s:z[s+'_quote_volume'] for s in SYMBOLS}
 Closing,_=account_api();reports=[]
 for arm in ARMS:
  tail=json.loads((state/arm/'TAIL.json').read_text());encoded=(state/arm/'FINAL_ACCOUNT.json.gz').read_bytes();raw=gzip.decompress(encoded);assert digest(encoded)==tail['final_snapshot_SHA256'] and digest(raw)==tail['final_account_state_SHA256'];snap=json.loads(raw);account=Closing.from_snapshot(snap);assert account.snapshot()==snap and account.summary()==tail['after']
  original,body,proof=parent(arm);assert proof==tail['parent_proof']
  for k,v in original['account']['fill_requests'].items():assert snap['fill_requests'][k]==v
  for k,v in original['account']['funding_events'].items():assert snap['funding_events'][k]==v
  for r in tail['requests']:
   at=r['event_us']-1;i=(at-START)//MINUTE;s=r['symbol'];assert 1<=i<60 and r['signal_us']==START and r['previous_quote_available_us']==at
   with localcontext() as c:c.prec=28;cap=D(str(float(volume[s][i-1])))*D('.001')/D(str(float(price[s][i])))
   assert str(cap)==r['capacity_quantity'] and snap['fill_requests'][r['fill_id']]['receipt']==r['receipt']
  assert all(t['leg']=='CLOSE' for t in tail['new_trades']) and tail['actual_end_us']<=END
  reports.append(dict(arm=arm,status=tail['status'],paid_flat=tail['paid_flat'],final_account_state_SHA256=tail['final_account_state_SHA256'],requests=len(tail['requests']),all_original_maps_and_new_requests='EXACT',actual_source_capacities='EXACT',all_tail_and_full_account_journals='EXACT',source_events_actual=True))
 report=dict(status='PASS_PUBLIC_THREE_GENUINE_SHORT_TAIL_ACCOUNTS_ZERO_ADVANCE',artifact_commit=artifact,cases=reports,account_advances=0,new_short_tail_forks=0,old_annual_replays=0,new_fits=0,provider_downloads=0,observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-began);save(state/'PUBLIC_RESTORE.json',report);print('PUBLIC_THREE_SHORT_TAIL_RESTORE_PASS',report['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();subs=p.add_subparsers(dest='command',required=True);q=subs.add_parser('pack');q.add_argument('--state',type=Path,required=True);q=subs.add_parser('restore');q.add_argument('--state',type=Path,required=True);q.add_argument('--artifact-commit',required=True);a=p.parse_args()
 if a.command=='pack':pack(a.state)
 else:restore(a.state,a.artifact_commit)
