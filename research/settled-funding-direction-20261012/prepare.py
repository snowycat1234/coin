"""Git-first exact existing source, raw rate direction, causal target proofs."""
import argparse,hashlib,importlib.util,io,json,subprocess,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from core import DAY,EXEC,SYMBOLS,ROOT,daily_rates,targets
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,sort_keys=True,indent=2,allow_nan=False)+'\n')
def git(s):return subprocess.check_output(['git','show',s],cwd=ROOT)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def parsed_zip(raw,checksum):
 assert checksum.decode().split()[0]==sha(raw)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==1
  f=pd.read_csv(z.open(z.namelist()[0]));assert list(f.columns)==['calc_time','funding_interval_hours','last_funding_rate']
 return f
def source2023():
 commit='53056adaa3b54f93ef6859269106ac288331dd9c';pre='research/monetary-policy-information-20261012/input/'
 raw=git(commit+':'+pre+'INPUTS.npz');assert sha(raw)=='e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4'
 meta=json.loads(git(commit+':'+pre+'PREPARATION.json'));assert tuple(meta['symbol_order'])==SYMBOLS
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:
  ids=(z['decision_us']>=pd.Timestamp('2023-01-01',tz='UTC').value//1000)&(z['decision_us']<pd.Timestamp('2024-01-01',tz='UTC').value//1000)
  inp={k:z[k][ids] for k in ('decision_us','p0','p1','funding_per_unit','owned_interval_valid')};t=z['close_available_us'];p=z['close']
 c='e0d3400b23842f11f167a63e7d80856d76501de8';prefix='research/temporal-feature-data-20261009/';ix=json.loads(git(c+':'+prefix+'INDEX.json'));pieces=[]
 for part in ix['parts']:
  b=git(c+':'+prefix+part['file']);assert sha(b)==part['SHA256'] and len(b)==part['bytes'];pieces.append(b)
 raw=b''.join(pieces);assert sha(raw)==ix['SHA256'];events={};proof=[]
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None;members=json.loads(z.read('MEMBERS.json'))['files']
  for s in SYMBOLS:
   name='source_tables_not_model_inputs/economics/'+s+'_funding_events.parquet';b=z.read(name);assert sha(b)==members[name]['SHA256']
   f=pq.read_table(io.BytesIO(b),filters=[('calc_time_ms','>=',int(inp['decision_us'][0]-31*DAY)//1000),('calc_time_ms','<',int(inp['decision_us'][-1]+2*DAY)//1000)]).to_pandas();events[s]=f
   proof.append(dict(symbol=s,source_member=name,SHA256=sha(b),projected_rows=len(f)))
 return t,p,inp,events,dict(cube_commit=commit,cube_SHA256=sha(git(commit+':'+pre+'INPUTS.npz')),raw_archive_commit=c,raw_archive_SHA256=ix['SHA256'],funding_members=proof)
def source2025():
 m=load('unchanged_existing_consumer',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py');z,read=m.consumer();ev={};execs=[]
 with np.load(io.BytesIO(read('features2025/FEATURES.npz')),allow_pickle=False) as a:t=a['completed_day_available_us'];p=a['close'];assert tuple(a['symbol_order'])==SYMBOLS
 for s in SYMBOLS:
  f=pd.read_parquet(io.BytesIO(read('economics2025/'+s+'_execution.parquet')));execs.append(f)
  ev[s]=pd.read_parquet(io.BytesIO(read('economics2025/'+s+'_funding_events.parquet')))
 z.close();d=execs[0].decision_us.to_numpy(np.int64);assert len(d)==365
 for f in execs:np.testing.assert_array_equal(f.decision_us,d);np.testing.assert_array_equal(f.execution_us,d+EXEC)
 p0=np.stack([f.exec_price.to_numpy(float) for f in execs],1)
 c='d69e9ac94478c5be54cb46c622afec7aaf3c61f7';ix=json.loads(git(c+':research_artifacts/native_20261008/INDEX.json'));r=next(r for r in ix['files'] if r['file_name']=='coin_public_tail_archives_20261008_part01.zip')
 raw=git(c+':'+r['path']);assert len(raw)==r['bytes'] and sha(raw)==r['sha256'];warm=[]
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  # Only the five already admitted December2024 funding members, no price bodies.
  for s in SYMBOLS:
   name=f'tail_data/data/raw/fundingRate/{s}/{s}-fundingRate-2024-12.zip';b=z.read(name);f=parsed_zip(b,z.read(name+'.CHECKSUM'));assert len(f)==93
   f=f.rename(columns={'calc_time':'calc_time_ms'});f['past_mark_price']=np.nan;f['past_mark_available_us']=np.nan;ev[s]=pd.concat([f,ev[s]],ignore_index=True);warm.append(dict(symbol=s,original_ZIP_SHA256=sha(b),rows=len(f)))
 source=Path('/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source');index=json.loads(git('534a18fbed0ec7a2f7ffbb298526c51b1a2a696c:research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json'))
 month=next(r for r in index['months'] if r['month']=='2025-12');b=(source/'months/2025-12.npz').read_bytes();assert sha(b)==month['source_NPZ_SHA256']
 with np.load(io.BytesIO(b),allow_pickle=False) as a:lastmarks={s:float(a[s+'_mark'][-1]) for s in SYMBOLS}
 path=ROOT/'research/terminal-readiness-2025-20261012/source/INPUTS.npz';b=path.read_bytes();assert sha(b)=='aded4e9a42c311c617489b2089aa58af56c2e030250d3dcba34303fab92e5257'
 with np.load(io.BytesIO(b),allow_pickle=False) as a:assert int(a['times'][0])==int(d[-1]+DAY) and tuple(a['symbol_order'])==SYMBOLS;terminal=np.array([a[s+'_close'][0] for s in SYMBOLS])
 b=(ROOT/'research/terminal-readiness-2025-20261012/source/EVENTS.json').read_bytes();assert sha(b)=='e6151f76f6550e457e50a5342a3494e3a6073f23166f5234934771084ae2bc65'
 for e in json.loads(b):
  s=e['symbol'];assert d[-1]+DAY<=e['event_us']<d[-1]+DAY+EXEC
  ev[s]=pd.concat([ev[s],pd.DataFrame([dict(calc_time_ms=e['event_us']//1000,funding_interval_hours=e['reported_interval_hours'],last_funding_rate=e['raw_rate'],past_mark_price=lastmarks[s],past_mark_available_us=int(d[-1]+DAY))])],ignore_index=True)
 inp=dict(decision_us=d,p0=p0,p1=np.vstack([p0[1:],terminal]),funding_per_unit=np.full_like(p0,np.nan),owned_interval_valid=np.zeros_like(p0,dtype=bool))
 return t,p,inp,ev,dict(consumer_commit=m.COMMIT if hasattr(m,'COMMIT') else 'be48f5519c23f0e64eb4d75f8b8358915c254f7b',warmup_commit=c,warmup_wrapper_SHA256=r['sha256'],warmup_original_ZIPs=warm,full_minute_source_commit='534a18fbed0ec7a2f7ffbb298526c51b1a2a696c',December_mark_NPZ_SHA256=month['source_NPZ_SHA256'],terminal_INPUTS_SHA256=sha(path.read_bytes()),terminal_scope='ADMITTED_JAN1_FIRST_MINUTE_ONLY')
def prepare(state):
 assert not state.exists();state.mkdir(parents=True);start=time.monotonic();allproof={}
 for year,reader in [(2023,source2023),(2025,source2025)]:
  t,p,inp,events,provenance=reader();d=inp['decision_us'];assert len(d)==365 and np.all(np.diff(d)==DAY);days=np.arange(d[0]-31*DAY,d[-1],DAY,dtype=np.int64);values=np.full((len(days),5),np.nan);latest=np.zeros((len(days),5),np.int64);eventout={};coeff=np.full((365,5),np.nan);owned=np.zeros((365,5),bool)
  if year==2023:
   index=json.loads(git('f38617c5a0917490c8b90fba355ecf0d5f1b87f4:research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json'));native_path=Path('/workspace/cs-2023-state/SOURCE_OBSERVED/EVENTS.json')
  else:
   index=json.loads(git('534a18fbed0ec7a2f7ffbb298526c51b1a2a696c:research/portfolio-risk-2025-native-20261012/input/SOURCE_INDEX.json'));native_path=Path('/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source/EVENTS.json')
  native_raw=native_path.read_bytes();assert sha(native_raw)==index['files']['EVENTS.json']['SHA256'];native_events=json.loads(native_raw);assert len(native_events)==5475;provenance['full_year_actual_event_SHA256']=sha(native_raw)
  for j,s in enumerate(SYMBOLS):
   f=events[s].sort_values('calc_time_ms');times=f.calc_time_ms.to_numpy(np.int64)*1000;rates=f.last_funding_rate.to_numpy(float);hours=f.funding_interval_hours.to_numpy(float);marks=f.past_mark_price.to_numpy(float);available=f.past_mark_available_us.to_numpy(float)
   expected=[e for e in native_events if e['symbol']==s];ids=(times>=d[0])&(times<d[-1]+DAY);np.testing.assert_array_equal(times[ids],np.array([e['event_us'] for e in expected]));np.testing.assert_array_equal(rates[ids],np.array([e['raw_rate'] for e in expected]));np.testing.assert_array_equal(hours[ids],np.array([e['reported_interval_hours'] for e in expected]))
   values[:,j],latest[:,j]=daily_rates(times,rates,hours,days);eventout[s]=dict(times=times.tolist(),rates=rates.tolist(),hours=hours.tolist())
   for i,at in enumerate(d):
    ids=(times>at+EXEC)&(times<=at+EXEC+DAY);a=times[ids];h=hours[ids]
    valid=len(a)>0 and abs(float(h.sum())-24)<1e-9 and np.isfinite(rates[ids]).all() and np.isfinite(marks[ids]).all() and (marks[ids]>0).all() and np.isfinite(available[ids]).all() and np.all(available[ids]<=a) and np.all(available[ids]>=a-60_000_000)
    if valid:coeff[i,j]=float(np.dot(rates[ids],marks[ids]));owned[i,j]=True
  if year==2023:np.testing.assert_allclose(coeff,inp['funding_per_unit'],rtol=1e-12,atol=1e-12);assert (owned==inp['owned_interval_valid']).all()
  else:
   inp['funding_per_unit']=coeff;inp['owned_interval_valid']=owned
   m=load('funding_consumer_parity',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py');z,read=m.consumer()
   for j,s in enumerate(SYMBOLS):
    f=pd.read_parquet(io.BytesIO(read('economics2025/'+s+'_funding_intervals.parquet')));assert len(f)==364;np.testing.assert_allclose(coeff[:364,j],f.mark_funding_per_unit,rtol=1e-12,atol=1e-12)
   z.close()
  out,proof,means,known=targets(t,p,d,days,values)
  for mode in ('FUTURE_RATE','FUTURE_NAN','FUTURE_PRICE','FUTURE_PRICE_NAN'):
   v=values.copy();prices=p.copy();cut=d[180]
   if mode=='FUTURE_RATE':v[days+2*DAY>cut]*=-100
   if mode=='FUTURE_NAN':v[days+2*DAY>cut]=np.nan
   if mode=='FUTURE_PRICE':prices[t>cut]*=100
   if mode=='FUTURE_PRICE_NAN':prices[t>cut]=np.nan
   alt,_,_,_=targets(t,prices,d,days,v)
   for arm in out:np.testing.assert_array_equal(alt[arm][d<=cut],out[arm][d<=cut])
  arrays=dict(symbol_order=np.array(SYMBOLS),close_available_us=t,close=p,funding_day_start_us=days,daily_raw_rate_sum=values,daily_last_event_us=latest,means21=means,input_known=known,**inp,**out)
  np.savez_compressed(state/f'Y{year}.npz',**arrays);save(state/f'Y{year}_RAW_EVENTS.json',eventout)
  allproof[str(year)]=dict(status='PASS_SOURCE_COVERAGE_CAUSAL_TARGETS',source=provenance,rows=365,funding_input_unknown_asset_days=int((~known).sum()),full_owned_source_asset_intervals=int(owned.sum()),changed_target_days=int(np.any(out['CARRY']!=out['SHORT'],axis=1).sum()),long_asset_days=int((out['CARRY']>0).sum()),cash_asset_days=int((out['CARRY']==0).sum()),risk=proof,future_rate_nan_price_nan_prefix='EXACT',original_funding_per_unit_parity='365_MPS' if year==2023 else '364_CONSUMER_PLUS_ACTUAL_TERMINAL_BOUNDARY',INPUTS_SHA256=sha((state/f'Y{year}.npz').read_bytes()),RAW_EVENTS_SHA256=sha((state/f'Y{year}_RAW_EVENTS.json').read_bytes()))
  print('ACTUAL_FUNDING_DIRECTION_PREPARED',year,365,allproof[str(year)]['changed_target_days'],allproof[str(year)]['funding_input_unknown_asset_days'],int(owned.sum()),flush=True)
 save(state/'PREPARATION.json',dict(status='PASS_TWO_FIXED_YEAR_FINANCING_DIRECTION_READY',years=allproof,protocol_SHA256=sha((HERE/'PROTOCOL.json').read_bytes()),new_fits=0,new_references=0,new_native_wallets=0,provider_GETs=0,seconds=time.monotonic()-start));assert time.monotonic()-start<120
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);a=p.parse_args();prepare(a.state)
