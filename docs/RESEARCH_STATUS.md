# COIN — 当前科研状态（2026-10-02）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前候选**：没有正净收益合格策略或可靠长期净 APR。现金为零收益对照。接受共同收益比较能力，公开 MIT Jesse Donchian COIN 1h Spot 适配保留作防御参照，已放弃把短窗口冠军当盈利主力。下一研究只检验一个固定2h低换手方向。
2. **实际净收益**：2025-08-01 至 2025-12-01 前连续122日，30bp名义往返成本：cash 0、Donchian −0.2673%、VM_BH −4.0601%、BH −5.6438%。36bp下Donchian −0.7053%。完整12账户实际及独立账本核验均exit0；不是unseen，不冒称长期净APR证明。原四段72账户平均七日Donchian +0.473%保留，但不能代替此连续阴性结果。
3. **最大阻碍**：Donchian同成交数量毛收益 +1.9355%，费用/价差/滑点合计2.2028%，盈亏平衡往返约26.36bp不足原30bp，158fills/38闭合往返。分钟 OHLC/容量仍为代理，真实BBO价格尚缺。共同风险机制不保证相同实现波动。
4. **本轮发现**：公开策略减少下跌期损失，但未产生绝对正净收益。连续分钟MDD公3.691%、VM9.449%、BH12.381%；实现年化波动公6.50%、VM10.31%、BH14.92%。连续账户末仓仅浮点dust，短窗口重置/余仓影响已排查。分钟趋势/MR旧高换手阴性与本次成本瓶颈一致，不以更多模型数量解释。
5. **下一实验及原因**：同一122日历/31日预热、原费用/执行/风险，仅一个固定2h公开规则变体与1h/现金/VM/BH参照。检验减少换手是否保住毛优势；不降费、加杠杆、调阈值或大搜索。源覆盖不变，仍SCREENING，不消耗locked。
6. **暂停与重开**：当前1h盈利部署和分钟trend/MR配方暂停；低换手或新因果信息达到原成本门槛后，再做真正未见验证重开。478cache两个审计blocker未被掩盖，只有研究确需才修复；深度/flow能力保留，依信息增益启用。maker需真实BBO/depth/queue；carry需Spot/USD-M资本、实际资金费时点和可成交价格映射。

完整收益、实际风险、成本、集中度与端点限制见 [共同策略比较](STRATEGY_COMPARISON_20261002.md)。实际输出为 [V3 收益报告](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json)，[实际退出及旧工件等价凭证](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json)。最终经济验收以独立复核及根验收凭证为准。

更新的主要结论见 [连续122日比较](STRATEGY_CONTINUOUS_122D_20261002.md)，
[实际报告](../reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json)和
[独立复核](../reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json)。
旧72账户复现使用Git `543cc9f`，当前普通增量仅薄参数化周期/策略子集与通用字段；
旧源码精确字节和失败凭证不覆盖，原engine/risk/cost/strategies保持。

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,363,274,677B**，测量于 **2026-10-02 12:22:32.895155 UTC**。这是实际扫描时刻值，非当前瞬时值；连续122日工件约86.4MB，旧72工件约40.4MB。
- 连续122日编排进程峰值 RAM **704,081,920B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `543cc9f9b6339fe5dfafde661f5cb3a5a2a6f18e`，共同收益比较与官方来源格式模块已推送。本地连续122日增量随后按模块验收提交；[实际远程一致凭证](../reports/GITHUB_INVESTMENT_COMPARISON_SYNC_VERIFIED_20261002_V1.json)。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
