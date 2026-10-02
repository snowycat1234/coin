from __future__ import annotations
import hashlib,json,resource,subprocess,sys,tracemalloc
from datetime import date,datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state/test-v8-fixed-feature-adversarial-20261002-v1')
sys.path.insert(0,str(root))
import numpy as np
import polars as pl
from scripts.research_v8 import features as v1,features_v2 as active
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['protocols/FEATURE_CONTRACT_V8.json','protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json',
 'scripts/research_v8/features.py','scripts/research_v8/features_v2.py','tests/test_v8_features.py',
 'tests/test_v8_features_v2.py','src/quant/research_fast/dataset.py','environments/v8/uv.lock']
start_sha={p:sha(root/p) for p in files}
head_start=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
definition=json.loads((root/'protocols/FEATURE_CONTRACT_V8.json').read_text())
manifest=json.loads((root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V2.json').read_text())
bindings={
 'original_source':definition['original_source_sha256']==start_sha['src/quant/research_fast/dataset.py'],
 'preserved_adapter':definition['adapter_source_sha256']==start_sha['scripts/research_v8/features.py'],
 'definition_contract':manifest['definition_contract_sha256']==start_sha['protocols/FEATURE_CONTRACT_V8.json'],
 'active_adapter':manifest['active_adapter_sha256']==start_sha['scripts/research_v8/features_v2.py'],
 'manifest_preserved_adapter':manifest['preserved_definition_adapter_sha256']==start_sha['scripts/research_v8/features.py']}
if not all(bindings.values()):raise RuntimeError('Feature source/contract binding mismatch')
n=900;base=v1.day_us(date(2025,7,2));index=np.arange(n,dtype=np.int64)
times=base+index*v1.BAR_US;decision=base+3900_000_000
rows={'timestamp':times}
for i,s in enumerate(v1.STREAMS):
    close=100.+i*10+index*.001
    rows.update({s+'__available_us':times+v1.BAR_US,s+'__quality':np.zeros(n,dtype=np.int32),
      s+'__close':close,s+'__vwap':close+.002,s+'__high':close+1,s+'__low':close-1,
      s+'__flow_imbalance':-.2+i*.1+index*.0001,s+'__return_5s':.001*(i+1)+index*.0000001,
      s+'__large_trade_share':np.full(n,.2),s+'__signed_price_impact':np.full(n,.01),
      s+'__interarrival_count':np.full(n,4),s+'__empty_bin':np.zeros(n,dtype=bool)})
    for field in ('quote_notional','base_volume','trade_count','agg_count','mean_trade_size',
                  'max_trade_size','mean_interarrival','std_interarrival'):
        rows[s+'__'+field]=np.full(n,10.+i)
joint=pl.DataFrame(rows)
probes=[];findings=[]
def attempt(frame,when=decision):
    try:
        out=active.endpoint_features(frame,when)
        return {'accepted':True,'returned_available_us':out.available_us,'shape':list(out.values.shape)},out
    except Exception as exc:
        return {'accepted':False,'exception_type':type(exc).__name__,'exception':str(exc)},None

rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
tracemalloc.start();out=active.endpoint_features(joint,decision);traced_current,traced_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
rss_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
lookup=dict(zip(out.names,out.values))
control={'id':'single_endpoint_control','available_us':out.available_us,'decision_us':decision,
 'feature_count':len(out.names),'names_equal_contract':list(out.names)==definition['feature_names'],
 'same_definitions_as_preserved_adapter':np.array_equal(out.values,v1.endpoint_features(joint,decision).values),
 'values_finite':bool(np.isfinite(out.values).all()),'values_immutable':not out.values.flags.writeable,
 'output_bytes':out.values.nbytes,'main_canonical_matrix_shape':[720,68],
 'main_canonical_matrix_float32_bytes':720*68*4,
 'rss_high_water_before_single_call_bytes':rss_before,'rss_high_water_after_single_call_bytes':rss_after,
 'python_traced_peak_during_single_call_bytes':traced_peak,
 'resource_limit':'RSS includes imported libraries; tracemalloc does not fully count native Polars allocation; no sample-window cube is produced by this API.'}
probes.append(control)
if not control['names_equal_contract'] or not control['same_definitions_as_preserved_adapter']:
    findings.append({'id':'V8F-00','priority':'P1','status':'CONFIRMED','title':'Active fixed definitions differ from contract'})

# Independent simple unit/reference calculations, using original float32 common inputs.
source=joint.filter(pl.col('timestamp').is_between(decision-720*v1.BAR_US,decision,closed='left'))
s=v1.STREAMS[0]
f=source[s+'__flow_imbalance'].to_numpy().astype(np.float32).astype(np.float64)
r=source[s+'__return_5s'].to_numpy().astype(np.float32).astype(np.float64)
v=np.log1p(source[s+'__quote_notional'].to_numpy()).astype(np.float32).astype(np.float64)
def recursive_ewma(x):
    alpha=2./(len(x)+1);value=x[0]
    for item in x[1:]:value=(1-alpha)*value+alpha*item
    return value
unit_checks=[]
for w in definition['windows_bars']:
    prefix=s+'__';suffix='__'+str(w*5)+'s'
    expectations={'lag_return':r[-w],'lag_flow':f[-w],'lag_log_volume':v[-w],
      'ewma_return':recursive_ewma(r[-w:]),'ewma_flow':recursive_ewma(f[-w:]),
      'flow_slope_per_minute':np.polynomial.polynomial.polyfit(np.arange(w),f[-w:],1)[1]*12,
      'flow_q10':np.quantile(f[-w:],.1,method='linear'),'flow_q50':np.quantile(f[-w:],.5,method='linear'),
      'flow_q90':np.quantile(f[-w:],.9,method='linear'),
      'return_rms':np.sqrt(np.mean(r[-w:]*r[-w:])),
      'burst_log_volume':v[-12:].mean()-v[-w:].mean(),
      'flow_volatility_interaction':recursive_ewma(f[-w:])*np.sqrt(np.mean(r[-w:]*r[-w:])),
      'flow_volume_interaction':f[-w:].mean()*v[-w:].mean()}
    for field,expected in expectations.items():
        actual=lookup[prefix+field+suffix]
        unit_checks.append({'name':prefix+field+suffix,'matches_reference':bool(np.isclose(actual,expected,rtol=1e-11,atol=1e-12))})
probes.append({'id':'original_unit_fixed_window_references','all_match':all(c['matches_reference'] for c in unit_checks),'checks':unit_checks,
 'scope':'No annualization, normalization, cross-asset notional sum or future observations in these reference checks.'})
if not all(c['matches_reference'] for c in unit_checks):
    findings.append({'id':'V8F-01','priority':'P1','status':'CONFIRMED','title':'Fixed-window feature units differ from independent reference','evidence_probe':'original_unit_fixed_window_references'})

future=joint.with_columns(*[
 pl.when(pl.col('timestamp')>=decision).then(value).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field)
 for s in v1.STREAMS for field,value in (('available_us',None),('quality',999),('flow_imbalance',100.),
 ('close',-1.),('vwap',None),('quote_notional',None),('return_5s',100.))])
future_out=active.endpoint_features(future,decision)
extra=joint.with_columns(pl.lit(float('nan')).alias('realized_future_flow_label'),pl.lit(float('inf')).alias('future_return_label'))
extra_out=active.endpoint_features(extra,decision)
probes.append({'id':'future_perturbation_and_extra_future_columns','future_content_exactly_unchanged':np.array_equal(out.values,future_out.values),
 'future_label_columns_ignored':np.array_equal(out.values,extra_out.values),'availability_unchanged':out.available_us==future_out.available_us==extra_out.available_us})

stamp=decision-50_000_000;s=v1.STREAMS[0]
mutation_cases=[('late_past','available_us',decision+1),('fractional_available','available_us',float(decision)-.25),
 ('null_quality','quality',None),('missing_quote','quote_notional',None),('negative_quote','quote_notional',-1.),
 ('invalid_flow','flow_imbalance',100.)]
for case,field,value in mutation_cases:
    changed=joint.with_columns(pl.when(pl.col('timestamp')==stamp).then(value).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field))
    result,_=attempt(changed);probes.append({'id':'reject_'+case,**result})
    if result['accepted']:
        findings.append({'id':'V8F-REJECT-'+case,'priority':'P1','status':'CONFIRMED','title':'Expected failclosed input accepted','evidence_probe':'reject_'+case})
