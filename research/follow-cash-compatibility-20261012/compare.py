"""Read-only matched paid economics and known-CASH journal diagnostics."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
from driver import HERE,OLD,follow,b,sha,save,SYMBOLS,MINUTE,targets
ARTIFACT={'Y2023':'9bdaf54178fb08e66d8e1fd58f72ddc77be3c525','Y2025':'1b7ee23dd2122b9a3df06ee1680300a8e1e7771e'}
def old_public(key):
 prefix='research/rejected-break-follow-native-20261012/result/'+key+'/';ix=json.loads(b.git('show',ARTIFACT[key]+':'+prefix+'INDEX.json'));pieces=[]
 for r in ix['parts']:
  data=b.git('show',ARTIFACT[key]+':'+prefix+r['file']);assert hashlib.sha256(data).hexdigest()==r['SHA256'] and len(data)==r['bytes'];pieces.append(data)
 raw=b''.join(pieces);assert hashlib.sha256(raw).hexdigest()==ix['packet_SHA256'];out={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  for name in ('ACCOUNT.json','MINUTE_NUMERIC.json','DAILY.csv'):
   data=z.read(name);r=next(v for v in ix['members'] if v['name']==name);assert hashlib.sha256(data).hexdigest()==r['SHA256'] and len(data)==r['bytes'];out[name]=data
 return out,ix
def clocks(body,d,w):
 lookup={(int(at),s):float(w[i,j]) for i,at in enumerate(d) for j,s in enumerate(SYMBOLS)};risk={r['signal_us'] for r in body['breaches']};closes=[];ambiguous=[]
 for r in body['trades']:
  if r['leg']=='CLOSE' and lookup.get((r['signal_us'],r['symbol']))==0:
   if r['signal_us'] in risk:ambiguous.append(r);continue
   closes.append(r)
 late=[r for r in closes if r['event_us']>r['signal_us']+5*MINUTE+1];flat=[r for r in closes if r['quantity_after']==0];reasons={}
 for r in body['rejections']:
  if r.get('reason','').startswith('SUPERSEDED_BY_') or r.get('kind')=='DAILY_TARGET':reason=r['reason'];reasons[reason]=reasons.get(reason,0)+1
 return dict(zero_target_close_fills=len(closes),after_fifth_attempt_paid_close_fills=len(late),zero_target_flat_close_legs=len(flat),max_observed_zero_target_flat_latency_minutes=max(((r['event_us']-r['signal_us']-1)/MINUTE for r in flat),default=0),ambiguous_risk_same_daily_clock_fills=len(ambiguous),journal_override_or_expiry_reasons=reasons,scope='Exactdailyzero-targetclockmatches; sameclockriskambiguities excluded, no inferred universal executiondeadline',late_fees_USDT=float(sum(r['fee_USDT_mid'] for r in late)),late_execution_cost_USDT=float(sum(r['execution_cost'] for r in late)))
def compare(key,state,dest):
 assert not dest.exists();saved,ix=old_public(key);a=json.loads(saved['ACCOUNT.json']);z=json.loads((state/'ACCOUNT.json').read_text());r=json.loads((state/'RESULT.json').read_text());old=json.loads((OLD/'summary'/key/'RESULT.json').read_text());assert a['summary']==old['summary'];d,w=targets(key);assert a['targets']==z['targets'];baseline_binding=json.loads((OLD/'summary'/key/'BINDING.json').read_text());new_binding=json.loads((state/'BINDING.json').read_text())
 for k in ('source_index_SHA256','target_archive_SHA256','quantity_profile_SHA256','account_class','calendar','end_us','terminal_signal_us','contract_from_initial_capital'):assert baseline_binding[k]==new_binding[k],k
 assert a['summary']['contract']==z['summary']['contract'] and a['summary']['terminal_cash_realized'] and z['summary']['terminal_cash_realized'];fields=('net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','realized_PnL','NAV');changes={k:float(z['summary'][k]-a['summary'][k]) for k in fields};fm=json.loads((state/'MINUTE_NUMERIC.json').read_text())['columns'];origfm=json.loads(saved['MINUTE_NUMERIC.json'])['columns'];exact=fm==origfm;finance_old=old['independent_decimal_NAV_bridge'];finance_new=r['independent_decimal_NAV_bridge'];from decimal import Decimal
 deltas={k:str(Decimal(finance_new[k])-Decimal(finance_old[k])) for k in ('gross_price_USDT','execution_USDT','fees_USDT','funding_cash_USDT','NAV')};bridge=Decimal(deltas['gross_price_USDT'])-Decimal(deltas['execution_USDT'])-Decimal(deltas['fees_USDT'])+Decimal(deltas['funding_cash_USDT']);assert abs(bridge-Decimal(deltas['NAV']))<Decimal('1e-18')
 out=dict(status='COMPLETE_READONLY_SAME_CONTRACT_CASH_EXECUTION_PAIR',window=key,baseline_public_artifact=ARTIFACT[key],baseline_packet_SHA256=ix['packet_SHA256'],baseline_state_hash=old['genuine_state_hash'],new_state_hash=r['genuine_state_hash'],targets_all_weights_and_identity='EXACT',unchanged_financial_contract='EXACT',baseline_result='REUSED_NO_ACCOUNT_REPLAY',new_paid_net=r['summary']['net_PnL'],baseline_paid_net=old['summary']['net_PnL'],numeric_delta=changes,independent_decimal_bridge_delta=deltas,minute_all37_fingerprint_bit_identical=exact,daily_csv_bit_identical=(state/'DAILY.csv').read_bytes()==saved['DAILY.csv'],trades_bit_identical=a['trades']==z['trades'],funding_journal_bit_identical=a['funding']==z['funding'],rejections_bit_identical=a['rejections']==z['rejections'],baseline_clock_diagnostic=clocks(a,d,w),candidate_clock_diagnostic=clocks(z,d,w),candidate_risk=r['metrics'],baseline_risk=old['metrics'],candidate_minute_DD=r['summary']['all_observation_max_drawdown'],baseline_minute_DD=old['summary']['all_observation_max_drawdown'],compatibility_economic_acceptance_gates=r['gates'],financial_correctness='PASS_INVENTORY_AND_DECIMAL_NAV_SEPARATE_FROM_NET_ACCEPTANCE',baseline_alpha_STOP='PRESERVED',new_fits=0,account_advances=0,old_wallet_replays=0,provider_downloads=0,scope='SEEN_POSTHOC_KNOWN_RULE_COMPATIBILITY_NOT_ALPHA_OR_ONLY_EXTRA_FEES_ATTRIBUTION');save(dest,out);print('ACTUAL_CASH_COMPAT_PAIR',key,changes['net_PnL'],exact,out['candidate_clock_diagnostic']['after_fifth_attempt_paid_close_fills'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--window',choices=['Y2023','Y2025'],required=True);p.add_argument('--state',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();compare(a.window,a.state,a.destination)
