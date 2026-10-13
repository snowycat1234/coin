"""Read-only compact outputs and journal arithmetic; no restore/minute scan."""
from pathlib import Path
from decimal import Decimal as D,localcontext
import hashlib,json
H=Path(__file__).resolve().parent;W=H.parent;M=W/'coin_headroom_risk_candidate_postrun_audit_20261013';C=W/'coin_headroom_risk_candidate_20261013';S=W/'coin_headroom_process_recovery_20261013/state_recovery_authorized_run'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text())
assert sha(M/'PREPARED_OBSERVER.json')=='ff3635f59948b421dd06194f0643633fdcf7a079f695b30ac78c7bad41743f5e'
summary=read(M/'LOCAL_RESULTS_SUMMARY.json');assert sha(M/'LOCAL_RESULTS_SUMMARY.json')=='ecb828842fcfb9e9c366c8c6add1177e5f8c92741fb6801895f49c7d166874b7';assert [r['year'] for r in summary['cases']]==[2021,2023]
plan=read(C/'CASE_BINDINGS.json');core=plan['cases'][0]['symbols'];assert len(core)==5
expected={2021:'71142bbe3bae43f994ecedb4cd5792c8195288a96af1ab519d0fe47c664e5002',2023:'758d899cdbc1a0d301685009b96b0195bd2be1bded20fe80387c0da0ac3605c6'}
outputs=[]
with localcontext() as ctx:
 ctx.prec=40
 for row in summary['cases']:
  year=row['year'];case=next(c for c in plan['cases'] if c['year']==year);p=M/row['cold_receipt_locator'];assert sha(p)==expected[year]==row['cold_receipt_SHA256'];cold=read(p)
  assert cold['observer_code_SHA256']=='9fa979359009ee69165b6caa09ce4fb31a489c5c64075b885fcb19cc50a15805' and cold['status']=='PASS_COLD_RESTORE_ZERO_ADVANCE'
  assert cold['historical_wallets_opened']==cold['financial_advances']==cold['controls_rerun']==0
  assert cold['day_chunks_sha_verified']==365 and cold['minute_rows_sha_verified']==525600 and cold['saved_result_verified'] and cold['all_CORE5_terminal_quantities_exact_zero']
  state=S/row['case_id'];account=read(state/'ACCOUNT.json');result=read(state/'RESULT.json');binding=read(state/'BINDING.json');pointer=read(state/'recovery/POINTER.json')
  for name in ['ACCOUNT.json','RESULT.json','BINDING.json','DAILY.csv','MINUTE_NUMERIC.json','recovery/POINTER.json']:
   path=state/name;assert sha(path)==cold['input_files_SHA256'][str(path.relative_to(W))]
  assert cold['summary']==account['summary'] and cold['protective_policy']==account['protective_policy']
  assert cold['state_hash']==result['genuine_state_hash']==pointer['state_hash'];assert binding==pointer['binding']
  metric=cold['metrics'];assert metric==row['HEADROOM'];assert metric['full_calendar'] and metric['paid_flat'] and metric['halt_count']==0 and metric['liquidation_event_count']==0
  assert metric['completed_minutes']==525600 and metric['required_minutes']==525600 and metric['daily_observed_days']==365 and metric['stop_us'] is None
  assert set(metric['terminal_residual_quantity'])==set(core) and all(D(q)==0 for q in metric['terminal_residual_quantity'].values())
  assert set(account['summary']['positions'])==set(core)
  assert all(D(p['decimal_strings']['quantity'])==0 and D(p['decimal_strings']['isolated_balance'])==0 for p in account['summary']['positions'].values())
  for key,value in metric.items():
   if key in result:assert result[key]==value,(year,key)
  oldroot=W/case['baseline_state_local_locator'];oldresult=read(oldroot/'RESULT.json');oldaccount=read(oldroot/'ACCOUNT.json')
  for name,h in case['baseline_files_SHA256'].items():assert sha(oldroot/name)==h
  assert cold['baseline_result']==oldresult
  defined=cold['original_financial_prefix_proof']['baseline_same_definition_metrics']
  for key,value in row['baseline_original'].items():assert value==(defined[key] if key in defined else oldresult[key]),(year,key)
  for key,value in row['HEADROOM_minus_original'].items():assert value==row['HEADROOM'][key]-row['baseline_original'][key],(year,key)
  assert row['prefix']==cold['original_financial_prefix_proof'] and row['prefix']['through_first_HEADROOM_signal']
  assert row['prefix']['minute_rows'] in [219522,279016] and row['prefix']['through_us_inclusive']==case['calendar'][0]+row['prefix']['minute_rows']*60_000_000
  events=account['protective_policy']['events'];signals=[e for e in events if e['kind']=='FULL_EXIT_SIGNAL'];assert len(signals)==1 and D(signals[0]['quantity'])<0
  assert signals[0]['event_us']==row['prefix']['first_HEADROOM_protective_signal_us']
  proof=cold['actual_execution_source_and_terminal_proof'];assert proof['all_actual_fill_requests_verified']==({2021:6538,2023:9575}[year]) and proof['protective_reduce_requests_verified']==1 and proof['terminal_eligible_opens']==5
  assert cold['signal_own_ledger_and_lock_proof']['signals_recomputed']==1 and cold['signal_own_ledger_and_lock_proof']['daily_direction_resets_verified']==1
  resource_name=f"Y{year}_STATIC50_FINE_HEADROOM_attempt{'002' if year==2021 else '001'}_RESOURCE.json";resource=read(M/resource_name);assert sha(M/resource_name)==row['resource_receipt_SHA256']
  assert resource['exit_code']==0 and resource['stop_reason'] is None and resource['sampled_peak_RSS']<=2_000_000_000 and resource['elapsed_seconds']<=360 and resource['RLIMIT_CPU_seconds']==300 and resource['RLIMIT_AS_bytes']==4_000_000_000 and resource['observer_code_SHA256']==cold['observer_code_SHA256']
  assert resource['admission']['memory']['SwapTotal']==resource['admission']['memory']['active_swaps']==0
  totals={k:D(0) for k in ['fees','execution_cost','realized_PnL','gross_fill_turnover','funding_cash']}
  for trade in account['trades']:
   x={k:D(v) for k,v in trade['decimal_strings'].items()};q=x['quantity'];mid=x['mid_price'];fill=x['fill_price'];direction=D(1) if trade['side']=='BUY' else D(-1)
   assert fill==mid*(1+direction*D('.0008')) and x['fee_amount']==q*fill*D('.00055') and x['execution_cost']==q*abs(fill-mid) and q%D('1e-8')==0
   for key,journal in [('fees','fee_amount'),('execution_cost','execution_cost'),('realized_PnL','realized_PnL')]:totals[key]+=x[journal]
   totals['gross_fill_turnover']+=q*fill
  assert len(account['funding'])==5475
  for fund in account['funding']:
   x=fund.get('decimal_strings',{});q=D(x.get('quantity',str(fund['quantity'])));amount=D(x.get('signed_funding_USDT',str(fund['signed_funding_USDT'])));rate=D(str(fund['raw_rate']))*D(str(fund['conditional_rate_scale']))
   assert rate==D(fund['assumed_fraction_decimal']) and bool(q)==fund['owned']
   assert amount==(-q*D(x['mark_price'])*rate if fund['owned'] else D(0))
   if fund['mark_price'] is not None:assert fund['mark_close_us']<fund['event_us']
   totals['funding_cash']+=amount
  assert {k:str(v) for k,v in totals.items()}==cold['live_economic_ledger_proof']['exact_journal_totals']
  decimals=account['summary']['decimal_strings'];net=D(decimals['net_PnL']);expected_net=totals['realized_PnL']-totals['fees']+totals['funding_cash'];bridge=net-expected_net;assert abs(bridge)<=D('1e-25')
  assert D(decimals['isolated_balance'])==D(decimals['unpaid_liability'])==D(decimals['unrealized_PnL'])==0 and D(decimals['NAV'])==D(decimals['free_cash']) and D(decimals['NAV'])-10000==net
  assert abs(D(decimals['gross_PnL_same_quantities'])-(totals['realized_PnL']+totals['execution_cost']))<=D('1e-25')
  outputs.append({'year':year,'case_id':row['case_id'],'cold_receipt_SHA256':expected[year],'paid_PnL_USDT':metric['paid_cash_PnL_USDT'],'paid_PnL_USDT_decimal':str(net),'baseline_paid_PnL_USDT':oldresult['paid_cash_PnL_USDT'],'paid_difference_USDT_decimal':str(net-D(oldaccount['summary']['decimal_strings']['net_PnL'])),'PnL_float_difference':row['HEADROOM_minus_original']['paid_cash_PnL_USDT'],'drawdown_delta':row['HEADROOM_minus_original']['minute_drawdown'],'annual_daily_vol_delta':row['HEADROOM_minus_original']['annual_daily_vol_full_calendar_only'],'mean_gross_delta':row['HEADROOM_minus_original']['mean_actual_gross'],'mean_signed_net_delta':row['HEADROOM_minus_original']['mean_actual_signed_net'],'absolute_max_signed_net_delta':row['HEADROOM_minus_original']['max_actual_abs_signed_net'],'actual_guard_symbol':signals[0]['symbol'],'actual_guard_signal_us':signals[0]['event_us'],'pretrigger_prefix_minutes':row['prefix']['minute_rows'],'all5_terminal_quantities_Decimal_zero':True,'journal_fee_spread_slip_funding_sums_verified':True,'independent_cash_journal_bridge_error_USDT':str(bridge),'all_minute_raw_bits_verified_by_reviewed_actual_cold':True,'no_duplicate_cold_or_minute_scan_by_final_reviewer':True})
