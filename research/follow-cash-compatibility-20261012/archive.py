"""Genuine complete scheduler/account/37-field public recovery; zero advances."""
import argparse,hashlib,io,json,sys,time,zipfile
from pathlib import Path
from driver import HERE,ROOT,OLD,follow,native,b,Closing,profile_sha,restore_snapshot,SYMBOLS,sha,save,proto,verify,load
def digest(raw):return hashlib.sha256(raw).hexdigest()
def expected(key):
 r=json.loads((HERE/'input/READINESS.json').read_text())['windows'][key];end=native.utc(proto()['windows'][key]['calendar'][1]);return dict(window=key,arm='FOLLOW_PERSISTENT_CASH',calendar=proto()['windows'][key]['calendar'],protocol_SHA256=sha(HERE/'PROTOCOL.json'),readiness_SHA256=sha(HERE/'input/READINESS.json'),target_archive_SHA256=r['target_SHA256'],source_index_SHA256=r['source_index_SHA256'],baseline_RESULT_SHA256=r['baseline_RESULT_SHA256'],baseline_state_hash=r['baseline_state_hash'],quantity_profile_SHA256=profile_sha(),account_class=Closing.VERSION,contract_from_initial_capital=True,persist_cash_close=True,final_day_target_zero=False,end_us=end,terminal_signal_us=end-360000000)
def identity(binding,result,key):
 for k,v in expected(key).items():assert binding[k]==v,k
 assert result['window']==key and result['arm']=='FOLLOW_PERSISTENT_CASH' and result['summary']['version']==Closing.VERSION and result['summary']['contract']['quantity_profile_SHA256']==profile_sha()
def pack(state,key,dest):
 assert dest.resolve()==(HERE/'result'/key).resolve() and not dest.exists();verify();identity(json.loads((state/'BINDING.json').read_text()),json.loads((state/'RESULT.json').read_text()),key);pointer=json.loads((state/'recovery/POINTER.json').read_text());names=['BINDING.json','RESULT.json','ACCOUNT.json','DAILY.csv','MINUTE_NUMERIC.json','TIMING.json','recovery/POINTER.json','recovery/'+pointer['snapshot_path']]+['recovery/'+r['path'] for r in pointer['chunks']]
 if (state/'HOLDING_DIAGNOSTIC.json').exists():names.append('HOLDING_DIAGNOSTIC.json')
 stream=io.BytesIO();members=[]
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in names:raw=(state/name).read_bytes();info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=digest(raw)))
 raw=stream.getvalue();assert len(raw)+sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/INDEX.json'))<proto()['budget']['published_total_bytes'];dest.mkdir(parents=True);parts=[]
 for off in range(0,len(raw),786432):name=f'PUBLIC.zip.part{len(parts):04d}';piece=raw[off:off+786432];(dest/name).write_bytes(piece);parts.append(dict(file=name,bytes=len(piece),SHA256=digest(piece)))
 save(dest/'INDEX.json',dict(expected(key),packet_bytes=len(raw),packet_SHA256=digest(raw),parts=parts,members=members,BINDING_SHA256=sha(state/'BINDING.json'),storage='GENUINE_SCHEDULER_ACCOUNT_ALL37_MINUTE_BITS_ORIGINAL_NPZ_BYTES'));print('ACTUAL_CASH_COMPAT_PUBLIC_PACKET',key,len(raw),len(parts),flush=True)
