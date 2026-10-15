"""Read saved JSON only; no accounts, clocks, providers, source arrays or network."""
from pathlib import Path
from decimal import Decimal, localcontext
from datetime import datetime,timezone
import hashlib,json,gzip,csv,io
PACKET_NAME='traditional_D_full2022_nine_compact_saved_results_public_recovery_20261015_v2'
ATT='traditional_D_full2022_20261015_v2_financial_attempt001'
REV='traditional_D_full2022_saved_results_independent_review_20261015'
EXEC='traditional_D_full2022_20261015_v2'
PREPDIR='traditional_D_full2022_20261015_v2_source_preparation_attempt001'
CELLS=tuple('2022_'+s+'_'+t+'_JAN1_DEC31_D' for s in ('STATIC50','H090','VOL_MANAGED_HOLD') for t in ('LOW','MID','HIGH'))
GO='bb9e7d6f969d3a07c5adc423d638d6b3c4b3b9044b717657c18a08c509dffa3e'
PREP='a4afcb2eb87d28936ba8d28e17dca52406fd63bbec2070c2036da1d5633fd9cf'
SOURCE_REVIEW='6fe46f96a5cac8d1c8f0830448eaa1d964fc35cf882ef92ccde7817cdd47644d'
CHECKER='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
FROZEN='c960bc137a1df1ee719166933c0ded70ed04595b6e97f398dfd63f4bf0785a5e'
QUALITY='22b2623be5bd11b0f6e79a24a477aa622db7e06171f8be901bf867da9a54bbcc'
SOURCE_ARCHIVE='a58c4b89a639134cb2e352a54211d6b801d446a2f6830cc87d1d1cecc94c1bdc'
SOURCE_PACKET_REVIEW='823b91574d604ead9a8a2ed6186ad1676ae79701e9dde50485efec749a24cc74'
FINAL_REVIEW='178e9c7f4ac8b4a63a6c9a4b2e1688d7fcfbe4e0e56546da1179abc13144c26b'
ROOT_EXIT='755f13481ff0b4938de86e20284951f395f9f407e6905a0ea1874e66c8e1e6ee'
VERSION='ORIGINAL_D_GUARD50_EXIT_FULL2022_JAN1_DEC31_NINE_DEV_V1'
CALENDAR=[1640995200000000,1672531200000000]
PRIVATE_NAMES=('ADMISSION_GO.json','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json','BOOTSTRAP_READY.json','ADMISSION_REVIEW.json')
SCOPE={'accounts_constructed':0,'financial_minutes_advanced':0,'financial_replays':0,'provider_iterations':0,'provider_downloads':0,'source_target_covariance_arrays_opened':0,'MINUTE_arrays_opened':0,'publication_performed':False,'period_start_UTC':'2022-01-01','period_end_inclusive_UTC':'2022-12-31','period_days':365,'minutes_per_case':525600,'separate_fresh_10000_DEV_accounts':9,'all_nine_approved_jobs_retained':True,'annual_wallets_compounded':False,'continuous_CAGR':None,'return_annualized':False,'OOS_or_live_performance_claim':False,'nominal_tier_is_not_exact_realized_risk_matching':True,'minute_risk_regenerated_by_compact_packet':False,'minute_risk_values_are_independently_reviewed_saved_evidence':True,'all_observation_MDD_does_not_establish_intraminute_market_price_path':True,'source27_quality':'UNKNOWN_OR_DERIVED','historical_arrival_installation_certified':False,'actual_exchange_liquidation_or_no_liquidation_certified':False,'counterfactual_mark_sensitivity_identified':False,'native40_event_arithmetic_authoritative':True,'raw100_diagnostics_retained_without_epsilon_or_forced_balancing':True,'new_run_or_publication_authority':False}
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
def impact_projection(review):
 a=review['source27_impact_audit'];cells=a['cells']
 keys=('actual_affected_asset_trades_during_unknown','actual_any_asset_trades_during_unknown','actual_owned_funding_during_unknown','conditional_model_settlements_during_unknown','new_unknown_warning_actions','paid_fill_mark_reference_during_unknown','saved_execution_attempt_outcomes_during_unknown','saved_financial_event_batches_during_unknown','saved_guard_records_during_unknown')
 counts={k:{'asset_minute_references':sum(len(c.get(k,[])) for c in cells),'unique_record_count':len(unique_records(cells,k))} for k in keys}
 return {'source_sidecar_SHA256':a['source_sidecar_SHA256'],'source_asset_minute_cells':a['actual_cell_count'],'held_asset_minute_cells':a['affected_held_asset_minute_cells'],'unique_missing_open_clocks':a['unique_missing_open_clocks'],'asset_runs':a['asset_runs'],'longest_asset_run_minutes':a['longest_asset_run_minutes'],'observed_unknown_interval_event_counts':counts,'new_unknown_quality_warning_actions':a['unknown_quality_itself_created_new_warning_actions'],'carried_native_guard50_predicate_true_asset_minutes':sum(c['carried_mark_native_risk_predicate']['model_guard50_equity_le_half_balance'] for c in cells),'carried_native_equity_le_maintenance_asset_minutes':sum(c['carried_mark_native_risk_predicate']['model_equity_le_maintenance'] for c in cells),'genuine_recovery_minute_present_asset_cells':sum(c['genuine_recovery_minute_present'] for c in cells),'genuine_recovery_marked_notional_checked_asset_cells':sum(c['saved_recovery_marked_notional_matches_genuine_price_float_projection'] for c in cells),'per_asset_minute':[{k:c[k] for k in ('symbol','missing_open_us','missing_completed_us','source_quality','actual_quantity_nonzero','actual_affected_position','genuine_anchor','carried_mark_native_risk_predicate','genuine_recovery_completed_us','genuine_recovery_minute_present','actual_arrival_installation','terminal_direct_clock_overlap','counterfactual_cashflow_quantity_sensitivity')} for c in cells],'no_counterfactual_replay':True,'counterfactual_terminal_return_sensitivity':'NOT_IDENTIFIED','zero_observed_overlap_does_not_prove_negligible_effect':True,'actual_exchange_liquidation_or_no_liquidation_certified':False}
