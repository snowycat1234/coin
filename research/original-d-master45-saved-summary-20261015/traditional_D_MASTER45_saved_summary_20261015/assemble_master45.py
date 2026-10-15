#!/usr/bin/env python3
"""Fixed saved-only 45-cell report assembler. Standard library only; no simulator imports."""
import argparse, csv, hashlib, json, os, pathlib
from collections import Counter
from decimal import Decimal
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
PINMAP_SHA256='c5184488a059ec03efcec72b7422496c2e7dfca95474c9c99e1f797c7230d022'
YEARS=(2021,2022,2023,2024,2025)
STRATEGIES=('STATIC50','H090','VOL_MANAGED_HOLD')
TIERS=('LOW','MID','HIGH')
P21='traditional_D_partial2021_independent_review_20261015/actual_nine_saved_review'
P22='traditional_D_full2022_saved_results_independent_review_20261015'
P25='traditional_D_full2025_saved_results_independent_review_20261015'
PX='bounded_native_continuation_guard50_exit_expansion_independent_review_20261015'
OVERALL=PX+'/actual_remaining12_saved_review/OVERALL18_D_MATRIX_INDEPENDENT_REVIEW.json'
RISK='saved_distinct_family_risk_evidence_20261015/final_saved_analysis_attempt001/RISK_EVIDENCE.json'
R21='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1/summary/REPORT.json'
PUB21='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1/SOURCE_PUBLICATION_REFERENCE.json'
PUBX='bounded_native_continuation_guard50_exit_expansion_REMAINING12_FINAL18_compact_saved_results_public_recovery_20261015_v2/SOURCE_PUBLICATION_REFERENCE.json'
PASTPUB='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1/PREVIOUS_2023_2024_SAVED_RESULTS_REFERENCES.json'
DERV=HERE.name+'/SAVED_DAILY_NAV_DERIVATION.json'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def dump(p,obj):p.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
def cell_id(y,s,t):return f'{y}_{s}_{t}'+('_APR2_DEC31_D' if y==2021 else '_JAN1_DEC31_D' if y in (2022,2025) else '')
def expected_keys():return [cell_id(y,s,t)for y in YEARS for s in STRATEGIES for t in TIERS]
def period(y):return (f'{y}-04-02' if y==2021 else f'{y}-01-01',f'{y}-12-31',274 if y==2021 else 366 if y==2024 else 365)
def pointer(j,p):
    for part in p.split('/'):
        if part:j=j[int(part)] if isinstance(j,list) else j[part]
    return j

def one_index(items,cell):
    found=[i for i,v in enumerate(items) if v['cell_id']==cell]
    if len(found)!=1:raise ValueError('Missing/duplicate cell binding: '+cell)
    return found[0]

class Inputs:
    def __init__(self,freeze=False):
        self.freeze=freeze; self.files={}; self.cache={}; self.bindings={};self.inherited={}
        self.pins={} if freeze else json.loads((HERE/'INPUT_PINMAP.json').read_text())
        if not freeze and sha(HERE/'INPUT_PINMAP.json')!=PINMAP_SHA256:raise ValueError('Input pinmap binding mismatch')
    def load(self,rel):
        if rel in self.cache:return self.cache[rel]
        if pathlib.PurePosixPath(rel).is_absolute() or '..' in pathlib.PurePosixPath(rel).parts:raise ValueError('Path exclusion')
        p=ROOT/rel
        actual={'SHA256':sha(p),'bytes':p.stat().st_size}
        if not self.freeze and self.pins['files'].get(rel)!=actual:raise ValueError('Source file pin/path mismatch: '+rel)
        self.files[rel]=actual;self.cache[rel]=json.loads(p.read_text());return self.cache[rel]
    def bind(self,row,field,rel,p):
        row[field]=pointer(self.load(rel),p)
        self.bindings.setdefault(row['cell_id'],{})[field]={'source':rel,'JSON_pointer':p}
    def copy(self,row,rel,prefix,mapping):
        for field,key in mapping.items():self.bind(row,field,rel,prefix+'/'+key)
    def indexed(self,rel,key,cell):
        arr=self.load(rel)[key];i=one_index(arr,cell);return '/'+key+'/'+str(i)
    def inherit(self,cell,rel,obj):
        self.inherited[cell]={'source_review':rel,'artifact_pins_from_saved_review_not_reopened':obj}

COMMON_FIN={'terminal_NAV_USDT':'NAV','net_PnL_USDT':'net_PnL','fees_USDT':'fees_USDT','execution_cost_USDT':'execution_cost_USDT','signed_funding_USDT':'funding_USDT','gross_paid_market_turnover_USDT':'gross_fill_turnover_USDT','unpaid_liability_USDT':'unpaid_liability'}

