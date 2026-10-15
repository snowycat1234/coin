from pathlib import Path
from decimal import Decimal
import ast,hashlib,json
R=Path(__file__).resolve().parent.parent
O=Path(__file__).resolve().parent
P=R/'saved_distinct_family_risk_evidence_20261015'
D=P/'final_saved_analysis_attempt001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
report=read(D/'RISK_EVIDENCE.json');index=read(P/'AUTHORIZED_FINAL_INPUT_INDEX.json')
assert report['source_code_SHA256']==sha(P/'saved_family_risk.py')=='f0e9c6dc001e26c61116e37e91628e850acb0612c5b48e0764793d9b930000bd'
assert report['input_index_SHA256']==sha(P/'AUTHORIZED_FINAL_INPUT_INDEX.json')=='e307ee6dbf4c4e2f01a1bd1bfbf4e37ee280bf1d79f200a73e77832f763d4660'
assert report['input_index']==index and report['parent_commit']=='48e42f4040e317edf732bfedc9dce5d54e29ed12'
for ref in [index[k] for k in ('comparison','comparison_index','frozen_manifest','exact_path_signatures_addendum')]:assert sha(R/ref['path'])==ref['SHA256']
original=read(D/'ORIGINAL_18ROW_COMPARISON.json');originalrows={r['cell_id']:r for r in original['rows']}
small={}
for cell in report['cells']:
 row=cell['authoritative_reviewed_matrix_row'];assert row==originalrows[cell['cell_id']]
 for ref in cell['reviewed_JSON_references_rehashed'].values():
  if isinstance(ref,dict) and set(ref)=={'path','SHA256'}:
   assert sha(R/ref['path'])==ref['SHA256'];small[ref['path']]=ref['SHA256']
 q=row['bindings']['original_saved_quality'];assert sha(R/q['reference']['path'])==q['reference']['SHA256'];assert read(R/q['reference']['path'])==q['value']
 small[q['reference']['path']]=q['reference']['SHA256']
lookup={c['cell_id']:c for c in report['cells']}
counts={'HOLD_raw_return_higher':0,'HOLD_vol_higher':0,'HOLD_native_MDD_higher':0,'HOLD_fullsample_return_per_vol_higher':0,'HOLD_gross_mean_lower':0,'HOLD_net_mean_higher':0,'HOLD_turnover_lower':0,'HOLD_fees_lower':0,'HOLD_execution_lower':0,'HOLD_funding_more_negative':0,'HOLD_overshoot_minutes_higher':0}
for pair in report['paired_comparisons']:
 s=lookup[pair['STATIC50_cell_id']];h=lookup[pair['VOL_MANAGED_HOLD_cell_id']];sa=s['saved_float64_aggregate'];ha=h['saved_float64_aggregate'];sc=s['native_costs'];hc=h['native_costs']
 counts['HOLD_raw_return_higher']+=Decimal(h['native_exact_paid_annual_return_fraction'])>Decimal(s['native_exact_paid_annual_return_fraction'])
 counts['HOLD_vol_higher']+=ha['daily_realized_annual_volatility']>sa['daily_realized_annual_volatility']
 counts['HOLD_native_MDD_higher']+=h['all_observation_native_MDD_fraction']>s['all_observation_native_MDD_fraction']
 k='paid_return_div_full_sample_daily_realized_annual_volatility';counts['HOLD_fullsample_return_per_vol_higher']+=Decimal(h['future_informed_descriptive_ratios'][k])>Decimal(s['future_informed_descriptive_ratios'][k])
 counts['HOLD_gross_mean_lower']+=ha['gross_weight_mean']<sa['gross_weight_mean'];counts['HOLD_net_mean_higher']+=ha['net_signed_weight_mean']>sa['net_signed_weight_mean']
 counts['HOLD_turnover_lower']+=Decimal(h['native_exact_paid_turnover_USDT'])<Decimal(s['native_exact_paid_turnover_USDT'])
 for key,label in [('fees_USDT','HOLD_fees_lower'),('execution_price_cost_USDT','HOLD_execution_lower'),('signed_funding_USDT','HOLD_funding_more_negative')]:counts[label]+=Decimal(hc[key])<Decimal(sc[key])
 counts['HOLD_overshoot_minutes_higher']+=h['forecast_risk_approved_report']['forecast_budget_overshoot_minutes']>s['forecast_risk_approved_report']['forecast_budget_overshoot_minutes']
 assert h['native_paid_warning_signals']==0 and all(a['signed_min']>=0 for a in ha['asset_weights'].values())
assert counts=={'HOLD_raw_return_higher':6,'HOLD_vol_higher':6,'HOLD_native_MDD_higher':4,'HOLD_fullsample_return_per_vol_higher':3,'HOLD_gross_mean_lower':5,'HOLD_net_mean_higher':6,'HOLD_turnover_lower':6,'HOLD_fees_lower':6,'HOLD_execution_lower':6,'HOLD_funding_more_negative':6,'HOLD_overshoot_minutes_higher':6}
tree=ast.parse((P/'saved_family_risk.py').read_text());imports=[]
for node in ast.walk(tree):
 if isinstance(node,ast.Import):imports.extend(n.name for n in node.names)
 if isinstance(node,ast.ImportFrom):imports.append(node.module)
