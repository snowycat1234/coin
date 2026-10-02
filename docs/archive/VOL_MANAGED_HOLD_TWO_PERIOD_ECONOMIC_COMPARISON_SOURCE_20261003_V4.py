"""D035 saved-summary comparison only; strict Pareto fixed before new results."""
import argparse,hashlib,importlib.util,json,os,sys
from pathlib import Path
from datetime import UTC,datetime
from quant import resources
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
REUSE='docs/archive/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_SOURCE_20261003_V2.py'
REUSE_SHA='6e7bc5d00c21127df860f9c443d497e468f894402c7af88bfd70db4c451c7309'
OUT='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_20261003_V1.json'
AUDIT='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json'
AUDIT_STATUS='PASS_D035_TWO_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
STATUS='COMPLETE_D035_TWO_PERIOD_SAVED_SUMMARY_RISK_COST_COMPARISON_NOT_LONG_TERM_APR'
VM='VOL_MANAGED_BUY_AND_HOLD';PUBLIC='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER';HYBRID='COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
FIXED={
 'CONT122':dict(days=122,start='2025-08-01',end='2025-12-01',months=['2025-08','2025-09','2025-10','2025-11'],
  public=('BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json','53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3'),
  hybrid=('PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1.json','9e7727b41b994db2ab1d3496094e22ef12de98ab841d050cd1c9c7fd31310313'),
  cash=('SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json','62cb5604580e3af8de3bcf7d1db5f76343581ef44f656ba89f927ba4bdb24e94')),
 'CONT90':dict(days=90,start='2025-12-01',end='2026-03-01',months=['2025-12','2026-01','2026-02'],
  public=('BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json','329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a'),
  hybrid=('PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1.json','3b6e1f58c9f76411a5d8bcddde29fdfc3c7bdb955a9f04013269599199c3bfb6'),
  cash=('PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json','7e47d20fb71a8c6f87cc5b1adc26a2e031bb9bdbd8cf1a64d61ab6b4ac25642c'))}
PROOFS={
 'public':('BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json','70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f'),
 'public_root':('BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json','04b98fbf88f5a3ed06675f0e49299468410153f809d7368987afa82496cdc253'),
 'hybrid':('PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json','a1af8448c0b44b6e79cbb0123f942bde05b773f90ebb01b0a7b751c4f23f77c9'),
 'hybrid_root':('PUBLIC_DONCHIAN_HYBRID_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json','a4623a44976ccd71eaf83b4f9d79aedd6ad8913f5e385b215ad726626112bf2a')}

