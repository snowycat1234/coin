#!/usr/bin/env python3
"""Pure saved-evidence reporting. No account, source-prep or provider imports.

The real matrix is deliberately not read on import. Final CLI execution requires a
parent-supplied authorization/index declaring all 17 new jobs terminal. It reads
only explicitly pinned saved JSON. MINUTE.npz is never opened by this tool.
"""
from __future__ import annotations
import argparse
import copy
import csv
from decimal import Decimal, localcontext
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = 'SAVED_FIXED_D_DEV_MATRIX_COMPARISON_V1'
EXPECTED_MANIFEST_SHA256 = '0c08a0c362c8222d2dc16735f7ebf11a26f4892999bc57b3b062d189ff050638'
REUSED_RECEIPT_SHA256 = 'b23e84937ec85275187b14785ec815e5f50e7bb0b7e81ba2cce99f9fa91b8dc5'
FINANCIAL_PROJECTION_FIELDS = ('free_cash','unpaid_liability','positions','marks','totals',
                               'trades','funding','funding_events','funding_ids')
QUALIFICATIONS = [
 'All 2023 and 2024 results are adaptive seen-development evidence, not independent out-of-sample validation.',
 'Candidates, nominal tiers, years, BASE27 costs and fixed D policy were frozen before these new outcomes; no performance-based winner selection, rescaling or grid search is performed.',
 'Each cell starts a separate fresh 10000-USDT annual account. Annual returns are not multiplied and no continuous two-year CAGR is computed.',
 'Equal nominal tiers are not exact matched realized risk. Actual held exposures, realized daily volatility and forecast overshoots are reported without post-hoc risk matching.',
 'All-observation MDD covers initial NAV, observed minute-close marks and scheduler fills/funding. It does not establish an intraminute bar-high/low price path.',
 'Held-risk statistics are post-transition minute-close observations unless a field explicitly says all-observation. Admission cash/margin/gross/asset rules are not continuous marked-state guarantees.',
 'Fees, execution friction, signed funding, internal transfers, conditional settlements, debt and support are separate quantities. Funding sign is retained as recorded.',
 'Exact realized-path duplicates are duplicate performance evidence, even when independently approved one-time jobs have different targets or rejected requests.',
 'Native venue filters, risk tiers, liquidation/insurance/ADL, fills, latency and funding publication remain uncertified model assumptions.',
 'Partial or halted prefixes are not annual return comparators. Conditional model-settled returns are not paid-market liquidation returns.',
 'Saved hashes and reviews do not authorize new historical runs, source reads, strategy changes, trades or publication.'
]

class EvidenceError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                      ensure_ascii=True).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def bound_json(base: Path, ref: dict) -> tuple[Any, dict]:
    if set(ref) != {'path', 'SHA256'}:
        raise EvidenceError('A saved JSON reference requires exactly path and SHA256.')
    p = Path(ref['path'])
    if p.is_absolute() or '..' in p.parts or p.suffix != '.json':
        raise EvidenceError('Only explicit relative saved JSON references are allowed.')
    p = (base / p).resolve()
    if not p.is_relative_to(base.resolve()):
        raise EvidenceError('Saved JSON reference escapes workspace.')
    actual = file_sha256(p)
    if actual != ref['SHA256']:
        raise EvidenceError(f'Saved evidence SHA256 mismatch: {ref["path"]}')
    with p.open() as f:
        value = json.load(f, parse_constant=lambda s: (_ for _ in ()).throw(EvidenceError(s)))
    return value, dict(ref)


def decimal_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise EvidenceError('Boolean is not a financial amount.')
    d = Decimal(str(value))
    if not d.is_finite():
        raise EvidenceError('Financial amount must be finite.')
    return str(value)


def zero(value: Any) -> bool:
    return value is not None and Decimal(str(value)) == 0


def exact_return(nav: Any) -> str:
    with localcontext() as ctx:
        ctx.prec = 100
        return str(Decimal(str(nav)) / Decimal('10000') - Decimal(1))


