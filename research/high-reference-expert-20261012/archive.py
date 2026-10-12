"""Public genuine state recovery; no wallet advance and no provider access."""
import argparse,hashlib,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
from driver import HERE,ROOT,native,b,Closing,SYMBOLS,DAY,sha,save,proto,verify,restore_snapshot,load

def digest(raw):return hashlib.sha256(raw).hexdigest()
def identity(binding,result,key):
 W=next(r for r in proto()['windows'] if r['name']==key)
 assert binding['year']==result['year']==key and binding['calendar']==result['calendar']==W['calendar']
 assert binding['protocol_SHA256']==sha(HERE/'PROTOCOL.json') and binding['target_SHA256']==sha(HERE/'input'/(key+'.npz'))
 assert binding['account_class']==result['summary']['version']==Closing.VERSION
 assert binding['quantity_profile_SHA256']==result['summary']['contract']['quantity_profile_SHA256']
 assert binding['original_baseline_not_replayed'] and binding['capital_USDT']==10000
 return W

def pack(state,key,destination):
 assert destination.resolve()==(HERE/'result'/key).resolve() and not destination.exists();verify()
 binding=json.loads((state/'BINDING.json').read_text());result=json.loads((state/'RESULT.json').read_text());W=identity(binding,result,key)
 pointer=json.loads((state/'recovery/POINTER.json').read_text());source=Path(W['native_source']);ix=json.loads((source/'SOURCE_INDEX.json').read_text());assert sha(source/'SOURCE_INDEX.json')==binding['source_index_SHA256']
 # Canonical already-admitted source arrays are republished only for days the
 # original from_snapshot API must walk. No finance is rerun during that walk.
 needed=[]
 for r in ix['months']:
  at=native.utc(r['month']+'-01')
  if at<pointer['cursor']:
   p=source/'months'/(r['month']+'.npz');assert sha(p)==r['source_NPZ_SHA256'] and p.stat().st_size==r['source_NPZ_bytes'];needed.append(p)
 members=[];packet=io.BytesIO()
 with zipfile.ZipFile(packet,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  def add(name,p):
   raw=p.read_bytes();info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw);members.append(dict(name=name,bytes=len(raw),SHA256=digest(raw)))
  for name in ['BINDING.json','RESULT.json','ACCOUNT.json','DAILY.csv','MINUTE_NUMERIC.json','recovery/POINTER.json','recovery/'+pointer['snapshot_path']]+['recovery/'+r['path'] for r in pointer['chunks']]:add(name,state/name)
  for name in ('SOURCE_INDEX.json','DAILY.json','EVENTS.json'):add('source/'+name,source/name)
  for p in needed:add('source/months/'+p.name,p)
 raw=packet.getvalue();total=len(raw)+sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/INDEX.json'));assert total<proto()['budget']['published_total_bytes']
 destination.mkdir(parents=True);parts=[]
 for i,off in enumerate(range(0,len(raw),786432)):
  name=f'PUBLIC.zip.part{i:04d}';piece=raw[off:off+786432];(destination/name).write_bytes(piece);parts.append(dict(file=name,bytes=len(piece),SHA256=digest(piece)))
 save(destination/'INDEX.json',dict(year=key,packet_bytes=len(raw),packet_SHA256=digest(raw),parts=parts,members=members,BINDING_SHA256=sha(state/'BINDING.json'),genuine_state_hash=pointer['state_hash'],source_months=[p.stem for p in needed],source_scope='SHA_EXACT_REUSED_CANONICAL_ARRAYS_FOR_ORIGINAL_SNAPSHOT_TAPE_WALK_RAW_SOURCE_PROVENANCE_REUSED',storage='GENUINE_NATIVE_ACCOUNT_SCHEDULER_ALL37_MINUTE_BITS_ORIGINAL_NPZ_SHA_REPRODUCIBLE'))
 print('HIGH_REFERENCE_PUBLIC_PACKET',key,len(raw),len(parts),flush=True)

