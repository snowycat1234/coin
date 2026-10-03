# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前APR候选**：投资/真钱NONE、长期净APR NE，资金选择现金；研究主力固定公开SMA50/200完整双向，Donchian为挑战者。signed永续能力已有真实空头成交验收。
2. **当前净收益证据**：D043完整213日独立10k、20固定选择器全部完成。SMA LO/LS条件净+1011.35..1224.57（10.11..12.25%），SO/CASH均0；Donchian+604.29..856.57。BASE/F SMA实际vol11.20%、全观察MDD7.75%，Donchian8.80%/6.36%，共同caps不称风险匹配。旧D040 short122/90日净+83.89..91.67/+615.47..641.54继续保留；窗口不拼NAV或稳定APR。
3. **最大阻碍**：能否超越同产品受控市场暴露，以及资金费单位/Bybit原生风险执行和未来独立证据。原547来源仍拒绝，官方8月缺两分钟不补价/删日；213完整不是547恢复。
4. **本轮发现**：本窗SMA无空头信号/成交，LS逐项等于LO，空头净增量0；这是固定信号行为，不否认D040真实做空能力。两策略各4/7正月，Feb占全期净约98%/125%；Apr/Jun扣费前亦负，利润不能仅归因低成本，SMA高收益同时实际风险更高。
5. **下一项及理由**：一个固定同USD-M、past30日cov风险/原caps/10k/费用/完整资金费的波动管理持有基准，在213/122/90完整已见窗口分别独立账户，对保存SMA/Donchian比较；直接检验收益是否只是beta，不做新模型/HPO/事后风险放大或月赢家拼接。尚未启动此基准。
6. **暂停及reopen**：完整547分钟需真实合法缺记录或事前独立验证缺失风险方法；SMA/Donchian投资与搜索需同产品强基准跨状态增量、合理实际风险和未来证据；新模型需强基准不能解释且有信息增益理由；D039仅具体决策需要时开。D40GB/shared5GB/swap0/GPU0/holdout/真钱/keys/paid边界不变。

**D043实际证据**：[完整比较与采用](PERPETUAL_213_COMPARISON_20261003.md)、[主体](../reports/fast_research/PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json)、[独立V3](../reports/fast_research/PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V3.json)、[保存经济比较](../reports/fast_research/PERPETUAL_213_ECONOMIC_COMPARISON_20261003_V1.json)、[根接受](../reports/fast_research/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json)。全72首次QA、唯一新因果接线case、主体/独立/比较/根均真实closed0。16交易＋1恒定cash工件，独立17金融调用＋3现金严格等价；无旧账户/QA重放。独立误差≤1.82e−11USDT/2.03e−14，原full-sizing和future-poison未独立全重建，scope不扩大。三个显示/metadata真实失败保留，V3金融数学不改。新源18.019MB/主体336.294MB/RSS503.87MB；实扫21,609,669,564B@2026-10-03 14:53:37.111144+08，后续工件不在scan，8765已原时刻发布。采用研究能力，投资仍现金；模块Git闭合待实际执行。
**D042实际证据**：[数据缺口与决策](PERPETUAL_HISTORY_GAP_20261003.md)、[source真实失败](../reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json)、[唯一单月独立](../reports/fast_research/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_20261003_V1.json)、[官方日档实测](../reports/fast_research/PERPETUAL_HISTORY_OFFICIAL_DAY_PROBE_20261003_V1.json)、[根诊断接受](../reports/fast_research/PERPETUAL_HISTORY_GAP_ROOT_ACCEPTANCE_20261003_V1.json)。任务META0/SOURCE1/GAP0/DAY0/ROOT0真实闭合；full148QA/source根/547经济未执行。source新工件165,967,471B/RSS170.44MB，原失败/partialPQ保留。实际ROOT+VHD21,402,704,833B于2026-10-03 13:41:59.842960+08结束，后续输出未计，8765已显示真实时刻；GPU0/共享5GB/collector540保持。模块文档/字节门槛及Git同步已完成并核远端一致792c6b1；后验凭证a47823a7下个正常模块入库。此为D042当时交接；213现已按上方D043实际完成，不改原547失败。

