"""Frozen source attribution, not an execution simulator or trading strategy."""
import argparse,csv,hashlib,json,pathlib,sys
import numpy as np
DAY=86400000000; MINUTE=60000000
START=1672531200000000;END=1704067200000000

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2,sort_keys=True,allow_nan=False)+'\n')
def calc(entry,exit,rate,mark):
 q=1.0/entry;sell=entry*(1-.0008);cover=exit*(1+.0008)
 price=q*(entry-exit);execution=q*.0008*(entry+exit);fee=q*.00055*(sell+cover);funding=q*mark*rate
 return dict(price=price,funding=funding,execution_cost=execution,fee=fee,net=price+funding-execution-fee)
def main():
 a=argparse.ArgumentParser();a.add_argument('--source',type=pathlib.Path,required=True);a.add_argument('--output',type=pathlib.Path,required=True);p=a.parse_args()
 here=pathlib.Path(__file__).resolve().parent;spec=json.loads((here/'SPEC.json').read_text());symbols=spec['assets'];source=p.source
 require(not p.output.exists(),'fresh output required')
 expected=json.loads((source.parent/'closure/SOURCE_INDEX.json').read_text());require((source/'SOURCE_INDEX.json').read_bytes()==(source.parent/'closure/SOURCE_INDEX.json').read_bytes(),'sourceindex mismatch')
 require(expected['calendar']==[START,END] and expected['symbol_order']==symbols,'calendar/asset mismatch')
 sourcepins={}
 for name,rec in expected['files'].items():
  f=source/name;require(f.stat().st_size==rec['bytes'] and sha(f)==rec['SHA256'],'source file mismatch');sourcepins[name]=rec
 chunks=[]
 for rec in expected['months']:
  f=source/'months'/(rec['month']+'.npz');require(f.stat().st_size==rec['source_NPZ_bytes'] and sha(f)==rec['source_NPZ_SHA256'],'month hash mismatch')
  with np.load(f,allow_pickle=False) as z:chunks.append({k:z[k].copy() for k in ['times']+[s+suffix for s in symbols for suffix in ['_open','_mark']]})
  sourcepins['months/'+f.name]={'bytes':f.stat().st_size,'SHA256':sha(f)}
 t=np.concatenate([x['times'] for x in chunks]);require(np.array_equal(t,np.arange(START,END,MINUTE,dtype=np.int64)),'minute grid')
 data={k:np.concatenate([x[k] for x in chunks]) for k in chunks[0] if k!='times'};del chunks
 require(all(np.isfinite(x).all() and (x>0).all() for x in data.values()),'nonpositive/nonfinite prices')
 events=json.loads((source/'EVENTS.json').read_text());slots=list(range(START,END,8*60*MINUTE));emap={};actual={}
 for e in events:
  slot=START+((e['event_us']-START)//(8*60*MINUTE))*(8*60*MINUTE);key=(e['symbol'],slot)
  require(key not in emap,'duplicate funding slot');require(e['symbol'] in symbols and slot in slots and 0<=e['event_us']-slot<=1000000,'unsupported funding clock offset');require(e['reported_interval_hours']==8 and np.isfinite(e['raw_rate']),'funding unit/interval');emap[key]=e['raw_rate'];actual[key]=e['event_us']
 require(len(emap)==len(slots)*len(symbols) and all((s,T) in emap for s in symbols for T in slots),'complete funding grid')
 # Independent flat-price arithmetic checks and SHORT funding sign, not fitted data.
 require(abs(calc(100,100,.001,100)['funding']-.001)<1e-15,'SHORT funding sign')
 require(abs(calc(100,100,0,100)['net']+.0027)<1e-15,'BASE27 flat-price cost')
 rows=[];excluded=[]
 for T in slots:
  times=[T-5*MINUTE,T+5*MINUTE,T+55*MINUTE,T+65*MINUTE,T-2*MINUTE]
  for s in symbols:
   if min(times)<START or max(times)>=END:
    excluded.append({'symbol':s,'event_us':T,'reason':'required minute outside fixed2023 source'});continue
   ids=[int((x-START)//MINUTE) for x in times];op=data[s+'_open'];mark=float(data[s+'_mark'][ids[4]])
   require(times[0]<actual[s,T]<times[1],'actual event lies strictly inside fixed event window')
   require(times[4]+MINUTE-1000<T and times[4]+MINUTE<T,'strictly past mark')
   require(not any(times[2]<=actual[s,u]<=times[3] for u in slots),'control has actual funding')
   ev=calc(float(op[ids[0]]),float(op[ids[1]]),emap[s,T],mark);co=calc(float(op[ids[2]]),float(op[ids[3]]),0,0)
   r={'symbol':s,'scheduled_slot_us':T,'event_us':actual[s,T],'day':int((T-START)//DAY),'month':str(np.datetime64(T//1000000,'s'))[:7],'raw_rate_fraction':emap[s,T]}
   for k,v in ev.items():r['event_'+k]=v*10000
   for k,v in co.items():r['control_'+k]=v*10000
   r['paired_net']=r['event_net']-r['control_net'];r['paired_price']=r['event_price']-r['control_price'];r['paired_cost_difference']=r['event_execution_cost']+r['event_fee']-r['control_execution_cost']-r['control_fee']
   r['break_even_total_roundtrip_cost_allowance']=r['event_price']+r['event_funding']
   r['additional_cost_headroom']=r['event_net'];rows.append(r)
 require(len(rows)==5470 and len(excluded)==5 and all(x['event_us']==START for x in excluded),'unexpected exclusions')
 keys=[k for k in rows[0] if k.startswith(('event_','control_','paired_')) and k!='event_us']+['break_even_total_roundtrip_cost_allowance','additional_cost_headroom']
 def aggregate(rs):return {'paired_samples':len(rs),'mean_bps':{k:float(np.mean([r[k] for r in rs])) for k in keys},'positive_event_net_samples':sum(r['event_net']>0 for r in rs),'positive_paired_net_samples':sum(r['paired_net']>0 for r in rs)}
 daily=[]
 for d in range(365):
  rs=[r for r in rows if r['day']==d];require(len(rs)==(10 if d==0 else 15),'daily sample count');daily.append({'day':d,**aggregate(rs)['mean_bps']})
 values=np.array([[d['event_net'],d['paired_net']] for d in daily]);rng=np.random.default_rng(spec['uncertainty']['seed']);bs=[]
 for _ in range(2000):
  ix=((rng.integers(0,365,size=27)[:,None]+np.arange(14))%365).ravel()[:365];bs.append(values[ix].mean(0))
 ci=np.percentile(np.array(bs),[2.5,97.5],axis=0)
 result={'status':'COMPLETE_FIXED_EVENT_WINDOW_ATTRIBUTION_NOT_WALLET','spec_SHA256':sha(here/'SPEC.json'),'code_SHA256':sha(pathlib.Path(__file__)),'source_recovery_commit':spec['source_recovery_commit'],'source_pins':sourcepins,'calendar_days':365,'scheduled_asset_events':len(events),'paired_samples':len(rows),'boundary_exclusions':excluded,'full_year_pooled':aggregate(rows),'by_asset':{s:aggregate([r for r in rows if r['symbol']==s]) for s in symbols},'by_month':{m:aggregate([r for r in rows if r['month']==m]) for m in sorted({r['month'] for r in rows})},'calendar_day_equal_weight_mean_bps':{'event_net':float(values[:,0].mean()),'paired_net':float(values[:,1].mean())},'day_block_bootstrap_interval_bps':{'event_net':ci[:,0].tolist(),'paired_net':ci[:,1].tolist()},'bootstrap':spec['uncertainty'],'funding_clock_unit_checks':{'timestamp_unit':'microseconds since Unix epoch','raw_rate_treated_as_fraction_not_percent':True,'all_scheduled_slots_exact_fixed8h':True,'actual_event_offsets_us':sorted(set(actual[s,T]-T for s,T in actual)),'offset_event_count':sum(actual[s,T]!=T for s,T in actual),'max_mapping_tolerance_us':1000000,'actual_event_timestamps_preserved':True,'all_reported_interval_hours':8,'short_positive_rate_credit_verified':True,'control_funding_events':0,'strict_past_mark_close_lag_minutes':1,'mark_bar_open_offset_us':-2*MINUTE,'raw_mark_close_endpoint_offset_us':-MINUTE-1000,'logical_mark_available_offset_us':-MINUTE,'mark_selection':'fixed conservative proxy, not exact original latest eligible mark'},'account_advances':0,'fits':0,'provider_downloads':0,'limitations':spec['limitations']}
 p.output.mkdir();write(p.output/'RESULT.json',result)
 with (p.output/'EVENT_MAPPING.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['symbol','scheduled_slot_us','actual_event_us','status'])
  for T in slots:
   for s in symbols:w.writerow([s,T,actual[s,T],'boundary_excluded' if T==START else 'paired'])
 with (p.output/'DAILY.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(daily[0]));w.writeheader();w.writerows(daily)
 print(json.dumps({k:result[k] for k in ['status','paired_samples','calendar_day_equal_weight_mean_bps','day_block_bootstrap_interval_bps']},indent=2))
if __name__=='__main__':main()
