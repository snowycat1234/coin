import json,subprocess
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
def read(p):return json.loads((ROOT/p).read_bytes())
def save(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
review='reports/FROZEN_EXPERT_MIXTURE_REVIEW_20261006_V1.json';r=read(review)
independent='reports/FROZEN_EXPERT_MIXTURE_INDEPENDENT_20261006_V1.json';audit=read(independent)
assert r['economic_accounts_referenced']==6 and r['reused_control_accounts']==4 and not r['qualified_static_research_challengers']
assert r['oracle_opportunity_persists'] and audit['maximum_target_error']<1e-12
paths=[v['path'] for v in r['producers']];producers=[read(p) for p in paths]
assert all(v['binding']['git_commit']==head for v in producers)
row=lambda family,unit:next(v for v in r['rows'] if v['strategy']==family and v['unit']==unit)
o=row('ORACLE60D','RAW_AS_PERCENT');st=row('STATIC_DIRECTION3','RAW_AS_PERCENT');eq=row('EQUAL_EXPERTS','RAW_AS_PERCENT')
next_action='真实oracle机会足够，但仍非因果/不能投资。下一有限主任务只用过去slow-trend×fast-trend×vol状态检验60日未来expert相对排名/赢家可预测性，先固定可解释状态映射，再chronological walk-forward与标签成熟，12个完整非重叠60日标签、尾部10日不充样本；固定/错位/打乱/同频随机placebo与oracle可行差距必须报告。0交易模型拟合、参数扫描或权重救配方。若不优于静态/placebo则暂停本selector配方，保留单策略与SHORT能力；reopen需新独立周期/合法多币机制。'
summary='D105把冻结expert目标放入真实单10k钱包。两资金费条件oracle相对最佳单expert增量3335.69/3386.30，比shadow诊断低27.93/28.69，机会门槛保留，但oracle未来知情始终不算候选。八expert等权弱于原仅多；固定SMA200/HOLD/CASH=.5/.25/.25降低实际波动/回撤、提高Sharpe，但净收益低于原仅多，两条件均未达替换门槛。投资NONE/CASH，原SMA200仅多风险效率参照及多空正SHORT挑战者保留。'
lines=['','## D105：冻结expert真实共享账户重放','',summary,'',
    '同BTC2022-01-01至2024-01-01、已见730日、每个反事实完整10k/caps30/60/1x。6新完整账户、4Cash/Hold完整复用；组合先合成有符号目标，再真实账户成交/资金费/钱包，不拼独立钱包收益。既有必要风险减仓与持仓清理保持。',
    '|账户 / BASE-PCT|净USDT|LONG|SHORT|价格毛PnL|费+执行|资金费|vol%|分钟DD%|Sharpe|换手|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for v in r['rows']:
    if v['unit']!='RAW_AS_PERCENT':continue
    label=v['strategy']+(' **未来知情，非候选**' if v['future_winner_used'] else '')
    values=(v['net_USDT'],v['direction']['LONG']['net_contribution'],v['direction']['SHORT']['net_contribution'],v['gross_USDT'],v['fees_USDT']+v['execution_USDT'],v['funding_USDT'],v['daily_metrics']['annual_volatility']*100,v['drawdown_percent'],v['daily_metrics']['sharpe'],v['turnover'])
    lines.append('|'+label+'|'+'|'.join(f'{x:.2f}' for x in values)+'|')
lines += ['',
    f"Oracle PCT实际净{o['net_USDT']:.2f}，2022净{o['calendar_year_contributions']['2022']['net']:.2f}（SHORT{o['calendar_year_contributions']['2022']['SHORT']:.2f}），2023净{o['calendar_year_contributions']['2023']['net']:.2f}（SHORT0）。6/7次expert切换沿已冻结诊断路径，两情景分别真实重放，不重优化成全局最优；存在未来输入，不能列入可交易leaderboard。额外shadow切换扣费在真实账本不再扣，实际成交费和执行成本一次记账。",
    f"固定三expert PCT毛价格{st['gross_USDT']:.2f}、费+执行{st['fees_USDT']+st['execution_USDT']:.2f}、资金费{st['funding_USDT']:.2f}，主要赚钱来自LONG{st['direction']['LONG']['net_contribution']:.2f}；SHORT2022 +{st['calendar_year_contributions']['2022']['SHORT']:.2f}、2023 {st['calendar_year_contributions']['2023']['SHORT']:.2f}，合计+{st['direction']['SHORT']['net_contribution']:.2f}。净{st['net_USDT']:.2f}比原LO1563.48少185.90，DD{st['drawdown_percent']:.2f}%比6.23%低、vol{st['daily_metrics']['annual_volatility']*100:.2f}%比6.68%低；不是risk-matched超越，不事后加杠杆缩放。",
    f"等权8expert PCT净{eq['net_USDT']:.2f}、SHORT{eq['direction']['SHORT']['net_contribution']:.2f}、Sharpe{eq['daily_metrics']['sharpe']:.3f}；机械保留所有expert未形成净分散优势。它不否定其他窗口/币种条件优势，暂停该固定等权配方作为主力；reopen需真正互补收益来源/独立证据，而不是已见窗口删输家调权重。",
    '独立标量逐730日重构六账户的原expert目标和组合权重/赢家边界；实际费用交易表逐项求和，最大目标误差2.78e-17；原有Decimal一分钟资金/NAV/多空归因继续通过。资源/时刻/源SHA见module close。所有新帐户实际平仓费用支付，未删除残仓。',
    next_action,'',
    'BinanceUSD-M价格配Bybit用户费用仍为代理；资金费单位、历史数量与MMR假设未原生认证。已看开发不改名unseen；未启封locked。测试、oracle高Sharpe与两年外推均不证明长期APR或真钱资格。',
    f'结果 `{review}`，独立核对 `{independent}`。复现：progress/bounded下 `run_cta_leaderboard.py --protocol protocols/FROZEN_EXPERT_MIXTURE_ORACLE_20261006_V1.json` 或 `FROZEN_EXPERT_MIXTURE_STATIC_20261006_V1.json`，各给新的STATE `--run-dir`、新的reports/fast_research `--output`；`review_expert_mixture.py --producer <oracle生产报告> --producer <静态生产报告> --output <新文件>`。','']
with (ROOT/'docs/SHORT_SELECTION.md').open('a') as f:f.write('\n'.join(lines))
leader=['','## D105：固定软组合的真实账户对照','',
    '与D100共同BTC730日/资本/成本/风险口径；参数未优化。未来知情ORACLE60D不纳入可交易排行榜；只保留 [机制证据](SHORT_SELECTION.md)。',
    '', '|固定方案 / BASE-PCT|净USDT|SHORT|vol%|分钟DD%|Sharpe|费+执行|','|---|---:|---:|---:|---:|---:|---:|']
baseline=next(v for v in r['baseline_rows'] if v['mode']=='LONG_ONLY' and v['unit']=='RAW_AS_PERCENT')
for v,label in [(baseline,'原SMA200仅多'),(st,'固定三expert软组合'),(eq,'八expert等权')]:
    leader.append('|'+label+'|'+'|'.join(f'{x:.2f}' for x in (v['net_USDT'],v['direction']['SHORT']['net_contribution'],v['daily_metrics']['annual_volatility']*100,v['drawdown_percent'],v['daily_metrics']['sharpe'],v['fees_USDT']+v['execution_USDT']))+'|')
leader+=['',summary+' RAW完整结果与瞬时风险漂移/集中度见工件，equal caps不代表同风险。','']
with (ROOT/'docs/CTA_LEADERBOARD.md').open('a') as f:f.write('\n'.join(leader))
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D105结果与自主决定\n\n'+summary+' STATIC_DIRECTION3保留为低风险控制，不替换主参照、不扫权重；EQUAL_EXPERTS暂停主力，reopen需独立互补收益源。'+next_action+' 工件 '+review+' SHA '+sha(ROOT/review)+'。\n')
with (ROOT/'docs/OPEN_SOURCE_REGISTRY.md').open('a') as f:f.write('\n- D105：无新第三方项目或kernel。既有pinned公开SMA/Donchian参数不改，脚本frozen_expert_mixture.py为薄目标组合adapter，NumPy既有einsum/Polars既有存储接口沿登记版本，OWN_MODIFICATION记录固定1/8与.5/.25/.25；账户和ExecutionContractV2原路径复用。ORACLE60D明确未来知情研究对照，static不是训练模型或原论文组合复现。无新库/行情/GPU。\n')
old=(ROOT/'docs/RESEARCH_STATUS.md').read_text();boundary=old[old.index('## 数据、账户与资源边界'):]
index=boundary.index('本轮10新完整账户')
elapsed=','.join(format(v['elapsed_seconds'],'.1f') for v in producers)
boundary=boundary[:index]+f"本轮6新730日组合账户+4完整控制复用；最多2并行，各2线程/1.2GB守卫。实际任务{elapsed}秒，RSS峰值{max(v['peak_RSS_bytes'] for v in producers)/1e6:.1f}MB、共享采样峰值{max(v['shared_RAM_sampled_peak_bytes'] for v in producers)/1e9:.2f}GB，新增目录合计{sum(v['owned_bytes'] for v in producers)/1e6:.1f}MB。实际区间并集/磁盘扫描时刻见本轮close，不把旧扫描当当前。\n\n## 运维与证据\n\n8765沿用；原public/micro公开采集存活核对另报，断档不拼72h资格。完整目标/权重/费用及Decimal资金NAV通过，真实平仓，不删残仓。未来知情oracle不进入候选；状态可预测性/placebo/可行adaptive账户NOT_RUN。无真钱/密钥/发单/付费/GPU/封存正文。\n"
(ROOT/'docs/RESEARCH_STATUS.md').write_text('# COIN 当前研究状态\n\n投资资格 **NONE/CASH**；长期净APR **NOT_EVALUABLE**。\n\n## 最新实际经济结果\n\n'+summary+'\n\nPCT实际oracle净5799.64（比最佳单expert2413.34增3386.30），DD6.62%、vol10.37%；未来知情、绝不作为可行策略或投资证据。真实账户净收益比shadow诊断低28.69。固定三expert净1377.58、SHORT189.50、Sharpe1.217、DD5.11%、vol5.42%；原LO净1563.48、Sharpe1.121、DD6.23%、vol6.68%。静态分散改善风险，但不是净收益全面优势；相同caps未等风险。\n\n## 当前研究问题与下一项\n\n'+next_action+'\n\n保持SHORT主线，暂停已测D101硬过滤、D102无重入CE、八expert机械等权以及ML/4h网格；不是永久删除能力。三expert静态配方保留低风险控制，不凭发版本替换主力；没有合格投资候选。D103公开50/200原family与所有专家参数保持冻结，未来数据启封未授权。\n\n[实际经济榜单](CTA_LEADERBOARD.md)；[完整结果与可复现命令](SHORT_SELECTION.md)。\n\n'+boundary)
selected=read('.cache/d105_selected_snapshot.json')
for p in ('docs/RESEARCH_STATUS.md','docs/SHORT_SELECTION.md','docs/CTA_LEADERBOARD.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md'):
    if p not in selected:selected.append(p)
c=dict(parent_commit=head,module='D105_FROZEN_EXPERT_SHARED_ACCOUNT_REPLAY',family='FROZEN_EXPERT_MIXTURE',recipe=producers[0]['protocol']['rules'],
    references={review:r['status'],independent:audit['status']},additional_tasks=[dict(id='7f0db7e6d6e64736a8998cfd9762a70a',expected_exit_code=0)],
    source_paths=[p for p in selected if p.endswith('.py')],decision='ORACLE_OPPORTUNITY_PERSISTS_NO_STATIC_REPLACEMENT_PROCEED_REGIME_PREDICTABILITY',next_action=next_action,primary_reference=review,
    economic_producers=paths,complete_accounts=6,runtime_directories=[v['run_dir'] for v in producers],
    closed='reports/FROZEN_EXPERT_MIXTURE_MODULE_CLOSED_20261006_V1.json',binding='reports/GITHUB_FROZEN_EXPERT_MIXTURE_SOURCE_BINDING_20261006_V1.json',
    prior_binding='reports/GITHUB_FROZEN_EXPERT_LIBRARY_SOURCE_BINDING_20261006_V2.json',selected_paths=selected,stage_script='.cache/stage_selected_expert_mixture.ps1')
save('protocols/FROZEN_EXPERT_MIXTURE_CLOSE_20261006_V1.json',c)
print(json.dumps(dict(status='ACTUAL_SHARED_MIXTURE_RESULTS_AND_DECISION_READY',summary=summary,next_action=next_action)))