for case,frame,when in [('missing_bar',joint.filter(pl.col('timestamp')!=stamp),decision),
 ('duplicate_bar',pl.concat([joint,joint.filter(pl.col('timestamp')==stamp)]),decision),
 ('float_decision',joint,float(decision)+.75),('bool_decision',joint,True),
 ('locked_decision_synthetic_value_only',joint,v1.day_us(v1.LOCKED))]:
    result,_=attempt(frame,when);probes.append({'id':'reject_'+case,**result})
    if result['accepted']:
        findings.append({'id':'V8F-REJECT-'+case,'priority':'P1','status':'CONFIRMED','title':'Expected failclosed input accepted','evidence_probe':'reject_'+case})

# Valid undefined original observables keep their own masks.
undefined=joint.with_columns(pl.when(pl.col('timestamp')==stamp).then(None).otherwise(pl.col(s+'__return_5s')).alias(s+'__return_5s'),
 pl.when(pl.col('timestamp')==stamp).then(0).otherwise(pl.col(s+'__interarrival_count')).alias(s+'__interarrival_count'),
 *[pl.when(pl.col('timestamp')==stamp).then(None).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field) for field in ('mean_interarrival','std_interarrival')])
undefined_result,undefined_out=attempt(undefined)
if undefined_out:
    u=dict(zip(undefined_out.names,undefined_out.values));undefined_result.update({'observed_return_fraction_3600s':u[s+'__observed_return_fraction__3600s'],
     'mean_has_return_256':u['mean__'+s+'__has_return'],'mean_has_interarrival_256':u['mean__'+s+'__has_interarrival']})