def build_rows(inp):
    rows=[]
    deriv=inp.load(DERV); overall=inp.load(OVERALL); risk=inp.load(RISK)
    inp.load(P21+'/FINAL_INDEPENDENT_ACTUAL_PARTIAL2021_NINE_REVIEW.json')
    pub21=inp.load(PUB21); pubx=inp.load(PUBX);inp.load(PASTPUB)
    for rel,expected_sha in overall['evidence_SHA256'].items():
        if rel.endswith('_RISK_REVIEW.json') or any(name in rel for name in ('REUSED_2024_STATIC50_MID_SUPPLEMENTARY_RISK_REVIEW.json','REUSED_2024_STATIC50_MID_PRIOR_HASH_ANCHOR_INDEPENDENT_ADDENDUM.json')):
            inp.load(rel)
            if inp.files[rel]['SHA256']!=expected_sha:raise ValueError('Inherited risk provenance pin mismatch: '+rel)
    for name in ('SAVED_FAMILY_RISK_MODULE_FINAL_REVIEW.json','EXACT_SIGNATURE_ADDENDUM_REVIEW.json','SAVED_MATRIX_COMPARISON_HELPER_REVIEW.json'):
        inp.load('saved_distinct_family_risk_independent_review_20261015/'+name)
    for y in YEARS:
        for s in STRATEGIES:
            for t in TIERS:
                cell=cell_id(y,s,t);start,end,days=period(y)
                row={'cell_id':cell,'year':y,'strategy':s,'strategy_definition':{'STATIC50':'CURRENT_CS_PLUS_HOLD_BLEND','H090':'FIXED_ALTERNATE_WRAPPER_POSTHOC_REALIZED_DUPLICATE_OF_STATIC50','VOL_MANAGED_HOLD':'VOL_MANAGED_HOLD'}[s],'tier':t,'period_start_UTC':start,'period_end_inclusive_UTC':end,'period_days':days,'partial_period':y==2021,'return_annualized':False,'initial_wallet_USDT':'10000','annual_wallets_compounded':False,'nominal_annual_volatility_budget':{'LOW':'0.05','MID':'0.10','HIGH':'0.15'}[t],'nominal_budget_is_exact_realized_risk_matching':False,'duplicate_realized_path_group':f'{y}_STATIC50_H090_{t}_POST_HOC_REALIZED' if s!='VOL_MANAGED_HOLD' else '', 'duplicate_independent_confirmation':False}
                if y==2021:
                    rp=f'{P21}/{cell}_SAVED_REVIEW.json';j=inp.load(rp)
                    q=inp.indexed(R21,'descriptive_period_rows',cell)
                    inp.copy(row,R21,q,{'period_return_fraction':'period_return_fraction','gross_held_mean_minute_close':'gross_held_mean_minute_close','gross_held_max_minute_close':'gross_held_max_minute_close','realized_daily_annualized_volatility':'realized_daily_annualized_volatility','forecast_annual_volatility_max':'forecast_annual_volatility_max','forecast_budget_overshoot_minutes':'forecast_budget_overshoot_minutes','minimum_free_cash_minute_close_USDT':'minimum_free_cash_minute_close_USDT','maximum_isolated_margin_minute_close_USDT':'maximum_isolated_margin_minute_close_USDT'})
                    inp.copy(row,rp,'/summary/decimal_strings',COMMON_FIN)
                    inp.copy(row,rp,'',{'completed_minutes':'completed_minutes','source_identity':'source_identity','quality_sidecar_SHA256':'quality_sidecar_SHA256','D_warning_signals':'D_warning_actions','conditional_settlement_count':'conditional_settlements','internal_transfer_count':'transfers','owned_funding_events':'owned_funding_events','return_taxonomy':'terminal_status'})
                    inp.bind(row,'all_observation_MDD_fraction',rp,'/economics/all_observation_max_drawdown');inp.bind(row,'conditional_insurance_support_USDT',rp,'/economics/conditional_insurance_overshoot_absorption_USDT')
                    rc=f'traditional_D_partial2021_20261015/actual_nine_attempt001/{cell}/CASE_RECEIPT.json';rt=inp.load(rc);inp.inherit(cell,rp,j['evidence'])
                    row.update(source_code_identity_kind='VERIFIED_PRIOR_PUBLIC_SOURCE_COMMIT',source_code_identity=pub21['source_commit'],source_reference_status='PRIOR_SOURCE_REMOTE_BYTES_VERIFIED_IN_PINNED_RECEIPT_NO_NEW_NETWORK_CHECK',source_quality_scope='BOUND_PARTIAL2021_MODEL_SOURCE; availability/units/venue not certified',volatility_basis='REUSED_INDEPENDENTLY_REVIEWED_COMPLETE_DAILY_NAV_METRIC',forecast_covariance_phase='ORIGINAL_2021_FROZEN_REPORT_CONVENTION',forecast_sameclock_max='',forecast_sameclock_overshoot_minutes='')
                elif y in (2022,2025):
                    p=P22 if y==2022 else P25;rp=f'{p}/{cell}_REVIEW.json';j=inp.load(rp);final=p+'/FINAL_NINE_SAVED_REVIEW_RECEIPT.json';q=inp.indexed(final,'metrics',cell)
                    inp.copy(row,rp,'/exact_financials',COMMON_FIN)
                    inp.copy(row,rp,'',{'period_return_fraction':'exact_marked_net_return','completed_minutes':'completed_minutes','source_identity':'source_identity','quality_sidecar_SHA256':'quality_sidecar_SHA256','D_warning_signals':'D_warning_episode_count','owned_funding_events':'owned_funding_rows','return_taxonomy':'terminal_classification','paid_trade_legs':'paid_trade_rows','source_code_identity':'code_checkpoint_SHA256'})
                    inp.copy(row,rp,'/economics',{'conditional_settlement_count':'conditional_position_settlements','conditional_insurance_support_USDT':'conditional_insurance_overshoot_absorption_USDT'})
                    inp.copy(row,rp,'/actual_held_exposure_and_both_covariance_phase_risk/actual_gross_weight',{'gross_held_mean_minute_close':'mean','gross_held_max_minute_close':'max'})
                    inp.bind(row,'all_observation_MDD_fraction',rp,'/actual_held_exposure_and_both_covariance_phase_risk/MDD_scopes/native_all_observation/max_drawdown')
                    inp.bind(row,'minimum_free_cash_minute_close_USDT',rp,'/actual_held_exposure_and_both_covariance_phase_risk/actual_free_cash_USDT/min');inp.bind(row,'maximum_isolated_margin_minute_close_USDT',rp,'/actual_held_exposure_and_both_covariance_phase_risk/actual_isolated_margin_USDT/max')
                    for phase,fields in [('CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION',{'forecast_annual_volatility_max':'maximum','forecast_budget_overshoot_minutes':'overshoot_minutes_above_reporting_tolerance_1e10'}),('CLOSE_WITH_SAMECLOCK_DAILY_DECISION',{'forecast_sameclock_max':'maximum','forecast_sameclock_overshoot_minutes':'overshoot_minutes_above_reporting_tolerance_1e10'})]:inp.copy(row,rp,'/actual_held_exposure_and_both_covariance_phase_risk/covariance_phases/'+phase,fields)
                    donor=cell_id(y,'STATIC50' if s=='H090' else s,t);d=inp.indexed(DERV,'cells',donor);inp.bind(row,'realized_daily_annualized_volatility',DERV,d+'/realized_daily_annualized_volatility')
                    eqfinal=inp.load(final);rt=eqfinal['runtime_observations']['case_runtime'][cell];rc=final+'#/runtime_observations/case_runtime/'+cell
                    row.update(internal_transfer_count=0,source_code_identity_kind='LOCAL_REVIEW_BOUND_CODE_CHECKPOINT_SHA256',source_reference_status='LOCAL_SAVED_ONLY_NO_NEW_PUBLISHED_CLAIM',source_quality_scope='27_CAUSAL_JULY_CARRY_POINTS_UNKNOWN_HELD_VALUATION; no direct gap fills/funding across nine; counterfactual sensitivity unidentified' if y==2022 else 'GENUINE_COMPLETE_2025_EMPTY_QUALITY_SOURCE; units/actual arrival/venue uncertified',volatility_basis='SAVED_NAV_ONLY_DERIVED_FROM_PINNED_365_DAILY_ENDPOINTS'+('_INHERITED_FROM_STATIC50_EXACT_FULL_PATH_PROOF' if s=='H090' else ''),forecast_covariance_phase='CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION')
                    inp.inherit(cell,rp,j['evidence'])
                else:
                    q=inp.indexed(OVERALL,'cases',cell);c=pointer(overall,q)
                    inp.copy(row,OVERALL,q+'/exact_financials',COMMON_FIN)
                    inp.copy(row,OVERALL,q,{'completed_minutes':'completed_minutes','all_observation_MDD_fraction':'all_observation_MDD','D_warning_signals':'Guard50_paid_warning_exits','conditional_settlement_count':'conditional_settlements','conditional_insurance_support_USDT':'insurance_support','internal_transfer_count':'transfers','gross_held_mean_minute_close':'actual_held_gross_mean','gross_held_max_minute_close':'actual_held_gross_max','forecast_annual_volatility_max':'held_forecast_volatility_max','forecast_budget_overshoot_minutes':'forecast_overshoot_case_minutes','minimum_free_cash_minute_close_USDT':'minimum_minute_free_cash','maximum_isolated_margin_minute_close_USDT':'maximum_minute_isolated_margin','paid_trade_legs':'trade_rows','return_taxonomy':'terminal_classification'})
                    donor=cell_id(y,'STATIC50' if s=='H090' else s,t);dr=inp.indexed(RISK,'cells',donor);dc=pointer(risk,dr)
                    inp.bind(row,'realized_daily_annualized_volatility',RISK,dr+'/saved_float64_aggregate/daily_realized_annual_volatility')
                    if cell=='2024_STATIC50_MID':
                        rp='bounded_native_continuation_guard50_exit_independent_review_20261015/SAVED_D_INDEPENDENT_REVIEW.json';j=inp.load(rp)
                        inp.bind(row,'period_return_fraction',RISK,dr+'/native_exact_paid_annual_return_fraction');inp.bind(row,'source_identity',RISK,dr+'/authoritative_reviewed_matrix_row/bindings/original_saved_contract/scope_binding/source_identity')
                        inp.bind(row,'quality_sidecar_SHA256',RISK,dr+'/authoritative_reviewed_matrix_row/bindings/original_saved_quality/value/identity/source_sidecar_sha256')
                        rc=dc['reviewed_JSON_references_rehashed']['case_receipt']['path'];rt=inp.load(rc)
                        inp.inherit(cell,rp,{'native_result':dc['reviewed_JSON_references_rehashed']['native_result'],'MINUTE_original':dc['MINUTE_original']})
                    else:
                        section='actual_first5_saved_review' if s=='STATIC50' else 'actual_remaining12_saved_review';rp=f'{PX}/{section}/{cell}_REVIEW.json';j=inp.load(rp)
                        inp.copy(row,rp,'',{'period_return_fraction':'exact_marked_net_return','source_identity':'source_identity'})
                        inp.bind(row,'quality_sidecar_SHA256',RISK,dr+'/authoritative_reviewed_matrix_row/bindings/original_saved_quality/value/identity/source_sidecar_sha256')
                        rt=j['runtime'];rc=rp+'#/runtime';inp.inherit(cell,rp,j['evidence_pins'])
                    row.update(owned_funding_events='NOT_REPORTED_IN_REUSED_SUMMARY',source_code_identity_kind='VERIFIED_PRIOR_PUBLIC_SOURCE_COMMIT',source_code_identity=pubx['source_commit'],source_reference_status='PRIOR_SOURCE_REMOTE_BYTES_VERIFIED_IN_PINNED_RECEIPT_NO_NEW_NETWORK_CHECK',source_quality_scope='BOUND_2024_CAUSAL_CARRY_UNKNOWN_MARK_QUALITY; not certified true-market risk' if y==2024 else 'BOUND_ORIGINAL_2023_MODEL_SOURCE; units/actual arrival/venue uncertified',volatility_basis='REUSED_INDEPENDENTLY_REVIEWED_COMPLETE_DAILY_NAV_METRIC'+('_INHERITED_FROM_STATIC50_EXACT_FULL_PATH_PROOF' if s=='H090' else ''),forecast_covariance_phase='ORIGINAL_2023_2024_FROZEN_REPORT_CONVENTION',forecast_sameclock_max='',forecast_sameclock_overshoot_minutes='')
                if y==2021:
                    inp.bind(row,'paid_trade_legs',rp,'/summary/trade_legs')
                    if pointer(inp.cache[R21],q+'/review_sha256')!=inp.files[rp]['SHA256']:raise ValueError('2021 report/review binding mismatch')
                elif y in (2022,2025):
                    if inp.cache[final]['review_evidence'][pathlib.Path(rp).name]['SHA256']!=inp.files[rp]['SHA256']:raise ValueError('Final/case review binding mismatch')
                else:
                    if c.get('cell_review_SHA256',dc['reviewed_JSON_references_rehashed']['finance_review']['SHA256'])!=inp.files[rp]['SHA256']:raise ValueError('Overall/case review binding mismatch')
                    if 'exact_financials' in j and any(c['exact_financials'][k]!=j['exact_financials'][k] for k in c['exact_financials']):raise ValueError('Overall/case exact financial mismatch')
                row.update(runtime_wall_seconds=rt.get('total_wall_seconds',rt.get('wall_seconds','NOT_REPORTED')),runtime_CPU_seconds=rt.get('CPU_seconds','NOT_REPORTED'),runtime_peak_RSS_bytes=rt.get('max_RSS_bytes','NOT_REPORTED'),runtime_source=rc,review_source=rp,review_SHA256=inp.files[rp]['SHA256'])
                row['primary_financial_values_are_exact_source_decimal_strings']=True
                if y in (2021,2023,2024):
                    inp.bind(row,'source_code_identity',PUB21 if y==2021 else PUBX,'/source_commit')
                if y==2021:
                    runtime_file=rc;runtime_prefix=''
                elif y in (2022,2025):
                    runtime_file=final;runtime_prefix='/runtime_observations/case_runtime/'+cell
                elif cell=='2024_STATIC50_MID':
                    runtime_file=rc;runtime_prefix=''
                else:
                    runtime_file=rp;runtime_prefix='/runtime'
                for output,key in [('runtime_wall_seconds','total_wall_seconds'),('runtime_CPU_seconds','CPU_seconds'),('runtime_peak_RSS_bytes','max_RSS_bytes')]:
                    inp.bind(row,output,runtime_file,runtime_prefix+'/'+key)
                inp.bindings.setdefault(cell,{})['runtime_metrics']={'source':rc,'fields':['total_wall_seconds','CPU_seconds','max_RSS_bytes'],'scope':'original financial-case runtime, not assembler or reviewer runtime'}
                for k in row:
                    inp.bindings.setdefault(cell,{}).setdefault(k,{'derivation':'FIXED_SCOPE_OR_EXPLICIT_SOURCE_QUALIFICATION_IN_ASSEMBLER','not_a_financial_resimulation':True})
                rows.append(row)
    verify_duplicates(inp,rows)
    exits=[('traditional_D_partial2021_20261015/actual_nine_attempt001/ROOT_OBSERVED_EXIT.json','exit_code'),('traditional_D_full2022_20261015_v2_financial_attempt001/ROOT_OBSERVED_EXIT.json','exit_code'),('traditional_D_full2025_saved_results_independent_review_20261015/ROOT_EXIT_BINDING_COMPANION.json','actual_exit_code_reported_by_root')]
    for path,key in exits:
        if inp.load(path)[key]!=0:raise ValueError('Root exit not zero')
    validate_rows(rows)
    return rows