def classify_return(*, reviewed: bool, terminal: bool, completed_minutes: int | None,
                    required_minutes: int, nav: Any, actual_paid_market_flat: bool | None,
                    conditional_settled_flat: bool | None, settlement_count: int | None,
                    unpaid_liability: Any, terminal_classification: str | None = None) -> dict:
    """Never turn missing/pending/partial evidence into a comparable annual zero."""
    out = {'return_taxonomy': 'PENDING_UNREVIEWED', 'annual_return_fraction': None,
           'comparable_paid_annual_return_fraction': None,
           'conditional_model_annual_return_fraction': None,
           'partial_prefix_marked_return_fraction': None}
    if not reviewed or not terminal:
        return out
    if nav is None or completed_minutes is None:
        out['return_taxonomy'] = 'TERMINAL_INCOMPLETE_EVIDENCE'
        return out
    if completed_minutes < 0 or completed_minutes > required_minutes:
        raise EvidenceError('Completed minutes outside frozen calendar.')
    full = completed_minutes == required_minutes
    ret = exact_return(nav)
    if not full:
        out.update(return_taxonomy='PARTIAL_HALTED_PREFIX_NOT_ANNUAL',
                   partial_prefix_marked_return_fraction=ret)
    elif (terminal_classification == 'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT'
          and actual_paid_market_flat is True and settlement_count == 0
          and zero(unpaid_liability) and conditional_settled_flat is not True):
        out.update(return_taxonomy='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT',
                   annual_return_fraction=ret, comparable_paid_annual_return_fraction=ret)
    elif terminal_classification in ('FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT','FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT') and conditional_settled_flat is True and settlement_count is not None and settlement_count > 0:
        out.update(return_taxonomy='FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT',
                   annual_return_fraction=ret, conditional_model_annual_return_fraction=ret)
    else:
        out['return_taxonomy'] = 'FULL_CALENDAR_UNRESOLVED_NOT_ANNUAL_COMPARATOR'
    return out


def validate_finite_numbers(value: Any, path: str = 'risk') -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise EvidenceError('Nonfinite saved numeric value: '+path)
    if isinstance(value, dict):
        for key, child in value.items(): validate_finite_numbers(child,path+'.'+str(key))
    elif isinstance(value, list):
        for i, child in enumerate(value): validate_finite_numbers(child,path+'.'+str(i))


def validate_terminal_status(receipt: dict, finance: dict, cell: dict) -> None:
    status=receipt.get('status','')
    completed=receipt.get('completed_minutes')
    required=cell['required_minutes']
    if not isinstance(completed,int) or isinstance(completed,bool) or not 0<=completed<=required:
        raise EvidenceError('Invalid terminal completed minute count.')
    if not status.startswith(('FULL_CALENDAR_','PARTIAL_','HALTED_')) or 'PENDING' in status or 'RUNNING' in status:
        raise EvidenceError('Unrecognized or nonterminal saved classification.')
    if status.startswith('FULL_CALENDAR_') != (completed==required):
        raise EvidenceError('Terminal classification contradicts completed calendar.')
    paid=finance.get('actual_paid_market_flat',finance.get('paid_flat'))
    conditional=finance.get('conditional_settled_flat')
    settlements=finance.get('conditional_settlement_rows',finance.get('settlements'))
    debt=(finance.get('exact_financials') or finance).get('unpaid_liability')
    if status=='FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT':
        if conditional is True or settlements!=0 or not zero(debt):
            raise EvidenceError('Paid terminal classification contradicts settlement/flat/debt flags.')
    elif completed==required and paid is True:
        raise EvidenceError('Paid annual flags contradict terminal classification.')
    if status in ('FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT','FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT'):
        if conditional is not True or paid is True or not isinstance(settlements,int) or settlements<=0:
            raise EvidenceError('Conditional terminal classification contradicts saved flags.')


