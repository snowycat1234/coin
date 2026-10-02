import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');sys.path.insert(0,str(ROOT))
from scripts.research_v8.registry import append_event,read_verified
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={};proofs={};archives=[]
def read(name):
 p=ROOT/'reports/fast_research'/name;proofs[str(p.relative_to(ROOT))]=sha(p);return json.loads(p.read_text())
def bind(m):
 for p,h in m.items():
  assert sha(ROOT/p)==h,p
  assert p not in sources or sources[p]==h,p
  sources[p]=h
def copy(original,rel,expected=None):
 p=Path(original);h=sha(p)
 if expected:assert h==expected,str(p)
 v=p.read_bytes();assert len(v)<4_000_000
 dest=ROOT/rel
 if dest.exists():assert dest.read_bytes()==v,rel
 else:
  with dest.open('xb') as f:f.write(v)
 proofs[rel]=h;archives.append(dict(original=str(p),archive=rel,sha256=h,bytes=len(v)))

r=read('V8_NONOVERLAP_MECHANISM_20261002_V3.json');a=read('V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V2.json')
assert a['status']=='PASS_COMPLETE_CALENDAR_SUPPLEMENT_SCOPE' and not a['acceptance_blocker_ids']
assert a['independent_checker_execution']['exit_code']==0
assert a['statistics_canonical_sha256']==r['supplement']['new_statistics_canonical_sha256']==r['supplement']['original_statistics_canonical_sha256']
bind(a['verified_runner_dependency_hashes']);bind(r['source_hashes'])
for item in a['verified_input_artifacts'].values():
 p=Path(item['path']);assert sha(p)==item['sha256'];proofs[str(p.relative_to(ROOT))]=item['sha256']
for f in r['folds']:assert sha(Path(f['calendar_path']))==f['calendar_sha256']
assert r['supplement']['added_rows']==240 and r['supplement']['added_outcome_valid_rows']==0
for c in r['supplement']['fold_checks']:
 assert c['full_TRAIN_minutes_per_variant']==17280 and c['OOS_minutes_per_variant']==10080
 assert c['original_all_rows_bitwise_unchanged'] and c['original_scored_rows_bitwise_unchanged']
old=read('V8_NONOVERLAP_MECHANISM_20261002_V2.json');old_audit=read('V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V1.json')
assert old_audit['status']=='FAIL_DIAGNOSTIC_CALENDAR_SCOPE' and old_audit['complete_TRAIN_missing_variant_rows']==240
read('V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_20261002_V2.json');actual=read('V8_NONOVERLAP_ACTUAL_EXECUTION_RECEIPT_20261002_V3.json')
bind(actual['source_hashes']);assert actual['actual_unified_session_id']==95905 and actual['actual_unified_exit_code']==0
task=json.loads((STATE/'task-progress/task-661405bfeea8411aade407d66bc65fe4.json').read_text())
assert task==actual['actual_task'] and task['exit_code']==0 and task['status']=='completed'
recheck=read('V8_NONOVERLAP_TASK_PATH_RECHECK_20261002_V1.json');assert recheck['status']=='PASS_ACTUAL_TASK_PATH_RECHECK'
for n in ('V8_NONOVERLAP_API_SMOKE_20261002_V1.json','V8_NONOVERLAP_PRESTART_FAILURE_20261002_V1.json',
 'V8_NONOVERLAP_SOURCE_STATIC_REVIEW_20261002_V1.json'):read(n)
for rel in ('scripts/research_v8/nonoverlap_mechanism.py','scripts/research_v8/smoke_nonoverlap_mechanism.py',
 'protocols/NONOVERLAP_MECHANISM_V8_V1.json','docs/archive/V8_NONOVERLAP_SOURCE_STATIC_REVIEW_SOURCE_20261002_V1.py'):
 bind({rel:sha(ROOT/rel)})