def public_window(source,binding):
 ix=json.loads((source/'SOURCE_INDEX.json').read_text());assert sha(source/'SOURCE_INDEX.json')==binding['source_index_SHA256']
 public_path='research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json' if binding['year']=='Y2023' else 'research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json'
 assert (source/'SOURCE_INDEX.json').read_bytes()==b.git('show',binding['source_artifact']+':'+public_path)
 for name in ('DAILY.json','EVENTS.json'):
  r=ix['files'][name];assert sha(source/name)==r['SHA256'] and (source/name).stat().st_size==r['bytes']
 def blocks():
  for r in ix['months']:
   p=source/'months'/(r['month']+'.npz')
   if not p.exists():raise RuntimeError('No unconsumed source or financial advance is authorized by this recovery packet')
   assert sha(p)==r['source_NPZ_SHA256'] and p.stat().st_size==r['source_NPZ_bytes']
   with np.load(p,allow_pickle=False) as a:times=a['times'];market={s:{k:a[s+'_'+k] for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
   for i in range(0,len(times),1440):yield dict(times=times[i:i+1440],market={s:{k:v[i:i+1440] for k,v in fields.items()} for s,fields in market.items()})
 start,end=ix['calendar'];return dict(start=start,end=end,symbols=SYMBOLS,daily=native.pl.DataFrame(json.loads((source/'DAILY.json').read_text())),events=json.loads((source/'EVENTS.json').read_text()),minute_blocks=blocks)

def restore(state,key,artifact):
 assert not state.exists() and not b.git('status','--porcelain');verify();state.mkdir(parents=True);began=time.monotonic();blocked=[]
 forbidden=('/workspace/expert-structure-state/OBSERVED_Y2023','/workspace/expert-structure-state/OBSERVED_Y2025','/workspace/portfolio-risk-budget-state','/workspace/quantity-grid-state','/workspace/unified-exit-economics-state','/workspace/cs-2023-state','/workspace/portfolio-risk-2025-state')
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=Path(args[0]).absolute()
   if any(p.is_relative_to(Path(x)) for x in forbidden):blocked.append(str(p));raise RuntimeError('Original financial/source STATE forbidden during cold recovery')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/'+key+'/';ix=json.loads(b.git('show',artifact+':'+prefix+'INDEX.json'));assert ix['year']==key
 pieces=[]
 for r in ix['parts']:
  raw=b.git('show',artifact+':'+prefix+r['file']);assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];pieces.append(raw)
 raw=b''.join(pieces);assert len(raw)==ix['packet_bytes'] and digest(raw)==ix['packet_SHA256'];dest=state/'account';dest.mkdir();members={r['name']:r for r in ix['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(members)
  for name in z.namelist():
   raw=z.read(name);r=members[name];assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];p=dest/name;assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 binding=json.loads((dest/'BINDING.json').read_text());result=json.loads((dest/'RESULT.json').read_text());identity(binding,result,key);assert sha(dest/'BINDING.json')==ix['BINDING_SHA256'];body=json.loads((dest/'ACCOUNT.json').read_text());snapshot,pointer=restore_snapshot(dest/'recovery',binding)
 win=public_window(dest/'source',binding)
 def denied(*args,**kwargs):raise RuntimeError('Financial advance forbidden during recovery')
 native.NativeDailySimulator.advance_day=denied
 sim=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing);assert sim.state_hash()==pointer['state_hash']==ix['genuine_state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==pointer['completed_minutes']
 case=sim.result();assert case['summary']==body['summary'];f=load('highref_original_fingerprint',ROOT/'research/cs-continuous-economics-20261012/persistence.py');assert f.minute_fingerprint(case['minute'])==json.loads((dest/'MINUTE_NUMERIC.json').read_text())['columns']
 for field in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[field]==body[field]
 assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations']
 assert case['minute'].filter(native.pl.col('close_us')%DAY==0).write_csv().encode()==(dest/'DAILY.csv').read_bytes()
 _,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 finance=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav())
 save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_HIGH_REFERENCE_ZERO_ADVANCE',year=key,artifact_commit=artifact,rows=sim.rows_written,genuine_state_hash=pointer['state_hash'],all37minutevalues='EXACT_BITS_CLOCKS',original_NPZ_bytes='EXACT_SHA256_REPRODUCIBLE',all_journals_targets_summary='EXACT',independent_decimal_NAV_bridge=finance,canonical_source_months=ix['source_months'],raw_original_source_decode='REUSED_PREVIOUS_PUBLIC_SOURCE_PROOF_NO_NEW_RAW_DECODE',observed_STATE_open_attempts=len(blocked),account_advances=0,new_wallets=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began));print('HIGH_REFERENCE_PUBLIC_RESTORE_PASS',key,sim.rows_written,time.monotonic()-began,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
 q=s.add_parser('pack');q.add_argument('--state',type=Path,required=True);q.add_argument('--year',choices=['Y2023','Y2025'],required=True);q.add_argument('--destination',type=Path,required=True)
 q=s.add_parser('restore');q.add_argument('--state',type=Path,required=True);q.add_argument('--year',choices=['Y2023','Y2025'],required=True);q.add_argument('--artifact-commit',required=True)
 a=p.parse_args()
 if a.command=='pack':pack(a.state,a.year,a.destination)
 else:restore(a.state,a.year,a.artifact_commit)
