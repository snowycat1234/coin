import json,sys
from collections import Counter
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/quantity-grid-sensitivity-20261012';sys.path.insert(0,str(here))
import archive as a
cases=[];total=0;seconds={}
for key in ('P1','P2'):
 seconds[key]=json.loads((here/'summary'/key/'RESULT.json').read_text())['seconds']
 for arm in ('CS_MATCHED','VOL_MATCHED','STATIC50'):
  s=here/'summary'/key/arm;d=here/'result'/key/arm;o=Path('/workspace/quantity-grid-state')/('OBSERVED_'+key)/arm
  for name in ('BINDING.json','RESULT.json'):assert (s/name).read_bytes()==(o/name).read_bytes()
  binding=json.loads((s/'BINDING.json').read_text());r=json.loads((s/'RESULT.json').read_text());idx=json.loads((d/'INDEX.json').read_text());side=json.loads((d/'INDEX_IDENTITY.json').read_text());cold=json.loads((s/'PUBLIC_RESTORE.json').read_text())
  a.identity(binding,r,key,arm);a.publication_destination(key,arm,d);a.check_index_identity(idx,side,key,arm,a.sha(d/'INDEX.json'));assert side['BINDING_SHA256']==a.sha(s/'BINDING.json')
  assert cold['window']==key and cold['arm']==arm and cold['status']=='PASS_EXACT_PUBLIC_UNIFIED_EXIT_ZERO_ACCOUNT_ADVANCE' and cold['account_advances']==cold['observed_STATE_open_attempts']==0
  assert cold['rows']==r['summary']['completed_minutes']==a.proto()['windows'][key]['days']*1440 and cold['state_hash']==r['genuine_state_hash'] and r['inventory_audit']=='PASS'
  assert cold['all37minutevalues']=='EXACT_BITS_AND_COORDINATES' and cold['original_NPZ_chunks']=='EXACT_BYTE_SHA256'
  assert r['summary']['unpaid_liability']==0
  if key=='P2' and arm=='VOL_MATCHED':
   assert r['summary']['terminal_cash_realized'] is False and r['summary']['terminal_marked_notional']==179.16 and r['summary']['positions']['DOGEUSDT']['decimal_strings']['quantity']=='2000'
  else:assert r['summary']['terminal_cash_realized'] and r['summary']['terminal_marked_notional']==0
  total+=idx['packet_bytes'];cases.append(dict(window=key,arm=arm,marked_net_USDT=r['summary']['net_PnL'],paid_flat=r['summary']['terminal_cash_realized'],residual_USDT=r['summary']['terminal_marked_notional'],rows=cold['rows'],state_hash=cold['state_hash'],cold_seconds=cold['seconds'],publication_identity='PASS_FROZEN_CLI_PROFILE_ORIGINAL_OBSERVED_BYTES'))
a.verify();assert total<500000000
receipts=[json.loads(p.read_text()) for p in Path('/workspace/quantity-grid-state/receipts').glob('*.json')];exits=Counter(r['exit_code'] for r in receipts);assert exits[1]==1 and set(exits)<=set((0,1))
branches=json.loads((here/'evidence/BRANCH_SHA_SNAPSHOT_20261012.json').read_text());assert branches['count']==58 and branches['terminal_page_empty'] and branches['full_git_ls_remote_heads']=='EXACT_ALL58_NAME_SHA_MATCH'
report=dict(status='PASS_ALL6_FULL_CALENDAR_PUBLIC_RECOVERY_IDENTITY_AND_GENUINE_RESIDUAL_PRESERVED_ECONOMIC_STATIC50_STOP',cases=cases,scientific_attempts=1,quantity_profile_choices=1,new_economic_wallets=6,fine_step_cases_REUSED=6,old_economic_replays=0,fits=0,new_targets=0,market_downloads=0,public_restore_advances=0,published_packet_bytes=total,source_SHA_count=len((here/'SOURCE_SHA256.txt').read_text().splitlines()),wallet_stage_seconds=seconds,cold_seconds=sum(c['cold_seconds'] for c in cases),maximum_sampled_descendant_RSS_bytes=max(r['maximum_sampled_descendant_RSS_bytes'] for r in receipts),guard_exit_counts=dict(exits),nonzero_guard_role='one initial synthetic-test KeyError fixture; original log/source retained, no historical financial failure or retry',native_authority_certified=False,branch_snapshot_count=58)
(here/'evidence/COMPLETION.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,indent=2))