def financial_projection_signature(audit: dict) -> str:
    """Strict existing reviewer projection. No trade/funding IDs are omitted.

    Scope/config/candidate wrapper metadata and fill_requests are outside this
    projection. Requests may differ while executions coincide. Policy journals
    are separately compared and bound in the saved duplicate proof.
    """
    missing = [k for k in FINANCIAL_PROJECTION_FIELDS if k not in audit]
    if missing:
        raise EvidenceError(f'Missing exact native financial fields: {missing}')
    return digest({k: audit[k] for k in FINANCIAL_PROJECTION_FIELDS})


def native_array_signature(arrays: list[tuple[str, Any]]) -> dict:
    """Small-fixture utility, not a real-matrix NPZ reader.

    Arrays are supplied in their original archive key order. Include both values
    and columns, dtype, shape and exact C-order bytes; no rounding/tolerance.
    Actual final reporting reuses independent saved proofs rather than invoking
    this function on historical arrays.
    """
    descriptors = []
    for key, array in arrays:
        if array.dtype.hasobject:
            raise EvidenceError('Object arrays cannot form a stable raw-byte signature.')
        descriptors.append({'key': key, 'dtype': array.dtype.str,
                            'shape': list(array.shape),
                            'raw_C_order_SHA256': hashlib.sha256(array.tobytes(order='C')).hexdigest()})
    if set(x['key'] for x in descriptors) != {'values','columns'} or len(descriptors) != 2:
        raise EvidenceError('Signature requires values and columns exactly once.')
    return {'schema': 'EXACT_OUTPUT_MINUTE_VALUES_AND_COLUMNS_V1',
            'arrays_in_original_key_order': descriptors,
            'canonical_descriptor_SHA256': digest(descriptors)}


def validate_duplicate_proof(proof: dict, left_id: str, right_id: str,
                             left_pins: dict, right_pins: dict) -> bool:
    """Classify only complete exact saved proofs, never matching terminal stats."""
    if proof.get('status') != 'PASS_EXACT_SAME_REALIZED_FINANCIAL_PATH':
        return False
    if proof.get('full37column_minute_matrix_byte_identical') is not True:
        return False
    same = proof.get('same_financial_fields', {})
    if set(same) != set(FINANCIAL_PROJECTION_FIELDS) or not all(v is True for v in same.values()):
        return False
    journals = proof.get('policy_journals_exact', {})
    if set(journals) != {'monitor_journal','settlement_journal','transfer_journal'} or not all(journals.values()):
        return False
    if proof.get('cell_id') not in (left_id, right_id):
        return False
    proof_pins = proof.get('source_file_pins', {})
    for pins in (left_pins, right_pins):
        for file in ('CASE_RECEIPT.json','ACCOUNT_FINANCIAL_AUDIT.json','MINUTE.npz'):
            matching = [sha for path, sha in proof_pins.items()
                        if path.endswith('/' + file) and sha == pins.get(file)]
            if not matching:
                return False
    return True


METRIC_KEYS = (
 'terminal_NAV_USDT','fees_USDT','execution_cost_USDT','signed_funding_USDT',
 'gross_paid_market_turnover_USDT','paid_trade_legs','D_warning_signals',
 'internal_transfer_count','internal_transfer_USDT','conditional_settlement_count',
 'conditional_NAV_adjustment_USDT','conditional_collateral_forfeited_USDT',
 'conditional_positive_residual_forfeited_USDT','unpaid_liability_USDT',
 'conditional_insurance_support_USDT','all_observation_MDD_fraction',
 'minute_close_MDD_fraction','complete_daily_close_MDD_fraction',
 'minimum_free_cash_minute_close_USDT','maximum_isolated_margin_minute_close_USDT',
 'minimum_free_cash_all_observations_USDT','gross_held_mean_minute_close',
 'gross_held_max_minute_close','gross_held_max_all_observations',
 'absolute_asset_weight_max_minute_close','absolute_asset_weight_max_by_symbol_minute_close',
 'absolute_asset_weight_mean_by_symbol_minute_close','signed_asset_weight_min_by_symbol_minute_close',
 'signed_asset_weight_max_by_symbol_minute_close','realized_daily_annualized_volatility',
 'nominal_annual_volatility_budget','forecast_annual_volatility_mean',
 'forecast_annual_volatility_max','forecast_max_absolute_budget_overshoot',
 'forecast_max_relative_budget_overshoot','forecast_budget_overshoot_minutes',
 'observed_minute_cash_floor_breach_minutes','observed_minute_margin_ceiling_breach_minutes',
 'observed_minute_gross_cap_breach_minutes','observed_minute_asset_cap_breach_minutes')


