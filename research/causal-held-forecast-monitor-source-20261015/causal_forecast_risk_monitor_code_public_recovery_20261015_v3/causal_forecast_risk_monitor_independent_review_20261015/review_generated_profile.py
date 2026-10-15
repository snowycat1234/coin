"""Read-only generated profile verification, no accounts/providers/advancement."""
from decimal import Decimal as D
from hashlib import sha256
import importlib.util,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
CASE=ROOT/'causal_forecast_risk_monitor_20261015'
OUT=Path(__file__).resolve().parent
P=CASE/os.environ.get('FORECAST_GENERATED_PROFILE','generated_profile_attempt004')/'GENERATED_PROFILE.json'
raw=P.read_bytes();profile=json.loads(raw)
sha=lambda p:sha256(p.read_bytes()).hexdigest()
assert profile['status']=='ALL_ADMITTED_ORDERED_CELLS_TERMINAL'
assert profile['monitor_SHA256']==sha(CASE/'forecast_monitor.py')=='9b89c04516136e95691351a357ed8bf0879a400e45d1c85903786b0bd47f02ce'
assert profile['profile_SHA256']==sha(CASE/'profile_generated.py')
old=ROOT/'bounded_native_continuation_guard50_exit_expansion_20261015'
assert profile['frozen_pool_SHA256']==sha(old/'run_expansion.py')=='085d58c293e35ab23d7eb28c70a31520f9721423d6b32c3090884adb1fbdd7de'
assert profile['generated_only'] is True and profile['historical_financial_runs']==0
assert profile['historical_account_objects_constructed']==0
assert profile['annual_resource_envelope_certified'] is False and profile['host_quota_guaranteed'] is False
assert profile['compute_thread_pools_maximum']==1 and profile['coordinator_CPU_affinity']==[2,3]
obs=profile['observations'];peak=0;maxlive=0;threads=set()
assigned={x['PID']:x['CPU'] for x in profile['cases']}
for row in obs:
    ws=row['workers'];assert len(ws)<=2
    assert row['aggregate_live_RSS_bytes']==sum(w['RSS_bytes'] for w in ws)
    assert row['aggregate_live_RSS_bytes']<3500000000
    maxlive=max(maxlive,len(ws));peak=max(peak,row['aggregate_live_RSS_bytes'])
    for w in ws:
        assert w['CPU_affinity']==[assigned[w['PID']]]
        assert w['RSS_bytes']<=2000000000
        for t in w['tasks']:
            threads.add(t['name']);assert t['CPU_affinity']==[assigned[w['PID']]]
spec=importlib.util.spec_from_file_location('_review_generated_profile_native40',old/'saved_native_reconciliation.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
cases=[];pins={str(P.relative_to(ROOT)):sha(P)}
for row in profile['cases']:
    folder=P.parent/row['cell_id'];cp=folder/'TERMINAL_CHECKPOINT.json'
    assert sha(cp)==row['checkpoint_SHA256']
    terminal=json.loads(cp.read_bytes());assert terminal['cell_id']==row['cell_id']
    for name,digest in terminal['files'].items():
        assert sha(folder/name)==digest;pins[str((folder/name).relative_to(ROOT))]=digest
    pins[str(cp.relative_to(ROOT))]=sha(cp)
    a=json.loads((folder/'GENERATED_AUDIT.json').read_bytes())
    r=json.loads((folder/'GENERATED_RESULT.json').read_bytes())
    proof=checker.reconcile_saved_native(a,r,expected_continuation_version='SEPARATE_CAUSAL_HELD_FORECAST_MID_PAID_REDUCTION_V1')
    assert proof==json.loads((folder/'GENERATED_NATIVE40_PROOF.json').read_bytes())
    receipt=json.loads((folder/'CASE_RECEIPT.json').read_bytes())
    assert receipt['generated_minutes']==1440 and receipt['paid_trade_rows']==14
    assert receipt['forecast_cohorts']==1 and receipt['paid_variance_rows']==5
    assert receipt['actual_affinity']==[row['CPU']]
    assert set(receipt['thread_environment'].values())=={'1'}
    assert receipt['historical_financial_runs']==receipt['historical_account_objects_constructed']==0
    assert all(D(x['quantity'])==0 for x in a['positions'].values())
    assert not a['transfer_journal'] and not a['transfer_ids'] and not a['settlement_journal']
    assert D(a['unpaid_liability'])==0
    assert all(D(x['paid_fee_delta'])>0 for x in a['forecast_fill_journal'])
    cases.append(dict(cell_id=row['cell_id'],generated_minutes=1440,paid_native_trade_rows=14,
        forecast_cohorts=1,paid_variance_rows=5,chronological_native40_and_raw100_proof_exact=True,
        maximum_RSS_bytes=receipt['max_RSS_bytes'],wall_seconds=receipt['wall_seconds']))
result=dict(schema='INDEPENDENT_CAUSAL_FORECAST_GENERATED_ACTIVE_PROFILE_REVIEW_V1',
 status='PASS_GENERATED_ONLY',started_UTC=profile['started_UTC'],ended_UTC=profile['ended_UTC'],
 generated_cases=cases,maximum_live_workers=maxlive,resource_observations=len(obs),
 peak_observed_aggregate_worker_RSS_bytes=peak,worker_CPUs=[2,3],all_observed_helper_affinities_confined=True,
 observed_task_names=sorted(threads),numerical_compute_pools_maximum=1,
 short_profile_is_not_annual_runtime_or_host_quota_certification=True,
 source_and_evidence_SHA256=pins,historical_accounts_constructed=0,historical_market_minutes_advanced=0,
 historical_GO_created=False,financial_replays=0,generated_saved_event_arithmetic_only=True)
(OUT/'FINAL_GENERATED_RESOURCE_REVIEW_AFTER_DEFERRAL.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps(result,indent=2))
