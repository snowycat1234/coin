import json,hashlib,sys
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/unified-closing-exempt-economics-20261012';sys.path.insert(0,str(here))
import archive as a
out=[];total=0;stage={}
for key in ('P1','P2'):
 stage[key]=json.loads((here/'summary'/key/'RESULT.json').read_text())['seconds']
 for arm in ('CS_MATCHED','VOL_MATCHED','STATIC50'):
  s=here/'summary'/key/arm;d=here/'result'/key/arm;o=Path('/workspace/unified-exit-economics-state')/('OBSERVED_'+key)/arm
  for name in ('BINDING.json','RESULT.json'):assert (s/name).read_bytes()==(o/name).read_bytes()
  binding=json.loads((s/'BINDING.json').read_text());r=json.loads((s/'RESULT.json').read_text());index=json.loads((d/'INDEX.json').read_text());identity=json.loads((d/'INDEX_IDENTITY.json').read_text());p=json.loads((s/'PUBLIC_RESTORE.json').read_text())
  a.identity(binding,r,key,arm);a.publication_destination(key,arm,d);a.check_index_identity(index,identity,key,arm,a.sha(d/'INDEX.json'))
  assert identity['BINDING_SHA256']==a.sha(s/'BINDING.json')
  assert p['window']==key and p['arm']==arm and p['status']=='PASS_EXACT_PUBLIC_UNIFIED_EXIT_ZERO_ACCOUNT_ADVANCE' and p['account_advances']==p['observed_STATE_open_attempts']==0
  assert p['rows']==r['summary']['completed_minutes']==a.proto()['windows'][key]['days']*1440
  assert p['state_hash']==r['genuine_state_hash'] and r['inventory_audit']=='PASS' and r['summary']['terminal_cash_realized'] is True
  assert r['summary']['terminal_marked_notional']==r['summary']['unpaid_liability']==0
  assert p['all37minutevalues']=='EXACT_BITS_AND_COORDINATES' and p['original_NPZ_chunks']=='EXACT_BYTE_SHA256'
  total+=index['packet_bytes'];out.append(dict(window=key,arm=arm,rows=p['rows'],status=r['status'],net_USDT=r['summary']['net_PnL'],public_cold_seconds=p['seconds'],publication_identity='PASS_EXTERNAL_CLI_PROTO_ORIGINAL_OBSERVED_BYTES'))
a.verify();assert total<500000000
receipts=[json.loads(p.read_text()) for p in Path('/workspace/unified-exit-economics-state/receipts').glob('*.json')]
assert all(r['exit_code']==0 and r['stop_reason'] is None for r in receipts)
report=dict(status='PASS_ALL6_FIXED_COMPLETE_PAID_AUDITED_PUBLIC_CASES_ECONOMIC_STATIC50_STOP_BOTH_WINDOWS',cases=out,new_economic_wallets=6,scientific_attempts=1,new_fits=0,new_target_archives=0,provider_downloads=0,old_wallet_replays=0,public_restore_account_advances=0,published_packet_bytes=total,source_SHA_count=len((here/'SOURCE_SHA256.txt').read_text().splitlines()),wallet_stage_seconds=stage,public_cold_seconds=sum(r['public_cold_seconds'] for r in out),maximum_sampled_descendant_RSS_bytes=max(r['maximum_sampled_descendant_RSS_bytes'] for r in receipts),all_guard_receipts_exit_zero=True,native_authority_certified=False,seen_history=True)
(here/'evidence/COMPLETION.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,indent=2))
