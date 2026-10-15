#!/usr/bin/env python3
"""Read-only saved annual-output telemetry, not an account or a backtester.

Final mode requires parent approval and the completed independently reviewed
18-row matrix. It opens precisely the 12 fixed STATIC50/HOLD saved outputs.
Only numpy and the standard library are imported; no financial/runtime imports.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import csv
import hashlib
import json
from pathlib import Path
from typing import Any
import numpy as np

SCHEMA = 'SAVED_DISTINCT_FAMILY_RISK_EVIDENCE_V1'
MANIFEST_SHA256 = '0c08a0c362c8222d2dc16735f7ebf11a26f4892999bc57b3b062d189ff050638'
PARENT_COMMIT = '48e42f4040e317edf732bfedc9dce5d54e29ed12'
MINUTE_US = 60_000_000
DAY_US = 86_400_000_000
INITIAL_NAV = 10000.0
SYMBOLS = ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
FAMILIES = ('STATIC50','VOL_MANAGED_HOLD')
TIERS = ('LOW','MID','HIGH')
CALENDARS = {2023:(1672531200000000,1704067200000000),
             2024:(1704067200000000,1735689600000000)}
PAID_STATUS = 'FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT'
CONDITIONAL_STATUS = 'FULL_CALENDAR_CONDITIONAL_MODEL_SETTLED_FLAT'
FULL_STATUS_ALLOWLIST = (PAID_STATUS,CONDITIONAL_STATUS)
COLUMN_NAMES = ('nav','free_cash','isolated_balance','gross_notional','net_signed_notional',
 'cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover') + \
 tuple(s+'_quantity' for s in SYMBOLS) + tuple(s+'_signed_marked_notional' for s in SYMBOLS) + \
 tuple(s+'_isolated_balance' for s in SYMBOLS) + tuple(s+'_isolated_equity' for s in SYMBOLS) + \
 tuple(s+'_signed_weight' for s in SYMBOLS) + ('gross_weight','net_signed_weight','close_us')
QUALIFICATIONS = [
 'These 2023/2024 adaptive seen-development annual outputs are not independent out-of-sample validation or alpha evidence.',
 'All 12 analysis cells are fixed in advance: two distinct families, all three nominal tiers, both years. The original 18-row cohort, including H090 exact duplicates, is retained; duplicate realized paths are not independent confirmation.',
 'Every annual cell starts a fresh 10000-USDT account. No annual returns are multiplied; no continuous two-year account or CAGR is constructed.',
 'Saved float64 NAV returns and weights are deterministic observation telemetry, not the native40 exact financial ledger. Native40 chronological terminal approvals remain authoritative; raw precision100 stored-delta residuals are preserved without repair.',
 'Daily volatility is std(ddof=1) of complete daily endpoint simple NAV returns including the initial10000 denominator, multiplied by sqrt365 even for leap-year2024.',
 'Native all-observation MDD includes initial NAV, observed minute-close marks and scheduler fills/funding. Minute-close MDD and daily-close MDD are separate; none certifies an intraminute bar-high/low price path.',
 'Exposure means, extrema and time-flat observations are post-transition minute-close telemetry. Admission limits do not guarantee continuous marked-state gross, cash, margin, asset weights or forecast volatility.',
 'Forecast-budget overshoots are copied only from independently approved frozen-covariance risk reports. This module does not reread targets, covariance, raw prices, financial accounts or historical providers.',
 'Funding is signed: positive receipts benefit NAV, negative payments reduce NAV. Fees and execution-price friction are separate costs. Same-quantity gross PnL is an accounting bridge, not a counterfactual strategy.',
 'Net annual return divided by full-sample realized volatility or mean gross exposure is future-informed descriptive arithmetic. It is not an executed scaled strategy, paid-cost resimulation, OOS test, executable advantage or alpha.',
 'No causal risk-control rule is implemented. Any past-only normalization policy needs a separate frozen specification and new approval before execution.',
 'All-minute originals are omitted from compact evidence. Public daily telemetry can reproduce this module\'s daily curves and aggregate table, but all-minute deep revalidation requires the hash-pinned omitted MINUTE.npz originals.',
 '2024 NAV, weights and forecasts retain the original bound carry-forward/unknown causal-mark-quality sidecar. They are frozen-model telemetry, not certified exchange prices/execution or true-market risk. Every fixed calendar observation is retained; no quality/performance subset or new quality rule is selected.',
 'Native venue filters, liquidation/insurance/ADL, fill/latency assumptions and funding publication remain uncertified. No paid/live/new-data/holdout/2025 or financial replay is performed.'
]

class EvidenceError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def json_sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):
            h.update(b)
    return h.hexdigest()


def relative_path(base: Path, text: str, suffix: str | None=None) -> Path:
    p=Path(text)
    require(not p.is_absolute() and '..' not in p.parts,'Only bounded relative saved paths allowed')
    if suffix:
        require(p.suffix==suffix,'Unexpected saved file extension')
    result=(base/p).resolve()
    require(result.is_relative_to(base.resolve()),'Saved path escapes workspace')
    return result


def bound_json(base: Path, ref: dict) -> dict:
    require(set(ref)=={'path','SHA256'},'JSON reference requires exactly path and SHA256')
    p=relative_path(base,ref['path'],'.json')
    require(file_sha(p)==ref['SHA256'],'Saved JSON hash mismatch: '+ref['path'])
    x=json.loads(p.read_text(),parse_constant=lambda s: (_ for _ in ()).throw(EvidenceError(s)))
    require(isinstance(x,dict),'Saved JSON object required')
    return x


def finite_decimal(x: Any) -> Decimal:
    require(x is not None and not isinstance(x,bool),'Missing financial amount')
    d=Decimal(str(x));require(d.is_finite(),'Nonfinite financial amount')
    return d


def exact_annual_return(nav: Any) -> str:
    with localcontext() as ctx:
        ctx.prec=100
        return str(finite_decimal(nav)/Decimal('10000')-1)


def cost_diagnostic(fees: Any, execution: Any, signed_funding: Any) -> dict:
    """Preserve funding sign; do not double-count execution against realized PnL."""
    f,e,u=(finite_decimal(x) for x in (fees,execution,signed_funding))
    require(f>=0 and e>=0,'Fees/execution costs cannot be negative')
    with localcontext() as ctx:
        ctx.prec=100
        return {'fees_USDT':str(f),'execution_price_cost_USDT':str(e),
                'signed_funding_USDT':str(u),
                'same_quantity_fee_execution_less_signed_funding_USDT':str(f+e-u),
                'funding_sign':'POSITIVE_RECEIPT_NEGATIVE_PAYMENT',
                'not_a_counterfactual_strategy':True}


def ratio_diagnostic(raw_return: Any, denominator: float) -> str | None:
    require(np.isfinite(denominator) and denominator>=0,'Invalid descriptive denominator')
    if denominator==0:
        return None
    with localcontext() as ctx:
        ctx.prec=100
        return str(finite_decimal(raw_return)/Decimal(str(denominator)))


def canonical_array_signature(values: np.ndarray, columns: np.ndarray,
                              original_key_order: list[str] | None=None) -> dict:
    """Canonical f64 is little-endian C order; ordered names are UTF8 JSON.

    Also retain original array dtype, shape and C-order byte signatures. A
    reordering of columns, one-bit value change or signed-zero change is visible.
    """
    require(values.ndim==2 and values.dtype.kind=='f' and values.dtype.itemsize==8,
            'Saved values must be a float64 matrix')
    require(columns.ndim==1 and columns.dtype.kind in 'US','String columns required')
    names=columns.tolist()
    require(len(names)==values.shape[1] and len(set(names))==len(names),'Invalid/duplicate column names')
    raw=[{'key':k,'dtype':a.dtype.str,'shape':list(a.shape),
          'raw_C_order_SHA256':hashlib.sha256(a.tobytes(order='C')).hexdigest()}
         for k,a in [('values',values),('columns',columns)]]
    if original_key_order is not None:
        require(set(original_key_order)=={'values','columns'} and len(original_key_order)==2,
                'Archive requires exactly values and columns')
        raw=sorted(raw,key=lambda x:original_key_order.index(x['key']))
    cv=np.asarray(values,dtype='<f8',order='C')
    return {'schema':'CANONICAL_LITTLE_ENDIAN_F64_AND_ORDERED_COLUMNS_V1',
            'values_dtype':'<f8','values_shape':list(cv.shape),
            'values_C_order_SHA256':hashlib.sha256(cv.tobytes(order='C')).hexdigest(),
            'columns_UTF8_canonical_JSON_SHA256':json_sha(names),
            'columns_order':names,'original_archive_array_descriptors':raw,
            'original_archive_descriptor_SHA256':json_sha(raw)}


def validate_minute(values: np.ndarray, columns: np.ndarray, calendar: tuple[int,int],
                    required_minutes: int) -> None:
    require(tuple(columns.tolist())==COLUMN_NAMES,'Exact frozen 37-column layout required')
    require(values.shape==(required_minutes,37),'Missing or extra minute observations')
    require(values.dtype.kind=='f' and values.dtype.itemsize==8,'Saved float64 values required')
    require(np.isfinite(values).all(),'Nonfinite saved telemetry')
    start,stop=calendar
    require(stop-start==required_minutes*MINUTE_US and required_minutes%1440==0,
            'Full exact daily annual calendar required')
    clock=values[:,36]
    expected=start+np.arange(1,required_minutes+1,dtype=np.int64)*MINUTE_US
    require(np.array_equal(clock,expected.astype(np.float64)),'Noncontiguous or wrong saved calendar')
    require(np.array_equal(clock.astype(np.int64),expected),'Lossy minute clock encoding')
    require((values[:,0]>0).all(),'NAV must be positive for risk telemetry')
    weights=values[:,29:34]
    require(np.max(np.abs(np.abs(weights).sum(1)-values[:,34]))<=1e-12,
            'Gross weight differs from signed asset projection')
    require(np.max(np.abs(weights.sum(1)-values[:,35]))<=1e-12,
            'Net weight differs from signed asset projection')


def daily_telemetry(values: np.ndarray, columns: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    """Every full day has1440 exact saved observations. No interpolation/tail."""
    n=len(values);require(n>0 and n%1440==0,'Complete days required')
    names=list(columns);require(tuple(names)==COLUMN_NAMES,'Exact minute columns required')
    d=values.reshape(-1,1440,37)
    out=[];out_names=[]
    def put(name,value):
        out_names.append(name);out.append(np.asarray(value,dtype=np.float64))
    put('day_close_us',d[:,-1,36]);put('minute_observation_count',np.full(len(d),1440.))
    nav=d[:,-1,0];put('nav_close',nav)
    put('daily_simple_return',nav/np.r_[INITIAL_NAV,nav[:-1]]-1)
    for k,c in [('gross_weight',34),('net_signed_weight',35)]:
        v=d[:,:,c]
        put(k+'_sum',v.sum(1));put(k+'_min',v.min(1));put(k+'_max',v.max(1))
        put('absolute_'+k+'_sum',np.abs(v).sum(1))
        put('absolute_'+k+'_max',np.abs(v).max(1))
    # Flat means every saved actual quantity is exactly zero, with no epsilon.
    put('flat_actual_quantity_minutes',np.all(d[:,:,9:14]==0,axis=2).sum(1))
    for i,s in enumerate(SYMBOLS):
        w=d[:,:,29+i]
        put(s+'_signed_weight_sum',w.sum(1));put(s+'_signed_weight_min',w.min(1))
        put(s+'_signed_weight_max',w.max(1));put(s+'_absolute_weight_sum',np.abs(w).sum(1))
        put(s+'_absolute_weight_max',np.abs(w).max(1))
    put('minimum_free_cash_USDT',d[:,:,1].min(1))
    put('maximum_isolated_margin_USDT',d[:,:,2].max(1))
    put('free_cash_below1000_minutes',(d[:,:,1]<1000-1e-8).sum(1))
    put('isolated_margin_above8500_minutes',(d[:,:,2]>8500+1e-8).sum(1))
    for key,c in [('fees_USDT',5),('execution_cost_USDT',6),('signed_funding_USDT',7),('turnover_USDT',8)]:
        cumulative=d[:,-1,c]
        put('cumulative_'+key,cumulative)
        put('daily_change_'+key,cumulative-np.r_[0.,cumulative[:-1]])
    return np.column_stack(out).astype('<f8'),np.asarray(out_names,dtype='<U64')


def aggregate_daily(values: np.ndarray, columns: np.ndarray) -> dict:
    require(values.ndim==2 and len(values)>1 and np.isfinite(values).all(),'Finite multiple daily rows required')
    names=list(columns);require(len(names)==len(set(names)),'Duplicate daily columns')
    def c(name):return values[:,names.index(name)]
    require(np.all(c('minute_observation_count')==1440),'Daily count must be1440')
    require(np.array_equal(np.diff(c('day_close_us')),np.full(len(values)-1,DAY_US)),
            'Noncontiguous daily clocks')
    nav=c('nav_close');require((nav>0).all(),'Nonpositive daily NAV')
    returns=nav/np.r_[INITIAL_NAV,nav[:-1]]-1
    require(np.array_equal(returns,c('daily_simple_return')),'Daily return column inconsistent')
    count=int(c('minute_observation_count').sum());curve=np.r_[INITIAL_NAV,nav]
    result={'observed_minutes':count,'complete_days':len(values),
      'saved_float64_terminal_NAV_USDT':float(nav[-1]),
      'daily_realized_annual_volatility':float(returns.std(ddof=1)*np.sqrt(365)),
      'daily_close_MDD_fraction':float(np.max(1-curve/np.maximum.accumulate(curve))),
      'gross_weight_mean':float(c('gross_weight_sum').sum()/count),
      'gross_weight_min':float(c('gross_weight_min').min()),
      'gross_weight_max':float(c('gross_weight_max').max()),
      'net_signed_weight_mean':float(c('net_signed_weight_sum').sum()/count),
      'net_signed_weight_min':float(c('net_signed_weight_min').min()),
      'net_signed_weight_max':float(c('net_signed_weight_max').max()),
      'net_absolute_weight_mean':float(c('absolute_net_signed_weight_sum').sum()/count),
      'net_absolute_weight_max':float(c('absolute_net_signed_weight_max').max()),
      'flat_actual_quantity_minutes':int(c('flat_actual_quantity_minutes').sum()),
      'flat_actual_quantity_fraction':float(c('flat_actual_quantity_minutes').sum()/count),
      'minimum_free_cash_minute_close_USDT':float(c('minimum_free_cash_USDT').min()),
      'maximum_isolated_margin_minute_close_USDT':float(c('maximum_isolated_margin_USDT').max()),
      'free_cash_below1000_minutes':int(c('free_cash_below1000_minutes').sum()),
      'isolated_margin_above8500_minutes':int(c('isolated_margin_above8500_minutes').sum()),
      'asset_weights':{}}
    for s in SYMBOLS:
        result['asset_weights'][s]={
          'signed_mean':float(c(s+'_signed_weight_sum').sum()/count),
          'signed_min':float(c(s+'_signed_weight_min').min()),
          'signed_max':float(c(s+'_signed_weight_max').max()),
          'absolute_mean':float(c(s+'_absolute_weight_sum').sum()/count),
          'absolute_max':float(c(s+'_absolute_weight_max').max())}
    return result


def validate_full_cohort(report: dict, manifest: dict) -> list[dict]:
    require(report.get('status')=='FINAL_SAVED_ONLY','Final approved comparison required')
    require(report.get('review_approved_terminal_rows')==18 and report.get('pending_rows')==0,
            'All18 annual cells must be independently approved')
    rows=report.get('rows',[])
    expected={(y,s,t) for y in CALENDARS for s in ('STATIC50','H090','VOL_MANAGED_HOLD') for t in TIERS}
    got={(r.get('year'),r.get('strategy'),r.get('tier')) for r in rows}
    require(len(rows)==18 and len({r.get('cell_id') for r in rows})==18 and got==expected,
            'Exact18-cell frozen cohort required; no selection or duplicates')
    manifest_cells={c['cell_id']:c for c in manifest['cells']}
    require(len(manifest_cells)==17,'Frozen17 manifest malformed')
    for r in rows:
        y=r['year'];require(r['cell_id']==f"{y}_{r['strategy']}_{r['tier']}",'Cell ID mismatch')
        require(r.get('evidence_status')=='REVIEW_APPROVED_SAVED_TERMINAL','Unapproved case')
        require(r.get('initial_wallet_USDT')=='10000','Fresh10000 annual account required')
        required=(CALENDARS[y][1]-CALENDARS[y][0])//MINUTE_US
        require(r.get('required_minutes')==required and r.get('completed_minutes')==required,
                'Partial/halted prefixes cannot become annual comparators')
        require(r.get('adaptive_DEV_only') is True,'DEV qualification required')
        require(r.get('bindings') is not None,'Missing reviewed saved bindings')
        if r['cell_id'] in manifest_cells:
            m=manifest_cells[r['cell_id']]
            require((m['year'],m['strategy'],m['tier'])==(y,r['strategy'],r['tier']),
                    'Frozen manifest cell mismatch')
            require(m['calendar']==list(CALENDARS[y]),'Frozen calendar mismatch')
            require(r['bindings'].get('new_expansion_manifest_SHA256')==MANIFEST_SHA256,
                    'Wrong expansion manifest binding')
        else:
            require(r['cell_id']=='2024_STATIC50_MID' and r.get('reused_prior_completed_case') is True,
                    'Only exact prior2024 STATIC MID may be reused')
        # Do not relabel conditional settlements, unresolved marked positions or
        # partial histories as comparable paid annual returns.
        require(r.get('return_taxonomy') in FULL_STATUS_ALLOWLIST,'Unknown/unresolved terminal taxonomy')
        for key in ('year','required_minutes','completed_minutes','conditional_settlement_count'):
            require(type(r.get(key)) is int,'Integer field required: '+key)
        require(r['conditional_settlement_count']>=0,'Negative settlement count')
        require(r.get('annual_return_fraction') is not None,'Full annual marked return required')
        require(finite_decimal(r['annual_return_fraction'])==Decimal(exact_annual_return(r['terminal_NAV_USDT'])),
                'Native marked annual return mismatch')
        for key in ('all_observation_MDD_fraction','minute_close_MDD_fraction','complete_daily_close_MDD_fraction',
                    'realized_daily_annualized_volatility','gross_held_mean_minute_close','gross_held_max_minute_close',
                    'minimum_free_cash_minute_close_USDT','maximum_isolated_margin_minute_close_USDT'):
            v=r.get(key)
            require(type(v) in (int,float) and np.isfinite(v),'Finite telemetry field required: '+key)
        paid=r.get('return_taxonomy')==PAID_STATUS
        if paid:
            require(r.get('conditional_settlement_count')==0 and finite_decimal(r['unpaid_liability_USDT'])==0,
                    'Paid comparator contains settlement/debt')
            require(r.get('comparable_paid_annual_return_fraction')==exact_annual_return(r['terminal_NAV_USDT']),
                    'Native exact annual return mismatch')
        else:
            require(r['conditional_settlement_count']>0,'Conditional taxonomy requires actual settlements')
            require(r.get('comparable_paid_annual_return_fraction') is None,
                    'Nonpaid taxonomy cannot provide paid annual return')
            require(finite_decimal(r.get('conditional_model_annual_return_fraction'))==
                    finite_decimal(r['annual_return_fraction']),'Conditional annual return mismatch')
    return sorted([r for r in rows if r['strategy'] in FAMILIES],
                  key=lambda r:(r['year'],TIERS.index(r['tier']),FAMILIES.index(r['strategy'])))


def close(a: float,b: float,name: str,tolerance=1e-12) -> None:
    require(np.isfinite(a) and np.isfinite(b) and abs(a-b)<=tolerance*max(1.,abs(a),abs(b)),
            'Saved telemetry/review mismatch: '+name)


def validate_review_inputs(base: Path,row: dict) -> tuple[Path,dict,dict,dict]:
    refs=row['bindings']['saved_JSON_references_rehashed']
    objs={k:bound_json(base,refs[k]) for k in ('case_receipt','finance_review','risk_report','risk_review')}
    receipt=objs['case_receipt'];finance=objs['finance_review'];risk=objs['risk_report'];review=objs['risk_review']
    require(finance.get('status','').startswith('PASS_') and review.get('status','').startswith('PASS_'),
            'Independent terminal and risk PASS required')
    require(receipt.get('status')==row['return_taxonomy'] or
            (row['return_taxonomy'].startswith('FULL_CALENDAR_') and receipt.get('status')==row['return_taxonomy']),
            'Receipt taxonomy mismatch')
    require(receipt.get('completed_minutes')==row['completed_minutes'],'Receipt calendar mismatch')
    pins=row['bindings']['independently_reviewed_terminal_output_pins']
    require(refs['case_receipt']['SHA256']==pins['CASE_RECEIPT.json'],'Receipt pin mismatch')
    reused=row['cell_id']=='2024_STATIC50_MID'
    if reused:
        ev=review.get('evidence_SHA256',{})
        minute_name=str(Path(refs['case_receipt']['path']).parent/'MINUTE.npz')
        require(ev.get(minute_name)==pins['MINUTE.npz'],'Supplementary review original MINUTE pin mismatch')
        require(ev.get(refs['risk_report']['path'])==refs['risk_report']['SHA256'],
                'Supplementary risk report review pin mismatch')
        require(review.get('original_code_policy_quality_source_preparation_GO_bindings_preserved') is True,
                'Original reused source/GO/code/policy/quality bindings not preserved')
        transport=refs.get('transported_risk_review',{})
        require(ev.get(transport.get('path'))==transport.get('SHA256') and bool(transport),
                'Transported independent risk review pin mismatch')
        objs['transported_risk_review']=bound_json(base,transport)
        require(objs['transported_risk_review'].get('status','').startswith('PASS_'),
                'Transported independent risk review not PASS')
        require(finance.get('source_GO_review_code_pins_verified') is True,
                'Original reused finance source/GO/code pins not verified')
    else:
        require(review.get('minute_SHA256')==pins['MINUTE.npz'],'Risk reviewer original MINUTE pin mismatch')
        require(review.get('risk_report_SHA256')==refs['risk_report']['SHA256'],'Risk report review pin mismatch')
    quality=row['bindings'].get('original_saved_quality',{})
    require(quality.get('reference') and 'value' in quality,'Original bound causal-mark quality required')
    require(bound_json(base,quality['reference'])==quality['value'],'Original saved quality value/hash mismatch')
    case=relative_path(base,refs['case_receipt']['path'],'.json').parent
    allowed=('bounded_native_continuation_guard50_exit_expansion_20261015/actual_first5_attempt001/',
             'bounded_native_continuation_guard50_exit_expansion_20261015/actual_remaining12_attempt001/',
             'bounded_native_continuation_guard50_exit_20261015/actual_2024_D_attempt001/GUARD50_EXIT_ONLY')
    text=str(case.relative_to(base.resolve()))
    require(any(text.startswith(x) for x in allowed),'Case outside exact allowed completed output dirs')
    if row['cell_id']!='2024_STATIC50_MID':
        require(case.name==row['cell_id'] and receipt.get('cell_id')==row['cell_id'],'Case directory/cell mismatch')
        require(receipt.get('calendar')==list(CALENDARS[row['year']]),'Receipt exact annual calendar mismatch')
        require(finance.get('native40_every_event_exact') is True,'Native40 exact approval required')
        require(finance.get('evidence_pins')==pins,'Approved finance output pins mismatch')
    # The source comparison already binds this completed result in the independent
    # terminal proof. Read only its pinned saved JSON summary, no audit replay.
    native_ref={'path':str((case/'NATIVE_RESULT.json').relative_to(base.resolve())),
                'SHA256':pins['NATIVE_RESULT.json']}
    objs['native_result']=bound_json(base,native_ref)
    refs=dict(refs);refs['native_result']=native_ref
    p=case/'MINUTE.npz'
    require(file_sha(p)==pins['MINUTE.npz'],'Saved completed MINUTE archive hash mismatch')
    return p,objs,pins,refs


def analyze_saved_cell(base: Path,row: dict,out: Path) -> dict:
    minute,objs,pins,refs=validate_review_inputs(base,row)
    with np.load(minute,allow_pickle=False) as z:
        require(set(z.files)=={'values','columns'} and len(z.files)==2,'Unexpected MINUTE members')
        values=z['values'];columns=z['columns'];order=list(z.files)
    validate_minute(values,columns,CALENDARS[row['year']],row['required_minutes'])
    signature=canonical_array_signature(values,columns,order)
    daily,daily_columns=daily_telemetry(values,columns)
    aggregate=aggregate_daily(daily,daily_columns)
    minute_returns=values[:,0]/np.r_[INITIAL_NAV,values[:-1,0]]-1
    require(np.isfinite(minute_returns).all(),'Nonfinite saved NAV return telemetry')
    minute_return_evidence={'formula':'nav[t]/nav[t-1]-1; first denominator10000',
      'count':len(minute_returns),'dtype':'<f8',
      'canonical_C_order_SHA256':hashlib.sha256(np.asarray(minute_returns,dtype='<f8').tobytes()).hexdigest(),
      'minimum':float(minute_returns.min()),'maximum':float(minute_returns.max()),
      'mean':float(minute_returns.mean()),'sample_std_ddof1':float(minute_returns.std(ddof=1)),
      'deterministic_saved_float64_telemetry_not_native40_ledger':True,
      'full_minute_returns_omitted_requires_originals_for_recompute':True}
    curve=np.r_[INITIAL_NAV,values[:,0]]
    minute_mdd=float(np.max(1-curve/np.maximum.accumulate(curve)))
    native_mdd=row['all_observation_MDD_fraction']
    require(native_mdd is not None and native_mdd+1e-12>=minute_mdd>=aggregate['daily_close_MDD_fraction']-1e-12,
            'MDD scopes inconsistent')
    checks=[(aggregate['daily_realized_annual_volatility'],row['realized_daily_annualized_volatility'],'daily vol'),
            (aggregate['gross_weight_mean'],row['gross_held_mean_minute_close'],'gross mean'),
            (aggregate['gross_weight_max'],row['gross_held_max_minute_close'],'gross max'),
            (minute_mdd,row['minute_close_MDD_fraction'],'minute MDD'),
            (aggregate['daily_close_MDD_fraction'],row['complete_daily_close_MDD_fraction'],'daily MDD'),
            (aggregate['minimum_free_cash_minute_close_USDT'],row['minimum_free_cash_minute_close_USDT'],'minimum cash'),
            (aggregate['maximum_isolated_margin_minute_close_USDT'],row['maximum_isolated_margin_minute_close_USDT'],'maximum margin')]
    for a,b,name in checks:close(a,b,name)
    for s in SYMBOLS:
        for k,rkey in [('absolute_mean','absolute_asset_weight_mean_by_symbol_minute_close'),
                       ('absolute_max','absolute_asset_weight_max_by_symbol_minute_close'),
                       ('signed_min','signed_asset_weight_min_by_symbol_minute_close'),
                       ('signed_max','signed_asset_weight_max_by_symbol_minute_close')]:
            close(aggregate['asset_weights'][s][k],row[rkey][s],s+' '+k)
    # These are deterministic float projections of reviewed native exact values,
    # never a claim that the saved float itself is the exact monetary ledger.
    for idx,key in [(0,'terminal_NAV_USDT'),(5,'fees_USDT'),(6,'execution_cost_USDT'),
                    (7,'signed_funding_USDT'),(8,'gross_paid_market_turnover_USDT')]:
        require(float(finite_decimal(row[key]))==float(values[-1,idx]),'Terminal native-to-float projection mismatch: '+key)
    native_summary=objs['native_result']['summary']['decimal_strings']
    require(native_summary['NAV']==row['terminal_NAV_USDT'],'Native exact NAV summary mismatch')
    for key,field in [('fees_USDT','fees_USDT'),('execution_cost_USDT','execution_cost_USDT'),
                      ('funding_USDT','signed_funding_USDT'),('gross_fill_turnover_USDT','gross_paid_market_turnover_USDT')]:
        require(finite_decimal(native_summary[key])==finite_decimal(row[field]),'Native cost summary mismatch: '+key)
    paid=row['comparable_paid_annual_return_fraction']
    result={'cell_id':row['cell_id'],'year':row['year'],'strategy':row['strategy'],'tier':row['tier'],
      'initial_wallet_USDT':'10000','return_taxonomy':row['return_taxonomy'],
      'native_exact_terminal_NAV_USDT':row['terminal_NAV_USDT'],
      'native_exact_paid_annual_return_fraction':paid,
      'native_exact_annual_marked_return_fraction':row['annual_return_fraction'],
      'all_observation_native_MDD_fraction':native_mdd,'minute_close_MDD_fraction':minute_mdd,
      'saved_float64_aggregate':aggregate,'minute_NAV_simple_return_evidence':minute_return_evidence,
      'forecast_risk_approved_report':{k:row[k] for k in [
       'nominal_annual_volatility_budget','forecast_annual_volatility_mean','forecast_annual_volatility_max',
       'forecast_max_absolute_budget_overshoot','forecast_max_relative_budget_overshoot','forecast_budget_overshoot_minutes',
       'observed_minute_gross_cap_breach_minutes','observed_minute_asset_cap_breach_minutes']},
      'native_costs':cost_diagnostic(row['fees_USDT'],row['execution_cost_USDT'],row['signed_funding_USDT']),
      'native_exact_paid_turnover_USDT':row['gross_paid_market_turnover_USDT'],
      'native_paid_trade_legs':row['paid_trade_legs'],'native_paid_warning_signals':row['D_warning_signals'],
      'native_warning_episode_unit':'PER_SYMBOL_INITIAL_WARNING_INTENT_WITH_PAID_EXIT_EVIDENCE; NOT_UNIQUE_PORTFOLIO_DAYS',
      'native40_financial_residuals':{k:objs['finance_review'][k] for k in (
       'native40_secondary_PnL_bridge_residual','raw_precision100_stored_delta_terminal_residuals',
       'native_secondary_residual','exact100_stored_delta_terminal_errors',
       'exact100_stored_cash_debt_delta_terminal_errors') if k in objs['finance_review']},
      'future_informed_descriptive_ratios':{
       'paid_return_div_full_sample_daily_realized_annual_volatility':None if paid is None else ratio_diagnostic(paid,aggregate['daily_realized_annual_volatility']),
       'paid_return_div_full_sample_mean_gross_weight':None if paid is None else ratio_diagnostic(paid,aggregate['gross_weight_mean']),
       'denominators_include_future_observations':True,'executed_scaled_trades_or_costs':False,
       'OOS_or_alpha_or_executable_advantage_claim':False},
      'MINUTE_original':{'path':str(minute.relative_to(base.resolve())), 'SHA256':pins['MINUTE.npz'],
                         'bytes':minute.stat().st_size,'omitted_from_compact_public_evidence':True,
                         'signature':signature},
      'daily_formula':'1440 contiguous original observations/day; endpoint NAV returns; unrounded daily sums/extrema of post-transition weights',
      'annual_aggregate_formula':'included aggregate_daily() applied to lossless published DAILY.npz',
      'authoritative_reviewed_matrix_row':row,
      'reviewed_JSON_references_rehashed':refs,
      'saved_only_accounts_created':0,'financial_replays':0,'raw_source_or_covariance_reads':0}
    result['native_same_quantity_accounting_bridge']={
      'gross_mid_price_PnL_same_executed_quantities_USDT':native_summary.get('gross_PnL_same_quantities'),
      'native_net_PnL_USDT':native_summary.get('net_PnL'),
      'native_accounting_bridge_error_USDT':native_summary.get('accounting_bridge_error_USDT'),
      'formula':'net_PnL = gross_PnL_same_quantities - execution_cost - fees + signed_funding + native_bridge_residual',
      'execution_already_in_realized_PnL_not_subtracted_twice':True,
      'native40_chronological_approval_authoritative':True,
      'no_counterfactual_no_cost_strategy':True}
    # Preserve native ledger secondary bridge information without rebuilding it.
    finance=objs['finance_review']
    if 'legacy_delta_sum_report_retained_non_authoritative' in finance:
        result['legacy_delta_sum_report_retained_non_authoritative']=finance['legacy_delta_sum_report_retained_non_authoritative']
    out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/'DAILY.npz',values=daily,columns=daily_columns)
    result['DAILY']={'filename':'DAILY.npz','SHA256':file_sha(out/'DAILY.npz'),
                     'bytes':(out/'DAILY.npz').stat().st_size,
                     'signature':canonical_array_signature(daily,daily_columns,['values','columns'])}
    write_json(out/'CELL_EVIDENCE.json',result)
    return result


def paired_rows(cells: list[dict]) -> list[dict]:
    lookup={(c['year'],c['tier'],c['strategy']):c for c in cells}
    require(len(cells)==12 and len(lookup)==12,'Exact12 distinct-family analysis cells required')
    result=[]
    for year in CALENDARS:
        for tier in TIERS:
            s,h=(lookup[(year,tier,f)] for f in FAMILIES)
            a,b=(x['native_exact_paid_annual_return_fraction'] for x in (s,h))
            gap=None
            if a is not None and b is not None:
                with localcontext() as ctx:
                    ctx.prec=100;gap=str(Decimal(b)-Decimal(a))
            result.append({'year':year,'tier':tier,'STATIC50_cell_id':s['cell_id'],
                'VOL_MANAGED_HOLD_cell_id':h['cell_id'],
                'STATIC50_paid_annual_return_fraction':a,'VOL_MANAGED_HOLD_paid_annual_return_fraction':b,
                'HOLD_minus_STATIC_paid_return_fraction':gap,
                'gap_status':'PAIRED_RAW_PAID_ANNUAL_RETURN' if gap is not None else 'NOT_COMPARABLE_PAID_ANNUAL',
                'STATIC50_daily_realized_annual_volatility':s['saved_float64_aggregate']['daily_realized_annual_volatility'],
                'VOL_MANAGED_HOLD_daily_realized_annual_volatility':h['saved_float64_aggregate']['daily_realized_annual_volatility'],
                'STATIC50_all_observation_native_MDD_fraction':s['all_observation_native_MDD_fraction'],
                'VOL_MANAGED_HOLD_all_observation_native_MDD_fraction':h['all_observation_native_MDD_fraction'],
                'STATIC50_mean_gross_weight':s['saved_float64_aggregate']['gross_weight_mean'],
                'VOL_MANAGED_HOLD_mean_gross_weight':h['saved_float64_aggregate']['gross_weight_mean'],
                'nominal_tier_equality_is_not_equal_realized_risk':True,
                'return_difference_is_not_risk_matched_alpha':True})
    return result


def write_json(path: Path,value: Any) -> None:
    require(not path.exists(),'Refusing to overwrite saved artifact: '+str(path))
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def write_summary(output: Path,report: dict) -> None:
    lines=['Saved distinct-family annual risk / exposure / cost evidence','',
      'SAVED-ONLY ADAPTIVE DEVELOPMENT; NO HISTORICAL REPLAY OR NEW POLICY','',
      'Raw paid annual comparisons; fractions displayed as percentages. HOLD minus STATIC is descriptive and does not equal risk-matched alpha.']
    for p in report['paired_comparisons']:
        def pct(v):return 'unavailable' if v is None else f'{100*float(v):.6f}%'
        lines.append(f"{p['year']} {p['tier']}: STATIC {pct(p['STATIC50_paid_annual_return_fraction'])}, HOLD {pct(p['VOL_MANAGED_HOLD_paid_annual_return_fraction'])}, raw gap {pct(p['HOLD_minus_STATIC_paid_return_fraction'])}; daily vol {pct(p['STATIC50_daily_realized_annual_volatility'])}/{pct(p['VOL_MANAGED_HOLD_daily_realized_annual_volatility'])}; all-observation MDD {pct(p['STATIC50_all_observation_native_MDD_fraction'])}/{pct(p['VOL_MANAGED_HOLD_all_observation_native_MDD_fraction'])}.")
    lines+=['','Full annual cells (STATIC/HOLD, fixed order):']
    flat=[]
    for c in report['cells']:
        a=c['saved_float64_aggregate'];n=c['native_costs'];f=c['forecast_risk_approved_report']
        lines.append(f"{c['cell_id']}: mean/max gross {a['gross_weight_mean']:.9f}/{a['gross_weight_max']:.9f}; mean signed net {a['net_signed_weight_mean']:.9f}; flat {100*a['flat_actual_quantity_fraction']:.4f}%; fees {n['fees_USDT']}, execution {n['execution_price_cost_USDT']}, signed funding {n['signed_funding_USDT']} USDT; turnover {c['native_exact_paid_turnover_USDT']}; paid legs {c['native_paid_trade_legs']}; warning signals {c['native_paid_warning_signals']}; forecast overshoot minutes {f['forecast_budget_overshoot_minutes']}.")
        flat.append({'cell_id':c['cell_id'],'native_paid_annual_return_fraction':c['native_exact_paid_annual_return_fraction'],
          'daily_realized_annual_volatility':a['daily_realized_annual_volatility'],
          'all_observation_native_MDD_fraction':c['all_observation_native_MDD_fraction'],
          'minute_close_MDD_fraction':c['minute_close_MDD_fraction'],'daily_close_MDD_fraction':a['daily_close_MDD_fraction'],
          'mean_gross_weight':a['gross_weight_mean'],'max_gross_weight':a['gross_weight_max'],
          'mean_signed_net_weight':a['net_signed_weight_mean'],'flat_quantity_fraction':a['flat_actual_quantity_fraction'],
          'fees_USDT':n['fees_USDT'],'execution_price_cost_USDT':n['execution_price_cost_USDT'],
          'signed_funding_USDT':n['signed_funding_USDT'],'turnover_USDT':c['native_exact_paid_turnover_USDT'],
          'paid_trade_legs':c['native_paid_trade_legs'],'paid_warning_signals':c['native_paid_warning_signals'],
          'forecast_budget_overshoot_minutes':f['forecast_budget_overshoot_minutes'],
          'return_div_full_sample_vol':c['future_informed_descriptive_ratios']['paid_return_div_full_sample_daily_realized_annual_volatility'],
          'return_div_full_sample_mean_gross':c['future_informed_descriptive_ratios']['paid_return_div_full_sample_mean_gross_weight']})
    for filename,data in [('ANNUAL_CELLS.csv',flat),('PAIRED_COMPARISONS.csv',report['paired_comparisons'])]:
        with (output/filename).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    lines+=['','Qualifications:']+['- '+q for q in QUALIFICATIONS]
    (output/'REPORT.txt').write_text('\n'.join(lines)+'\n')


def final_run(workspace: Path,index_path: Path,output: Path,authorize: bool) -> dict:
    require(authorize,'Explicit saved-final CLI authorization required')
    base=workspace.resolve();index=json.loads(index_path.read_text())
    require(index.get('parent_authorized_saved_family_risk_final') is True,'Parent final saved-only authorization required')
    require(index.get('parent_commit')==PARENT_COMMIT,'Wrong verified publication parent')
    manifest=bound_json(base,index['frozen_manifest'])
    require(index['frozen_manifest']['SHA256']==MANIFEST_SHA256,'Wrong frozen manifest')
    comparison=bound_json(base,index['comparison'])
    compindex=bound_json(base,index['comparison_index'])
    require(compindex.get('parent_authorized_all17_terminal_saved_comparison') is True,'All17 terminal authorization missing')
    require(comparison.get('evidence_index_SHA256')==index['comparison_index']['SHA256'],'Comparison index binding mismatch')
    require(comparison['manifest']==index['frozen_manifest'],'Comparison frozen manifest binding mismatch')
    selected=validate_full_cohort(comparison,manifest)
    addendum=bound_json(base,index['exact_path_signatures_addendum'])
    require(addendum.get('original_comparison_unchanged')==index['comparison'],
            'Exact-path addendum binds another comparison')
    require(addendum.get('no_additional_independent_confirmation_claimed') is True,
            'Exact duplicates cannot count as independent confirmation')
    expected_pairs={(f'{y}_STATIC50_{t}',f'{y}_H090_{t}') for y in CALENDARS for t in TIERS}
    require(len(addendum.get('pairs',[]))==6 and
            {tuple(p['cell_ids']) for p in addendum['pairs']}==expected_pairs,
            'Exact six frozen H090/STATIC duplicate groups required')
    duplicate_proofs=[]
    for pair in addendum['pairs']:
        proof=bound_json(base,pair['exact_path_proof'])
        require(proof.get('status')=='PASS_EXACT_SAME_REALIZED_FINANCIAL_PATH' and
                proof.get('full37column_minute_matrix_byte_identical') is True,
                'Complete exact duplicate proof required')
        require(proof.get('same_financial_fields') and all(proof['same_financial_fields'].values()),
                'Duplicate exact financial fields incomplete')
        require(proof.get('policy_journals_exact') and all(proof['policy_journals_exact'].values()),
                'Duplicate exact policy journals incomplete')
        duplicate_proofs.append({'reference':pair['exact_path_proof'],'value':proof})
    canonical_duplicate_evidence=bound_json(base,addendum['independent_canonical_projection_and_arrays_evidence'])
    require(not output.exists(),'New immutable output directory required')
    output.mkdir(parents=True)
    cells=[analyze_saved_cell(base,r,output/'cells'/r['cell_id']) for r in selected]
    cell_lookup={c['cell_id']:c for c in cells}
    for pair in addendum['pairs']:
        c=cell_lookup[pair['cell_ids'][0]]
        arrays=pair['exact_signature']['descriptor']['canonical_output_arrays_in_role_order']
        value_sig=next(a for a in arrays if a['role']=='values')
        require(c['MINUTE_original']['signature']['values_C_order_SHA256']==value_sig['raw_C_SHA256'],
                'Independent STATIC duplicate signature differs from saved output')
    report={'schema':SCHEMA,'status':'COMPLETE_SAVED_ONLY_AWAITING_INDEPENDENT_MODULE_REVIEW',
      'parent_commit':PARENT_COMMIT,'created_UTC':datetime.now(timezone.utc).isoformat(),
      'input_index_SHA256':file_sha(index_path),'input_index':index,
      'analysis_cell_count':12,'matched_pair_count':6,'cohort_cell_count':18,
      'original_18row_comparison_preserved':'ORIGINAL_18ROW_COMPARISON.json',
      'all_six_H090_STATIC_exact_duplicate_groups_preserved':'EXACT_DUPLICATE_EVIDENCE.json',
      'duplicate_paths_counted_as_independent_confirmation':False,
      'cells':cells,'paired_comparisons':paired_rows(cells),'qualifications':QUALIFICATIONS,
      'source_code_SHA256':file_sha(Path(__file__)),
      'actions':{'saved_MINUTE_archives_read':12,'new_accounts':0,'financial_replays':0,
       'raw_market_or_holdout_reads':0,'covariance_reads':0,'retuning':0,'new_causal_rules':0,
       'financial_code_or_policy_edits':0,'publication_actions':0}}
    write_json(output/'ORIGINAL_18ROW_COMPARISON.json',comparison)
    write_json(output/'INPUT_INDEX.json',index)
    write_json(output/'EXACT_DUPLICATE_EVIDENCE.json',{'addendum':addendum,
      'exact_path_proofs':duplicate_proofs,'independent_canonical_projection_and_arrays_evidence':canonical_duplicate_evidence})
    write_json(output/'RISK_EVIDENCE.json',report)
    write_summary(output,report)
    files={str(p.relative_to(output)):{'SHA256':file_sha(p),'bytes':p.stat().st_size}
           for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output/'COMPACT_ARTIFACT_MANIFEST.json',{'schema':'COMPACT_SAVED_RISK_FILES_V1',
      'files':files,'original_MINUTE_archives_included':False,
      'public_daily_recompute':'python saved_family_risk.py --recompute-compact DIRECTORY',
      'all_minute_deepcheck_requires_hash_pinned_omitted_originals':True})
    return report


def recompute_compact(directory: Path) -> dict:
    manifest=json.loads((directory/'COMPACT_ARTIFACT_MANIFEST.json').read_text())
    for path,info in manifest['files'].items():
        require(file_sha(relative_path(directory,path))==info['SHA256'],'Compact evidence file hash mismatch')
    report=json.loads((directory/'RISK_EVIDENCE.json').read_text())
    for c in report['cells']:
        p=directory/'cells'/c['cell_id']/'DAILY.npz'
        require(file_sha(p)==c['DAILY']['SHA256'],'Daily archive binding mismatch')
        with np.load(p,allow_pickle=False) as z:
            a=z['values'];columns=z['columns']
        require(canonical_array_signature(a,columns,['values','columns'])==c['DAILY']['signature'],
                'Daily canonical signature mismatch')
        agg=aggregate_daily(a,columns)
        require(agg==c['saved_float64_aggregate'],'Daily-to-annual aggregate mismatch')
        r=c['authoritative_reviewed_matrix_row']
        require(c['native_costs']==cost_diagnostic(r['fees_USDT'],r['execution_cost_USDT'],r['signed_funding_USDT']),
                'Native cost description recompute mismatch')
        paid=c['native_exact_paid_annual_return_fraction']
        if paid is not None:
            require(finite_decimal(paid)==Decimal(exact_annual_return(c['native_exact_terminal_NAV_USDT'])),
                    'Native annual return recompute mismatch')
            ratios=c['future_informed_descriptive_ratios']
            require(ratios['paid_return_div_full_sample_daily_realized_annual_volatility']==
                    ratio_diagnostic(paid,agg['daily_realized_annual_volatility']),
                    'Descriptive full-sample vol ratio mismatch')
            require(ratios['paid_return_div_full_sample_mean_gross_weight']==
                    ratio_diagnostic(paid,agg['gross_weight_mean']),
                    'Descriptive full-sample gross ratio mismatch')
    require(paired_rows(report['cells'])==report['paired_comparisons'],'Paired comparison recompute mismatch')
    return {'status':'PASS_PUBLIC_DAILY_AGGREGATE_AND_PAIR_RECOMPUTATION','cells':12,'pairs':6,
            'all_minute_deepcheck_performed':False,'native40_ledger_reconstruction_performed':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path);p.add_argument('--index',type=Path)
    p.add_argument('--output',type=Path);p.add_argument('--authorize-saved-final',action='store_true')
    p.add_argument('--recompute-compact',type=Path)
    args=p.parse_args()
    if args.recompute_compact:
        require(not any((args.workspace,args.index,args.output,args.authorize_saved_final)),
                'Choose compact recompute or final derivation')
        print(json.dumps(recompute_compact(args.recompute_compact),sort_keys=True));return
    require(all((args.workspace,args.index,args.output)),'workspace,index,output required')
    r=final_run(args.workspace,args.index,args.output,args.authorize_saved_final)
    print(json.dumps({'status':r['status'],'cells':12,'pairs':6,'output':str(args.output)},sort_keys=True))

if __name__=='__main__':main()
