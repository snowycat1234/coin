"""Fixed-state ranking diagnostic, chronological labels; no trading model fit.

Ranks of saved expert net returns are a label proxy. This script produces no
portfolio return, Sharpe, APR or fill claim. Placebos are diagnostic controls.
"""
import argparse,json,os,time,resource
from pathlib import Path
from datetime import UTC,datetime
import numpy as np
import polars as pl
from scipy.stats import rankdata
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
from scripts.investment.cta_cycle_window import load_window
from scripts.task_progress_api import Progress

DAY=86_400_000_000

def features(bars,decisions):
    b=bars.filter(pl.col('symbol')=='BTCUSDT').sort('close_us')
    assert b.height==b['close_us'].n_unique() and np.all(np.diff(b['close_us'])==DAY)
    b=b.with_columns((pl.col('close')/pl.col('close').shift(1)-1).alias('r'))
    b=b.with_columns(pl.col('close').rolling_mean(50).alias('ma50'),pl.col('close').rolling_mean(200).alias('ma200'),
        pl.col('r').rolling_std(30,ddof=1).alias('v30'),pl.col('r').rolling_std(200,ddof=1).alias('v200'))
    lookup={v['close_us']:v for v in b.iter_rows(named=True)};out=[]
    for t in decisions:
        r=lookup[int(t)];assert r['available_us']<=t and all(r[k] is not None and np.isfinite(r[k]) for k in ('close','ma50','ma200','v30','v200'))
        past=b.filter(pl.col('close_us')<=t).tail(201);assert past.height==201 and past['available_us'].max()<=t
        out.append(dict(decision_us=int(t),slow=int(np.sign(r['close']-r['ma200'])),fast=int(np.sign(r['close']-r['ma50'])),
            high_vol=r['v30']>r['v200'],distance50=r['close']/r['ma50']-1,distance200=r['close']/r['ma200']-1,
            sample_vol30=r['v30'],sample_vol200=r['v200']))
    return out

def rule_weights(names,state):
    """One preregistered map, never selected using future block returns."""
    w=np.zeros(len(names));slow,fast=state['slow'],state['fast']
    if slow<0 and fast<0:blend={'SMA200_SIGNED':.75,'CASH':.25}
    elif slow<0 and fast>0:blend={'HOLD':.5,'CASH':.5}
    elif slow>0 and fast>0:blend={'SMA200_SIGNED':.5,'HOLD':.5}
    elif slow>0 and fast<0:blend={'SMA200_SIGNED':.25,'CASH':.75}
    else:blend={'CASH':1.}
    for n,v in blend.items():w[names.index(n)]=v
    if state['high_vol']:
        w*=.5;w[names.index('CASH')]+=.5
    return w

def bounded_path(desired,initial,max_l1=.5):
    previous=np.asarray(initial,float);out=[]
    assert (previous>=0).all() and abs(previous.sum()-1)<1e-12
    for value in desired:
        value=np.asarray(value,float);assert value.shape==previous.shape and (value>=0).all() and abs(value.sum()-1)<1e-12
        distance=float(np.abs(value-previous).sum());scale=min(1.,max_l1/distance) if distance else 1.
        current=previous+scale*(value-previous)
        assert np.abs(current-previous).sum()<=max_l1+1e-12 and (current>=-1e-15).all() and abs(current.sum()-1)<1e-12
        out.append(current);previous=current
    return np.array(out)

def maturity_folds(decisions,ends,min_history=4):
    folds=[]
    for i,t in enumerate(decisions):
        mature=[j for j in range(i) if ends[j]<=t]
        assert mature==list(range(i)) and all(ends[j]<=t and ends[j]<=decisions[i] for j in mature)
        if len(mature)>=min_history:folds.append(dict(index=i,decision_us=int(t),mature_indices=mature,label_end_us=int(ends[i])))
    return folds

