"""Thin final preservation, resource and account/source checks; zero simulation."""
import argparse,json,shutil,time
from pathlib import Path
from native_apis import HERE,ROOT,file_sha,save,verify

def run(out):
 assert not out.exists();verify();old=json.loads((ROOT/'research/co-tail-risk-20261012/evidence/COMPLETION.json').read_text());preserved=[]
 for row in old['original23_financial_snapshots_unchanged']:
  p=Path(row['pointer']);ptr=json.loads(p.read_text());s=p.parent/ptr['snapshot_path'];assert ptr['snapshot_SHA256']==row['original_snapshot_SHA256']==file_sha(s);preserved.append(dict(pointer=str(p),snapshot_SHA256=file_sha(s),unchanged=True))
 assert len(preserved)==23
 ix=json.loads((ROOT/'research/follow-cash-compatibility-20261012/preserved/Y2023/INDEX.json').read_text());p=Path('/workspace/follow-cash-compatibility-state/OBSERVED_Y2023/recovery/POINTER.json');ptr=json.loads(p.read_text());assert file_sha(p.parent/ptr['snapshot_path'])==ptr['snapshot_SHA256']==ix['genuine_snapshot_SHA256'];preserved.append(dict(pointer=str(p),snapshot_SHA256=ptr['snapshot_SHA256'],unchanged=True))
 for key in ('Y2023','Y2025'):
  p=Path('/workspace/sma200-native-state')/('OBSERVED_'+key)/'recovery/POINTER.json';ptr=json.loads(p.read_text());ix=json.loads((HERE/'result'/key/'INDEX.json').read_text());r=json.loads((HERE/'summary'/key/'RESULT.json').read_text());proof=json.loads((HERE/'evidence'/(key+'_PUBLIC_RESTORE.json')).read_text());assert file_sha(p.parent/ptr['snapshot_path'])==ptr['snapshot_SHA256']==ix['snapshot_SHA256']==proof['snapshot_SHA256'];assert ptr['state_hash']==ix['state_hash']==proof['genuine_state_hash']==r['genuine_state_hash'];assert r['full_calendar'] and r['inventory_audit']=='PASS' and proof['rows']==525600 and proof['original_STATE_open_attempts']==proof['account_advances']==0;preserved.append(dict(pointer=str(p),snapshot_SHA256=ptr['snapshot_SHA256'],new_SMA_baseline=True,paid_flat=r['paid_flat']))
 receipts=[];destination=HERE/'evidence/GUARDS';destination.mkdir(exist_ok=True)
 for folder in ('/workspace/sma200-native-state/receipts','/workspace/sma200-public-cold-guard/receipts'):
  for p in sorted(Path(folder).glob('*.json')):
   b=p.read_bytes();r=json.loads(b);target=destination/p.name
   if target.exists():assert target.read_bytes()==b
   else:target.write_bytes(b)
   assert r['stop_reason'] is None and r['maximum_sampled_descendant_RSS_bytes']<2000000000 and r['maximum_host_used_bytes']<8000000000 and r['affinity_cpu_count']==1 and r['thread_limit']==1 and not r['swap_active'] and not r['gpu_enabled'];receipts.append(dict(file=target.name,exit_code=r['exit_code'],elapsed_seconds=r['elapsed_seconds'],RSS=r['maximum_sampled_descendant_RSS_bytes'],host=r['maximum_host_used_bytes']))
 free=shutil.disk_usage('/workspace').free;assert free>=16106127360
 comparison=json.loads((HERE/'COMPARISON.json').read_text());assert comparison['new_wallets']==comparison['new_fits']==comparison['old_wallet_replays']==comparison['new_RNG']==comparison['downloads']==0
 report=dict(status='COMPLETE_TWO_FROZEN_ORIGINAL_SMA_YEARS_NATIVE_AUDIT_PUBLIC_COLD_PRESERVED',created_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),financial_states=len(preserved),original23_plus_FOLLOW2023_unchanged=True,snapshots=preserved,new_financial_wallets=2,old_financial_replays=0,fits=0,seeds='NONE_DETERMINISTIC_NO_RNG',provider_downloads=0,financial_attempts={'Y2023':1,'Y2025':1},public_native_cold_attempts={'Y2023':1,'Y2025':1},tests={'unique_meaningful_synthetic':3,'invocations':2,'first_fixture_failed':True,'second_all_pass':True},source_preparation_attempts=1,read_only_comparison_attempts=2,read_only_comparison_first_failed_before_control_read=True,guard_receipts=receipts,max_sampled_descendant_RSS=max(r['RSS'] for r in receipts),max_sampled_host_used=max(r['host'] for r in receipts),disk_free_bytes=free,disk_reserve_bytes=16106127360,public_packets_total_bytes=sum(json.loads(p.read_text())['packet_bytes'] for p in (HERE/'result').glob('*/INDEX.json')),source_manifest_entries=len((HERE/'SOURCE_SHA256.txt').read_text().splitlines()),source_cache_scope='PREVIOUS_INDEPENDENT_PUBLIC_RECOVERY_REUSED_SHA_IDENTICAL_MONTHS_DAILY_EVENTS; NO_NEW_RAW_REPARSE',own_public_part_checkout_reclaimed_only_after_published_native_cold=True,shared_cgroup_enforcement=False,guard_scope='SAMPLED_COMMAND_DESCENDANT_RSS_AND_HOST; ONE_FINANCIAL_WALLET_AT_A_TIME',paid_investment_qualified=False,blockers=['SMA_BOTH_YEARS_NEGATIVE','SMA_BOTH_YEARS_TERMINAL_RESIDUAL','CS2025_TERMINAL_RESIDUAL','HISTORICAL_NATIVE_VENUE_FILTER_FUNDING_UNIT_PIT_CERTIFICATION_UNKNOWN'],full_repo_tests='NOT_RUN_SCOPE_SPECIFIC_ONLY',Library=False,keys_credentials_pay_live_deploy_force=False,protected2026_lock_opened=False,lost2026_ledger_recovery_claim=False)
 save(out,report)
 for key,row in comparison['years'].items():
  print(key,json.dumps({a:{k:r[k] for k in ('marked_net_USDT','marked_return','paid_flat','terminal_marked_notional','price_gross_USDT','fees_USDT','execution_USDT','funding_USDT','annual_daily_vol','minute_DD','mean_actual_gross','max_actual_gross','mean_signed_net','max_abs_signed_net')} for a,r in [('SMA',row['SMA200_10PCT']),('CS',row['REUSED_CS'])]},ensure_ascii=False),flush=True)
 print('ACTUAL_SMA_COMPLETION_AUDIT_PASS',len(preserved),len(receipts),free,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