for name,o in (('V1',old_audit),('V2',a)):
 p=o['independent_checker'];tag='V8_NONOVERLAP_INDEPENDENT_AUDIT_'+name
 copy(Path(p['directory'])/'check_outputs.py','docs/archive/'+tag+'_EXACT_CHECKER_20261002.py',p['script_sha256'])
 copy(p.get('output_path',p.get('output')),'reports/fast_research/'+tag+'_EXACT_OUTPUT_20261002.json',p['output_sha256'])
for name in ('v8_mechanism_receipt_adapter_v2_20261001_v1.py',):
 pass
for name in ('v8_mechanism_receipt_adapter_v2_20261002_v1.py','v8_mechanism_execution_receipt_20261002_v2.py'):
 copy(ROOT/'.cache'/name,'docs/archive/'+name.upper())
copy(actual['run_binding_path'],'reports/fast_research/V8_NONOVERLAP_SUPPLEMENT_ACTUAL_RUN_BINDING_20261002_V1.json',actual['run_binding_sha256'])

meta_archive=read('V8_OFFICIAL_INPUT_SOURCE_ARCHIVE_20261002_V1.json')
assert meta_archive['status']=='EXACT_SOURCE_ARCHIVE_VERIFIED' and meta_archive['metadata_exit_code']==0
for x in meta_archive['report_bindings']:
 p=x['path'].replace('\\','/');assert sha(ROOT/p)==x['sha256'];proofs[p]=x['sha256']
for x in meta_archive['source_bindings']:
 assert sha(ROOT/x['source'])==sha(ROOT/x['archive'])==x['sha256'];sources[x['archive']]=x['sha256']
feas=read('V8_OFFICIAL_INPUT_FEASIBILITY_20261002_V1.json');meta=read('V8_OFFICIAL_INPUT_METADATA_20261002_V1.json')
assert not meta['archive_bodies_downloaded'] and not meta['row_or_model_outcomes_read'] and not meta['locked_consumed']
metadata_task=json.loads((STATE/'task-progress/task-ac50f1d742454a85b18fc2bde3f1e4a1.json').read_text())
assert metadata_task['status']=='completed' and metadata_task['exit_code']==0

history=read_verified((ROOT/'reports/experiment_registry.jsonl').read_bytes())
for exp in ('v8-nonoverlap-mechanism-20261002-v2','v8-nonoverlap-calendar-supplement-20261002-v3'):
 e=next(x for x in history if x['event_id']==exp+':RESULT');assert e['artifact_sha256']==proofs['reports/fast_research/'+('V8_NONOVERLAP_MECHANISM_20261002_V2.json' if exp.endswith('v2') else 'V8_NONOVERLAP_MECHANISM_20261002_V3.json')]
base={k:r['registration_start'][k] for k in ('git_commit','data_manifest_hash','protocol_hash','feature_set','labels','model_family','hyperparameters','seed','thresholds','cost_assumptions','all_folds')}
registered=[]
for name,status in (
 ('V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V1.json','FAIL_DIAGNOSTIC_CALENDAR_SCOPE'),
 ('V8_NONOVERLAP_MECHANISM_INDEPENDENT_AUDIT_20261002_V2.json','PASS_COMPLETE_CALENDAR_SUPPLEMENT_SCOPE'),
 ('V8_NONOVERLAP_TASK_PATH_RECHECK_20261002_V1.json','PASS_ACTUAL_TASK_PATH_RECHECK'),
 ('V8_OFFICIAL_INPUT_FEASIBILITY_20261002_V1.json','OFFICIAL_METADATA_ROUTE_FEASIBILITY_ONLY')):
 event=base|dict(experiment_id=name.removesuffix('.json'),event_id=name+':ROOT_REGISTERED_RESULT',
 event_type='INDEPENDENT_AUDIT_RESULT_OR_METADATA_REVIEW',success_failure=status,
 reason_for_next_experiment='Bound actual nonoverlap evidence selects limited strictOOF falsification plus funding/mark/index frontier QA; no deeper family.',
 result_influenced_later_choice=True,artifact_path='reports/fast_research/'+name,artifact_sha256=proofs['reports/fast_research/'+name],
 trial_count_eligible=False,market_models_fit=0,metadata_from='Parent diagnostic binding describes reviewed experiment; metadata review is not a new market-model trial')
 registered.append(append_event(ROOT/'reports/experiment_registry.jsonl',event)['record_sha256'])
