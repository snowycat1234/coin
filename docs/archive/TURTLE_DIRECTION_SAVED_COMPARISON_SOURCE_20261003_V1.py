"""UNRUN D049 saved comparison; no prices, ledger IO, replay or direction selection.

Root freezes --binding after new MARKET/INDEPENDENT genuinely close0. It has
contract_id/helper_sha256/budgets/run_dir/output_path/market_protocol,
roles {path,sha256,required_status,task_id}, frozen_sources and private SHA guard.
No execution before the final frozen binding and actual completed prerequisites.
"""
from __future__ import annotations
import argparse, os, resource, sys, time
from pathlib import Path
from quant import resources
from scripts.investment import closing_exempt_saved_comparison as saved

ROOT=saved.ROOT;STATE=saved.STATE
PARENT='scripts/investment/closing_exempt_saved_comparison.py'
PARENT_SHA='c0a369dfd68c2e039defce4f849c5f890bd1c0821facab640a0eff931391e3d3'
CONTRACT='D049_TURTLE_DIRECTION_SAVED_COMPARISON_V1'
STATUS='COMPLETE_D049_TURTLE_DIRECTION_SAVED_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
MARKET_CONTRACT='D049_FIXED303D_TURTLE_DIRECTION_ABLATION_CONDITIONAL_V1'
MARKET_STATUS='COMPLETE_D049_EIGHT_TURTLE_DIRECTION_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
AUDIT_STATUS='PASS_D049_EIGHT_RECORDED_TURTLE_DIRECTION_ACCOUNTING_NOT_NATIVE_FILTERS_OR_LONG_TERM_APR'
LO='LONG_ONLY';SO='SHORT_ONLY';LS='LONG_SHORT';HOLD='HOLD_LONG_ONLY'
STRATEGY_ID='COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER'
PRIOR_ACTUAL='reports/fast_research/CLOSING_EXEMPT_RESEARCH_ACTUAL_20261003_V1.json'
PRIOR_ACTUAL_SHA='85da71baf2550e7545d1148c5df2172fd2eda4a1abc1f00cf1be28ea4fbed8c1'
PRIOR_COMPARE='reports/fast_research/CLOSING_EXEMPT_SAVED_COMPARISON_20261003_V1.json'
PRIOR_COMPARE_SHA='ef992eb11d764d0571da5733584051e0aadebb8a52a74cff8d9f97e59b6776e6'
RISK_KEYS=('initial_capital_USDT','annual_vol_target','asset_abs_cap','gross_cap','leverage',
 'MMR','sizing_buffer','maximum_attempts','participation_rate','funding','terminal',
 'past_covariance_completed_days','quantity_step_assumption','min_quantity_assumption',
 'closing_min_notional_exempt','filter_profile_id','opening_min_notional_assumption_USDT')


