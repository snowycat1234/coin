# COIN — 当前科研状态（2026-10-02）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。固定 MIT Jesse Donchian 的 COIN 1h/2h Spot 适配保留为研究参照；2h由原研究主力降为防御参照，现金为零收益对照。后续平台费用标准按用户新增授权采用 **Bybit 普通用户**。
2. **实际净收益**：固定2025-12-01..<2026-03-01连续90日，原30/32/36bp名义往返成本下，1h净 **−0.7497% / −0.8335% / −1.0024%**，2h净 **−1.8175% / −1.8684% / −1.9709%**。30bp：cash 0、VM_BH −5.5815%、BH −5.5734%。15账户实际exit0、独立15账本数学核验exit0。原122日2h +0.6580%保持，但这两个账户段不拼接；两段均已见历史SCREENING，不证明长期APR或项目级unseen。
3. **最大阻碍**：本段2h毛收益已转负，降低费用不能解释或修复毛亏损。30bp的1h毛+52.62USDT/成本127.59；2h毛−104.26/成本77.49。2h分钟MDD **3.721%**、实现年化波动6.601%，1h为3.252%/6.187%，风险并非完全相同。分钟价格/容量代理仍不等于Bybit或Binance真实可成交行情。
4. **本轮发现**：2h三个月毛/净USDT：Dec −184.79/−223.69、Jan +180.08/+149.86、Feb −99.55/−107.92；仅1/3正月，正毛月全部集中Jan。信号时间尺度和行情稳定性是新瓶颈；现有证据尚不能证明慢退出是原因。BH/VM/1h末仓分别约860.86/613.47/660.26USDT，已计MTM，不能视为免费平仓。独立核验限定精确Parquet与逻辑日历/值：原内存IPC指纹未重现，首次FAIL保留，不宣称字节指纹通过。
5. **下一实验及原因**：先补Bybit现货费用资产的最薄账本适配：公开普通用户Spot maker/taker均10bp/side，数值与旧Spot相同，但buy扣收到的base、sell扣收到的quote；冻结旧引擎和证据，兼容层独立验证。再评估唯一固定2h入场/1h退出挑战者，分辨联合退出时间尺度是否改善gross/net/MDD；不继续扫周期。永续5.5bp taker另属不同产品，不能移植到Spot后宣称盈利。新平台价格、过滤器与实际账户地区费率仍未覆盖。
6. **暂停与重开**：1h/2h盈利部署、分钟trend/MR固定配方和更多周期搜索暂停；新因果改进或独立证据可以重开，不因90d负结果删能力。478cache两个blocker保留，研究确需时修复；深度/flow能力保留。maker需真实BBO/depth/queue；carry需资本、实际资金费时点和可成交价格映射。

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

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,382,577,169B**，测量于 **2026-10-02 13:30:46.612451 UTC**。这是实际扫描时刻值，非当前瞬时值；新90d工件约73.83MB，新2h工件约29.45MB，原连续122日工件约86.4MB，旧72工件约40.4MB。
- 新90d编排进程峰值 RAM **632,123,392B**，独立复核峰值428,220,416B；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `1519a61b1398bba0f6a4f2793f50a39aae4126ac`，2h共同收益模块已验收推送；[远程一致凭证](../reports/GITHUB_PUBLIC_DONCHIAN_2H_SYNC_VERIFIED_20261002_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改任何冻结科研证据。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
