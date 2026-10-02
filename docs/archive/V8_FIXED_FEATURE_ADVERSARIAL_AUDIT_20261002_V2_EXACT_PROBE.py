from __future__ import annotations
import hashlib,json,resource,subprocess,sys,tracemalloc
from datetime import date,datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-fixed-feature-adversarial-20261002-v2')
sys.path.insert(0,str(root))
import numpy as np
import polars as pl
from scripts.research_v8 import features as definition,features_v2 as prior,features_v3 as active
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['protocols/FEATURE_CONTRACT_V8.json','protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json','protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json',
 'scripts/research_v8/features.py','scripts/research_v8/features_v2.py','scripts/research_v8/features_v3.py',
 'tests/test_v8_features.py','tests/test_v8_features_v2.py','tests/test_v8_features_v3.py','environments/v8/uv.lock']
start_sha={p:sha(root/p) for p in files};head_start=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
contract=json.loads((root/files[0]).read_text());manifest=json.loads((root/files[2]).read_text())
previous_audit_path=root/'reports/fast_research/V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V1.json'
previous_audit=json.loads(previous_audit_path.read_text());previous_audit_sha=sha(previous_audit_path)
if previous_audit_sha!='5997a1b021a541cd40df78ff03539ec9a541035ddb819b0bed56aa35363c8495':raise RuntimeError('Prior audit bytes changed')
bindings={'original_definition_contract_unchanged':start_sha[files[0]]=='1567496fd28bff5d0d4659c819ccb92f27de56ab94469c87de49a933b702c823',
 'definition_contract_binding':manifest['definition_contract_sha256']==start_sha[files[0]],
 'active_adapter_binding':manifest['active_adapter_sha256']==start_sha['scripts/research_v8/features_v3.py'],
 'preserved_adapter_binding':manifest['preserved_definition_adapter_sha256']==start_sha['scripts/research_v8/features.py'],
 'previous_active_manifest_binding':manifest['previous_active_contract_sha256']==start_sha[files[1]]}
if not all(bindings.values()):raise RuntimeError('Contract binding mismatch')
n=900;base=definition.day_us(date(2025,7,2));index=np.arange(n,dtype=np.int64);times=base+index*definition.BAR_US
rows={'timestamp':times}
for i,s in enumerate(definition.STREAMS):
    close=100.+10*i+index*.001
    rows.update({s+'__available_us':times+definition.BAR_US,s+'__quality':np.zeros(n,dtype=np.int32),
      s+'__close':close,s+'__vwap':close+.002,s+'__high':close+1,s+'__low':close-1,
      s+'__flow_imbalance':np.full(n,.1*(i+1)),s+'__return_5s':np.full(n,.001*(i+1)),
      s+'__large_trade_share':np.full(n,.2),s+'__signed_price_impact':np.full(n,.01),
      s+'__interarrival_count':np.full(n,4),s+'__empty_bin':np.zeros(n,dtype=bool)})
    for field in ('quote_notional','base_volume','trade_count','agg_count','mean_trade_size','max_trade_size','mean_interarrival','std_interarrival'):
        rows[s+'__'+field]=np.full(n,10.+i)
joint=pl.DataFrame(rows);decision=base+3900_000_000;stamp=decision-50_000_000;s=definition.STREAMS[0]
probes=[];regressions=[];findings=[]
def attempt(frame,when=decision):
    try:
        result=active.endpoint_features(frame,when);return {'accepted':True},result
    except Exception as exc:
        return {'accepted':False,'exception_type':type(exc).__name__,'exception':str(exc)},None

def mutate(frame,changes,when=stamp):
    return frame.with_columns(*[pl.when(pl.col('timestamp')==when).then(value).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field) for field,value in changes])
rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;tracemalloc.start()
out=active.endpoint_features(joint,decision);_,trace_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
rss_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
probes.append({'id':'healthy_common_definition_and_resource','feature_count':len(out.names),
 'names_equal_contract':list(out.names)==contract['feature_names'],
 'definitions_equal_frozen_adapter':np.array_equal(out.values,definition.endpoint_features(joint,decision).values),
 'available_us':out.available_us,'output_bytes':out.values.nbytes,'values_finite':bool(np.isfinite(out.values).all()),
 'values_immutable':not out.values.flags.writeable,'rss_high_water_before_bytes':rss_before,'rss_high_water_after_bytes':rss_after,
 'python_traced_peak_bytes':trace_peak,'nominal_canonical_input_shape':[720,68],
 'resource_limit':'RSS includes imported libraries; tracemalloc does not fully count native allocation; endpoint API produces a 478-value summary without a sample-window cube.'})