**D041实际完成证据**：[本版经济与决策](PERPETUAL_PUBLIC_BENCHMARK_20261003.md)、[新八金融](../reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ACTUAL_20261003_V1.json)、[新独立](../reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_AUDIT_20261003_V1.json)、[根与保存比较](../reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ROOT_ACCEPTANCE_20261003_V1.json)。bc89/bf13/b50b真closed0；new8/old32saved、2新tests、仅两新源QA，原账户/绿测/42源不重做。最大独立误差money1.09e−11/ratio3.51e−14；金融body原字节复用，全市场frozenintent sizing尚未独立重建。实际source118KB/market70,982,924B/RSS598.5MB，共享硬5GB/swap0/GPU0。最近ROOT+VHD实际21,296,913,232B于2026-10-03 12:40:08.465729+08完成；后来输出不在scan。8765实际完成数/旧扫描真实时刻，打开queued无visible假报。文档、373冻结blob/0敏感匹配门槛、本版正常提交推送与远程精确一致已完成f1fafea；后验凭证b261于下个正常模块入库。D042补源148元数据已真0，source于第84档完整日历守卫处真1，原165,967,471B工件保留，独立raw缺口诊断正在实施；新经济未查看。

**D040完整证据**：[多空模块](PERPETUAL_LONG_SHORT_20261003.md)、[原32实际](../reports/fast_research/PERPETUAL_DIRECTIONAL_ACTUAL_20261003_V1.json)、[原独立](../reports/fast_research/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT_20261003_V1.json)、[新两正确性复测](../reports/fast_research/PERPETUAL_SETTLEMENT_REPLAY_ACTUAL_20261003_V1.json)、[新两独立](../reports/fast_research/PERPETUAL_SETTLEMENT_TWO_CASE_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_20261003_V1.json)。根session78036/chunkec583c/task1b11a04998844f838174bc73af22df73实际exit0，10个先决角色真实closed0；源/账户/信号/controller/原32/新两金融与必要失败按源码哈希闭合，private lock仅本地核不入portable。原30金融/旧QA/绿测不重放。新的完整两case各129600分钟/90天/3月，独立最大金额3.64e−12、比例2.22e−15，原stop前129legs/540资金费/180targets/129595分钟政策数量价格时序完全相同，prefix金额误差0。ROOT+VHD最近实际扫描21,256,028,075B于2026-10-03 11:31:35.351906+08结束，后来新两输出不在该扫描；8765已发布准确时间。共享硬5GB/swap0/GPU0保持；主体RSS382.8MB、新两336.6MB、独立312.1/267.3MB，未超预算。模块文档/源码字节门槛/正常提交推送与远程精确一致已完成09d6a7a；后验小凭证ca6c3446于下一正常模块入库，D041已实际启动；完成结果另用新凭证，不覆盖D040。
**D038完整证据**：[模块](PUBLIC_SMA_DAILY_20261003.md)、[547日实际](../reports/fast_research/PUBLIC_SMA_DAILY_547D_ACTUAL_20261003_V1.json)、[122日实际](../reports/fast_research/PUBLIC_SMA_DAILY_122D_ACTUAL_20261003_V1.json)、[90日实际](../reports/fast_research/PUBLIC_SMA_DAILY_90D_ACTUAL_20261003_V1.json)、[独立V2](../reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json)、[保存比较](../reports/fast_research/PUBLIC_SMA_DAILY_ECONOMIC_COMPARISON_20261003_V1.json)、[根V3薄入口实际报告](../reports/fast_research/PUBLIC_SMA_DAILY_ROOT_ACCEPTANCE_20261003_V1.json)。原MIT hook未改；复用66日档与原分钟输入、每窗200完成日warmup/fresh flat，0 fit/HPO/locked/orders。唯一caseV1错误约束合法补买以及独立V1拒绝新registry路径的真实失败保留，V2只修首次BUY断言/精确metadata路径，源/金融/费用/target/容差未改。独立核759日/1092960分钟/25月，根七closed0角色与失败/专属目录/冻结字节闭合，旧金融/QA不重放。实际独立target保留生成时UNRUN注释，以实际调用PASS为准。

