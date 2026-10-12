import hashlib,json,sys
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012';sys.path.insert(0,str(here));import archive as a
a.verify();total=0;rows=0;seconds=[];cold_seconds=[];cases=[]
for key in ('P1','P2'):
 for arm in ('VOL_MATCHED','STATIC50'):
  summary=here/'summary'/key/arm;state=Path('/workspace/portfolio-risk-budget-state')/('OBSERVED_'+key)/arm;dest=here/'result'/key/arm
  for name in ('BINDING.json','RESULT.json'):assert (summary/name).read_bytes()==(state/name).read_bytes()
  binding=json.loads((summary/'BINDING.json').read_text());result=json.loads((summary/'RESULT.json').read_text());index=json.loads((dest/'INDEX.json').read_text());cold=json.loads((summary/'PUBLIC_RESTORE.json').read_text());a.identity(binding,result,key,arm)
  for field,value in a.expected_identity(key,arm).items():assert index[field]==value
  assert index['BINDING_SHA256']==a.sha(summary/'BINDING.json')==next(r['SHA256'] for r in index['members'] if r['name']=='BINDING.json')
  assert cold['window']==key and cold['arm']==arm and cold['status']=='PASS_EXACT_PUBLIC_PORTFOLIO_RISK_ZERO_ACCOUNT_ADVANCE' and cold['account_advances']==cold['observed_STATE_open_attempts']==cold['provider_downloads']==0
  assert cold['rows']==result['summary']['completed_minutes']==a.proto()['windows'][key]['days']*1440 and cold['state_hash']==result['genuine_state_hash']
  assert cold['all37minutevalues']=='EXACT_BITS_AND_COORDINATES' and cold['original_NPZ_chunks']=='EXACT_BYTE_SHA256_REPRODUCIBLE' and result['inventory_audit']=='PASS'
  assert result['summary']['unpaid_liability']==0
  if key=='P2' and arm=='VOL_MATCHED':
   assert not result['summary']['terminal_cash_realized'] and result['summary']['terminal_marked_notional']==179.16 and result['summary']['positions']['DOGEUSDT']['decimal_strings']['quantity']=='2000' and result['comparison']['paid_net_difference_USDT'] is None
  else:assert result['summary']['terminal_cash_realized'] and result['summary']['terminal_marked_notional']==0
  total+=index['packet_bytes'];rows+=cold['rows'];seconds.append(json.loads((summary/'TIMING.json').read_text())['seconds']);cold_seconds.append(cold['seconds']);cases.append(dict(window=key,arm=arm,source_commit=binding['science_source_commit'],paid_flat=result['summary']['terminal_cash_realized'],net_USDT=result['summary']['net_PnL'],state_hash=cold['state_hash'],public_artifact=cold['artifact_commit']))
 for arm in ('CS_MATCHED',):
  summary=here/'summary'/key/arm;old=root/'research/quantity-grid-sensitivity-20261012/summary'/key/arm;reuse=json.loads((summary/'REUSE.json').read_text());assert reuse['status']=='REUSED_EXACT_TARGET_BITS_SAME_CAUSAL_FIXED10_BUDGET_WITH_CAP_SHORTFALLS'
  for name in ('BINDING.json','RESULT.json','DAILY.csv','PUBLIC_RESTORE.json'):assert (summary/name).read_bytes()==(old/name).read_bytes()
assert total<500000000 and rows==2364480
review=json.loads((here/'evidence/RESULT_REVIEWED.json').read_text());assert len(review['cases'])==6 and review['new_wallets_completed']==4 and review['financial_advances']==0
assert review['windows']['P1']['equal_forecast_sigma_days']==432 and review['windows']['P1']['all_three_nominal_target_met_days']==431 and review['windows']['P1']['all_three_intrinsic_cash_days']==1
assert review['windows']['P2']['equal_forecast_sigma_days']==review['windows']['P2']['all_three_nominal_target_met_days']==240 and review['windows']['P2']['all_three_intrinsic_cash_days']==0
receipts=[json.loads(p.read_text()) for p in Path('/workspace/portfolio-risk-budget-state/receipts').glob('*.json')];assert all(r['exit_code']==0 for r in receipts)
observed_bytes=sum(p.stat().st_size for d in ('OBSERVED_P1','OBSERVED_P2') for p in (Path('/workspace/portfolio-risk-budget-state')/d).rglob('*') if p.is_file());assert observed_bytes<650000000
out=dict(status='COMPLETE_FOUR_NEW_TWO_EXACT_CS_REUSED_ALL_FOUR_PUBLIC_COLD_PASS_ECONOMIC_STOP',scientific_attempts=1,fixed_risk_budget_choices=1,quantity_profile_choices=0,new_economic_wallets=4,CS_full_accounts_REUSED=2,old_economic_replays=0,new_fits=0,normalizer_fits=0,market_downloads=0,public_cold_financial_advances=0,new_original_minute_rows=rows,REUSED_CS_minute_rows=1182240,published_packet_bytes=total,all_four_original_case_bytes=observed_bytes,wallet_seconds=sum(seconds),public_cold_seconds=sum(cold_seconds),maximum_sampled_descendant_RSS_bytes=max(r['maximum_sampled_descendant_RSS_bytes'] for r in receipts),source_SHA_count=len((here/'SOURCE_SHA256.txt').read_text().splitlines()),guard_receipts_at_check=len(receipts),guard_nonzero_exit_counts=0,tests='9 PASS4.92s; original8 PASS4.14s retained',response_stream_errors_parent_reported=2,economic_attempts_from_stream_errors=0,failed_normal_pushes=2,push_failure_scope='commit_refs thenHTTP503; subsequent ordinary publication b9ca3d31 remote exact',publication_sequence_deviation='last wallet began before previous receipt commit remote-confirmed; all60 frozen sources already exactly public4d8ed9fa, no unpublic financial change; saved in failure evidence',policy_nominal_risk=.10,original_execution_quantity_multiplier=.99,actual_caps_instantaneous_guarantee=False,P2_STATIC50_actual_gross_max=.6202281848094549,P2_STATIC50_risk_reduction_signals=29,P2_HOLD_residual_DOGE='2000',P2_HOLD_residual_USDT=179.16,history='ALREADY_SEEN_DEVELOPMENT_NOT_NEW_OOS_OR_PAPER_EXACT',native_certified=False,cases=cases)
(here/'evidence/COMPLETION.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps(out,indent=2))