def row(root,cell):
 root=Path(root);d=root/ATT/cell;r=load(d/'NATIVE_RESULT.json');a=load(d/'ACCOUNT_FINANCIAL_AUDIT.json');s=r['summary'];ds=s['decimal_strings'];rv=load(root/REV/(cell+'_REVIEW.json'));risk=rv['actual_held_exposure_and_both_covariance_phase_risk'];tr=a['trades'];last=max(t['event_us'] for t in tr) if tr else None;first=min(t['event_us'] for t in tr) if tr else None
 return dict(cell_id=cell,year=2022,strategy=rv['strategy'],tier=rv['tier'],calendar=CALENDAR,completed_minutes=rv['completed_minutes'],initial_wallet_USDT='10000',terminal_classification=rv['terminal_classification'],terminal_NAV_USDT=ds['NAV'],exact_marked_net_return=exact_return(ds['NAV']),fees_USDT=ds['fees_USDT'],execution_cost_USDT=ds['execution_cost_USDT'],signed_funding_USDT=ds['funding_USDT'],actual_owned_funding_USDT=rv['owned_funding_USDT'],actual_paid_turnover_USDT=rv['actual_paid_turnover_USDT'],paid_trade_rows=rv['paid_trade_rows'],paid_open_legs=rv['paid_open_legs'],paid_close_legs=rv['paid_close_legs'],D_warning_episode_count=rv['D_warning_episode_count'],D_warning_episodes=rv['D_warning_episodes'],economic_qualification=rv['economics'],funding_counts=dict(source_scheduler_rows=rv['scheduler_source_funding_rows'],saved_native_rows=rv['total_saved_funding_rows'],owned_native_rows=rv['owned_funding_rows'],fresh_flat_no_past_mark_events=s['fresh_flat_no_past_mark_events']),actual_first_paid_fill_us=first,actual_first_paid_fill_UTC=utc(first),actual_last_paid_fill_us=last,actual_last_paid_fill_UTC=utc(last),terminal_close_legs=rv['terminal_close_legs'],minimum_free_cash_all_native_observations_USDT=s['minimum_actual_free_cash_all_observations_USDT'],maximum_gross_weight_all_native_observations=s['maximum_actual_gross_weight'],maximum_absolute_asset_weight_all_native_observations=s['maximum_actual_asset_weights'],actual_held_exposure_and_both_covariance_phase_risk=risk,original_actual_held_risk_report=load(d/'ACTUAL_HELD_RISK_REPORT.json'),source27_impact=impact_projection(rv),native40_proof=rv['native40_proof'],independent_saved_review_SHA256=sha(root/REV/(cell+'_REVIEW.json')))
