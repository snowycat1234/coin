import json,os,subprocess,sys,importlib.metadata
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
from scripts.investment.chandelier_short_levels import runtime
runtime();sys.path.append('/home/xflops/coin-state/selector-support-v1')
parent=json.loads((ROOT/'protocols/FROZEN_EXPERT_MIXTURE_ORACLE_20261006_V1.json').read_bytes())
features=['distance20','distance50','distance100','distance200','slope50','slope100','slope200',
    'momentum5','momentum20','momentum60','momentum120','momentum200','rv10','rv30','rv60','rv200',
    'drawdown20','drawdown60','drawdown200','vol_of_vol','rebound_velocity','volume_momentum','volume_zscore','atr_normalized','rsi','donchian_position']
source=['scripts/research/'+n for n in ('audit_selector_splits.py','selector_data.py','selector_jobs.py','selector_report.py','run_selector_research.py','selector.sh')]
source+=['tests/test_selector_research.py','scripts/investment/chandelier_short_levels.py','scripts/investment/regime_ranking_screen.py','scripts/investment/frozen_expert_mixture.py','scripts/investment/oracle_expert_opportunity.py',
    'scripts/investment/cta_cycle_window.py','scripts/investment/perpetual_directional.py','scripts/investment/audit_shared_direction.py','scripts/investment/bybit_cost_inputs.py','scripts/investment/perpetual_closing_exempt_account.py','src/quant/perpetual_account.py',
    'scripts/bounded.sh','scripts/with_task_progress.sh','scripts/env.sh','environments/v8/uv.lock']
versions={p:importlib.metadata.version(p) for p in ('numpy','polars','scipy','scikit-learn','xgboost-cpu','PyYAML','joblib','matplotlib','psutil','pandas-ta-classic')}
config=dict(version='selector_v1',created_utc=datetime.now(UTC).isoformat(),run_dir=str(STATE/'selector-v1-20261006'),
    git_executable='/mnt/c/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe',
    data=dict(manifest=parent['data_manifest'],oracle_library=parent['expert_mixture'],locked_sha256=parent['locked_sha256'],
        split_audit=dict(path='reports/DATA_SPLIT_AUDIT.json',sha256=sha(ROOT/'reports/DATA_SPLIT_AUDIT.json')),
        d106_reference=dict(path='reports/REGIME_RANKING_SCREEN_20261006_V1.json',sha256=sha(ROOT/'reports/REGIME_RANKING_SCREEN_20261006_V1.json')),
        training_scope=['2022-01-01','2024-01-01'],role='SEEN_TRAIN_DEVELOPMENT_AND_INTERNAL_CHRONOLOGICAL_VALIDATION_NOT_OOS',FINAL_LOCKED_TEST='NOT_AUTHORIZED_NOT_READ'),
    experts=['SMA200_SIGNED','HOLD','CASH'],expert_parameters_changed=False,
    features=features,feature_availability='EXCLUSIVE_COMPLETED_UTC_DAY_CLOSE; ALL_FEATURE_INPUTS<=t; sourcepublication not nativecertified',
    feature_parameters=dict(slope_days=5,ATR=14,RSI=14,Donchian=20,volume_zscore=30,vol_of_vol_std_of_rv30_days=20,rebound_velocity='5d_return_minus_preceding5d_return',cross_sectional='OMITTED_INCOMPLETE_COMMON2022ETH_MARK',funding_basis='OMITTED_UNKNOWN_UNIT_PUBLICATION'),
    support_runtime=dict(path='reports/SELECTOR_SUPPORT_RUNTIME_20261006_V1.json',sha256=sha(ROOT/'reports/SELECTOR_SUPPORT_RUNTIME_20261006_V1.json')),indicator_runtime=dict(path='reports/SHORT_CHANDELIER_PROBE_20261006_V1.json',sha256=sha(ROOT/'reports/SHORT_CHANDELIER_PROBE_20261006_V1.json')),
    horizons=[30,60,90],units=['RAW_AS_FRACTION','RAW_AS_PERCENT'],
    labels='3expert_Hday_net_marked_NAV_relative_return_minus_cross_expert_mean; fees/execution/funding retained; immature tail NaN never zero; source standalonecapitalpath proxy, not switchwalletoutcome',
    folds=[['2022-10-01','2023-01-01'],['2023-01-01','2023-04-01'],['2023-04-01','2023-07-01'],['2023-07-01','2023-10-01'],['2023-10-01','2024-01-01']],
    validation_start='2022-10-01',validation_end='2024-01-01',min_train_rows=90,embargo='label_end<=validation_start-Hdays; overlapping labels purged plus H extra embargo; scaler/model fit only train',
    models=dict(LINEAR=dict(alpha=30.),TREE=dict(n_estimators=80,max_depth=2,learning_rate=.05,min_child_weight=30.,reg_lambda=20.,subsample=1.,colsample_bytree=1.,objective='reg:squarederror',tree_method='hist',device='cpu',n_jobs=2,random_state=10620261006)),
    tree_scalar_heads=3,linear_multioutput_fits=1,mlp_min_train_rows=1000,MLP_policy='SKIP_THIS730DAY_INPUT; require separately budgeted larger future dataset, not inflated overlapping rows',
    softmax_temperature=.02,max_daily_L1_change=.1,weights='nonnegative simplex; startfromCASH; smooth causaldesiredweight via convex L1 capped step; no fitted temperature or turnover budget',
    seed=10720261006,placebo=dict(shuffle_each=16,random=32,total_paths=64,per_unit_conditions=2,
        label_shuffle='only matured purged traininglabels permuted; validation clocks untouched',feature_shuffle='only trainingfeature rows permuted; validationfeaturetime unchanged',
        random_protocol='condition on feasible actualweight-change timing/L1 magnitude; random3expert destinations; diagnostic only notdeployable; seeds fixed no seedselection'),
    selection='one champion byminimum across2fundingconditions common-mature-date chronologicalutilityrank; not finalwalletPnL, nottrainingR2; common date cutoff datasetend-maxH',
    comparisons=['SMA200_SIGNED','HOLD','CASH','STATIC_SMA0.5_HOLD0.25_CASH0.25','EXPANDING_MATURE_PAST_WINNER','D106_FIXED_MAP_ORIGINAL_FROZEN_PATH','LABEL_SHUFFLE','FEATURE_SHUFFLE','RANDOM_MATCHED_WEIGHT_FREQUENCY','ORACLE30_60_90_FUTURE_INFORMED'],
    success=dict(capture_min=.15,max_realized_vol=.11,DD_floor=.05,DD_factor=1.10,
        rule='BOTHfundingconditions: completeallnecessaryaccounts; net>beststatic; >95th ofEACHlabelshuffle/featureshuffle/random; positive netincrement2022Q4 AND2023; capture>=.15 matchingH oracle; realizedriskwithin fixedlimits. Passed seen screen only, notstablealpha/investment. Failure no complexityincrease.'),
    risk=dict(capital_USDT=10000,abs_asset_cap=.3,gross_cap=.6,isolated_leverage=1,no_auto_topup=True,cost='Bybitcurrent5.5bpTAKERside +4halfspread+4slippage; BinanceUSD-Mpriceproxy; allactualfunding2conditionalunits; nativequantity/MMRunknown'),
    workers=2,threads_each=2,source_hashes={p:sha(ROOT/p) for p in source},runtime_versions=versions,
    budget=dict(wall_seconds=28800,worker_RSS_bytes=1500000000,account_wall_seconds=1200,disk_reserved_bytes=12000000000,max_job_attempts=2,
        primary_CV_groups=60,shuffle_CV_groups=320,max_base_scalar_fits=1080,max_scalar_fit_attempts_with_one_retry=2160,max_base_accounts=158,max_account_attempts=316,total_base_jobs=547,
        shared_RAM_bytes=8000000000,D_total_bytes=150000000000,swap=0,GPU=0,LLM_API_calls=0))