def metric(weight,ranks,folds,decisions):
    ix=[v['index'] for v in folds];score=(weight*ranks).sum(axis=1);years={}
    for i in ix:
        year=str(datetime.fromtimestamp(int(decisions[i])//1_000_000,UTC).year);years.setdefault(year,[]).append(float(score[i]))
    return dict(mean_weighted_rank=float(np.mean(score[ix])),per_fold_weighted_rank=[float(score[i]) for i in ix],
        winner_weight_mass=[float(weight[i][ranks[i]==ranks[i].max()].sum()) for i in ix],
        mean_winner_weight_mass=float(np.mean([weight[i][ranks[i]==ranks[i].max()].sum() for i in ix])),
        by_decision_year={y:dict(folds=len(v),mean_weighted_rank=float(np.mean(v))) for y,v in years.items()})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    spec=json.loads((ROOT/a.protocol).read_bytes());began=time.monotonic();phase=Progress()
    assert os.getenv('COIN_TASK_ID') and spec['horizon_days']==60 and spec['min_mature_labels']==4 and spec['placebo_replicates']==32
    for p,h in spec['source_hashes'].items():assert sha(ROOT/p)==h
    assert sha(ROOT/'state/dataset_lock.json')==spec['locked_sha256']
    import xml.etree.ElementTree as ET
    test=spec['tests'];assert sha(ROOT/test['path'])==test['sha256'];suites=list(ET.parse(ROOT/test['path']).getroot().iter('testsuite'))
    assert sum(int(v.get('tests',0)) for v in suites)==test['count'] and not any(int(v.get('errors',0))+int(v.get('failures',0)) for v in suites)
    ref=ROOT/spec['oracle_reference']['path'];assert sha(ref)==spec['oracle_reference']['sha256'];oracle=json.loads(ref.read_bytes())
    tid=oracle['task_id'];task=json.loads((STATE/'task-progress'/('task-'+tid+'.json')).read_bytes());assert task['status']=='completed' and task['exit_code']==0
    names=oracle['protocol']['experts'];assert len(names)==8
    start=1640995200000000;end=1704067200000000;decisions=np.arange(start,start+720*DAY,60*DAY,dtype=np.int64);ends=decisions+60*DAY
    folds=maturity_folds(decisions,ends,spec['min_mature_labels']);assert len(decisions)==12 and len(folds)==8
    phase.update('读取已验完整日线，固定三状态特征',0,3,'阶段')
    manifest=spec['data_manifest'];assert sha(manifest['path'])==manifest['sha256']
    window=load_window(manifest['path'],('BTCUSDT',),1630454400000000,end)
    states=features(window['daily'],decisions);cash=np.zeros(len(names));cash[names.index('CASH')]=1
    fixed=np.zeros(len(names));fixed[names.index('SMA200_SIGNED')]=.5;fixed[names.index('HOLD')]=.25;fixed[names.index('CASH')]=.25
    desired=np.array([rule_weights(names,v) for v in states]);hand=bounded_path(desired,cash)
    lag=bounded_path(np.vstack([cash,desired[:-1]]),cash)
    constant=np.tile(fixed,(12,1));equal=np.full((12,len(names)),1/len(names))
    best=np.zeros_like(hand);best[:,names.index('SMA200_SIGNED')]=1
    # Diagnostic controls retain the observed change-block pattern and L1 step
    # sizes. Their future change schedule is conditioned, not a deployable rule.
    rng=np.random.default_rng(spec['seed']);shuffled=[];random=[];change_steps=[float(np.abs(hand[0]-cash).sum())]+[float(np.abs(hand[i]-hand[i-1]).sum()) for i in range(1,12)]
    for repeat in range(32):
        shuffled.append(bounded_path(desired[rng.permutation(12)],cash))
        previous=cash.copy();path=[]
        for distance in change_steps:
            if distance>1e-12:
                candidates=[j for j in range(len(names)) if 2*(1-previous[j])>=distance-1e-12]
                j=int(rng.choice(candidates));choice=np.zeros(len(names));choice[j]=1
                previous=previous+(distance/(2*(1-previous[j])))*(choice-previous)
            path.append(previous.copy())
        random.append(np.array(path))
    assert all(np.array_equal(np.linalg.norm(np.diff(np.vstack([cash,p]),axis=0),ord=1,axis=1)>1e-12,np.array(change_steps)>1e-12) for p in random)
    phase.update('完整60日排名标签与时间顺序成熟核对',1,3,'阶段');results=[];bindings=[]
    for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
        growth=[]
        for name in names:
            entry=next(v for v in oracle['library'] if v['unit']==unit and v['expert']==name);v=entry['artifacts']['daily_nav.parquet']
            p=Path(v['path']);assert p.is_relative_to(STATE) and sha(p)==v['sha256']
            f=pl.read_parquet(p).sort('day_end_us');assert f.height==730 and np.array_equal(f['day_end_us'].to_numpy(),np.arange(start+DAY,end+DAY,DAY))
            nav=np.r_[10000.,f['nav'].to_numpy()];assert (nav>0).all()
            growth.append([nav[(i+1)*60]/nav[i*60]-1 for i in range(12)]);bindings.append(dict(expert=name,unit=unit,**v))
        growth=np.array(growth).T;ranks=np.array([(rankdata(v,method='average')-1)/7 for v in growth])
        metrics={n:metric(w,ranks,folds,decisions) for n,w in [('HAND_FIXED',hand),('LAG60_FEATURES',lag),('STATIC_DIRECTION3',constant),('EQUAL8',equal),('BEST_SINGLE_SMA200_DEVELOPMENT_REFERENCE',best)]}
        # Past-only statistical rank reference, no fitted trading classifier.
        expanding=np.tile(cash,(12,1))
        for fold in folds:
            scores=ranks[fold['mature_indices']].mean(axis=0);expanding[fold['index']]=0;expanding[fold['index'],int(np.argmax(scores))]=1
        metrics['MATURE_PAST_RANK_REFERENCE']=metric(expanding,ranks,folds,decisions)
        shuffle_scores=[metric(w,ranks,folds,decisions)['mean_weighted_rank'] for w in shuffled]
        random_scores=[metric(w,ranks,folds,decisions)['mean_weighted_rank'] for w in random]
        baseline=max(metrics[n]['mean_weighted_rank'] for n in ('STATIC_DIRECTION3','EQUAL8','BEST_SINGLE_SMA200_DEVELOPMENT_REFERENCE','MATURE_PAST_RANK_REFERENCE'))
        actual=metrics['HAND_FIXED']['mean_weighted_rank'];checks=dict(rank_gt_strong_reference_by005=actual>=baseline+.05,
            rank_gt_shuffle95=actual>float(np.quantile(shuffle_scores,.95)),rank_gt_samefrequency_random95=actual>float(np.quantile(random_scores,.95)),
            rank_gt_lag60=actual>metrics['LAG60_FEATURES']['mean_weighted_rank'])
        years={}
        for year,h in metrics['HAND_FIXED']['by_decision_year'].items():
            baseline_year=max(metrics[n]['by_decision_year'][year]['mean_weighted_rank'] for n in ('STATIC_DIRECTION3','EQUAL8','BEST_SINGLE_SMA200_DEVELOPMENT_REFERENCE','MATURE_PAST_RANK_REFERENCE'))
            years[year]=dict(folds=h['folds'],hand_rank=h['mean_weighted_rank'],strong_reference=baseline_year)
        checks['both_decision_years_positive_increment']=all(v['hand_rank']>v['strong_reference'] and v['folds']>=3 for v in years.values())
        results.append(dict(unit=unit,net_relative_ranking_labels=growth.tolist(),ordinal_ranks=ranks.tolist(),metrics=metrics,year_comparison=years,
            placebo_shuffle=dict(replicates=32,scores=shuffle_scores,percentile95=float(np.quantile(shuffle_scores,.95)),causal_policy=False),
            placebo_samefrequency_random=dict(replicates=32,scores=random_scores,percentile95=float(np.quantile(random_scores,.95)),causal_policy=False,scope='Conditioned same realized step schedule and L1 magnitude, random expert destinations'),
            checks=checks,pass_mechanism_probe=all(checks.values()),oracle_ranking_ceiling=1.,hand_to_oracle_rank_gap=1-actual))
    passed=all(v['pass_mechanism_probe'] for v in results)
    assert time.monotonic()-began<spec['budget']['wall_seconds'] and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['budget']['RSS_bytes']
    out=dict(status='COMPLETE_CAUSAL_FIXED_STATE_RANKING_PROBE_NOT_PORTFOLIO_OR_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),protocol=spec,protocol_sha256=sha(ROOT/a.protocol),
        results=results,feature_states=states,weight_path=hand.tolist(),expert_order=names,maturity_folds=folds,data_bindings=bindings,
        evaluated_nonoverlap_horizons=8,all_full_horizons=12,tail10days_not_a_label=True,
        conditional_random_switches=sum(v>1e-12 for v in change_steps),L1_steps=change_steps,
        statistical_rank_reference_updates=len(folds)*2,trading_models_fit=0,new_economic_accounts=0,GPU_hours=0,locked_consumed=False,
        decision='RETAIN_MECHANISM_PROBE_NEEDS_INDEPENDENT_DATA_NO_CLASSIFIER_PROMOTION' if passed else 'PAUSE_THIS_FIXED_STATE_MAP_NO_RANKING_EVIDENCE_RETAIN_STRONG_SINGLE',
        investment_candidate='NONE_CASH',net_portfolio_return='NOT_RUN',long_term_APR='NOT_EVALUABLE',
        limits=['ONE_SEEN_BTC_CYCLE_ONLY8EVALUATED_LABELS','LABELS_ARE_NET_MARKED_EXPERT_NAV_RELATIVE_RETURNS_NOT_SWITCH_ACCOUNT_PNL','SEQUENTIAL_NONOVERLAP_NO_RANDOM_CV','SAVED_EXPERT_WALLET_CAPITAL_PATH_PROXY','PLACEBO_REPLICATES_NOT_MORE_HISTORY','RANK_REFERENCE_NOT_DEPLOYED_STRATEGY','NATIVE_FUNDING_FILTERS_UNKNOWN','TAIL10D_EXCLUDED_FROM_LABELS_NOT_ACCOUNT_ECONOMICS'],
        elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,created_utc=datetime.now(UTC).isoformat())
    p=(ROOT/a.output).resolve();assert p.is_relative_to(ROOT/'reports')
    with p.open('x') as f:json.dump(out,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    phase.update('排名可预测性探测完成；不产生投资收益',3,3,'阶段');phase.stop.set();phase.thread.join(timeout=3)
    print(json.dumps(dict(status=out['status'],decision=out['decision'],scores=[v['metrics']['HAND_FIXED']['mean_weighted_rank'] for v in results],checks=[v['checks'] for v in results])))

if __name__=='__main__':main()
