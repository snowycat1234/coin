"""Post-hoc same-tier SAVED financial equality; never an execution alias."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{6})
import sys,json
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;MODULE=ROOT/'traditional_D_partial2021_20261015'
sys.path.insert(0,str(MODULE))
import numpy as np
import partial_entry as e
import run_partial as runner
ACTUAL=MODULE/'actual_nine_attempt001'
def load(path):return json.loads(Path(path).read_bytes())
def pin(path):
    raw=Path(path).read_bytes();return dict(SHA256=sha256(raw).hexdigest(),bytes=len(raw))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def jsha(v):return sha256(canonical(v)).hexdigest()
def normalized_audit(value):
    value=deepcopy(value);value.pop('historical_execution_scope');value['contract'].pop('scope_binding');value.pop('fill_requests')
    return value
def normalized_summary(value):
    value=deepcopy(value);value['contract'].pop('scope_binding');return value
def normalized_request(value):
    value=deepcopy(value);value['identity'].pop('quantity')
    receipt=value['receipt']
    for key in ('requested_quantity','remaining_quantity'):receipt.pop(key,None)
    for key in ('requested_quantity','remaining_quantity'):receipt.get('decimal_strings',{}).pop(key,None)
    return value
pairs=[]
for tier in ('LOW','MID','HIGH'):
    static='2021_STATIC50_'+tier+'_APR2_DEC31_D';h090='2021_H090_'+tier+'_APR2_DEC31_D'
    left,right=ACTUAL/static,ACTUAL/h090
    for cell in (static,h090):
        r=load(OUT/(cell+'_SAVED_REVIEW.json'));assert r['status']=='PASS_SAVED_ONLY_NO_FINANCIAL_RERUN'
        assert r['terminal_checkpoint']==pin(ACTUAL/cell/'TERMINAL_CHECKPOINT.json')
    a,b=load(left/'ACCOUNT_FINANCIAL_AUDIT.json'),load(right/'ACCOUNT_FINANCIAL_AUDIT.json')
    ar,br=load(left/'NATIVE_RESULT.json'),load(right/'NATIVE_RESULT.json')
    fa,fb=normalized_audit(a),normalized_audit(b)
    assert fa==fb,tier
    differing_audit_keys=[key for key in a if a[key]!=b[key]]
    assert differing_audit_keys==['contract','fill_requests','historical_execution_scope']
    assert set(a['fill_requests'])==set(b['fill_requests'])
    request_differences=[key for key,value in a['fill_requests'].items() if value!=b['fill_requests'][key]]
    assert request_differences
    for key in a['fill_requests']:assert normalized_request(a['fill_requests'][key])==normalized_request(b['fill_requests'][key])
    fields=('trades','funding','financial_ledger','monitor_journal','settlement_journal','positions','marks','totals',
        'operation_ids','pending_exits','blocked_signals','noop_receipts','noop_rolling_SHA256','mode_journal','capacity_used','capacity_registrations')
    exact_financial_fields={key:jsha(a[key])==jsha(b[key]) for key in fields}
    assert all(exact_financial_fields.values())
    with np.load(left/'MINUTE.npz',allow_pickle=False) as z:
        av=z['values'];ac=z['columns'];av_sha=sha256(av.tobytes()).hexdigest();ac_sha=sha256(ac.tobytes()).hexdigest();shape=list(av.shape)
    with np.load(right/'MINUTE.npz',allow_pickle=False) as z:
        bv=z['values'];bc=z['columns'];bv_sha=sha256(bv.tobytes()).hexdigest();bc_sha=sha256(bc.tobytes()).hexdigest()
        assert av.dtype==bv.dtype and av.shape==bv.shape and av.tobytes()==bv.tobytes()
        assert ac.dtype==bc.dtype and ac.shape==bc.shape and ac.tobytes()==bc.tobytes()
    assert ar['economics']==br['economics']
    assert normalized_summary(ar['summary'])==normalized_summary(br['summary'])
    assert ar['trades']==br['trades'] and ar['funding']==br['funding']
    assert normalized_summary(ar['continuation_economic_report'])==normalized_summary(br['continuation_economic_report'])
    saved_risk_left=load(left/'ACTUAL_HELD_RISK_REPORT.json');saved_risk_right=load(right/'ACTUAL_HELD_RISK_REPORT.json')
    # Target shortfall diagnostics can differ even with the exact same held
    # financial path, because original raw target bytes are genuinely distinct.
    risk_differences=[key for key in saved_risk_left if saved_risk_left[key]!=saved_risk_right[key]]
    with np.load(MODULE/'source_preparation_final/2021/TARGETS.npz',allow_pickle=False) as z:
        st=z['STATIC50_'+tier];ht=z['H090_'+tier]
        assert st.tobytes()!=ht.tobytes()
        raw_target_differences=int(np.count_nonzero(st!=ht));raw_target_decision_differences=int(np.count_nonzero(np.any(st!=ht,axis=1)))
        raw_st_sha=sha256(st.tobytes()).hexdigest();raw_ht_sha=sha256(ht.tobytes()).hexdigest()
    pairs.append(dict(tier=tier,STATIC50_cell=static,H090_cell=h090,both_separately_executed=True,
        full_saved_financial_audit_exact_except_scope_metadata=False,
        full_audit_differing_top_level_fields=differing_audit_keys,
        realized_financial_state_and_history_exact_after_excluding_scope_metadata_and_request_intents=True,
        excluded_scope_metadata_paths=['historical_execution_scope','contract.scope_binding'],
        distinct_request_intent_log_retained=True,different_fill_request_records=len(request_differences),
        fill_request_keys_clocks_prices_capacity_status_reasons_actual_executed_quantities_and_fills_exact=True,
        fill_request_only_differing_fields=['identity.quantity','receipt.requested_quantity','receipt.remaining_quantity',
            'receipt.decimal_strings.requested_quantity','receipt.decimal_strings.remaining_quantity'],
        STATIC50_fill_requests_canonical_SHA256=jsha(a['fill_requests']),H090_fill_requests_canonical_SHA256=jsha(b['fill_requests']),
        normalized_realized_financial_state_and_history_SHA256=jsha(fa),financial_field_equalities=exact_financial_fields,
        decompressed_minute_values_byte_exact=True,minute_values_dtype=str(av.dtype),minute_values_shape=shape,
        minute_values_raw_SHA256=av_sha,minute_columns_raw_SHA256=ac_sha,minute_columns_byte_exact=True,
        result_economics_exact=True,result_summary_exact_except_contract_scope_binding=True,
        result_trades_and_funding_exact=True,continuation_economic_report_exact_except_contract_scope_binding=True,
        raw_target_paths_byte_exact=False,STATIC50_target_raw_SHA256=raw_st_sha,H090_target_raw_SHA256=raw_ht_sha,
        different_raw_target_float64_cells=raw_target_differences,different_raw_target_decision_dates=raw_target_decision_differences,
        guard_receipt_files_byte_exact=pin(left/'GUARD_RECEIPTS.json')['SHA256']==pin(right/'GUARD_RECEIPTS.json')['SHA256'],
        saved_risk_report_differing_fields=risk_differences,
        interpretation='POST_HOC_REALIZED_FINANCIAL_MINUTE_PATH_DUPLICATE_WITH_DISTINCT_REQUEST_INTENTS_NOT_INDEPENDENT_EVIDENCE_OR_EXECUTION_REUSE_AUTHORITY',
        alias_created=False,root_GO_or_scope_modified=False,source_target_pins_unchanged=True,
        left_evidence={name:pin(left/name) for name in ('ACCOUNT_FINANCIAL_AUDIT.json','MINUTE.npz','NATIVE_RESULT.json','TERMINAL_CHECKPOINT.json')},
        right_evidence={name:pin(right/name) for name in ('ACCOUNT_FINANCIAL_AUDIT.json','MINUTE.npz','NATIVE_RESULT.json','TERMINAL_CHECKPOINT.json')}))
record=dict(schema='POST_HOC_PARTIAL2021_STATIC50_H090_SAVED_FINANCIAL_PATH_EQUALITY_V1',status='PASS_THREE_SAME_TIER_REALIZED_PATH_DUPLICATES_WITH_DISTINCT_REQUEST_INTENTS',
    root_GO_SHA256='79dfb608da4e423833df12f1e512a26ff5610ae2f7ea03d41c9e62e1a2a555f8',
    source_generated_review_SHA256='5cd2fcc60a565a91866a0ddfbce1bd41e643f97d46aaddf17601e049815e6404',
    approved_nine_cells_all_retained=True,execution_aliases_created=0,nominal_evidence_is_not_nine_independent_paths=True,
    post_hoc_only=True,financial_reruns=0,account_constructions=0,provider_iterations=0,process_launches=0,GO_edits=0,
    future_execution_reuse_authorized=False,CPU_affinity=[6],pairs=pairs,review_script=pin(__file__))
path=OUT/'STATIC50_H090_POST_HOC_SAVED_EQUALITY.json'
with path.open('xb') as stream:stream.write(runner.body(record));stream.flush();os.fsync(stream.fileno())
print(str(path));print(pin(path)['SHA256'])
