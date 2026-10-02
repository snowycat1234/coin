from __future__ import annotations
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date,datetime,timezone
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-adversarial-20261002-v5')
sys.path.insert(0,str(root/'scripts/research_v8'))
import numpy as np
import polars as pl
import labels_v5 as v8
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['protocols/LABEL_CONTRACT_V8.json','scripts/research_v8/labels.py','scripts/research_v8/labels_v2.py','scripts/research_v8/labels_v3.py',
 'tests/test_v8_label_contract.py','tests/test_v8_label_contract_v2.py','tests/test_v8_label_contract_v3.py','environments/v8/uv.lock']
files += ['scripts/research_v8/labels_v4.py','scripts/research_v8/labels_v5.py','tests/test_v8_label_contract_v4.py','tests/test_v8_label_contract_v5.py']
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


checks=[]
def check(name, passed, evidence):
    checks.append({'id':name,'passed':bool(passed),'evidence':evidence})
    if not passed:
        findings.append({'id':name,'priority':'P2','status':'CONFIRMED_CONTRACT_IMPLEMENTATION_GAP','evidence':evidence})

# Repeat both prior V3 missing-policy findings, including all-invalid batches.
anchor_results=[]
for variant,spec in v8.contract()['labels'].items():
    for kind in ('PAST_ONLY_PREDICTED_FLOW','OBSERVED_FUTURE_FLOW_DIAGNOSTIC'):
        clean=v8.label_table(joint,decisions,variant,signal_kind=kind)
        for field,side in (('last_trade_us','entry'),('available_us','exit')):
            for mode,bad in (('mixed',float('inf')),('all_invalid',float('-inf'))):
                offset=spec['return_start_offset_seconds' if side=='entry' else 'return_end_offset_seconds']*v8.US-v8.BAR_US
                stamps=decisions[-1:]+offset if mode=='mixed' else decisions+offset
                changed=joint.with_columns(pl.when(pl.col('timestamp').is_in(stamps.tolist())).then(bad).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field))
                meta,out=call(lambda:v8.label_table(changed,decisions,variant,signal_kind=kind))
                expected=[True,False] if mode=='mixed' else [False,False]
                e={'variant':variant,'signal_kind':kind,'field':field,'side':side,'mode':mode,**meta}
                ok=False
                if out is not None:
                    invalid=np.flatnonzero(~np.asarray(expected));good=np.flatnonzero(np.asarray(expected))
                    e.update({'decision_grid_retained':out['decision_us'].to_list()==decisions.tolist(),
                      'valid':out['label_valid'].to_list(),
                      'invalid_targets_nan':all(np.isnan(out[c][int(i)]) for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS) for i in invalid),
                      'invalid_total_and_return_maturity_unknown':all(out[c][int(i)] is None for c in ('label_mature_us','return_label_mature_us') for i in invalid),
                      'anchor_metadata_unknown':all(out[f'{s}__{side}_price_{"trade" if field=="last_trade_us" else "available"}_us'][int(i)] is None for i in invalid),
                      'valid_rows_unchanged':all(out.row(int(i),named=True)==clean.row(int(i),named=True) for i in good),
                      'direct_targets_identical':all(v8.direct_return_labels(out)[c].equals(out[c]) for c in v8.RETURN_COLUMNS),
                      'canonical_layout':out.columns==clean.columns,
                      'integer_schema':all(dtype==pl.Int64 for col,dtype in out.schema.items() if col.endswith('_us'))})
                    ok=all(e[key] for key in ('decision_grid_retained','invalid_targets_nan','invalid_total_and_return_maturity_unknown','anchor_metadata_unknown','valid_rows_unchanged','direct_targets_identical','canonical_layout','integer_schema')) and e['valid']==expected
                anchor_results.append(e)
                check('V5_anchor_'+variant+'_'+kind+'_'+field+'_'+mode,ok,e)
print('Prior nine regressions and nonfinite anchor probes completed',flush=True)

