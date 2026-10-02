# COIN — 当前科研状态（2026-10-02）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前主力研究方案**：固定 MIT Jesse Donchian 的 COIN 2h Spot 适配，保留1h作参照。仅采用为研究主力；**真钱部署候选仍为 NONE**，现金为零收益对照。
2. **实际净收益**：2025-08-01 至 2025-12-01 前连续122日，2h在原30/32/36bp名义往返成本下净收益分别 **+0.6580% / +0.5958% / +0.4692%**。30bp原参照：cash 0、1h −0.2673%、VM_BH −4.0601%、BH −5.6438%。仅新3账户运行、独立3账本实际exit0，旧12绑定输入/日期/成本/引擎直接复用。全部已见历史SCREENING；不证明长期净APR，也不是独立OOS。
3. **最大阻碍**：成本瓶颈改善，稳定性和泛化成为主要未知。30bp的2h毛收益160.62USDT、成本94.82USDT，较1h保留83.0%毛收益、成本下降57.0%；仍只有17闭合往返。2h分钟MDD **4.709%** 高于1h **3.691%**，实现年化波动6.20%与6.50%也不完全相同。分钟OHLC和容量仍是代理，真实BBO可成交性未证明。
4. **本轮发现**：2h非纯降频，20/200根回看物理跨度也翻倍。30bp月净贡献USDT为 Aug +109.31、Sep −78.10、Oct +170.38、Nov −135.79；仅2/4正月。Sep、Nov的同数量毛收益均为负，Nov损失还大于1h；正毛月最高贡献58.96%。成本可覆盖不等于跨状态可靠。末仓仅浮点dust，月间不重置。
5. **下一实验及原因**：先做固定规则的时间段外稳健性：2025-12-01..<2026-03-01连续90日、Oct31..<Dec1的31日预热，cash/BH/VM/1h/2h五方向×原三成本；不继续试周期选赢家、不调参。旧A05/A06已查看Dec–Feb，因此明确不是项目级unseen；仍在locked起点之前。先验收推送本模块，再冻结新来源绑定与实验。
6. **暂停与重开**：1h盈利部署、分钟trend/MR固定配方和继续周期搜索暂停；需要新的因果改进或独立证据才能重开。2h若外推毛收益不足则缩小为防御参照，不降低费用以晋级。478cache两个blocker保留，研究确需时修复；深度/flow能力保留。maker需真实BBO/depth/queue；carry需资本、实际资金费时点和可成交价格映射。

完整收益、实际风险、成本、集中度与端点限制见 [共同策略比较](STRATEGY_COMPARISON_20261002.md)。实际输出为 [V3 收益报告](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json)，[实际退出及旧工件等价凭证](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json)。最终经济验收以独立复核及根验收凭证为准。

更新的主要结论见 [连续122日比较](STRATEGY_CONTINUOUS_122D_20261002.md)，
[实际报告](../reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json)和
[独立复核](../reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json)。
旧72账户复现使用Git `543cc9f`，当前普通增量仅薄参数化周期/策略子集与通用字段；
旧源码精确字节和失败凭证不覆盖，原engine/risk/cost/strategies保持。

本轮主要结论见 [公开策略1h/2h比较](PUBLIC_STRATEGY_HORIZON_COMPARISON_20261002.md)，
[2h实际报告](../reports/fast_research/PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json)和
[3账本独立复核](../reports/fast_research/PUBLIC_DONCHIAN_2H_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json)。
默认1h合法目标及receipt与归档原版本精确等价；原122日参照复现使用Git `bcd35b0`。

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,379,178,257B**，测量于 **2026-10-02 12:51:32.074285 UTC**。这是实际扫描时刻值，非当前瞬时值；新2h工件约29.45MB，原连续122日工件约86.4MB，旧72工件约40.4MB。
- 新2h编排进程峰值 RAM **649,715,712B**，独立复核峰值352,219,136B；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `bcd35b0723933b4f3727d19c3fb18b98911290fe`，两版共同收益及连续122日模块均已验收推送；[连续版本远程一致凭证](../reports/GITHUB_CONTINUOUS_122D_SYNC_VERIFIED_20261002_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改任何冻结科研证据。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
