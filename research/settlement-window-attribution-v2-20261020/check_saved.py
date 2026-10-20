from pathlib import Path
import csv,json,hashlib,numpy as np
B=Path(__file__).resolve().parent;O=B/'result';S=B.parent/'public_2023_source_restore/reconstructed_source';START=1672531200000000;END=1704067200000000;HOUR=3600000000
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((O/'RESULT.json').read_text());spec=json.loads((B/'SPEC.json').read_text())
assert h(B/'SPEC.json')==r['spec_SHA256']=='d5965868e3ad30095069a1aebe1be9e303bce84bb21012ba569ebe6d648dd383'
assert h(B/'analyze.py')==r['code_SHA256']=='a57117e7ca7a30e1bd96142cac1986caadfaac550a4127ad3ebb76137f20e7e8'
m=list(csv.DictReader((O/'EVENT_MAPPING.csv').open()));d=[{k:float(v) for k,v in x.items()} for x in csv.DictReader((O/'DAILY.csv').open())];assert len(m)==5475 and len(d)==365 and [x['day'] for x in d]==list(range(365))
events=json.loads((S/'EVENTS.json').read_text());assert h(S/'EVENTS.json')==r['source_pins']['EVENTS.json']['SHA256'];actual={(e['symbol'],e['event_us']) for e in events};assert len(actual)==5475
expected={(s,t) for s in spec['assets'] for t in range(START,END,8*HOUR)};seen=set();offsets=[]
for x in m:
 s=x['symbol'];t=int(x['scheduled_slot_us']);a=int(x['actual_event_us']);assert (s,t) in expected and (s,t) not in seen;seen.add((s,t));assert (s,a) in actual and 0<=a-t<=1000000;assert x['status']==('boundary_excluded' if t==START else 'paired');offsets.append(a-t)
assert seen==expected and r['paired_samples']==5470 and len(r['boundary_exclusions'])==5
assert {(x['symbol'],x['event_us']) for x in r['boundary_exclusions']}=={(s,START) for s in spec['assets']}
def check(x):
 for p in ['event','control']:assert abs(x[p+'_net']-(x[p+'_price']+x[p+'_funding']-x[p+'_execution_cost']-x[p+'_fee']))<1e-10
 assert abs(x['paired_net']-(x['event_net']-x['control_net']))<1e-10
 assert abs(x['paired_net']-(x['paired_price']+x['event_funding']-x['paired_cost_difference']))<1e-10
 assert abs(x['break_even_total_roundtrip_cost_allowance']-x['event_price']-x['event_funding'])<1e-10
 assert x['additional_cost_headroom']==x['event_net'] and x['control_funding']==0
for x in d:check(x)
for a in [r['full_year_pooled'],*r['by_asset'].values(),*r['by_month'].values()]:check(a['mean_bps'])
assert len(r['by_asset'])==5 and len(r['by_month'])==12
assert all(x['mean_bps']['event_net']<0 for x in [*r['by_asset'].values(),*r['by_month'].values()])
weights=np.array([10]+[15]*364);assert weights.sum()==5470
for k in r['full_year_pooled']['mean_bps']:assert abs(np.average([x[k] for x in d],weights=weights)-r['full_year_pooled']['mean_bps'][k])<1e-10
v=np.array([[x['event_net'],x['paired_net']] for x in d]);rng=np.random.default_rng(20261020);means=[]
for _ in range(2000):
 ix=np.concatenate([(int(start)+np.arange(14))%365 for start in rng.integers(0,365,27)])[:365];means.append(v[ix].mean(axis=0))
ci=np.percentile(means,[2.5,97.5],axis=0)
for j,k in enumerate(['event_net','paired_net']):assert abs(v[:,j].mean()-r['calendar_day_equal_weight_mean_bps'][k])<1e-12;assert np.array_equal(ci[:,j],r['day_block_bootstrap_interval_bps'][k])
out=dict(status='PASS_INDEPENDENT_SAVED_EVENT_ATTRIBUTION_CHECK',paired_samples=5470,boundary_exclusions=5,actual_scheduled_mapping_verified=5475,offset_event_count=int(np.count_nonzero(offsets)),saved365day_accounting_and_pooled_weighting_verified=True,joint2000_draw14day_circular_bootstrap_exact=True,event_day_mean_bps=float(v[:,0].mean()),paired_day_mean_bps=float(v[:,1].mean()),bootstrap_intervals_bps=ci.T.tolist(),all12months_and5assets_event_net_negative=True,source_analysis_rerun=False,wallet_or_account_advances=0,limitations='Conditional retrospective unit-notional attribution only; non-executable1USDT, fixed charge-mark proxy, no causal identification or annualized wallet return.',pins={str(p.relative_to(B)):dict(bytes=p.stat().st_size,sha256=h(p)) for p in [B/'SPEC.json',B/'analyze.py',O/'RESULT.json',O/'DAILY.csv',O/'EVENT_MAPPING.csv']})
p=O/'INDEPENDENT_SAVED_REVIEW.json';p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=h(p),result=out)))
