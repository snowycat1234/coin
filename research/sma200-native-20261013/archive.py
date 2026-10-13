"""Public original states and lossless minute codec; cold decode in RAM only."""
import argparse,gzip,io,json,shutil,sys,time,zipfile
from pathlib import Path
import numpy as np
from native_apis import HERE,ROOT,native,Closing,profile_sha,SYMBOLS,file_sha,sha,save,proto,verify,git,window,fingerprint,load
def expected(key):
 r=json.loads((HERE/'input/READINESS.json').read_text());W=proto()['windows'][key];end=native.utc(W['calendar'][1]);return dict(window=key,arm='SMA200_10PCT',calendar=W['calendar'],main_commit=proto()['main_commit'],protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),readiness_SHA256=file_sha(HERE/'input/READINESS.json'),target_archive_SHA256=file_sha(HERE/'input'/(key+'.npz')),source_index_SHA256=r['years'][key]['source_index_SHA256'],quantity_profile_SHA256=profile_sha(),account_class=Closing.VERSION,contract_from_initial_capital=True,persist_cash_close=False,final_day_target_zero=False,end_us=end,terminal_signal_us=end-360000000)
def identity(binding,key):
 for k,v in expected(key).items():assert binding[k]==v,k
def pack(state,key):
 verify();dest=HERE/'result'/key;assert not dest.exists();binding=json.loads((state/'BINDING.json').read_text());identity(binding,key);ptr=json.loads((state/'recovery/POINTER.json').read_text());names=['BINDING.json','RUN_PROCESS.json','RESULT.json','ACCOUNT.json','DAILY.csv','MINUTE_NUMERIC.json','TIMING.json','recovery/POINTER.json','recovery/'+ptr['snapshot_path']]+['recovery/'+r['path'] for r in ptr['chunks']];members={};stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in names:b=(state/name).read_bytes();info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b);members[name]=dict(bytes=len(b),SHA256=sha(b))
 raw=stream.getvalue();total=len(raw)+sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/INDEX.json'));assert total<proto()['budget']['published_total_bytes'];assert shutil.disk_usage('/workspace').free-2*len(raw)-1048576>=16106127360,'Room for public checkout and Git objects must retain reserve';dest.mkdir(parents=True);parts=[]
 for off in range(0,len(raw),786432):name=f'PUBLIC.zip.part{len(parts):04d}';b=raw[off:off+786432];(dest/name).write_bytes(b);parts.append(dict(file=name,bytes=len(b),SHA256=sha(b)))
 save(dest/'INDEX.json',dict(expected(key),packet_bytes=len(raw),packet_SHA256=sha(raw),parts=parts,members=members,state_hash=ptr['state_hash'],snapshot_SHA256=ptr['snapshot_SHA256'],all37_bits_original_NPZ='PRESERVED_GENUINE_LATEST_STATE_WITH_ORIGINAL_CHUNK_CODEC',quarter_intermediate_checkpoints='RETAINED_IN_ORIGINAL_STATE_NOT_NEEDED_FOR_COMPLETE_LASTSTATE_RESTORE'));print('ACTUAL_SMA200_PUBLIC_PACKET',key,len(raw),len(members),flush=True)
