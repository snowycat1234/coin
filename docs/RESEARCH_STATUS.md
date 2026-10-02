# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。保留matched pair只减仓／继续持有作为低换手条件参照，90日时间外推已实际完成并验收，尚无稳定长期APR候选。Bybit VIP0 Spot10bp／perp5.5bp taker及收费资产语义继续；官网2026-10-03核对基础费率未变，账户地区实际费率未认证。
2. **净APR证据**：122日减仓条件净收益 **+0.247449%**；新增90日两固定控制均10000→10003.988973，净 **+0.039890%**，funding17.573984／手续费价差滑点13.362536USDT。样本机械年化分别+0.742143%／+0.161874%，均只描述已见条件样本；长期净APR **NE**。两段独立账户不拼接为连续APR，原全平122日−0.110113%保留。
3. **最大阻碍**：费用后余量薄，正资金费收入跨时段变号；90日2月净−9.373282、signed funding−3.189198USDT。单位、真实Bybit价格／收费mark／filters／MMR及完整风险等价仍未认证。保留403／451，不绕过或重复失败API。
4. **本轮发现**：90日没有cap或margin退出／部分减仓，两方案minute与daily净值字节完全一致，差值0；不能重复宣称减仓优势。全部540事件538计入／2排除、8fills。全观察MDD **0.198205%**，daily0.094190%不能替代；两个账户独立129600分钟现金最大误差1.04774e−11USDT只认证会计。独立适配两次真实exit1保留，V3及根验收真实exit0。
5. **下一实验及原因**：D032只增加一个固定过去资金费永久退出控制，原资本／费用／caps／margin不变，两完整122／90日各一个新账户，对照保存的pair-trim而不重跑旧控制。仅检验过去负coupon是否有持续性及早退错失收入；明确一日availability滞后仍是假设，不把event time当已认证交易信号。先冻结协议和新正确性边界后数学，0 HPO、不择月、增杠杆或降费用。
6. **暂停与重开**：静态carry盈利采用与pair-target HPO暂停，保留控制／能力；独立原生时间或新过去可得状态信息在同成本风险下显示净稳定性才重开。新固定资金费退出若两窗改善不一致／主要正收入被截断即暂停，不扫其他窗口；需新状态信息或真正时间外证据重开。Bybit原生映射需合规可达输入及实际执行保证金；旧flow低费映射需过去可得优势及独立perp经济证据。RSI2／分钟／1h／2h／hybrid和maker依原reopen，普通科研与locked／资金／资源边界不变。

此前基差模块为 [固定全122日基差风险](BASIS_RISK_DIAGNOSTIC_20261003.md)、[实际结果](../reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json)。三主体任务真实closed0；采用诊断能力，该模块未计算cash NAV或APR。D028修正粗STOP，D029在carry新合成／市场回放前固定口径。

**此前已验收全平账户**：[D029连续条件carry](CONDITIONAL_CARRY_ACCOUNT_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json)、[唯一独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json)。主体session10927／chunk1714f6、独立session22783／chunkfa9bb0、根chunka0d87a均真实exit0。采用账本能力，暂停固定全平配方盈利采用；负结果／Windows元数据启动失败保留。单位与执行仍条件代理，长期APR NE；D030另事前冻结及完成，见下。

**已验收机制**：[D030部分减仓控制](CONDITIONAL_CARRY_PAIR_TRIM_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SOURCE_BINDING_20261003_V1.json)。原主体、独立及根实际exit0继续保留。

**最新经济验收**：[D031固定90日两控制](CONDITIONAL_CARRY_90D_20261003.md)、[ALL_FLAT实际](../reports/fast_research/CARRY_90D_ALL_FLAT_ACTUAL_20261003_V1.json)、[PAIR_TRIM实际](../reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json)、[独立V3](../reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json)、[根验收](../reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json)、[实际闭合绑定](../reports/GITHUB_CARRY_90D_SOURCE_BINDING_20261003_V1.json)。两个实际分别chunk66dec8／61416e，独立chunk17c029、根chunkc5523e均exit0。原simulation代码不改，只隔离日期／来源／计数；新1case检查来源与端点。V1／V2独立适配失败、部分已核结果与源码保持原字节，最终两账户V3复核完成；不重放122日旧经济／旧QA／绿测。候选NONE／长期APR NE。

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

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,425,376,322B**，扫描结束于 **2026-10-03 04:09:22.467076 +08:00**；project4,397,185,090B＋VHD15,028,191,232B，预留50MB、状态OK；两个90日账户独占STATE合计12,431,046B随后写入，非当前瞬时总量。复用已有扫描发布到窗口，未新增全盘扫描。两个主体RSS449,466,368／447,397,888B、独立V3 117,313,536B；共享5GB边界保持。
- 新RSI2 122/90编排进程峰值 RAM **626,372,608 / 526,163,968B**，独立审计 **409,174,016B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `dbd9dfb2e78eefc912e317d7f161861834c94b6f`，D031新增18来源主体／独立／根验收、实际metadata字节与失败、协议／实现／文档已推送；[远程一致凭证](../reports/GITHUB_CARRY_CHRONOLOGY_SOURCE_SYNC_VERIFIED_20261003_V1.json)。[原pair-trim同步](../reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SYNC_VERIFIED_20261003_V1.json)保留。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改冻结科研证据。[旧全平carry同步](../reports/GITHUB_CONDITIONAL_CARRY_SYNC_VERIFIED_20261003_V1.json)、[旧基差风险同步](../reports/GITHUB_BASIS_RISK_SYNC_VERIFIED_20261003_V1.json)、[旧Bybit原生失败同步](../reports/GITHUB_BYBIT_FUNDING_PILOT_SYNC_VERIFIED_20261003_V1.json)、[旧条件资金费同步](../reports/GITHUB_FUNDING_INCOME_SYNC_VERIFIED_20261003_V1.json)、[旧RSI2同步](../reports/GITHUB_RSI2_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧hybrid同步](../reports/GITHUB_HYBRID_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧Bybit费用模块同步](../reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json)、旧90d和2h同步凭证保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：D031来源和固定90日两控制经济版本均实际完成／独立核验／根验收；正在正常模块checkpoint，下一D032固定过去资金费永久退出假设，尚未新数学。完整项目目标继续，原来源／失败字节保持。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
