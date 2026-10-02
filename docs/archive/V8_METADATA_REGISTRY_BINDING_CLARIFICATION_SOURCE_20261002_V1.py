import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path.insert(0,str(root))
from scripts.research_v8.registry import append_event,read_verified
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reg=root/'reports/experiment_registry.jsonl';history=read_verified(reg.read_bytes())
prior=next(e for e in history if e['event_id']=='V8_OFFICIAL_INPUT_FEASIBILITY_20261002_V1.json:ROOT_REGISTERED_RESULT')
meta=root/'reports/fast_research/V8_OFFICIAL_INPUT_METADATA_20261002_V1.json'
feas=root/'reports/fast_research/V8_OFFICIAL_INPUT_FEASIBILITY_20261002_V1.json'
script=root/'docs/archive/V8_OFFICIAL_INPUT_METADATA_SOURCE_20261002_V1.py'
event=dict(experiment_id='v8-official-metadata-provenance-clarification-20261002-v1',
 event_id='v8-official-metadata-provenance-clarification-20261002-v1:RESULT',event_type='OPERATIONAL_RESULT_BINDING_CLARIFICATION',
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=sha(meta),protocol_hash=sha(script),feature_set='NONE_OFFICIAL_METADATA_ONLY',labels='NONE',model_family='NONE',
 hyperparameters=dict(archive_bodies_read=0,rows_read=0,market_model_fits=0),seed='NOT_APPLICABLE_DETERMINISTIC_METADATA',
 thresholds='HTTP_HEADERS_AND_SMALL_OFFICIAL_CHECKSUM_EXISTENCE_ONLY_NOT_SOURCE_ACCEPTANCE',cost_assumptions='NOT_EVALUATED',
 all_folds=prior['all_folds'],success_failure='BOUND_ACTUAL_METADATA_INPUTS_CLARIFIED',
 reason_for_next_experiment='Small independent funding/mark/index archive QA; percentage-depth is not executable BBO/L5.',
 result_influenced_later_choice=True,trial_count_eligible=False,market_models_fit=0,
 clarification_of_event_sha256=prior['record_sha256'],artifact_path=str(feas.relative_to(root)),artifact_sha256=sha(feas),
 prior_parent_context_not_actual_metadata_run_inputs=True,
 clarification='Previous root review explicitly used parent diagnostic context. This event binds actual metadata inventory and exact metadata script instead; no rerun or new experiment.',
 protocol_hash_scope='Exact archived metadata script; this operational inspection has no model protocol',
 source_hashes={str(script.relative_to(root)):sha(script)})
saved=append_event(reg,event)
archive=root/'docs/archive/V8_METADATA_REGISTRY_BINDING_CLARIFICATION_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
receipt=dict(status='APPEND_ONLY_METADATA_RUN_BINDING_CLARIFICATION',created_utc=datetime.now(UTC).isoformat(),
 previous_root_review_record_sha256=prior['record_sha256'],new_clarification_record=saved,
 source_hashes={str(archive.relative_to(root)):sha(archive),str(script.relative_to(root)):sha(script)},
 verified_prior_files={str(meta.relative_to(root)):sha(meta),str(feas.relative_to(root)):sha(feas)},
 original_record_preserved=True,new_metadata_requests=0,new_model_fits=0,trial_count_eligible=False)
out=root/'reports/fast_research/V8_METADATA_REGISTRY_BINDING_CLARIFICATION_20261002_V1.json'
with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],receipt_sha256=sha(out))))