def cash_difference(row,money):
    full=row['complete_calendar']
    return dict(scope='FULL_SEPARATE_ACCOUNT_VS_KNOWN_ZERO_POSITION_CASH' if full else 'NOT_EVALUABLE_HALTED_PREFIX',
        net_USDT=float(row['summary']['net_PnL']) if full else None,
        delta_USDT={k:row['summary'][k] for k in money} if full else None,
        cash_initial_capital_USDT=10000,cash_PnL_USDT=0,cash_actual_volatility=0,cash_MDD=0,
        new_cash_account_simulated=False,unknown_rate_filled_with_zero=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('binding','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();began=time.monotonic()
    if not all((MARKET_CONTRACT,MARKET_STATUS,AUDIT_STATUS)):raise ValueError('Final producer/auditor identity pending')
    if saved.sha(ROOT/PARENT)!=PARENT_SHA:raise ValueError('Frozen saved-comparison helpers changed')
    g=saved.module(saved.GUARD,saved.GUARD_SHA);v=saved.module(saved.VIEW,saved.VIEW_SHA);check=g.check
    plan,plan_sha=g.small(a.binding);own=saved.sha(__file__)
    check(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2')
        and a.binding.parent==ROOT/'protocols' and plan['ready_to_execute'] is True
        and plan['contract_id']==CONTRACT and plan['helper_sha256']==own and plan['budgets']==saved.BUDGET,'Frozen comparison caller')
    check(a.run_dir==Path(plan['run_dir']) and a.run_dir.parent==STATE and not a.run_dir.exists()
        and a.output==(ROOT/plan['output_path']).resolve() and a.output.parent==ROOT/'reports/fast_research'
        and not a.output.exists(),'Exclusive new metadata ownership')
    before=resources.status();g.bounded(before);hashes=dict(plan['frozen_sources']);records={};tasks={}
    check(plan['local_non_git_hash_guard']=={saved.LOCK:saved.LOCK_SHA}
        and saved.sha(ROOT/saved.LOCK)==saved.LOCK_SHA,'Private lock streamSHA only')
    for name,digest in hashes.items():
        check(name!=saved.LOCK,'Private lock not exported');g.small(g.project(name),digest,False)
    check(hashes.get(Path(__file__).relative_to(ROOT).as_posix())==own and hashes.get(PARENT)==PARENT_SHA,'Exact executed comparison sources')
    check(set(plan['roles'])=={'MARKET','INDEPENDENT'},'Two new actual prerequisites')
    for role,ref in plan['roles'].items():
        report,digest=g.small(g.project(ref['path']),ref['sha256']);tasks[role]=g.closed(ref['task_id'])
        check(report['status']==ref['required_status']==(MARKET_STATUS if role=='MARKET' else AUDIT_STATUS)
            and report['binding']['task_id']==ref['task_id'],'Real completed role identity')
        records[role]=report;hashes[ref['path']]=digest
    check(tasks['INDEPENDENT']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'Actual finance chronology')
    actual,audit=records['MARKET'],records['INDEPENDENT'];ref=plan['market_protocol']
    spec,proto_sha=g.small(g.project(ref['path']),ref['sha256']);hashes[ref['path']]=proto_sha
    check(spec['contract_id']==MARKET_CONTRACT and spec['period_ids']==['303D']
        and actual['binding']['protocol_sha256']==proto_sha and actual['binding']['source_hashes']==spec['frozen_sources']
        and all(hashes.get(k)==h for k,h in spec['frozen_sources'].items()),'Actual fixed scientific inputs')
    check(actual['required_cases']==actual['completed_cases']==audit['completed_cases_verified']==len(actual['cases'])==len(audit['cases'])==8
        and g.canonical_reports(audit['binding']['actual_reports'])=={str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Eight audited new selectors')
    for row in records.values():
        check(row['funding_rate_unit']=='UNCONFIRMED' and not row['unit_certified'] and not row['native_market_certified']
            and row['long_term_APR']=='NOT_EVALUABLE','No unit/native/APR promotion')
    old,_=g.small(g.project(PRIOR_ACTUAL),PRIOR_ACTUAL_SHA);prior,_=g.small(g.project(PRIOR_COMPARE),PRIOR_COMPARE_SHA)
    hashes.update({PRIOR_ACTUAL:PRIOR_ACTUAL_SHA,PRIOR_COMPARE:PRIOR_COMPARE_SHA})
    check(prior['status']==saved.STATUS and actual['input_windows']==old['input_windows'],'Accepted shared94-source and4-warmup view')
    oldref=Path(old['binding']['protocol_path']);oldspec,oldsha=g.small(oldref,old['binding']['protocol_sha256'])
    hashes[oldref.relative_to(ROOT).as_posix()]=oldsha
    check(spec['cost_scenarios']==oldspec['cost_scenarios'] and spec['unit_scenarios']==oldspec['unit_scenarios']
        and all(spec['rules'][k]==oldspec['rules'][k] for k in RISK_KEYS),'Same capital/current risk/cost/funding/quantity policy')
    proofs={r['id']:r for r in audit['cases']};index={}
    for case in actual['cases']:
        key=case['cost_id'],case['unit_id'],case['mode'];proof=proofs[case['id']]
        check(key not in index and case['period']=='303D' and case['strategy_id']==STRATEGY_ID
            and case['summary']['required_minutes']==436320,'Fixed Turtle direction selector')
        index[key]=v.view(case,proof)
        index[key]['summary'].update({k:case['summary'].get(k) for k in ('gross_notional','net_signed_notional','gross_weight','asset_weights')})
    check(set(index)=={(c,u,m) for c in saved.COSTS for u in saved.UNITS for m in (LO,SO)},'All four conditions, no directional subset')
    previous={(r['cost_id'],r['unit_id']):r for r in prior['groups']};groups=[]
    check(set(previous)=={(c,u) for c in saved.COSTS for u in saved.UNITS},'Exact saved four-group reference')
    for cost in saved.COSTS:
        for unit in saved.UNITS:
            oldgroup=previous[cost,unit];rows={LO:index[cost,unit,LO],SO:index[cost,unit,SO],LS:oldgroup['TURTLE'],HOLD:oldgroup['HOLD']}
            pairs={label:saved.delta(rows[left],rows[right],v.MONEY) for label,left,right in (
                ('LS_MINUS_LO',LS,LO),('LS_MINUS_SO',LS,SO),('LO_MINUS_HOLD',LO,HOLD),('LS_MINUS_HOLD',LS,HOLD))}
            groups.append(dict(cost_id=cost,unit_id=unit,selectors=rows,paired_deltas=pairs,
                each_minus_known_CASH0={m:cash_difference(r,v.MONEY) for m,r in rows.items()},
                short_increment_definition='LS_MINUS_LO_SEPARATE_SHARED_RISK_AND_PATH_ACCOUNT_DIFFERENCE_NOT_ADDITIVE_SHORT_PNL',
                return_or_risk_winner_selected=False))
    a.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=own,plan_sha256=plan_sha,
        source_hashes=hashes,command=[sys.executable,*sys.argv]);rb_sha,_=g.write(a.run_dir/'RUN_BINDING.json',binding)
    after=resources.status();g.bounded(after)
    result=dict(status=STATUS,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=rb_sha,closed_prerequisite_tasks=tasks,
        groups=groups,new_accounts_referenced=8,saved_D048_accounts_referenced=8,known_CASH0_new_account=False,
        score_start='2024-09-01',score_end_exclusive='2025-07-01',days=303,initial_capital_each_USDT=10000,
        common_caps_equal_realized_risk=False,direction_PnLs_additive=False,joined_NAV=False,selected_direction_or_unit=False,
        market_ledger_IO=False,old_QA_or_financial_replay=False,new_financial_metrics_recalculated=False,
        candidate='NO_QUALIFIED_CANDIDATE',investment='CASH_NONE',long_term_APR='NOT_EVALUABLE',
        funding_unit_certified=False,native_market_certified=False,complete_strategy_intents_independently_rebuilt=False,
        resources_before=before,resources_after=after,elapsed_seconds=time.monotonic()-began,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    check(result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=1_000_000_000,'Saved comparison budget')
    digest,size=g.write(a.output,result);check(size+(a.run_dir/'RUN_BINDING.json').stat().st_size<=5_000_000,'Metadata5MB');print(digest)


if __name__=='__main__':main()
