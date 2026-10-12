"""Completion identities/resources only; zero fits or financial advances."""
import hashlib,json,shutil,time
from pathlib import Path
from driver import HERE,ROOT,sha,save,proto
def read(p):return json.loads(p.read_text())
old=read(ROOT/'research/calendar-weekday-mean-20261012/evidence/COMPLETION.json')['original21_financial_snapshots_unchanged'];assert len(old)==21
for item in old:
 p=Path(item['pointer']);pointer=read(p);actual=sha(p.parent/pointer['snapshot_path']);assert actual==pointer['snapshot_SHA256']==item['original_snapshot_SHA256'];item['unchanged']=True
manifest=(HERE/'SOURCE_SHA256.txt').read_text().splitlines()
for line in manifest:
 expected,name=line.split(maxsplit=1);assert sha(ROOT/name)==expected,name
guard={}
for path in ('/workspace/rejected-break-follow-native-state','/workspace/follow-native-2023-cold-guard','/workspace/follow-native-2025-cold-guard'):
 for p in sorted((Path(path)/'receipts').glob('*.json')):guard[str(p)]=read(p)
assert all(r['affinity_cpu_count']==1 and r['thread_limit']==1 and not r['gpu_enabled'] and not r['swap_active'] and r['per_process_address_limit_bytes']==4000000000 and r['aggregate_RSS_stop_bytes']==2000000000 for r in guard.values())
years={};native_seconds=0.;cold_seconds=0.;bytes_total=0
for key in ('Y2023','Y2025'):
 case=Path('/workspace/rejected-break-follow-native-state')/('OBSERVED_'+key);summary=HERE/'summary'/key;result=read(summary/'RESULT.json');cold=read(summary/'PUBLIC_RESTORE.json');hold=read(summary/'HOLDING_DIAGNOSTIC.json');pointer=read(case/'recovery/POINTER.json');account=read(case/'ACCOUNT.json');ix=read(HERE/'result'/key/'INDEX.json')
 assert result['status']=='STOP_CONDITIONAL_POSTHOC_FOLLOW_PATH_GATES' and result['gates']==dict(full_paid_audited=True,net_positive=True,cash_path_CI=False,risk=True)
 assert pointer['completed_minutes']==result['summary']['completed_minutes']==cold['rows']==525600 and pointer['state_hash']==result['genuine_state_hash']==cold['genuine_state_hash']
 assert sha(case/'recovery'/pointer['snapshot_path'])==pointer['snapshot_SHA256'] and result['summary']==account['summary'] and result['summary']['terminal_cash_realized'] and result['summary']['terminal_marked_notional']==0
 assert not account['liquidations'] and result['inventory_audit']=='PASS' and cold['status']=='PASS_EXACT_PUBLIC_FOLLOW_ZERO_ADVANCE' and cold['observed_STATE_open_attempts']==cold['account_advances']==cold['provider_downloads']==cold['new_fits']==0
 child=read(HERE/'evidence'/('COLD_'+key+'_SOURCE_CHILD_AUDIT.json'));assert child['original_STATE_open_attempts']==0
 assert cold['packet_bytes']==ix['packet_bytes'] and cold['members']==373
 for r in ix['parts']:p=HERE/'result'/key/r['file'];assert sha(p)==r['SHA256'] and p.stat().st_size==r['bytes']
 timing=read(case/'TIMING.json')['seconds'];native_seconds+=timing;cold_seconds+=cold['seconds'];bytes_total+=ix['packet_bytes'];years[key]=dict(result=result,cold=cold,holding=hold,original_new_native_pointer=str(case/'recovery/POINTER.json'),original_new_native_snapshot_SHA256=pointer['snapshot_SHA256'],wallet_seconds=timing)
comparisons=read(HERE/'COMPARISONS.json');assert all(all(v['checks'].values()) for year in comparisons['years'].values() for v in year['comparisons'].values())
assert all(v['paid_cash_net_difference_USDT'] is None for v in comparisons['years']['Y2025']['comparisons'].values())
free=shutil.disk_usage('/workspace').free;assert free>=proto()['budget']['disk_reserve'];assert bytes_total==17286981
out=dict(status='STOP_CONDITIONAL_POSTHOC_FOLLOW_PATH_GATES',project='ACTIVE',created_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),scientific_recipe=1,new_historical_native_wallets=2,new_fits=0,old_financial_replays=0,provider_downloads=0,new_live_orders=0,source_readiness_attempts=1,unique_relevant_tests=11,tests='finalown3PASS3.50s/grid5PASS4.00s/source2025_3PASS3.86s; retainedcollection/namespacefailures; fullrepositoryNOT_RUN',SOURCE_manifest_entries=len(manifest),years=years,comparisons=comparisons,original21_financial_snapshots_unchanged=old,all_23_original_native_snapshots_present=True,native_wallet_seconds=native_seconds,public_cold_seconds=cold_seconds,source_rebuild_nested_within_cold_not_added_again=True,unmeasured_planning_Git_reasoning_time='UNKNOWN',public_packet_bytes=bytes_total,guard_receipts=len(guard),maximum_sampled_descendant_RSS_bytes=max(r['maximum_sampled_descendant_RSS_bytes'] for r in guard.values()),maximum_sampled_host_used_bytes=max(r['maximum_host_used_bytes'] for r in guard.values()),disk_free_bytes=free,disk_reserve_bytes=proto()['budget']['disk_reserve'],approval_requests=0,coarse_profile='94b2238_EXISTING_PRESSURE_TRUE_HISTORICAL_MINQTY_UNKNOWN',terminal='FIXED_NATIVE_END_MINUS6MIN_NOT_PROXY_JAN1_00:01',strict24h_actual_ownership_claim=False,native_minus_proxy_attributed_solely_to_cost=False,original_FADE_STOP_preserved=True,mark_trade_fallback='NOT_RUN_NO_CURRENT_SOURCE_PERMISSION_BLOCKER_NEXT_CANDIDATE_RETAINED',lock='MISSING_NOT_AUTHORIZATION_NO_PROTECTED_OR_UNKNOWN_RESERVE_BODY_READ',lost2026ledger_recovery_claim=False,Library=False,account_key_or_credential_creation=False,paid_or_live_venue_certification=False)
save(HERE/'evidence/COMPLETION.json',out);save(HERE/'evidence/GUARD_RECEIPTS.json',guard);print('ACTUAL_FOLLOW_COMPLETION_PASS',len(old),2,len(manifest),bytes_total,native_seconds,cold_seconds,free,out['maximum_sampled_descendant_RSS_bytes'],flush=True)
