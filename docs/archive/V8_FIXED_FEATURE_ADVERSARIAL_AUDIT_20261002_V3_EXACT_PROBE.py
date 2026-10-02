from __future__ import annotations
import hashlib,json,resource,subprocess,sys,tracemalloc
from datetime import date,datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-fixed-feature-adversarial-20261002-v3')
sys.path.insert(0,str(root))
import numpy as np
import polars as pl
from scripts.research_v8 import features as definition,features_v2 as prior,features_v4 as active
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['protocols/FEATURE_CONTRACT_V8.json','protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json','protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V3.json',
 'scripts/research_v8/features.py','scripts/research_v8/features_v2.py','scripts/research_v8/features_v3.py',
 'tests/test_v8_features.py','tests/test_v8_features_v2.py','tests/test_v8_features_v3.py','environments/v8/uv.lock']
files += ['protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json','scripts/research_v8/features_v4.py','tests/test_v8_features_v4.py','src/quant/research_fast/dataset.py']
start_sha={p:sha(root/p) for p in files};head_start=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
contract=json.loads((root/files[0]).read_text());manifest=json.loads((root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json').read_text())
previous_audit_path=root/'reports/fast_research/V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V1.json'
previous_audit=json.loads(previous_audit_path.read_text());previous_audit_sha=sha(previous_audit_path)
if previous_audit_sha!='5997a1b021a541cd40df78ff03539ec9a541035ddb819b0bed56aa35363c8495':raise RuntimeError('Prior audit bytes changed')
bindings={'original_definition_contract_unchanged':start_sha[files[0]]=='1567496fd28bff5d0d4659c819ccb92f27de56ab94469c87de49a933b702c823',
 'definition_contract_binding':manifest['definition_contract_sha256']==start_sha[files[0]],
 'active_adapter_binding':manifest['active_adapter_sha256']==start_sha['scripts/research_v8/features_v4.py'],
 'preserved_adapter_binding':manifest['preserved_definition_adapter_sha256']==start_sha['scripts/research_v8/features.py'],
 'previous_active_manifest_binding':manifest['previous_active_contract_sha256']==start_sha[files[2]]}
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


checks=[]
def check(name,passed,evidence):
    checks.append({'id':name,'passed':bool(passed),'evidence':evidence})
    if not passed:findings.append({'id':name,'priority':'P2','status':'CONFIRMED_CONTRACT_IMPLEMENTATION_GAP','evidence':evidence})

healthy=probes[0]
check('V4_478_unchanged_names_units_and_endpoint_resources',all(healthy[k] for k in ('names_equal_contract','definitions_equal_frozen_adapter','values_finite','values_immutable')) and healthy['feature_count']==478 and healthy['output_bytes']==478*8,healthy)
future_check=next(p for p in probes if p['id']=='future_perturbation_all_primitives')
check('V4_all_stream_future_perturbation',all(future_check[k] for k in ('values_exactly_unchanged','availability_unchanged','extra_future_label_columns_ignored')),future_check)
for name in ('legitimate_undefined_return_impact_interarrival','legitimate_no_trade_bin_masks'):
    e=next(p for p in probes if p['id']==name)
    check('V4_'+name,e['accepted'] and e['equals_preserved_adapter'],e)

for name,changed,old_id in (
 ('false_empty_positive_activity',mutate(joint,[('empty_bin',True),('close',None),('vwap',None),('high',None),('low',None),('mean_trade_size',None),('max_trade_size',None)]),'V8F-03'),
 ('integer_empty_mask',joint.with_columns(pl.col(s+'__empty_bin').cast(pl.Int64)),'V8F-04')):
    meta,_=attempt(changed)
    regressions.append({'prior_finding':old_id,'probe':name,'status':'FIXED_IN_THIS_PROBE' if not meta['accepted'] else 'STILL_FAILING',**meta})
    check('V4_repeat_'+old_id,not meta['accepted'],meta)

# Same registered empty-mask requirement is checked at the past window edge and last bar.
for when in (decision-720*definition.BAR_US,decision-definition.BAR_US):
    meta,_=attempt(mutate(joint,[('empty_bin',True)],when))
    check('V4_false_empty_at_'+str(when),not meta['accepted'],meta)
for name,changed in (
 ('unknown_bool_mask',mutate(joint,[('empty_bin',None)])),
 ('float_mask',joint.with_columns(pl.col(s+'__empty_bin').cast(pl.Float64))),
 ('fractional_trade_count',mutate(joint,[('trade_count',10.5)])),
 ('disagree_aggregate_count',mutate(joint,[('agg_count',11)])),
 ('negative_interarrival_count',mutate(joint,[('interarrival_count',-.5)])),
 ('empty_positive_quote',mutate(legal_empty,[('quote_notional',1)])),
 ('empty_positive_base',mutate(legal_empty,[('base_volume',1)])),
 ('empty_positive_interarrival',mutate(legal_empty,[('interarrival_count',1)])),
 ('unknown_traded_vwap',mutate(joint,[('vwap',None)])),
 ('unknown_traded_size',mutate(joint,[('mean_trade_size',None)])),
 ('negative_traded_size',mutate(joint,[('mean_trade_size',-.5)])),
 ('invalid_traded_flow_units',mutate(joint,[('flow_imbalance',100.)]))):
    meta,_=attempt(changed);check('V4_input_'+name,not meta['accepted'],meta)

for name,changed,when in (
 ('past_late',mutate(joint,[('available_us',decision+1)]),decision),
 ('past_quality_unknown',mutate(joint,[('quality',None)]),decision),
 ('past_grid_missing',joint.filter(pl.col('timestamp')!=stamp),decision),
 ('past_grid_duplicate',pl.concat([joint,joint.filter(pl.col('timestamp')==stamp)]),decision),
 ('fractional_decision',joint,float(decision)+.75),
 ('boolean_decision',joint,True),
 ('locked_decision_metadata_only',joint,definition.day_us(definition.LOCKED))):
    meta,_=attempt(changed,when);check('V4_boundary_'+name,not meta['accepted'],meta)
print('Independent V4 primitive/mask/causality probes completed',flush=True)

prior_v2_path=root/'reports/fast_research/V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V2.json'
prior_v2_sha=sha(prior_v2_path)
if prior_v2_sha!='ad9c4e48b741a3c29f5e8b2f599571222e32b1621f16a2be32f903e8e03cdf02':raise RuntimeError('Second prior independent audit changed')
start_path=root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V4.json'
receipt_path=root/'reports/fast_research/V8_FIXED_FEATURE_CHECK_RECEIPT_20261002_V4.json'
xml_path=root/'reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V4.xml'
start=json.loads(start_path.read_text());execution=json.loads(receipt_path.read_text());tree=ET.parse(xml_path);suites=tree.findall('.//testsuite')
counts={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','errors','failures','skipped')}
output_bindings={'all_provided_feature_source_hashes_equal':all(start['source_hashes'][p]==execution['source_hashes'][p]==start_sha[p] for p in start['source_hashes']),
 'protocol_equals_active_manifest':start['protocol_hash']==execution['protocol_hash']==start_sha['protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json'],
 'definition_original_dependency':contract['original_source_sha256']==start_sha['src/quant/research_fast/dataset.py'],
 'lock_equals_current':start['environment_hash']==execution['environment_hash']==start_sha['environments/v8/uv.lock'],
 'command_equal':start['exact_command']==execution['exact_command'],
 'start_receipt_digest_equal':sha(start_path)==execution['start_receipt_sha256'],
 'junit_digest_equal':sha(xml_path)==execution['junit_sha256'],
 'junit_counts_equal':counts==execution['junit_counts']=={'tests':16,'errors':0,'failures':0,'skipped':0},
 'actual_session_exit_zero':execution['actual_unified_session_id']==68984 and execution['actual_unified_exit_code']==execution['actual_task']['exit_code']==0}
if not all(output_bindings.values()):raise RuntimeError('Actual feature output binding mismatch')
end_sha={p:sha(root/p) for p in files}
if end_sha!=start_sha:raise RuntimeError('Audited source changed during probe')
if sha(previous_audit_path)!=previous_audit_sha or sha(prior_v2_path)!=prior_v2_sha:raise RuntimeError('Prior audit artifacts changed')
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
raw={'verified_source_hashes':start_sha,'prior_counterexamples':regressions,'probes':probes,'additional_checks':checks,'findings':findings}
raw_path=state/'probes.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
report={'report_id':'V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V3','audited_active_adapter':'scripts/research_v8/features_v4.py',
 'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'FAIL_FEATURE_CONTRACT_IMPLEMENTATION' if findings else 'PASS_FEATURE_CONTRACT_IMPLEMENTATION',
 'candidate_status':'NO_QUALIFIED_CANDIDATE','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_probe_start':head_start,'actual_HEAD_at_report':head_end,'verified_source_hashes':start_sha,
 'source_unchanged_during_probe':True,'definition_and_active_manifest_bindings':bindings,
 'preserved_prior_independent_audits':[{'path':str(previous_audit_path),'sha256':previous_audit_sha},{'path':str(prior_v2_path),'sha256':prior_v2_sha}],
 'prior_counterexamples_all_fixed_in_this_probe':all(r['status']=='FIXED_IN_THIS_PROBE' for r in regressions),
 'prior_counterexample_results':regressions,'probes':probes,'additional_checks':checks,'findings':findings,'acceptance_blocker_ids':[f['id'] for f in findings],
 'scope':{'read_market_data':False,'read_real_locked_or_model_artifacts':False,'fit_market_model':False,'GPU_used':False,
  'read_builder_explanations_or_root_state_documents':False,'source_modified':False,'top_level_docs_modified':False,
  'python':sys.executable,'PYTHONPATH':'/mnt/d/codex/coin/src','resource_policy':'hpc_linux with_task_progress/bounded.sh shared 5GB RAM, swap0, GPU0',
  'experiment_registry_writer':'root agent; auditor did not append shared registry'},
 'execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--','bash','-lc',
  'cd /mnt/d/codex/coin && scripts/with_task_progress.sh --title V8共同特征第四版独立反例审计 -- env PYTHONPATH=/mnt/d/codex/coin/src /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /home/xflops/coin-state/test-v8-fixed-feature-adversarial-20261002-v3/probe.py']},
 'independent_probe':{'directory':str(state),'script':str(state/'probe.py'),'script_sha256':sha(state/'probe.py'),'output':str(raw_path),'output_sha256':sha(raw_path)},
 'provided_actual_outputs':{'start_receipt':str(start_path),'start_receipt_sha256':sha(start_path),'execution_receipt':str(receipt_path),
  'execution_receipt_sha256':sha(receipt_path),'junit':str(xml_path),'junit_sha256':sha(xml_path),'junit_counts':counts,
  'actual_session':68984,'actual_exit_code':0,'verified_bindings':output_bindings},
 'ten_model_actual_caller_routing':'NOT_AUDITED',
 'limits':['Conclusion covers the specified fixed 478-feature definitions and V4 adapter guards, measured single-endpoint outputs and synthetic past-only/mask boundaries.',
  'All ten model actual caller routing, shared calendar ledger and train-only normalization wiring remain NOT_AUDITED.',
  'No full market source semantic derivation, market fit, OOS performance, P1 economic/statistical gate, fills/costs or alpha qualification was evaluated.',
  'Resource observations include imported/native library limitations; no sample-window cube was materialized by the single-endpoint API.',
  'Registered unknown return/interarrival and genuine zero-activity empty masks are preserved exactly; old source and negative evidence remain unchanged.'],
 'decision':'PASS_FEATURE_CONTRACT_IMPLEMENTATION for verified V4 adapter/manifest hashes in this scope only. Keep ten-model actual caller routing NOT_AUDITED, NO_QUALIFIED_CANDIDATE, and P1 statistical/economic gate NOT_EVALUATED.' if not findings else 'Block this specified feature implementation on the independently reproduced findings; no economic or alpha inference.'}
path=root/'reports/fast_research/V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V3.json'
if path.exists():raise RuntimeError('Refusing to overwrite prior audit artifact')
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(path),'report_sha256':sha(path),'status':report['status'],
 'prior_counterexamples_fixed':report['prior_counterexamples_all_fixed_in_this_probe'],'additional_checks':len(checks),
 'blockers':report['acceptance_blocker_ids'],'provided_output_bindings':output_bindings,
 'active_source_sha256':start_sha['scripts/research_v8/features_v4.py'],'active_manifest_sha256':start_sha['protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json'],
 'actual_HEAD_at_probe_start':head_start,'actual_HEAD_at_report':head_end},indent=2))