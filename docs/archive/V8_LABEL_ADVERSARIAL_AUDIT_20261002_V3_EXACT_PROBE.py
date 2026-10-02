from __future__ import annotations
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date,datetime,timezone
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-adversarial-20261002-v3')
sys.path.insert(0,str(root/'scripts/research_v8'))
import numpy as np
import polars as pl
import labels_v3 as v8
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['protocols/LABEL_CONTRACT_V8.json','scripts/research_v8/labels.py','scripts/research_v8/labels_v2.py','scripts/research_v8/labels_v3.py',
 'tests/test_v8_label_contract.py','tests/test_v8_label_contract_v2.py','tests/test_v8_label_contract_v3.py','environments/v8/uv.lock']
start_sha={p:sha(root/p) for p in files}
head_start=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if start_sha['protocols/LABEL_CONTRACT_V8.json']!='4de017bc8528f0b264318f309c83acc0267eb8b5de2ca894746da0965e474d47':raise RuntimeError('Contract changed')
base=v8.BEGIN;n=1000;index=np.arange(n,dtype=np.int64);times=base+index*v8.BAR_US
rows={'timestamp':times}
for i,s in enumerate(v8.STREAMS):
    price=100.+10*i+index*.01
    rows.update({s+'__available_us':times+v8.BAR_US,s+'__quality':np.zeros(n,dtype=np.int32),
      s+'__aggressive_buy_notional':np.full(n,100.+i),s+'__aggressive_sell_notional':np.full(n,80.+i),
      s+'__close':price,s+'__last_trade_us':times+v8.BAR_US-1_000_000,
      s+'__open':price-.002,s+'__vwap':price-.001,s+'__high':price+.01,s+'__low':price-.01,
      s+'__empty_bin':np.zeros(n,dtype=bool),s+'__return_5s':np.full(n,.0001),s+'__flow_imbalance':np.full(n,.1),
      s+'__large_trade_share':np.full(n,.2),s+'__signed_price_impact':np.full(n,.01),s+'__interarrival_count':np.full(n,10)})
    for field in ('quote_notional','base_volume','trade_count','agg_count','mean_trade_size','max_trade_size','mean_interarrival','std_interarrival'):
        rows[s+'__'+field]=np.full(n,10.+i)
joint=pl.DataFrame(rows);decisions=base+np.asarray([1800,1860],dtype=np.int64)*v8.US;d=int(decisions[0]);s=v8.STREAMS[0]
probes=[];regressions=[];findings=[]
def call(fn):
    try:
        result=fn();return {'accepted':True},result
    except Exception as exc:
        return {'accepted':False,'exception_type':type(exc).__name__,'exception':str(exc)},None

def previous(case_id,passed,evidence):
    regressions.append({'original_finding_id':case_id,'status':'FIXED_IN_THIS_PROBE' if passed else 'STILL_FAILING','evidence':evidence})
    if not passed:findings.append({'id':case_id+'-V3','priority':'P1','status':'CONFIRMED_REGRESSION_FAILURE','evidence':evidence})

for variant,spec in v8.contract()['labels'].items():
    output=v8.label_table(joint,decisions,variant)
    probes.append({'id':'control_exact_'+variant,'all_valid':bool(output['label_valid'].all()),
       'integer_export_schema':all(dtype==pl.Int64 for name,dtype in output.schema.items() if name.endswith('_us')),
       'maturity_lag_us':(output['label_mature_us'].to_numpy()-decisions).tolist(),
       'direct_targets_identical':all(v8.direct_return_labels(output)[c].equals(output[c]) for c in v8.RETURN_COLUMNS)})

late=d+2000*v8.US
changed=joint.with_columns(pl.when(pl.col('timestamp')==d+150*v8.US).then(late).otherwise(pl.col(s+'__available_us')).alias(s+'__available_us'))
output=v8.label_table(changed,decisions[:1],'EARLY_LATE_150S_GAP10')
e={'id':'repeat_gap10_quality_maturity','label_valid':bool(output['label_valid'][0]),'maturity_us':int(output['label_mature_us'][0]),'required_minimum_us':late}
probes.append(e);previous('V8A-01',e['label_valid'] and e['maturity_us']>=late,e)
output=v8.label_table(joint,decisions[:1],'EARLY_LATE_150S_GAP10')
mutated=output.with_columns((pl.col('flow_label_end_us')+5*v8.US).alias('return_label_start_us'),
 (pl.col('flow_label_end_us')+5*v8.US).alias('delayed_entry_us'),(pl.col('return_label_end_us')-5*v8.US).alias('return_label_end_us'))
