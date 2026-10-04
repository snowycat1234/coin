"""Compare one actual shared-wallet blend with saved same-pool controls."""
import hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment import compare_multi_asset_portfolios as reuse
from scripts.research_v8.registry import FIELDS,append_event
STEM='HOLD_EXIT_BLEND_20261005_V1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p,h=None):
    if h:assert sha(p)==h,str(p)
    return json.loads(Path(p).read_bytes())
def closed(a):
    t=read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];return t
pp=ROOT/'protocols'/(STEM+'.json');p=read(pp)
ap=ROOT/'reports/fast_research'/(STEM+'.json');fp=ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json')
a=read(ap);f=read(fp)
roles={'market':closed(a),'financial':closed(f)};reports={'BLEND_TWO':a};resolution={}
assert a['complete_calendar_cases']==f['financial_case_calls']==4 and f['independent_blend_targets_verified']
for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
for name,ref in p['saved_comparisons'].items():
    old=read(ROOT/ref['actual_path'],ref['actual_sha256']);oldf=read(ROOT/ref['financial_path'],ref['financial_sha256'])
    oldp=read(ROOT/ref['protocol_path'],ref['protocol_sha256'])
    roles[name+'_market']=closed(old);roles[name+'_financial']=closed(oldf)
    assert old['complete_calendar_cases']==oldf['financial_case_calls']==4 and oldf['status'].startswith('PASS_CONFIGURED_N_')
    reports[name]=old;resolved={}
    for n,h in oldp['source_hashes'].items():
        if sha(ROOT/n)==h:resolved[n]='UNCHANGED_CURRENT_BYTES'
        else:
            blob=subprocess.check_output(['git','show',ref['accepted_source_commit']+':'+n],cwd=ROOT)
            assert hashlib.sha256(blob).hexdigest()==h,n;resolved[n]='EXACT_ACCEPTED_GIT_BYTES_NOT_RUNTIME_DEPENDENCY'
    resolution[name]=resolved
    for k in ('start','end_exclusive','period_days','data_manifest','source_acceptances','pool_receipt','initial_capital_USDT','account_path','data_role'):
        assert p[k]==oldp[k],k
    for n in reuse.FINANCE_SOURCES:assert p['source_hashes'][n]==oldp['source_hashes'][n],n
rows=[];pairs=[];targets={};metas={}
for policy,report in reports.items():
    for c in report['cases']:
        for item in c['artifacts'].values():assert sha(item['path'])==item['sha256']
        assert c['symbols']==['BTCUSDT','ETHUSDT'] and c['summary']['completed_minutes']==c['summary']['required_minutes']==436320
        key=policy,c['cost_id'],c['unit_id']
        targets[key]=pl.read_parquet(c['artifacts']['targets.parquet']['path'])
        metas[key]=read(c['artifacts']['target_meta.json']['path'])
        rows.append(dict(policy=policy,cost=c['cost_id'],funding_unit=c['unit_id'],case_id=c['id'],symbols=c['symbols'],
            **reuse.measures(c),months_continuous_not_fresh_accounts=c['summary']['months']))
for r in rows:
    if r['policy']!='BLEND_TWO':continue
    key=r['cost'],r['funding_unit'];new=targets['BLEND_TWO',*key]
    h=targets['HOLD10_TWO',*key];d=targets['EXIT10_TWO',*key]
    columns=['available_us','symbol','mode','eligibility_reason']
    assert new.select(columns).equals(h.select(columns)) and new.select(columns).equals(d.select(columns))
    for column in ('target_weight','raw_signed_target'):
        np.testing.assert_allclose(new[column].to_numpy(),.5*h[column].to_numpy()+.5*d[column].to_numpy(),rtol=0,atol=1e-12)
    for refname in ('HOLD10_TWO','HOLD8_TWO','EXIT10_TWO'):
        control=next(v for v in rows if v['policy']==refname and (v['cost'],v['funding_unit'])==key)
        diff={k:r[k]-control[k] for k in ('net_USDT','gross_USDT','fees_USDT','execution_USDT','funding_USDT','turnover_full_capital','actual_daily_annualized_volatility','minute_MDD')}
        assert abs(diff['net_USDT']-(diff['gross_USDT']-diff['fees_USDT']-diff['execution_USDT']+diff['funding_USDT']))<1e-7
        dominates=(control['net_USDT']>=r['net_USDT']-1e-7 and
            control['actual_daily_annualized_volatility']<=r['actual_daily_annualized_volatility']+1e-10 and
            control['minute_MDD']<=r['minute_MDD']+1e-10 and
            (diff['net_USDT'] < -1e-7 or diff['actual_daily_annualized_volatility'] > 1e-10 or diff['minute_MDD'] > 1e-10))
        pairs.append(dict(challenger='BLEND_TWO',reference=refname,cost=key[0],funding_unit=key[1],differences=diff,
            actual_risk_matched=False,same_pool=True,same_component_risk_budget=refname!='HOLD8_TWO',
            reference_dominates_in_net_vol_and_MDD=dominates,
            scope='FIXED_TARGET_BLEND_IN_ONE_SHARED_ACCOUNT_NOT_SUM_OR_AVERAGE_OF_NAV'))
    oldnets=[next(v['net_USDT'] for v in rows if v['policy']==name and (v['cost'],v['funding_unit'])==key) for name in ('HOLD10_TWO','EXIT10_TWO')]
    r['net_minus_arithmetic_average_of_component_account_net_USDT']=r['net_USDT']-.5*sum(oldnets)
out=ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json')
value=dict(status='COMPLETE_FIXED_BLEND_SHARED_WALLET_PAIRED_DIAGNOSTIC_NOT_APR',task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),
    protocol_sha256=sha(pp),actual_report_sha256=sha(ap),financial_report_sha256=sha(fp),closed_roles=roles,
    control_source_resolution=resolution,rows=rows,paired_cases=pairs,
    actual_targets_equal_fixed_half_saved_component_targets=True,
    all_scenarios_undominated_by_existing_same_pool_controls=not any(x['reference_dominates_in_net_vol_and_MDD'] for x in pairs),
    independent_market_evidence=False,invest_candidate='NONE',long_term_APR='NOT_EVALUABLE',market_replays=0,posthoc_scaling=False)
with out.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False,allow_nan=False);w.write('\n')
event=dict.fromkeys(FIELDS);event.update(event_id='D073-BLEND:PAIRED_RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=p['experiment_id'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    data_manifest_hash=p['data_manifest']['sha256'],protocol_hash=sha(pp),model_family='NONE',fits=0,all_folds='SEEN_DEVELOPMENT_CONTINUOUS303',success_failure=value['status'],artifact_path=out.relative_to(ROOT).as_posix(),artifact_sha256=sha(out),
    reason_for_next_experiment='Judge fixed blend from actual full wallet and risk, not arithmetic NAV mixture',result_influenced_later_choice='DECISION_AFTER_RESULTS')
append_event(ROOT/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(path=str(out),sha256=sha(out),paired_cases=len(pairs),all_scenarios_undominated=value['all_scenarios_undominated_by_existing_same_pool_controls'],
    base_rows=[{k:r[k] for k in ('policy','net_USDT','gross_USDT','fees_USDT','execution_USDT','funding_USDT','actual_daily_annualized_volatility','minute_MDD','turnover_full_capital')} for r in rows if r['cost']=='BASE27' and r['funding_unit']=='RAW_AS_FRACTION'])))
