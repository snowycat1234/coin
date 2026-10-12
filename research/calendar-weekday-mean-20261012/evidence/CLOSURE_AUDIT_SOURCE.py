import json,hashlib,shutil,time
from pathlib import Path
root=Path('/workspace/coin-tail-risk')
here=root/'research/calendar-weekday-mean-20261012'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(root/'research/failed-breakout-rejection-20261012/evidence/COMPLETION.json')['original21_financial_snapshots_unchanged']
assert len(old)==21
for item in old:
 p=Path(item['pointer']);pointer=read(p);actual=sha(p.parent/pointer['snapshot_path'])
 assert actual==pointer['snapshot_SHA256']==item['original_snapshot_SHA256']
 item['unchanged']=True
lines=(here/'SOURCE_SHA256.txt').read_text().splitlines()
for line in lines:
 expected,name=line.split(maxsplit=1);assert sha(root/name)==expected
assert len(lines)==9
guards={}
for state in ('/workspace/calendar-weekday-state','/workspace/calendar-weekday-cold-guard'):
 for p in sorted((Path(state)/'receipts').glob('*.json')):
  guards[str(p)]=read(p)
assert guards and all(r['affinity_cpu_count']==1 and r['thread_limit']==1 and not r['swap_active'] and not r['gpu_enabled'] for r in guards.values())
free=shutil.disk_usage('/workspace').free;assert free>=16106127360
proof=read(Path('/workspace/calendar-weekday-public-cold/PUBLIC_RESTORE.json'))
assert proof['status']=='PASS_EXACT_PUBLIC_CALENDAR_ZERO_REFIT' and proof['packet_bytes']==374057 and proof['original_STATE_open_attempts']==0
result=read(here/'result/RESULT.json')
assert result['status']=='STOP_FIXED_CALENDAR_INFORMATION_GATE'
out=dict(status=result['status'],project='ACTIVE',created_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),protocol_commit='48959dc751a9f7fe5c25f03d60950a1af023c7fa',input_commit='53d5eea19bf5d248a059d2aeb939c5c11e28302a',frozen_model_commit_before_validation='1acb3ee892c5a2247b8d0eee0175f4e2d59a54bd',public_score_commit='8382b27b709baf52a730ff149cac689132cc1438',SOURCE_manifest_entries=len(lines),source_preparation_attempts=2,first_import_failure_before_arrays_or_fit=True,scientific_recipes=1,candidate_fits=1,constant_control_fits=1,normalizer_fits=1,validation_fits=0,new_economic_references=0,new_native_wallets=0,old_financial_replays=0,provider_GETs=0,economics='NOT_RUN_INFORMATION_GATE_FAILED',tests='4 synthetic focused tests PASS0.19s',cold_restore=proof,all_packet_bytes=374057,original21_financial_snapshots_unchanged=old,maximum_sampled_descendant_RSS_bytes=max(r['maximum_sampled_descendant_RSS_bytes'] for r in guards.values()),guard_receipts=len(guards),disk_free_bytes=free,disk_reserve_bytes=16106127360,reclaimed_only_verified_disposable_clone='/workspace/rejected-break-public-cold; original zero-replay receipt preserved; all actual inputs/accounts/failed preparations untouched',lock='MISSING_NOT_AUTHORIZATION; no reserve body read',lost2026Q1Q2_recovery_claim=False,approval_requests=0,next_mechanism='NEXT_MECHANISM.json: actual synchronized own-contract mark/trade dislocation; new source-only preflight still required',current_results=result)
(here/'evidence/COMPLETION.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
(here/'evidence/GUARD_RECEIPTS.json').write_text(json.dumps(guards,indent=2,sort_keys=True)+'\n')
print('CLOSURE_PASS',len(old),len(lines),free,proof['seconds'],out['maximum_sampled_descendant_RSS_bytes'])
