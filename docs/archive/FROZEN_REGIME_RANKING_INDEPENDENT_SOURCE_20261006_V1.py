"""Independent scalar features, hand path, labels and published rank metrics."""
import json,os,statistics,math
from pathlib import Path
from datetime import UTC,datetime
import importlib.metadata
import polars as pl
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
from scripts.investment.cta_cycle_window import load_window
name='reports/REGIME_RANKING_SCREEN_20261006_V1.json';r=json.loads((ROOT/name).read_bytes());p=r['protocol'];day=86_400_000_000
task=r['task_id'];from quant.paths import STATE
t=json.loads((STATE/'task-progress'/('task-'+task+'.json')).read_bytes());assert t['status']=='completed' and t['exit_code']==0
window=load_window(p['data_manifest']['path'],('BTCUSDT',),1630454400000000,1704067200000000)
bars=list(window['daily'].filter(pl.col('symbol')=='BTCUSDT').sort('close_us').iter_rows(named=True));lookup={v['close_us']:i for i,v in enumerate(bars)}
names=r['expert_order'];previous=dict.fromkeys(names,0.);previous['CASH']=1.;expected=[];max_feature_error=max_weight_error=max_label_error=0.
for feature in r['feature_states']:
    index=lookup[feature['decision_us']];history=bars[index-200:index+1];assert len(history)==201 and all(v['available_us']<=feature['decision_us'] for v in history)
    close=[v['close'] for v in history];returns=[close[i+1]/close[i]-1 for i in range(200)]
    ma50=statistics.fmean(close[-50:]);ma200=statistics.fmean(close[-200:]);vol30=statistics.stdev(returns[-30:]);vol200=statistics.stdev(returns)
    sign=lambda v:1 if v>0 else -1 if v<0 else 0
    slow=sign(close[-1]-ma200);fast=sign(close[-1]-ma50);high=vol30>vol200
    assert (slow,fast,high)==(feature['slow'],feature['fast'],feature['high_vol'])
    for actual,value in [(feature['distance50'],close[-1]/ma50-1),(feature['distance200'],close[-1]/ma200-1),(feature['sample_vol30'],vol30),(feature['sample_vol200'],vol200)]:
        max_feature_error=max(max_feature_error,abs(actual-value));assert abs(actual-value)<1e-10
    desired=dict.fromkeys(names,0.)
    if slow<0 and fast<0:desired.update(SMA200_SIGNED=.75,CASH=.25)
    elif slow<0 and fast>0:desired.update(HOLD=.5,CASH=.5)
    elif slow>0 and fast>0:desired.update(SMA200_SIGNED=.5,HOLD=.5)
    elif slow>0 and fast<0:desired.update(SMA200_SIGNED=.25,CASH=.75)
    else:desired['CASH']=1.
    if high:
        desired={key:value*.5 for key,value in desired.items()};desired['CASH']+=.5
    distance=sum(abs(desired[n]-previous[n]) for n in names);factor=min(1,.5/distance) if distance else 1.
    current={n:previous[n]+factor*(desired[n]-previous[n]) for n in names};expected.append(current);previous=current
for actual,w in zip(r['weight_path'],expected):
    max_weight_error=max(max_weight_error,max(abs(actual[i]-w[n]) for i,n in enumerate(names)))
    assert max_weight_error<1e-12 and abs(sum(w.values())-1)<1e-12
for fold in r['maturity_folds']:
    i=fold['index'];decision=r['feature_states'][i]['decision_us'];assert fold['label_end_us']==decision+60*day
    assert fold['mature_indices']==list(range(i)) and i>=4
    assert all(r['feature_states'][j]['decision_us']+60*day<=decision for j in fold['mature_indices'])
di=json.loads((ROOT/p['oracle_reference']['path']).read_bytes());details=[]
for result in r['results']:
    labels={}
    for n in names:
        entry=next(v for v in di['library'] if v['expert']==n and v['unit']==result['unit']);artifact=entry['artifacts']['daily_nav.parquet'];assert sha(artifact['path'])==artifact['sha256']
        f=pl.read_parquet(artifact['path']).sort('day_end_us');nav=[10000.]+f['nav'].to_list()
        labels[n]=[nav[(i+1)*60]/nav[i*60]-1 for i in range(12)]
    ranks=[]
    for i in range(12):
        values=[labels[n][i] for n in names]
        # Average ties by pairwise comparisons, independent of SciPy rankdata.
        ranked=[(sum(other<v for other in values)+.5*(sum(other==v for other in values)-1))/7 for v in values]
        ranks.append(ranked)
        max_label_error=max(max_label_error,max(abs(values[k]-result['net_relative_ranking_labels'][i][k]) for k in range(8)))
        assert ranked==result['ordinal_ranks'][i]
    ix=[v['index'] for v in r['maturity_folds']]
    hand=[sum(expected[i][n]*ranks[i][k] for k,n in enumerate(names)) for i in ix]
    assert max(abs(a-b) for a,b in zip(hand,result['metrics']['HAND_FIXED']['per_fold_weighted_rank']))<1e-12
    assert abs(statistics.fmean(hand)-result['metrics']['HAND_FIXED']['mean_weighted_rank'])<1e-12
    assert len(result['placebo_shuffle']['scores'])==len(result['placebo_samefrequency_random']['scores'])==32
    assert result['checks']['rank_gt_shuffle95']==(statistics.fmean(hand)>result['placebo_shuffle']['percentile95'])
    details.append(dict(unit=result['unit'],mean_hand_rank=statistics.fmean(hand),all8fold_scores_verified=True,all12nonoverlap_rank_labels_verified=True))
assert max_label_error<1e-12 and r['decision']=='PAUSE_THIS_FIXED_STATE_MAP_NO_RANKING_EVIDENCE_RETAIN_STRONG_SINGLE'
out=dict(status='PASS_INDEPENDENT_SCALAR_FEATURE_TIME_LABEL_RANK_AND_FIXED_WEIGHT_PATH',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    input=dict(path=name,sha256=sha(ROOT/name)),maximum_feature_error=max_feature_error,maximum_weight_error=max_weight_error,maximum_label_error=max_label_error,
    details=details,official_rank_library=dict(package='scipy',version=importlib.metadata.version('scipy'),license='BSD-3-Clause',local_modifications='NONE'),
    independent_reference='stdlib statistics plus scalar pairwise rank comparisons; verification only, not production indicator implementation',
    new_accounts=0,models_fit=0,scope='12complete labels,8chronological evaluation folds, all past201daily availability, official rolling features, no future input or investment return claim',created_utc=datetime.now(UTC).isoformat())
with (ROOT/'reports/REGIME_RANKING_SCREEN_INDEPENDENT_20261006_V1.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],feature_error=max_feature_error,weight_error=max_weight_error,scipy=out['official_rank_library']['version'])))
