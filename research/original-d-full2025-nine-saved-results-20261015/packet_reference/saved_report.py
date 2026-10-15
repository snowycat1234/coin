"""Read saved JSON only; no accounts, clocks, providers, source arrays or network."""
from pathlib import Path
from decimal import Decimal, localcontext
from datetime import datetime,timezone
import hashlib,json,gzip,csv,io
PACKET_NAME='traditional_D_full2025_nine_compact_saved_results_public_recovery_20261015_v1'
ATT='traditional_D_full2025_20261015_financial_attempt001'
REV='traditional_D_full2025_saved_results_independent_review_20261015'
EXEC='traditional_D_full2025_20261015'
PREPDIR='traditional_D_full2025_20261015_source_preparation_attempt001'
CELLS=tuple('2025_'+s+'_'+t+'_JAN1_DEC31_D' for s in ('STATIC50','H090','VOL_MANAGED_HOLD') for t in ('LOW','MID','HIGH'))
GO='6e461c3b47ee4318683cd94fd1e9fd8296b91d6848b5a0bfe71b252f13c8aba9'
PREP='847fd5123ad94a7fbd0e1bd51cd9b969737859a1e8cff03346e806994da57eab'
SOURCE_REVIEW='45b9f520b6f69d8b00b2fd2621ebd195a363d64b756a29d26826105f912ab2b8'
CHECKER='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
FROZEN='e967a444e88d063772ba3f33ec87159a85eb5a320d2b4cf4018239fbdde58ab2'
QUALITY='47eeea07fb3965203f12c6101554f79dc959419a848a8f93ce3892298abf1a36'
SOURCE_ARCHIVE='e2278f738d5f2a3aa2d2d71a1b81bf80f80ebe96eeeeaea27a69a39edb0beade'
SOURCE_PACKET_REVIEW='531f4a662c4078be03079a7ed33fcf5199fa4d9706feba0a1c7c81935b690581'
FINAL_REVIEW='6c5618f7b974a0dbd26f0eb61a0a18829be8fcefe497cc786e263447113c9df2'
ROOT_EXIT='b6158d0bf41eb283d377eae193e8ae78357b815b144cdc10137462d59e031997'
VERSION='ORIGINAL_D_GUARD50_EXIT_FULL2025_JAN1_DEC31_NINE_DEV_V1'
CALENDAR=[1735689600000000,1767225600000000]
PRIVATE_NAMES=('ADMISSION_GO.json','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json','BOOTSTRAP_READY.json','ADMISSION_REVIEW.json')
SCOPE={'counts_apply_to':'compact_native40_and_report_regeneration_only','accounts_constructed':0,'financial_minutes_advanced':0,'financial_replays':0,'provider_iterations':0,'provider_downloads':0,'source_target_covariance_arrays_opened':0,'MINUTE_arrays_opened':0,'publication_performed':False,'period_start_UTC':'2025-01-01','period_end_inclusive_UTC':'2025-12-31','period_days':365,'minutes_per_case':525600,'separate_fresh_10000_DEV_accounts':9,'all_nine_approved_jobs_retained':True,'annual_wallets_compounded':False,'continuous_CAGR':None,'return_annualized':False,'OOS_or_live_performance_claim':False,'nominal_tier_is_not_exact_realized_risk_matching':True,'minute_risk_regenerated_by_compact_packet':False,'minute_risk_values_are_independently_reviewed_saved_evidence':True,'all_observation_MDD_does_not_establish_intraminute_market_price_path':True,'derived_source_asset_minutes':0,'no_source_imputation':True,'historical_arrival_installation_certified':False,'actual_exchange_liquidation_or_no_liquidation_certified':False,'counterfactual_mark_sensitivity_identified':False,'native40_event_arithmetic_authoritative':True,'raw100_diagnostics_retained_without_epsilon_or_forced_balancing':True,'new_run_or_publication_authority':False}
def raw(path):
 p=Path(path)
 if p.exists():return p.read_bytes()
 return gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
def strict_json(data):
 def pairs(items):
  out={}
  for k,v in items:
   require(k not in out,'DUPLICATE_JSON_OBJECT_KEY:'+str(k));out[k]=v
  return out
 return json.loads(data,object_pairs_hook=pairs)
