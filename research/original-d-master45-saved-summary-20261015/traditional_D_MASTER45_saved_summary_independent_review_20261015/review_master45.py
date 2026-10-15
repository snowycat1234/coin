#!/usr/bin/env python3
"""Independent saved-only row, provenance, rendering, and changed-copy review."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,{1})
import ast,copy,csv,datetime as dt,hashlib,importlib.util,io,json,pathlib
from collections import Counter
from decimal import Decimal,localcontext
ROOT=pathlib.Path(__file__).resolve().parent.parent;HERE=pathlib.Path(__file__).resolve().parent;AUTHOR=ROOT/'traditional_D_MASTER45_saved_summary_20261015'
P21='traditional_D_partial2021_independent_review_20261015/actual_nine_saved_review';PX='bounded_native_continuation_guard50_exit_expansion_independent_review_20261015';RISK='saved_distinct_family_risk_evidence_20261015/final_saved_analysis_attempt001/RISK_EVIDENCE.json'
FIN={'terminal_NAV_USDT':'NAV','net_PnL_USDT':'net_PnL','fees_USDT':'fees_USDT','execution_cost_USDT':'execution_cost_USDT','signed_funding_USDT':'funding_USDT','gross_paid_market_turnover_USDT':'gross_fill_turnover_USDT','unpaid_liability_USDT':'unpaid_liability'}
SOURCES={2021:'b2962b671e4130a8562cea2ff75f0c3d98b51f6d4b46dfc04eecaf7e94272cd3',2022:'1d5fc1db1ee3fd95746f29d267ea7d7c3edac616d5a8f0bee1320f6ee786da2f',2023:'ced6e9a12f813483d431c52f0005b30720e744529061ae140c19f1dae9db23d9',2024:'3794f1d1502740816bb1ac31096e60a4720d1b7a19d588150fd469ef1515966b',2025:'70c8f1c773cdb9db30aa6e0d9a4e52d174f894d868883dd3ccda87bc1a928ef6'}
CODE={2021:'f8239806dd68e833273c6684102ebefffc3033b1',2022:'abb7d3cc390b9fe4fda01bc24f066fe04a4fd6c38f6c5b57dcf808f5f6af6a9c',2023:'5a48a669f71c290a119fa9dabc8f14480626fc7d',2024:'5a48a669f71c290a119fa9dabc8f14480626fc7d',2025:'e694248085094a7b258036129c7c521ae3999eadabfa1d2991d2ba1a3f15f89e'}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(rel):return json.loads((ROOT/rel).read_text())
def ptr(obj,path):
 for x in path.split('/'):
  if x:obj=obj[int(x)] if isinstance(obj,list) else obj[x]
 return obj
def eq(a,b,label):
 if a!=b:raise AssertionError(label+': '+str(a)+' != '+str(b))
def exactly(arr,cell):
 v=[x for x in arr if x['cell_id']==cell];assert len(v)==1,cell;return v[0]
def run():
 pinmap=json.loads((AUTHOR/'INPUT_PINMAP.json').read_text());rows=json.loads((AUTHOR/'MASTER45_ROWS.json').read_text());before={p:sha(ROOT/p) for p in pinmap['files']}
 for p,v in pinmap['files'].items():eq({'SHA256':before[p],'bytes':(ROOT/p).stat().st_size},v,p)
 risk=read(RISK);per=[];codes={};leaf_refs={};all_fields=0
 expected=[]
 for year in range(2021,2026):
  for strategy in ('STATIC50','H090','VOL_MANAGED_HOLD'):
   for tier in ('LOW','MID','HIGH'):expected.append(f'{year}_{strategy}_{tier}'+('_APR2_DEC31_D' if year==2021 else '_JAN1_DEC31_D' if year in (2022,2025) else ''))
 eq([r['cell_id']for r in rows],expected,'45 fixed independent identities');assert len(set(expected))==45
 for row in rows:
  cell=row['cell_id'];year=row['year'];strategy=row['strategy'];tier=row['tier']
  start=dt.datetime(year,4 if year==2021 else 1,2 if year==2021 else 1,tzinfo=dt.timezone.utc);end=dt.datetime(year+1,1,1,tzinfo=dt.timezone.utc);days=(end-start).days;calendar=[int(start.timestamp()*1000000),int(end.timestamp()*1000000)]
  eq(row['period_days'],days,cell+' days');eq(row['period_start_UTC'],start.date().isoformat(),cell+' start');eq(row['period_end_inclusive_UTC'],(end-dt.timedelta(days=1)).date().isoformat(),cell+' end');eq(row['completed_minutes'],days*1440,cell+' minutes')
  assert row['partial_period']==(year==2021) and row['return_annualized'] is False and row['annual_wallets_compounded'] is False and row['initial_wallet_USDT']=='10000'
  assert row['nominal_budget_is_exact_realized_risk_matching'] is False and row['duplicate_independent_confirmation'] is False
  eq(row['nominal_annual_volatility_budget'],{'LOW':'0.05','MID':'0.10','HIGH':'0.15'}[tier],cell+' nominal budget')
  eq(row['source_identity'],SOURCES[year],cell+' actual year source');eq(row['source_code_identity'],CODE[year],cell+' year code identity')
  rp=row['review_source'];j=read(rp);leaf_refs[rp]=sha(ROOT/rp);eq(row['review_SHA256'],leaf_refs[rp],cell+' review pin')
  if year==2021:
   eq(j['cell_id'],cell,cell+' review cell');eq(j['calendar'],calendar,cell+' review calendar');eq(j['strategy'],strategy,cell+' strategy');eq(j['tier'],tier,cell+' tier');f=j['summary']['decimal_strings'];riskj=j['actual_held_risk'];eq(row['all_observation_MDD_fraction'],j['economics']['all_observation_max_drawdown'],cell+' native MDD')
   eq(row['realized_daily_annualized_volatility'],riskj['realized_daily_simple_return_annual_volatility'],cell+' realized volatility');assert j['partial_period_return_annualized'] is False
   codes.update(j['code_identity'])
  elif year in (2022,2025):
   eq(j['cell_id'],cell,cell+' review cell');eq(j['calendar'],calendar,cell+' review calendar');eq(j['year'],year,cell+' year');eq(j['strategy'],strategy,cell+' strategy');eq(j['tier'],tier,cell+' tier');f=j['exact_financials'];riskj=j['actual_held_exposure_and_both_covariance_phase_risk'];eq(row['period_return_fraction'],j['exact_marked_net_return'],cell+' exact native return');eq(row['all_observation_MDD_fraction'],riskj['MDD_scopes']['native_all_observation']['max_drawdown'],cell+' native MDD')
   if strategy=='STATIC50' and tier=='LOW':
    actualbase='traditional_D_full2022_20261015_v2_financial_attempt001' if year==2022 else 'traditional_D_full2025_20261015_financial_attempt001'
    admission=f'{actualbase}/{cell}/ADMISSION_GO.json';eq(sha(ROOT/admission),j['evidence']['ADMISSION_GO.json']['SHA256'],cell+' original admission pin');codes.update(read(admission)['code_identity']);leaf_refs[admission]=sha(ROOT/admission)
    cp=('traditional_D_full2022_20261015_v2' if year==2022 else 'traditional_D_full2025_20261015')+'/DELIVERABLE_PINS.json';eq(sha(ROOT/cp),row['source_code_identity'],cell+' actual year code checkpoint');leaf_refs[cp]=sha(ROOT/cp)
   mapping={'gross_held_max_minute_close':riskj['actual_gross_weight']['max'],'gross_held_mean_minute_close':riskj['actual_gross_weight']['mean'],'minimum_free_cash_minute_close_USDT':riskj['actual_free_cash_USDT']['min'],'maximum_isolated_margin_minute_close_USDT':riskj['actual_isolated_margin_USDT']['max'],'forecast_annual_volatility_max':riskj['covariance_phases']['CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION']['maximum'],'forecast_budget_overshoot_minutes':riskj['covariance_phases']['CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION']['overshoot_minutes_above_reporting_tolerance_1e10'],'forecast_sameclock_max':riskj['covariance_phases']['CLOSE_WITH_SAMECLOCK_DAILY_DECISION']['maximum'],'forecast_sameclock_overshoot_minutes':riskj['covariance_phases']['CLOSE_WITH_SAMECLOCK_DAILY_DECISION']['overshoot_minutes_above_reporting_tolerance_1e10']}
   for k,v in mapping.items():eq(row[k],v,cell+' '+k)
   eq(row['D_warning_signals'],j['D_warning_episode_count'],cell+' warnings');eq(row['owned_funding_events'],j['owned_funding_rows'],cell+' owned funding')
  else:
   donor=f'{year}_{"STATIC50" if strategy=="H090" else strategy}_{tier}';dc=exactly(risk['cells'],donor)
   if cell=='2024_STATIC50_MID':
    f=exactly(read(PX+'/actual_remaining12_saved_review/OVERALL18_D_MATRIX_INDEPENDENT_REVIEW.json')['cases'],cell)['exact_financials'];eq(f['NAV'],j['NAV'],cell+' original NAV');eq(f['fees_USDT'],j['fees_USDT'],cell+' original fees');eq(f['execution_cost_USDT'],j['execution_cost_USDT'],cell+' original cost');eq(f['funding_USDT'],j['funding_USDT'],cell+' original funding')
    riskpath=PX+'/actual_remaining12_saved_review/REUSED_2024_STATIC50_MID_SUPPLEMENTARY_RISK_REVIEW.json';rj=read(riskpath);riskj=rj['matched_risk_fields'];eq(row['runtime_CPU_seconds'],read('bounded_native_continuation_guard50_exit_20261015/actual_2024_D_attempt001/GUARD50_EXIT_ONLY/CASE_RECEIPT.json')['CPU_seconds'],cell+' original case CPU')
   else:
    eq(j['cell_id'],cell,cell+' review cell');eq(j['calendar'],calendar,cell+' review calendar');eq(j['year'],year,cell+' year');eq(j['tier'],tier,cell+' tier');f=j['exact_financials'];eq(row['period_return_fraction'],j['exact_marked_net_return'],cell+' exact native return')
    riskpath=PX+('/actual_first5_risk_review/' if strategy=='STATIC50' else '/actual_remaining12_risk_review/')+cell+'_RISK_REVIEW.json';rj=read(riskpath);riskj=rj['recomputed_saved_fields']
   leaf_refs[riskpath]=sha(ROOT/riskpath)
   eq(row['all_observation_MDD_fraction'],rj['all_observation_MDD'],cell+' independent native MDD');eq(row['realized_daily_annualized_volatility'],dc['saved_float64_aggregate']['daily_realized_annual_volatility'],cell+' daily volatility donor')
  for k,v in FIN.items():assert isinstance(row[k],str);eq(row[k],f[v],cell+' exact decimal '+k)
  with localcontext() as ctx:
   ctx.prec=100;eq(Decimal(row['terminal_NAV_USDT'])-Decimal('10000'),Decimal(row['net_PnL_USDT']),cell+' NAV-minus-wallet');eq(Decimal(row['period_return_fraction']),Decimal(row['net_PnL_USDT'])/Decimal('10000'),cell+' exact return arithmetic')
  if year not in (2022,2025):
   mapping={'gross_held_mean_minute_close':'gross_exposure_mean','gross_held_max_minute_close':'gross_exposure_max','forecast_annual_volatility_max':'forecast_annual_volatility_max','forecast_budget_overshoot_minutes':'forecast_volatility_breach_minutes','minimum_free_cash_minute_close_USDT':'minimum_observed_free_cash_USDT','maximum_isolated_margin_minute_close_USDT':'maximum_observed_isolated_margin_USDT'}
   for k,v in mapping.items():eq(row[k],riskj[v],cell+' independent risk '+k)
  for field,binding in pinmap['field_bindings'][cell].items():
   if 'JSON_pointer'in binding:eq(row[field],ptr(read(binding['source']),binding['JSON_pointer']),cell+' declared field pointer '+field);all_fields+=1
  assert row['return_taxonomy']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT' and row['conditional_settlement_count']==0 and row['internal_transfer_count']==0 and Decimal(row['conditional_insurance_support_USDT'])==0 and Decimal(row['unpaid_liability_USDT'])==0
  per.append({'cell_id':cell,'status':'PASS_EXACT_FINANCIAL_CALENDAR_SOURCE_CODE_RISK_PROVENANCE','review_SHA256':row['review_SHA256']})
 for p,h in codes.items():eq(sha(ROOT/p),h,'original code unchanged '+p)
 # Import only the report assembler. Static AST forbids external/model dependencies.
 code=(AUTHOR/'assemble_master45.py').read_text();tree=ast.parse(code);imports=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.extend(a.name.split('.')[0]for a in node.names)
  elif isinstance(node,ast.ImportFrom):imports.append(node.module.split('.')[0])
 assert set(imports)<={'argparse','csv','hashlib','json','os','pathlib','collections','decimal'},imports
 spec=importlib.util.spec_from_file_location('independent_inspect_saved_master45',AUTHOR/'assemble_master45.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);inp=m.Inputs();reference=m.build_rows(inp);eq(reference,rows,'deterministic rows')
 buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(reference[0]),lineterminator='\n');w.writeheader();w.writerows(reference);eq(buf.getvalue().encode(),(AUTHOR/'MASTER45.csv').read_bytes(),'CSV bytes');eq(m.markdown(reference).encode(),(AUTHOR/'MASTER45.md').read_bytes(),'Markdown bytes')
 negatives=[]
 def negative(name,mutate):
  candidate=copy.deepcopy(rows);mutate(candidate)
  try:m.validate_candidate(candidate,reference)
  except (ValueError,AssertionError,KeyError) as e:negatives.append({'name':name,'rejected':True,'reason':str(e)});return
  raise AssertionError('NEGATIVE_ACCEPTED:'+name)
 negative('wrong_row_same_value_copy',lambda c:c.__setitem__(0,copy.deepcopy(c[3])))
 negative('wrong_source_period_identity',lambda c:c[9].__setitem__('source_identity',SOURCES[2025]))
 negative('wrong_year_source_review_path',lambda c:c[9].__setitem__('review_source',c[36]['review_source']))
 negative('swapped_fee_execution_cost',lambda c:c[0].update(fees_USDT=c[0]['execution_cost_USDT'],execution_cost_USDT=c[0]['fees_USDT']))
 negative('native_fee_decimal_last_digit_changed',lambda c:c[0].__setitem__('fees_USDT',c[0]['fees_USDT']+'1'))
 negative('wrong_duplicate_group_other_tier',lambda c:c[3].__setitem__('duplicate_realized_path_group',c[1]['duplicate_realized_path_group']))
 negative('duplicate_as_independent_confirmation',lambda c:c[3].__setitem__('duplicate_independent_confirmation',True))
 negative('original_case_runtime_zero_substitution',lambda c:c[28].__setitem__('runtime_CPU_seconds',0))
 negative('partial2021_annualized',lambda c:c[0].__setitem__('return_annualized',True))
 class ChangedProof:
  def __init__(self):self.data={k:copy.deepcopy(v)for k,v in inp.cache.items()};self.files=copy.deepcopy(inp.files)
  def load(self,p):return self.data[p]
 for name,path,key in [('missing_2025_duplicate_path_proof',m.P25+'/H090_STATIC50_THREE_TIER_PATH_COMPARISON.json','rows'),('missing_2023_duplicate_proof',m.OVERALL,'exact_H090_STATIC50_realized_equivalence_groups')]:
  changed=ChangedProof();changed.data[path][key]=[]
  try:m.verify_duplicates(changed,copy.deepcopy(rows))
  except (ValueError,AssertionError,KeyError) as e:negatives.append({'name':name,'rejected':True,'reason':str(e)})
  else:raise AssertionError('NEGATIVE_ACCEPTED:'+name)
 for name,cell,field,value in [('false_2023_full_path_byte_equality','2023_H090_LOW','full37column_minute_matrix_byte_identical',False),('wrong_2024_duplicate_donor_period','2024_H090_LOW','saved_D_STATIC_case','bounded_native_continuation_guard50_exit_expansion_20261015/actual_first5_attempt001/2023_STATIC50_LOW')]:
  changed=ChangedProof();path=m.PX+'/actual_remaining12_saved_review/'+cell+'_STATIC50_REALIZED_EQUIVALENCE.json';changed.data[path][field]=value
  try:m.verify_duplicates(changed,copy.deepcopy(rows))
  except (ValueError,AssertionError,KeyError) as e:negatives.append({'name':name,'rejected':True,'reason':str(e)})
  else:raise AssertionError('NEGATIVE_ACCEPTED:'+name)
 # Recheck all direct immutable inputs and every additionally inspected leaf/code after review.
 for p,h in before.items():eq(sha(ROOT/p),h,'input unchanged '+p)
 for p,h in leaf_refs.items():eq(sha(ROOT/p),h,'leaf review unchanged '+p)
 for p,h in codes.items():eq(sha(ROOT/p),h,'code unchanged '+p)
 report={'schema':'INDEPENDENT_MASTER45_SAVED_REPORT_FIELD_REVIEW_V1','status':'PASS','CPU_affinity':sorted(os.sched_getaffinity(0)),'numerical_pools':1,'actual_claim_rows':len(rows),'posthoc_duplicate_groups':15,'distinct_realized_paths':30,'independent_strategy_confirmations':False,'financial_replays_accounts_providers_source_targets_GO_claims_network_publication':0,'direct_input_count':len(before),'exact_JSON_field_pointers_checked':all_fields,'additional_leaf_review_pins':leaf_refs,'original_code_files_pinned_and_unchanged':codes,'independent_rows':per,'changed_copy_negative_tests':negatives,'original_inputs_code_and_leaf_reviews_unchanged':True,'author_file_pins':{p.name:{'SHA256':sha(p),'bytes':p.stat().st_size}for p in [AUTHOR/'MASTER45.csv',AUTHOR/'MASTER45.md',AUTHOR/'MASTER45_ROWS.json',AUTHOR/'INPUT_PINMAP.json',AUTHOR/'assemble_master45.py']}}
 (HERE/'INDEPENDENT_FIELD_REVIEW.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':'PASS','rows':45,'field_pointers':all_fields,'negative_tests':len(negatives),'direct_inputs':len(before),'code_files':len(codes),'receipt_SHA256':sha(HERE/'INDEPENDENT_FIELD_REVIEW.json')},indent=2))
if __name__=='__main__':run()
