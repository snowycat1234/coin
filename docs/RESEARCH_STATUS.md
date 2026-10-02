# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。保留matched pair减仓及公开2h／hybrid作为研究参照；D032固定过去资金费永久退出已完成，暂停该配方采用。Bybit VIP0 Spot10bp／perp5.5bp taker及收费资产规则继续，账户地区实际费率未认证。
2. **净APR证据**：原carry控制122日+0.247449%、90日+0.039890%保留；新退出各为 **+0.121382%／+0.065673%**，10k资本净12.138169／6.567334USDT，分别较控制 **−12.606683／+2.578361**。已见两独立账户不拼接为APR；长期净APR **NE**。原样本机械年化只描述条件筛选，非投资证据。
3. **最大阻碍**：收益源跨时段不稳定、费用后余量薄；过去小负coupon不能稳定预测后续负收入。单位、真实Bybit价格／收费mark／filters／MMR及完全风险等价仍未认证；保留403／451，不绕过或重试失败API。
4. **本轮发现**：新退出两窗各触发一次。122日避免负coupon0.707383却错失正12.164115USDT，成本14.390056→15.888201、全观察MDD0.387572%→0.416530%；90日避免负3.862038、错失正1.649367，成本13.362536→13.016100、MDD0.198205%→0.121545%。独立完整核验175680／129600分钟、732／540事件，现金最大误差1.42027e−11、舍入敏感计数0。真实actual／audit／comparison／root均exit0；会计正确不等于配方通过经济门槛。
5. **下一实验及原因**：D033以既有公开2h参照、hybrid挑战者与现金，在2024-01-01..<2025-07-01的547日固定长路径做开发否证，原配方／共同资本风险、已接受36bp保守费用档、0 HPO；2023-12仅warmup。先薄适配日期与38档旧QA元数据来源，不放宽共享label守卫／重写策略。该历史已被旧训练／测试使用，只称SCREENING，不洗白unseen。长经济路径更能区分少数月份贡献、信号不稳和交易成本，比继续扫描退出窗更有信息价值。
6. **暂停与重开**：固定7日／1日滞后永久退出暂停，不扫其他窗口；新过去可得状态信息或真正时间外证据才重开。静态carry盈利采用／pair-target HPO仍暂停，控制与能力保留；原生独立时间在同成本风险下净稳定才重开。公开2h／hybrid仅重开冻结配方的长开发否证，未重开调参或投资资格；RSI2／分钟／1h依旧证据暂停。Bybit原生映射需合规可达输入及执行保证金；flow需过去可得优势与perp经济证据，maker需真实BBO／queue。普通科研继续，locked／资金／资源边界保持。

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

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,428,900,324B**，扫描结束于 **2026-10-02 20:45:31.888181 UTC**；project4,400,709,092B＋VHD15,028,191,232B，预留25MB、状态OK；D032两个账户独占STATE合计10,801,350B随后写入，非当前瞬时总量。复用该完成扫描发布到窗口，未新增可选全盘扫描。两主体RSS535,875,584／450,338,816B、独立133,304,320B；共享5GB边界保持。
- 新RSI2 122/90编排进程峰值 RAM **626,372,608 / 526,163,968B**，独立审计 **409,174,016B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `92948501b1e4a250820d08ffdc1a78239ee0ef04`，D031固定90日两控制、独立V3／根验收、两次真实独立失败、协议／实现／文档已推送；[远程一致凭证](../reports/GITHUB_CARRY_90D_SYNC_VERIFIED_20261003_V1.json)。[18来源同步](../reports/GITHUB_CARRY_CHRONOLOGY_SOURCE_SYNC_VERIFIED_20261003_V1.json)、[原pair-trim同步](../reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SYNC_VERIFIED_20261003_V1.json)保留。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改冻结科研证据。[旧全平carry同步](../reports/GITHUB_CONDITIONAL_CARRY_SYNC_VERIFIED_20261003_V1.json)、[旧基差风险同步](../reports/GITHUB_BASIS_RISK_SYNC_VERIFIED_20261003_V1.json)、[旧Bybit原生失败同步](../reports/GITHUB_BYBIT_FUNDING_PILOT_SYNC_VERIFIED_20261003_V1.json)、[旧条件资金费同步](../reports/GITHUB_FUNDING_INCOME_SYNC_VERIFIED_20261003_V1.json)、[旧RSI2同步](../reports/GITHUB_RSI2_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧hybrid同步](../reports/GITHUB_HYBRID_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧Bybit费用模块同步](../reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json)、旧90d和2h同步凭证保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：D032两完整新账户／独立金融／经济比较／根验收已实际完成，经济门槛false，配方暂停，文档与116源码闭合绑定保存；当前模块准备推送。下一D033长公开策略开发否证，38来源元数据静态就绪，来源专属验收与数学尚未运行。完整项目目标继续，原来源／失败字节保持。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
