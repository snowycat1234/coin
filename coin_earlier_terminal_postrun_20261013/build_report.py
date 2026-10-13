"""Read-only two-arm report, conditional accounting ablation, no finance advance."""
from __future__ import annotations
from pathlib import Path
import json,hashlib,csv,datetime,math
from decimal import Decimal as D
H=Path(__file__).resolve().parent;R=H.parent;M=R/'coin_earlier_terminal_exit_20261013';S=M/'state_resumed_authorized_once'
SYMS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def utc(t):return datetime.datetime.fromtimestamp(t/1e6,datetime.timezone.utc).isoformat()
def validate_result(r,identity):
 if r['case_id']!=identity or r['year']!=2025 or r['mode']!='ORIGINAL' or r['required_minutes']!=525600:raise ValueError('Foreign result')
 if set(r['terminal_residual_quantity'])!=set(SYMS):raise ValueError('Incomplete terminal inventory')
 full=r['completed_minutes']==525600
 paid=full and r['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and all(D(q)==0 for q in r['terminal_residual_quantity'].values())
 if r['full_calendar']!=full or r['paid_flat']!=paid or r['paid_cash_PnL_USDT']!=(r['marked_PnL_USDT'] if paid else None):raise ValueError('Paid/result classification changed')
 return full,paid

def validate_summary(r,a):
 flat=all(D(q)==0 for q in r['terminal_residual_quantity'].values())
 if a['summary']['net_PnL']!=r['marked_PnL_USDT'] or a['summary']['terminal_cash_realized']!=flat:raise ValueError('Summary PnL/cash-flat fields differ')

def validate_daily_chunks(p,rows,r,pointer):
 """Read-only CSV integrity against already cold-audited durable numeric chunks."""
 import numpy as np
 day=86_400_000_000;start=1735689600000000
 expected=r['completed_minutes']//1440
 if len(rows)!=expected or len(rows)!=r['daily_observed_days']:raise ValueError('Daily count changed')
 chunks=pointer['chunks']
 if len(chunks)<expected:raise ValueError('Missing audited daily chunks')
 for i,row in enumerate(rows):
  if int(row['close_us'])!=start+(i+1)*day:raise ValueError('Noncontiguous daily clock')
  c=chunks[i];path=p/'recovery'/c['path']
  if c['path']!=f'DAY_{i:04d}.npz' or c['rows']!=1440 or sha(path)!=c['SHA256']:raise ValueError('Daily audited chunk identity changed')
  with np.load(path,allow_pickle=False) as data:
   x=data['minute_chunk']
   if x.shape!=(1440,c['columns']) or not math.isfinite(float(x[-1,0])) or float(row['nav'])!=float(x[-1,0]):raise ValueError('Daily NAV differs from audited minute close')
 return dict(DAILY_SHA256=sha(p/'DAILY.csv'),audited_chunk_count=expected,continuous_daily_clock=True,day_close_NAV_exact=True)

def metrics(r,a,rows):
 nav=[10000.]+[float(x['nav']) for x in rows];returns=[nav[i]/nav[i-1]-1 for i in range(1,len(nav))]
 mean=sum(returns)/len(returns) if returns else 0
 var=sum((x-mean)**2 for x in returns)/(len(returns)-1) if len(returns)>1 else None
 summary=a['summary']
 out={k:r.get(k) for k in ('full_calendar','paid_flat','paid_cash_PnL_USDT','marked_PnL_USDT','minute_drawdown','mean_actual_gross','max_actual_gross','trade_legs','rejection_counts','terminal_residual_quantity','terminal_residual_gross_notional_USDT','terminal_residual_marked_notional_USDT','account_status','completion','completed_minutes','required_minutes','stop_us','mean_actual_signed_net','max_actual_abs_signed_net')}
 for k in ('gross_fill_turnover_USDT','fees_USDT','execution_cost_USDT','funding_USDT','risk_reduction_signal_count','minimum_actual_free_cash_all_observations_USDT'):out[k]=summary[k]
 out['annual_daily_vol']=math.sqrt(var*365) if r['full_calendar'] and var is not None else None
 out['worst_observed_30_days']=min((nav[i]/nav[i-30]-1 for i in range(30,len(nav))),default=None)
 month={}
 for row in rows:month[utc(int(row['close_us'])-1)[:7]]=float(row['nav'])-10000
 out['month_end_cumulative_PnL_USDT']=month
 return out

def main():
 review=read(H/'REPORT_REVIEW_RECEIPT.json')
 if review.get('status')!='PASS_INDEPENDENT_READ_ONLY_REPORT_REVIEW' or review.get('build_report_SHA256')!=sha(Path(__file__)):raise ValueError('Exact independent report review required')
 sys=__import__('sys');sys.path.insert(0,str(R/'coin_earlier_terminal_recovery_20261013'))
 from cold_recovery import verify_recovery_aggregate
 recovery_plan,recovered_state=verify_recovery_aggregate()
 if recovered_state!=S:raise ValueError('Wrong report recovery destination')
 plan=read(M/'CASE_BINDINGS.json');controller=read(S/'RESOURCE_RECEIPTS.json');run=read(S/'RUN_BINDING.json')
 expected={c['case_id']+'_FINE_ORIGINAL' for c in plan['cases']}
 if len(expected)!=2 or {c['arm'] for c in plan['cases']}!={'STATIC50','COMBINED'} or plan['terminal_opens']!=60:raise ValueError('Fixed population changed')
 if set(controller['per_case'])|set(controller['unstarted_case_ids'])!=expected or controller['status']!='ALL_CASES_FINISHED':raise ValueError('A program/resource STOP requires a partial diagnostic, not a completed report')
 if any(r['exit_code'] or r['stop_reason'] for r in controller['per_case'].values()):raise ValueError('Unclean worker')
 if run['freeze_manifest_SHA256']!=sha(M/'FROZEN_CODE.json') or run['runner_SHA256']!=sha(M/'run_cases.py'):raise ValueError('Run bytes changed')
 out=dict(status='COMPLETE_FIXED_TWO_ARM_2025_EXECUTION_ABLATION',scope='Seen development history. Earlier charged terminal execution only; no trading-rule change before the preset exit, new OOS claim, native venue readiness or reliable live APR.',preregistration=read(M/'PUBLICATION_RECEIPT.json')['commit'],freeze_manifest_SHA256=sha(M/'FROZEN_CODE.json'),source_index_SHA256=plan['cases'][0]['source_index_SHA256'],year=2025,capital_per_wallet_USDT=10000,terminal_real_opens=60,calendar_end_us=1767225600000000,case_count=2,cases=[],resource_receipts=controller,original_resource_STOP_preserved=True,original_resource_STOP_receipt_SHA256=recovery_plan['original_STOP_receipt_SHA256'],recovery_manifest_SHA256=sha(R/'coin_earlier_terminal_recovery_20261013/FROZEN_RECOVERY.json'))
 for c in plan['cases']:
  identity=c['case_id']+'_FINE_ORIGINAL';new=S/identity;old=R/c['baseline_state_local_locator'];receipt=read(M/'receipts'/f'{identity}.json')
  recovery_cold=read(R/'coin_earlier_terminal_recovery_20261013/receipts'/f'{identity}.json')
  if recovery_cold['status']!='PASS_RESUMED_AGGREGATE_AND_FROZEN_ZERO_ADVANCE_COLD' or recovery_cold['frozen_cold_receipt_SHA256']!=sha(M/'receipts'/f'{identity}.json') or recovery_cold['new_ACCOUNT_SHA256']!=sha(new/'ACCOUNT.json') or recovery_cold['new_RESULT_SHA256']!=sha(new/'RESULT.json'):raise ValueError('Aggregate recovery cold receipt changed')
  if receipt['status']!='PASS_ZERO_ADVANCE_COLD_RESTORE_AND_IDENTICAL_PRE_EXIT_PREFIX' or receipt['new_result_SHA256']!=sha(new/'RESULT.json') or receipt['baseline_result_SHA256']!=sha(old/'RESULT.json'):raise ValueError('Cold receipt/result identity changed')
  for name,digest in c['baseline_files_SHA256'].items():
   if sha(old/name)!=digest:raise ValueError('Original baseline bytes changed: '+name)
  payload={}
  for label,p in (('original_five_open',old),('fixed_60_real_open',new)):
   result=read(p/'RESULT.json');account=read(p/'ACCOUNT.json');validate_result(result,identity)
   validate_summary(result,account)
   if label=='fixed_60_real_open':
    snapshot=read(p/'recovery/POINTER.json');
    if snapshot['state_hash']!=receipt['genuine_state_hash']:raise ValueError('Cold/state identity differs')
   with (p/'DAILY.csv').open() as file:rows=list(csv.DictReader(file))
   if len(rows)!=result['daily_observed_days']:raise ValueError('Daily count changed')
   payload[label]=metrics(result,account,rows)
   if label=='fixed_60_real_open':payload[label]['daily_input_integrity']=validate_daily_chunks(p,rows,result,snapshot)
  delta={k:payload['fixed_60_real_open'][k]-payload['original_five_open'][k] for k in ('marked_PnL_USDT','minute_drawdown','mean_actual_gross','max_actual_gross','trade_legs','gross_fill_turnover_USDT','fees_USDT','execution_cost_USDT','funding_USDT')}
  account=read(new/'ACCOUNT.json');signal=1767221940000000;terminal=[f for f in account['trades'] if f['signal_us']==signal]
  oldaccount=read(old/'ACCOUNT.json');oldterminal=[f for f in oldaccount['trades'] if f['signal_us']==1767225240000000]
  info={}
  for label,trades in (('original_five_open',oldterminal),('fixed_60_real_open',terminal)):
   info[label]=dict(fill_legs=len(trades),first_fill_us=min((f['event_us'] for f in trades),default=None),last_fill_us=max((f['event_us'] for f in trades),default=None),fees_USDT=sum(f['fee_amount'] for f in trades),execution_cost_USDT=sum(f['execution_cost'] for f in trades),by_symbol={s:dict(fill_legs=sum(f['symbol']==s for f in trades),quantity_closed=sum(f['quantity'] for f in trades if f['symbol']==s)) for s in SYMS})
  out['cases'].append(dict(case_id=identity,arm=c['display_arm'],target_array_SHA256=c['target_array_SHA256'],old=payload['original_five_open'],new=payload['fixed_60_real_open'],same_clock_new_minus_old_numeric_delta=delta,delta_interpretation='Old nonflat marked PnL is not paid cash PnL. Numeric new-minus-old changes include earlier price movement and paid execution; this is not incremental predictive alpha.',terminal=info,cold=receipt,recovery_cold=recovery_cold,account_hashes={'old':sha(old/'ACCOUNT.json'),'new':sha(new/'ACCOUNT.json')}))
 with (H/'RESULTS_COMPACT.json').open('x') as file:json.dump(out,file,indent=2,sort_keys=True,allow_nan=False);file.write('\n')
 lines=['# Fixed sixty-real-open terminal exit, 2025','',out['scope'],'','Both original fine 2025 controls retain their original full-calendar marked results and nonflat status. The new fixed rule uses the same calendar end and 60 real next-minute opens; there are no January2026 quotes or additional free fills.','']
 for row in out['cases']:
  a,b=row['old'],row['new'];kind='paid cash' if b['paid_flat'] else 'marked at year end' if b['full_calendar'] else 'partial marked at stop'
  lines += [f"## {row['arm']}",f"Original marked PnL {a['marked_PnL_USDT']:+.6f} USDT; new {kind} PnL {b['marked_PnL_USDT']:+.6f} USDT. New paid-flat={b['paid_flat']}; completed {b['completed_minutes']}/{b['required_minutes']} minutes.",f"Residual gross marked notional {a['terminal_residual_gross_notional_USDT']:.6f} → {b['terminal_residual_gross_notional_USDT']:.6f} USDT; minute DD {a['minute_drawdown']*100:.6f}% → {b['minute_drawdown']*100:.6f}%.",f"Trade legs {a['trade_legs']} → {b['trade_legs']}; total fees {a['fees_USDT']:.6f} → {b['fees_USDT']:.6f}; execution cost {a['execution_cost_USDT']:.6f} → {b['execution_cost_USDT']:.6f}; funding cash {a['funding_USDT']:.6f} → {b['funding_USDT']:.6f} USDT.",f"Actual mean/max gross {a['mean_actual_gross']:.9f}/{a['max_actual_gross']:.9f} → {b['mean_actual_gross']:.9f}/{b['max_actual_gross']:.9f}. Pre-exit all-numeric prefix {row['cold']['pre_intervention_numeric_minutes_checked']} minutes exact; cold restore zero financial advances.",'']
 lines += ['## Preserved resource interruption','The first parallel controller stopped on conservative future-memory reservation at330.3seconds; exact triggering host_used is UNKNOWN. Both durable anchors were independently cold-restored, then the same accounts continued sequentially from300/330days under only869remainingseconds per process. Original resource STOP, pointers, financial freeze and all stored prefixes remain unchanged. This is one interrupted experiment, not a second full-year trial.','', '## Interpretation','This repairs a specific terminal-execution convention under a conditional model. It does not add a trading signal, establish new OOS advantage, certify actual exchange filters/arrival/funding/MMR, or support a reliable live APR. Original annual payment STOPs, earlier extension results, all prior halts/negative findings and the protective-exit adverse effects remain unchanged. The half portfolio is an execution control; this module does not expand SMA research.','',f"Preregistered code: https://github.com/snowycat1234/coin/commit/{out['preregistration']}",'Detailed same-clock monthly cumulative PnL, costs, exposure, terminal fills/requests/capacity and residuals are in RESULTS_COMPACT.json and the two independent cold receipts.']
 with (H/'SUMMARY.md').open('x') as file:file.write('\n'.join(lines)+'\n')
 print(json.dumps({'status':out['status'],'cases':[dict(arm=x['arm'],old=x['old']['marked_PnL_USDT'],new=x['new']['marked_PnL_USDT'],paid=x['new']['paid_flat']) for x in out['cases']]},indent=2))
if __name__=='__main__':main()
