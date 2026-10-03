"""UNRUN D043 saved-summary comparison; no Parquet, prices or replay.

Root freezes --binding only after source QA, market and independent finance
tasks really close0. Existing save_case/daily_metrics outputs are reused as
saved; directions, costs, units or independent accounts are never pooled.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, os, resource, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant import resources

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
CONTRACT='D043_FIXED_213D_SAVED_SUMMARY_ECONOMIC_COMPARISON_V1'
STATUS='COMPLETE_D043_213D_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
MARKET_STATUS='COMPLETE_D043_FIXED213D_PUBLIC_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
AUDIT_STATUS='PASS_D043_TWENTY_FIXED213D_PUBLIC_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
MODES=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH','DONCHIAN_LONG_ONLY')
COSTS=('BASE27','STRESS43');UNITS=('RAW_AS_FRACTION','RAW_AS_PERCENT')
MONEY=('net_PnL','gross_PnL_same_quantities','fees_USDT','spread_cost_USDT','slippage_cost_USDT','funding_USDT')
PAIRS=(('LS_MINUS_LO','LONG_SHORT','LONG_ONLY'),('SO_MINUS_CASH','SHORT_ONLY','CASH'),
    ('LS_MINUS_SO','LONG_SHORT','SHORT_ONLY'),('DONCHIAN_MINUS_SMA_LO','DONCHIAN_LONG_ONLY','LONG_ONLY'))
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def view(case,proof):
    """Reuse saved metrics, attribution and whole-month tables; no new curve."""
    s=case['summary'];complete=bool(proof['complete_calendar_verified'])
    daily=s.get('daily_metrics') or {}
    fields=MONEY+('NAV','free_cash','isolated_balance','unpaid_liability','terminal_marked_notional',
        'all_observation_max_drawdown','minute_max_drawdown','normalized_total_turnover','trade_legs',
        'net_return_on_full_initial_capital_percent','realized_exposure','maximum_actual_gross_weight',
        'maximum_actual_asset_weights','minimum_actual_free_cash_all_observations_USDT',
        'long_short_marked_contribution','daily_net_gain_concentration','positive_month_count','total_month_count',
        'completed_minutes','required_minutes','account_status','completion','halt_witness',
        'terminal_cash_realized','terminal_signed_marked_notional','funding_owned_events',
        'risk_reduction_signal_count','maximum_observed_first_risk_reduction_latency_us')
    return dict(id=case['id'],strategy_id=case.get('strategy_id',s.get('strategy_id')),
        selector=case.get('selector_mode',case['mode']),complete_calendar=complete,
        common_initial_capital_USDT=10000,summary={k:s.get(k) for k in fields},
        saved_daily_metrics=daily,realized_annual_volatility=daily.get('annual_volatility'),
        daily_MDD=daily.get('max_drawdown'),saved_months=s['months'],
        descriptive_annual_return=daily.get('annual_return') if complete else None,
        annual_return_role='DESCRIPTIVE_EXTRAPOLATION_NOT_LONG_TERM_APR',
        financial_artifact_hashes_referenced_only={k:v['sha256'] for k,v in case['artifacts'].items()},
        financial_metrics_recalculated=False)


def compare(cases,proofs):
    """Four cost/unit groups, fixed paired arithmetic over separate accounts."""
    by_id={p['id']:p for p in proofs};index={}
    for case in cases:
        selector=case.get('selector_mode',case['mode']);key=case['cost_id'],case['unit_id'],selector
        if key in index:raise ValueError('Duplicate predeclared selector')
        index[key]=view(case,by_id[case['id']])
    if set(index)!={(c,u,m) for c in COSTS for u in UNITS for m in MODES}:
        raise ValueError('Exactly20 cases, no post-result subset or cost/unit selection')
    groups=[]
    for cost in COSTS:
        for unit in UNITS:
            legs={m:index[cost,unit,m] for m in MODES};deltas=[]
            for label,left,right in PAIRS:
                a,b=legs[left],legs[right];full=a['complete_calendar'] and b['complete_calendar']
                values={k:float(a['summary'][k])-float(b['summary'][k]) for k in MONEY} if full else None
                months=[]
                if full:
                    am={r['month']:r for r in a['saved_months']};bm={r['month']:r for r in b['saved_months']}
                    if set(am)!={f'2024-{m:02d}' for m in range(1,8)} or set(bm)!=set(am):
                        raise ValueError('Exact Jan-Jul monthly pairing')
                    for month in sorted(am):
                        months.append(dict(month=month,delta_net_USDT=am[month]['net_PnL']-bm[month]['net_PnL'],
                            delta_gross_USDT=am[month]['gross_PnL']-bm[month]['gross_PnL'],
                            delta_funding_USDT=am[month]['funding_USDT']-bm[month]['funding_USDT']))
                deltas.append(dict(comparison=label,left=a['id'],right=b['id'],
                    scope='FULL_SEPARATE_ACCOUNTS' if full else 'NOT_EVALUABLE_FULL_PERIOD_HALTED_PREFIX',
                    delta_USDT=values,delta_full_capital_return_percentage_points=values['net_PnL']/100 if full else None,
                    delta_realized_volatility=a['realized_annual_volatility']-b['realized_annual_volatility'] if full else None,
                    delta_all_observation_MDD=a['summary']['all_observation_max_drawdown']-b['summary']['all_observation_max_drawdown'] if full else None,
                    monthly_deltas=months,risk_equalized=False,pure_short_causal_effect_identified=False))
            groups.append(dict(cost_id=cost,unit_id=unit,selectors=legs,paired_deltas=deltas))
    return groups


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('binding','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();began=time.monotonic()
    if sha(ROOT/GUARD)!=GUARD_SHA:raise ValueError('Frozen accepted metadata guards')
    loader=importlib.util.spec_from_file_location('_d043_saved_summary_guard',ROOT/GUARD)
    g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    plan,plan_sha=g.small(a.binding)
    g.check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
        and plan['ready_to_execute'] is True and plan['contract_id']==CONTRACT
        and plan['helper_sha256']==sha(__file__) and plan['budgets']==BUDGET,'Root-frozen bounded metadata-only comparison')
    g.check(a.binding.parent==ROOT/'protocols' and a.run_dir.parent==STATE and not a.run_dir.exists()
        and a.run_dir==Path(plan['run_dir']).resolve()
        and a.output==(ROOT/plan['output_path']).resolve() and a.output.is_relative_to(ROOT/'reports/fast_research')
        and not a.output.exists(),'Exclusive comparison output/STATE')
    before=resources.status();g.bounded(before);records={};tasks={};hashes=dict(plan['frozen_sources'])
    for name,digest in hashes.items():g.small(g.project(name),digest,False)
    g.check(set(plan['roles'])=={'SOURCE_INDEPENDENT','MARKET','INDEPENDENT'},'Three genuinely completed prerequisites')
    for role,ref in plan['roles'].items():
        row,digest=g.small(g.project(ref['path']),ref['sha256'])
        g.check(row['status']==ref['required_status'] and row['binding']['task_id']==ref['task_id'],'Exact actual role '+role)
        records[role]=row;tasks[role]=g.closed(ref['task_id']);hashes[ref['path']]=digest
    g.check(len({t['task']['id'] for t in tasks.values()})==3
        and tasks['MARKET']['task']['started_at']>=tasks['SOURCE_INDEPENDENT']['task']['ended_at']
        and tasks['INDEPENDENT']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'Real source/finance chronology')
    actual,audit=records['MARKET'],records['INDEPENDENT'];spec,proto_sha=g.small(g.project(plan['market_protocol']['path']),plan['market_protocol']['sha256'])
    g.check(records['SOURCE_INDEPENDENT']['status'].startswith('PASS_') and audit['status']==AUDIT_STATUS,
        'Actual independent format/finance success, not a completed failure receipt')
    g.check(actual['status']==MARKET_STATUS and actual['binding']['protocol_sha256']==proto_sha
        and actual['binding']['source_hashes']==spec['frozen_sources']
        and spec['rules']['initial_capital_USDT']==10000 and spec['period_ids']==['213D'], 'Same fixed independent213-day10k accounts')
    g.check(actual['required_cases']==actual['completed_cases']==audit['completed_cases_verified']==len(actual['cases'])==len(audit['cases'])==20
        and {c['id'] for c in actual['cases']}=={c['id'] for c in audit['cases']},'Complete20 selector evidence, no missing direction')
    g.check(g.canonical_reports(audit['binding']['actual_reports'])=={
        str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Exact independent actual identity')
    for report in (actual,audit):
        g.check(report['funding_rate_unit']=='UNCONFIRMED' and not report['unit_certified'] and not report['native_market_certified']
            and report['candidate']=='NO_QUALIFIED_CANDIDATE' and report['long_term_APR']=='NOT_EVALUABLE', 'No unit/native/investment promotion')
    proofs={r['id']:r for r in audit['cases']}
    for case in actual['cases']:
        proof=proofs[case['id']];s=case['summary']
        g.check(case['period']=='213D' and s['required_minutes']==306720
            and s['cost_scenario']==next(c for c in spec['cost_scenarios'] if c['id']==case['cost_id'])
            and s['unit_scenario']==next(u for u in spec['unit_scenarios'] if u['id']==case['unit_id']), 'Fixed date/cost/unit selector')
        for key in MONEY[:3]+('execution_cost_USDT','funding_USDT'):g.near(s[key],proof['summary'][key],1e-7)
        g.near(s['all_observation_max_drawdown'],proof['all_observation_max_drawdown'],1e-10)
    groups=compare(actual['cases'],audit['cases']);a.run_dir.mkdir()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=sha(__file__),plan_sha256=plan_sha,
        source_hashes=dict(hashes),command=[sys.executable,*sys.argv])
    rb_sha,_=g.write(a.run_dir/'RUN_BINDING.json',binding);after=resources.status();g.bounded(after)
    result=dict(status=STATUS,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=rb_sha,closed_prerequisite_tasks=tasks,
        groups=groups,compared_selectors=20,cost_unit_groups=4,source_only_QA_repeated=False,market_or_Parquet_IO=False,
        saved_metrics_reused=True,new_accounts_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',funding_unit_certified=False,native_market_certified=False,
        economic_action='ACCEPT_SAVED_COMPARISON_CAPABILITY_NO_INVESTMENT_ADOPTION',common_caps_do_not_equalize_realized_risk=True,
        pooling_or_selected_months_or_joined_NAV=False,resources_before=before,resources_after=after,
        elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        created_utc=datetime.now(UTC).isoformat())
    g.check(result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=1_000_000_000,'Small comparison budget')
    digest,size=g.write(a.output,result)
    g.check(size+(a.run_dir/'RUN_BINDING.json').stat().st_size<=5_000_000,'Metadata output5MB bound')
    print(digest)


if __name__=='__main__':main()
