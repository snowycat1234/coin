"""Read-only, conservative storage admission from observed predecessor wallets."""
import json,shutil,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def run():
 p=json.loads((HERE/'PROTOCOL.json').read_text());ready=json.loads((HERE/'input/READINESS.json').read_text());assert ready['status'].startswith('PASS_')
 observed=[]
 for year in ('Y2023','Y2025'):
  base=HERE.parent/'sma200-native-20261013';ix=json.loads((base/'result'/year/'INDEX.json').read_text());state=Path('/workspace/sma200-native-state')/('OBSERVED_'+year)
  observed.append(dict(year=year,original_state_bytes=sum(f.stat().st_size for f in state.rglob('*') if f.is_file()),public_packet_bytes=ix['packet_bytes']))
 free=shutil.disk_usage('/workspace').free;reserve=p['budget_this_stage']['disk_reserve'];margin=free-reserve;case=max(x['original_state_bytes'] for x in observed);packet=max(x['public_packet_bytes'] for x in observed);publication_cushion=1048576
 need_one=case+2*packet+publication_cushion;need_two=2*case+3*packet+publication_cushion
 report=dict(status='STOP_RESOURCE_GATE_FOR_NEW_NATIVE_WALLETS' if margin<need_one else 'RESOURCE_ONLY_ADMITTED_PARENT_PROXY_STILL_REQUIRED',sampled_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),disk_free_bytes=free,disk_reserve_bytes=reserve,margin_bytes=margin,observed_original_SMA_cases=observed,case_upper_reference_bytes=case,packet_upper_reference_bytes=packet,publication_cushion_bytes=publication_cushion,required_margin_for_first_wallet_and_normal_Git_publication_bytes=need_one,shortfall_first_bytes=max(0,need_one-margin),required_margin_for_two_wallets_with_prior_own_public_checkout_sparse_exclusion_bytes=need_two,shortfall_two_bytes=max(0,need_two-margin),method='REFERENCE_SMA_OBSERVED_STATE_PLUS_TWO_NEW_PACKETS_PER_COMMIT_AND_ONE_PRIOR_PACKET_GIT_OBJECT; OWN_CHECKOUT_EXCLUDED_AFTER_PUBLISHED_COLD; ADMISSION_PLANNING_NOT_PROMISE_OF_ACTUAL_COMPRESSION',parent_daily_proxy_status='NOT_RECEIVED',new_native_wallets=0,old_native_wallets_replayed=0,source_targets_ready=True,source_fits=0,source_downloads=0,protected_original_accounts_preserved=True)
 (HERE/'RESOURCE_GATE.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(report['status'],report['margin_bytes'],report['shortfall_first_bytes'],flush=True)
if __name__=='__main__':run()
