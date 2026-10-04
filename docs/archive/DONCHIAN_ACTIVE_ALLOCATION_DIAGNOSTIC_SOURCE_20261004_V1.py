"""Paired saved-ledger diagnosis; no market replay or posthoc scaling."""
import hashlib, json, os, resource, subprocess
from pathlib import Path
from datetime import UTC, datetime
from decimal import Decimal
import numpy as np
import polars as pl
from quant.paths import ROOT, STATE
from scripts.investment import compare_multi_asset_portfolios as reuse
from scripts.research_v8.registry import FIELDS, append_event

STEM = 'DONCHIAN_ACTIVE_ALLOCATION_20261004_V1'
assert os.environ['COIN_TASK_ID']

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def read(p, h=None):
    p=Path(p); assert p.is_file() and not p.is_symlink()
    if h: assert sha(p)==h, str(p)
    return json.loads(p.read_bytes())

def closed(a):
    task=read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
    assert task['status']=='completed' and task['exit_code']==0 and task['ended_at']
    return task

pp=ROOT/'protocols'/(STEM+'.json'); p=read(pp); ctrl=p['saved_control']
ap=ROOT/'reports/fast_research'/(STEM+'.json'); a=read(ap)
fp=ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json'); f=read(fp)
old=read(ROOT/ctrl['actual_path'],ctrl['actual_sha256'])
oldf=read(ROOT/ctrl['financial_path'],ctrl['financial_sha256'])
oldp=read(ROOT/ctrl['protocol_path'],ctrl['protocol_sha256'])
roles={name:closed(value) for name,value in [('market',a),('finance',f),('control_market',old),('control_finance',oldf)]}
assert a['completed_cases']==a['complete_calendar_cases']==old['completed_cases']==4
assert f['financial_case_calls']==f['completed_cases_verified']==oldf['financial_case_calls']==4
assert f['status'].startswith('PASS_CONFIGURED_N_') and oldf['status'].startswith('PASS_CONFIGURED_N_')
assert a['binding']['protocol_sha256']==sha(pp) and a['binding']['source_hashes']==p['source_hashes']
assert a['allocation']=='ACTIVE_EQUAL' and old['allocation']=='EQUAL'
for n,h in p['source_hashes'].items(): assert sha(ROOT/n)==h,n
old_source_resolution={}
for n,h in oldp['source_hashes'].items():
    if sha(ROOT/n)==h: old_source_resolution[n]='UNCHANGED_CURRENT_BYTES'
    else:
        blob=subprocess.check_output(['git','show',ctrl['accepted_source_commit']+':'+n],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest()==h,n
        old_source_resolution[n]='EXACT_GIT_55798A1_BYTES_NOT_RUNTIME_DEPENDENCY'
for k in ['start','end_exclusive','period_days','data_manifest','source_acceptances','pools','pool_receipt',
          'strategy','initial_capital_USDT','account_path','data_role','signal']:
    assert p[k]==oldp[k],k
changed_rules={'raw_allocation','inactive_signal_budget_redistributed','allocation',
    'active_signal_zero_is_cash','clipped_budget_not_redistributed'}
assert {k:v for k,v in p['strategy_rules'].items() if k not in changed_rules}=={
    k:v for k,v in oldp['strategy_rules'].items() if k not in changed_rules}
for n in reuse.FINANCE_SOURCES: assert p['source_hashes'][n]==oldp['source_hashes'][n],n
rows=[]; pairs=[]
for new in a['cases']:
    control=next(c for c in old['cases'] if c['id']==new['id'])
    assert new['symbols']==control['symbols'] and new['summary']['cost_scenario']==control['summary']['cost_scenario']
    assert new['summary']['unit_scenario']==control['summary']['unit_scenario']
    assert ctrl['artifacts'][control['id']]==control['artifacts']
    matrices={}; metrics={}; metas={}
    for name,c in [('EQUAL',control),('ACTIVE_EQUAL',new)]:
        assert c['summary']['completed_minutes']==c['summary']['required_minutes']==436320
        for item in c['artifacts'].values(): assert sha(item['path'])==item['sha256']
        t=pl.read_parquet(c['artifacts']['targets.parquet']['path']); matrices[name]=t
        meta=read(c['artifacts']['target_meta.json']['path'])
        metas[name]=meta
        assert meta['allocation']==name
        perday=t.group_by('available_us').agg(pl.col('raw_signed_target').abs().sum().alias('raw'),
            pl.col('target_weight').abs().sum().alias('target'),(pl.col('raw_signed_target')!=0).sum().alias('active'))
        m=reuse.measures(c); metrics[name]=m
        rows.append(dict(allocation=name,case_id=c['id'],cost=c['cost_id'],funding_unit=c['unit_id'],**m,
            opportunity=dict(mean_active=float(perday['active'].mean()),cash_days=int(perday['active'].eq(0).sum()),
                mean_raw_gross=float(perday['raw'].mean()),mean_risk_target_gross=float(perday['target'].mean()),
                peak_raw_gross=float(perday['raw'].max()),peak_risk_target_gross=float(perday['target'].max())),
            months_continuous_not_fresh_accounts=c['summary']['months']))
    x,y=matrices['EQUAL'],matrices['ACTIVE_EQUAL']
    keys=['available_us','symbol','mode','eligibility_reason']
    assert x.select(keys).equals(y.select(keys))
    assert np.array_equal(x['raw_signed_target'].to_numpy()!=0,y['raw_signed_target'].to_numpy()!=0)
    weights_x=x['target_weight'].to_numpy(); weights_y=y['target_weight'].to_numpy()
    assert np.all(np.abs(weights_y)<=.3+1e-13)
    daily=y.group_by('available_us').agg(pl.col('target_weight').abs().sum().alias('gross'))
    assert daily['gross'].max()<=.6+1e-13
    changed=np.abs(weights_x-weights_y)>1e-12
    control_risk={r['decision_us']:r for r in metas['EQUAL']['risk']}
    new_risk={r['decision_us']:r for r in metas['ACTIVE_EQUAL']['risk']}
    assert control_risk.keys()==new_risk.keys()
    for decision,risk in control_risk.items():
        assert risk['covariance_symbol_order']==new_risk[decision]['covariance_symbol_order']
    saturated={d for d,risk in control_risk.items() if risk['unscaled_signed_covariance_annual_vol']>=.10}
    changed_days=set(y.filter(pl.Series('changed',changed))['available_us'].to_list())
    assert not changed_days.intersection(saturated)
    mx,my=metrics['EQUAL'],metrics['ACTIVE_EQUAL']
    gross=my['gross_USDT']-mx['gross_USDT']; cost=(my['fees_USDT']+my['execution_USDT'])-(mx['fees_USDT']+mx['execution_USDT'])
    funding=my['funding_USDT']-mx['funding_USDT']; net=my['net_USDT']-mx['net_USDT']
    assert abs(net-(gross-cost+funding))<1e-7
    pairs.append(dict(cost=new['cost_id'],funding_unit=new['unit_id'],net_increment_USDT=net,
        gross_increment_USDT=gross,cost_increment_USDT=cost,funding_increment_USDT=funding,
        same_signal_state_and_identity=True,changed_target_rows=int(changed.sum()),target_rows=y.height,
        changed_decision_days=y.filter(pl.Series('changed',changed))['available_us'].n_unique(),
        maximum_weight_difference=float(np.max(np.abs(weights_y-weights_x))),actual_risk_matched=False,
        same_covariance_symbol_order=True,control_risk_saturated_days=len(saturated),
        changed_control_saturated_days=0,changed_control_unsaturated_days=len(changed_days),
        annualized_daily_vol_increment=my['actual_daily_annualized_volatility']-mx['actual_daily_annualized_volatility'],
        minute_MDD_increment=my['minute_MDD']-mx['minute_MDD'],
        turnover_increment=my['turnover_full_capital']-mx['turnover_full_capital'],
        terminal_cash_control=mx['terminal_cash_realized'],terminal_cash_challenger=my['terminal_cash_realized']))
event=dict.fromkeys(FIELDS); event.update(event_id='D065-ACTIVE-SAVED-DIAGNOSTIC:RESULT',
    event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id='D065-ACTIVE-EQUAL-SEPJUN303-20261004',
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    data_manifest_hash=p['data_manifest']['sha256'],protocol_hash=sha(pp),model_family='NONE',fits=0,
    all_folds='SEEN_DEVELOPMENT_CONTINUOUS303',success_failure='SAVED_PAIRED_RESULTS_NOT_APR',
    cost_assumptions=dict(unchanged=True,funding_unit_certified=False),
    reason_for_next_experiment='Interpret active budget effect on real net, risk and turnover',
    result_influenced_later_choice='RESEARCH_DECISION_AFTER_RESULTS')
result=dict(status='COMPLETE_ACTIVE_BUDGET_SAVED_PAIRED_DIAGNOSTIC_NOT_APR',
    task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(Path(__file__)),
    protocol_sha256=sha(pp),actual_report_sha256=sha(ap),financial_report_sha256=sha(fp),
    closed_roles=roles,rows=rows,paired_cases=pairs,control_source_resolution=old_source_resolution,
    finite_changes='ONE_RAW_BUDGET_POLICY_ONLY_NO_REPLAY_OF_SAVED_CONTROL',
    same_signal_states_verified=True,unchanged_account_engine_cost_and_caps_verified=True,
    new_market_accounts=0,saved_control_accounts=4,independent_market_evidence=False,
    HPO=0,models_fit=0,new_QA=0,new_downloads=0,orders_sent=0,locked_consumed=False,
    investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',
    process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
out=ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json')
with out.open('x') as f: json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
event.update(artifact_path=out.relative_to(ROOT).as_posix(),artifact_sha256=sha(out))
append_event(ROOT/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(path=str(out),sha256=sha(out),pairs=pairs)),flush=True)