for variant,spec in v8.contract()['labels'].items():
    for kind in ('PAST_ONLY_PREDICTED_FLOW','OBSERVED_FUTURE_FLOW_DIAGNOSTIC'):
        tail_second=((5000-spec['return_end_offset_seconds'])//60+1)*60
        tail=base+tail_second*v8.US
        meta,mixed=call(lambda:v8.label_table(joint,np.asarray([d,tail],dtype=np.int64),variant,signal_kind=kind))
        e={'variant':variant,'signal_kind':kind,'tail_decision_us':tail,'source_closed_end_us':int(times[-1])+v8.BAR_US,**meta}
        ok=False
        if mixed is not None:
            single=v8.label_table(joint,np.asarray([tail],dtype=np.int64),variant,signal_kind=kind)
            clean=v8.label_table(joint,np.asarray([d],dtype=np.int64),variant,signal_kind=kind)
            futureless=v8.label_table(joint,np.asarray([base+4980*v8.US]),variant,signal_kind=kind)
            e.update({'valid':mixed['label_valid'].to_list(),'earlier_row_unchanged':mixed.head(1).equals(clean),
                'all_invalid_equals_mixed_tail':single.equals(mixed.tail(1)),
                'decision_grid_retained':mixed['decision_us'].to_list()==[d,tail],
                'known_nominal_end_preserved':mixed['return_label_end_us'][1]==tail+spec['return_end_offset_seconds']*v8.US,
                'unknown_maturity':mixed['label_mature_us'][1] is None and mixed['return_label_mature_us'][1] is None,
                'unknown_missing_exit_anchor':all(mixed[f'{st}__exit_price_trade_us'][1] is None and np.isnan(mixed[f'{st}__exit_price_proxy'][1]) for st in v8.RETURN_STREAMS),
                'invalid_targets_nan':all(np.isnan(mixed[c][1]) for c in (*v8.FLOW_COLUMNS,*v8.RETURN_COLUMNS)),
                'entirely_missing_future_kept_invalid':len(futureless)==1 and not futureless['label_valid'][0] and futureless['flow_label_mature_us'][0] is None and futureless['label_mature_us'][0] is None,
                'direct_targets_identical':all(v8.direct_return_labels(mixed)[c].equals(mixed[c]) for c in v8.RETURN_COLUMNS)})
            ok=e['valid']==[True,False] and all(e[k] for k in ('earlier_row_unchanged','all_invalid_equals_mixed_tail','decision_grid_retained','known_nominal_end_preserved','unknown_maturity','unknown_missing_exit_anchor','invalid_targets_nan','entirely_missing_future_kept_invalid','direct_targets_identical'))
        check('V5_tail_'+variant+'_'+kind,ok,e)
previous('V8C-01',all(x['passed'] for x in checks if x['id'].startswith('V5_anchor_')),{'cases':len(anchor_results),'all_passed':all(x['passed'] for x in checks if x['id'].startswith('V5_anchor_'))})
previous('V8C-02',all(x['passed'] for x in checks if x['id'].startswith('V5_tail_')),{'cases':6,'all_passed':all(x['passed'] for x in checks if x['id'].startswith('V5_tail_'))})

# Unknown availability inside future flow is retained; the same unknown in past is refused.
changed=joint.with_columns(pl.when(pl.col('timestamp')==d+5*v8.US).then(float('nan')).otherwise(pl.col(s+'__available_us')).alias(s+'__available_us'))
meta,out=call(lambda:v8.label_table(changed,decisions[:1],signal_kind='OBSERVED_FUTURE_FLOW_DIAGNOSTIC'))
e={**meta}
if out is not None:e.update({'invalid_retained':len(out)==1 and not out['label_valid'][0],'flow_signal_and_order_unknown':all(out[c][0] is None for c in ('flow_label_mature_us','observed_future_flow_available_us','signal_available_us','earliest_permissible_order_us','label_mature_us'))})
check('V5_unknown_future_flow_availability',out is not None and e['invalid_retained'] and e['flow_signal_and_order_unknown'],e)
changed=joint.with_columns(pl.when(pl.col('timestamp')==d-v8.BAR_US).then(float('inf')).otherwise(pl.col(s+'__available_us')).alias(s+'__available_us'))
a,_=call(lambda:v8.label_table(changed,decisions[:1]));b,_=call(lambda:v8.past_features(changed,d))
check('V5_unknown_past_availability',not a['accepted'] and not b['accepted'],{'labels':a,'features':b})

# Actual flow availability controls order time; a late diagnostic cannot score as valid.
late=d+700*v8.US
changed=joint.with_columns(pl.when(pl.col('timestamp')==d+5*v8.US).then(late).otherwise(pl.col(s+'__available_us')).alias(s+'__available_us'))
a=v8.label_table(changed,decisions[:1],signal_kind='PAST_ONLY_PREDICTED_FLOW')
b=v8.label_table(changed,decisions[:1],signal_kind='OBSERVED_FUTURE_FLOW_DIAGNOSTIC')
check('V5_delayed_flow_signal_maturity',a['label_valid'][0] and a['label_mature_us'][0]>=late and not b['label_valid'][0] and b['flow_label_mature_us'][0]==late and b['earliest_order_us'][0]==late+5*v8.US,
 {'past_signal_valid':a['label_valid'][0],'observed_diagnostic_valid':b['label_valid'][0],'flow_mature_us':b['flow_label_mature_us'][0],'earliest_order_us':b['earliest_order_us'][0],'required_actual_availability_us':late})

# No future label validity/values may become a past feature filter.
past,available=v8.past_features(joint,d)
expr=[pl.when(pl.col('timestamp')>=d).then(pl.col(c)*3+7).otherwise(pl.col(c)).alias(c) for c in joint.columns
      if c!='timestamp' and not c.endswith('_us') and not c.endswith('__empty_bin') and not c.endswith('__quality')]
perturbed=joint.with_columns(*expr)
future,favailable=v8.past_features(perturbed,d)
check('V5_future_perturbation_no_past_change',np.array_equal(past,future) and available==favailable,
 {'feature_shape':list(past.shape),'bit_exact':np.array_equal(past,future),'same_availability':available==favailable})

# All frame/binding entry points reject older active-version tags.
version_checks=[]
for tag in ('V8_LABELS_V1_20261002','V8_LABELS_V2_20261002','V8_LABELS_V3_20261002','V8_LABELS_V4_20261002','UNKNOWN'):
    old=frame.with_columns(pl.lit(tag).alias('implementation_version'))
    guards=[]
    for name,fn in (('frame',lambda:v8.assert_nonoverlap(old)),('direct',lambda:v8.direct_return_labels(old)),('split',lambda:v8.assert_split_chronology(old,**args))):
        meta,_=call(fn);guards.append({'guard':name,**meta})
    check('V5_active_version_'+tag,all(not x['accepted'] for x in guards),{'tag':tag,'guards':guards})
    version_checks.extend(guards)
binding={k:'same' for k in v8.MATCH_KEYS}
for k in ('endpoint_row_ids','train_row_ids','validation_row_ids','test_row_ids'):
    if k in binding:binding[k]=(1,2)
binding['decision_frequency_seconds']=60;binding['label_variant']='LEAD_LAG_5M_5M';binding['label_implementation_version']=v8.IMPLEMENTATION_VERSION
meta,_=call(lambda:v8.assert_matched_direct_baseline(binding,binding.copy()))
check('V5_matched_direct_active_control',meta['accepted'],meta)
for tag in ('V8_LABELS_V3_20261002','V8_LABELS_V4_20261002'):
    bad={**binding,'label_implementation_version':tag}
    meta,_=call(lambda:v8.assert_matched_direct_baseline(bad,bad.copy()))
    check('V5_matched_direct_version_'+tag,not meta['accepted'],meta)
for key in v8.MATCH_KEYS:
    bad={**binding,key:'different'}
    meta,_=call(lambda:v8.assert_matched_direct_baseline(binding,bad))
    check('V5_matched_direct_mismatch_'+key,not meta['accepted'],meta)

# Missing label rows remain in the calendar but cannot enter fit/scored splits.
bad_test=v8.label_table(joint,np.asarray([base+4440*v8.US]),split='OOS_SCREENING')
bad_frame=pl.concat([frame.head(2),bad_test])
meta,_=call(lambda:v8.assert_split_chronology(bad_frame,**{**args,'test_ids':[base+4440*v8.US]}))
check('V5_missing_future_split_rejected',not meta['accepted'],meta)

receipt=v8.OOFPredictionReceipt((10,11),(base+1800*v8.US,base+1860*v8.US),(base+1800*v8.US,base+1860*v8.US),
 (0,1,2),(base+500*v8.US,base+600*v8.US,base+650*v8.US),base+700*v8.US,100*v8.US,'a'*64)
meta,out=call(lambda:v8.flow_surprise(np.full((2,4),.2),np.full((2,4),.05),receipt,receipt))
check('V5_oof_original_units_positive_control',meta['accepted'] and np.allclose(out,.15),meta)
for name,bad in [('fit_forecast_id',replace(receipt,fit_row_ids=(0,1,10))),('duplicate_forecast_id',replace(receipt,forecast_row_ids=(10,10))),
 ('future_forecast_feature',replace(receipt,forecast_feature_available_us=(base+1800*v8.US+1,base+1860*v8.US))),
 ('immature_fit_label',replace(receipt,fit_label_mature_us=(base+500*v8.US,base+600*v8.US,base+700*v8.US+1))),
 ('locked_fit_maturity',replace(receipt,fit_label_mature_us=(v8.END,v8.END,v8.END))),
 ('metadata_broadcast',replace(receipt,forecast_feature_available_us=(base+1800*v8.US,))),
 ('fractional_metadata',replace(receipt,fit_cutoff_us=float(base+700*v8.US))),
 ('cutoff_at_embargo_boundary',replace(receipt,fit_cutoff_us=base+1700*v8.US,embargo_us=100*v8.US))]:
    meta,_=call(lambda:v8.flow_surprise(np.full((2,4),.2),np.full((2,4),.05),bad,receipt))
    check('V5_oof_'+name,not meta['accepted'],meta)
for name,row_ids,train_ids,available,cutoff in (
 ('future_input',[0,1],[0,1],[base+700,base+701],base+700),
 ('validation_id',[0,1],[0],[base+700,base+700],base+700),
 ('broadcast',[0,1],[0,1],[base+700],base+700),
 ('locked',[0,1],[0,1],[v8.END,v8.END],v8.END-1)):
    meta,_=call(lambda:v8.fit_train_scaler(np.asarray([[1.,2.],[2.,3.]]),row_ids,train_ids,available,cutoff))
    check('V5_scaler_'+name,not meta['accepted'],meta)
meta,_=call(lambda:v8.fit_conditional_expectation(np.asarray([[1.,2.],[2.,3.]]),np.full((2,4),.1),[0,1],[0,1],[base+700,base+700],[base+700,base+701],base+700))
check('V5_expectation_immature_target',not meta['accepted'],meta)
print('All independent synthetic boundary probes completed',flush=True)

# Verify provided actual outputs and pre-execution bindings, independently from probe results.
receipt_path=root/'reports/fast_research/V8_LABEL_V5_SYNTHETIC_ACCEPTANCE_20261002_V1.json'
v4_path=root/'reports/fast_research/V8_LABEL_V4_SYNTHETIC_ACCEPTANCE_20261002_V1.json'
provided=json.loads(receipt_path.read_text());old_failure=json.loads(v4_path.read_text())
binding_path=Path(provided['junit_path']).parent/'RUN_BINDING.json'
prebinding=json.loads(binding_path.read_text());xml_path=Path(provided['junit_path'])
tree=ET.parse(xml_path);suites=tree.findall('.//testsuite');counts={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','errors','failures','skipped')}
properties=[{p.attrib['name']:p.attrib.get('value') for p in case.findall('./properties/property')} for case in tree.findall('.//testcase')]
# Allowed source keys only; no unprovided builder explanations/state read.
provided_bindings={'current_source_hashes_equal_prebound':all(provided['binding']['source_hashes'][p]==prebinding['source_hashes'][p]==start_sha[p] for p in files),
 'same_binding_object':provided['binding']==prebinding,
 'RUN_BINDING_sha256':sha(binding_path)==provided['run_binding_sha256'],
 'JUnit_sha256':sha(xml_path)==provided['junit_sha256'],
 'actual_exit_zero':provided['actual_test_exit_code']==0,
 'source_unchanged_receipt':provided['source_bytes_unchanged'],
 'lock_sha256':provided['binding']['environment_lock_sha256']==start_sha['environments/v8/uv.lock'],
 '29_actual_testcases':counts=={'tests':29,'errors':0,'failures':0,'skipped':0},
 'V4_failure_preserved':old_failure['actual_test_exit_code']!=0}
# Retain exact emitted test properties as evidence; validate every testcase has pre-run binding fields.
property_names=sorted(set().union(*(set(p) for p in properties)))
provided_bindings['all_testcase_binding_properties_present']=len(properties)==29 and all(any('binding' in k for k in p) and any('lock' in k for k in p) and any('adapter' in k for k in p) for p in properties)
check('V5_provided_actual_output_bindings',all(provided_bindings.values()),provided_bindings)
end_sha={p:sha(root/p) for p in files};check('V5_source_bytes_unchanged',end_sha==start_sha,{'start':start_sha,'end':end_sha})
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
raw={'previous_regressions':regressions,'probes':probes,'additional_checks':checks,'findings':findings}
raw_path=state/'probes.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
report={'report_id':'V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'status':'FAIL_CONTRACT_IMPLEMENTATION' if findings else 'PASS_CONTRACT_IMPLEMENTATION',
 'candidate_status':'NO_QUALIFIED_CANDIDATE','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_probe_start':head_start,'actual_HEAD_at_report':head_end,'verified_source_hashes':start_sha,
 'source_unchanged_during_probe':end_sha==start_sha,'original_contract_unchanged':True,
 'scope':{'read_market_data':False,'read_real_locked_observations':False,'fit_market_model':False,'GPU_used':False,
  'read_builder_explanations_or_root_state_documents':False,'modified_audited_sources':False,'modified_top_level_docs':False,
  'python':sys.executable,'PYTHONPATH':'/mnt/d/codex/coin/src','resource_policy':'hpc_linux with_task_progress/bounded.sh shared 5GB RAM, swap0, GPU0',
  'experiment_registry_writer':'root agent; auditor did not append shared registry'},
 'execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--','bash','-lc',
  'cd /mnt/d/codex/coin && scripts/with_task_progress.sh --title V8标签第五版独立反例审计 -- env PYTHONPATH=/mnt/d/codex/coin/src /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /home/xflops/coin-state/test-v8-adversarial-20261002-v5/probe.py']},
 'independent_probe':{'directory':str(state),'script':str(state/'probe.py'),'script_sha256':sha(state/'probe.py'),
  'output':str(raw_path),'output_sha256':sha(raw_path)},
 'provided_actual_output':{'path':str(receipt_path),'sha256':sha(receipt_path),'run_binding':str(binding_path),
  'run_binding_sha256':sha(binding_path),'junit_path':str(xml_path),'junit_sha256':sha(xml_path),'junit_counts':counts,
  'actual_exit_code':provided['actual_test_exit_code'],'verified_bindings':provided_bindings,
  'testcase_property_names':property_names,'testcase_properties':properties},
 'preserved_V4_failure':{'path':str(v4_path),'sha256':sha(v4_path),'actual_exit_code':old_failure['actual_test_exit_code']},
 'previous_independent_audit':{'path':'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V3.json',
  'sha256':sha(root/'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V3.json')},
 'previous_V1_V2_V3_counterexamples_all_fixed_in_this_probe':all(x['status']=='FIXED_IN_THIS_PROBE' for x in regressions),
 'previous_regression_results':regressions,'probes':probes,'additional_checks':checks,'findings':findings,
 'acceptance_blocker_ids':[x['id'] for x in findings],
 'limits':['This conclusion applies only to verified V5 label contract adapter hashes and the synthetic adversarial boundaries actually exercised.',
  'It does not accept market labels or forecasts, OOS model performance, model selection, fees/fills, four dispersed regimes, nonoverlap economic mechanism results or P1 statistical/economic gates.',
  'Fixed feature adapter acceptance and ten-model actual caller routing remain separate gates; past-feature future perturbation here is only a label adapter control.',
  'Frozen V1/V2/V3/V4 failures and earlier audits are preserved; no prior receipt is rewritten and no market/locked/model artifact was accessed.'],
 'decision':'PASS_CONTRACT_IMPLEMENTATION for verified V5 hashes only; keep NO_QUALIFIED_CANDIDATE and P1 statistical/economic gate NOT_EVALUATED.' if not findings else 'Block contract acceptance on the listed independently reproduced implementation findings; no alpha/economic inference.'}
report_path=root/'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5.json'
if report_path.exists():raise RuntimeError('Refusing to overwrite prior audit artifact')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(report_path),'report_sha256':sha(report_path),'status':report['status'],
 'previous_counterexamples_fixed':report['previous_V1_V2_V3_counterexamples_all_fixed_in_this_probe'],
 'additional_checks':len(checks),'failures':report['acceptance_blocker_ids'],'provided_bindings':provided_bindings,
 'verified_source_hashes':start_sha},indent=2))