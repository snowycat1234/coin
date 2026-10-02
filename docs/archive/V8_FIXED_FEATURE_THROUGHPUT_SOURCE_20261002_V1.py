import hashlib,json,os,resource,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');sys.path[:0]=[str(root),str(root/'tests')]
from test_v8_features import joint,decision
from scripts.research_v8.features_v4 import endpoint_features
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={p:sha(root/p) for p in ['scripts/research_v8/features.py','scripts/research_v8/features_v2.py',
 'scripts/research_v8/features_v3.py','scripts/research_v8/features_v4.py','tests/test_v8_features.py']}
event=dict.fromkeys(FIELDS)
event.update(event_id='v8-feature-throughput-20261002-v1:START',event_type='OPERATIONAL_START',
 experiment_id='v8-feature-throughput-20261002-v1',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=sources['tests/test_v8_features.py'],protocol_hash=sha(root/'protocols/FEATURE_V8_ACTIVE_IMPLEMENTATION_V4.json'),
 feature_set='FROZEN_478_SYNTHETIC_ONLY',labels='NONE',model_family='NONE',hyperparameters={'timing_calls':10},seed='NOT_APPLICABLE_DETERMINISTIC',
 thresholds='NO_MODEL_OR_THRESHOLD',cost_assumptions='NOT_EVALUATED',all_folds=[],success_failure='START',
 reason_for_next_experiment='Measure actual fixed-feature API cost before scheduling a shared four-fold first-layer cache; avoid impractical serial runtime.',
 result_influenced_later_choice=False,source_hashes=sources,environment_hash=sha(root/'environments/v8/uv.lock'),
 exact_command="bash scripts/with_task_progress.sh --title 'V8 共同特征吞吐实测 · 仅合成10端点' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python .cache/v8_feature_throughput_20261002_v1.py",trial_count_eligible=False,market_models_fit=0)
append_event(root/'reports/experiment_registry.jsonl',event)
j=joint.__wrapped__();d=decision.__wrapped__(j);progress=Progress();timings=[]
for i in range(10):
 start=time.perf_counter();out=endpoint_features(j,d);timings.append(time.perf_counter()-start)
 assert len(out.values)==478
 progress.update('同一固定特征API实际测量',i+1,10,'合成端点')
for p,h in sources.items():assert sha(root/p)==h
archive=root/'docs/archive/V8_FIXED_FEATURE_THROUGHPUT_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
receipt=dict(status='PASS_SYNTHETIC_THROUGHPUT_MEASUREMENT_NOT_MARKET_FIT',created_utc=datetime.now(UTC).isoformat(),
 registration_start=event,source_hashes=sources,source_archive_sha256=sha(archive),durations_seconds=timings,
 average_seconds_per_endpoint=sum(timings)/len(timings),upper_measured_seconds_per_endpoint=max(timings),
 mean_runtime_110000_endpoint_extrapolation_seconds=sum(timings)/len(timings)*110000,
 timing_extrapolation_not_guarantee=True,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 market_inputs_read=False,market_models_fit=0,locked_consumed=False,GPU_hours=0)
path=root/'reports/fast_research/V8_FIXED_FEATURE_THROUGHPUT_20261002_V1.json'
with path.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
append_event(root/'reports/experiment_registry.jsonl',dict(event,event_id='v8-feature-throughput-20261002-v1:RESULT',event_type='OPERATIONAL_RESULT',
 success_failure=receipt['status'],artifact_path=str(path.relative_to(root)),artifact_sha256=sha(path)))
progress.stop.set();print(json.dumps(dict(status=receipt['status'],seconds_per_endpoint=receipt['average_seconds_per_endpoint'],estimated_110000_seconds=receipt['mean_runtime_110000_endpoint_extrapolation_seconds'])))