描述性Pareto支配关系（net≥、实现vol≤、分钟MDD≤且至少一项严格，非显著性或未来资格）：547天：波动管理持有；122天：波动管理持有、2小时Donchian及混合周期Donchian；90天：无参照支配SMA现金，但现金也不产生正交易alpha。

**D037完整证据**：[固定日线模块](PUBLIC_DONCHIAN_DAILY_20261003.md)、[547日实际](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_547D_ACTUAL_20261003_V1.json)、[122日实际](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_122D_ACTUAL_20261003_V1.json)、[90日实际](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_90D_ACTUAL_20261003_V1.json)、[独立](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json)、[保存经济比较](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_ECONOMIC_COMPARISON_20261003_V1.json)、[根V2](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V2.json)。66官方CHECKSUM日档完整2008行、每币1004日；每窗恰好200完成日仅预热/fresh flat，下一分钟+1us原成交代理。独立759日/1092960分钟/25月、金额误差≤1.7648563e−11USDT；全事件MDD/原生publication/成交未认证。两个来源初始化失败及根V1内部pytest链接误拒绝保持原字节，新薄版本仅metadata修正，不改原金融/费用/资源守卫。源/唯一1case/三实际/独立/保存比较均真实closed0；根V2后验最终退出在Git同步凭证绑定。
**D036完整证据**：[公开策略互补诊断](PUBLIC_PAIR_COMPLEMENTARITY_20261003.md)、[实际V2](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ACTUAL_20261003_V2.json)、[独立](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_ACCEPTANCE_20261003_V1.json)。实际session48238/chunk53589f、独立session7464/chunkf1f6cf、根chunk949fc5均exit0；逐窗759日／1518个账户日／2185920分钟投影，12文件，仅新统计，无原账户／QA重放。独立最大金额误差1.136868e−13／比率误差1.745271e−13。源码与输入SHA冻结；第一次PowerShell别名／Progress显示初始化失败在数组前，原字节和实际失败任务保留，V2薄适配只改显示初始化，科学数学保持。协议显示文字P/TaskHash误字以独立erratum解释为P/H，门槛和原协议未改。两专属STATE1,064,080B≤5MB；实际RAM峰406,355,968B、独立401,903,616B，共享5GB／swap0／GPU0。实际盘扫描20,178,767,678B于2026-10-03 07:18:58.237603+08完成，后续工件不在该扫描；已发布至8765。模块Git提交与远程一致核验真实完成，d8f6c3fbc6df919f1a68e30415df09e0e666b3c5；[后验同步凭证](../reports/GITHUB_PUBLIC_PAIR_COMPLEMENTARITY_SYNC_VERIFIED_20261003_V1.json) SHAa0468bcf…将在下一正常模块入库。
**D035完整证据**：[两后续窗口结果](VOL_MANAGED_HOLD_TWO_PERIOD_COMPARISON_20261003.md)、[122日实际](../reports/fast_research/VOL_MANAGED_HOLD_122D_ACTUAL_20261003_V1.json)、[90日实际](../reports/fast_research/VOL_MANAGED_HOLD_90D_ACTUAL_20261003_V1.json)、[独立V2](../reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json)、[共同经济比较](../reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_20261003_V1.json)、[根验收](../reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_ROOT_ACCEPTANCE_20261003_V1.json)。两个市场session65778/chunk466c98、session71502/chunkdf569f；独立session82449/chunk3ab59c、比较chunk8791e5、最终根session29904/chunkbf08c9均exit0。新1case覆盖两metadata路由，旧QA／账户／绿测未重跑；独立V1缺scope字段、根首次Python误解析JSON的真实失败和未运行草稿均分别保留。独立212日／305280分钟／7月核算，逐成交Decimal最大现金误差1.735752e−11。市场RSS665MB／568MB，独立454MB；六STATE127,021,300B≤事前150MB。最新实际扫描20,110,293,084B于2026-10-03 06:38:51.801197+08完成，后续工件不在此旧时刻；模块Git提交／推送真实完成，远程一致89a305dff9a6ed3708b1bd0add44acf047531fe0；[后验同步凭证](../reports/GITHUB_VOL_MANAGED_HOLD_TWO_PERIOD_SYNC_VERIFIED_20261003_V1.json) SHA1f6f7db2…在下一正常模块入库。
**D034完整证据**：[波动管理持有比较](VOL_MANAGED_HOLD_547D_COMPARISON_20261003.md)、[实际](../reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json)、[独立](../reports/fast_research/VOL_MANAGED_HOLD_547D_INDEPENDENT_AUDIT_20261003_V1.json)、[共同经济比较](../reports/fast_research/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_20261003_V1.json)、[根验收](../reports/fast_research/VOL_MANAGED_HOLD_547D_ROOT_ACCEPTANCE_20261003_V1.json)。实际session38342/chunk1b1bda、独立session20430/chunk7f97b9、比较chunk3e134a、根session6234/chunk4847fd均exit0；唯一边界V2通过，V1行序测试失败保留。主体RSS2.147GB／81.55s，独立974MB／27.76s，五个明确新增STATE目录268,476,489B≤300MB；扫描19,773,190,377B于2026-10-03 06:06:46.642795+08:00完成，随后工件不在此扫描值。Git模块提交／推送已核远程一致6ce25c0115ff24ce1dc97ed0115eb9dea522535d；[实际同步凭证](../reports/GITHUB_VOL_MANAGED_HOLD_547D_SYNC_VERIFIED_20261003_V1.json)后验SHA409d0e…在下一正常模块入库。
**D033完整证据**：[固定547日公开策略比较](PUBLIC_LONG_547D_COMPARISON_20261003.md)、[主体实际](../reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json)、[独立V3](../reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json)、[根验收](../reports/fast_research/PUBLIC_LONG_547D_ROOT_ACCEPTANCE_20261003_V1.json)。source／唯一新边界case／主体／独立／根均真实closed0；协议启动路径失败与独立V1/V2空现金兼容失败保持原字节。[实际源码闭合](../reports/GITHUB_PUBLIC_LONG_547D_SOURCE_BINDING_20261003_V1.json)真实session12160／chunke7a304 exit0，112个冻结文件、九个真实任务含失败记录保存；13个明确自有目录合计334,974,156B。主体RSS2.246GB、独立1.056GB，新增主体333,111,127B；共享5GB／swap0／GPU0及D40GB不变。
此前基差模块为 [固定全122日基差风险](BASIS_RISK_DIAGNOSTIC_20261003.md)、[实际结果](../reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json)。三主体任务真实closed0；采用诊断能力，该模块未计算cash NAV或APR。D028修正粗STOP，D029在carry新合成／市场回放前固定口径。