for name,when,field,value in [('missing_historical_close',stamp,'close',None),('missing_current_vwap',decision-definition.BAR_US,'vwap',None),
 ('missing_traded_mean_size',decision-definition.BAR_US,'mean_trade_size',None),('negative_traded_mean_size',decision-definition.BAR_US,'mean_trade_size',-.5)]:
    meta,_=attempt(mutate(joint,[(field,value)],when));regressions.append({'prior_finding':'V8F-02','probe':name,'status':'FIXED_IN_THIS_PROBE' if not meta['accepted'] else 'STILL_FAILING',**meta})
    if meta['accepted']:findings.append({'id':'V8F-02-'+name+'-V3','priority':'P1','status':'CONFIRMED_REGRESSION_FAILURE'})

future=joint.with_columns(*[pl.when(pl.col('timestamp')>=decision).then(value).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field)
 for s in definition.STREAMS for field,value in [('available_us',None),('quality',999),('vwap',None),('close',-1.),('mean_trade_size',None),
 ('flow_imbalance',100.),('empty_bin',None),('return_5s',None),('signed_price_impact',None)]])
future_out=active.endpoint_features(future,decision)
extra=joint.with_columns(pl.lit(float('inf')).alias('future_return_label'),pl.lit(float('nan')).alias('future_flow_label'))
extra_out=active.endpoint_features(extra,decision)
probes.append({'id':'future_perturbation_all_primitives','values_exactly_unchanged':np.array_equal(out.values,future_out.values),
 'availability_unchanged':out.available_us==future_out.available_us,'extra_future_label_columns_ignored':np.array_equal(out.values,extra_out.values)})

undefined=mutate(joint,[('return_5s',None),('signed_price_impact',None),('interarrival_count',0),('mean_interarrival',None),('std_interarrival',None)])
meta,masked_out=attempt(undefined)
if masked_out is not None:
    lookup=dict(zip(masked_out.names,masked_out.values));meta.update({'equals_preserved_adapter':np.array_equal(masked_out.values,definition.endpoint_features(undefined,decision).values),
      'observed_return_fraction_3600s':lookup[s+'__observed_return_fraction__3600s'],
      'mean_has_return_256':lookup['mean__'+s+'__has_return'],'mean_has_interarrival_256':lookup['mean__'+s+'__has_interarrival']})
probes.append({'id':'legitimate_undefined_return_impact_interarrival',**meta})

# A true no-trade bin is internally consistent and retains its original masks.
empty_changes=[('empty_bin',True),('quote_notional',0.),('base_volume',0.),('trade_count',0.),('agg_count',0.),
 ('close',None),('vwap',None),('high',None),('low',None),('mean_trade_size',None),('max_trade_size',None),
 ('flow_imbalance',None),('large_trade_share',None),('return_5s',None),('signed_price_impact',None),
 ('interarrival_count',0),('mean_interarrival',None),('std_interarrival',None)]
legal_empty=mutate(joint,empty_changes);meta,empty_out=attempt(legal_empty)
if empty_out is not None:
    lookup=dict(zip(empty_out.names,empty_out.values));meta.update({'equals_preserved_adapter':np.array_equal(empty_out.values,definition.endpoint_features(legal_empty,decision).values),
      'mean_has_trade_256':lookup['mean__'+s+'__has_trade']})
probes.append({'id':'legitimate_no_trade_bin_masks',**meta})

# A corrupted empty mask must not relabel an observed positive-activity traded bar.
contradictory=mutate(joint,[('empty_bin',True),('close',None),('vwap',None),('high',None),('low',None),('mean_trade_size',None),('max_trade_size',None)])
meta,bypassed_out=attempt(contradictory)
e={'id':'positive_trade_activity_false_empty_mask','raw_empty_bin':True,'raw_trade_count':10.,'raw_agg_count':10.,
 'raw_quote_notional':10.,'raw_base_volume':10.,'raw_interarrival_count':4,'missing_prices_and_size':True,**meta}