a,_=call(lambda:v8.assert_nonoverlap(mutated));b,_=call(lambda:v8.direct_return_labels(mutated))
e={'id':'repeat_gap10_contraction','frame_guard':a,'direct_guard':b};probes.append(e);previous('V8A-02',not a['accepted'] and not b['accepted'],e)
output=v8.label_table(joint,decisions[:1],signal_kind='OBSERVED_FUTURE_FLOW_DIAGNOSTIC')
mutated=output.with_columns(pl.col('decision_us').alias('signal_available_us'),
 (pl.col('decision_us')+5*v8.US).alias('earliest_order_us'),(pl.col('decision_us')+5*v8.US).alias('earliest_permissible_order_us'))
a,_=call(lambda:v8.assert_nonoverlap(mutated));b,_=call(lambda:v8.direct_return_labels(mutated))
e={'id':'repeat_observed_signal_early','frame_guard':a,'direct_guard':b};probes.append(e);previous('V8A-03',not a['accepted'] and not b['accepted'],e)
control=v8.label_table(joint,decisions)
changed=joint.with_columns(pl.when(pl.col('timestamp')==d+5*v8.US).then(float('nan')).otherwise(pl.col(s+'__aggressive_buy_notional')).alias(s+'__aggressive_buy_notional'))
output=v8.label_table(changed,decisions)
e={'id':'repeat_missing_future_notional','valid':output['label_valid'].to_list(),
 'first_all_targets_nan':all(np.isnan(output[c][0]) for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS)),
 'second_targets_exactly_unchanged':all(output[c][1]==control[c][1] for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS))}
probes.append(e);previous('V8A-04',e['valid']==[False,True] and e['first_all_targets_nan'] and e['second_targets_exactly_unchanged'],e)

frame=pl.concat([v8.label_table(joint,np.asarray([base+t*v8.US]),split=split)
 for t,split in ((1320,'TRAIN'),(3000,'VALIDATION'),(4200,'OOS_SCREENING'))])
args=dict(train_ids=[base+1320*v8.US],validation_ids=[base+3000*v8.US],test_ids=[base+4200*v8.US],fit_cutoff_us=base+2100*v8.US,
 validation_start_us=base+3000*v8.US,test_start_us=base+4200*v8.US,test_end_us=base+4900*v8.US,embargo_us=100*v8.US,max_label_lag_us=600*v8.US)
good_receipt=v8.assert_split_chronology(frame,**args)
a,_=call(lambda:v8.assert_split_chronology(frame,**{**args,'max_label_lag_us':599*v8.US}))
b,_=call(lambda:v8.assert_split_chronology(frame,**{**args,'test_start_us':int(frame['label_mature_us'][1])+args['embargo_us']}))
e={'id':'repeat_full_split_boundaries','control_receipt':good_receipt,'lag_below_actual':a,'validation_maturity_at_boundary':b}
probes.append(e);previous('V8A-05',not a['accepted'] and not b['accepted'],e)
shift=v8.END-base
shifted=frame.with_columns(*[(pl.col(c)+shift).alias(c) for c in frame.columns if c.endswith('_us')])
shift_args={k:([x+shift for x in val] if k in ('train_ids','validation_ids','test_ids') else val+shift if k in ('fit_cutoff_us','validation_start_us','test_start_us','test_end_us') else val) for k,val in args.items()}
a,_=call(lambda:v8.assert_nonoverlap(shifted));b,_=call(lambda:v8.assert_split_chronology(shifted,**shift_args));c,_=call(lambda:v8.direct_return_labels(shifted))
e={'id':'repeat_locked_export_and_split','frame_guard':a,'split_guard':b,'direct_guard':c,'synthetic_metadata_only':True}
probes.append(e);previous('V8B-01',not a['accepted'] and not b['accepted'] and not c['accepted'],e)
a,_=call(lambda:v8.assert_fit_chronology(fit_cutoff_us=base+2450*v8.US,validation_start_us=base+3400*v8.US,embargo_us=0,
 max_label_lag_us=920*v8.US,fitting_label_mature_us=[base+2300*v8.US,base+1980*v8.US],fitting_decision_us=[base+1380*v8.US]))