**此前已验收全平账户**：[D029连续条件carry](CONDITIONAL_CARRY_ACCOUNT_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json)、[唯一独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json)。主体session10927／chunk1714f6、独立session22783／chunkfa9bb0、根chunka0d87a均真实exit0。采用账本能力，暂停固定全平配方盈利采用；负结果／Windows元数据启动失败保留。单位与执行仍条件代理，长期APR NE；D030另事前冻结及完成，见下。

**已验收机制**：[D030部分减仓控制](CONDITIONAL_CARRY_PAIR_TRIM_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SOURCE_BINDING_20261003_V1.json)。原主体、独立及根实际exit0继续保留。

**此前经济验收**：[D031固定90日两控制](CONDITIONAL_CARRY_90D_20261003.md)、[ALL_FLAT实际](../reports/fast_research/CARRY_90D_ALL_FLAT_ACTUAL_20261003_V1.json)、[PAIR_TRIM实际](../reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json)、[独立V3](../reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json)、[根验收](../reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json)、[实际闭合绑定](../reports/GITHUB_CARRY_90D_SOURCE_BINDING_20261003_V1.json)。两个实际分别chunk66dec8／61416e，独立chunk17c029、根chunkc5523e均exit0。原simulation代码不改，只隔离日期／来源／计数；新1case检查来源与端点。V1／V2独立适配失败、部分已核结果与源码保持原字节，最终两账户V3复核完成；不重放122日旧经济／旧QA／绿测。候选NONE／长期APR NE。

