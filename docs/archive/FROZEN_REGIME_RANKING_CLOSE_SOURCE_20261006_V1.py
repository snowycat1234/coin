import json,subprocess
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
def read(p):return json.loads((ROOT/p).read_bytes())
def save(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
name='reports/REGIME_RANKING_SCREEN_20261006_V1.json';r=read(name)
audit_name='reports/REGIME_RANKING_SCREEN_INDEPENDENT_20261006_V1.json';audit=read(audit_name)
assert r['evaluated_nonoverlap_horizons']==8 and r['all_full_horizons']==12 and r['new_economic_accounts']==r['trading_models_fit']==0
assert r['protocol']['parent_commit']==head and r['source_sha256']==sha(ROOT/'scripts/investment/regime_ranking_screen.py')
assert audit['input']['sha256']==sha(ROOT/name) and audit['maximum_weight_error']<1e-12 and audit['maximum_label_error']<1e-12
assert r['decision']=='PAUSE_THIS_FIXED_STATE_MAP_NO_RANKING_EVIDENCE_RETAIN_STRONG_SINGLE'
next_action='不再在BTC同窗口改状态/阈值/权重，也不训练交易classifier。下一主任务先只读核现有授权历史manifest、完整专家账本及选择影响记录，明确可增加哪些合法完整周期或多币横截面标签；只在授权非locked范围补足有效样本，冻结专家原样做跨窗口条件优势迁移核对，已看历史仍标开发，不冒称unseen。当前映射reopen需多个周期的稳定相对排名信息或新增可解释past-only信息；仅8标签不足升级学习控制器。既有资金费单位/数量/MMR不确定继续限制投资结论。'
summary='D106单一slow×fast×vol固定软映射未通过事前排名门槛：RAW/PCT平均加权排名0.67049/0.69400，静态三expert0.63839/0.66518，最佳单expert与只用成熟过去排名均0.64286/0.69643；虽胜同频随机和滞后60日特征，未超过打乱状态95%对照0.67637/0.70124，两年相对优势也不一致。仅8个评价标签，不声称regime alpha；暂停这个映射，保留SHORT与专家库。'
lines=['','## D106：固定状态的排名可预测性筛查','',summary,'',
    '12个完整不重叠60日标签；前4段成熟后评价8段（2022年3段、2023年5段）。所有输入由当时完成201日日线计算；慢/快为价格与200/50均线距离符号，vol30>vol200为固定高波动条件，ddof1。soft映射与每次L1≤.5的平滑在运行前固定，0交易模型拟合/网格/新账户。尾部10日不当60日标签，原730日实际账户经济结果未删日期。',
    '|资金费条件|固定状态排名|固定三expert|最佳单expert/成熟过去排名|滞后状态|打乱95%|同频随机95%|到完美排名差距|',
    '|---|---:|---:|---:|---:|---:|---:|---:|']
for v in r['results']:
    m=v['metrics'];values=(m['HAND_FIXED']['mean_weighted_rank'],m['STATIC_DIRECTION3']['mean_weighted_rank'],m['BEST_SINGLE_SMA200_DEVELOPMENT_REFERENCE']['mean_weighted_rank'],m['LAG60_FEATURES']['mean_weighted_rank'],v['placebo_shuffle']['percentile95'],v['placebo_samefrequency_random']['percentile95'],v['hand_to_oracle_rank_gap'])
    lines.append('|'+v['unit']+'|'+'|'.join(f'{x:.5f}' for x in values)+'|')
lines += ['',
    '得分是未来专家净NAV相对排名的权重平均（0–1），不是收益率/准确率/投资业绩；source labels来自已付费用/执行/资金费的完整独立expert账本，只是相对排名标签，不把它们加成组合收益。过去均值排名对照仅使用截至决策已成熟标签，16次统计更新完整记录；无随机CV。',
    '32打乱状态、32同频随机权重路径各在两资金费解释下评分，固定seed、不选赢家；同频随机保留固定映射的实际12次权重变化时刻及L1大小（含初始从CASH变化），未来变化时序条件化，故明确是不可部署的诊断控制。打乱对照也不可部署，重复次数不增加市场历史。',
    '2022年固定映射相对强参照有小优势，2023年落后；超过随机但不超过打乱，说明尚不能把少量收益排序改进归为有用的状态时序信息。未运行这个adaptive映射的真实账户，net/Sharpe/DD均NOT_RUN；D105的真实oracle与静态经济结果保留，不把排名失败改写为所有selector失败。',
    f"独立标量复核全部过去201日特征、12组relative标签、SciPy平均tie排名、8个成熟fold及权重路径；特征最大误差{audit['maximum_feature_error']:.3g}、权重/标签误差0。生产rankdata直接复用SciPy{audit['official_rank_library']['version']} BSD-3-Clause；无本地修改。", 
    next_action,'',
    f'结果 `{name}`，独立核对 `{audit_name}`。复现：progress/bounded下 `regime_ranking_screen.py --protocol protocols/REGIME_RANKING_SCREEN_20261006_V1.json --output <未使用reports文件>`；独立参考见archive/FROZEN_REGIME_RANKING_INDEPENDENT_SOURCE_20261006_V1.py（默认旧输出应改为新文件）。0新市场数据/模型/钱包，核心计算与真实任务时间分开记录；不是把核心{r["elapsed_seconds"]:.2f}秒称整轮时间。', '']
with (ROOT/'docs/SHORT_SELECTION.md').open('a') as f:f.write('\n'.join(lines))
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D106结果与自主决定\n\n'+summary+' D105真实oracle机会仍大，当前最大瓶颈是过去信息的条件排名与跨周期证据，不是执行成本消灭机会。不能用初筛失败永久否定regime-aware方向。'+next_action+' 工件 '+name+' SHA '+sha(ROOT/name)+'。\n')
with (ROOT/'docs/OPEN_SOURCE_REGISTRY.md').open('a') as f:f.write('\n- D106：SciPy https://github.com/scipy/scipy version'+audit['official_rank_library']['version']+' BSD-3-Clause（实际bounded环境metadata读取），仅复用stats.rankdata平均tie ordinal排名，无本地库修改；Polars既有rolling_mean/rolling_std做完成日线特征。fixed soft state map/L1凸步为薄OWN_ADAPTER，不声称公开策略原版；stdlib标量/排序仅独立核验，不作为生产重写库。无新增下载、模型或依赖安装。\n')
status=ROOT/'docs/RESEARCH_STATUS.md';old=status.read_text();economics=old[old.index('## 最新实际经济结果'):old.index('## 当前研究问题与下一项')];boundary=old[old.index('## 数据、账户与资源边界'):]
status.write_text('# COIN 当前研究状态\n\n投资资格 **NONE/CASH**；长期净APR **NOT_EVALUABLE**。\n\n'+economics+'## 当前研究问题与下一项\n\n'+summary+'\n\n'+next_action+'\n\n原SMA200仅多风险效率参照及正SHORT多空挑战者保持；三expert静态保留低风险控制。暂停已测D106映射、D101硬过滤、D102无重入CE、八expert等权主力与ML/4h网格，能力与负结果不删除；reopen条件见决策日志，不降低SHORT研究优先级。\n\n[实际榜单](CTA_LEADERBOARD.md)；[完整经济与排名证据](SHORT_SELECTION.md)。\n\n'+boundary.replace('状态可预测性/placebo/可行adaptive账户NOT_RUN。','D106状态可预测性及排名placebo已测并未通过；可行adaptive账户净收益仍NOT_RUN。'))
selected=read('.cache/d106_selected_snapshot.json')
for path in ('docs/RESEARCH_STATUS.md','docs/SHORT_SELECTION.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md'):
    if path not in selected:selected.append(path)
c=dict(parent_commit=head,module='D106_FIXED_REGIME_RANKING_PROBE',family='PAST_ONLY_FIXED_STATE_MAP',recipe=r['protocol'],
    references={name:r['status'],audit_name:audit['status']},additional_tasks=[dict(id='786a48a87f0745e395a3c6f28d510561',expected_exit_code=0)],
    source_paths=[p for p in selected if p.endswith('.py')],decision=r['decision'],next_action=next_action,primary_reference=name,
    runtime_directory='/home/xflops/coin-state/d106-regime-rank-tests-tmp-20261006-v1',
    closed='reports/REGIME_RANKING_SCREEN_MODULE_CLOSED_20261006_V1.json',binding='reports/GITHUB_REGIME_RANKING_SCREEN_SOURCE_BINDING_20261006_V1.json',
    prior_binding='reports/GITHUB_FROZEN_EXPERT_MIXTURE_SOURCE_BINDING_20261006_V1.json',selected_paths=selected,stage_script='.cache/stage_selected_regime_rank.ps1')
save('protocols/REGIME_RANKING_SCREEN_CLOSE_20261006_V1.json',c)
print(json.dumps(dict(status='NEGATIVE_FIXED_STATE_MAP_RETAINED_WITH_REOPEN_CONDITIONS',summary=summary,next_action=next_action)))