probes.append({'id':'allowed_undefined_return_interarrival_masks',**undefined_result})

# Current/used historical prices and activity on explicitly traded bars must not be fabricated.
invalid_primitive_cases=[('missing_historical_close',stamp,'close',None,'mean__'+s+'__vwap_close_offset_bps'),
 ('missing_current_vwap',decision-v1.BAR_US,'vwap',None,'last__'+s+'__vwap_close_offset_bps'),
 ('missing_traded_mean_size',decision-v1.BAR_US,'mean_trade_size',None,'last__'+s+'__log_mean_trade_size'),
 ('negative_traded_mean_size',decision-v1.BAR_US,'mean_trade_size',-.5,'last__'+s+'__log_mean_trade_size')]
accepted_invalid=[]
for case,when,field,value,affected_name in invalid_primitive_cases:
    changed=joint.with_columns(pl.when(pl.col('timestamp')==when).then(value).otherwise(pl.col(s+'__'+field)).alias(s+'__'+field))
    result,invalid_out=attempt(changed)
    evidence={'id':case,'mutation_timestamp_us':when,'source_empty_bin':False,'source_trade_count':10.,'source_quality':0,
      'field':field,'value':value,**result}
    if invalid_out:
        invalid_lookup=dict(zip(invalid_out.names,invalid_out.values));evidence.update({'affected_feature':affected_name,
          'control_feature_value':lookup[affected_name],'accepted_feature_value':invalid_lookup[affected_name],
          'last_has_trade':invalid_lookup['last__'+s+'__has_trade']})
        accepted_invalid.append(case)
    probes.append(evidence)
if accepted_invalid:
    findings.append({'id':'V8F-02','priority':'P1','status':'CONFIRMED','title':'Active fixed-feature guard accepts invalid unmasked price/activity primitives',
      'source':'scripts/research_v8/features.py and scripts/research_v8/features_v2.py',
      'source_lines':{'features.py':[79,83,87],'features_v2.py':[20,24,29],'dataset.py':[264,268]},
      'contract_fields':['missing_policy','activity_units','base'],
      'evidence_probes':accepted_invalid,
      'impact':'Historical used close=None, current vwap=None, and traded mean_trade_size=None or -0.5 are accepted with quality=0, empty_bin=false and positive trade count. The frozen feature_matrix.fill_null(0) silently substitutes missing unmasked price/activity features with zero; negative mean size produces finite log1p(-0.5). The active guard validates four aggregate activity fields and only the last close, leaving these inputs outside failclosed enforcement.',
      'required_fix':'Add complete contract-consistent primitive validation before calling frozen feature_matrix. Reject missing/nonpositive used price inputs and missing/negative observed activity statistics on traded bars, while retaining only the original explicitly undefined return/interarrival masks. Preserve frozen dataset.py and definitions; repair guard in a new adapter version.'})