(ROOT/'configs').mkdir(exist_ok=True)
with (ROOT/'configs/selector_v1.yaml').open('x') as f:json.dump(config,f,indent=2,ensure_ascii=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D108 ML selector运行前授权与冻结\n\n'+config['created_utc']+'：用户明确允许有限ML，覆盖D106未开放classifier的暂缓。只用SMA200/HOLD/CASH，参数不变。所有2157历史metadata/manifest/选择记录审计已生成DATA_SPLIT_AUDIT；2022–23已见，内部时间验证不叫OOS，final封存正文不读。26past-only特征，H30/60/90固定，Ridgealpha30与单一小XGB80depth2，MLP因样本不足不跑。5expandingfolds，purge后H额外embargo，初折H90仅94训练日，重叠日标签非独立样本。60主CV组+320shuffleCV组，最多1080底层fit（故障保留最多1retry，总预算2160），64placebo路径，两资金费条件，158完整共享钱包对照；0Optuna/密扫/调温度/改成本。成功门槛'+config['success']['rule']+' 2022shortcapture只评价Q4的92日，不冒称全年。2worker各2线程/1.5GB，8小时、12GB新增空间上界、D150GB/RAM8GB/swap0/GPU0。正式fit之前必须commit这套config/source/split，runner逐字核Git；后台Python自行完成，全程0LLM/API。\n')
with (ROOT/'docs/OPEN_SOURCE_REGISTRY.md').open('a') as f:f.write('\n- D108：复用scikit-learn '+versions['scikit-learn']+' BSD-3-Clause https://github.com/scikit-learn/scikit-learn （StandardScaler/Ridge/MultiOutputRegressor）；XGBoost '+versions['xgboost-cpu']+' Apache-2.0 https://github.com/dmlc/xgboost （CPUhist fixed3utilityheads）；pandas-ta-classic '+versions['pandas-ta-classic']+' MIT （ATR/RSI/Donchian原库，逐文件SHA核旧安装）；SciPy '+versions['scipy']+' BSD-3-Clause （softmax/rankdata）；PyYAML '+versions['PyYAML']+' MIT、joblib '+versions['joblib']+' BSD-3-Clause、matplotlib '+versions['matplotlib']+' PSF兼容license、psutil '+versions['psutil']+' BSD-3-Clause，训练库沿现有环境与uv.lock；配置/进度/绘图依赖独立selector-support-v1安装，第三方库无本地修改。新增仅薄feature/label/job/报告adapter与本地DAG；金融kernel不重写。详见configs/selector_v1.yaml逐版本及sourceSHA。\n')
print(json.dumps(dict(status='SELECTOR_FULL_DAG_PROTOCOL_FROZEN_NO_MODEL_FITS',task_id=os.environ['COIN_TASK_ID'],head=head,features=len(features),versions=versions)))