def cold(key,commit,out):
 assert not out.exists();verify();begin=time.monotonic();blocked=[];prefixes=json.loads((HERE/'evidence/ORIGINAL_FINANCIAL_PREFIXES.json').read_text())+['/workspace/sma200-native-state']
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes)) and any(Path(args[0]).absolute().is_relative_to(Path(p)) for p in prefixes):blocked.append(str(args[0]));raise RuntimeError('Original observed STATE forbidden in public cold')
 sys.addaudithook(audit);prefix=str(HERE.relative_to(ROOT))+'/result/'+key+'/';ix=json.loads(git(commit+':'+prefix+'INDEX.json'))
 for k,v in expected(key).items():assert ix[k]==v,k
 pieces=[]
 for r in ix['parts']:b=git(commit+':'+prefix+r['file']);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];pieces.append(b)
 raw=b''.join(pieces);assert len(raw)==ix['packet_bytes'] and sha(raw)==ix['packet_SHA256'];data={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==len(ix['members']) and set(z.namelist())==set(ix['members'])
  for name,r in ix['members'].items():b=z.read(name);assert len(b)==r['bytes'] and sha(b)==r['SHA256'];data[name]=b
 binding=json.loads(data['BINDING.json']);identity(binding,key);ptr=json.loads(data['recovery/POINTER.json']);assert ptr['binding']==binding and ptr['state_hash']==ix['state_hash'] and ptr['snapshot_SHA256']==ix['snapshot_SHA256'];b=data['recovery/'+ptr['snapshot_path']];assert sha(b)==ptr['snapshot_SHA256'];snapshot=json.loads(gzip.decompress(b));assert snapshot['persist_cash_close'] is False and snapshot['final_day_target_zero'] is False;codec=load('sma_existing_public_chunk_codec',ROOT/'research/portfolio-risk-budget-20261012/compact_state.py');chunks=[]
 for r in ptr['chunks']:
  b=data['recovery/'+r['path']];assert sha(b)==r['SHA256']
  with np.load(io.BytesIO(b),allow_pickle=False) as z:a=np.ascontiguousarray(z['column_chunk'].T)
  assert a.shape==(r['rows'],36) and a.dtype==np.float64 and np.isfinite(a).all() and sha(codec.original_npz(a))==r['original_NPZ_SHA256'];chunks.append(a)
 assert sum(len(a) for a in chunks)==ptr['completed_minutes'];snapshot['minute_chunks']=chunks;win=window(key);sim=native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=Closing);assert sim.state_hash()==ptr['state_hash'] and sim.account.snapshot()==snapshot['account'];case=sim.result();body=json.loads(data['ACCOUNT.json']);result=json.loads(data['RESULT.json']);assert case['summary']==body['summary']==result['summary'] and result['genuine_state_hash']==ptr['state_hash'];assert fingerprint(case['minute'])==json.loads(data['MINUTE_NUMERIC.json'])['columns']
 for k in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[k]==body[k],k
 assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations'];daily=case['minute'].filter(native.pl.col('close_us')%86400000000==0);assert daily.write_csv().encode()==data['DAILY.csv'];_,q=native.episodes(case['trades'],SYMBOLS)
 for s in SYMBOLS:assert q[s]==sim.account.positions[s].quantity
 bridge=native.nav_bridge(case['trades'],case['funding'],q,body['summary']['terminal_mark_prices'],sim.account.nav());assert bridge==result['independent_decimal_NAV_bridge'];assert len(case['funding'])==len(win['events'])
 for a,b in zip(case['funding'],win['events'],strict=True):
  for k,v in b.items():assert a[k]==v,k
 assert sim.state_hash()==ptr['state_hash'] and not blocked;proof=dict(status='PASS_EXACT_PUBLIC_ORIGINAL_SMA200_NATIVE_ZERO_ADVANCE',window=key,artifact_commit=commit,packet_bytes=ix['packet_bytes'],members=len(data),rows=sim.rows_written,genuine_state_hash=ptr['state_hash'],snapshot_SHA256=ptr['snapshot_SHA256'],all37_bits_clocks_original_NPZ_daily_journals_targets_summary='EXACT',complete_scheduler_and_account='EXACT',independent_decimal_NAV_bridge=bridge,inventory={s:str(v) for s,v in q.items()},funding_source_event_identity='EXACT',funding_events=len(case['funding']),paid_flat=body['summary']['terminal_cash_realized'],source='REUSED_VERIFIED_PUBLIC_SOURCE_CACHE_BYTE_IDENTITY_NOT_NEW_PROVIDER_ORIGINAL_REPARSE',transport='PUBLIC_GIT_PACKET_RAM_ONLY_NO_ORIGINAL_OBSERVED_STATE_READ_OR_DUPLICATE_DISK_ACCOUNT',account_advances=0,new_wallets=0,new_fits=0,RNG_draws=0,downloads=0,original_STATE_open_attempts=len(blocked),seconds=time.monotonic()-begin);save(out,proof);print('ACTUAL_SMA200_NATIVE_PUBLIC_COLD_PASS',key,sim.rows_written,proof['seconds'],flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('phase',choices=['pack','cold']);q.add_argument('--state',type=Path);q.add_argument('--window',choices=['Y2023','Y2025'],required=True);q.add_argument('--artifact-commit');q.add_argument('--output',type=Path);a=q.parse_args();pack(a.state,a.window) if a.phase=='pack' else cold(a.window,a.artifact_commit,a.output)