def pending_row(cell: dict) -> dict:
    row = {k: cell[k] for k in ('cell_id','year','strategy','tier','config','required_minutes')}
    row.update(evidence_status='PENDING_NOT_READ_OR_APPROVED', completed_minutes=None,
               initial_wallet_USDT='10000', adaptive_DEV_only=True,
               reused_prior_completed_case=cell.get('reused',False),
               duplicate_realized_path_group=None, duplicate_realized_path_evidence=None,
               exact_signature=None, bindings=None)
    row.update({k: None for k in METRIC_KEYS})
    row.update(classify_return(reviewed=False,terminal=False,completed_minutes=None,
                              required_minutes=cell['required_minutes'],nav=None,
                              actual_paid_market_flat=None,conditional_settled_flat=None,
                              settlement_count=None,unpaid_liability=None))
    return row


def expected_cells(manifest: dict) -> list[dict]:
    cells = copy.deepcopy(manifest['cells'])
    reused = manifest['reused_excluded_completed_cell']
    cells.append({'cell_id': reused['cell_id'], 'year': 2024, 'strategy':'STATIC50',
                  'tier':'MID','config':'STATIC50_MID','required_minutes':527040,
                  'calendar':[1704067200000000,1735689600000000],
                  'source_identity':'3794f1d1502740816bb1ac31096e60a4720d1b7a19d588150fd469ef1515966b',
                  'reused':True})
    want = {(y,s,t) for y in (2023,2024) for s in ('STATIC50','H090','VOL_MANAGED_HOLD')
            for t in ('LOW','MID','HIGH')}
    got = {(c['year'],c['strategy'],c['tier']) for c in cells}
    if len(cells) != 18 or got != want or len({c['cell_id'] for c in cells}) != 18:
        raise EvidenceError('Frozen cohort must be precisely 18 unique fixed cells.')
    return sorted(cells,key=lambda c:(c['year'],('STATIC50','H090','VOL_MANAGED_HOLD').index(c['strategy']),('LOW','MID','HIGH').index(c['tier'])))


