"""Original genuine FOLLOW states and all minute bits; cold restore advances no account."""
import argparse,hashlib,io,json,subprocess,sys,time,zipfile
from pathlib import Path
from driver import HERE,ROOT,native,b,Closing,profile_sha,restore_snapshot,SYMBOLS,sha,save,proto,verify,window,load,TARGET_COMMIT
def digest(raw):return hashlib.sha256(raw).hexdigest()
def expected(key):
 W=proto()['windows'][key]
 return dict(window=key,arm='FOLLOW',calendar=W['calendar'],account_class=Closing.VERSION,contract_from_initial_capital=True,target_artifact=TARGET_COMMIT,target_archive_SHA256=sha(HERE/'input'/(key+'.npz')),risk_proof_SHA256=sha(HERE/'input/ORIGINAL_TARGET_PREPARATION.json'),readiness_SHA256=sha(HERE/'input/READINESS.json'),protocol_SHA256=sha(HERE/'PROTOCOL.json'),quantity_profile_SHA256=profile_sha(),end_us=native.utc(W['calendar'][1]),terminal_signal_us=native.utc(W['calendar'][1])-360000000)
def identity(binding,result,key):
 for field,value in expected(key).items():assert binding[field]==value,field
 assert result['window']==key and result['arm']=='FOLLOW' and result['calendar']==proto()['windows'][key]['calendar'] and result['summary']['version']==Closing.VERSION
 assert result['summary']['contract']['quantity_profile_SHA256']==profile_sha() and result['summary']['contract']['closing_min_notional_exempt'] is True
def pack(state,key,dest):
 assert dest.resolve()==(HERE/'result'/key).resolve() and not dest.exists();verify();identity(json.loads((state/'BINDING.json').read_text()),json.loads((state/'RESULT.json').read_text()),key);pointer=json.loads((state/'recovery/POINTER.json').read_text());members=[];stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  names=['BINDING.json','RESULT.json','ACCOUNT.json','DAILY.csv','MINUTE_NUMERIC.json','TIMING.json','recovery/POINTER.json','recovery/'+pointer['snapshot_path']]+['recovery/'+r['path'] for r in pointer['chunks']]
  for name in names:
   raw=(state/name).read_bytes();info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=digest(raw)))
 raw=stream.getvalue();total=len(raw)+sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/INDEX.json'));assert total<proto()['budget']['published_total_bytes'];dest.mkdir(parents=True);parts=[]
 for off in range(0,len(raw),786432):
  name=f'PUBLIC.zip.part{len(parts):04d}';piece=raw[off:off+786432];(dest/name).write_bytes(piece);parts.append(dict(file=name,bytes=len(piece),SHA256=digest(piece)))
 save(dest/'INDEX.json',dict(expected(key),packet_bytes=len(raw),packet_SHA256=digest(raw),parts=parts,members=members,BINDING_SHA256=sha(state/'BINDING.json'),storage='GENUINE_ORIGINAL_SNAPSHOT_ALL37_MINUTE_BITS_LOSSLESS_COLUMN_CODEC_ORIGINAL_NPZ_BYTES_REPRODUCIBLE'))
 print('ACTUAL_FOLLOW_PUBLIC_PACKET',key,len(raw),len(parts),flush=True)
def rebuild_source(key,state):
 command=[sys.executable,str(HERE/'cold_source.py'),key,str(state)];prepared=state if key=='Y2023' else state/'source'
 # Separate normal main imports preserve old APIs; child hook covers original STATE reads.
 with (state.parent/'SOURCE_REBUILD.log').open('x') as log:subprocess.check_call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 assert json.loads((state.parent/'SOURCE_CHILD_AUDIT.json').read_text())['original_STATE_open_attempts']==0
 return prepared
def restore(state,key,artifact):
 assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(x)) for x in ('/workspace/rejected-break-follow-native-state/OBSERVED_Y2023','/workspace/rejected-break-follow-native-state/OBSERVED_Y2025','/workspace/cs-2023-state','/workspace/cs-continuous-state','/workspace/portfolio-risk-2025-state','/workspace/portfolio-risk-budget-state','/workspace/quantity-grid-state','/workspace/unified-exit-economics-state')):blocked.append(str(p));raise RuntimeError('Observed/original STATE forbidden in public cold restore')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/'+key+'/';ix=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'))
 for k,v in expected(key).items():assert ix[k]==v,k
 pieces=[]
 for r in ix['parts']:
  raw=b.git('show',artifact+':'+prefix+r['file']);assert digest(raw)==r['SHA256'] and len(raw)==r['bytes'];pieces.append(raw)
 raw=b''.join(pieces);assert digest(raw)==ix['packet_SHA256'] and len(raw)==ix['packet_bytes'];dest=state/'account';dest.mkdir();members={r['name']:r for r in ix['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and set(z.namelist())==set(members) and len(z.namelist())==len(members)
  for name,r in members.items():
   raw=z.read(name);assert digest(raw)==r['SHA256'] and len(raw)==r['bytes'];p=dest/name;assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 binding=json.loads((dest/'BINDING.json').read_text());result=json.loads((dest/'RESULT.json').read_text());identity(binding,result,key);assert sha(dest/'BINDING.json')==ix['BINDING_SHA256'];prepared=rebuild_source(key,state/'source_rebuilt');win=window(key,prepared);snapshot,pointer=restore_snapshot(dest/'recovery',binding)
 sim=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing);assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==pointer['completed_minutes'];case=sim.result();body=json.loads((dest/'ACCOUNT.json').read_text());assert case['summary']==body['summary']
 f=load('follow_cold_original_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');assert f.minute_fingerprint(case['minute'])==json.loads((dest/'MINUTE_NUMERIC.json').read_text())['columns']
 for field in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[field]==body[field],field
 assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations'];_,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav());assert not blocked
 report=dict(status='PASS_EXACT_PUBLIC_FOLLOW_ZERO_ADVANCE',window=key,artifact_commit=artifact,rows=sim.rows_written,packet_bytes=ix['packet_bytes'],members=len(ix['members']),genuine_state_hash=pointer['state_hash'],all37minutevalues='EXACT_BITS_AND_CLOCKS',original_NPZ_bytes='EXACT_SHA256_REPRODUCIBLE',all_journals_targets_summary='EXACT',independent_decimal_NAV_bridge=finance,paid_flat=body['summary']['terminal_cash_realized'],account_advances=0,new_wallets=0,new_fits=0,provider_downloads=0,observed_STATE_open_attempts=len(blocked),source_recovery='FRESH_PUBLIC_GIT_REBUILD_UNCHANGED_SOURCE_SCRIPTS_NO_RESEARCH_FIT',seconds=time.monotonic()-began)
 save(state/'PUBLIC_RESTORE.json',report);print('ACTUAL_FOLLOW_PUBLIC_COLD_PASS',key,report['rows'],report['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['pack','restore']);p.add_argument('--state',type=Path,required=True);p.add_argument('--window',choices=['Y2023','Y2025'],required=True);p.add_argument('--destination',type=Path);p.add_argument('--artifact-commit');a=p.parse_args()
 if a.phase=='pack':pack(a.state,a.window,a.destination)
 else:restore(a.state,a.window,a.artifact_commit)
