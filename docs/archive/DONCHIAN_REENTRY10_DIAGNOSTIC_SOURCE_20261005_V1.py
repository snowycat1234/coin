"""Compare saved full accounts; no posthoc NAV scaling or market replay."""
import hashlib,json,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment import compare_multi_asset_portfolios as reuse
from scripts.research_v8.registry import FIELDS,append_event
STEM='DONCHIAN_REENTRY10_20261005_V1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p,h=None):
    if h:assert sha(p)==h,str(p)
    return json.loads(Path(p).read_bytes())
def closed(a):
    t=read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];return t
pp=ROOT/'protocols'/(STEM+'.json');p=read(pp);ctrl=p['saved_control']
ap=ROOT/'reports/fast_research'/(STEM+'.json');fp=ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json')
a=read(ap);f=read(fp);old=read(ROOT/ctrl['actual_path'],ctrl['actual_sha256']);oldf=read(ROOT/ctrl['financial_path'],ctrl['financial_sha256']);oldp=read(ROOT/ctrl['protocol_path'],ctrl['protocol_sha256'])
roles={n:closed(v) for n,v in [('market',a),('financial',f),('control_market',old),('control_financial',oldf)]}
assert a['complete_calendar_cases']==old['complete_calendar_cases']==f['financial_case_calls']==oldf['financial_case_calls']==4
assert f['status'].startswith('PASS_CONFIGURED_N_')
for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
resolution={}
for n,h in oldp['source_hashes'].items():
    if sha(ROOT/n)==h:resolution[n]='UNCHANGED_CURRENT_BYTES'
    else:
        blob=subprocess.check_output(['git','show',ctrl['accepted_source_commit']+':'+n],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest()==h,n;resolution[n]='EXACT_GIT_33FA0DE_BYTES_NOT_RUNTIME_DEPENDENCY'
for key in ('start','end_exclusive','period_days','data_manifest','source_acceptances','pools','pool_receipt','initial_capital_USDT','account_path','data_role','signal','allocation'):
    assert p[key]==oldp[key],key
for n in reuse.FINANCE_SOURCES:assert p['source_hashes'][n]==oldp['source_hashes'][n],n
changed={'reentry_period','initial_entry_period','reentry_predicate','reentry_armed_only_by_signal_exit','successful_reentry_clears_arm','ineligible_or_cash_resets_reentry_arm','original_long_entry_filter_hooks_used','original_SMA200_filter_used','reentry_is_COIN_adaptation'}
assert {k:v for k,v in p['strategy_rules'].items() if k not in changed}=={k:v for k,v in oldp['strategy_rules'].items() if k not in changed}
rows=[];pairs=[]
for new in a['cases']:
    control=next(c for c in old['cases'] if c['id']==new['id']);metrics={};targets={};metas={}
    assert new['symbols']==control['symbols'] and new['cost_id']==control['cost_id'] and new['unit_id']==control['unit_id']
    for label,c in [('REENTRY20',control),('REENTRY10',new)]:
        for item in c['artifacts'].values():assert sha(item['path'])==item['sha256']
        assert c['summary']['completed_minutes']==c['summary']['required_minutes']==436320
        targets[label]=pl.read_parquet(c['artifacts']['targets.parquet']['path']);metas[label]=read(c['artifacts']['target_meta.json']['path'])
        m=reuse.measures(c);metrics[label]=m
        rows.append(dict(policy=label,case_id=c['id'],cost=c['cost_id'],funding_unit=c['unit_id'],**m,months_continuous_not_fresh_accounts=c['summary']['months']))
    x,y=targets['REENTRY20'],targets['REENTRY10']
    assert x.select('available_us','symbol','mode','eligibility_reason').equals(y.select('available_us','symbol','mode','eligibility_reason'))
    assert all(rx['covariance_symbol_order']==ry['covariance_symbol_order'] for rx,ry in zip(metas['REENTRY20']['risk'],metas['REENTRY10']['risk'],strict=True))
    weights=y['target_weight'].to_numpy();assert np.abs(weights).max()<=.3+1e-13
    assert y.group_by('available_us').agg(pl.col('target_weight').abs().sum())['target_weight'].max()<=.6+1e-13
    mx,my=metrics['REENTRY20'],metrics['REENTRY10'];gross=my['gross_USDT']-mx['gross_USDT'];cost=(my['fees_USDT']+my['execution_USDT'])-(mx['fees_USDT']+mx['execution_USDT']);fund=my['funding_USDT']-mx['funding_USDT'];net=my['net_USDT']-mx['net_USDT']
    assert abs(net-(gross-cost+fund))<1e-7
    diff=np.abs(weights-x['target_weight'].to_numpy())>1e-12
    pairs.append(dict(cost=new['cost_id'],funding_unit=new['unit_id'],net_increment_USDT=net,gross_increment_USDT=gross,cost_increment_USDT=cost,funding_increment_USDT=fund,
        changed_target_rows=int(diff.sum()),changed_decision_days=y.filter(pl.Series('changed',diff))['available_us'].n_unique(),
        changed_signal_rows=int(np.sum((y['raw_signed_target'].to_numpy()!=0)!=(x['raw_signed_target'].to_numpy()!=0))),
        annualized_daily_vol_increment=my['actual_daily_annualized_volatility']-mx['actual_daily_annualized_volatility'],minute_MDD_increment=my['minute_MDD']-mx['minute_MDD'],turnover_increment=my['turnover_full_capital']-mx['turnover_full_capital'],
        terminal_cash_control=mx['terminal_cash_realized'],terminal_cash_challenger=my['terminal_cash_realized'],actual_risk_matched=False))
out=ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json')
value=dict(status='COMPLETE_REENTRY10_SAVED_PAIRED_DIAGNOSTIC_NOT_APR',task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(Path(__file__)),protocol_sha256=sha(pp),actual_report_sha256=sha(ap),financial_report_sha256=sha(fp),closed_roles=roles,control_source_resolution=resolution,rows=rows,paired_cases=pairs,
    independent_market_evidence=False,invest_candidate='NONE',long_term_APR='NOT_EVALUABLE',market_replays=0,posthoc_scaling=False,source_inputs_unchanged=True)
with out.open('x') as writer:json.dump(value,writer,indent=2,ensure_ascii=False,allow_nan=False);writer.write('\n')
event=dict.fromkeys(FIELDS);event.update(event_id='D070-REENTRY10-SAVED-PAIR:RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=p['experiment_id'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),data_manifest_hash=p['data_manifest']['sha256'],protocol_hash=sha(pp),model_family='NONE',fits=0,all_folds='SEEN_DEVELOPMENT_CONTINUOUS303',success_failure=value['status'],artifact_path=out.relative_to(ROOT).as_posix(),artifact_sha256=sha(out),reason_for_next_experiment='Compare one-factor armed recovery reentry on actual net, cost and risk',result_influenced_later_choice='DECISION_AFTER_RESULTS')
append_event(ROOT/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(path=str(out),sha256=sha(out),pairs=pairs)))
