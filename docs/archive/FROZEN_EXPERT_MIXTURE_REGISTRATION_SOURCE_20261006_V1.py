import json,os,subprocess
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
def read(p):return json.loads((ROOT/p).read_bytes())
def save(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
base=read('protocols/PUBLIC_SMA50_200_LONG_SHORT_20261006_V1.json');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
ref='reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V2.json';proof='reports/FROZEN_EXPERT_ORACLE_INDEPENDENT_20261006_V1.json'
test='reports/FROZEN_EXPERT_MIXTURE_TESTS_20261006_V1.xml'
base.update(experiment_id='D105_SHARED_ACCOUNT_FROZEN_EXPERT_REPLAY',parent_commit=head,created_utc=datetime.now(UTC).isoformat(),
    question='Does the fixed60day informed path preserve its opportunity in actual shared-wallet execution? Compare with equal8 and one fixed soft direction allocation, sameBTC730d capital/cost/risk. No learning, no strategy parameter or winner-path retuning.',
    expert_mixture=dict(path=ref,sha256=sha(ROOT/ref),independent_path=proof,independent_sha256=sha(ROOT/proof)),
    mixture_regression=dict(path=test,sha256=sha(ROOT/test),source_sha256=sha(ROOT/'tests/test_frozen_expert_mixture.py'),tests=6),
    controls_reuse_regression=dict(path=test,sha256=sha(ROOT/test),source_sha256=sha(ROOT/'tests/test_reuse_cycle_controls.py'),tests=6),
    source_scope='FROZEN_TARGET_INTENTS_FROM_SAME730D_EXPERT_LIBRARY; REAL_ONE_SHARED_ACCOUNT; NOT_REBASED_EXPERT_RETURN_STITCH',
    source_expert_parameters_changed=False,account_modes=['LONG_SHORT'],
    budgets_estimation='SIX_NEW_COMPLETE_WALLETS: ORACLE2_PLUS_STATIC4; TWO_CONCURRENT_TASKS_MAX2THREADS_EACH_1.2GB_1800SECONDS_600MB; FOUR_COMPLETE_CASH_HOLD_CONTROLS_REUSED;0FITS0GRID0NEW_DATA',
    stopping='SIX_FIXED_CASES_OR_DECLARED_ACCOUNT_HALT; NO_OBSERVED_RESULT_WEIGHT_PERIOD_OR_PATH_CHANGE; REAL_FILL_COST_ONCE_NOT_SHADOW_SURCHARGE',
    adoption='Oracle remains NONCAUSAL and never candidate. Opportunity persists only if both units actual oracle net minus fixed best single>=500USDT. Static ensemble research challenger only if both units net>=D100 ownLO, Sharpe>=D100 LO and minuteDD<=D100 LO; report actual risk and price/funding/cost/concentration, no risk-matched or investment claim. Retain all negative results and do not rescue weights.',
    comparison_reference=dict(path='reports/SMA200_FIXED_CYCLE_REVIEW_20261006_V1.json',sha256=sha(ROOT/'reports/SMA200_FIXED_CYCLE_REVIEW_20261006_V1.json')))
base['rules'].update(ORACLE60D='D104_COST_AWARE_ORACLE_PATH_FIXED_PER_UNIT; FUTURE_WINNER_NONCAUSAL_DIAGNOSTIC_ONLY; DAILY_FROZEN_EXPERT_TARGETS_TO_ONE_WALLET',
    EQUAL_EXPERTS='ALL8_REGISTERED_EXPERT_TARGETS_WEIGHT1/8_INCLUDING_CASH_AND_HOLD; NO_REDISTRIBUTION_OR_FUTURE_WINNER',
    STATIC_DIRECTION3='FIXED_SMA200_WEIGHT.5_HOLD.25_CASH.25; POST_D104_DEVELOPMENT_PROBE; ZERO_OPTIMIZATION; NO_REGIME_FEATURES_OR_FUTURE_WINNER',
    mixture_economics='EXPERT_TARGET_INTENTS_COMBINE_BEFORE_EXECUTION; ONE10K_WALLET; ORIGINAL_SIGNED_COV_CAPS_MINUTE_FILL_FUNDING_AND_RISK_REDUCTIONS; NO_ADDITIONAL_SHADOW_SWITCH_SURCHARGE')
for p in ('scripts/investment/run_cta_leaderboard.py','scripts/investment/reuse_cycle_controls.py','scripts/investment/frozen_expert_mixture.py','scripts/investment/oracle_expert_opportunity.py','tests/test_frozen_expert_mixture.py'):
    base['frozen_source_hashes'][p]=sha(ROOT/p)
for name,families in [('ORACLE',['ORACLE60D']),('STATIC',['EQUAL_EXPERTS','STATIC_DIRECTION3'])]:
    save('protocols/FROZEN_EXPERT_MIXTURE_'+name+'_20261006_V1.json',dict(base,families=families))
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D105运行前 '+base['created_utc']+'\n\n'+base['question']+' 只冻结3配方：ORACLE60D沿D104两单位路径不改（未来知情、不能投资）；全部8expert等权；SMA200/HOLD/CASH=.5/.25/.25作为事后D104提出但运行前固定的开发静态参照，不是优化权重。无独立/unseen声明。6新730日实际账户、最多2并行各2线程/1.2GB/1800s/600MB，共享8GB、150GB，0训练/搜参/新数据。实际成交、资金、费用一次记账，不沿用诊断净收益或二扣shadow切换费用。'+base['adoption']+' 必要减仓、标的顺序、完整资本和原封存边界保持。\n')
print(json.dumps(dict(status='SIX_FIXED_SHARED_WALLET_REPLAYS_PREREGISTERED',task_id=os.environ['COIN_TASK_ID'],head=head)))