assert set(imports)<= {'__future__','argparse','datetime','decimal','csv','hashlib','json','pathlib','typing','numpy'}
raw=read(O/'FAMILY_SAVED_ARRAY_ARITHMETIC_REVIEW.json');assert raw['status']=='PASS_ALL12_SAVED_ARRAYS_DAILY_AND_AGGREGATE_ARITHMETIC'
files=[P/'saved_family_risk.py',P/'test_saved_family_risk.py',P/'README.txt',P/'INTERPRETATION.txt',P/'AUTHORIZED_FINAL_INPUT_INDEX.json',O/'test_family_independent.py',O/'check_family_saved_arrays.py',O/'seal_family_review.py',O/'FAMILY_AUTHOR_FIXTURES_FINAL.txt',O/'FAMILY_INDEPENDENT_FIXTURES_FINAL.txt',O/'FAMILY_PUBLIC_RECOMPUTE.txt',O/'FAMILY_SAVED_ARRAY_ARITHMETIC_REVIEW.json',O/'FAMILY_SAVED_ARRAY_ARITHMETIC_REVIEW.log',D/'RISK_EVIDENCE.json',D/'COMPACT_ARTIFACT_MANIFEST.json',D/'REPORT.txt',D/'ANNUAL_CELLS.csv',D/'PAIRED_COMPARISONS.csv',D/'EXACT_DUPLICATE_EVIDENCE.json',D/'ORIGINAL_18ROW_COMPARISON.json',D/'INPUT_INDEX.json']
x={'schema':'INDEPENDENT_SAVED_DISTINCT_FAMILY_MODULE_FINAL_REVIEW_V1','status':'PASS_CODE_GENERATED_FIXTURES_ALL12_SAVED_OUTPUT_ARITHMETIC_AND_COMPACT_REPRODUCTION','parent_commit':report['parent_commit'],'author_generated_tests':13,'independent_generated_tests':7,'fixed_annual_family_cases':12,'matched_pairs':6,'original_cohort_cases':18,'duplicate_pairs_preserved_without_independent_count':6,'checks':['All12 original completed saved minute archives rehashed and decompressed exactly once','Exact original float64 array signatures, columns, calendars, positive finite NAV and weights projection','Exact deterministic minute NAV return hashes and all minute return summary fields','Every lossless published daily endpoint/count/cost/exposure column recomputed independently','Frozen daily realized volatility std(ddof1)*sqrt365, minute/daily MDD, gross/net/asset/flat/cash/margin summaries','Exact native financial cost strings, signed funding, turnover, original raw100 residual schemas and native same-quantity bridge preserved','Fullsample future-informed ratios independently recomputed and explicitly nonexecuted/nonOOS/nonalpha','All6 raw native paid annual return differences recomputed; original18 rows remain fixed with strict duplicates','Source/policy/calendar/GO/review/quality bound through unchanged matrix and independently rehashed small JSON','Public compact recompute PASS without original minute arrays','Narrative interpretation numerical counts checked against all six pairs'],'narrative_claim_counts':counts,'small_JSON_references_independently_rehashed':small,'file_pins':{str(p.relative_to(R)):{'SHA256':sha(p),'bytes':p.stat().st_size} for p in files},'execution':{'CPU_affinity':[5],'numerical_threads':1,'original_saved_MINUTE_archives_decompressed':12,'new_accounts':0,'financial_replays':0,'raw_prices_covariance_provider_or_holdout_reads':0,'retuning':0,'financial_code_changes':0,'author_evidence_changes':0,'publication_actions':0},'qualifications':['Independent telemetry review does not replace authoritative native40 chronological financial proofs or certify true exchange marks/execution/funding. Original raw precision100 residuals are preserved without repair.','Exact monetary strings and byte hashes are checked with no monetary epsilon. Independently accumulated daily exposure sums use2e-15relative/2e-13absolute scalar tolerance; independent dimensionless exposure summaries2e-12relative with1floor.','The final analysis requires this exact full-calendar reviewed cohort and fails closed for partial or unresolved rows. It does not extrapolate a partial history or fill a missing tail.','Daily compact evidence reproduces daily curves/aggregates/pairs. Rechecking all-minute return hashes/extrema requires the omitted original hash-pinned archives; no full minute arrays included.','HOLD raw return is higher6/6 and realized daily volatility higher6/6; fullsample return/vol favors each family3/6. These adaptive-development observations establish no causal equal-risk, executable/OOS/alpha advantage.','Report raw gap percentages denote percentage-point differences in annual return, not relative percentage growth; INTERPRETATION.txt states units explicitly.']}
p=O/'SAVED_FAMILY_RISK_MODULE_FINAL_REVIEW.json';assert not p.exists();p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':x['status'],'receipt':str(p.relative_to(R)),'SHA256':sha(p)}))