**D032已验收**：[固定过去资金费退出](CARRY_PAST_FUNDING_EXIT_20261003.md)、[122日实际](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_122D_ACTUAL_20261003_V1.json)、[90日实际](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_90D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json)、[经济比较](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_ECONOMIC_COMPARISON_20261003_V1.json)、[根验收](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_ROOT_ACCEPTANCE_20261003_V1.json)、[实际闭合绑定](../reports/GITHUB_CARRY_PAST_FUNDING_EXIT_SOURCE_BINDING_20261003_V1.json)。采用因果退出／统一比较能力，配方经济门槛false，暂停并保留负结果。两个实际、独立、比较、根任务均实际closed0；初次import启动exit1保留，后修环境；唯一新1case、原金融循环和费用守卫未改。条件归因不是现金流，单位与availability没有获认证。

最新实现／实际失败／费用与后续决策见 [Bybit原生资金费小窗口](BYBIT_NATIVE_FUNDING_PILOT_20261003.md)、[实际exit1报告](../reports/fast_research/BYBIT_FUNDING_HISTORY_PILOT_ACTUAL_20261003_V1.json)、[独立源失败审计](../reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_FAILED_RESPONSE_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/BYBIT_FUNDING_PILOT_ROOT_ACCEPTANCE_20261003_V1.json)。模块边界验收完成，原生data／unit gate **NOT_PASSED**。D026／D027事前范围与结果决策保留。