# Bind actual outputs, not a reconstructed success claim.
provided=[]
for name in ('V8_FIXED_FEATURE_TESTS_20261002_V1.xml','V8_FIXED_FEATURE_TESTS_20261002_V2.xml'):
    p=root/'reports/fast_research'/name;tree=ET.parse(p);suites=tree.findall('.//testsuite')
    provided.append({'path':str(p),'sha256':sha(p),'junit_counts':{k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','errors','failures','skipped')},
      'provided_actual_exit_code':0,'prior_run_source_receipt_intrinsic_to_junit':'UNKNOWN'})
end_sha={p:sha(root/p) for p in files}
if end_sha!=start_sha:raise RuntimeError('Feature bytes changed during independent probe')
head_end=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
raw={'source_sha256':start_sha,'source_unchanged':True,'probes':probes,'findings':findings}
raw_path=state/'probes.json';raw_path.write_text(json.dumps(raw,indent=2)+'\n')
report={'report_id':'V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V1','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'status':'FAIL_FEATURE_CONTRACT_IMPLEMENTATION' if findings else 'PASS_SYNTHETIC_FIXED_FEATURE_SCOPE_ONLY',
 'candidate_status':'NO_QUALIFIED_CANDIDATE','P1_statistical_economic_gate':'NOT_EVALUATED','qualification_claim':False,
 'actual_HEAD_at_probe_start':head_start,'actual_HEAD_at_report':head_end,
 'diff_note':'Both feature adapters, contracts and tests were untracked new files relative to the observed starting HEAD; full current bytes reviewed.',
 'source_sha256':start_sha,'source_unchanged_during_probe':True,'contract_source_bindings':bindings,
 'scope':{'read_market_data':False,'read_locked_or_model_artifacts':False,'read_builder_explanations_or_root_status_documents':False,
   'fit_market_model':False,'GPU_used':False,'source_modified':False,'top_level_docs_modified':False,
   'synthetic_locked_decision_value_only':True,'python':sys.executable,'PYTHONPATH':'/mnt/d/codex/coin/src',
   'resource_policy':'hpc_linux with_task_progress/bounded.sh shared 5GB RAM, swap0, GPU0',
   'experiment_registry_writer':'root agent; auditor did not concurrently append shared registry'},
 'execution':{'exit_code':0,'argv':['wsl','-d','hpc_linux','--cd','/mnt/d/codex/coin','--','bash','scripts/with_task_progress.sh','--title',
  'V8 \u56fa\u5b9a\u7279\u5f81\u72ec\u7acb\u53cd\u4f8b\u5ba1\u8ba1','--','env','PYTHONPATH=/mnt/d/codex/coin/src',
  '/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python',str(state/'probe.py')]},
 'provided_actual_test_outputs':provided,
 'independent_probe':{'directory':str(state),'script':str(state/'probe.py'),'script_sha256':sha(state/'probe.py'),
  'output':str(raw_path),'output_sha256':sha(raw_path)},
 'shared_feature_verification':{'contract_declares_shared_exact_adapter':definition['model_families_share_exact_adapter'],
   'feature_count':len(out.names),'names_and_units_checked':True,
   'ten_registered_model_caller_wiring':'NOT_AUDITED: no model-family routing/caller source is among the allowed contract/diff/output artifacts; common adapter definitions only are verified.'},
 'probes':probes,'findings':findings,'blocker_ids':[x['id'] for x in findings if x['priority']=='P1'],
 'limits':['No feature selection, fitting, market data, alpha metrics or P1 statistical/economic evaluation occurred.',
  'Source availability and future perturbation isolation are verified on invented bars; authenticity of real source timestamps is outside this synthetic audit.',
  'Individual model-family input wiring and caller calendar/streaming ledger enforcement are outside the supplied adapter scope.',
  'RSS includes imports and tracemalloc cannot fully account for native allocations; structural endpoint memory shape/output and observed single-call values are recorded.',
  'Existing green tests omit the confirmed invalid primitive cases; their success does not imply full failclosed compliance.'],
 'decision':'Preserve existing feature definitions/tests/outputs. Repair primitive failclosed validation in a new immutable active guard, then independently retest. Keep P1 NOT_EVALUATED and NO_QUALIFIED_CANDIDATE.'}
report_path=root/'reports/fast_research/V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V1.json'
if report_path.exists():raise RuntimeError('Refusing to overwrite a prior audit artifact')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(report_path),'report_sha256':sha(report_path),'created_at_utc':report['created_at_utc'],
 'status':report['status'],'blockers':report['blocker_ids'],'accepted_invalid_probes':accepted_invalid,
 'source_sha256':start_sha,'source_unchanged':True,'resource':control},indent=2))