def verify_duplicates(inp,rows):
    eq21=inp.load(P21+'/STATIC50_H090_POST_HOC_SAVED_EQUALITY.json')['pairs']
    eq22=inp.load(P22+'/FINAL_NINE_SAVED_REVIEW_RECEIPT.json')['H090_STATIC50_same_tier_actual_paths']
    eq25=inp.load(P25+'/H090_STATIC50_THREE_TIER_PATH_COMPARISON.json')['rows']
    eqx=inp.load(OVERALL)['exact_H090_STATIC50_realized_equivalence_groups']
    for y in YEARS:
        for t in TIERS:
            h=cell_id(y,'H090',t);st=cell_id(y,'STATIC50',t)
            items=eq21 if y==2021 else eq22 if y==2022 else eq25 if y==2025 else eqx
            match=[v for v in items if v.get('H090_cell',v.get('cell_id'))==h]
            if len(match)!=1:raise ValueError('Missing duplicate proof '+h)
            v=match[0]
            if y==2021:ok=v['decompressed_minute_values_byte_exact'] and v['both_separately_executed'] and v['STATIC50_cell']==st
            elif y in (2022,2025):ok=v['all_saved_minute_fields_bit_equal'] and v['actual_quantity_paths_equal'] and v['differing_minute_rows']==0 and v['STATIC50_cell']==st
            else:
                proof_path=f'{PX}/actual_remaining12_saved_review/{h}_STATIC50_REALIZED_EQUIVALENCE.json'
                proof=inp.load(proof_path)
                ok=(inp.files[proof_path]['SHA256']==v['proof_SHA256'] and proof['cell_id']==h and proof['saved_D_STATIC_case']==('bounded_native_continuation_guard50_exit_20261015/actual_2024_D_attempt001/GUARD50_EXIT_ONLY' if st=='2024_STATIC50_MID' else ('bounded_native_continuation_guard50_exit_expansion_20261015/actual_first5_attempt001/'+st)) and pathlib.Path(proof['saved_D_H090_case']).name==h and proof['full37column_minute_matrix_byte_identical'] and all(proof['same_financial_fields'].values()) and proof['minute_matrix_raw_SHA256']==v['minute_values_raw_C_SHA256'] and bool(v['canonical_financial_projection_SHA256']) and v['minute_values_shape'][0]==period(y)[2]*1440)
            if not ok:raise ValueError('Invalid exact duplicate proof '+h)
            a=next(r for r in rows if r['cell_id']==h);b=next(r for r in rows if r['cell_id']==st)
            for key in ('terminal_NAV_USDT','period_return_fraction','fees_USDT','execution_cost_USDT','signed_funding_USDT','gross_paid_market_turnover_USDT','all_observation_MDD_fraction','realized_daily_annualized_volatility'):
                if a[key]!=b[key]:raise ValueError('Duplicate bound financial metric differs: '+h+' '+key)