if bypassed_out is not None:
    lookup=dict(zip(bypassed_out.names,bypassed_out.values));e.update({'mean_has_trade_256':lookup['mean__'+s+'__has_trade'],
     'mean_log_trade_count_256':lookup['mean__'+s+'__log_trade_count'],'mean_vwap_close_offset_bps_256':lookup['mean__'+s+'__vwap_close_offset_bps']})
probes.append(e)
if meta['accepted']:
    findings.append({'id':'V8F-03','priority':'P1','status':'CONFIRMED_CONTRACT_IMPLEMENTATION_GAP',
      'title':'Contradictory empty-bin mask bypasses traded primitive rejection',
      'source':'scripts/research_v8/features_v3.py','source_lines':[19,22,27,29,31,33],
      'contract_fields':['missing_policy','FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.input_primitive_masks','activity_units'],
      'evidence_probe':'positive_trade_activity_false_empty_mask',
      'impact':'A bar still has positive trade_count/agg_count/quote_notional/base_volume and interarrival count, but empty_bin is changed to True and its traded prices/sizes become None. V3 trusts the mask without checking that it is a legitimate no-trade bin, skips primitive checks, and accepts zero-filled missing features. A genuinely empty zero-activity bin remains valid in the positive control; the failure is the inconsistent mask/observed activity path.',
      'required_fix':'Before applying no-trade masks, validate that the traded/empty state is known and consistent with the underlying observed activity/count primitives. Reject contradictory positive-activity empty bins and retain the original mask behavior for actual zero-activity empty bins. Keep definitions/source bytes preserved in older versions.'})

# Nonboolean masks are tested solely as a malformed-input boundary.
numeric=joint.with_columns(pl.col(s+'__empty_bin').cast(pl.Int64).alias(s+'__empty_bin'))
meta,numeric_out=attempt(numeric)
e={'id':'nonboolean_empty_state','dtype':'Int64',**meta}
if numeric_out is not None:
    lookup=dict(zip(numeric_out.names,numeric_out.values));e.update({'last_has_trade':lookup['last__'+s+'__has_trade'],'mean_has_trade':lookup['mean__'+s+'__has_trade']})
    findings.append({'id':'V8F-04','priority':'P2','status':'CONFIRMED_CONTRACT_IMPLEMENTATION_GAP','title':'Nonboolean empty state accepted','evidence_probe':'nonboolean_empty_state',
     'required_fix':'Require an explicit boolean empty/traded state before mask application; do not silently coerce arbitrary primitive state values.'})
probes.append(e)

# Existing failclosed timestamp/quality/calendar controls remain checked once.
for name,frame,when in [('past_late',mutate(joint,[('available_us',decision+1)]),decision),
 ('past_quality_unknown',mutate(joint,[('quality',None)]),decision),('past_grid_missing',joint.filter(pl.col('timestamp')!=stamp),decision),
 ('fractional_decision',joint,float(decision)+.75),('locked_decision_value_only',joint,definition.day_us(definition.LOCKED))]:
    meta,_=attempt(frame,when);probes.append({'id':name,**meta})

