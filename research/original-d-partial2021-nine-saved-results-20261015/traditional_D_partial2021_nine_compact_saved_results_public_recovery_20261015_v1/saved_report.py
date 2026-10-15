#!/usr/bin/env python3
"""Pure saved-JSON report. No accounts, financial clocks, source arrays or network."""
from pathlib import Path
from decimal import Decimal, localcontext
import hashlib,json,gzip,csv,io
ATT='traditional_D_partial2021_20261015/actual_nine_attempt001'
REV='traditional_D_partial2021_independent_review_20261015/actual_nine_saved_review'
OLD='bounded_native_continuation_saved_matrix_comparison_20261015/final_saved_comparison_attempt001/MATRIX_COMPARISON.json'
CELLS=tuple('2021_'+s+'_'+t+'_APR2_DEC31_D' for s in ('STATIC50','H090','VOL_MANAGED_HOLD') for t in ('LOW','MID','HIGH'))
GO='79dfb608da4e423833df12f1e512a26ff5610ae2f7ea03d41c9e62e1a2a555f8'
CHECKER='d4df52de450b6c1a83801168e0bb8069bd3dd94d3058854fda971175bf6f5135'
PREP='40e9eda0977f2fc28c051b9f1d08c214be9b384e398ef43f166100924fde3f02'
SOURCE_REVIEW='5cd2fcc60a565a91866a0ddfbce1bd41e643f97d46aaddf17601e049815e6404'
FROZEN='03b8016fd98fc2bc5c60db5800672a05a558351b4cfef760dfa34014aa5be85c'
VERSION='ORIGINAL_D_GUARD50_EXIT_PARTIAL2021_APR2_DEC31_NINE_DEV_V1'
EQUALITY='6a0216503c733d041639e2037500e811e198d1a9f7683b2df805de38131cc4e9'
CALENDAR=[1617321600000000,1640995200000000]
SCOPE={
 'accounts_constructed':0,'financial_minutes_advanced':0,'provider_downloads':0,'raw_market_source_or_target_arrays_opened':0,
 'nine_separate_fresh_initial_10000_partial_accounts':True,'all_nine_approved_executions_retained':True,
 'period':'2021-04-02 through 2021-12-31 UTC','period_days':274,'minutes_per_2021_case':394560,
 'January_March_used_only_for_warmup':True,'partial_return_annualized':False,'annual_or_cross_cell_wallets_compounded':False,
 'continuous_CAGR':None,'adaptive_DEV_only':True,'OOS_or_live_performance_claim':False,
 'native_exchange_or_funding_publication_certified':False,'nominal_budget_is_not_exact_realized_risk_matching':True,
 'financial_authority':'CHRONOLOGICAL_NATIVE40_EXACT_EVENT_STATE','raw100_residuals_preserved_without_epsilon_or_repair':True,
 'all_minute_risk_regenerated':False,'saved_risk_values_are_exact_independently_reviewed_evidence':True,
 'all_observation_MDD_does_not_establish_intraminute_price_path':True,
 'period_comparison_is_descriptive_with_different_lengths':True,'performance_winner_selection_performed':False,
 'post_hoc_STATIC50_H090_realized_duplicates_are_nonindependent':True,'full_audit_byte_identity_claim':False,
 'execution_alias_or_future_reuse_permission':False,'new_financial_run_or_publication_authority':False}

def raw(path):
 p=Path(path)
 if p.exists():return p.read_bytes()
 return gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
def load(path):return json.loads(raw(path))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def same(a,b):return canonical(a)==canonical(b)
def require(value,message):
 if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(raw(path)).hexdigest()
