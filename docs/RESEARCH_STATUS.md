# COIN — 当前科研状态（2026-10-02）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **最佳研究方向**：公开 MIT Jesse Donchian 的 COIN 1h Spot 适配。作为下一轮研究主力，保留 VM 买入持有、普通买入持有和现金对照。当前四段运行的预选主参照仍是 VM_BH，不能事后改成 Donchian。
2. **净 APR 证据**：尚无可靠长期净 APR。已完成六策略 × 四个已见七日窗口 × 三成本的 72 个独立账户。30bp 名义往返成本下，Donchian 平均七日净收益 +0.473%，普通买入持有 +0.421%，VM_BH +0.188%。这是筛选结果，不拼接、不年化、不称 unseen OOS。
3. **最大阻碍**：Donchian 只有 7 个闭合往返，约 78% 正净收益来自 B 窗口；D 窗口终端仍有约 1,135 USDT 估值持仓。共同风险机制不保证相同实现波动；分钟 OHLC/容量为代理，真实 BBO 可成交价尚缺。
4. **本轮发现**：分钟趋势、分钟均值回归的平均同成交数量毛收益约 +0.184%、+0.035%，成本使净收益分别成为 −2.907%、−9.101%。目前优先解决换手与经济效果；再增加同类模型数量没有充分依据。
5. **下一实验及原因**：使用已验收的同一来源，从 2025-08-01 至 2025-12-01 前连续 122 日运行四个固定策略 × 三成本，仅一次账户初始化与终端处理。参数、成本和风险机制保持，检查收益集中、连续回撤、暴露及余仓影响。该范围按现有覆盖选择，仍属 SCREENING；不消耗 locked。
6. **暂停与重开**：暂停当前分钟趋势/MR 固定配方；在新信息或较低换手机制具有明确经济假设时重开。478 特征缓存有两个独立审计 blocker，暂停完整构建；当下一研究确实需要它时按反例修复。深度模型保留能力，需对应可用信息和预期净收益增益再启。maker 需历史 BBO/depth/queue；carry 需现金与 USD-M 的资本、实际资金费时点及可成交价格映射。

完整收益、实际风险、成本、集中度与端点限制见 [共同策略比较](STRATEGY_COMPARISON_20261002.md)。实际输出为 [V3 收益报告](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json)，[实际退出及旧工件等价凭证](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json)。最终经济验收以独立复核及根验收凭证为准。

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,360,045,166B**，测量于 **2026-10-02 11:45:06.442813 UTC**。这是实际扫描时刻值，非当前瞬时值；V3 比较工件约 40.4MB。
- V3 编排进程峰值 RAM **407,851,008B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `73546402fa45970044e6e091afb58cbde6700bc4`。本版完成验收、修缮文档后按模块提交推送；实际远程一致凭证位于 `reports/GITHUB_*SYNC_VERIFIED*.json`。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