assert summary['financial_advances']==summary['new_historical_wallets_opened_by_observer']==summary['controls_rerun']==0
failure=summary['retained_failure'];assert sha(M/'Y2021_STATIC50_FINE_HEADROOM_attempt001.log')==failure['log_SHA256'] and sha(M/'Y2021_STATIC50_FINE_HEADROOM_attempt001_RESOURCE.json')==failure['resource_SHA256']
assert "ModuleNotFoundError: No module named 'polars'" in (M/'Y2021_STATIC50_FINE_HEADROOM_attempt001.log').read_text()
assert all(r['drawdown_delta']>0 and r['annual_daily_vol_delta']>0 and r['mean_signed_net_delta']>0 for r in outputs)
receipt={'status':'PASS_INDEPENDENT_LOCAL_HEADROOM_POSTRUN_OUTPUT_AND_JOURNAL_REVIEW','observer_manifest_SHA256':sha(M/'PREPARED_OBSERVER.json'),'observer_code_SHA256':sha(M/'cold_audit.py'),'observer_code_review_SHA256':sha(M/'OBSERVER_REVIEW_RECEIPT.json'),'local_summary_SHA256':sha(M/'LOCAL_RESULTS_SUMMARY.json'),'local_RESULTS_md_SHA256':sha(M/'RESULTS.md'),'package_README_SHA256':sha(W/'coin_headroom_risk_candidate_postrun_package_20261013/README.md'),'finance_package_byte_review_SHA256':sha(H/'FINANCE_PACKAGE_REVIEW_RECEIPT.json'),'local_years':[2021,2023],'cases':outputs,'first_pre_restore_system_interpreter_failure_preserved':True,'actual_2024_economic_result_reviewed_here':False,'new_2025_wallet_executed':False,'2025_scope':'Previously independently reviewed INFERRED_NO_OP original5open path only; original nonzero residual/marked1612.841014/paid_false preserved. Terminal60 ablation is not substituted.','economic_interpretation':'Local2021 PnL rises,2023 falls; both DD/annual daily volatility and directional net exposure increase. This does not establish consistent economic or risk improvement. All3 fixed economic cases plus original2025 inferred no-op are needed for final synthesis.','historical_financial_advances':0,'new_historical_wallets_executed':0,'cold_restores_or_controls_rerun_by_final_reviewer':0,'minute_arrays_rescanned_by_final_reviewer':0,'public_full_minute_cold_supported':False,'code_reported_risk_limits_are_sampled_not_kernel_RSS_certification':True,'blockers':[]}
b=(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
for p in [H/'LOCAL_OUTPUT_REVIEW_RECEIPT.json',M/'LOCAL_OUTPUT_REVIEW_RECEIPT.json']:
 with p.open('xb') as f:f.write(b)
print(json.dumps(receipt,indent=2,sort_keys=True));print('RECEIPT_SHA256',hashlib.sha256(b).hexdigest())
