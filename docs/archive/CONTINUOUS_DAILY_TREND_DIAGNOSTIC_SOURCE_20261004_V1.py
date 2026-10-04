"""Explain saved continuous accounts; no account replay or parameter changes."""
import hashlib,json,os,resource
from pathlib import Path
from datetime import UTC,datetime
from decimal import Decimal
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment import compare_multi_asset_portfolios as reuse
from scripts.research_v8.registry import FIELDS,append_event
assert os.environ['COIN_TASK_ID']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p,h=None):
    p=Path(p);assert p.is_file() and not p.is_symlink()
    if h:assert sha(p)==h
    return json.loads(p.read_bytes())
def D(r,k):return reuse.decimal(r,k)
def closed(r,code=0):
    t=read(STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json'))
    assert t['status']==('completed' if code==0 else 'failed') and t['exit_code']==code;return t['id']
recipes={};rows=[]
for recipe in ['HOLD_TWO','HOLD_TEN','DONCHIAN_TEN']:
    stem='CONTINUOUS_DAILY_TREND_'+recipe+'_20261004_V1'
    ap=ROOT/'reports/fast_research'/(stem+'.json');a=read(ap);failed=recipe=='HOLD_TEN';task=closed(a,1 if failed else 0)
    if failed:assert a['status']=='FAILED_MULTI_ASSET_DEVELOPMENT_COMPARISON' and a['reason']=='Finite output/wall research budget reached'
    fp=ROOT/'reports/fast_research'/('CONTINUOUS_DAILY_TREND_'+recipe+'_FINANCIAL_20261004_V1.json');f=read(fp)
    assert f['status'].startswith('PASS_CONFIGURED_N_') and f['financial_case_calls']==f['completed_cases_verified']==4
    assert closed(f)
    p=read(ROOT/'protocols'/(stem+'.json'));assert a['binding']['source_hashes']==p['source_hashes']
    assert a['actual_calendar_days']==303 and a['completed_cases']==4 and all(c['summary']['completed_minutes']==c['summary']['required_minutes']==436320 for c in a['cases'])
    for c in a['cases']:
        s=c['summary'];meta=read(c['artifacts']['target_meta.json']['path'],c['artifacts']['target_meta.json']['sha256'])
        tp=c['artifacts']['targets.parquet'];assert sha(Path(tp['path']))==tp['sha256']
        targets=pl.read_parquet(tp['path']);target_at={(r['available_us'],r['symbol']):r for r in targets.iter_rows(named=True)}
        bp=c['artifacts']['breaches.json'];breach=read(bp['path'],bp['sha256']);risk_times={int(r['signal_us']) for r in breach}
        trp=c['artifacts']['trades.json'];tr=read(trp['path'],trp['sha256']);by={}
        for r in tr:
            q0,q1=D(r,'quantity_before'),D(r,'quantity_after');sig=int(r['signal_us'])
            target=target_at.get((sig,r['symbol']))
            if sig==1751328000000000-6*60000000:reason='TERMINAL_EXIT' if q0!=0 and abs(q1)<abs(q0) else 'UNKNOWN'
            elif sig in risk_times:reason='RISK_REDUCTION_SIGNAL_TIMESTAMP' if q0!=0 and abs(q1)<abs(q0) else 'UNKNOWN'
            elif target is None:reason='UNKNOWN'
            elif target['eligibility_reason']!='ELIGIBLE':reason=target['eligibility_reason']
            elif target['target_weight']==0:reason='SIGNAL_FLAT_EXIT'
            elif q0==0 and q1!=0:reason='ENTRY_FROM_FLAT'
            elif q0*q1<0:reason='REVERSAL'
            elif abs(q1)>abs(q0):reason='DAILY_ALLOCATION_INCREASE'
            elif abs(q1)<abs(q0):reason='DAILY_ALLOCATION_DECREASE'
            else:reason='UNKNOWN'
            direction='LONG' if (q0 if r['leg']=='CLOSE' else D(r,'position_delta'))>0 else 'SHORT'
            key=reason+'|'+direction;one=by.setdefault(key,dict(fill_legs=0,notional=Decimal(0),fee=Decimal(0),execution=Decimal(0)))
            one['fill_legs']+=1;one['notional']+=D(r,'quantity')*D(r,'fill_price');one['fee']+=D(r,'fee_USDT_mid');one['execution']+=D(r,'execution_cost')
        assert abs(sum((v['fee'] for v in by.values()),Decimal(0))-D(s,'fees_USDT'))<Decimal('1e-7')
        assert abs(sum((v['execution'] for v in by.values()),Decimal(0))-D(s,'execution_cost_USDT'))<Decimal('1e-7')
        perday=targets.group_by('available_us').agg(pl.col('raw_signed_target').abs().sum().alias('raw_gross'),pl.col('target_weight').abs().sum().alias('target_gross'),(pl.col('raw_signed_target')!=0).sum().alias('active'))
        metrics=reuse.measures(c)
        rows.append(dict(recipe=recipe,case_id=c['id'],cost=c['cost_id'],funding_unit=c['unit_id'],
            **metrics,monthly_continuous_contributions=s['months'],
            opportunity_budget=dict(raw_member_fraction=.6/len(c['symbols']),inactive_budget_redistributed=False,
                mean_active_members=float(perday['active'].mean()),cash_signal_days=int(perday['active'].eq(0).sum()),
                mean_raw_gross=float(perday['raw_gross'].mean()),mean_risk_target_gross=float(perday['target_gross'].mean()),
                peak_raw_gross=float(perday['raw_gross'].max()),peak_risk_target_gross=float(perday['target_gross'].max())),
            fill_cost_by_reconstructed_reason_and_direction={k:{n:float(v) if isinstance(v,Decimal) else v for n,v in x.items()} for k,x in by.items()},
            reason_scope='Quantity lifecycle and exact target/breach/terminal signal timestamps only; UNKNOWN retained. This assigns costs, not causal profit.',
            reconstructed_reason_costs_match_total=True))
    recipes[recipe]=dict(actual_report=str(ap.relative_to(ROOT)),sha256=sha(ap),actual_closed_task=task,
        independent_report=str(fp.relative_to(ROOT)),independent_sha256=sha(fp),elapsed_seconds=a['elapsed_seconds'],producer_status=a['status'],producer_budget_passed=not failed,original_failed_task_preserved=failed,
        peak_RSS_bytes=a['peak_RSS_bytes'],shared_RAM_sampled_peak_bytes=a['shared_RAM_sampled_peak_bytes'],owned_bytes=a['owned_bytes'])
# Pool correlation before scoring is descriptive, never used for reselection.
mp=STATE/'d064-longspan-input-binding-20261004-v1/INPUT_MANIFEST.json';m=read(mp)
ret=[]
for symbol in m['selected_symbols']:
    src=[r for r in m['daily_records'] if r['symbol']==symbol and r['month']=='2024-08'];assert len(src)==1
    r=src[0];p=Path(r['normalized_path']);assert sha(p)==r['normalized_sha256']
    bars=pl.read_parquet(p,columns=['close_us','available_us','close']).sort('close_us')
    assert np.array_equal(bars['close_us'].to_numpy(),np.arange(1722470400000000+86400000000,1725148800000000+1,86400000000))
    assert bars['available_us'].max()<=1725148800000000 and bars.height==31
    close=bars['close'].to_numpy();ret.append(np.diff(close)/close[:-1])
x=np.column_stack(ret);corr=np.corrcoef(x,rowvar=False);cov=np.cov(x,rowvar=False,ddof=1);eig=np.linalg.eigvalsh(corr)
w=np.repeat(.06,10);rc=w*(cov@w);riskshare=rc/rc.sum()
correlation=dict(role='30_AUGUST_RETURNS_AVAILABLE_BY_SEPTEMBER1_DECISION_EXCLUSIVE_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED',
    symbols=m['selected_symbols'],observations=30,
    dependence_scope='30-return correlation participation ratio, not independent coins/sample count/long-term diversification. Risk shares use static raw .06, not actual portfolio.',mean_pairwise_correlation=float(corr[np.triu_indices(10,1)].mean()),
    correlation_eigen_effective_dimension=float(eig.sum()**2/(eig@eig)),
    first_correlation_component_share=float(eig[-1]/eig.sum()),equal_weight_covariance_risk_contribution_share=riskshare.tolist(),
    maximum_equal_weight_risk_contribution_share=float(riskshare.max()),correlation_matrix=corr.tolist())
# All pairs use one full10k per portfolio and the same costs/market; never sum wallets.
actuals={name:read(ROOT/value['actual_report']) for name,value in recipes.items()}
protos={name:reuse.saved_protocol(actual)[0] for name,actual in actuals.items()}
for p in protos.values():
    for key in ['start','end_exclusive','initial_capital_USDT','pools','data_manifest','account_path','data_role','pool_receipt']:
        assert p[key]==protos['HOLD_TWO'][key],key
    assert p['source_hashes']==protos['HOLD_TWO']['source_hashes']
index={(r['recipe'],r['cost'],r['funding_unit']):r for r in rows};pairs=[]
for contrast,left,right in [('POOL','HOLD_TWO','HOLD_TEN'),('SIGNAL','HOLD_TEN','DONCHIAN_TEN')]:
    for c in actuals[left]['cases']:
        mate=next(q for q in actuals[right]['cases'] if (q['cost_id'],q['unit_id'])==(c['cost_id'],c['unit_id']))
        assert c['summary']['cost_scenario']==mate['summary']['cost_scenario'] and c['summary']['unit_scenario']==mate['summary']['unit_scenario']
        x=index[(left,c['cost_id'],c['unit_id'])];y=index[(right,c['cost_id'],c['unit_id'])]
        delta=y['net_USDT']-x['net_USDT'];gross=y['gross_USDT']-x['gross_USDT'];cost=(y['fees_USDT']+y['execution_USDT'])-(x['fees_USDT']+x['execution_USDT']);fund=y['funding_USDT']-x['funding_USDT']
        assert abs(delta-(gross-cost+fund))<1e-7
        pairs.append(dict(contrast=contrast,control_recipe=left,challenger_recipe=right,cost=c['cost_id'],funding_unit=c['unit_id'],net_increment_USDT=delta,gross_increment_USDT=gross,cost_increment_USDT=cost,funding_increment_USDT=fund,actual_risk_matched=False,control_terminal_cash=x['terminal_cash_realized'],challenger_terminal_cash=y['terminal_cash_realized'],source_budget_failure_preserved=left=='HOLD_TEN' or right=='HOLD_TEN'))
result=dict(status='COMPLETE_SAVED_CONTINUOUS303_ECONOMIC_AND_OPPORTUNITY_DIAGNOSTIC_NOT_APR',
    task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(Path(__file__)),created_utc=datetime.now(UTC).isoformat(),
    recipes=recipes,rows=rows,paired_saved_accounts=pairs,CASH=dict(net_USDT=0,capital_USDT=10000,risk=0),pre_score_pool_dependence=correlation,market_accounts=0,models_fit=0,HPO=0,
    new_downloads=0,new_QA=0,locked_consumed=False,orders_sent=0,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE')
out=ROOT/'reports/fast_research/CONTINUOUS_DAILY_TREND_DIAGNOSTIC_20261004_V1.json'
with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
e=dict.fromkeys(FIELDS);e.update(event_id='D064-CONTINUOUS303-DIAGNOSTIC:RESULT',experiment_id='D064-CONTINUOUS303-DIAGNOSTIC',event_type='SAVED_RESEARCH_DIAGNOSTIC',success_failure=result['status'],artifact_path=out.relative_to(ROOT).as_posix(),artifact_sha256=sha(out),reason_for_next_experiment='Explain saved price/cost/risk/opportunity differences without changing old orders')
append_event(ROOT/'reports/experiment_registry.jsonl',e)
print(json.dumps(dict(status=result['status'],correlation=correlation,rows=[{k:r[k] for k in ['recipe','cost','funding_unit','net_USDT','gross_USDT','fees_USDT','execution_USDT','funding_USDT','minute_MDD','actual_daily_annualized_volatility']} for r in rows])),flush=True)
