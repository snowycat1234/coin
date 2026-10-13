"""Read-only whole-calendar comparison of frozen SMA and reused genuine CS."""
import argparse,gzip,io,json,time,zipfile
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
from native_apis import HERE,ROOT,SYMBOLS,DAY,native,git,sha,file_sha,save,proto,verify
from driver import directional_parts

PREFIXES={'Y2023':'research/quantity-grid-sensitivity-20261012/result/P2/CS_MATCHED/',
          'Y2025':'research/portfolio-risk-2025-native-20261012/result/Y2025/CS_MATCHED/'}
FINANCIAL=('scripts/investment/resumable_perpetual.py',
           'scripts/investment/perpetual_closing_exempt_account.py',
           'research/quantity-grid-sensitivity-20261012/grid_account.py',
           'src/quant/perpetual_account.py')

def control(key):
 W=proto()['windows'][key];commit=W['CS_packet_commit'];prefix=PREFIXES[key]
 index_raw=git(commit+':'+prefix+'INDEX.json');ix=json.loads(index_raw);parts=[]
 for r in ix['parts']:
  b=git(commit+':'+prefix+r['file']);assert len(b)==r['bytes'] and sha(b)==r['SHA256'];parts.append(b)
 raw=b''.join(parts);assert len(raw)==ix['packet_bytes'] and sha(raw)==ix['packet_SHA256']
 members={r['name']:r for r in ix['members']};selected={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==len(members) and set(z.namelist())==set(members)
  def read(name):
   b=z.read(name);r=members[name];assert len(b)==r['bytes'] and sha(b)==r['SHA256'];return b
  for name in ('RESULT.json','BINDING.json','ACCOUNT.json','DAILY.csv','recovery/POINTER.json'):selected[name]=read(name)
  ptr=json.loads(selected['recovery/POINTER.json']);b=read('recovery/'+ptr['snapshot_path']);assert sha(b)==ptr['snapshot_SHA256'];snapshot=json.loads(gzip.decompress(b))
 result=json.loads(selected['RESULT.json']);binding=json.loads(selected['BINDING.json']);body=json.loads(selected['ACCOUNT.json'])
 for name in ('RESULT.json','BINDING.json'):assert selected[name]==git(W['CS_summary_commit']+':'+W['CS_summary_prefix']+'/'+name)
 assert body['summary']==result['summary'] and ptr['state_hash']==result['genuine_state_hash']
 assert ptr['binding']==binding and ptr['completed_minutes']==525600
 assert binding['source_index_SHA256']==json.loads((HERE/'input/READINESS.json').read_text())['years'][key]['source_index_SHA256']
 clocks=[native.utc(x) for x in W['calendar']]
 assert snapshot['market_range']==clocks and tuple(snapshot['symbols'])==SYMBOLS
 assert snapshot['persist_cash_close'] is False and snapshot['final_day_target_zero'] is False
 assert snapshot['cost']==native.COSTS[0] and snapshot['unit']==native.UNITS[0]
 assert snapshot['state']['rows_written']==525600 and snapshot['state']['cursor']==clocks[1]
 assert Decimal(snapshot['account']['config']['initial_cash'])==10000
 assert result['summary']['clock_us']==clocks[1] and result['calendar']==W['calendar']
 code={}
 for path in FINANCIAL:
  b=git(binding['science_source_commit']+':'+path);assert sha(b)==file_sha(ROOT/path);code[path]=sha(b)
 daily=native.pl.read_csv(io.BytesIO(selected['DAILY.csv']));np.testing.assert_array_equal(daily['close_us'].to_numpy(),np.arange(clocks[0]+DAY,clocks[1]+1,DAY))
 with localcontext() as c:c.prec=50;directions=directional_parts(body)
 meta=dict(status='REUSED_PUBLIC_GENUINE_CS_NO_ADVANCE',summary_commit=W['CS_summary_commit'],packet_commit=commit,packet_prefix=prefix,index_SHA256=sha(index_raw),packet_SHA256=ix['packet_SHA256'],DAILY_SHA256=sha(selected['DAILY.csv']),snapshot_SHA256=ptr['snapshot_SHA256'],state_hash=ptr['state_hash'],financial_code_SHA256=code,market_range=clocks,cost=snapshot['cost'],unit=snapshot['unit'],inception_config=snapshot['account']['config'],persist_cash_close=False,final_day_target_zero=False,terminal_signal_us=clocks[1]-360000000,account_advances=0,new_wallets=0,downloads=0)
 return result,binding,daily,directions,meta

def numbers(result,daily,directions):
 s=result['summary'];b=result['independent_decimal_NAV_bridge'];nav=np.r_[10000.,daily['nav'].to_numpy()];r=np.diff(nav)/nav[:-1]
 out=dict(marked_net_USDT=s['net_PnL'],marked_return=s['net_PnL']/10000,paid_flat=s['terminal_cash_realized'],paid_cash_return=s['net_PnL']/10000 if s['terminal_cash_realized'] else None,terminal_marked_notional=s['terminal_marked_notional'],price_gross_USDT=b['gross_price_USDT'],fees_USDT=b['fees_USDT'],execution_USDT=b['execution_USDT'],funding_USDT=b['funding_cash_USDT'],spread_USDT=str(Decimal(b['execution_USDT'])/2),slippage_USDT=str(Decimal(b['execution_USDT'])/2),annual_daily_vol=float(r.std(ddof=1)*np.sqrt(365)),minute_DD=s['all_observation_max_drawdown'],worst30=float((nav[30:]/nav[:-30]-1).min()),direction_contributions=directions,inventory=s['positions'])
 m=result['metrics'];e=s.get('realized_exposure',{})
 out['mean_actual_gross']=m.get('mean_actual_gross',e.get('minute_mean_gross_weight'))
 out['max_actual_gross']=m.get('max_actual_gross',m.get('maximum_actual_gross',e.get('minute_max_gross_weight')))
 out['mean_signed_net']=m.get('mean_signed_net',m.get('mean_actual_signed_net',e.get('minute_mean_net_signed_weight')))
 out['max_abs_signed_net']=m.get('max_abs_signed_net',m.get('maximum_absolute_actual_net',max(abs(e.get('minute_max_net_signed_weight',0)),abs(e.get('minute_min_net_signed_weight',0)))))
 return out

def run(out):
 assert not out.exists();verify();begin=time.monotonic();years={}
 for key in ('Y2023','Y2025'):
  cs,cb,cd,dirs,meta=control(key);folder=HERE/'summary'/key;sma=json.loads((folder/'RESULT.json').read_text());sb=json.loads((folder/'BINDING.json').read_text());sd=native.pl.read_csv(folder/'DAILY.csv');np.testing.assert_array_equal(sd['close_us'].to_numpy(),cd['close_us'].to_numpy())
  assert sma['full_calendar'] and sma['inventory_audit']=='PASS' and cs['inventory_audit']=='PASS'
  assert sma['summary']['contract']==cs['summary']['contract'] and sma['summary']['cost_scenario']==cs['summary']['cost_scenario']
  for field in ('account_class','contract_from_initial_capital','quantity_profile_SHA256','source_index_SHA256'):assert sb[field]==cb[field],field
  assert sb['calendar']==sma['calendar']==cs['calendar'] and sb['end_us']==meta['market_range'][1] and sb['terminal_signal_us']==meta['terminal_signal_us']
  sn=numbers(sma,sd,sma['direction_contributions']);cn=numbers(cs,cd,dirs);snav=np.r_[10000.,sd['nav'].to_numpy()];cnav=np.r_[10000.,cd['nav'].to_numpy()];sr=np.diff(snav)/snav[:-1];cr=np.diff(cnav)/cnav[:-1];months=[]
  for month in range(1,13):
   year=int(key[1:]);lo=native.utc(f'{year}-{month:02d}-01');hi=native.utc(f'{year+(month==12)}-{1 if month==12 else month+1:02d}-01');ids=np.flatnonzero((sd['close_us'].to_numpy()>lo)&(sd['close_us'].to_numpy()<=hi));assert len(ids)==(hi-lo)//DAY;first,last=ids[0],ids[-1];sv=float(snav[last+1]-snav[first]);cv=float(cnav[last+1]-cnav[first]);months.append(dict(month=f'{year}-{month:02d}',days=len(ids),SMA_NAV_change_USDT=sv,CS_NAV_change_USDT=cv,SMA_minus_CS_USDT=sv-cv,no_reset=True))
  years[key]=dict(calendar=sma['calendar'],days=365,SMA200_10PCT=sn,REUSED_CS=cn,SMA_minus_CS_marked_net_USDT=sn['marked_net_USDT']-cn['marked_net_USDT'],SMA_minus_CS_marked_return=sn['marked_return']-cn['marked_return'],paired_mean_daily_return_difference=float((sr-cr).mean()),paired_daily_SMA_higher=int((sr>cr).sum()),monthly_continuous=months,paid_cash_difference='NOT_AVAILABLE_EITHER_ARM_UNPAID',compatibility='EXACT_CALENDAR_NATIVE_CODE_CONTRACT_SOURCE_COST_UNIT_CAPITAL_QUANTITY_TERMINAL; TARGET_RISK_RULES_AND_REALIZED_EXPOSURES_DIFFER',CS_source_proof=meta)
 save(out,dict(status='COMPLETE_DESCRIPTIVE_FULL_YEAR_NATIVE_BASELINE_COMPARISON_NOT_INVESTMENT_ADOPTION',years=years,new_wallets=0,new_fits=0,new_RNG=0,old_wallet_replays=0,downloads=0,bootstrap='NOT_REQUESTED_NOT_RUN',seconds=time.monotonic()-begin))
 print('ACTUAL_SMA_CS_READONLY_COMPARISON_PASS',time.monotonic()-begin,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