start_path=root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V3.json'
receipt_path=root/'reports/fast_research/V8_FIXED_FEATURE_CHECK_RECEIPT_20261002_V3.json'
xml_path=root/'reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V3.xml'
start=json.loads(start_path.read_text());execution=json.loads(receipt_path.read_text());tree=ET.parse(xml_path);suites=tree.findall('.//testsuite')
counts={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','errors','failures','skipped')}
output_bindings={'all_provided_feature_source_hashes_equal':all(start['source_hashes'][p]==execution['source_hashes'][p]==start_sha[p] for p in start['source_hashes']),
 'protocol_equals_active_manifest':start['protocol_hash']==execution['protocol_hash']==start_sha['protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json'],
 'lock_equals_current':start['environment_hash']==execution['environment_hash']==start_sha['environments/v8/uv.lock'],
 'command_equal':start['exact_command']==execution['exact_command'],'start_receipt_digest_equal':sha(start_path)==execution['start_receipt_sha256'],
 'junit_digest_equal':sha(xml_path)==execution['junit_sha256'],'junit_counts_equal':counts==execution['junit_counts'],
 'actual_session_exit_zero':execution['actual_unified_session_id']==77221 and execution['actual_unified_exit_code']==execution['actual_task']['exit_code']==0}
if not all(output_bindings.values()):raise RuntimeError('Feature execution output binding mismatch')
if {p:sha(root/p) for p in files}!=start_sha:raise RuntimeError('Audited source changed during probe')
if sha(previous_audit_path)!=previous_audit_sha:raise RuntimeError('Previous audit changed during probe')
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
raw={'sources_sha256':start_sha,'source_unchanged':True,'previous_primitive_regressions':regressions,'probes':probes,'findings':findings}
raw_path=state/'probes.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
report={'report_id':'V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V2','audited_active_adapter':'features_v3.py',
 'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'FAIL_FEATURE_CONTRACT_IMPLEMENTATION' if findings else 'PASS_SYNTHETIC_FEATURE_CONTRACT_SCOPE_ONLY',
 'candidate_status':'NO_QUALIFIED_CANDIDATE','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_probe_start':head_start,'actual_HEAD_at_report':head_end,'sources_sha256':start_sha,'source_unchanged_during_probe':True,
 'definition_and_manifest_bindings':bindings,'previous_audit':{'path':str(previous_audit_path),'sha256':previous_audit_sha,'old_artifacts_unchanged':True},
 'previous_four_primitive_counterexamples_all_fixed':all(x['status']=='FIXED_IN_THIS_PROBE' for x in regressions),'previous_regression_results':regressions,
 'scope':{'read_market_data':False,'read_real_locked_or_model_artifacts':False,'fit_market_model':False,'GPU_used':False,
  'read_builder_explanations_or_root_state_documents':False,'source_modified':False,'top_level_docs_modified':False,
  'python':sys.executable,'PYTHONPATH':'/mnt/d/codex/coin/src','resource_policy':'hpc_linux with_task_progress/bounded.sh shared 5GB RAM, swap0, GPU0',
  'experiment_registry_writer':'root agent; auditor did not append shared registry'},
 'execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--cd','/mnt/d/codex/coin','--','bash','scripts/with_task_progress.sh','--title',
  'V8 \u5171\u540c\u7279\u5f81\u7b2c\u4e09\u7248\u72ec\u7acb\u53cd\u4f8b\u5ba1\u8ba1','--','env','PYTHONPATH=/mnt/d/codex/coin/src',
  '/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python',str(state/'probe.py')]},
 'independent_probe':{'directory':str(state),'script':str(state/'probe.py'),'script_sha256':sha(state/'probe.py'),'output':str(raw_path),'output_sha256':sha(raw_path)},
 'provided_actual_outputs':{'start_receipt':str(start_path),'start_receipt_sha256':sha(start_path),'execution_receipt':str(receipt_path),
  'execution_receipt_sha256':sha(receipt_path),'junit':str(xml_path),'junit_sha256':sha(xml_path),'junit_counts':counts,
  'actual_session':77221,'actual_exit_code':0,'bindings':output_bindings},
 'ten_model_actual_caller_routing':'NOT_AUDITED','probes':probes,'findings':findings,'acceptance_blocker_ids':[x['id'] for x in findings],
 'limits':['Only shared fixed feature adapter and synthetic primitive/causality/mask behavior were audited.',
  'All ten model actual caller routing, common caller calendar ledger and train-only normalization routing remain NOT_AUDITED.',
  'No market/model fitting, OOS result, alpha performance or P1 economic/statistical gate was assessed.',
  'Resource observations include imports/native allocation limitations; no sample-window cube is materialized by the single-endpoint API.',
  'Registry recovery bookkeeping and unrelated label-adapter repairs are outside this feature implementation audit.'],
 'decision':'Preserve older feature sources/evidence. Prior primitive defects are repaired, but validate contradictory traded/empty masks in a new immutable guard before claiming complete failclosed feature compliance. Keep NO_QUALIFIED_CANDIDATE and P1 statistical/economic gate NOT_EVALUATED.'}
report_path=root/'reports/fast_research/V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V2.json'
if report_path.exists():raise RuntimeError('Refusing to overwrite previous audit artifact')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(report_path),'report_sha256':sha(report_path),'created_at_utc':report['created_at_utc'],
 'status':report['status'],'old_counterexamples_all_fixed':report['previous_four_primitive_counterexamples_all_fixed'],
 'acceptance_blockers':report['acceptance_blocker_ids'],'HEAD_start':head_start,'HEAD_report':head_end,
 'source_v3_sha256':start_sha['scripts/research_v8/features_v3.py'],'tests_v3_sha256':start_sha['tests/test_v8_features_v3.py'],
 'output_bindings':output_bindings,'junit_counts':counts},indent=2))