def build(root):
 root=Path(root);rows=[row(root,c) for c in CELLS];final=load(root/REV/'FINAL_NINE_SAVED_REVIEW_RECEIPT.json')
 return {'schema':'ORIGINAL_D_FULL2022_EXACT_NINE_COMPACT_SAVED_REPORT_V1','scope':dict(SCOPE),'rows':rows,'H090_STATIC50_same_tier_actual_paths':final['H090_STATIC50_same_tier_actual_paths'],'all_nine_final_review_SHA256':sha(root/REV/'FINAL_NINE_SAVED_REVIEW_RECEIPT.json'),'qualifications':['Nine separate fresh 10000-USDT Jan1-Dec31 2022 adaptive DEV accounts; 365 days and 525600 minutes each. No annual wallet compounding, continuous CAGR, out-of-sample claim or performance selection.','Exact native40 chronological event-state reconstruction is monetary authority. Precision100 stored-delta diagnostics and legacy residual booleans remain unchanged; no epsilon, tolerance, repair or forced balancing.','Source marks contain 27 UNKNOWN_OR_DERIVED asset-minutes at 11 OPEN clocks in 8 runs, longest 7 minutes. Genuine past anchors retain their age and historical arrival/installation is UNKNOWN. They affect held valuation and native risk predicates.','Observed unknown-interval trade, funding, attempt and Guard50 counts are descriptive saved evidence. Latent eligible-but-unattempted scheduler intents remain unidentified. Even zero direct overlaps do not establish negligible counterfactual cashflow, quantity, terminal return or liquidation sensitivity. No alternative-mark replay occurred.','Actual gross/asset/cash/isolated-margin paths, native all-observation MDD and both exact-midnight covariance phase conventions are retained. Nominal budgets and entry caps do not establish exact realized-risk matching or continuous marked-state guarantees.','Actual terminal paid-fill clocks and warning-paid closures are retained. Any proven same-tier H090/STATIC50 duplicate realized paths are post-hoc dependent evidence; all nine separately executed approved jobs remain retained.','Compact checks reconstruct full exact financial event states from saved JSON. All-minute exposure/MDD/forecast-risk regeneration requires omitted exact local MINUTE and covariance/source arrays, or a fresh separately admitted identical run. Hashes cannot recreate omitted bytes.','Real exchange fills, funding units/publication, historical arrival, venue filters, maintenance tiers, insurance/ADL and liquidation or no-liquidation are uncertified model assumptions. Conditional model settlements are distinguished from actual paid-market closures.','The original result economics source27 field may still say PENDING_ACTUAL_SAVED_EVIDENCE. It is preserved unchanged; the separate independently reviewed post-hoc 27-cell owned-inventory/event-dependency proof is included.','Source remote publication remains a separate prerequisite. This local packet grants no financial execution, claim, restart or publication authority.']}
CSV_FIELDS=['cell_id','strategy','tier','completed_minutes','initial_wallet_USDT','terminal_classification','terminal_NAV_USDT','exact_marked_net_return','fees_USDT','execution_cost_USDT','signed_funding_USDT','actual_paid_turnover_USDT','paid_trade_rows','paid_close_legs','D_warning_episode_count','actual_first_paid_fill_us','actual_last_paid_fill_us']
def render_csv(rows):
 out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=CSV_FIELDS,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows);return out.getvalue()
def render_text(report):
 text=['ORIGINAL D FULL2022: SAVED RESULTS','Jan1-Dec31 2022 UTC; nine separate fresh 10000-USDT adaptive DEV accounts; 525600 minutes each.','']
 for r in report['rows']:
  risk=r['actual_held_exposure_and_both_covariance_phase_risk'];ph=risk['covariance_phases'];counts='/'.join(str(v['overshoot_minutes_above_reporting_tolerance_1e10']) for v in ph.values())
  text.append(f"{r['strategy']} {r['tier']}: exact return {r['exact_marked_net_return']}; NAV {r['terminal_NAV_USDT']}; native all-observation MDD {risk['MDD_scopes']['native_all_observation']['max_drawdown']}; fees {r['fees_USDT']}; execution cost {r['execution_cost_USDT']}; owned funding {r['actual_owned_funding_USDT']}; forecast overshoot minutes (both phases) {counts}; D warning episodes {r['D_warning_episode_count']}; held UNKNOWN source cells {r['source27_impact']['held_asset_minute_cells']}/27; final paid fill {r['actual_last_paid_fill_UTC']}.")
 return '\n'.join(text+['','QUALIFICATIONS']+['- '+q for q in report['qualifications']])+'\n'
