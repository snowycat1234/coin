# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。Bybit普通用户Spot10bp／perp5.5bp taker及收费资产语义已采用。下一研究候选为同风险caps的carry部分减仓控制，尚未运行；2h/hybrid仍只是条件参照，没有长期净APR证明。
2. **净APR证据**：固定122日连续账户10000USDT→9988.988651，条件净收益 **−0.110113%**；funding+5.621259，手续费／价差／滑点16.680241USDT。全观察MDD0.110113%，机械样本年化−0.329077%只描述已见条件窗口；长期净APR **NE**。旧coupon、basis统计及Spot收益不拼接为净APR。
3. **最大阻碍**：全平guard在约11.65日截断收入，成本未摊薄。账本资本／净qty／费用／正负funding已闭合，但单位、真实Bybit价格／收费mark／filters／MMR与完整风险等价未认证。HTTP403／451失败继续保留，不绕过接口限制。
4. **本轮发现**：ETH名义gross达到0.3导致下一分钟全平，触发时isolated权益约997＞625，非保证金破产。全部732事件中只有68持有期计入、664排除，9–11月真实保持CASH。独立175680分钟／122日／4月账本现金误差1.42027e−11USDT，说明负结果的会计可核；不产生原生投资资格。
5. **下一实验及原因**：D030只固定一个同资本／同成本／同0.3与0.6caps的matched pair减仓控制。signal冻结qty到0.25NAV，下一closed分钟减超限币两腿、保留另一币，不增仓／重入／补资；原1250reserve与625margin阈值不放松。直接检验继续持有是否覆盖维护成本；不降成本、提高杠杆、HPO或称同窗unseen OOS。
6. **暂停与重开**：本全平配方暂停盈利采用、保留能力与控制；新独立时间／原生信息在同成本与caps下显示持有净稳定性后重开。Bybit原生映射需合规可达原生输入及真实执行／保证金。固定RSI2及阈值HPO仍暂停，新独立信息的毛优势与成本余量经事前冻结后重开。其他分钟／1h／2h／hybrid依原reopen；maker需真实BBO/depth/queue。普通科研继续，locked／资金／资源边界不变。

最新模块为 [固定全122日基差风险](BASIS_RISK_DIAGNOSTIC_20261003.md)、[实际结果](../reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json)。三主体任务真实closed0；采用诊断能力，未计算cash NAV或APR。D028修正粗STOP，D029在carry新合成／市场回放前固定口径。

**最新已验收账户**：[D029连续条件carry](CONDITIONAL_CARRY_ACCOUNT_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json)、[唯一独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json)。主体session10927／chunk1714f6、独立session22783／chunkfa9bb0、根chunka0d87a均真实exit0。采用账本能力，暂停固定全平配方盈利采用；负结果／Windows元数据启动失败保留。单位与执行仍条件代理，长期APR NE；下一单一减仓机制需另事前固定。

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

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,414,326,918B**，扫描结束于 **2026-10-03 02:47:10.171751 +08:00**；project4,386,135,686B＋VHD15,028,191,232B，预留50MB、状态OK。是实际扫描时刻值，非当前瞬时值。carry主体RSS539,357,184B／独立119,386,112B，新独占STATE1,856,955B；旧kernel资源凭证保留。
- 新RSI2 122/90编排进程峰值 RAM **626,372,608 / 526,163,968B**，独立审计 **409,174,016B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `9c918ae9b3c9f9caddbd77d78a45fd07cbb04dd9`，全122日基差风险主体／独立及根验收、文档与失败来源已推送；[远程一致凭证](../reports/GITHUB_BASIS_RISK_SYNC_VERIFIED_20261003_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改冻结科研证据。[旧Bybit原生失败同步](../reports/GITHUB_BYBIT_FUNDING_PILOT_SYNC_VERIFIED_20261003_V1.json)、[旧条件资金费同步](../reports/GITHUB_FUNDING_INCOME_SYNC_VERIFIED_20261003_V1.json)、[旧RSI2同步](../reports/GITHUB_RSI2_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧hybrid同步](../reports/GITHUB_HYBRID_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧Bybit费用模块同步](../reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json)、旧90d和2h同步凭证保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：D029固定122日连续carry账户、唯一新手算、完整独立Decimal及根验收已完成；来源字节保持、各closed0任务可核。原单位失败与metadata启动失败保留。下一项D030同caps matched pair减仓控制正做独立薄适配准备，尚未运行；旧QA／绿测试／Spot账本不重跑。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
