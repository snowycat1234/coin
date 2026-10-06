import json,subprocess,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
base=json.loads((ROOT/'protocols/FROZEN_EXPERT_MIXTURE_ORACLE_20261006_V1.json').read_bytes())
test='reports/REGIME_RANKING_SCREEN_TESTS_20261006_V1.xml'
spec=dict(experiment_id='D106_FIXED_REGIME_RANKING_PROBE',parent_commit=head,created_utc=datetime.now(UTC).isoformat(),
    question='Is one interpretable past slow/fast/vol soft state map informative about60day frozen expert net relative ranks beyond static/lag/shuffle/samefrequency random? No trading model training or PnL optimization.',
    data_manifest=base['data_manifest'],locked_sha256=base['locked_sha256'],data_role='ONE_SEEN_BTC2022_2023_DEVELOPMENT_MECHANISM_NOT_UNSEEN',
    oracle_reference=base['expert_mixture'],horizon_days=60,min_mature_labels=4,placebo_replicates=32,seed=10620261006,
    features=dict(slow='SIGN_COMPLETED_PRICE_MINUS_LAST200DAILY_MEAN',fast='SIGN_COMPLETED_PRICE_MINUS_LAST50DAILY_MEAN',
        high_vol='PAST30DAILY_RETURN_SAMPLE_STD_GT_PAST200_SAMPLE_STD;DDOF1;FIXED_RATIO1',
        availability='ALL201COMPLETED_DAILY_ROWS_AVAILABLE_AT_DECISION; NO_FUNDING_BASIS_FEATURES_WHILE_UNKNOWN'),
    hand_map=dict(both_negative='SMA200.75_CASH.25',slow_negative_fast_positive='HOLD.5_CASH.5',both_positive='SMA200.5_HOLD.5',slow_positive_fast_negative='SMA200.25_CASH.75',equal='CASH1',
        high_vol='HALVE_ALL_NONCASH_WEIGHTS_PUT_REST_CASH',update='AT_NONOVERLAP60DAY_BOUNDARIES; START_FROM_CASH;MAX_L1_CHANGE.5_VIA_CONVEX_STEP;NO_PARAMETER_FITTING'),
    labels='EXPERT_NEXT60D_MARKED_NAV_RATIO_MINUS1_FROM_ACTUAL_FULL730D_WALLET; NET_WITH_FEES_EXECUTION_FUNDING; RELATIVE_ORDINAL_RANK_AVERAGE_TIES_OFFICIAL_SCIPY; [t,t+60d), maturity at t+60d; no tail10d label, no shortened label',
    evaluation='12fullhorizons; first4available historical labels then8chronological decisions; onlylabels ending<=decision in expanding past-rank reference. Fixed hand map has0fit. No randomCV; adjacentnonoverlap endpoints causally closed.',
    controls=['STATIC_DIRECTION3_FIXED_0.5_0.25_0.25','EQUAL8','SMA200_SIGNED_FIXED_PRIOR_RESEARCH_REFERENCE','EXPANDING_MATURE_PAST_MEAN_EXPERT_RANK','LAG60DAY_STATE_FEATURES','SHUFFLE_REGIME_FEATURE_ROWS32_FIXED_SEED','RANDOM_DESTINATIONS32_SAME_OBSERVED_WEIGHTCHANGE_SCHEDULE_AND_L1_MAGNITUDES','ORACLE_RANK_CEILING1'],
    placebo_scope='Shuffle and conditional matched random are explicitly diagnostic/nondeployable controls. All32realizations reported, no winning seed selection, no extra history claimed.',
    adoption='Only retain this fixed-map mechanism probe if BOTH units weightedrank>=strongeststatic/past reference+.05, above shuffle/random95th and lag, positiveincrement inbothdecisionyears with>=3evalfolds each. EvenPASS does not permit trading classifier or investment: only8oldcycle labels, independent ranking evidence still needed. FAIL pauses this map, no same-window threshold/weight/horizon rescue. SHORT capability and otherregime hypotheses remain.',
    budgets=dict(hand_maps=1,threshold_or_horizon_grid=0,placebo_paths=64,unit_conditions=2,score_evaluations=140,statistical_past_rank_updates=16,new_economic_accounts=0,trading_models_fit=0),
    budget=dict(wall_seconds=120,RSS_bytes=700000000,GPU=0,new_market_bytes=0),
    source_hashes={p:sha(ROOT/p) for p in ('scripts/investment/regime_ranking_screen.py','tests/test_regime_ranking_screen.py','scripts/investment/cta_cycle_window.py','scripts/investment/reuse_cycle_controls.py')},
    tests=dict(path=test,sha256=sha(ROOT/test),count=2),investment_candidate='NONE_CASH')
with (ROOT/'protocols/REGIME_RANKING_SCREEN_20261006_V1.json').open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False);f.write('\n')
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D106运行前 '+spec['created_utc']+'\n\n'+spec['question']+' 固定特征price/SMA200、price/SMA50符号及vol30>vol200(sampleddof1)，映射bothdown=.75SMA+.25CASH；down/rebound=.5HOLD+.5CASH；bothup=.5SMA+.5HOLD；up/pullback=.25SMA+.75CASH；equalCash；highvol将非现金减半。60日权重更新，从CASH起每次L1≤.5，不扫描。只用12完整非重叠标签，前4成熟后评价8，尾部10日不充标签。官方SciPy rankdata；先评价净relative排名，不生成收益/Sharpe/APR。过去均值排名仅统计对照、16更新，0交易模型拟合；64固定seed placebo路径×2单位及静态/错位对照全部保留。'+spec['adoption']+' 120s/700MB/0GPU/0新账户/0行情。\n')
print(json.dumps(dict(status='ONE_FIXED_MAP_NONOVERLAP_RANKING_SCREEN_PREREGISTERED',task_id=os.environ['COIN_TASK_ID'],head=head)))
