import ast,hashlib,json,os,resource,time
from collections import Counter
from decimal import Decimal,getcontext
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
getcontext().prec=50
started=time.monotonic()
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state'); HERE=Path(__file__).parent
STEM='DONCHIAN_REENTRY10_20261005_V3'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dec(v):return Decimal(str(v))
def task(tid):
 t=read(STATE/'task-progress'/('task-'+tid+'.json'))
 assert t['status']=='completed' and t['exit_code']==0 and t['ended_at']
 return {'id':tid,'exit_code':t['exit_code'],'ended_at':t['ended_at']}
p=read(ROOT/'protocols'/(STEM+'.json'))
a=read(ROOT/'reports/fast_research'/(STEM+'.json'))
f=read(ROOT/'reports/fast_research'/(STEM+'_FINANCIAL_V6.json'))
d=read(ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC_V6.json'))
closed=[task(a['binding']['task_id']),task(f['binding']['task_id']),task(d['task_id'])]
assert len(a['cases'])==len(f['cases'])==4 and f['financial_case_calls']==4
assert a['complete_calendar_cases']==a['terminal_cash_realized_cases']==4
assert d['protocol_sha256']==sha(ROOT/'protocols'/(STEM+'.json'))
assert d['actual_report_sha256']==sha(ROOT/'reports/fast_research'/(STEM+'.json'))
assert d['financial_report_sha256']==sha(ROOT/'reports/fast_research'/(STEM+'_FINANCIAL_V6.json'))
oldpath=ROOT/'docs/archive/DONCHIAN_REENTRY10_PRE_COMPACT_FINANCIAL_SOURCE_20261005_V1.py'
newpath=ROOT/'scripts/investment/multi_asset_financial_audit.py'
assert sha(oldpath)=='f8a753969337a2f86fc9932634d598e284b829a95a9fc8118ea37372c671e9d4'
assert sha(newpath)=='684166eafc9eafb37358bb747edccaa5a215fb272783a2d02211062e70f6a8a7'
old=oldpath.read_text();new=newpath.read_text()
begin=new.index("            witnesses = window['independent_Donchian_state_witnesses']")
end=new.index('                independent_Donchian_reference=',begin)
restored=new[:begin]+"            report.update(independent_Donchian_state_witnesses=window['independent_Donchian_state_witnesses'],\n"+new[end:]
assert restored==old,'Source delta must be exactly witness report encoding block'
old_ast=ast.parse(old);new_ast=ast.parse(new)
old_functions={x.name:ast.dump(x,include_attributes=False) for x in old_ast.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name!='main'}
new_functions={x.name:ast.dump(x,include_attributes=False) for x in new_ast.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name!='main'}
assert old_functions==new_functions
w=f['independent_Donchian_state_witnesses'];assert w['encoding']=='ORDERED_KEY_SCHEMAS_AND_ROWS_V1'
schemas=w['schemas'];records=[]
for packed in w['rows']:
 schema=schemas[packed[0]];assert len(schema)==len(set(schema)) and len(schema)==len(packed)-1
 records.append({key:packed[i+1] for i,key in enumerate(schema)})
assert len(records)==w['logical_row_count']==3030
logical=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
assert logical==w['logical_sha256']
assert [[next(i for i,s in enumerate(schemas) if s==list(r)),*r.values()] for r in records]==w['rows']
symbols=p['pools'][1]['symbols'];start=1725148800000000;DAY=86400000000
assert [(r['decision_us'],r['symbol']) for r in records]==[(start+i*DAY,s) for i in range(303) for s in symbols]
state={s:(0,False) for s in symbols};actions=Counter();armed_entries=0
for r in records:
 s=r['symbol'];before,arm=state[s]
 assert r['old_state']==before and r['arm_before'] is arm
 assert r['reentry_period']==10
 if r['action']=='RESET_UNAVAILABLE':
  after,newarm=0,False;assert r['entry_period_used'] is None
 elif before:
  after=int(not(r['completed_close']<r['prior10_lower']));newarm=not bool(after)
  assert r['entry_period_used'] is None
  assert r['action']==('KEEP_LONG' if after else 'EXIT_TO_CASH')
 else:
  period=10 if arm else 20;assert r['entry_period_used']==period
  upper=r['prior10_upper'] if arm else r['prior20_upper']
  after=int(r['completed_close']>upper and r['completed_close']>r['current_completed_SMA200'])
  newarm=False if after else arm
  assert r['action']==('ENTER_LONG' if after else 'STAY_CASH')
  armed_entries+=int(arm and after)
 assert r['new_state']==after and r['arm_after'] is newarm
 assert r['channel_last_close_us']==r['decision_us']-DAY and r['channel_excludes_current'] is True
 state[s]=(after,newarm);actions[r['action']]+=1
errors=[];pair_rows=[]
for row in d['rows']:
 bridge=dec(row['gross_USDT'])-dec(row['fees_USDT'])-dec(row['execution_USDT'])+dec(row['funding_USDT'])
 errors.append(abs(bridge-dec(row['net_USDT'])))
 for k in ('net_USDT','gross_USDT','fees_USDT','execution_USDT','funding_USDT'):
  errors.append(abs(sum((dec(x[k]) for x in row['asset_contributions'].values()),Decimal(0))-dec(row[k])))
 assert len(row['asset_contributions'])==10 and row['terminal_cash_realized']
 assert all(x['terminal_quantity']==0 for x in row['asset_contributions'].values())
for pair in d['paired_cases']:
 rows=[r for r in d['rows'] if r['cost']==pair['cost'] and r['funding_unit']==pair['funding_unit']]
 x=next(r for r in rows if r['policy']=='REENTRY20');y=next(r for r in rows if r['policy']=='REENTRY10')
 ng=dec(y['gross_USDT'])-dec(x['gross_USDT']);nc=dec(y['fees_USDT'])+dec(y['execution_USDT'])-dec(x['fees_USDT'])-dec(x['execution_USDT']);nf=dec(y['funding_USDT'])-dec(x['funding_USDT']);nn=dec(y['net_USDT'])-dec(x['net_USDT'])
 errors.extend([abs(nn-(ng-nc+nf)),abs(nn-dec(pair['net_increment_USDT']))])
 assert nn<0 and not pair['actual_risk_matched'] and y['minute_MDD']>x['minute_MDD']
 pair_rows.append({'cost':pair['cost'],'unit':pair['funding_unit'],'old_net':x['net_USDT'],'new_net':y['net_USDT'],'net_increment':str(nn),'gross_increment':str(ng),'cost_increment':str(nc),'fund_increment':str(nf),'old_vol':x['actual_daily_annualized_volatility'],'new_vol':y['actual_daily_annualized_volatility'],'old_MDD':x['minute_MDD'],'new_MDD':y['minute_MDD'],'old_turnover':x['turnover_full_capital'],'new_turnover':y['turnover_full_capital'],'old_avg_gross':x['minute_mean_gross_weight'],'new_avg_gross':y['minute_mean_gross_weight']})
for c in a['cases']:
 assert c['pool_id']=='LIQUIDITY_TEN' if 'pool_id' in c else c['id'].startswith('LIQUIDITY_TEN_')
 assert c['symbols']==symbols
 sm=c['summary'];fc=next(v for v in f['cases'] if v['id']==c['id'])
 assert sm['completed_minutes']==sm['required_minutes']==436320
 assert sm['terminal_cash_realized'] and sm['terminal_marked_notional']==0
 assert all(v['quantity']==0 for v in sm['positions'].values())
 ds=sm['decimal_strings'];b=dec(ds['gross_PnL_same_quantities'])-dec(ds['fees_USDT'])-dec(ds['execution_cost_USDT'])+dec(ds['funding_USDT'])
 errors.append(abs(b-dec(ds['net_PnL'])))
 errors.append(abs(dec(ds['NAV'])-Decimal(10000)-dec(ds['net_PnL'])))
 for k in ('net_PnL','fees_USDT','funding_USDT','execution_cost_USDT','gross_PnL_same_quantities'):
  errors.append(abs(dec(fc['summary'][k])-dec(sm[k])))
 errors.append(abs(sum((dec(m['net_PnL']) for m in sm['months']),Decimal(0))-dec(sm['net_PnL'])))
 assert sum(m['days'] for m in sm['months'])==303 and len(sm['months'])==10
 assert sm['maximum_actual_gross_weight']<=.6 and max(sm['maximum_actual_asset_weights'].values())<=.3
assert max(errors)<Decimal('1e-7')
failures=[]
for name in ('DONCHIAN_REENTRY10_FINANCIAL_OUTPUT_FAILURE_20261005_V3.json','DONCHIAN_REENTRY10_FINANCIAL_SOURCE_BINDING_FAILURE_20261005_V4.json','DONCHIAN_REENTRY10_FINANCIAL_SOURCE_BINDING_FAILURE_20261005_V5.json'):
 z=read(ROOT/'reports'/name);t=z['actual_closed_task'];assert t['status']=='failed' and t['exit_code']==1
 failures.append({'file':name,'task':t['id'],'exit':t['exit_code'],'calls':z.get('accounts_visited_in_progress',z.get('financial_calls_started'))})
value={'status':'PASS_SAVED_REPORT_DECODE_AND_DECIMAL_BRIDGES_ONLY','task_id':os.environ['COIN_TASK_ID'],'source_sha256':sha(__file__),'closed_roles':closed,'elapsed_seconds':time.monotonic()-started,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'logical_rows':len(records),'logical_sha256':logical,'schemas':len(schemas),'repacked_exact':True,'source_delta_only_report_encoding':True,'nonmain_functions_identical':len(old_functions),'actions':dict(actions),'armed_successful_entries':armed_entries,'max_saved_report_arithmetic_error_USDT':str(max(errors)),'pairs':pair_rows,'financial_failures':failures,'market_replays':0,'target_recomputations':0,'tests':0}
with (HERE/'result.json').open('x') as writer:json.dump(value,writer,indent=2,allow_nan=False);writer.write('\n')
print(json.dumps(value,allow_nan=False))