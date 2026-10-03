"""UNRUN D048 saved JSON comparison. Root freezes --binding after finance0.
Roles MARKET/INDEPENDENT: path,sha256,required_status,task_id. No ledger IO.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, os, resource, sys, time
from pathlib import Path
from quant import resources

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
VIEW='scripts/investment/compare_perpetual_213_results.py'
VIEW_SHA='c7af4ac72b0332e27b41312f58362e255cacd94614de3173a64725e67b361792'
CONTRACT='D048_SAVED_CLOSING_EXEMPT_COMPARISON_V1'
STATUS='COMPLETE_D048_SAVED_CLOSING_EXEMPT_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
MARKET='COMPLETE_D048_EIGHT_CLOSING_EXEMPT_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
AUDIT='PASS_D048_EIGHT_RECORDED_CLOSING_EXEMPT_PERPETUAL_ACCOUNTING_NOT_NATIVE_FILTERS_OR_LONG_TERM_APR'
TURTLE='TURTLE_LONG_SHORT';HOLD='HOLD_LONG_ONLY'
COSTS=('BASE27','STRESS43');UNITS=('RAW_AS_FRACTION','RAW_AS_PERCENT')
MONTHS=[f'2024-{m:02d}' for m in range(9,13)]+[f'2025-{m:02d}' for m in range(1,7)]
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
LOCK='state/dataset_lock.json'
LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
PRIORS=(('TURTLE_PERPETUAL_RESEARCH_ACTUAL_20261003_V2.json','1308bc58dce63944e3de3c000e6215def3564330b6ebf188b17eac5bf05a527a'),
('TURTLE_PERPETUAL_FINANCIAL_INDEPENDENT_20261003_V1.json','bc59297c44636ca14ba7778d2f2dfe2478887411211ccdde6f84e58c5a097bed'))

def sha(path):
  h=hashlib.sha256()
  with Path(path).open('rb') as stream:
    for part in iter(lambda:stream.read(65536),b''):h.update(part)
  return h.hexdigest()

def module(path,digest):
  if sha(ROOT/path)!=digest:raise ValueError(path)
  loader=importlib.util.spec_from_file_location('_d048_'+Path(path).stem,ROOT/path)
  value=importlib.util.module_from_spec(loader);loader.loader.exec_module(value);return value

def delta(a,b,money):
  full=a['complete_calendar'] and b['complete_calendar']
  values={k:float(a['summary'][k])-float(b['summary'][k]) for k in money} if full else None
  months=[]
  if full:
    left={r['month']:r for r in a['saved_months']};right={r['month']:r for r in b['saved_months']}
    if set(left)!=set(MONTHS) or set(right)!=set(MONTHS):raise ValueError('Months')
    months=[dict(month=m,**{k:left[m][k]-right[m][k] for k in ('net_PnL','gross_PnL','funding_USDT')}) for m in MONTHS]
  return dict(left=a['id'],right=b['id'],scope='FULL_SEPARATE_ACCOUNTS' if full else 'NOT_EVALUABLE_HALTED_PREFIX',
    delta_USDT=values,delta_full_capital_return_percentage_points=values['net_PnL']/100 if full else None,
    delta_realized_volatility=a['realized_annual_volatility']-b['realized_annual_volatility'] if full else None,
    delta_all_observation_MDD=a['summary']['all_observation_max_drawdown']-b['summary']['all_observation_max_drawdown'] if full else None,
    monthly_deltas=months,risk_equalized=False,pure_causal_effect_identified=False)

def main():
  parser=argparse.ArgumentParser(description=__doc__)
  for name in ('binding','run-dir','output'):parser.add_argument('--'+name,type=Path,required=True)
  a=parser.parse_args();started=time.monotonic();g=module(GUARD,GUARD_SHA);v=module(VIEW,VIEW_SHA);check=g.check
  plan,plan_sha=g.small(a.binding)
  check(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
    and a.binding.parent==ROOT/'protocols' and plan['ready_to_execute'] is True
    and plan['contract_id']==CONTRACT and plan['helper_sha256']==sha(__file__) and plan['budgets']==BUDGET,'Caller')
  check(a.run_dir==Path(plan['run_dir']) and a.run_dir.parent==STATE and not a.run_dir.exists()
    and a.output==(ROOT/plan['output_path']).resolve() and a.output.parent==ROOT/'reports/fast_research'
    and not a.output.exists(),'Exclusive')
  before=resources.status();g.bounded(before);hashes=dict(plan['frozen_sources']);tasks={};records={}
  check(plan['local_non_git_hash_guard']=={LOCK:LOCK_SHA} and sha(ROOT/LOCK)==LOCK_SHA,'Lock SHA only')
  for name,digest in hashes.items():
    check(name!=LOCK,'Private map');g.small(g.project(name),digest,False)
  check(hashes.get(str(Path(__file__).relative_to(ROOT)))==sha(__file__),'Own pin')
  check(set(plan['roles'])=={'MARKET','INDEPENDENT'},'Roles')
  for role,ref in plan['roles'].items():
    row,digest=g.small(g.project(ref['path']),ref['sha256']);tasks[role]=g.closed(ref['task_id'])
    check(row['binding']['task_id']==ref['task_id'] and row['status']==ref['required_status']==(MARKET if role=='MARKET' else AUDIT),'Role')
    records[role]=row;hashes[ref['path']]=digest
  check(tasks['INDEPENDENT']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'Chronology')
  actual,audit=records['MARKET'],records['INDEPENDENT'];ref=plan['market_protocol']
  spec,proto_sha=g.small(g.project(ref['path']),ref['sha256']);hashes[ref['path']]=proto_sha
  check(spec['contract_id']=='D048_FIXED303D_TURTLE_AND_HOLD_CLOSING_EXEMPT_CONDITIONAL_V1'
    and actual['binding']['protocol_sha256']==proto_sha and Path(actual['binding']['protocol_path'])==ROOT/ref['path']
    and actual['binding']['source_hashes']==spec['frozen_sources']
    and all(hashes.get(k)==h for k,h in spec['frozen_sources'].items()),'Protocol/pins')
  check(all(r['funding_rate_unit']=='UNCONFIRMED' and not r['unit_certified'] and not r['native_market_certified'] for r in records.values()),'Units/native')
  check(all(spec['rules'][k]==n for k,n in dict(initial_capital_USDT=10000,annual_vol_target=.1,asset_abs_cap=.3,gross_cap=.6,leverage=1).items()),'Capital/caps')
  check(g.canonical_reports(audit['binding']['actual_reports'])=={str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']}
    and actual['required_cases']==actual['completed_cases']==audit['completed_cases_verified']==len(actual['cases'])==len(audit['cases'])==8,'Eight cases')
  priors=[]
  for name,digest in PRIORS:
    path='reports/fast_research/'+name;row,_=g.small(g.project(path),digest);priors.append(row);hashes[path]=digest
  old,old_audit=priors;check(actual['input_windows']==old['input_windows'],'Same input')
  proofs={p['id']:p for p in audit['cases']};old_proofs={p['id']:p for p in old_audit['cases']};index={};previous={}
  for case in actual['cases']:
    proof=proofs[case['id']];s=case['summary'];key=case['cost_id'],case['unit_id'],case['selector_mode']
    check(key not in index and case['period']=='303D' and s['required_minutes']==436320,'Selector')
    index[key]=v.view(case,proof)
    index[key]['summary'].update({k:s.get(k) for k in ('gross_notional','net_signed_notional','gross_weight','asset_weights')})
  check(set(index)=={(c,u,s) for c in COSTS for u in UNITS for s in (TURTLE,HOLD)},'Eight selectors')
  for case in old['cases']:previous[case['cost_id'],case['unit_id']]=v.view(case,old_proofs[case['id']])
  check(set(previous)=={(c,u) for c in COSTS for u in UNITS}
    and {k for k,r in previous.items() if r['complete_calendar']}=={('BASE27','RAW_AS_PERCENT')},'Old prefixes')
  groups=[]
  for cost in COSTS:
    for unit in UNITS:
      t,h=index[cost,unit,TURTLE],index[cost,unit,HOLD];o=previous[cost,unit]
      groups.append(dict(cost_id=cost,unit_id=unit,TURTLE=t,HOLD=h,Turtle_minus_HOLD=delta(t,h,v.MONEY),
        each_minus_known_CASH0={r['selector']:r['summary']['net_PnL'] if r['complete_calendar'] else None for r in (t,h)},
        old_Turtle=o,Turtle_before_after=delta(t,o,v.MONEY)))
  a.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=sha(__file__),plan_sha256=plan_sha,
    source_hashes=hashes,command=[sys.executable,*sys.argv]);rb_sha,_=g.write(a.run_dir/'RUN_BINDING.json',binding)
  after=resources.status();g.bounded(after)
  result=dict(status=STATUS,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=rb_sha,closed_prerequisite_tasks=tasks,groups=groups,
    compared_new_cases=8,prior_full_cases=1,prior_prefix_cases_NOT_EVALUABLE=3,known_CASH_USDT_PnL=0,
    HOLD_vs_older_D045_is_pure_filter_change=False,complete_strategy_intents_independently_rebuilt=False,
    funding_unit_certified=False,native_market_certified=False,common_caps_equal_realized_risk=False,
    investment='CASH_NONE',candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',
    market_ledger_IO=False,old_replay=False,joined_NAV=False,unit_or_cost_winner_selected=False,
    resources_before=before,resources_after=after,elapsed_seconds=time.monotonic()-started,
    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
  check(result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=1_000_000_000,'Budget')
  digest,size=g.write(a.output,result);check(size+(a.run_dir/'RUN_BINDING.json').stat().st_size<=5_000_000,'Size');print(digest)

if __name__=='__main__':main()