def load(path):return strict_json(raw(path))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def same(a,b):return canonical(a)==canonical(b)
def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):return hashlib.sha256(raw(path)).hexdigest()
def json_bytes(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def validate_scope(v):require(same(v,SCOPE),'EXACT_TYPED_HONEST_SAVED_SCOPE_REQUIRED')
def utc(us):return datetime.fromtimestamp(us/1e6,timezone.utc).isoformat() if us is not None else None
def exact_return(nav):
 with localcontext() as c:c.prec=100;return str((Decimal(nav)-Decimal('10000'))/Decimal('10000'))
def unique_records(cells,key):
 vals={canonical(v):v for cell in cells for v in cell.get(key,[])}
 return list(vals.values())
def row(root,cell):
 root=Path(root);d=root/ATT/cell;r=load(d/'NATIVE_RESULT.json');a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');s=r['summary'];ds=s['decimal_strings'];rv=load(root/REV/(cell+'_REVIEW.json'));risk=rv['actual_held_exposure_and_both_covariance_phase_risk'];tr=a['trades'];last=max(t['event_us'] for t in tr) if tr else None;first=min(t['event_us'] for t in tr) if tr else None
 return dict(cell_id=cell,year=2025,strategy=rv['strategy'],tier=rv['tier'],calendar=CALENDAR,completed_minutes=rv['completed_minutes'],initial_wallet_USDT='10000',terminal_classification=rv['terminal_classification'],terminal_NAV_USDT=ds['NAV'],exact_marked_net_return=exact_return(ds['NAV']),fees_USDT=ds['fees_USDT'],execution_cost_USDT=ds['execution_cost_USDT'],signed_funding_USDT=ds['funding_USDT'],actual_owned_funding_USDT=rv['owned_funding_USDT'],actual_paid_turnover_USDT=rv['actual_paid_turnover_USDT'],paid_trade_rows=rv['paid_trade_rows'],paid_open_legs=rv['paid_open_legs'],paid_close_legs=rv['paid_close_legs'],D_warning_episode_count=rv['D_warning_episode_count'],D_warning_episodes=rv['D_warning_episodes'],economic_qualification=rv['economics'],funding_counts=dict(source_scheduler_rows=rv['scheduler_source_funding_rows'],saved_native_rows=rv['total_saved_funding_rows'],owned_native_rows=rv['owned_funding_rows'],fresh_flat_no_past_mark_events=s['fresh_flat_no_past_mark_events']),actual_first_paid_fill_us=first,actual_first_paid_fill_UTC=utc(first),actual_last_paid_fill_us=last,actual_last_paid_fill_UTC=utc(last),terminal_close_legs=rv['terminal_close_legs'],minimum_free_cash_all_native_observations_USDT=s['minimum_actual_free_cash_all_observations_USDT'],maximum_gross_weight_all_native_observations=s['maximum_actual_gross_weight'],maximum_absolute_asset_weight_all_native_observations=s['maximum_actual_asset_weights'],actual_held_exposure_and_both_covariance_phase_risk=risk,original_actual_held_risk_report=load(d/'ACTUAL_HELD_RISK_REPORT.json'),source_quality_review=rv['source_quality_review'],coldstart_no_position_no_past_mark_funding=rv['coldstart_no_position_no_past_mark_funding'],source_target_covariance_calendar_binding=rv['target_covariance_calendar_binding'],source_identity=rv['source_identity'],terminal_summary_clock_us=s['clock_us'],terminal_summary_stop_us=s['stop_us'],terminal_summary_completion=s['completion'],terminal_summary_paid_flat=r['economics']['paid_flat'],unpaid_liability_USDT=ds['unpaid_liability'],native40_proof=rv['native40_proof'],independent_saved_review_SHA256=sha(root/REV/(cell+'_REVIEW.json')))
def build(root):
 root=Path(root);rows=[row(root,c) for c in CELLS];final=load(root/REV/'FINAL_NINE_SAVED_REVIEW_RECEIPT.json')
 require(all(Decimal(r['exact_marked_net_return'])<0 for r in rows),'ALL_NINE_NET_NEGATIVE_SAVED_RESULTS')
 comparison=load(root/REV/'H090_STATIC50_THREE_TIER_PATH_COMPARISON.json');distinct_paths=len({r['terminal_NAV_USDT'] for r in rows});require(distinct_paths==6,'SIX_DISTINCT_TERMINAL_NAVS_WITH_THREE_PROVEN_EQUAL_PATH_PAIRS')
 return {'schema':'ORIGINAL_D_FULL2025_EXACT_NINE_COMPACT_SAVED_REPORT_V1','scope':dict(SCOPE),'rows':rows,'H090_STATIC50_same_tier_actual_paths':final['H090_STATIC50_same_tier_actual_paths'],'all_nine_net_negative':True,'distinct_realized_minute_paths':distinct_paths,'distinct_path_count_derivation':'Six distinct exact terminal NAVs establish at least six distinct paths; all three full-minute H090/STATIC50 equality proofs establish at most six among nine.','same_tier_path_comparison_proof':comparison,'coldstart':final['coldstart'],'same_year_same_source_A_D_reference':final['same_year_same_source_A_D_reference'],'source_quality':final['source_quality'],'native_all_observation_supplement':final['native_all_observation_supplement'],'all_nine_final_review_SHA256':sha(root/REV/'FINAL_NINE_SAVED_REVIEW_RECEIPT.json'),'qualifications':[
 'Nine separate fresh 10000-USDT Jan1-Dec31 2025 adaptive DEV accounts; 365 days and 525600 minutes each. All nine approved jobs are retained. No annual wallet compounding, continuous CAGR, out-of-sample claim or performance selection.',
 'All nine marked net returns are negative. Exact native40 chronological event-state reconstruction is monetary authority. Precision100 stored-delta diagnostics and legacy residual booleans remain unchanged; no epsilon, tolerance, repair or forced balancing.',
 'The full2025 source has zero derived or imputed mark asset-minutes, an empty derived-quality sidecar and a genuine Dec31 23:59 native endpoint. No old 2022 27-point carry provenance applies. Actual historical arrival and installation remain UNKNOWN_NOT_CERTIFIED.',
 'All cases complete 525600 minutes and end actual-paid-market-flat with zero debt and no conditional settlements. Actual terminal paid-fill clocks and warning-paid closures are retained.',
 'Each full-calendar case observes 5475 scheduled source funding events. Five Jan1+15ms events are unowned, have no prior completed mark and charge zero; 5470 rows reach the native account. Source coverage is distinct from owned funding charges.',
 'Actual gross/asset/cash/isolated-margin paths, native all-observation MDD and both exact-midnight covariance phase conventions are retained. Nominal budgets and entry caps do not establish exact realized-risk matching or continuous marked-state guarantees. The 1e-10 overshoot threshold is reporting-only; strict-positive counts are retained and financial equality uses no tolerance.',
 'All three same-tier H090/STATIC50 pairs have bit-equal saved minute fields over the entire 525600-minute year, despite distinct launched claims and different selected raw targets. They are post-hoc dependent evidence, not independent confirmation. The nine executions represent six distinct realized minute paths; no alias or pruning is applied.',
 'Compact checks reconstruct exact chronological financial event states from saved JSON. Full-minute exposure/MDD/forecast-risk regeneration requires omitted exact local MINUTE and covariance/source arrays, or a fresh separately admitted identical run. Hashes cannot recreate omitted bytes. The complete intraminute path and separate signal-only/fill-only MDD are not persisted.',
 'Real exchange fills, raw funding units/publication, historical arrival, venue filters, maintenance tiers, insurance/ADL and liquidation or no-liquidation are uncertified model assumptions. Conditional model settlements are distinct from actual paid-market closures.',
 'No eligible native full2025 A/D reference bound to this exact source identity exists in the admitted evidence. Wrong-year, daily-proxy, legacy CS and old-contract references were not substituted.',
 'The source/generated packet has no financial outcomes. Qualifier V1 failed-path evidence is preserved there and is not a global no-financial-execution claim. This results packaging and its cold checks perform no new financial/source execution.',
 'Source remote publication is capability-blocked and remains a separate prerequisite. The pending dependency chain is 2022 source, 2022 results, 2025 source, then these 2025 results. No remote commit or remote-byte verification is claimed. This local packet grants no financial execution, claim, restart or publication authority.']}
CSV_FIELDS=['cell_id','strategy','tier','completed_minutes','initial_wallet_USDT','terminal_classification','terminal_NAV_USDT','exact_marked_net_return','fees_USDT','execution_cost_USDT','signed_funding_USDT','actual_paid_turnover_USDT','paid_trade_rows','paid_close_legs','D_warning_episode_count','actual_first_paid_fill_us','actual_last_paid_fill_us']
def render_csv(rows):
 out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=CSV_FIELDS,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows);return out.getvalue()
def render_text(report):
 text=['ORIGINAL D FULL2025: SAVED RESULTS','Jan1-Dec31 2025 UTC; nine separate fresh 10000-USDT adaptive DEV accounts; 525600 minutes each. All nine net-negative; six distinct realized minute paths.','']
 for r in report['rows']:
  risk=r['actual_held_exposure_and_both_covariance_phase_risk'];ph=risk['covariance_phases'];counts='/'.join(str(v['overshoot_minutes_above_reporting_tolerance_1e10']) for v in ph.values())
  text.append(f"{r['strategy']} {r['tier']}: exact return {r['exact_marked_net_return']}; NAV {r['terminal_NAV_USDT']}; native all-observation MDD {risk['MDD_scopes']['native_all_observation']['max_drawdown']}; fees {r['fees_USDT']}; execution cost {r['execution_cost_USDT']}; owned funding {r['actual_owned_funding_USDT']}; forecast overshoot minutes (both phases) {counts}; D warning episodes {r['D_warning_episode_count']}; final paid fill {r['actual_last_paid_fill_UTC']}.")
 return '\n'.join(text+['','QUALIFICATIONS']+['- '+q for q in report['qualifications']])+'\n'
