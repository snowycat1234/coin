# COIN — 当前科研状态（2026-10-02）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。Bybit普通用户现货费用资产语义已经采用；固定2h及2h入场/1h退出hybrid保留为研究参照。本轮混合结果不足以选统一赢家或证明长期净APR。
2. **实际净收益**：hybrid六个新账户真实exit0，30/32/36bp下122日净 **−1.1585% / −1.2583% / −1.4540%**，90日 **+0.8667% / +0.8161% / +0.7136%**。同native2h控制分别为 **+0.6570% / +0.5932% / +0.4671%** 与 **−1.8173% / −1.8680% / −1.9705%**，原控制不重跑。两段单独连续资金，均已见SCREENING；不拼接、不选赢期、不年化成长期证据。
3. **最大阻碍**：退出机制存在跨期取舍。30bp下122日hybrid毛诊断32.62USDT、成本148.47（控制160.53/94.83），90日162.73/76.06（控制−104.24/77.49）。前段损伤毛收益且增加换手，后段改善主要来自毛收益；不是降低手续费制造的改善。历史Binance分钟成交/lot代理仍非Bybit原生行情和过滤器。
4. **本轮发现**：共同风险规则下实现风险不同。hybrid122/90分钟MDD **4.970% / 2.762%**，年化实际波动 **5.597% / 5.868%**；控制 **4.709% / 3.720%**、**6.204% / 6.601%**。新六账本逐fill/分钟/日/月独立数学与完整因果目标核验PASS，旧合成及控制证据直接复用。正dust仍MTM；严格全库存归零RT=0不能解释为没有卖出或作为独立交易数。
5. **下一实验及原因**：暂停本固定hybrid配方继续调周期；换一个有明确公开规则的入场信息假说。优先同MIT pin的公开RSI2 long-only1h趋势内回撤，与追突破形成对照。先核成熟官方RSI依赖及输出兼容，不手写kernel；固定阈值/周期、同费用风险评价，收益未知且短持仓仍可能被成本消耗。不得按本两段结果路由策略。永续费率不得移植到Spot。
6. **暂停与重开**：1h/2h/hybrid盈利部署、旧分钟trend/MR配方、更多周期/HPO暂停；新未消费时期或明确新信息支持的机制假说并事前冻结协议可重开。保留突破/均值回归/深度/flow能力，不为保持方向机械重跑。478cache仅研究依赖需要时修复；maker需真实BBO/depth/queue，carry需真实资金费时点、资本和可成交价格映射。

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
core、common、native费用及已验收hybrid目标代码均保持原字节，只增加一个新的联合合成测试与新协议/实际凭证。

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,399,213,181B**，测量于 **2026-10-02 23:20:58.963501 +08:00**（15:20:58.963501 UTC），发生在hybrid新账本产出前。是实际扫描时刻值，非当前瞬时值；本轮122/90日新工件79.18/62.31MB。
- 新hybrid122/90编排进程峰值 RAM **626,176,000 / 566,685,696B**，独立审计 **409,313,280B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `7fb70fbffd35cbe0851089cf9858ccc817a2d8ca`，Bybit费用资产与六个2h控制账户模块已验收推送；[远程一致凭证](../reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改冻结科研证据。旧90d和2h同步凭证保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：六个native2h控制账户保持验收；本轮hybrid六个新账户和一次完整六账本独立数学/目标核验完成，单个新增集成用例PASS。旧4+7合成凭证直接复用，不称一次12PASS。费用资产旧失败与恢复、原IPC失败保留，详见D017–D020。当前混合结果不采用为盈利主力。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