e={'id':'repeat_standalone_lag_broadcast','guard':a};probes.append(e);previous('V8B-02',not a['accepted'],e)
a,_=call(lambda:v8.label_table(joint,np.asarray([d+.5],dtype=np.float64)))
e={'id':'repeat_fractional_decision_coercion','guard':a};probes.append(e);previous('V8B-03',not a['accepted'],e)
mutated=frame.with_columns(pl.lit(100.).alias(v8.FLOW_COLUMNS[0]))
a,_=call(lambda:v8.assert_nonoverlap(mutated));b,_=call(lambda:v8.assert_split_chronology(mutated,**args))
e={'id':'repeat_flow_unit_corruption','frame_guard':a,'split_guard':b};probes.append(e);previous('V8B-04',not a['accepted'] and not b['accepted'],e)

# Original OOF/scaler protections under the new integer/development domain.
receipt=v8.OOFPredictionReceipt((10,11),(base+1800*v8.US,base+1860*v8.US),(base+1800*v8.US,base+1860*v8.US),
 (0,1,2),(base+500*v8.US,base+600*v8.US,base+650*v8.US),base+700*v8.US,100*v8.US,'a'*64)
receipt.validate();v8.flow_surprise(np.full((2,4),.2),np.full((2,4),.05),receipt,receipt)
oof=[]
for name,bad in [('fit_forecast_id',replace(receipt,fit_row_ids=(0,1,10))),
 ('future_forecast_feature',replace(receipt,forecast_feature_available_us=(base+1800*v8.US+1,base+1860*v8.US))),
 ('immature_fit_label',replace(receipt,fit_label_mature_us=(base+500*v8.US,base+600*v8.US,base+700*v8.US+1))),
 ('locked_fit_maturity',replace(receipt,fit_label_mature_us=(v8.END,v8.END,v8.END)))]:
    meta,_=call(lambda:v8.flow_surprise(np.full((2,4),.2),np.full((2,4),.05),bad,receipt));oof.append({'case':name,**meta})
scaler_meta,_=call(lambda:v8.fit_train_scaler(np.asarray([[1.,2.],[2.,3.]]),[0,1],[0,1],[base+700,base+701],base+700))
probes.append({'id':'control_oof_scaler_new_domain','oof_rejections':oof,'future_scaler_input':scaler_meta})

# New boundary: unknown nonfinite metadata at emitted price anchors.
anchor_cases=[('nan_entry_trade_control',d+300*v8.US,'last_trade_us',float('nan')),
 ('inf_entry_trade',d+300*v8.US,'last_trade_us',float('inf')),
 ('inf_exit_availability',d+600*v8.US-v8.BAR_US,'available_us',float('inf'))]
nonfinite_failed=[]
for name,stamp,field,value in anchor_cases:
    changed=joint.with_columns(pl.when(pl.col('timestamp')==stamp).then(value).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field))
    meta,result=call(lambda:v8.label_table(changed,decisions[:1]))
    e={'id':name,'field':field,'nonfinite_kind':'NaN' if np.isnan(value) else 'Infinity',**meta}
    if result is not None:
        e.update({'row_retained':len(result)==1,'label_valid':bool(result['label_valid'][0]),
          'all_targets_nan':all(np.isnan(result[c][0]) for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS))})
    if name!='nan_entry_trade_control' and not meta['accepted']:nonfinite_failed.append(name)
    probes.append(e)
if nonfinite_failed:
    findings.append({'id':'V8C-01','priority':'P2','status':'CONFIRMED_CONTRACT_IMPLEMENTATION_GAP',
     'title':'Nonfinite price-anchor timestamps abort instead of retaining invalid labels',
     'source':'scripts/research_v8/labels_v3.py','source_lines':[77,86,93,101],
     'contract_fields':['missing_policy','timestamps_per_row'], 'evidence_probes':nonfinite_failed,
     'impact':'Infinity in a future entry trade timestamp or exit availability is admitted by the finite-only source metadata check as unknown. The V2 builder invalidates the row, but V3 converts only NaN to nullable integers and attempts to cast Infinity to Int64, raising an exception. The same NaN anchor control retains a label_valid=false row and NaN targets. This is failclosed operational rejection, not demonstrated causal leakage.',
     'required_fix':'Treat every nonfinite emitted timestamp consistently as explicit unknown nullable metadata after per-row invalidation; reject invalid fitting/scored rows without aborting unaffected label rows or inventing timestamps.'})