def validate_rows(rows):
    if len(rows)!=45 or [r['cell_id'] for r in rows]!=expected_keys():raise ValueError('Exactly 45 unique fixed ordered cells required')
    if len({r['cell_id']for r in rows})!=45:raise ValueError('Duplicate cell')
    for r in rows:
        y,s,t=r['year'],r['strategy'],r['tier'];start,end,days=period(y)
        if r['cell_id']!=cell_id(y,s,t) or (r['period_start_UTC'],r['period_end_inclusive_UTC'],r['period_days'])!=(start,end,days):raise ValueError('Period/tier identity binding')
        if r['completed_minutes']!=days*1440 or r['partial_period']!=(y==2021) or r['return_annualized'] or r['annual_wallets_compounded']:raise ValueError('Calendar/wallet scope')
        for key in COMMON_FIN:
            if not isinstance(r[key],str):raise ValueError('Primary financial string lost: '+key)
        if not isinstance(r['period_return_fraction'],str):raise ValueError('Exact return string lost')
        if r['return_taxonomy']!='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT':raise ValueError('Paid status missing')
        if r['conditional_settlement_count']!=0 or Decimal(r['conditional_insurance_support_USDT'])!=0 or Decimal(r['unpaid_liability_USDT'])!=0 or r['internal_transfer_count']!=0:raise ValueError('Zero settlement/support/debt/transfer invariant')
        if not (0<=r['realized_daily_annualized_volatility']<10):raise ValueError('Missing/invalid volatility')
    counts=Counter(r['duplicate_realized_path_group']for r in rows if r['duplicate_realized_path_group'])
    if len(counts)!=15 or set(counts.values())!={2}:raise ValueError('Exactly15 two-claim duplicate groups required')
    if len({Decimal(r['terminal_NAV_USDT']) for r in rows})!=30:raise ValueError('Exactly30 distinct native terminal NAVs required as sufficient distinct-path evidence')

