"""Read-only closure of three real accounts and their original public identities."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path('/workspace/coin-tail-risk');HERE=ROOT/'research/portfolio-risk-2025-native-20261012';STATE=Path('/workspace/portfolio-risk-2025-state');ARMS=('CS_MATCHED','VOL_MATCHED','STATIC50')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def read(p):return json.loads(p.read_text())
reports=[]
for arm in ARMS:
 obs=STATE/('OBSERVED_'+arm);r=read(obs/'RESULT.json');binding=read(obs/'BINDING.json');summary=HERE/'summary'/arm;index=read(HERE/'result/Y2025'/arm/'INDEX.json');cold=read(summary/'PUBLIC_RESTORE.json')
 assert r['arm']==binding['arm']==cold['arm']==index['arm']==arm and r['calendar']==['2025-01-01','2026-01-01']
 assert r['summary']['completed_minutes']==cold['rows']==525600 and r['inventory_audit']=='PASS'
 assert cold['status']=='PASS_EXACT_PUBLIC_FULL2025_ZERO_ADVANCE' and cold['account_advances']==cold['new_wallets']==cold['new_fits']==cold['provider_downloads']==cold['observed_STATE_open_attempts']==0
 for n in ('RESULT.json','BINDING.json'):
  assert (obs/n).read_bytes()==(summary/n).read_bytes();member=next(x for x in index['members'] if x['name']==n);assert sha(obs/n)==member['SHA256']
 assert binding['target_archive_SHA256']==sha(HERE/'input/Y2025.npz') and binding['risk_proof_SHA256']==sha(HERE/'input/Y2025_RISK.json') and binding['quantity_profile_SHA256']=='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf'
 original_index=git('show',cold['artifact_commit']+':'+str((HERE/'result/Y2025'/arm/'INDEX.json').relative_to(ROOT)));assert original_index==(HERE/'result/Y2025'/arm/'INDEX.json').read_bytes()
 paid=r['summary']['terminal_cash_realized'];positions={s:q['decimal_strings'] for s,q in r['summary']['positions'].items() if q['quantity']!=0}
 assert paid==(len(positions)==0)
 reports.append(dict(arm=arm,marked_net_USDT=r['summary']['net_PnL'],paid_net_USDT=r['summary']['net_PnL'] if paid else None,paid_flat=paid,residual_positions=positions,residual_USDT=r['summary']['terminal_marked_notional'],metrics=r['metrics'],gates=r['gates'],forecast_risk=r['forecast_risk'],fees_USDT=r['summary']['fees_USDT'],execution_cost_USDT=r['summary']['execution_cost_USDT'],funding_USDT_original_sign=r['summary']['funding_USDT'],risk_reductions=r['summary']['risk_reduction_signal_count'],financial_seconds=read(obs/'TIMING.json')['seconds'],public_restore_seconds=cold['seconds'],packet_bytes=index['packet_bytes'],artifact_commit=cold['artifact_commit'],science_source_commit=r['science_source_commit'],new_original_case_bytes=sum(p.stat().st_size for p in obs.rglob('*') if p.is_file())))
risk=read(HERE/'input/Y2025_RISK.json');matched=sum(max(x['arms'][a]['post_sigma'] for a in ARMS)-min(x['arms'][a]['post_sigma'] for a in ARMS)<=1e-12 for x in risk);all_target=sum(all(x['arms'][a]['risk_target_met'] for a in ARMS) for x in risk)
old=[]
for root in ('/workspace/unified-exit-economics-state','/workspace/quantity-grid-state','/workspace/portfolio-risk-budget-state'):
 for p in sorted(Path(root).rglob('POINTER.json')):
  if any(part.startswith('OBSERVED') for part in p.parts):
   ptr=read(p);assert (p.parent/ptr['snapshot_path']).exists()
   assert all((p.parent/x['path']).exists() for x in ptr['chunks']);old.append(dict(pointer=str(p),completed_minutes=ptr['completed_minutes'],state_hash=ptr['state_hash']))
assert len(old)==16
out=dict(status='COMPLETE_FULL2025_FIXED_POLICY_THREE_ORIGINAL_NATIVE_PUBLIC_RECOVERIES',cases=reports,new_historical_wallets=3,scientific_policy_attempts=1,source_H2_original_recovery_attempts=1,H2_original_archive_bodies=60,H2_original_body_bytes=82770519,old_historical_wallet_replays=0,normalizer_fits=0,model_fits=0,parameter_scans=0,financial_provider_downloads=0,all_new_minute_rows=1576800,all_new_original_NPZ_chunks=1095,all70financial_source_hashes='VERIFIED',forecast_equal_days=matched,all_three_nominal10_target_days=all_target,financial_seconds=sum(r['financial_seconds'] for r in reports),public_account_restore_seconds=sum(r['public_restore_seconds'] for r in reports),published_payload_bytes=sum(r['packet_bytes'] for r in reports),new_original_case_bytes=sum(r['new_original_case_bytes'] for r in reports),old16_original_accounts_retained=old,actual_caps_instantaneous_guarantee=False,data_role='ALREADY_SEEN_CROSSYEAR_DEVELOPMENT_NOT_UNSEEN_OOS',crossyear_fixed_half_qualification='STOP_PRIOR2023_GATES_AND_NO_PAID2025_INCREMENT',scope='NO_PREDICTION_ALPHA_OR_PAPER_EXACT_CLAIM',remaining_authority='CONDITIONAL_QUANTITY_FEE_FUNDING_MMR_ARRIVAL_UNCERTIFIED')
assert out['new_original_case_bytes']<650000000 and out['published_payload_bytes']<500000000
(STATE/'COMPLETION.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