# New boundary: exact past exists, but future target extends beyond finite explicit source.
tail_decision=base+4440*v8.US
past,past_available=v8.past_features(joint,tail_decision)
meta,result=call(lambda:v8.label_table(joint,np.asarray([d,tail_decision],dtype=np.int64)))
e={'id':'finite_source_tail_missing_future_anchor','exact_past_feature_shape':list(past.shape),
 'past_feature_available_us':past_available,'tail_decision_us':tail_decision,
 'source_close_end_us':int(times[-1])+v8.BAR_US,'nominal_tail_return_end_us':tail_decision+600*v8.US,**meta}
if result is not None:
    e.update({'decision_rows':result['decision_us'].to_list(),'label_valid':result['label_valid'].to_list()})
probes.append(e)
if not meta['accepted']:
    findings.append({'id':'V8C-02','priority':'P2','status':'CONFIRMED_CONTRACT_IMPLEMENTATION_GAP',
     'title':'Finite source tail loses per-row missing-future label behavior',
     'source':'scripts/research_v8/labels_v3.py, labels_v2.py and preserved labels.py',
     'source_lines':{'labels_v3.py':[101],'labels_v2.py':[62,63,64,65],'labels.py':[64,66]},
     'contract_fields':['missing_policy'], 'evidence_probe':e['id'],
     'impact':'A valid dense source with a complete past256 and available past features for the 4440s minute lacks the future return-end anchor at 5040s because the explicit source ends at 5000s. Passing this decision beside a fully valid earlier decision aborts the whole batch with Required label anchor outside explicit source. The contract requires unavailable future/price anchors to retain label_valid=false and NaN target rows, and future label validity must not become an online feature/calendar filter.',
     'required_fix':'Retain every explicitly supplied legal decision row. Mark windows/anchors outside the explicit finite future source as invalid with unknown maturity and NaN labels, while preserving known nominal registered endpoints and unaffected rows; never interpolate or fabricate source bars.'})

# Binding actual pre-run/output evidence is separate from contract acceptance.
start_path=root/'reports/fast_research/V8_CLEAN_CI_START_20261002_V2.json'
receipt_path=root/'reports/fast_research/V8_CLEAN_CI_EXECUTION_RECEIPT_20261002_V2.json'
start=json.loads(start_path.read_text());execution=json.loads(receipt_path.read_text())
ci_xml=root/'reports/fast_research/V8_CLEAN_CI_20261002_V2.xml'
source_keys=[p for p in files if p in start['source_hashes']]
ci_bindings={'audited_label_source_hashes_equal_start_and_execution':all(start['source_hashes'][p]==execution['source_hashes'][p]==start_sha[p] for p in source_keys),
 'protocol_equal_current':start['protocol_hash']==execution['protocol_hash']==start_sha['protocols/LABEL_CONTRACT_V8.json'],
 'environment_lock_equal_current':start['environment_hash']==execution['environment_hash']==start_sha['environments/v8/uv.lock'],
 'exact_command_equal':start['exact_command']==execution['exact_command'],
 'start_record_binding_equal':start['record_sha256']==execution['start_record_sha256'],
 'junit_digest_equal':sha(ci_xml)==execution['junit_sha256'],
 'actual_exit_zero':execution['actual_task']['exit_code']==0,'source_bytes_equal_before_after_claimed':execution['source_bytes_equal_before_after']}