def json_bytes(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def validate_scope(scope):require(same(scope,SCOPE),'EXACT_TYPED_HONEST_SAVED_SCOPE_REQUIRED')
def return_string(nav):
 with localcontext() as c:
  c.prec=100
  return str((Decimal(nav)-Decimal('10000'))/Decimal('10000'))

def row2021(root,cell):
 d=Path(root)/ATT/cell;r=load(d/'NATIVE_RESULT.json');s=r['summary'];e=r['economics'];risk=load(d/'ACTUAL_HELD_RISK_REPORT.json');review=load(Path(root)/REV/(cell+'_SAVED_REVIEW.json'));ds=s['decimal_strings']
 strategy=review['strategy'];tier=review['tier']
 # Exact strings come from native saved state. Risk numbers are copied from
 # reviewed reports; their arrays are deliberately not loaded or regenerated.
 row=dict(cell_id=cell,year=2021,strategy=strategy,tier=tier,period_start_UTC='2021-04-02',period_end_inclusive_UTC='2021-12-31',period_days=274,required_minutes=394560,completed_minutes=s['completed_minutes'],initial_wallet_USDT='10000',terminal_NAV_USDT=ds['NAV'],period_return_fraction=return_string(ds['NAV']),return_taxonomy=review['terminal_status'],partial_period=True,return_annualized=False,adaptive_DEV_only=True,duplicate_realized_path_group=('2021_STATIC50_H090_'+tier+'_POST_HOC_REALIZED' if strategy in ('STATIC50','H090') else None),
 fees_USDT=ds['fees_USDT'],execution_cost_USDT=ds['execution_cost_USDT'],signed_funding_USDT=ds['funding_USDT'],gross_paid_market_turnover_USDT=e['actual_paid_market_turnover_USDT'],paid_trade_legs=s['trade_legs'],D_warning_signals=s['risk_reduction_signal_count'],D_warning_actions=review['D_warning_actions'],paid_full_warning_exits=review['paid_full_warning_exits'],internal_transfer_count=review['transfers'],conditional_settlement_count=e['conditional_position_settlements'],conditional_NAV_adjustment_USDT=e['conditional_NAV_adjustment_USDT'],conditional_collateral_forfeited_USDT=e['actual_remaining_isolated_collateral_forfeited_USDT'],conditional_positive_residual_forfeited_USDT=e['conditional_positive_residual_forfeited_USDT'],conditional_insurance_support_USDT=e['conditional_insurance_overshoot_absorption_USDT'],unpaid_liability_USDT=ds['unpaid_liability'],actual_paid_market_flat=e['actual_paid_market_flat'],
 all_observation_MDD_fraction=s['all_observation_max_drawdown'],minimum_free_cash_all_observations_USDT=s['minimum_actual_free_cash_all_observations_USDT'],gross_held_max_all_observations=s['maximum_actual_gross_weight'],absolute_asset_weight_max_by_symbol_all_observations=s['maximum_actual_asset_weights'],
 minimum_free_cash_minute_close_USDT=risk['minimum_observed_free_cash_USDT'],maximum_isolated_margin_minute_close_USDT=risk['maximum_observed_isolated_margin_USDT'],gross_held_mean_minute_close=risk['gross_exposure_mean'],gross_held_max_minute_close=risk['gross_exposure_max'],absolute_asset_weight_max_minute_close=risk['asset_exposure_absolute_max'],absolute_asset_weight_max_by_symbol_minute_close=risk['actual_absolute_weight_max_by_symbol'],absolute_asset_weight_mean_by_symbol_minute_close=risk['asset_exposure_absolute_mean_by_symbol'],signed_asset_weight_min_by_symbol_minute_close=risk['actual_signed_weight_min_by_symbol'],signed_asset_weight_max_by_symbol_minute_close=risk['actual_signed_weight_max_by_symbol'],realized_daily_annualized_volatility=risk['realized_daily_simple_return_annual_volatility'],nominal_annual_volatility_budget=risk['nominal_annual_volatility_budget'],forecast_annual_volatility_mean=risk['forecast_annual_volatility_mean'],forecast_annual_volatility_max=risk['forecast_annual_volatility_max'],forecast_max_absolute_budget_overshoot=risk['forecast_volatility_breach_max_absolute'],forecast_max_relative_budget_overshoot=risk['forecast_volatility_breach_max_relative_to_budget'],forecast_budget_overshoot_minutes=risk['forecast_volatility_breach_minutes'],observed_minute_cash_floor_breach_minutes=risk['minutes_observed_free_cash_below1000'],observed_minute_margin_ceiling_breach_minutes=risk['minutes_observed_margin_above8500'],
 observed_funding_events=s['funding_observed_events'],native_applied_funding_events=s['funding_account_applied_events'],owned_funding_events=s['funding_owned_events'],fresh_flat_no_past_mark_events=s['fresh_flat_no_past_mark_events'],first_paid_entry_us=review['first_actual_paid_entry_us'],last_paid_fill_us=review['last_actual_paid_fill_us'],terminal_signal_us=review['terminal_signal_us'],native40_secondary_PnL_bridge_residual=review['authoritative_native40_proof']['native40_secondary_PnL_bridge_residual'],raw100_stored_delta_residuals=review['authoritative_native40_proof']['raw_precision100_stored_delta_terminal_residuals'],review_sha256=sha(Path(root)/REV/(cell+'_SAVED_REVIEW.json')))
 return row

def oldrow(r):
 # A descriptive cross-period table; no annualization of partial2021 and no
 # chaining separately funded accounts. No old large financial body is loaded.
 y=r['year'];days=365 if y==2023 else 366
 keys=['cell_id','year','strategy','tier','required_minutes','completed_minutes','initial_wallet_USDT','terminal_NAV_USDT','return_taxonomy','duplicate_realized_path_group','fees_USDT','execution_cost_USDT','signed_funding_USDT','gross_paid_market_turnover_USDT','paid_trade_legs','D_warning_signals','internal_transfer_count','conditional_settlement_count','conditional_NAV_adjustment_USDT','conditional_collateral_forfeited_USDT','conditional_positive_residual_forfeited_USDT','conditional_insurance_support_USDT','unpaid_liability_USDT','all_observation_MDD_fraction','minimum_free_cash_all_observations_USDT','gross_held_max_all_observations','minimum_free_cash_minute_close_USDT','maximum_isolated_margin_minute_close_USDT','gross_held_mean_minute_close','gross_held_max_minute_close','absolute_asset_weight_max_minute_close','absolute_asset_weight_max_by_symbol_minute_close','absolute_asset_weight_mean_by_symbol_minute_close','signed_asset_weight_min_by_symbol_minute_close','signed_asset_weight_max_by_symbol_minute_close','realized_daily_annualized_volatility','nominal_annual_volatility_budget','forecast_annual_volatility_mean','forecast_annual_volatility_max','forecast_max_absolute_budget_overshoot','forecast_max_relative_budget_overshoot','forecast_budget_overshoot_minutes','observed_minute_cash_floor_breach_minutes','observed_minute_margin_ceiling_breach_minutes']
 v={k:r[k] for k in keys};v.update(period_start_UTC=str(y)+'-01-01',period_end_inclusive_UTC=str(y)+'-12-31',period_days=days,period_return_fraction=r['comparable_paid_annual_return_fraction'],partial_period=False,return_annualized=False,adaptive_DEV_only=True,actual_paid_market_flat=r['return_taxonomy']=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT')
 return v

def build(root):
 root=Path(root);rows=[row2021(root,c) for c in CELLS];old=load(root/OLD)
 require(old['status']=='FINAL_SAVED_ONLY' and old['review_approved_terminal_rows']==18 and len(old['rows'])==18,'COMPLETE_18_PRIOR_SAVED_ROWS_REQUIRED')
 previous=[oldrow(r) for r in old['rows']]
 eq=load(root/REV/'STATIC50_H090_POST_HOC_SAVED_EQUALITY.json')
 pairs=[{k:r[k] for k in ('tier','STATIC50_cell','H090_cell','both_separately_executed','raw_target_paths_byte_exact','minute_columns_byte_exact','decompressed_minute_values_byte_exact','full_saved_financial_audit_exact_except_scope_metadata','different_fill_request_records','fill_request_only_differing_fields','interpretation')} for r in eq['pairs']]
 return dict(schema='SAVED_ORIGINAL_D_PARTIAL2021_NINE_AND_DESCRIPTIVE_PRIOR_PERIODS_V1',scope=dict(SCOPE),rows=rows,descriptive_period_rows=rows+previous,post_hoc_same_tier_realized_duplicates=pairs,prior_18_saved_matrix_sha256=sha(root/OLD),equality_receipt_sha256=sha(root/REV/'STATIC50_H090_POST_HOC_SAVED_EQUALITY.json'),qualifications=[
 'All nine 2021 cases are separate fresh 10000-USDT Apr2-Dec31 accounts: 274 days and 394560 minute closes each. Jan-Mar is warmup only. Partial returns are not annualized.',
 'The 2023 and 2024 comparison rows cover 365 and 366 days. This is a descriptive period table, not an equal-horizon ranking, compounded account, continuous CAGR or out-of-sample test.',
 'STATIC50 and H090 raw target paths differ at every tier. All nine approved jobs were executed and retained. Post-hoc same-tier realized financial/minute paths duplicate evidence; requested/unfilled intent quantities and full audit bytes differ.',
 'Forecast budget overshoots and actual held risk are retained. Equal nominal budgets are not exact realized-risk matching. Admission caps and cash/margin rules are not continuous marked-state guarantees.',
 'MDD covers observed minute closes plus native fill/funding observations. It does not establish intraminute bar-high/low paths. Deep MDD/minute-risk regeneration requires omitted exact local arrays or a separately admitted identical run.',
 'Native40 chronological reconstruction is monetary authority. Raw precision100 stored-delta diagnostics are preserved, with no tolerance, epsilon, forced balancing or cashflow repair.',
 'All evidence is adaptive DEV research. Exchange execution, funding publication/units, risk tiers, insurance/ADL, quantity filters and settlement are uncertified model assumptions. No adoption, financial run or publication authority is granted.'])

CSV_FIELDS=['cell_id','year','strategy','tier','period_start_UTC','period_end_inclusive_UTC','period_days','completed_minutes','initial_wallet_USDT','terminal_NAV_USDT','period_return_fraction','return_taxonomy','partial_period','return_annualized','duplicate_realized_path_group','fees_USDT','execution_cost_USDT','signed_funding_USDT','gross_paid_market_turnover_USDT','paid_trade_legs','D_warning_signals','conditional_settlement_count','conditional_insurance_support_USDT','unpaid_liability_USDT','all_observation_MDD_fraction','gross_held_mean_minute_close','gross_held_max_minute_close','realized_daily_annualized_volatility','nominal_annual_volatility_budget','forecast_annual_volatility_max','forecast_budget_overshoot_minutes','minimum_free_cash_minute_close_USDT','maximum_isolated_margin_minute_close_USDT']
def render_csv(rows):
 out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=CSV_FIELDS,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows);return out.getvalue()
def render_text(report):
 text=['ORIGINAL D: PARTIAL2021 SAVED RESULTS','Apr2-Dec31 2021 UTC; 274 days; 394560 minutes; separate fresh 10000-USDT accounts.','']
 for r in report['rows']:
  text.append(f"{r['cell_id']}: period return {r['period_return_fraction']}; exact NAV {r['terminal_NAV_USDT']}; all-observation MDD {r['all_observation_MDD_fraction']}; forecast-budget overshoots {r['forecast_budget_overshoot_minutes']}/394560 minute closes; fees {r['fees_USDT']}; signed funding {r['signed_funding_USDT']}; paid flat {r['actual_paid_market_flat']}.")
 text+=['','QUALIFICATIONS']+['- '+q for q in report['qualifications']]
 return '\n'.join(text)+'\n'