def normalize_reviewed_row(cell: dict, receipt: dict, finance: dict, risk: dict,
                           risk_review: dict, pins: dict, refs: dict,
                           extra: dict | None = None) -> dict:
    """Project saved approved reports only. Missing fields stay null, never zero."""
    extra = extra or {}
    validate_finite_numbers(extra)
    validate_finite_numbers(risk)
    validate_finite_numbers(risk_review)
    validate_finite_numbers(finance)
    validate_terminal_status(receipt,finance,cell)
    row = pending_row(cell)
    reused = cell.get('reused',False)
    if not finance.get('status','').startswith('PASS_') or not risk_review.get('status','').startswith('PASS_'):
        raise EvidenceError(f'Finance/risk review not PASS for {cell["cell_id"]}')
    if not reused:
        for key in ('cell_id','config','year','tier','calendar','source_identity','required_minutes'):
            if receipt.get(key) != cell.get(key) or finance.get(key) != cell.get(key):
                raise EvidenceError(f'Case/manifest/review mismatch for {cell["cell_id"]}: {key}')
        if receipt.get('manifest_SHA256') != EXPECTED_MANIFEST_SHA256:
            raise EvidenceError('Expansion receipt not bound to frozen 17-cell manifest.')
        if finance.get('native40_every_event_exact') is not True or finance.get('source_code_policy_scope_exact') is not True:
            raise EvidenceError('Missing exact native40/code/policy approval.')
        if finance.get('all_checkpoint_files_rehashed') is not True:
            raise EvidenceError('Independent terminal checkpoint rehash evidence missing.')
        if finance.get('evidence_pins') != pins:
            raise EvidenceError('Finance review pins must be carried forward unchanged.')
    else:
        if pins.get('CASE_RECEIPT.json') != REUSED_RECEIPT_SHA256:
            raise EvidenceError('Reused MID must retain its exact original receipt.')
        if finance.get('case_receipt_SHA256') != REUSED_RECEIPT_SHA256:
            raise EvidenceError('Reused finance review has another receipt.')
        if finance.get('source_GO_review_code_pins_verified') is not True:
            raise EvidenceError('Original reused source/GO/code bindings unverified.')
    if reused:
        ev=risk_review.get('evidence_SHA256',{})
        if ev.get(refs['risk_report']['path']) != refs['risk_report']['SHA256']:
            raise EvidenceError('Supplementary risk review does not pin report.')
        minute_path=str(Path(refs['case_receipt']['path']).parent/'MINUTE.npz')
        if ev.get(minute_path) != pins.get('MINUTE.npz'):
            raise EvidenceError('Supplementary review minute archive pin mismatch.')
        if risk_review.get('original_code_policy_quality_source_preparation_GO_bindings_preserved') is not True:
            raise EvidenceError('Original reused bindings not independently approved.')
        transport_ref=refs.get('transported_risk_review',{})
        if ev.get(transport_ref.get('path')) != transport_ref.get('SHA256'):
            raise EvidenceError('Supplementary review does not bind transported risk review.')
    if risk_review.get('cell_id') != cell['cell_id']:
        raise EvidenceError('Risk review belongs to another cell.')
    if reused:
        for key in ('config','calendar','source_identity','required_minutes'):
            if receipt.get(key) != cell.get(key):
                raise EvidenceError('Reused original receipt scope mismatch: '+key)
    if extra and extra.get('original_native_result',{}).get('SHA256') != pins.get('NATIVE_RESULT.json'):
        raise EvidenceError('Supplementary summary not bound to reviewed native result.')
    if receipt.get('status') != finance.get('terminal_classification'):
        raise EvidenceError('Terminal receipt/review classification mismatch.')
    if receipt.get('completed_minutes') != finance.get('completed_minutes'):
        raise EvidenceError('Completed minute mismatch.')
    if not reused and risk_review.get('terminal_status') != receipt.get('status'):
        raise EvidenceError('Risk review terminal mismatch.')
    if refs['case_receipt']['SHA256'] != pins.get('CASE_RECEIPT.json'):
        raise EvidenceError('Receipt reference not the reviewer-approved receipt.')
    if not reused and refs['risk_report']['SHA256'] != pins.get('ACTUAL_HELD_RISK_REPORT.json'):
        raise EvidenceError('Risk report reference not the reviewer-approved terminal report.')
    if reused and risk.get('supplementary_saved_only_posthoc_reporting') is not True:
        raise EvidenceError('Reused risk report must be explicitly supplementary saved-only reporting.')
    if not reused and risk_review.get('risk_report_SHA256') != refs['risk_report']['SHA256']:
        raise EvidenceError('Risk review does not bind supplied risk report.')
    if not reused and risk_review.get('minute_SHA256') != pins.get('MINUTE.npz'):
        raise EvidenceError('Risk review minute-output pin mismatch.')
    if risk.get('observation_count') != receipt.get('completed_minutes'):
        raise EvidenceError('Risk observations do not cover completed minutes.')
    f = finance.get('exact_financials') or extra.get('exact_financials') or finance
    amount_map = {'terminal_NAV_USDT':'NAV','fees_USDT':'fees_USDT','execution_cost_USDT':'execution_cost_USDT',
                  'signed_funding_USDT':'funding_USDT','gross_paid_market_turnover_USDT':'gross_fill_turnover_USDT',
                  'unpaid_liability_USDT':'unpaid_liability'}
    for out,key in amount_map.items():
        row[out] = decimal_text(f.get(key))
    rr=extra.get('transported_risk_summary',risk_review) if reused else risk_review
    row.update(completed_minutes=receipt['completed_minutes'],evidence_status='REVIEW_APPROVED_SAVED_TERMINAL',
               paid_trade_legs=finance.get('paid_trade_rows',finance.get('native_trade_rows')),
               D_warning_signals=(len(finance['paid_warning_signals']) if 'paid_warning_signals' in finance else finance.get('initial_Guard50_warning_intents')),
               internal_transfer_count=(0 if finance.get('no_transfer') is True else finance.get('transfers')),
               internal_transfer_USDT=('0' if finance.get('no_transfer') is True else decimal_text(finance.get('transferred_USDT'))),
               conditional_settlement_count=finance.get('conditional_settlement_rows',finance.get('settlements')),
               conditional_NAV_adjustment_USDT=decimal_text(finance.get('conditional_NAV_adjustment',finance.get('NAV_adjustment_USDT'))),
               conditional_collateral_forfeited_USDT=decimal_text(finance.get('actual_remaining_isolated_collateral_forfeited',finance.get('remaining_collateral_forfeited_USDT'))),
               conditional_positive_residual_forfeited_USDT=decimal_text(finance.get('conditional_positive_residual_forfeited',finance.get('positive_residual_forfeited_USDT'))),
               conditional_insurance_support_USDT=decimal_text(finance.get('conditional_insurance_support',finance.get('support_USDT'))),
               all_observation_MDD_fraction=finance.get('all_observation_max_drawdown',finance.get('all_observation_MDD')),
               minute_close_MDD_fraction=rr.get('minute_close_MDD'),
               complete_daily_close_MDD_fraction=rr.get('complete_daily_close_MDD'))
    rmap = {'minimum_free_cash_minute_close_USDT':'minimum_observed_free_cash_USDT',
            'maximum_isolated_margin_minute_close_USDT':'maximum_observed_isolated_margin_USDT',
            'gross_held_mean_minute_close':'gross_exposure_mean','gross_held_max_minute_close':'gross_exposure_max',
            'absolute_asset_weight_max_minute_close':'asset_exposure_absolute_max',
            'absolute_asset_weight_max_by_symbol_minute_close':'actual_absolute_weight_max_by_symbol',
            'absolute_asset_weight_mean_by_symbol_minute_close':'asset_exposure_absolute_mean_by_symbol',
            'signed_asset_weight_min_by_symbol_minute_close':'actual_signed_weight_min_by_symbol',
            'signed_asset_weight_max_by_symbol_minute_close':'actual_signed_weight_max_by_symbol',
            'realized_daily_annualized_volatility':'realized_daily_simple_return_annual_volatility',
            'nominal_annual_volatility_budget':'nominal_annual_volatility_budget',
            'forecast_annual_volatility_mean':'forecast_annual_volatility_mean',
            'forecast_annual_volatility_max':'forecast_annual_volatility_max',
            'forecast_max_absolute_budget_overshoot':'forecast_volatility_breach_max_absolute',
            'forecast_max_relative_budget_overshoot':'forecast_volatility_breach_max_relative_to_budget',
            'forecast_budget_overshoot_minutes':'forecast_volatility_breach_minutes',
            'observed_minute_cash_floor_breach_minutes':'minutes_observed_free_cash_below1000',
            'observed_minute_margin_ceiling_breach_minutes':'minutes_observed_margin_above8500'}
    by_symbol={'actual_absolute_weight_max_by_symbol','asset_exposure_absolute_mean_by_symbol',
               'actual_signed_weight_min_by_symbol','actual_signed_weight_max_by_symbol'}
    for out,key in rmap.items():
        value=risk.get(key)
        if value is not None:
            if key in by_symbol:
                if not isinstance(value,dict) or set(value)!={'BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'}:
                    raise EvidenceError('Saved by-symbol metric requires exactly frozen five symbols: '+key)
                if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in value.values()):
                    raise EvidenceError('Saved by-symbol children must be finite numeric values: '+key)
            elif isinstance(value,bool) or not isinstance(value,(int,float)):
                raise EvidenceError('Saved risk metric must be numeric: '+key)
        row[out]=value
    row.update(observed_minute_gross_cap_breach_minutes=rr.get('held_gross_cap_breach_minutes'),
               observed_minute_asset_cap_breach_minutes=rr.get('held_asset_cap_breach_minutes'),
               minimum_free_cash_all_observations_USDT=extra.get('minimum_free_cash_all_observations_USDT'),
               gross_held_max_all_observations=extra.get('gross_held_max_all_observations'))
    row.update(classify_return(reviewed=True,terminal=True,completed_minutes=row['completed_minutes'],
               required_minutes=row['required_minutes'],nav=row['terminal_NAV_USDT'],
               actual_paid_market_flat=finance.get('actual_paid_market_flat',finance.get('paid_flat')),
               conditional_settled_flat=finance.get('conditional_settled_flat'),
               settlement_count=row['conditional_settlement_count'],unpaid_liability=row['unpaid_liability_USDT'],
               terminal_classification=receipt['status']))
    row['bindings'] = {'source_identity':receipt.get('source_identity'),
                       'code_identity':receipt.get('code_identity'),
                       'policy_identity':receipt.get('policy_identity'),
                       'preparation_SHA256':receipt.get('preparation_SHA256'),
                       'root_GO_SHA256':receipt.get('root_GO_SHA256'),
                       'independent_source_review_SHA256':receipt.get('independent_review_SHA256'),
                       'new_expansion_manifest_SHA256':receipt.get('manifest_SHA256'),
                       'saved_JSON_references_rehashed':refs,
                       'independently_reviewed_terminal_output_pins':pins,
                       'large_output_hashes_reused_from_review_not_rehashed_or_decompressed':True,
                       'reused_risk_report_is_separate_supplement_not_original_case_output':reused,
                       'original_saved_contract':extra.get('original_saved_contract'),
                       'original_saved_quality':extra.get('original_saved_quality'),
                       'target_identity_from_frozen_manifest':{k:cell.get(k) for k in ('selected_target_raw_SHA256','frozen_TARGETS_NPZ_SHA256','frozen_annual_preparation_SHA256')}}
    return row


