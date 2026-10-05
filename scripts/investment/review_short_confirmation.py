"""Paired review of one selective-short recipe; no additional replay or search."""
import argparse,json,hashlib,os
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def near(x,y):assert abs(x-y)<1e-7,(x,y)
ap=argparse.ArgumentParser();ap.add_argument('--cost',choices=['BASE27','STRESS43'],required=True);a=ap.parse_args()
producer=ROOT/f'reports/fast_research/SHORT_CONFIRMATION_{a.cost}_20261006_V1.json';raw=json.loads(producer.read_bytes());proto=raw['protocol']
assert raw['status']=='COMPLETE_FROZEN_CTA_2_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS' and len(raw['cases'])==2
assert raw['models_fit']==raw['search_configurations']==0
prior_path=ROOT/proto['research_primary_reference']['path'];assert sha(prior_path)==proto['research_primary_reference']['sha256'];prior=json.loads(prior_path.read_bytes())
task=STATE/'task-progress'/('task-'+raw['binding']['task_id']+'.json');closed=json.loads(task.read_bytes());assert closed['status']=='completed' and closed['exit_code']==0
pairs=[]
for c in raw['cases']:
 s=c['summary'];ind=c['independent'];assert ind['status'].startswith('PASS') and ind['target_reference']['status'].startswith('PASS')
 assert ind['maximum_NAV_error_USDT']<1e-7 and ind['maximum_wallet_error_USDT']<1e-7
 for art in c['artifacts'].values():assert sha(art['path'])==art['sha256']
 old=next(v for v in prior['rows'] if v['strategy']=='DC_TWO_SPEED' and v['mode']=='LONG_SHORT' and v['cost']==a.cost and v['unit']==c['unit'])
 assert s['symbols']==proto['symbols'] and prior['initial_capital_per_counterfactual_USDT']==10000
 new=dict(id=c['id'],unit=c['unit'],complete=s['completed_minutes']==s['required_minutes'],net=s['net_PnL'],gross=s['gross_PnL_same_quantities'],fees=s['fees_USDT'],execution=s['execution_cost_USDT'],funding=s['funding_USDT'],LONG=s['long_short_marked_contribution']['LONG']['net_contribution'],SHORT=s['long_short_marked_contribution']['SHORT']['net_contribution'],vol=s['daily_metrics']['annual_volatility'] if s['daily_metrics'] else None,DD=s['minute_max_drawdown'],residual=s['terminal_marked_notional'],risk=s.get('realized_exposure',{}),status=s['account_status'],regimes=ind['by_past_regime'],reference=old)
 near(new['gross']+new['funding']-new['fees']-new['execution'],new['net']);near(new['LONG']+new['SHORT'],new['net'])
 new['delta']=dict(net=new['net']-old['net_USDT'] if new['complete'] else None,LONG=new['LONG']-old['LONG'],SHORT=new['SHORT']-old['SHORT'],cost=new['fees']+new['execution']-old['fees_USDT']-old['execution_USDT'],gross=new['gross']-old['gross_USDT'],funding=new['funding']-old['funding_USDT'],vol=new['vol']-old['vol'] if new['complete'] else None,DD=new['DD']-old['DD'] if new['complete'] else None)
 for label in ('BEAR','BULL','SIDEWAYS'):
  new['delta']['SHORT_'+label]=new['regimes'].get(label,{}).get('SHORT',0)-old['by_past_regime'].get(label,{}).get('SHORT',0)
 new['passes_predeclared']=(new['complete'] and new['delta']['net']>0 and new['delta']['SHORT']>0 and new['delta']['cost']<=0 and new['delta']['vol']<=0 and new['delta']['DD']<=0 and new['delta']['SHORT_BEAR']>0 and new['regimes'].get('BULL',{}).get('SHORT',0)>=0)
 pairs.append(new)
result=dict(status='PASS_PAIRED_SHORT_RULE_REVIEW_NOT_INVESTMENT',cost=a.cost,created_utc=datetime.now(UTC).isoformat(),producer=dict(path=str(producer),sha256=sha(producer),task_id=raw['binding']['task_id'],task_sha256=sha(task)),reference=dict(path=str(prior_path),sha256=sha(prior_path)),pairs=pairs,all_pass=all(v['passes_predeclared'] for v in pairs),model_configurations=1,new_accounts=2,models_fit=0,data_downloads=0,source_sha256=sha(__file__),review_task_id=os.environ['COIN_TASK_ID'],scope='SOURCE_BOUND_SAVED_INDEPENDENT_TARGET_AND_MINUTE_FINANCE_PROOFS_REUSED; THIS_REVIEW_CHECKS_SUMMARY_BRIDGES_AND_PAIR_GATES_NOT_NEW_FINANCIAL_REPLAY',resources=dict(wall_seconds=raw['elapsed_seconds'],peak_process_RSS=raw['peak_RSS_bytes'],shared_sampled_peak=raw['shared_RAM_sampled_peak_bytes'],owned_bytes=raw['owned_bytes']),limitations=['SEEN_DEVELOPMENT_DIAGNOSTIC_SELECTED_RULE_NOT_UNSEEN','BYBIT_COST_BINANCE_SOURCE_PROXY','FUNDING_UNIT_UNKNOWN_ALL_INTERPRETATIONS_RETAINED','PAST_BTC_LABELS_NOT_CERTIFIED_BULL_BEAR_CYCLES','SAME_CAPS_NOT_SAME_ACTUAL_RISK','UNCHANGED_POSITIVE_FORECAST_DOES_NOT_MEAN_IDENTICAL_REALIZED_LONG_EXPOSURE','MARKED_RESIDUAL_NOT_LIQUIDATED_RETURN'])
out=ROOT/f'reports/SHORT_CONFIRMATION_{a.cost}_REVIEW_20261006_V1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
print(json.dumps(dict(all_pass=result['all_pass'],pairs=[{k:v[k] for k in ('id','complete','net','SHORT','vol','DD','delta','passes_predeclared')} for v in pairs]),ensure_ascii=False))
