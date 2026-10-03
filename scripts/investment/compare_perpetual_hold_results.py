"""UNRUN D044: twelve newly audited holds against sixty saved summaries; no arrays.
Root freezes --binding only after actual/independent closed0. Plan keys:
contract_id/helper_sha256/ready_to_execute/frozen_sources/budgets/run_dir/output_path,
market_protocol{path,sha256},hold_strategy_id,roles MARKET/INDEPENDENT
{path,sha256,required_status,task_id}. Prior immutable proofs are fixed below.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, os, resource, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
from scripts.investment.compare_perpetual_213_results import MONEY, view

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
CONTRACT='D044_ALWAYS_LONG_THREE_PERIOD_SAVED_COMPARISON_V1'
STATUS='COMPLETE_D044_ALWAYS_LONG_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
MARKET_CONTRACT='D044_THREE_SEEN_USDM_PAST30_COVARIANCE_HOLD_REFERENCE_V1'
MARKET_STATUS='COMPLETE_D044_TWELVE_CONDITIONAL_PERPETUAL_HOLD_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
HOLD_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
COSTS=('BASE27','STRESS43'); UNITS=('RAW_AS_FRACTION','RAW_AS_PERCENT')
SELECTORS=('HOLD','SMA_LO','SMA_SO','SMA_LS','CASH','DONCHIAN')
MODES=dict(LONG_ONLY='SMA_LO',SHORT_ONLY='SMA_SO',LONG_SHORT='SMA_LS',CASH='CASH',DONCHIAN_LONG_ONLY='DONCHIAN')
PERIODS={'213D':(213,[f'2024-{m:02d}' for m in range(1,8)]),
    '122D':(122,[f'2025-{m:02d}' for m in range(8,12)]),'90D':(90,['2025-12','2026-01','2026-02'])}
PRIOR={
    'D043_MARKET':('reports/fast_research/PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json','d0e3488de09f89fa78aed06539fd1b77c32df3d4d1af8db9a1aab245d665a105'),
    'D043_AUDIT':('reports/fast_research/PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V3.json','0fb451c29c14e361a117333281cbc50e0809bcdb977d8b2983daef40d8e6b54e'),
    'D043_ROOT':('reports/fast_research/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json','4edb2ceaa3e29995c30dd130f04ed290da2b779e66de22b0b3c1cf6ef86716ca'),
    'D040_ROOT':('reports/fast_research/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_20261003_V1.json','5b6fa633f14e976e75babb1405bedb97dfb91af9ed7cc25ae0363fa62ca5e89c'),
    'D041_ROOT':('reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ROOT_ACCEPTANCE_20261003_V1.json','b50ba2987d0b8cc59d652dc8d3aae06c7c4127668dce64f65454b3fc74824d11')}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def add(index,c,proof,selector,evidence,g):
    key=(c['period'],c['cost_id'],c['unit_id'],selector); s=c['summary']; days,months=PERIODS[c['period']]
    g.check(key not in index and s['required_minutes']==days*1440,'Unique fixed whole-window selector')
    expected_cost=dict(id=c['cost_id'],half_spread_bps=4 if c['cost_id']=='BASE27' else 8,slippage_bps=4 if c['cost_id']=='BASE27' else 8,roundtrip_bps=27 if c['cost_id']=='BASE27' else 43)
    g.check(s['cost_scenario']==expected_cost and s['unit_scenario']==dict(id=c['unit_id'],scale=1.0 if c['unit_id']=='RAW_AS_FRACTION' else .01),'Exact same preregistered cost and unit conditions')
    full=proof['complete_calendar_verified'] is True
    if full:g.check(s['completed_minutes']==days*1440 and [r['month'] for r in s['months']]==months,'Unchanged complete month/calendar scope')
    row=view(c,proof);row.update(period=c['period'],selector=selector,saved_evidence=evidence)
    index[key]=row

def comparison(index,g):
    expected={(p,c,u,s) for p in PERIODS for c in COSTS for u in UNITS for s in SELECTORS}
    g.check(set(index)==expected,'72 rows: twelve holds plus sixty saved references, no chosen subset')
    groups=[]
    for period in PERIODS:
        for cost in COSTS:
            for unit in UNITS:
                rows={s:index[period,cost,unit,s] for s in SELECTORS}; h=rows['HOLD']; pairs=[]
                for selector in SELECTORS[1:]:
                    r=rows[selector]; full=h['complete_calendar'] and r['complete_calendar']
                    risks=(h['realized_annual_volatility'],r['realized_annual_volatility'],h['summary']['all_observation_max_drawdown'],r['summary']['all_observation_max_drawdown'])
                    evaluable=full and all(x is not None for x in risks)
                    delta={k:float(h['summary'][k])-float(r['summary'][k]) for k in MONEY} if evaluable else None
                    pairs.append(dict(reference=selector,scope='FULL_SEPARATE_ACCOUNTS' if evaluable else 'NOT_EVALUABLE_INCOMPLETE_OR_MISSING_SAVED_RISK',
                        hold_minus_reference_USDT=delta,delta_full_capital_return_percentage_points=delta['net_PnL']/100 if evaluable else None,
                        delta_realized_volatility=risks[0]-risks[1] if evaluable else None,delta_all_observation_MDD=risks[2]-risks[3] if evaluable else None,
                        monthly_deltas=[dict(month=a['month'],net_USDT=a['net_PnL']-b['net_PnL'],gross_USDT=a['gross_PnL']-b['gross_PnL'],funding_USDT=a['funding_USDT']-b['funding_USDT']) for a,b in zip(h['saved_months'],r['saved_months'],strict=True)] if evaluable else None,
                        risk_equalized=False,pure_direction_causal_effect_identified=False))
                groups.append(dict(period=period,cost_id=cost,unit_id=unit,selectors=rows,paired_deltas=pairs))
    return groups

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('binding','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();began=time.monotonic()
    if sha(ROOT/GUARD)!=GUARD_SHA:raise ValueError('Frozen accepted metadata guards')
    loader=importlib.util.spec_from_file_location('_d044_summary_guard',ROOT/GUARD);g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    plan,plan_sha=g.small(a.binding);g.check(os.getenv('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
        and plan['ready_to_execute'] is True and plan['contract_id']==CONTRACT and plan['helper_sha256']==sha(__file__) and plan['budgets']==BUDGET,'Actual frozen bounded metadata-only comparison')
    g.check(a.binding.parent==ROOT/'protocols' and a.run_dir.parent==STATE and a.run_dir==Path(plan['run_dir']).resolve() and not a.run_dir.exists()
        and a.output==(ROOT/plan['output_path']).resolve() and a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'Exclusive output/STATE')
    before=resources.status();g.bounded(before);hashes=dict(plan['frozen_sources']);tasks={};new={};prior={}
    for name,digest in hashes.items():g.small(g.project(name),digest,False)
    g.check(set(plan['roles'])=={'MARKET','INDEPENDENT'},'Two newly completed scientific roles')
    for role,ref in plan['roles'].items():
        row,digest=g.small(g.project(ref['path']),ref['sha256']);g.check(row['status']==ref['required_status'] and row['binding']['task_id']==ref['task_id'],'Exact new actual role')
        new[role]=row;tasks[role]=g.closed(ref['task_id']);hashes[ref['path']]=digest
    g.check(tasks['MARKET']['task']['id']!=tasks['INDEPENDENT']['task']['id'] and tasks['INDEPENDENT']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'Real independent post-market accounting')
    for role,(name,digest) in PRIOR.items():prior[role],_=g.small(g.project(name),digest);hashes[name]=digest
    for role in ('D043_ROOT','D040_ROOT','D041_ROOT'):g.check(prior[role]['status'].startswith('PASS_ROOT_'),'Previously accepted saved reference');tasks[role]=g.closed(prior[role]['binding']['task_id'])
    g.check(prior['D041_ROOT']['prior']['original_root']==dict(path=PRIOR['D040_ROOT'][0],sha256=PRIOR['D040_ROOT'][1]),'D040 original30 plus corrected2 references already accepted')
    actual,audit=new['MARKET'],new['INDEPENDENT'];spec,proto_sha=g.small(g.project(plan['market_protocol']['path']),plan['market_protocol']['sha256'])
    g.check(actual['status']==MARKET_STATUS and audit['status'].startswith('PASS_') and spec['contract_id']==MARKET_CONTRACT and plan['hold_strategy_id']==HOLD_ID
        and actual['binding']['protocol_sha256']==proto_sha and actual['binding']['source_hashes']==spec['frozen_sources'] and spec['rules']['initial_capital_USDT']==10000 and set(spec['period_ids'])==set(PERIODS),'Fixed three independent10k windows')
    g.check(actual['required_cases']==actual['completed_cases']==audit['completed_cases_verified']==len(actual['cases'])==len(audit['cases'])==12,'All twelve predeclared selectors present')
    g.check(g.canonical_reports(audit['binding']['actual_reports'])=={str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Independent exact actual identity')
    for r in (actual,audit):g.check(r['funding_rate_unit']=='UNCONFIRMED' and not r['unit_certified'] and not r['native_market_certified'] and r['candidate']=='NO_QUALIFIED_CANDIDATE' and r['long_term_APR']=='NOT_EVALUABLE','No native/unit/APR promotion')
    proofs={r['id']:r for r in audit['cases']};index={}
    for c in actual['cases']:
        q=proofs[c['id']];g.check(c['strategy_id']==plan['hold_strategy_id'],'Only fixed new HOLD')
        for k in MONEY[:3]+('execution_cost_USDT','funding_USDT'):g.near(c['summary'][k],q['summary'][k],1e-7)
        g.near(c['summary']['all_observation_max_drawdown'],q['all_observation_max_drawdown'],1e-10)
        add(index,c,q,'HOLD',plan['roles']['MARKET'],g)
    oldproofs={r['id']:r for r in prior['D043_AUDIT']['cases']}
    g.check(prior['D043_AUDIT']['actual_report_sha256']==PRIOR['D043_MARKET'][1],'Accepted213 summary/audit identity')
    for c in prior['D043_MARKET']['cases']:add(index,c,oldproofs[c['id']],MODES[c['selector_mode']],dict(path=PRIOR['D043_MARKET'][0],sha256=PRIOR['D043_MARKET'][1]),g)
    for group in prior['D041_ROOT']['comparisons']:
        tokens=group['id'].split('_');period=tokens[0];cost=next(c for c in COSTS if c in tokens);unit=next(u for u in UNITS if group['id'].endswith('_'+u))
        rows=[('DONCHIAN',group['id'],group['Donchian_summary'])]+[(MODES[c['summary']['mode']],c['id'],c['summary']) for c in group['SMA_controls']]
        for selector,identity,s in rows:
            c=dict(id=identity,period=period,cost_id=cost,unit_id=unit,mode=selector,summary=s,artifacts={})
            add(index,c,dict(complete_calendar_verified=s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'),selector,dict(path=PRIOR['D041_ROOT'][0],sha256=PRIOR['D041_ROOT'][1],scope='PREVIOUSLY_ACCEPTED_CANONICAL_SAVED_SUMMARY_NO_ARTIFACT_REREAD'),g)
    groups=comparison(index,g);a.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=sha(__file__),plan_sha256=plan_sha,source_hashes=dict(hashes),command=[sys.executable,*sys.argv])
    rb_sha,_=g.write(a.run_dir/'RUN_BINDING.json',binding);after=resources.status();g.bounded(after)
    result=dict(status=STATUS,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=rb_sha,closed_prerequisite_tasks=tasks,groups=groups,
        compared_new_selectors=12,saved_reference_rows=60,summary_rows=72,cost_unit_period_groups=12,paired_comparisons=60,
        market_or_Parquet_IO=False,financial_metrics_recalculated=False,old_accounts_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',funding_unit_certified=False,native_market_certified=False,seen_screening=True,
        common_caps_do_not_equalize_realized_risk=True,risk_rescaled_after_results=False,joined_NAV_or_chosen_months=False,
        economic_action='ACCEPT_SAVED_COMPARISON_CAPABILITY_NO_INVESTMENT_ADOPTION',resources_before=before,resources_after=after,
        elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,created_utc=datetime.now(UTC).isoformat())
    g.check(result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=1_000_000_000,'Small comparison budget');digest,size=g.write(a.output,result)
    g.check(size+(a.run_dir/'RUN_BINDING.json').stat().st_size<=5_000_000,'Metadata output bound');print(digest)

if __name__=='__main__':main()
