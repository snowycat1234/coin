"""One saved public 2023 scheduler, existing restore/NAV APIs, zero advances."""
import argparse,json,sys,time
from decimal import Decimal,localcontext
from pathlib import Path

HERE=Path(__file__).resolve().parent
q=argparse.ArgumentParser();q.add_argument('--account',type=Path,required=True);q.add_argument('--prepared',type=Path,required=True);q.add_argument('--output',type=Path,required=True);a=q.parse_args();assert not a.output.exists();begin=time.monotonic();blocked=[]
prefixes=json.loads((HERE/'evidence/ORIGINAL_FINANCIAL_PREFIXES.json').read_text())
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)) and any(Path(args[0]).absolute().is_relative_to(Path(p)) for p in prefixes):blocked.append(str(args[0]));raise RuntimeError('Original financial STATE forbidden')
sys.addaudithook(audit)
import driver as m
m.verify();ix=json.loads((HERE/'preserved/Y2023/INDEX.json').read_text());binding=json.loads((a.account/'BINDING.json').read_text());body=json.loads((a.account/'ACCOUNT.json').read_text())
for name in ('BINDING.json','ACCOUNT.json','MINUTE_NUMERIC.json','DAILY.csv','recovery/POINTER.json'):assert m.sha(a.account/name)==ix['members'][name]['SHA256']
identity=m.load('saved_cold_expected_identity',HERE/'archive.py')
for k,v in identity.expected('Y2023').items():assert binding[k]==v,k
prior=json.loads((a.prepared.parent/'PUBLIC_RESTORE.json').read_text());assert prior['status']=='PASS_EXACT_PUBLIC_FOLLOW_ZERO_ADVANCE' and prior['observed_STATE_open_attempts']==prior['account_advances']==0;assert m.sha(a.prepared/'SOURCE_INDEX.json')==binding['source_index_SHA256']
win=m.follow.window('Y2023',a.prepared);snapshot,pointer=m.restore_snapshot(a.account/'recovery',binding);assert pointer['snapshot_SHA256']==ix['genuine_snapshot_SHA256'] and pointer['state_hash']==ix['genuine_state_hash'];assert snapshot['persist_cash_close'] is True and snapshot['final_day_target_zero'] is False
print('ACTUAL_SAVED_NATIVE_RESTORE_LOADING_NO_ADVANCE',pointer['completed_minutes'],flush=True)
sim=m.native.NativeDailySimulator.from_snapshot(snapshot,win,account_class=m.Closing)
assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and sim.rows_written==525600 and sim.cursor==win['end'] and sim.stop is None
case=sim.result();assert case['summary']==body['summary']
for k in ('trades','funding','rejections','breaches','extrema','target_meta'):assert case[k]==body[k],k
assert case['targets'].to_dicts()==body['targets'] and case.get('liquidations',[])==body['liquidations'];f=m.load('saved_cold_minute_fingerprint',m.ROOT/'research/cs-continuous-economics-20261012/persistence.py');columns=f.minute_fingerprint(case['minute']);assert len(columns)==37 and columns==json.loads((a.account/'MINUTE_NUMERIC.json').read_text())['columns']
daily=case['minute'].filter(m.native.pl.col('close_us')%m.DAY==0);assert daily.write_csv().encode()==(a.account/'DAILY.csv').read_bytes()
_,inventory=m.native.episodes(case['trades'],m.SYMBOLS)
for s in m.SYMBOLS:assert inventory[s]==sim.account.positions[s].quantity==0
finance=m.native.nav_bridge(case['trades'],case['funding'],inventory,body['summary']['terminal_mark_prices'],sim.account.nav())
assert len(case['funding'])==len(win['events'])==5475;trades=case['trades'];owned={s:Decimal(0) for s in m.SYMBOLS};cursor=0;max_error=Decimal(0);fund_sum=Decimal(0);owned_events=0
with localcontext() as ctx:
 ctx.prec=40
 for r,raw in zip(case['funding'],win['events'],strict=True):
  for k,v in raw.items():assert r[k]==v,k
  while cursor<len(trades) and trades[cursor]['event_us']<r['event_us']:
   t=trades[cursor];owned[t['symbol']]+=Decimal(t['decimal_strings']['position_delta']);cursor+=1
  strings=r.get('decimal_strings',{});quantity=Decimal(strings.get('quantity',str(r['quantity'])));assert quantity==owned[r['symbol']];assert bool(quantity)==r['owned'];rate=Decimal(r['assumed_fraction_decimal']);assert rate==Decimal(str(raw['raw_rate']))*Decimal(str(sim.unit['scale']));charge=Decimal(strings.get('signed_funding_USDT',str(r['signed_funding_USDT'])))
  if r['mark_price'] is None:assert quantity==charge==0;expected=Decimal(0)
  else:
   assert r['mark_close_us']<=r['event_us'];mark=Decimal(strings['mark_price']);expected=-quantity*mark*rate
  error=abs(charge-expected);max_error=max(max_error,error);assert error<Decimal('1e-24');fund_sum+=charge;owned_events+=bool(quantity)
 assert abs(fund_sum-Decimal(body['summary']['decimal_strings']['funding_USDT']))<Decimal('1e-24')
assert sim.state_hash()==pointer['state_hash'] and sim.account.snapshot()==snapshot['account'] and not blocked
out=dict(status='PASS_SAVED_PUBLIC_2023_NATIVE_ZERO_ADVANCE',source_code_SHA256=m.sha(Path(__file__)),saved_account_artifact='3bc4a2ec24186696ab582c4e4a7669c0393a9dbd',rows=sim.rows_written,minute_columns=37,all37minute_bits_clocks_and_original_NPZ_SHA='EXACT',daily_csv_journals_targets_summary='EXACT',scheduler_flags_pending_previous_quote_dedup_and_account='EXACT',genuine_state_hash=pointer['state_hash'],snapshot_SHA256=pointer['snapshot_SHA256'],source_index_SHA256=binding['source_index_SHA256'],source='REUSED_ALREADY_VERIFIED_PUBLIC_SOURCE_CACHE_EXISTING_WINDOW_ADAPTER_NO_NEW_SOURCE_RECOVERY',native_loader='UNCHANGED_FROM_SNAPSHOT_PASSIVE_MARKET_TAPE_CURSOR_RESTORATION_NO_FINANCIAL_TRANSITIONS',independent_decimal_NAV_bridge=finance,inventory={s:str(v) for s,v in inventory.items()},funding_events=5475,owned_funding_events=owned_events,independent_funding_cash_USDT=str(fund_sum),maximum_independent_funding_error_USDT=str(max_error),paid_flat=body['summary']['terminal_cash_realized'],account_advances=0,wallet_replays=0,new_wallets=0,new_fits=0,RNG_draws=0,downloads=0,new_agents=0,original_financial_STATE_open_attempts=len(blocked),original_CI='NOT_AVAILABLE_NOT_RESAMPLED',Y2025='NOT_RUN',full_two_year_experiment='INCOMPLETE',venue_PIT_funding_unit_authority='UNCHANGED_CONDITIONAL_NOT_CERTIFIED',seconds=time.monotonic()-begin);m.save(a.output,out);print('ACTUAL_SAVED_2023_NATIVE_COLD_PASS',sim.rows_written,finance['NAV'],out['seconds'],flush=True)
