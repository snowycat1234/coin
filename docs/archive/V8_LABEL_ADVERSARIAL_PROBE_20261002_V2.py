from __future__ import annotations
import hashlib, json, subprocess, sys
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state/test-v8-adversarial-20261002-v2')
sys.path.insert(0, str(ROOT/'scripts/research_v8'))
import numpy as np
import polars as pl
import labels_v2 as v8

FILES=['protocols/LABEL_CONTRACT_V8.json','scripts/research_v8/labels_v2.py','tests/test_v8_label_contract_v2.py',
       'scripts/research_v8/labels.py','tests/test_v8_label_contract.py','environments/v8/uv.lock']
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
start_sha={p:sha(ROOT/p) for p in FILES}
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
v1_audit_path=ROOT/'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V1.json'
v1_audit_sha=sha(v1_audit_path)
assert start_sha['protocols/LABEL_CONTRACT_V8.json']=='4de017bc8528f0b264318f309c83acc0267eb8b5de2ca894746da0965e474d47'
base=v8.day_us(date(2025,7,1))
n=1000
times=base+np.arange(n,dtype=np.int64)*v8.BAR_US
rows={'timestamp':times}
for i,s in enumerate(v8.STREAMS):
    rows.update({s+'__available_us':times+v8.BAR_US,s+'__quality':np.zeros(n,dtype=np.int32),
      s+'__aggressive_buy_notional':np.full(n,100.+i),s+'__aggressive_sell_notional':np.full(n,80.+i),
      s+'__close':100.+i*10+np.arange(n)*.01,s+'__last_trade_us':times+v8.BAR_US-1_000_000})
joint=pl.DataFrame(rows)
decisions=base+np.asarray([1800,1860],dtype=np.int64)*v8.US
d=int(decisions[0]); stream=v8.STREAMS[0]
probes=[]; regressions=[]; findings=[]

def attempted(fn):
    try:
        result=fn()
        return {'accepted':True,'exception':None}
    except Exception as exc:
        return {'accepted':False,'exception_type':type(exc).__name__,'exception':str(exc)}

def old_case(case_id,passed,evidence):
    regressions.append({'original_finding_id':case_id,'status':'FIXED_IN_THIS_PROBE' if passed else 'STILL_FAILING', 'evidence':evidence})
    if not passed:
        findings.append({'id':case_id+'-V2','priority':'P1','status':'CONFIRMED_REGRESSION_FAILURE','evidence':evidence})

for variant in v8.contract()['labels']:
    labels=v8.label_table(joint,decisions,variant)
    probes.append({'id':'control_exact_'+variant,'all_valid':bool(labels['label_valid'].all()),
                   'maturity_lag_us':(labels['label_mature_us'].to_numpy()-decisions).tolist()})

late=d+2000*v8.US
late_joint=joint.with_columns(pl.when(pl.col('timestamp')==d+150*v8.US).then(late)
    .otherwise(pl.col(stream+'__available_us')).alias(stream+'__available_us'))
late_labels=v8.label_table(late_joint,decisions[:1],'EARLY_LATE_150S_GAP10')
e={'id':'repeat_v1_gap10_delayed_quality','label_valid':bool(late_labels['label_valid'][0]),
   'label_mature_us':float(late_labels['label_mature_us'][0]),'required_minimum_us':late,
   'validity_mature_us':float(late_labels['validity_mature_us'][0])}
probes.append(e);old_case('V8A-01',e['label_valid'] and e['label_mature_us']>=late,e)

labels10=v8.label_table(joint,decisions[:1],'EARLY_LATE_150S_GAP10')
bad_gap=labels10.with_columns((pl.col('flow_label_end_us')+5*v8.US).alias('return_label_start_us'),
   (pl.col('flow_label_end_us')+5*v8.US).alias('delayed_entry_us'),
   (pl.col('return_label_end_us')-5*v8.US).alias('return_label_end_us'))
e={'id':'repeat_v1_gap10_contracted_to_gap5','frame_guard':attempted(lambda:v8.assert_nonoverlap(bad_gap)),
   'direct_selector':attempted(lambda:v8.direct_return_labels(bad_gap))}
probes.append(e);old_case('V8A-02',not e['frame_guard']['accepted'] and not e['direct_selector']['accepted'],e)

observed=v8.label_table(joint,decisions[:1],signal_kind='OBSERVED_FUTURE_FLOW_DIAGNOSTIC')
bad_signal=observed.with_columns(pl.col('decision_us').alias('signal_available_us'),
    (pl.col('decision_us')+5*v8.US).alias('earliest_order_us'),
    (pl.col('decision_us')+5*v8.US).alias('earliest_permissible_order_us'))
e={'id':'repeat_v1_observed_future_signal_falsely_early','frame_guard':attempted(lambda:v8.assert_nonoverlap(bad_signal)),
   'direct_selector':attempted(lambda:v8.direct_return_labels(bad_signal))}
