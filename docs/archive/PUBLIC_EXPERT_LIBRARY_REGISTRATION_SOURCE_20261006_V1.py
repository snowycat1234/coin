import json,subprocess,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
def read(p):return json.loads((ROOT/p).read_bytes())
def save(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
base=read('protocols/SMA200_SHORT50_SHORT_ONLY_20261006_V1.json');base.pop('unchanged_long_controls')
prior=read(base['reused_cycle_controls']['path'])
for p in base['recipe_source_changes']:base['recipe_source_changes'][p]['current']=sha(ROOT/p)
test='reports/PUBLIC_SMA_FULL_HOOK_TESTS_20261006_V1.xml'
base['controls_reuse_regression']=dict(path=test,sha256=sha(ROOT/test),source_sha256=sha(ROOT/'tests/test_reuse_cycle_controls.py'),tests=5)
base.update(parent_commit=head,created_utc=datetime.now(UTC).isoformat(),
    source_scope='PINNED_UNMODIFIED_JESSE50_200_ENTRY_AND_EXIT_HOOKS_IN_EXISTING_PUBLIC_SMA_PERPETUAL; COIN_SIZING_AND_EXECUTION_ADAPTER_NOT_NATIVE_JESSE',
    budgets_estimation='TEN_NEW730D_WALLETS: PUBLIC50_200_SIX_AND_TWO_OTHER_FROZEN_EXPERTS_FOUR; TWO_CONCURRENT_PROCESSES_MAX; FOUR_WHOLE_CASH_HOLD_REUSED;0FITS0PARAMETER_SEARCH',
    stopping='TEN_FIXED_CASES_OR_EXPLICIT_HALT; ONE60DAY_ORACLE_DIAGNOSTIC; NO_RESCUE_PERIOD_SEARCH_NEW_DATA_OR_TRAINING')
for p in ('scripts/investment/run_cta_leaderboard.py','scripts/investment/reuse_cycle_controls.py','scripts/investment/audit_cta_classics.py'):
    base['frozen_source_hashes'][p]=sha(ROOT/p)
base['public_hook_regression']=dict(path=test,sha256=sha(ROOT/test),source_sha256=sha(ROOT/'tests/test_public_sma_perpetual.py'),tests=5)
for p in ('scripts/investment/public_sma_daily.py','scripts/investment/public_sma_perpetual.py','tests/test_public_sma_perpetual.py',
          'third_party/jesse_example_smacrossover/smacrossover_original.py','third_party/jesse_example_smacrossover/LICENSE'):
    base['frozen_source_hashes'][p]=sha(ROOT/p)
base['rules']['PUBLIC_SMA50_200']='PINNED_SHOULD_LONG_FAST50_GT_SLOW200_SHOULD_SHORT_LT; UPDATE_POSITION_OPPOSITE_ORDER_CLOSE; EQUALITY_HOLD; NO_SAME_CLOSE_REENTRY; FRESH_FLAT; INVERSE_VOL30_AND_EXISTING_SIGNED_COV'
base.update(experiment_id='D103_PUBLIC_SMA50_200_FROZEN_EXPERT',families=['PUBLIC_SMA50_200'],
    question='Complete frozen public50/200 family, not another SMA200 exit filter: sameBTC730d account/cost/risk, long-only short-only long-short. Does it retain bear short gains with less2023 short loss and improve the risk-aware reference?',
    adoption='Both units: complete730d; LSnet>ownLO and>D100LS; SHORTwhole>0 and2022>0;2023SHORTloss reduced; LSminuteDD<=D100LS; LSSharpe>=D100LS. Different actual risk reported, no equal-risk/native/investment claim. Failure retains strongest existing reference. These are fixed family comparisons, not selector tuning.')
for name,modes in [('DIRECTIONS',['LONG_ONLY','SHORT_ONLY']),('LONG_SHORT',['LONG_SHORT'])]:
    save('protocols/PUBLIC_SMA50_200_'+name+'_20261006_V1.json',dict(base,account_modes=modes))
experts=dict(base,experiment_id='D104_FROZEN_EXPERT_LIBRARY_COMPLETE',families=['DONCHIAN20_10','DC_TWO_SPEED'],account_modes=['LONG_SHORT'],
    source_scope='UNCHANGED_EXISTING_CTA_PRIOR_CHANNEL_EXPERTS; PINNED_PUBLIC_DONCHIAN_KERNEL; FIXED20_10_AND55_20_NO_PERIOD_SEARCH',
    question='Fill missing same-window frozen expert accounts for a cost-aware oracle opportunity diagnostic. Do not tune experts or promote from oracle.',
    adoption='No single-family replacement from this completion step. Preserve all negative accounts; selector advancement depends on the preregistered cost-aware60day opportunity ceiling, not ex-post best expert.')
save('protocols/FROZEN_EXPERT_LIBRARY_COMPLETE_20261006_V1.json',experts)
oracle=dict(experiment_id='D104_ORACLE_OPPORTUNITY_60D',parent_commit=head,created_utc=base['created_utc'],
    experts=['CASH','HOLD','SMA200_SIGNED','DONCHIAN20_10','DC_TWO_SPEED','DC_CONFIRMED_SHORT','PUBLIC_SMA50_200'],
    decision_horizons_days=[60],data_role=base['data_role'],economics_start=base['economics_start'],economics_end_exclusive=base['economics_end_exclusive'],
    assumptions='Saved full-wallet daily NAV returns rebased to one10k diagnostic wealth, not added independent wallets; net expert returns retain actual within-expert costs. Boundary switching turnover=sum(abs(new_target-old_target));13.5bp side surcharge on the diagnostic NAV. This is an approximate informed-selection opportunity bound, not an executable backtest or mathematically certified global maximum; actual single-account replay required before any feasible selector comparison.',
    switching_boundary='Every60calendar days starting2022-01-01; final10days retained; terminal costs already in expert returns; keep CASH/HOLD; both funding unit conditions separately, never choose profitable interpretation.',
    opportunity_gate='Both funding conditions: switching-cost-aware informed wealth minus best full-window single expert >=500USDT per10k, with positive LONG and SHORT contribution in selected segments. Only permits predictability screening, not candidate promotion. If fail pause selector; no horizon scan.',
    next_if_pass='Predeclare one slow-trend x fast-trend x volatility state map and chronological non-overlapping60d winner/ranking predictability, static/equal-weight and frequency-matched placebo controls. No training or PnL tuning in this stage.',
    resource_budget=dict(wall_seconds=120,RSS_bytes=700000000,new_wallets=0,models_fit=0,configurations=1,GPU=0),investment_status='NONE_CASH',locked_consumed=False)
save('protocols/FROZEN_EXPERT_ORACLE_20261006_V1.json',oracle)
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:
    f.write('\n## D103/D104运行前 '+base['created_utc']+'\n\n用户将regime-aware冻结expert组合提升主候选；SHORT优先级保持，不继续exit/filter网格。完成公开50/200原hook6账户及DC20/10、双通道2family各2资金费账户，合计10新钱包，顺序两批、最多2并行各2线程/1.2GB/1800秒/600MB，0训练/下载/参数扫描。原4Cash/Hold控制严格字节绑定复用，不相加资本。'+base['adoption']+' 下一阶段只冻结60日oracle诊断：'+oracle['opportunity_gate']+' 归一化单10k财富诊断保留各expert已付成本并另扣边界换仓估计；不是真实可交易oracle，也不能据此宣称ensemble alpha。通过后需同一共享账户真实重放与过去特征可预测性、placebo对照；只读诊断120秒/700MB。全部已见开发、原风险/资源/封存/资金边界保持。\n')
print(json.dumps(dict(status='PUBLIC_EXPERT_LIBRARY_AND_ONE_HORIZON_ORACLE_PREREGISTERED',task_id=os.environ['COIN_TASK_ID'],head=head)))