def main():
 p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
 raw=(ROOT/REUSE).read_bytes();assert hashlib.sha256(raw).hexdigest()==REUSE_SHA
 imp=importlib.util.spec_from_file_location('d035_accepted_saved_comparison',ROOT/REUSE);r=importlib.util.module_from_spec(imp);imp.loader.exec_module(r)
 need,small=r.require,r.small;bind,bindsha=small(a.binding);_,ownsha=small(__file__,bind['comparator_sha256'])
 need(a.binding.parent==ROOT/'protocols' and os.environ.get('COIN_TASK_ID') and a.run_dir.parent==STATE and not a.run_dir.exists() and not (ROOT/OUT).exists(),'Exclusive bounded metadata comparison')
 runtime=resources.status();need(runtime['ram_limit_bytes']<=5_000_000_000 and runtime['swap_bytes']==0 and not runtime['gpu_used'],'Shared5GB/swap0/GPU0')
 need(bind['audit']['path']==AUDIT and set(bind['cases'])==set(FIXED),'Two predeclared periods and unique new audit')
 audit,_=small(ROOT/AUDIT,bind['audit']['sha256']);audit_task=r.closed(audit,bind['audit']['task_id'])
 need(audit['status']==AUDIT_STATUS and audit['completed_ledgers_verified']==2 and len(audit['ledgers'])==2,'Completed independent two-account proof')
 pinned={REUSE:REUSE_SHA,AUDIT:bind['audit']['sha256']};proofs={}
 for role,(name,digest) in PROOFS.items():
  path='reports/fast_research/'+name;proofs[role]=small(ROOT/path,digest)[0];pinned[path]=digest
 need(proofs['public']['status']=='PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE' and proofs['hybrid']['status']=='PASS_HYBRID_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE','Preserved exact accepted numerical scopes')
 need(proofs['public_root']['status']=='ACCEPT_BYBIT_SPOT_FEE_ACCOUNTING_ONLY_NO_PROFITABLE_CANDIDATE' and proofs['hybrid_root']['status']=='SCREENING_MIXED_EXIT_MECHANISM_NO_WINNER','Preserved prior root acceptance')
 output_cases=[];pairs=[];tasks={'INDEPENDENT':audit_task};hashes={};actual_maps={};all_summaries={}
 for fold,config in FIXED.items():
  case=bind['cases'][fold];spec,psha=small(ROOT/case['protocol']['path'],case['protocol']['sha256']);actual,asha=small(ROOT/case['actual']['path'],case['actual']['sha256'])
  task=r.closed(actual,case['actual']['task_id']);tasks[fold]=task;actual_maps[str((ROOT/case['actual']['path']).resolve())]=asha
  need(audit_task['task']['started_at']>=task['task']['ended_at'] and actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['completed_ledgers']==1 and actual['all_planned_ledgers_complete'] and actual['source_bytes_unchanged'],'Closed complete actual before independent')
  need(spec['strategy_ids']==actual['binding']['strategies']==[VM] and spec['planned_ledgers']==actual['planned_ledgers']==1 and actual['binding']['protocol_sha256']==psha and actual['binding']['source_hashes']==audit['verified_source_hashes'][fold],'Exact sole VM source/protocol binding')
  need(spec['folds']==[dict(id=fold,period_start=config['start'],period_end_exclusive=config['end'])] and spec['costs']['spread_bps']==[8] and spec['costs']['nominal_roundtrip_bps']==[36] and spec['common_config']['initial_cash']==10000 and spec['common_config']==actual['registration_start']['hyperparameters'],'Fixed period/capital/cost/risk')
  need(actual['market_models_fit']==actual['orders_sent']==0 and not actual['locked_consumed'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Seen screening only')
  pinned[case['protocol']['path']]=psha;pinned[case['actual']['path']]=asha;hashes[fold]=actual['binding']['source_hashes'];rows={}
  for strategy,role,report in [(VM,'new',actual)]+[(s,role,None) for s,role in [(PUBLIC,'public'),(HYBRID,'hybrid'),('CASH','cash')]]:
   if report is None:
    name,digest=config[role];path='reports/fast_research/'+name;report=small(ROOT/path,digest)[0];pinned[path]=digest
    need(report['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and report['all_planned_ledgers_complete'] and report['registration_start']['hyperparameters']==spec['common_config'],'Preserved same capital/risk complete reference')
   else:path=case['actual']['path'];digest=asha
   folds=[f for f in report['folds'] if f['fold']==fold];need(len(folds)==1 and folds[0]['days']==config['days'] and folds[0]['start_us']==actual['folds'][0]['start_us'] and folds[0]['end_us']==actual['folds'][0]['end_us'],'Actual account dates equal')
   selected=[x for x in folds[0]['results'] if x['strategy']==strategy and x['spread_bps']==8 and x['nominal_roundtrip_bps']==36];need(len(selected)==1,'Unique same36bp account')
   summary=selected[0]['summary'];need(summary['initial_nav']==10000 and summary['period_days']==config['days'] and not summary['candidate_qualification_allowed'],'Same capital/whole scoring scope')
   months=None
   if strategy!='CASH':
    proof=audit if strategy==VM else proofs[role];ledger=[x for x in proof['ledgers'] if x['fold']==fold and x['strategy']==strategy and x['spread_bps']==8];need(len(ledger)==1,'Unique accepted independent reference')
    ledger=ledger[0];months=ledger['months'];need([x['month'] for x in months]==config['months'],'All predeclared months')
    for k,j,tol in [('net_cash_PnL','net_PnL',1e-7),('gross_cash_PnL_same_quantities','gross_PnL_same_quantities',1e-7),('fees','fees',1e-7),('max_observed_minute_MDD','minute_MDD',1e-10),('max_drawdown','daily_MDD',1e-10)]:r.near(summary[k],ledger[j],tol)
    need(report['fee_settlement']==spec['fee_settlement']=='BYBIT_SPOT_RECEIVED_ASSET_V1' and report['fee_profile_sha256']==spec['fee_profile_sha256'] and report['source_receipt_sha256']==actual['source_receipt_sha256'] and report['minute_source']['sha256']==actual['reused_minute_input']['sha256'],'Same accepted native fee/source price values')
   else:
    need(summary['trade_count']==0 and summary['terminal_positions_flat'] and all(float(q)==0 for q in summary['open_positions'].values()) and summary['net_cash_PnL']==summary['gross_cash_PnL_same_quantities']==summary['fees']==summary['spread_cost']==summary['slippage_cost']==0,'Legacy quote-fee zero-trade cash only, not relabeled native')
   metrics={k:summary[k] for k in r.METRICS};rows[strategy]=metrics;output_cases.append(dict(fold=fold,days=config['days'],strategy=strategy,report_path=path,report_sha256=digest,summary=metrics,months=months,legacy_quote_fee_cash_zero_trade=(strategy=='CASH')))
  for strategy in (PUBLIC,HYBRID):
   new,ref=rows[VM],rows[strategy];forward,reverse=r.dominates(new,ref),r.dominates(ref,new)
   pairs.append(dict(fold=fold,new_strategy=VM,reference_strategy=strategy,new_Pareto_dominates_reference=forward,reference_Pareto_dominates_new=reverse,net_PnL_delta_USDT=new['net_cash_PnL']-ref['net_cash_PnL'],annual_volatility_delta=new['annual_volatility']-ref['annual_volatility'],minute_MDD_delta=new['max_observed_minute_MDD']-ref['max_observed_minute_MDD'],conclusion='NEW_DESCRIPTIVE_PARETO_DOMINANCE' if forward else 'REFERENCE_DESCRIPTIVE_PARETO_DOMINANCE' if reverse else 'NO_STRICT_PARETO_DOMINANCE_NO_SCALAR_WINNER'))
  all_summaries[fold]=rows
 need(audit['binding']['actual_reports']==actual_maps,'Exact two independently accepted actual reports')
 a.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=ownsha,comparison_binding_path=str(a.binding),comparison_binding_sha256=bindsha,actual_reports=actual_maps)
 (a.run_dir/'RUN_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
 value=dict(status=STATUS,created_utc=datetime.now(UTC).isoformat(),binding=binding,cases=output_cases,pairs=pairs,source_hashes_by_period=hashes,small_report_hashes=pinned,actual_task_copies=tasks,predeclared_Pareto_rule=r.PARETO_RULE,economic_action='TWO_SEEN_PERIODS_NO_INVESTMENT_ADOPTION',same_caps_not_equal_realized_risk=True,accounts_stitched_or_months_selected=False,old_financial_validation_or_source_QA_replayed=False,market_arrays_read=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',resources=runtime)
 with (ROOT/OUT).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
 print(json.dumps(dict(status=STATUS,output=OUT,sha256=small(ROOT/OUT)[1])))
if __name__=='__main__':main()