def build_report(manifest: dict, rows: list[dict], manifest_ref: dict, *, final: bool) -> dict:
    cells = expected_cells(manifest)
    if [r['cell_id'] for r in rows] != [c['cell_id'] for c in cells]:
        raise EvidenceError('Rows must cover the frozen cohort once, in fixed display order.')
    approved = sum(r['evidence_status']=='REVIEW_APPROVED_SAVED_TERMINAL' for r in rows)
    if final and approved != 18:
        raise EvidenceError('Final comparison requires all 18 reviewed terminal cells.')
    return {'schema':SCHEMA,'status':'FINAL_SAVED_ONLY' if final else 'PARTIAL_SNAPSHOT_PENDING_EXCLUDED',
            'manifest':manifest_ref,'expected_rows':18,'review_approved_terminal_rows':approved,
            'pending_rows':18-approved,'row_order':'YEAR_STRATEGY_PREDECLARED_TIER',
            'winner_selection_performed':False,'historical_runs_performed':0,
            'market_source_reads_performed':0,'NPZ_arrays_opened':0,
            'new_accounts_or_financial_clocks':0,'publication_actions':0,
            'continuous_two_year_CAGR':None,'qualifications':QUALIFICATIONS,'rows':rows}


def write_outputs(report: dict, output: Path) -> None:
    output.mkdir(parents=True,exist_ok=False)
    (output/'MATRIX_COMPARISON.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    rows=[]
    for row in report['rows']:
        rows.append({k:(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
                        if isinstance(v,(dict,list)) else v) for k,v in row.items()})
    with (output/'MATRIX_COMPARISON.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lines=['Fixed D frozen development matrix', '', report['status'], '',
           f"Reviewed terminal rows: {report['review_approved_terminal_rows']}/18. Pending rows: {report['pending_rows']}.", '',
           'Fixed-order annual results (no ranking or winner selection):']
    for r in report['rows']:
        ret=r['annual_return_fraction']
        text='pending or unavailable' if ret is None else f"{Decimal(ret)*100:.6f}%"
        mdd=r['all_observation_MDD_fraction']
        md='unavailable' if mdd is None else f'{100*mdd:.6f}%'
        duplicate=('; exact duplicate group '+r['duplicate_realized_path_group']) if r['duplicate_realized_path_group'] else ''
        lines.append(f"- {r['cell_id']}: {text}; {r['return_taxonomy']}; all-observation MDD {md}{duplicate}")
    lines += ['', 'Interpretation and limitations:']+['- '+q for q in QUALIFICATIONS]
    lines += ['', 'Full cost, exposure, risk, warning, debt, settlement and exact binding fields are retained in JSON and CSV. Null means unavailable or pending; it never means an observed zero.']
    (output/'REPORT.txt').write_text('\n'.join(lines)+'\n')


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--index',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--authorize-saved-final',action='store_true')
    p.add_argument('--partial-snapshot',action='store_true')
    args=p.parse_args()
    if args.authorize_saved_final == args.partial_snapshot:
        raise EvidenceError('Choose exactly one explicit final authorization or partial snapshot mode.')
    index=json.loads(args.index.read_text())
    if args.authorize_saved_final and index.get('parent_authorized_all17_terminal_saved_comparison') is not True:
        raise EvidenceError('Final reporting needs parent all17-terminal authorization in index.')
    manifest,manifest_ref=bound_json(args.workspace,index['manifest'])
    if manifest_ref['SHA256']!=EXPECTED_MANIFEST_SHA256:
        raise EvidenceError('Wrong frozen manifest.')
    rows=[]
    by_id=index.get('cells',{})
    for cell in expected_cells(manifest):
        spec=by_id.get(cell['cell_id'])
        if spec is None or spec.get('review_approved_terminal') is not True:
            rows.append(pending_row(cell));continue
        objects={};refs={}
        for key in ('case_receipt','finance_review','risk_report','risk_review'):
            objects[key],refs[key]=bound_json(args.workspace,spec[key])
        extra={}
        if spec.get('transported_risk_review'):
            _,refs['transported_risk_review']=bound_json(args.workspace,spec['transported_risk_review'])
        if spec.get('extra_saved_metrics'):
            extra,refs['extra_saved_metrics']=bound_json(args.workspace,spec['extra_saved_metrics'])
        pins=objects['finance_review'].get('evidence_pins') or spec.get('original_reviewed_output_pins')
        if not isinstance(pins,dict):
            raise EvidenceError('Reviewed output pins required.')
        rows.append(normalize_reviewed_row(cell,objects['case_receipt'],objects['finance_review'],
                     objects['risk_report'],objects['risk_review'],pins,refs,extra))
    by_row={r['cell_id']:r for r in rows}
    for spec in index.get('duplicate_proofs',[]):
        left=by_row[spec['left_cell_id']];right=by_row[spec['right_cell_id']]
        if not left['bindings'] or not right['bindings']:
            continue
        proof,ref=bound_json(args.workspace,spec['proof'])
        if not validate_duplicate_proof(proof,left['cell_id'],right['cell_id'],
             left['bindings']['independently_reviewed_terminal_output_pins'],
             right['bindings']['independently_reviewed_terminal_output_pins']):
            raise EvidenceError('Duplicate assertion lacks complete exact saved path proof.')
        for row in (left,right):
            row['duplicate_realized_path_group']=spec['group_id']
            row['duplicate_realized_path_evidence']=ref
    report=build_report(manifest,rows,manifest_ref,final=args.authorize_saved_final)
    report['additional_saved_provenance_evidence']=[]
    for ref in index.get('additional_provenance_evidence',[])+index.get('existing_duplicate_definition_addenda',[]):
        _,verified_ref=bound_json(args.workspace,ref)
        report['additional_saved_provenance_evidence'].append(verified_ref)
    report['comparison_helper_SHA256']=file_sha256(Path(__file__))
    report['evidence_index_SHA256']=file_sha256(args.index)
    write_outputs(report,args.output)
    print(json.dumps({'status':report['status'],'rows':18,'output':str(args.output)}))

if __name__=='__main__':
    main()
