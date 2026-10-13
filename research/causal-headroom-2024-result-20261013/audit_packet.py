"""Independent HEADROOM packet audit, adapted only to original result schema.
No financial imports, account construction, fitting or historical advance."""
import argparse,csv,gzip,hashlib,io,json,math
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
D=Decimal
CORE=['nav','free_cash','isolated_balance','gross_notional','net_signed_notional','cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover','gross_weight','net_signed_weight']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def audit(folder,target=None):
 import zipfile
 index=json.loads((folder/'INDEX.json').read_text());pieces=[]
 for r in index['parts']:
  raw=(folder/r['name']).read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256'];pieces.append(raw)
 raw=b''.join(pieces);assert len(raw)==index['packet_bytes'] and sha(raw)==index['packet_sha256']
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(index['members']) and z.testzip() is None
  members={n:z.read(n) for n in z.namelist()}
 for n,raw in members.items():assert len(raw)==index['members'][n]['bytes'] and sha(raw)==index['members'][n]['sha256']
 original_result=json.loads(members['RESULT.json']);result=dict(original_result);result.update(case=original_result['case_id'],state_hash=original_result['genuine_state_hash'],binding_sha256=sha(members['BINDING.json']),paid_PnL_USDT=original_result['paid_cash_PnL_USDT'],minute_DD=original_result['minute_drawdown'],mean_gross=original_result['mean_actual_gross'],max_gross=original_result['max_actual_gross'],**json.loads(members['METRICS.json']));bind=json.loads(members['BINDING.json']);pointer=json.loads(members['POINTER.json']);summary=json.loads(members['SUMMARY.json']);snapshot=json.loads(gzip.decompress(members['FINAL_STATE.json.gz']))
 assert pointer['binding']==bind and pointer['state_hash']==result['state_hash']==index['original_state_hash']
 assert sha(members['FINAL_STATE.json.gz'])==pointer['snapshot_SHA256']==index['original_checkpoint_sha256']
 assert sha(members['BINDING.json'])==result['binding_sha256']
 assert snapshot['market_range']==bind['calendar'] and snapshot['state']['rows_written']==result['completed_minutes']==pointer['completed_minutes']
 assert snapshot['account']['status']==result['account_status'] and snapshot['state']['stop']==result['stop_us']
 assert snapshot['cost']==summary['summary']['cost_scenario'] and snapshot['unit']['scale']==1.0
 config=snapshot['account']['config'];assert D(config['initial_cash'])==10000 and D(config['leverage'])==1
 assert D(config['max_asset_weight'])==D('.3') and D(config['max_gross_weight'])==D('.6') and D(config['maintenance_margin_rate'])==D('.005')
 assert D(config['fee_rate'])==D('.00055') and snapshot['account']['closing_min_notional_exempt']
 assert all(D(v['quantity_step'])==D('1e-8') for v in snapshot['account']['instrument_profiles'].values())
 friction=D('.0008')
 assert D(config['half_spread_bps'])==D(config['slippage_bps'])==4
 assert snapshot['protective_policy']['policy_id']=='causal_execution_headroom_full_exit_v1'
 assert snapshot['protective_policy']['terminal_opens']==bind['terminal_opens']==5 and not snapshot['persist_cash_close'] and not snapshot['final_day_target_zero']
 assert snapshot['protective_policy']['feature_binding']==bind['feature_binding']
 assert snapshot['protective_policy']['reused_execution']=='GUARD50_SCHEDULE_ATTEMPT_ADVANCE_DAY_UNCHANGED'
 with np.load(io.BytesIO(members['CORE_MINUTE.npz']),allow_pickle=False) as z:
  values=z['values'].copy();clocks=z['close_us'].copy();assert list(z['columns'])==CORE
 n=result['completed_minutes'];start,end=bind['calendar'];assert values.shape==(n,len(CORE)) and values.dtype==np.float64 and np.isfinite(values).all()
 assert clocks.dtype==np.int64;np.testing.assert_array_equal(clocks,np.arange(n,dtype=np.int64)*60000000+start+60000000)
 fingerprints={r['name']:r for r in json.loads(members['MINUTE_NUMERIC.json'])['columns']};assert len(fingerprints)==37
 for j,name in enumerate(CORE):assert sha(values[:,j].tobytes())==fingerprints[name]['raw_SHA256'] and fingerprints[name]['rows']==n
 assert sha(clocks.tobytes())==fingerprints['close_us']['raw_SHA256']
 assert len(json.loads(members['MINUTE_NUMERIC.json'])['columns'])==37 and sum(r['rows'] for r in pointer['chunks'])==n
 rows=list(csv.DictReader(io.StringIO(members['DAILY.csv'].decode())))
 for r in rows:
  t=int(r['close_us']);assert t%86400000000==0;k=(t-start)//60000000-1;assert 0<=k<n
  for j,name in enumerate(CORE):assert float(r[name])==values[k,j],(name,t)
 if target is not None:
  assert sha(target.read_bytes())==bind['target_archive_SHA256']
  actual=list(csv.DictReader(io.StringIO(members['TARGETS.csv'].decode())))
  with np.load(target,allow_pickle=False) as z:
   names=tuple(z['symbol_order']);targets=z['STATIC50'];decisions=z['decision_us']
  assert len(actual)==len(decisions)*len(names)
  for i,t in enumerate(decisions):
   for j,s in enumerate(names):
    r=actual[i*len(names)+j];assert int(r['available_us'])==t and r['symbol']==s and float(r['target_weight'])==targets[i,j]
 symbols=snapshot['symbols'];quantity={s:D(0) for s in symbols};fees=execution=funding=turnover=gross=D(0);ids=set();terminal_legs=[]
 with localcontext() as ctx:
  ctx.prec=50
  for r in snapshot['account']['trades']:
   x=r['decimal_strings'];s=r['symbol'];q=D(x['quantity']);before=D(x['quantity_before']);after=D(x['quantity_after']);delta=D(x['position_delta']);mid=D(x['mid_price']);fill=D(x['fill_price']);sign=D(1) if r['side']=='BUY' else D(-1)
   assert before==quantity[s] and after==before+delta and delta==sign*q and before*after>=0
   assert q>0 and q/D('1e-8')==(q/D('1e-8')).to_integral_value()
   key=(s,r['event_us'],r['fill_id']);assert key not in ids;ids.add(key)
   assert r['event_us']>=r['signal_us']+60000001
   assert fill==mid*(1+sign*friction)
   assert abs(D(x['fee_amount'])-q*fill*D('.00055'))<D('1e-25')
   assert abs(D(x['execution_cost'])-q*abs(fill-mid))<D('1e-25')
   quantity[s]=after;fees+=D(x['fee_amount']);execution+=D(x['execution_cost']);turnover+=q*fill;gross-=delta*mid
   if r['signal_us']==end-6*60000000:terminal_legs.append(r)
  for r in snapshot['state']['funding_journal']:
   if r['quantity']==0:assert r['signed_funding_USDT']==0;continue
   x=r['decimal_strings'];q=D(x['quantity']);mark=D(x['mark_price']);rate=D(x['rate_fraction']);amount=D(x['signed_funding_USDT'])
   assert rate==D(str(r['raw_rate']))*D(str(r['conditional_rate_scale']))
   assert r['mark_close_us']<r['event_us']
   assert abs(amount+q*mark*rate)<D('1e-25');funding+=amount
  unrealized=D(0);isolated=D(0);residual_gross=D(0)
  for s,q in quantity.items():
   position=snapshot['account']['positions'][s];assert q==D(position['quantity'])==D(result['terminal_residual_quantity'][s])
   if q:
    mark=D(str(summary['summary']['terminal_mark_prices'][s]));gross+=q*mark;unrealized+=q*(mark-D(position['entry_price']));residual_gross+=abs(q*mark)
   isolated+=D(position['isolated_balance'])
  expected=D(10000)+gross-fees-execution+funding
  final=D(snapshot['account']['free_cash'])+isolated+unrealized-D(snapshot['account']['unpaid_liability'])
  error=abs(expected-final);assert error<D('1e-25'),error
  assert abs(expected-D(summary['summary']['decimal_strings']['NAV']))<D('1e-25')
  assert abs(float(expected)-10000-result['marked_PnL_USDT'])<1e-8
  for value,name in ((fees,'fees_USDT'),(execution,'execution_cost_USDT'),(funding,'funding_USDT'),(turnover,'turnover_USDT'),(residual_gross,'terminal_residual_gross_USDT')):assert abs(float(value)-result[name])<1e-8
  full=n==(end-start)//60000000;paid=full and snapshot['state']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and all(q==0 for q in quantity.values())
  assert full==result['full_calendar'] and paid==result['paid_flat'] and (result['paid_PnL_USDT'] is not None)==paid
  if paid:assert result['paid_PnL_USDT']==result['marked_PnL_USDT']
 mean_gross=float(np.mean(values[:,9]));max_gross=float(np.max(values[:,9]));mean_net=float(np.mean(values[:,10]));max_abs_net=float(np.max(np.abs(values[:,10])))
 for v,name in ((mean_gross,'mean_gross'),(max_gross,'max_gross'),(mean_net,'mean_net'),(max_abs_net,'max_abs_net')):assert abs(v-result[name])<1e-13
 np.testing.assert_allclose(values[:,9],values[:,3]/values[:,0],rtol=1e-14,atol=1e-14)
 np.testing.assert_allclose(values[:,10],values[:,4]/values[:,0],rtol=1e-14,atol=1e-14)
 witness=next(r for r in summary['extrema'] if r['kind']=='MAX_DRAWDOWN')
 assert abs(result['minute_DD']-(1-witness['NAV']/witness['peak_NAV']))<1e-15
 close_nav=np.r_[10000.,values[:,0]];close_dd=float(np.max(1-close_nav/np.maximum.accumulate(close_nav)));assert close_dd<=result['minute_DD']+1e-14
 assert snapshot['state']['mdd']==result['minute_DD']
 assert np.all(np.diff(values[:,5])>=-1e-10) and np.all(np.diff(values[:,6])>=-1e-10) and np.all(np.diff(values[:,8])>=-1e-8)
 return dict(status='PASS_READONLY_FINANCIAL_AND_NUMERICAL_PACKET',case=result['case'],core_minute_rows=n,exact_core_float_columns=len(CORE),original_fingerprint_columns=37,daily_rows=len(rows),independent_Decimal_NAV=str(expected),independent_NAV_error=str(error),funding_events_checked=len(snapshot['state']['funding_journal']),trade_legs_checked=len(ids),paid_flat=paid,terminal_paid_close_legs=len(terminal_legs),terminal_close_turnover_USDT=float(sum((D(r['decimal_strings']['quantity'])*D(r['decimal_strings']['fill_price']) for r in terminal_legs),D(0))),terminal_close_fees_USDT=float(sum((D(r['decimal_strings']['fee_amount']) for r in terminal_legs),D(0))),minute_close_DD=close_dd,all_observation_DD_with_witness=result['minute_DD'],financial_imports=0,account_constructions=0,account_advances=0,old_or_new_historical_replays=0,fits=0)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--target',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();r=audit(a.folder,a.target)
 if a.output:
  with a.output.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(r))