provided=[]
for p,exit_code in [(Path('/home/xflops/coin-state/test-v8-label-contract-v3-20261002-v1.xml'),0),(ci_xml,execution['actual_task']['exit_code'])]:
    tree=ET.parse(p);suites=tree.findall('.//testsuite')
    provided.append({'path':str(p),'sha256':sha(p),'actual_exit_code':exit_code,
      'junit_counts':{k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','errors','failures','skipped')}})
if provided[-1]['junit_counts']!=execution['junit_counts']:raise RuntimeError('CI JUnit count receipt mismatch')
if not all(ci_bindings.values()):raise RuntimeError('CI output binding mismatch')
end_sha={p:sha(root/p) for p in files}
if end_sha!=start_sha:raise RuntimeError('Audited label bytes changed')
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
raw={'sources_sha256':start_sha,'source_unchanged':True,'previous_regressions':regressions,'probes':probes,'findings':findings}
raw_path=state/'probes.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
report={'report_id':'V8_LABEL_ADVERSARIAL_AUDIT_20261002_V3','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'status':'FAIL_CONTRACT_IMPLEMENTATION' if findings else 'PASS_SYNTHETIC_LABEL_CONTRACT_SCOPE_ONLY',
 'candidate_status':'NO_QUALIFIED_CANDIDATE','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_probe_start':head_start,'actual_HEAD_at_report':head_end,'sources_sha256':start_sha,
 'source_unchanged_during_probe':True,'original_contract_unchanged':True,
 'diff_note':'labels_v3.py and test_v8_label_contract_v3.py are reviewed as full new-file bytes; prior V1/V2 sources and test artifacts preserved.',
 'scope':{'read_market_data':False,'read_real_locked_observations':False,'fit_market_model':False,'GPU_used':False,
  'read_builder_explanations_or_root_state_documents':False,'modified_audited_sources':False,'modified_top_level_docs':False,
  'python':sys.executable,'PYTHONPATH':'/mnt/d/codex/coin/src','resource_policy':'hpc_linux with_task_progress/bounded.sh shared 5GB RAM, swap0, GPU0',
  'experiment_registry_writer':'root agent; auditor did not concurrently append shared registry'},
 'execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--cd','/mnt/d/codex/coin','--','bash','scripts/with_task_progress.sh','--title',
  'V8 \u6807\u7b7e\u7b2c\u4e09\u7248\u72ec\u7acb\u53cd\u4f8b\u5ba1\u8ba1','--','env','PYTHONPATH=/mnt/d/codex/coin/src',
  '/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python',str(state/'probe.py')]},
 'independent_probe':{'directory':str(state),'script':str(state/'probe.py'),'script_sha256':sha(state/'probe.py'),
  'output':str(raw_path),'output_sha256':sha(raw_path)},
 'provided_actual_outputs':provided,
 'CI_evidence':{'start_receipt':str(start_path),'start_receipt_sha256':sha(start_path),'execution_receipt':str(receipt_path),
  'execution_receipt_sha256':sha(receipt_path),'bindings':ci_bindings,'audited_source_keys_checked':source_keys,
  'interpretation':'Prebound actual execution and output bindings verified for allowed label sources; this does not turn existing unit coverage into contract or economic acceptance.'},
 'previous_V1_V2_counterexamples_all_fixed_in_this_probe':all(x['status']=='FIXED_IN_THIS_PROBE' for x in regressions),
 'previous_regression_results':regressions,'probes':probes,'findings':findings,
 'acceptance_blocker_ids':[x['id'] for x in findings], 'causal_P1_blocker_ids':[x['id'] for x in findings if x['priority']=='P1'],
 'limits':['Only label contract implementation and synthetic chronology/source boundaries were audited.',
  'No market labels, forecasts, OOS metrics, fees/fills, model-selection behavior, P1 economic/statistical gates or ten-family common caller wiring were evaluated.',
  'The two new missing-policy gaps reject operationally and do not demonstrate acceptance of a future-leaking or locked scored row.',
  'Feature adapter acceptance remains a separate report and is not implied by this label or clean-CI output.'],
 'decision':'All nine prior label counterexamples are fixed, but two existing missing-policy requirements remain unimplemented. Preserve V1/V2/V3 evidence, repair per-row invalid-future/anchor behavior in a new immutable version and independently retest. Keep NO_QUALIFIED_CANDIDATE and P1 statistical/economic gate NOT_EVALUATED.'}
report_path=root/'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V3.json'
if report_path.exists():raise RuntimeError('Refusing to overwrite prior audit artifact')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(report_path),'report_sha256':sha(report_path),'created_at_utc':report['created_at_utc'],
 'status':report['status'],'prior_counterexamples_all_fixed':report['previous_V1_V2_counterexamples_all_fixed_in_this_probe'],
 'acceptance_blockers':report['acceptance_blocker_ids'],'causal_P1_blockers':report['causal_P1_blocker_ids'],
 'sources_sha256':start_sha,'CI_bindings':ci_bindings,'actual_outputs':provided},indent=2))