当前实际诊断见 [资金费条件结果与经济边界](FUNDING_INCOME_CONDITIONAL_DIAGNOSTIC_20261003.md)、[732事件结果](../reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[独立组合核验](../reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json)、[根验收](../reports/fast_research/FUNDING_INCOME_ROOT_MODULE_ACCEPTANCE_20261003_V1.json)。单位失败保持UNCONFIRMED；数学成功不代表单位、实际现金收入或APR认证。

完整收益、实际风险、成本、集中度与端点限制见 [共同策略比较](STRATEGY_COMPARISON_20261002.md)。实际输出为 [V3 收益报告](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json)，[实际退出及旧工件等价凭证](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json)。最终经济验收以独立复核及根验收凭证为准。

更新的主要结论见 [连续122日比较](STRATEGY_CONTINUOUS_122D_20261002.md)，
[实际报告](../reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json)和
[独立复核](../reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json)。
旧72账户复现使用Git `543cc9f`，当前普通增量仅薄参数化周期/策略子集与通用字段；
旧源码精确字节和失败凭证不覆盖，原engine/risk/cost/strategies保持。

原122日结论见 [公开策略1h/2h比较](PUBLIC_STRATEGY_HORIZON_COMPARISON_20261002.md)，
[2h实际报告](../reports/fast_research/PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json)和
[3账本独立复核](../reports/fast_research/PUBLIC_DONCHIAN_2H_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json)。
默认1h合法目标及receipt与归档原版本精确等价；原122日参照复现使用Git `bcd35b0`。

当前结论见 [连续90日比较](PUBLIC_STRATEGY_CHRONOLOGY_90D_20261002.md)、
[实际15账户](../reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json)、
[独立限定核验](../reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2_R2.json)、
[根验收](../reports/fast_research/PUBLIC_STRATEGY_90D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)。
Bybit标准登记见 [费用口径](BYBIT_NONVIP_COST_STANDARD_20261002.md)。

最新费用资产实测见 [六账户经济影响](BYBIT_SPOT_NATIVE_FEE_ECONOMICS_20261002.md)、
[实现与失败记录](BYBIT_SPOT_RECEIVED_ASSET_IMPLEMENTATION_20261002.md)、
[根验收](../reports/fast_research/BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)。
原quote证据继续按Git `d7aaeb4`复现；新薄兼容层不覆盖旧引擎、合同或任何旧结果。

本轮固定退出机制实际结果见 [hybrid共同经济比较](PUBLIC_DONCHIAN_HYBRID_NATIVE_FEE_ECONOMICS_20261002.md)、
[六新账本独立审计](../reports/fast_research/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json)。
[根验收](../reports/fast_research/PUBLIC_DONCHIAN_HYBRID_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)
已绑定三主体任务与审计真实exit0；导出失败字节见
[元数据出口与源码凭证](../reports/GITHUB_HYBRID_NATIVE_AUDIT_EXPORT_SOURCE_BINDING_20261002_V1.json)。
该hybrid模块验收时core、common、native费用及已验收hybrid目标代码保持原字节；当前RSI2增量仅演进common策略ID和三行路由，原bff源码精确归档。

最新固定公开RSI2结果见 [共同经济比较与实现](PUBLIC_RSI2_NATIVE_FEE_ECONOMICS_20261002.md)、
[六新账本独立审计](../reports/fast_research/PUBLIC_RSI2_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json)、
[根验收](../reports/fast_research/PUBLIC_RSI2_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)。
唯一新集成1case实际PASS，旧绿色凭证直接复用；官方`jesse-rust1.3.0` wheel在D承载STATE单独安装，
原env/uv.lock与core/native费率适配器不改。两次安装失败、官方240bar语义和实际退出凭证保留。

最新输入模块：[固定90日18来源](CARRY_CHRONOLOGY_SOURCE_18_20261003.md)、[主体](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ACTUAL_20261003_V1.json)、[独立QA](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_INDEPENDENT_QA_20261003_V1.json)、[根验收](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ROOT_ACCEPTANCE_20261003_V1.json)。来源验收只认证格式；本版90日经济协议在新数学前另冻结。原wrapper参数失败及单位UNCONFIRMED保持。

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 历史资源、进度与同步（当前值见顶部）

- 最新已完成实际扫描20,886,214,070B于2026-10-03 00:54:32.790511UTC/08:54:32.790511+08结束；project4,415,182,262B＋VHD16,471,031,808B，后续工件不在旧扫描内。该实际值/时刻已发布8765，非新扫描；D40GB/32预警/36停新增不变。
- 新三市场RSS2,015,547,392/642,916,352/542,232,576B；共享硬4,999,999,488B、历史峰3,263,008,768B、swap0/GPU0，内核资源限制未变。
- [本机窗口](http://localhost:8765/)API健康errors[]，任务使用真实状态；未知内部总量不造百分比。既有公开采集来源未改、不拼接健康资格。
- 上一模块D037远程一致7da8e0202874d50a6c00651312c261e65811772b，后验同步凭证c0af3204…本轮入库。D038实际/独立V2/保存比较/根验收/文档/231冻结blob门槛/正常提交推送/远程精确一致均已完成：4bf2bc1c521835c22598482900329c96a0564d4f。后验同步凭证d90af8745d03f537a8628599456be9c5457650b5aec6f1754251fc7499ada04d在下一正常模块入库，根最终closed0已核。
- 完整项目目标继续，D038模块验收与同步完成，下一固定保存账本分币gross/暴露归因已选定尚未运行；长期APR NE/候选NONE。locked/真钱须用户另行授权。
- 根核八个明确独占STATE合计388013693B≤450MB；独立V2RSS1051361280B。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