rows=[dict(fold=f['fold'],variant=v['variant'],flow_stream=p['flow_stream'],spearman=p['test']['spearman'],
 train_signed_mean_response_bps=p['train_signed_mean_response_bps'],OOS_sign_agreement=p['OOS_sign_agreement'])
 for f in r['folds'] for v in f['variants'] for p in v['pairs'] if p['primary']]
assert len(rows)==24
archive=ROOT/'docs/archive/V8_MECHANISM_ROUTE_ROOT_ACCEPTANCE_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
sources[str(archive.relative_to(ROOT))]=sha(archive)
receipt=dict(status='ROOT_PASS_NONOVERLAP_DIAGNOSTIC_V3_AND_OFFICIAL_METADATA_ROUTE_EVIDENCE_ONLY',
 created_utc=datetime.now(UTC).isoformat(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 data_hash=r['registration_start']['data_manifest_hash'],protocol_hash=r['registration_start']['protocol_hash'],
 environment_hash=sha(ROOT/'environments/v8/uv.lock'),seed=None,
 exact_command='bash scripts/bounded.sh /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python .cache/v8_mechanism_route_root_acceptance_20261002_v1.py',
 source_hashes=sources,verified_prior_files=proofs,exact_archives=archives,actual_supplement_task=task,actual_metadata_task=metadata_task,
 root_registered_result_record_sha256=registered,descriptive_hypotheses=96,independent_trial_count='UNKNOWN_NOT_96',
 primary_rows=rows,primary_spearman_min=min(x['spearman'] for x in rows),primary_spearman_max=max(x['spearman'] for x in rows),
 primary_abs_spearman_max=max(abs(x['spearman']) for x in rows),primary_train_OOS_sign_agreements=sum(x['OOS_sign_agreement'] for x in rows),
 primary_train_signed_response_min_bps=min(x['train_signed_mean_response_bps'] for x in rows),
 primary_train_signed_response_max_bps=max(x['train_signed_mean_response_bps'] for x in rows),
 candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',classification='SCREENING_MECHANISM_AND_SOURCE_FEASIBILITY_ONLY',
 P1_gate='NOT_READY',next_depth_gate_allowed=False,net_CAGR=None,gross_executed_edge=None,net_executed_edge=None,
 strongest_benchmark_delta=None,break_even_roundtrip_cost=None,multiple_testing_corrected_evidence=None,PnL_concentration=None,
 locked_consumed=False,market_models_fit=0,orders_sent=0,GPU_hours=0,
 next_highest_information_gain='One preregistered strictOOF first-layer surprise vs matchedDIRECT and common risk/cost evaluator; in parallel small official funding+mark/index independent QA.',
 limitations=['Observed future flow is not a predictor or a tradable ceiling; response statistic is not net edge.',
 'Four dispersed months do not establish four independent economic regimes; selection follows observed diagnostic and is registered.',
 'Historical bookDepth is percentage-band30s aggregate, not trueL5/BBO; HEAD+CHECKSUM existence is not archive/source acceptance.',
 'BBO/size/latency/historical fees, complete riskmatched benchmark and multiple-testing history are incomplete.',
 'No new full disk scan; last actual19.355GB is a dated measurement, not instantaneous.'])
out=ROOT/'reports/fast_research/V8_MECHANISM_ROUTE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],receipt_sha256=sha(out),primary_abs_spearman_max=receipt['primary_abs_spearman_max'],P1_gate=receipt['P1_gate'])))
