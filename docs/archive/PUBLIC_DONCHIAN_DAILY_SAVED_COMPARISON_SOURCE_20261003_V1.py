"""D037 accepted saved metrics only: reuse existing descriptive Pareto definition."""
import hashlib,importlib.util,json,os
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/PUBLIC_DONCHIAN_DAILY_SAVED_COMPARISON_SOURCE_20261003_V1.py'
REUSE='docs/archive/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_SOURCE_20261003_V2.py'
REUSE_SHA='6e7bc5d00c21127df860f9c443d497e468f894402c7af88bfd70db4c451c7309'
AUDIT='reports/fast_research/PUBLIC_DONCHIAN_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json'
OUT='reports/fast_research/PUBLIC_DONCHIAN_DAILY_ECONOMIC_COMPARISON_20261003_V1.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('COIN_TASK_ID') and sha(__file__)==sha(ROOT/ARCHIVE) and sha(ROOT/REUSE)==REUSE_SHA
mod=importlib.util.spec_from_file_location('d037_saved_metrics',ROOT/REUSE);r=importlib.util.module_from_spec(mod);mod.loader.exec_module(r)
audit,ah=r.small(ROOT/AUDIT);r.require(audit['status']=='PASS_D037_THREE_DAILY_PUBLIC_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR','New daily audit actually passed')
audit_task=r.closed(audit,audit['binding']['task_id']);cases=[];hashes={ARCHIVE:sha(__file__),REUSE:REUSE_SHA,AUDIT:ah};prior={}
for period,name in [('CONT547','VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_20261003_V1.json'),('CONT122','VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_20261003_V1.json'),('CONT90','VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_20261003_V1.json')]:
    path='reports/fast_research/'+name;proof,h=r.small(ROOT/path);hashes[path]=h
    prior[period]=[row for row in proof['cases'] if row.get('fold',period)==period]
for fold,label,days in [('CONT547','547D',547),('CONT122','122D',122),('CONT90','90D',90)]:
    path=f'reports/fast_research/PUBLIC_DONCHIAN_DAILY_{label}_ACTUAL_20261003_V1.json';actual,h=r.small(ROOT/path);hashes[path]=h
    r.closed(actual,actual['binding']['task_id']);row=actual['folds'][0]['results'][0];summary=row['summary']
    r.require(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and row['spread_bps']==8 and row['nominal_roundtrip_bps']==36
        and summary['initial_nav']==10000 and summary['period_days']==days,'Same whole capital/cost period')
    accepted=[x for x in audit['ledgers'] if x['fold']==fold];r.require(len(accepted)==1,'One independent daily ledger')
    for k,j,t in [('net_cash_PnL','net_PnL',1e-7),('fees','fees',1e-7),('max_observed_minute_MDD','minute_MDD',1e-10)]:r.near(summary[k],accepted[0][j],t)
    metrics={k:summary[k] for k in r.METRICS};metrics['execution_costs']=summary['execution_costs']
    metrics['total_cost_USDT']=summary['fees']+summary['spread_cost']+summary['slippage_cost']
    controls=[]
    for old in prior[fold]:
        s=old['summary'];control={**old,'daily_descriptive_Pareto_dominates_control':False,'control_descriptive_Pareto_dominates_daily':False}
        if old['strategy']!='CASH':
            control.update(daily_descriptive_Pareto_dominates_control=r.dominates(metrics,s),control_descriptive_Pareto_dominates_daily=r.dominates(s,metrics))
        control.update(net_PnL_delta_USDT=metrics['net_cash_PnL']-s['net_cash_PnL'],
            daily_minus_control_total_cost_USDT=metrics['total_cost_USDT']-sum(s[k] for k in ('fees','spread_cost','slippage_cost')),
            daily_minus_control_gross_PnL_USDT=metrics['gross_cash_PnL_same_quantities']-s['gross_cash_PnL_same_quantities'])
        controls.append(control)
    cases.append(dict(fold=fold,days=days,strategy=row['strategy'],actual_report=path,actual_report_sha256=h,
        summary=metrics,controls=controls,cash_equivalent_no_fills=summary['trade_count']==0))
value=dict(status='COMPLETE_D037_SAVED_METRICS_COMPARISON_NOT_NEW_ACCOUNT_OR_LONG_TERM_APR',created_utc=datetime.now(UTC).isoformat(),
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__)),source_hashes=hashes,audit_closed0_task=audit_task,cases=cases,
    descriptive_Pareto_rule=r.PARETO_RULE,same_caps_not_equal_realized_risk=True,all_history_previously_seen_SCREENING=True,
    no_trade_period_is_cash_avoidance_not_positive_trade_alpha=True,accounts_stitched=False,old_financial_or_QA_replayed=False,
    market_arrays_read=False,models_fit=0,orders_sent=0,locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
with (ROOT/OUT).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
print(json.dumps(dict(status=value['status'],output_sha256=sha(ROOT/OUT))))