def validate_candidate(candidate,reference):
    validate_rows(candidate)
    if candidate!=reference:raise ValueError('Candidate metric/source binding differs from deterministic reassembly')


def markdown(rows):
    lines=['# Original D MASTER45: saved-only descriptive summary','','**2021 is April 2–December 31 only: 274 days. Its period return is never annualized.** The other four periods are full calendar years (2024:366 days; others:365). Each of the45 separately approved/executed claims uses a fresh10000-USDT wallet. No annual-return product, CAGR or synthetic continuous wallet is calculated.','','45 actual claims are retained. There are15 post-hoc same-period/same-tier H090↔STATIC50 duplicate groups and30 distinct realized paths: two realized families × three tiers × five periods. These are not30 strategies, independent confirmations or OOS validations. No aliases, pruning or execution-reuse authority is created.','','## Definitions and interpretation','','- Current STATIC50 means the CS+HOLD blend. H090 is the fixed alternate wrapper that realizes the same15 financial/minute paths here. VOL_MANAGED_HOLD is the other realized family. Legacy pureCS/CS+SMA name collisions and the planned unexecuted CSMOM21_COMMON_TIER15 are excluded.','- All periods are adaptive seen-development evidence. 2023/24 returns are positive and2022/25 returns are negative across the nine cells. This does not establish cross-cycle profitability, alpha or investable risk-matched excess returns.','- Nominal5%/10%/15% volatility budgets are not equal realized risk. Held forecast maxima and overshoot minutes are preserved below/inCSV. They are distinct from realized daily volatility. Admission limits need not hold continuously as marks drift.','- Daily descriptive volatility: sample std(ddof=1) of complete UTC daily endpoint NAV simple returns, including initial10000 as the first denominator, multiplied by sqrt365 for every period (also partial2021 and leap2024). The return itself is never annualized. Saved float64 NAV telemetry is not the exact native40 ledger.','- 2021 and2023/24 volatility reuse already independent-reviewed saved metrics. 2022/25 volatility is derived only from12 hash-pinned saved MINUTE arrays,365 saved daily endpoints per donor; H090 inherits its same-tier STATIC50 metric solely through the exact full-path proof. SAVED_DAILY_NAV_DERIVATION.json and derive_saved_daily_nav.py contain exact arrays, hashes and reproducible arithmetic.','- Primary financial columns inMASTER45.csv preserve source decimal strings exactly. Human percentage displays below are separately rounded for readability; they are not replacements for the primary values. Native all-observation MDD covers initial NAV, minute marks and scheduler fill/funding observations; it does not certify an intraminute high/low path.','- Executioncost is execution-price friction, separate from fees. Signed funding is positive for receipts, negative for payments. Net results already include these effects; do not subtract fees/executioncost/funding again. Same-quantity accounting bridges are not counterfactual strategies.','- OriginalD uses conditional collateral-forfeiture settlement assumptions; zero modeled settlements/support/debt here is not actual-venue no-liquidation certification. Native venue filters, actual fills/liquidity, funding publication/units, insurance/ADL and historical arrival/installation remain uncertified.','','## Source-quality and reporting scope','','-2022 retains27 causal July carry points (8 asset runs,11 distinct open clocks, longest7 minutes), with UNKNOWN held valuation. Across nine cells the saved audits show no direct same-gap paid fills or owned funding. That does not show negligible counterfactual cashflow, quantity or terminal-return impact.243 held asset-minute-case cells remain exposed to the qualification.','-2025 binds the genuine complete2025 source with an empty quality source. Its cold start preserves5475 raw source funding events and5470 native account events; five initial unowned events at+15ms cause no pre-owned funding charge. It does not inherit2022 carry provenance. Funding units and historical actual arrival/installation remain uncertified.','-2024 retains its original bound causal carry/unknown mark-quality sidecar.2021 coverage is shorter; source identities, runtime cost and risk-report conventions differ across periods.','-2022/25 report both before-same-clock and including-same-clock covariance conventions. Primary forecast columns use CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION.2021 and2023/24 keep their original frozen-report conventions without claiming identical midnight treatment.','- Original execution runtime is kept per cell. The reused 2024 STATIC50 MID runtime is taken from its exact saved original case receipt. Reporting/assembler runtime is not financial-case runtime.','- Source references reuse pinned prior publication receipts without any new network verification.2022/25 use local review-bound code checkpoint SHA identities; no new publication claim is made. Root exit evidence for2021/22 and2025 companion is pinned.','','## Human-rounded result display','','Return and MDD/volatility are percentages; maxgross is NAV-relative. Exact native financial values and full provenance are inMASTER45.csv andINPUT_PINMAP.json.','', '| Period | Core | Tier | Return% | NativeMDD% | Dailyvol% | Maxgross | Forecastmax% | Overshootmin | Guard50warnings |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        label='2021 Apr2–Dec31 (274d PARTIAL)' if r['year']==2021 else str(r['year'])
        vals=[label,r['strategy'],r['tier'],f"{Decimal(r['period_return_fraction'])*100:.4f}",f"{r['all_observation_MDD_fraction']*100:.4f}",f"{r['realized_daily_annualized_volatility']*100:.4f}",f"{r['gross_held_max_minute_close']:.6f}",f"{r['forecast_annual_volatility_max']*100:.4f}",str(r['forecast_budget_overshoot_minutes']),str(r['D_warning_signals'])]
        lines.append('| '+' | '.join(vals)+' |')
    lines+=['','## Reproduction','','Run taskset-c0 python assemble_master45.py from this folder (with spaces: taskset -c 0 python assemble_master45.py). It verifies the fixed input pinmap and every directly used saved JSON hash, validates45 exact ordered identities and15 duplicate groups, then writes deterministic CSV/MD plus field-level bindings. It never opens accounts, providers, targets or raw sources. Optional deeper saved-array rederivation: taskset -c 0 python derive_saved_daily_nav.py --rederive-from-pinned-saved-arrays. This reads only the12 pinned saved arrays, onecase at a time with a temporary mmap and numerical pools1.','','Focused positive/negative binding tests are in test_master45.py andfixtures/NEGATIVE_BINDING_CASES.json. No financial replay, new GO, claim, tuning, network or publication is performed.','']
    text='\n'.join(lines)
    replacements={'2024:366':'2024: 366','others:365':'others: 365','the45':'the 45','fresh10000':'fresh 10,000','are15':'are 15','and30':'and 30','not30':'not 30','same15':'same 15','pureCS':'pure CS','and2022':'and 2022','Nominal5':'Nominal 5','below/inCSV':'below and in the CSV','initial10000':'initial 10,000','sqrt365':'sqrt(365)','partial2021':'partial 2021','leap2024':'leap 2024','and2023':'and 2023','from12':'from 12','arrays,365':'arrays, 365','inMASTER45':'in MASTER45','Executioncost':'Execution cost','executioncost':'execution cost','OriginalD':'Original D','-2022':'- 2022','-2024':'- 2024','-2025':'- 2025','preserves5475':'preserves 5475','and5470':'and 5470','at+15ms':'at +15 ms','retains27':'retains 27','runs,11':'runs, 11','longest7':'longest 7','impact.243':'impact. 243','complete2025':'complete 2025','inherit2022':'inherit 2022','sidecar.2021':'sidecar. 2021','DECISION.2021':'DECISION. 2021','verification.2022':'verification. 2022','for2021':'for 2021','and2025':'and 2025','maxgross':'max gross','andINPUT':'and INPUT','NativeMDD':'Native MDD','Dailyvol':'Daily vol','Maxgross':'Max gross','Forecastmax':'Forecast max','Overshootmin':'Overshoot min','Guard50warnings':'Guard50 warnings','Apr2–Dec31':'Apr 2–Dec 31','(274d':'(274 d','Run taskset-c0 python assemble_master45.py from this folder (with spaces: taskset -c 0 python assemble_master45.py).':'Run taskset -c 0 python assemble_master45.py from this folder.','validates45':'validates 45','and15':'and 15','only the12':'only the 12','onecase':'one case','pools1':'pools 1','andfixtures/':'and fixtures/','unexecuted CSMOM21_COMMON_TIER15':'unexecuted 15-cell CSMOM21_COMMON_TIER baseline'}
    for old,new in replacements.items():text=text.replace(old,new)
    return text

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-inputs',action='store_true');args=p.parse_args();os.sched_setaffinity(0,{0})
    inp=Inputs(args.freeze_inputs);rows=build_rows(inp)
    if args.freeze_inputs:
        pinmap={'schema':'ORIGINAL_D_MASTER45_FIXED_SAVED_INPUT_PINMAP_V1','scope':{'cells':expected_keys(),'actual_claims':45,'posthoc_duplicate_groups':15,'distinct_realized_paths':30,'financial_replay':False,'new_network':False,'all45_claims_retained':True,'partial2021_days':274},'files':inp.files,'field_bindings':inp.bindings,'inherited_terminal_artifact_pins':inp.inherited,'saved_daily_original_arrays':[{k:v for k,v in c.items()if k in ('cell_id','original_MINUTE','bound_review','daily_endpoints_raw_C_order_SHA256','daily_returns_raw_C_order_SHA256','nav_column_raw_C_order_SHA256')}for c in inp.cache[DERV]['cells']]}
        dump(HERE/'INPUT_PINMAP.json',pinmap);print('PINMAP',sha(HERE/'INPUT_PINMAP.json'));return
    if inp.files!=inp.pins['files'] or inp.bindings!=inp.pins['field_bindings'] or inp.inherited!=inp.pins['inherited_terminal_artifact_pins']:raise ValueError('Source coverage/field binding drift')
    with open(HERE/'MASTER45.csv','w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (HERE/'MASTER45.md').write_text(markdown(rows));dump(HERE/'MASTER45_ROWS.json',rows)
    out={'schema':'MASTER45_ASSEMBLER_RECEIPT_V1','status':'COMPLETE_SAVED_ONLY_AWAITING_INDEPENDENT_REVIEW','actual_claims':45,'posthoc_duplicate_groups':15,'distinct_realized_paths':30,'financial_reruns':0,'source_provider_target_reads':0,'new_accounts_GO_claims_network_publication':0,'CPU_affinity':sorted(os.sched_getaffinity(0)),'input_pinmap_SHA256':sha(HERE/'INPUT_PINMAP.json'),'assembler_SHA256':sha(pathlib.Path(__file__)),'outputs':{p.name:{'SHA256':sha(p),'bytes':p.stat().st_size}for p in (HERE/'MASTER45.csv',HERE/'MASTER45.md',HERE/'MASTER45_ROWS.json')}}
    dump(HERE/'ASSEMBLER_RECEIPT.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
