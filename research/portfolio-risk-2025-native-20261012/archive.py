"""Lossless original publication in RAM; zero-advance cold restore of saved accounts."""
import argparse,hashlib,io,json,sys,time,zipfile
from pathlib import Path
from driver import HERE,ROOT,native,b,Closing,profile_sha,checkpoint,restore_snapshot,SYMBOLS,ARMS,sha,save,proto,verify,window
def digest(raw):return hashlib.sha256(raw).hexdigest()
def expected(arm):
 assert arm in ARMS
 return dict(window='Y2025',arm=arm,calendar=proto()['calendar'],account_class=Closing.VERSION,contract_from_initial_capital=True,annual_risk_budget=.10,target_archive_SHA256=sha(HERE/'input/Y2025.npz'),risk_proof_SHA256=sha(HERE/'input/Y2025_RISK.json'),quantity_profile_SHA256=profile_sha())
def identity(binding,result,arm):
 for k,v in expected(arm).items():assert binding[k]==v,k
 assert result['window']=='Y2025' and result['arm']==arm and result['calendar']==proto()['calendar'] and result['summary']['version']==Closing.VERSION
 assert result['summary']['contract']['quantity_profile_SHA256']==profile_sha() and result['summary']['contract']['closing_min_notional_exempt'] is True
def pack(state,arm,destination):
 assert destination.resolve()==(HERE/'result/Y2025'/arm).resolve() and not destination.exists();verify();identity(json.loads((state/'BINDING.json').read_text()),json.loads((state/'RESULT.json').read_text()),arm)
 members=[];packet=io.BytesIO();pointer=json.loads((state/'recovery/POINTER.json').read_text())
 with zipfile.ZipFile(packet,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in ['BINDING.json','RESULT.json','ACCOUNT.json','DAILY.csv','MINUTE_NUMERIC.json','TIMING.json','recovery/POINTER.json','recovery/'+pointer['snapshot_path']]+['recovery/'+r['path'] for r in pointer['chunks']]:
   raw=(state/name).read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=digest(raw)))
 raw=packet.getvalue();total=len(raw)+sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/*/INDEX.json'));assert total<proto()['budget']['published_total_bytes'] and len(raw)<100000000
 destination.mkdir(parents=True);parts=[]
 for i,off in enumerate(range(0,len(raw),786432)):
  name=f'PUBLIC.zip.part{i:04d}';piece=raw[off:off+786432];(destination/name).write_bytes(piece);parts.append(dict(file=name,bytes=len(piece),SHA256=digest(piece)))
 save(destination/'INDEX.json',dict(expected(arm),packet_bytes=len(raw),packet_SHA256=digest(raw),parts=parts,members=members,BINDING_SHA256=sha(state/'BINDING.json'),storage='UNCHANGED_LOSSLESS_COLUMN_CODEC_GENUINE_NATIVE_SNAPSHOT_ALL37_BITS_ORIGINAL_NPZ_BYTES'))
 print('EXACT2025_PUBLIC_PACKET',arm,len(raw),len(parts),flush=True)
def restore(state,arm,artifact,prepared):
 assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir(parents=True);began=time.monotonic();blocked=[]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(x)) for x in ('/workspace/portfolio-risk-2025-state/OBSERVED_CS_MATCHED','/workspace/portfolio-risk-2025-state/OBSERVED_VOL_MATCHED','/workspace/portfolio-risk-2025-state/OBSERVED_STATIC50','/workspace/portfolio-risk-2025-state/SOURCE_OBSERVED','/workspace/portfolio-risk-2025-state/H2_ORIGINAL_BODIES','/workspace/portfolio-risk-budget-state','/workspace/quantity-grid-state','/workspace/unified-exit-economics-state','/workspace/cs-continuous-state','/workspace/cs-2023-state')):blocked.append(str(p));raise RuntimeError('Observed STATE forbidden in cold restoration')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/Y2025/'+arm+'/';index=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'))
 for k,v in expected(arm).items():assert index[k]==v,k
 chunks=[]
 for r in index['parts']:
  raw=b.git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];chunks.append(raw)
 raw=b''.join(chunks);assert len(raw)==index['packet_bytes'] and digest(raw)==index['packet_SHA256'];dest=state/'account';dest.mkdir();members={r['name']:r for r in index['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(members)
  for name in z.namelist():
   raw=z.read(name);r=members[name];assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];p=dest/name;assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 binding=json.loads((dest/'BINDING.json').read_text());result=json.loads((dest/'RESULT.json').read_text());identity(binding,result,arm);assert sha(dest/'BINDING.json')==index['BINDING_SHA256']
 assert (prepared/'SOURCE_INDEX.json').read_bytes()==b.git('show',proto()['source_artifact']+':research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json');win=window(prepared);body=json.loads((dest/'ACCOUNT.json').read_text());snapshot,pointer=restore_snapshot(dest/'recovery',binding)
 sim=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing);assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==pointer['completed_minutes'];case=sim.result();assert case['summary']==body['summary']
 from driver import load
 f=load('cold2025_original_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');assert f.minute_fingerprint(case['minute'])==json.loads((dest/'MINUTE_NUMERIC.json').read_text())['columns']
 for field in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[field]==body[field]
 assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations']
 _,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav())
 report=dict(status='PASS_EXACT_PUBLIC_FULL2025_ZERO_ADVANCE',arm=arm,artifact_commit=artifact,rows=sim.rows_written,genuine_state_hash=pointer['state_hash'],all37minutevalues='EXACT_BITS_CLOCKS',original_NPZ_bytes='EXACT_SHA256_REPRODUCIBLE',all_journals_targets_summary='EXACT',independent_decimal_NAV_bridge=finance,paid_flat=body['summary']['terminal_cash_realized'],account_advances=0,new_wallets=0,new_fits=0,provider_downloads=0,observed_STATE_open_attempts=len(blocked),seconds=time.monotonic()-began);save(state/'PUBLIC_RESTORE.json',report);print('EXACT2025_PUBLIC_RESTORE_PASS',arm,report['rows'],report['seconds'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();subs=p.add_subparsers(dest='command',required=True);q=subs.add_parser('pack');q.add_argument('--state',type=Path,required=True);q.add_argument('--arm',choices=ARMS,required=True);q.add_argument('--destination',type=Path,required=True);q=subs.add_parser('restore');q.add_argument('--state',type=Path,required=True);q.add_argument('--arm',choices=ARMS,required=True);q.add_argument('--artifact-commit',required=True);q.add_argument('--prepared',type=Path,required=True);a=p.parse_args()
 if a.command=='pack':pack(a.state,a.arm,a.destination)
 else:restore(a.state,a.arm,a.artifact_commit,a.prepared)