probes.append(e);old_case('V8A-03',not e['frame_guard']['accepted'] and not e['direct_selector']['accepted'],e)

control=v8.label_table(joint,decisions)
missing=joint.with_columns(pl.when(pl.col('timestamp')==d+5*v8.US).then(float('nan'))
    .otherwise(pl.col(stream+'__aggressive_buy_notional')).alias(stream+'__aggressive_buy_notional'))
missing_out=v8.label_table(missing,decisions)
e={'id':'repeat_v1_missing_future_notional','label_valid':missing_out['label_valid'].to_list(),
  'first_all_targets_nan':all(np.isnan(missing_out[c][0]) for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS)),
  'second_targets_exactly_unchanged':all(missing_out[c][1]==control[c][1] for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS))}
probes.append(e);old_case('V8A-04',e['label_valid']==[False,True] and e['first_all_targets_nan'] and e['second_targets_exactly_unchanged'],e)

frames=[v8.label_table(joint,np.asarray([base+t*v8.US]),split=split)
    for t,split in ((1320,'TRAIN'),(3000,'VALIDATION'),(4200,'OOS_SCREENING'))]
split_frame=pl.concat(frames)
args=dict(train_ids=[base+1320*v8.US],validation_ids=[base+3000*v8.US],test_ids=[base+4200*v8.US],
          fit_cutoff_us=base+2100*v8.US,validation_start_us=base+3000*v8.US,
          test_start_us=base+4200*v8.US,test_end_us=base+4900*v8.US,embargo_us=100*v8.US,max_label_lag_us=600*v8.US)
normal_receipt=v8.assert_split_chronology(split_frame,**args)
validation_equal=attempted(lambda:v8.assert_split_chronology(split_frame,**{**args,
    'test_start_us':float(split_frame['label_mature_us'][1])+args['embargo_us']}))
small_lag=attempted(lambda:v8.assert_split_chronology(split_frame,**{**args,'max_label_lag_us':599*v8.US}))
e={'id':'repeat_v1_full_split_gap','normal_receipt':normal_receipt,
   'validation_maturity_at_test_minus_embargo':validation_equal,'declared_lag_below_actual':small_lag}
probes.append(e);old_case('V8A-05',not validation_equal['accepted'] and not small_lag['accepted'],e)

# Purely synthetic shift; no locked dataset is read or generated from market data.
locked_shift=v8.day_us(v8.LOCKED)-base
locked_source=joint.with_columns((pl.col('timestamp')+locked_shift).alias('timestamp'))
locked_source_result=attempted(lambda:v8.label_table(locked_source,decisions+locked_shift))
shifted=split_frame.with_columns(*[(pl.col(c)+locked_shift).alias(c) for c in split_frame.columns if c.endswith('_us')])
shift_args={k:([x+locked_shift for x in value] if k in ('train_ids','validation_ids','test_ids')
               else value+locked_shift if k in ('fit_cutoff_us','validation_start_us','test_start_us','test_end_us')
               else value) for k,value in args.items()}
e={'id':'locked_date_exported_frame_and_split','source_builder':locked_source_result,
   'frame_guard':attempted(lambda:v8.assert_nonoverlap(shifted)),
   'split_guard':attempted(lambda:v8.assert_split_chronology(shifted,**shift_args)),
   'locked_start_us':v8.day_us(v8.LOCKED),'accepted_decision_us':shifted['decision_us'].to_list(),
   'market_data_read':False}
probes.append(e)
if e['frame_guard']['accepted'] or e['split_guard']['accepted']:
    findings.append({'id':'V8B-01','priority':'P1','status':'CONFIRMED',
      'title':'Exported-frame and full split guards accept locked-date labels',
      'source':'scripts/research_v8/labels_v2.py','source_lines':[138,217,221],
      'contract_fields':['qualification.locked_holdout_allowed','split','AGENTS development/locked boundary'],
      'evidence_probe':e['id'],
      'impact':'Shifting every synthetic timestamp and split boundary into dates at/after LOCKED passes both public frame and full split validators. label_table rejects an actual source grid at those dates, but its exported/scored-fit receipt path does not retain that development/locked boundary. No real locked observations were read; this is an accepted forbidden-date metadata path.',
      'required_fix':'Require valid development decision/observation endpoints and price trade timestamps in exported-frame and split validation, preserving the exact allowed pre-LOCKED endpoint convention. Reject any scored/fitting receipt that uses locked observation dates.'})

# Metadata alignment must reject broadcasting of one decision across two labels.
e={'id':'standalone_fit_lag_broadcast','fitting_maturity_us':[base+2300*v8.US,base+1980*v8.US],
   'supplied_fitting_decision_us':[base+1380*v8.US],
   'hypothetical_aligned_fitting_decision_us':[base+1320*v8.US,base+1380*v8.US],
   'declared_lag_us':920*v8.US,'true_aligned_maximum_lag_us':980*v8.US}
