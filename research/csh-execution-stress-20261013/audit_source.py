"""Read-only original-tape capacity, midpoint and strict-past funding-mark audit."""
import argparse,datetime,functools,gzip,hashlib,json
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
from recover import STATE,REPO
D=Decimal
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(case):
 out=STATE/'wallets'/case;result=json.loads((out/'RESULT.json').read_text());year=result['year'];source=STATE/f'prepared_{year}'
 binding=json.loads((out/'BINDING.json').read_text());pointer=json.loads((out/'recovery/POINTER.json').read_text());snapshot=json.loads(gzip.decompress((out/'recovery'/pointer['snapshot_path']).read_bytes()))
 original=json.loads((REPO/'research/csh-execution-stress-20261013/SOURCE_BINDINGS.json').read_text())[str(year)]['source_index']
 for r in original['months']:
  p=source/'months'/(r['month']+'.npz');assert sha(p)==r['source_NPZ_SHA256'] and p.stat().st_size==r['source_NPZ_bytes']
 assert sha(source/'EVENTS.json')==original['files']['EVENTS.json']['SHA256']
 raw_events=json.loads((source/'EVENTS.json').read_text());raw={(r['symbol'],r['event_us']):r for r in raw_events};assert len(raw)==5475
 @functools.lru_cache(maxsize=2)
 def month(stamp):
  with np.load(source/'months'/(stamp+'.npz'),allow_pickle=False) as z:
   return {n:z[n].copy() for n in z.files if n=='times' or n.endswith(('_open','_quote_volume','_mark'))}
 def value(stamp,s,field):
  name=datetime.datetime.fromtimestamp(stamp/1e6,datetime.UTC).strftime('%Y-%m');a=month(name);i=int(np.searchsorted(a['times'],stamp));assert i<len(a['times']) and a['times'][i]==stamp
  return D(str(a[s+'_'+field][i]))
 budgets={};rate_checks=mark_checks=0
 with localcontext() as ctx:
  ctx.prec=50
  for r in snapshot['account']['trades']:
   t=(r['event_us']-1)//60000000*60000000;s=r['symbol'];x=r['decimal_strings'];assert r['event_us']==t+1
   assert D(x['mid_price'])==value(t,s,'open');key=(s,t);budgets[key]=budgets.get(key,D(0))+D(x['quantity'])
  for (s,t),quantity in budgets.items():
   assert t-60000000>=binding['calendar'][0]
   cap=value(t-60000000,s,'quote_volume')*D(binding['capacity_fraction'])/value(t,s,'open')
   assert quantity<=cap+D('1e-25'),(case,s,t,quantity,cap)
  for r in snapshot['state']['funding_journal']:
   e=raw[r['symbol'],r['event_us']]
   for k in ('raw_rate','reported_interval_hours'):assert r[k]==e[k]
   rate_checks+=1
   if r['quantity']==0:continue
   latest_open=((r['event_us']-1)//60000000)*60000000-60000000
   assert r['mark_close_us']==latest_open+60000000<r['event_us']
   assert D(r['decimal_strings']['mark_price'])==value(latest_open,r['symbol'],'mark');mark_checks+=1
  # Finally-restored quote at completed state must still be the actual raw tape.
  previous=binding['calendar'][0]+(snapshot['state']['rows_written']-1)*60000000
  for s,q in snapshot['state']['previous_quote'].items():assert D(str(q))==value(previous,s,'quote_volume')
 return dict(status='PASS_TRUE_SOURCE_QUOTE_CAPACITY_AND_FUNDING_MARKS',case=case,original_month_NPZ_hashes_checked=12,raw_funding_events_checked=rate_checks,owned_strict_prior_marks_checked=mark_checks,shared_symbol_minute_fill_budgets_checked=len(budgets),capacity_fraction=binding['capacity_fraction'],no_repeated_scaling_in_persisted_quotes=True,raw_OHLC_volume_and_marks_unchanged=True,account_constructions=0,account_advances=0,financial_imports=0,provider_downloads=0)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.case)
 with a.output.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(r))