def restore(state,key,artifact):
 assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir(parents=True);begin=time.monotonic();blocked=[];prefixes=json.loads((HERE/'evidence/ORIGINAL_FINANCIAL_PREFIXES.json').read_text())
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)) and any(Path(args[0]).absolute().is_relative_to(Path(p)) for p in prefixes):blocked.append(str(args[0]));raise RuntimeError('Original financial/scientific STATE forbidden')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/'+key+'/';ix=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'))
 for k,v in expected(key).items():assert ix[k]==v,k
 pieces=[]
 for r in ix['parts']:raw=b.git('show',artifact+':'+prefix+r['file']);assert digest(raw)==r['SHA256'] and len(raw)==r['bytes'];pieces.append(raw)
 raw=b''.join(pieces);assert digest(raw)==ix['packet_SHA256'] and len(raw)==ix['packet_bytes'];dest=state/'account';dest.mkdir();members={r['name']:r for r in ix['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and set(z.namelist())==set(members) and len(z.namelist())==len(members)
  for name,r in members.items():raw=z.read(name);assert digest(raw)==r['SHA256'] and len(raw)==r['bytes'];p=dest/name;assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 binding=json.loads((dest/'BINDING.json').read_text());result=json.loads((dest/'RESULT.json').read_text());identity(binding,result,key);assert sha(dest/'BINDING.json')==ix['BINDING_SHA256'];prepared=Path(proto()['windows'][key]['cold_public_source']);prior=json.loads((prepared.parent/'PUBLIC_RESTORE.json' if key=='Y2023' else prepared.parents[1]/'PUBLIC_RESTORE.json').read_text());assert prior['status']=='PASS_EXACT_PUBLIC_FOLLOW_ZERO_ADVANCE' and prior['observed_STATE_open_attempts']==prior['account_advances']==0;assert sha(prepared/'SOURCE_INDEX.json')==binding['source_index_SHA256'];win=follow.window(key,prepared);snapshot,pointer=restore_snapshot(dest/'recovery',binding);assert snapshot['persist_cash_close'] is True and snapshot['final_day_target_zero'] is False
 sim=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing);assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==pointer['completed_minutes'];case=sim.result();body=json.loads((dest/'ACCOUNT.json').read_text());assert case['summary']==body['summary'];f=load('cash_cold_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');assert f.minute_fingerprint(case['minute'])==json.loads((dest/'MINUTE_NUMERIC.json').read_text())['columns']
 for k in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[k]==body[k],k
 assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations'];_,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav())
 if (dest/'HOLDING_DIAGNOSTIC.json').exists():holding=load('cash_cold_holding',OLD/'holding.py');holding.diagnose(key,dest,state/'CHECKED_HOLDING.json');assert json.loads((state/'CHECKED_HOLDING.json').read_text())==json.loads((dest/'HOLDING_DIAGNOSTIC.json').read_text())
 assert not blocked;out=dict(status='PASS_EXACT_PUBLIC_CASH_COMPAT_ZERO_ADVANCE',window=key,artifact_commit=artifact,rows=sim.rows_written,members=len(members),packet_bytes=ix['packet_bytes'],genuine_state_hash=pointer['state_hash'],all37minute_bits_clocks_NPZ_SHA_and_journals='EXACT',complete_scheduler_flags_pending_maps_previous_quote='EXACT',independent_decimal_NAV_bridge=finance,paid_flat=body['summary']['terminal_cash_realized'],source='REUSED_PREVIOUSLY_INDEPENDENTLY_VERIFIED_PUBLIC_SOURCE_CACHE_MONTH_SHA_CHECKED_NOT_OBSERVED_FINANCIAL_STATE',source_index_SHA256=binding['source_index_SHA256'],source_original_provider_reparse_or_duplicate_recovery=0,new_fits=0,new_wallets=0,account_advances=0,provider_downloads=0,original_STATE_open_attempts=len(blocked),seconds=time.monotonic()-begin);save(state/'PUBLIC_RESTORE.json',out);print('ACTUAL_CASH_COMPAT_COLD_PASS',key,sim.rows_written,out['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['pack','restore']);p.add_argument('--state',type=Path,required=True);p.add_argument('--window',choices=['Y2023','Y2025'],required=True);p.add_argument('--destination',type=Path);p.add_argument('--artifact-commit');a=p.parse_args();pack(a.state,a.window,a.destination) if a.phase=='pack' else restore(a.state,a.window,a.artifact_commit)