e['guard']=attempted(lambda:v8.assert_fit_chronology(fit_cutoff_us=base+2450*v8.US,
    validation_start_us=base+3400*v8.US,embargo_us=0,max_label_lag_us=e['declared_lag_us'],
    fitting_label_mature_us=e['fitting_maturity_us'],fitting_decision_us=e['supplied_fitting_decision_us']))
probes.append(e)
if e['guard']['accepted']:
    findings.append({'id':'V8B-02','priority':'P2','status':'CONFIRMED',
      'title':'Standalone fit chronology helper silently broadcasts mismatched row metadata',
      'source':'scripts/research_v8/labels_v2.py','source_lines':[208,210,211,212],
      'contract_fields':['split'], 'evidence_probe':e['id'],
      'impact':'Two fitting label maturities and one fitting decision pass because NumPy broadcasts the single decision. Declared lag 920s is accepted, although the aligned example has actual max lag 980s and fit cutoff 2450s would violate the true validation boundary. The full-frame split validator constructs aligned arrays internally; this defect is in the public standalone helper.',
      'required_fix':'Require one-dimensional finite integer timestamp arrays with equal nonzero lengths before subtracting; reject any broadcasting or row alignment ambiguity.'})

# Numeric timestamps outside the declared integer-microsecond domain.
fractional_input=np.asarray([d+0.5],dtype=np.float64)
fractional_labels=v8.label_table(joint,fractional_input)
e={'id':'fractional_decision_silently_coerced','input_decision_us':float(fractional_input[0]),
   'returned_decision_us':int(fractional_labels['decision_us'][0]),'accepted':True}
probes.append(e)
if e['input_decision_us']!=e['returned_decision_us']:
    findings.append({'id':'V8B-03','priority':'P2','status':'CONFIRMED',
      'title':'Fractional decision timestamps are silently changed before validation',
      'source':'scripts/research_v8/labels_v2.py','source_lines':[57,58,59],
      'contract_fields':['timestamp_unit','decision_frequency_seconds'], 'evidence_probe':e['id'],
      'impact':'Input decision+0.5 microsecond is silently cast to the exact minute decision and accepted. The integer UTC microsecond/minute-grid contract requires rejecting malformed decision timestamps, not rounding them into a different endpoint ID.',
      'required_fix':'Validate the original decision array type, dimensionality, finite integer values and exact minute grid before int64 conversion. Apply an equivalent integer-domain policy to known source availability/trade timestamps.'})

bad_flow=split_frame.with_columns(pl.lit(100.).alias(v8.FLOW_COLUMNS[0]))
e={'id':'impossible_flow_ratio_exported_frame','injected_flow_value':100.,
   'frame_guard':attempted(lambda:v8.assert_nonoverlap(bad_flow)),
   'split_guard':attempted(lambda:v8.assert_split_chronology(bad_flow,**args))}
probes.append(e)
if e['frame_guard']['accepted'] or e['split_guard']['accepted']:
    findings.append({'id':'V8B-04','priority':'P2','status':'CONFIRMED',
      'title':'Exported/scored-flow frames accept ratios outside original flow units',
      'source':'scripts/research_v8/labels_v2.py','source_lines':[159,160,162,217,221],
      'contract_fields':['flow_units','FLOW_SURPRISE.assertions'], 'evidence_probe':e['id'],
      'impact':'The source builder rejects flow values outside [-1,1], but both exported-frame and scored split guards accept future flow=100 with label_valid=true. That cannot equal a signed nonnegative-notional ratio and can conceal a bps/unit conversion or target corruption before fitting.',
      'required_fix':'For any present valid future-flow columns, enforce the original ratio bounds with the same registered numerical tolerance used by label generation.'})

# Known original OOF/scaler chronology protections remain intact.
r=v8.OOFPredictionReceipt((10,11),(1000,1100),(1000,1100),(0,1,2),(500,600,650),700,100,'a'*64)
r.validate()
probes.append({'id':'control_oof_scaler','fitted_forecast_id':attempted(lambda:replace(r,fit_row_ids=(0,1,10)).validate()),
 'future_scaler_source':attempted(lambda:v8.fit_train_scaler(np.asarray([[1.,2.],[2.,3.]]),[0,1],[0,1],[700,701],700))})

end_sha={p:sha(ROOT/p) for p in FILES}
assert start_sha==end_sha,'Audited bytes changed during probe'
assert v1_audit_sha==sha(v1_audit_path),'V1 audit artifact changed during probe'
assert head==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'HEAD changed during probe'
raw={'git_HEAD':head,'sources_sha256':start_sha,'source_unchanged':True,'v1_regression_results':regressions,'probes':probes,'findings':findings}
raw_path=STATE/'probes.json'
raw_path.write_text(json.dumps(raw,indent=2)+'\n')
print(json.dumps({'probe_output':str(raw_path),'source_unchanged':True,'v1_regressions_all_fixed':all(r['status']=='FIXED_IN_THIS_PROBE' for r in regressions),
 'findings':[{k:f[k] for k in ('id','priority','title')} for f in findings]}))