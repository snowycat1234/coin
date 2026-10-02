# COIN — 当前科研状态（2026-10-02）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。固定 MIT Jesse Donchian 的 COIN 1h/2h Spot 适配保留为研究参照；2h由原研究主力降为防御参照，现金为零收益对照。后续平台费用标准按用户新增授权采用 **Bybit 普通用户**。
2. **实际净收益**：新Bybit现货费用资产规则、同固定2h信号下，122日三成本净 **+0.6570% / +0.5932% / +0.4671%**，后来90日 **−1.8173% / −1.8680% / −1.9705%**，六个新账户实际exit0。旧quote共同15账户和2h原122日证据保持；原1h90日净−0.7497/−0.8335/−1.0024%、cash0。新旧各段不拼接；均已见SCREENING，不证明长期APR或项目级unseen。
3. **最大阻碍**：90日新2h毛诊断仍 **−104.24USDT**、成本77.49；费用资产适配未修复毛亏损。新2h分钟MDD **3.720%**，原1h3.252%及实现年化波动6.187%只为旧quote参照，不能称相同实现风险。分钟价格/容量、Binance lot仍不等于Bybit真实可成交行情与过滤器。
4. **本轮发现**：最低成本下新费用规则与旧结果只差122日−0.1022USDT、90日+0.0168USDT，69/65笔成交未增减；真实正dust约0.074～0.956USDT完整MTM。买入base费用不能当quote收费后只改标签，薄适配已经使现金/净持仓/上限一致。旧90日仅Jan正毛/净月的问题未因此消失，信号稳定性仍是瓶颈。原内存IPC未复现的FAIL继续保留；新输入改为物理Arrow文件先保存再读入执行，直接绑定实际文件SHA。
5. **下一实验及原因**：Bybit费用资产兼容完成后，只评估已经7项信号验收的固定2h入场/1h退出挑战者，在同native费用/资金/风险下与这六个2h控制账户比较；经济账本尚未启动。它联合改变退出物理时间尺度和检查频率，不称纯退出延迟因果，不继续扫周期。永续5.5bp taker不得移植到Spot。新平台价格、过滤器与实际账户地区费率仍未覆盖。
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

最新费用资产实测见 [六账户经济影响](BYBIT_SPOT_NATIVE_FEE_ECONOMICS_20261002.md)、
[实现与失败记录](BYBIT_SPOT_RECEIVED_ASSET_IMPLEMENTATION_20261002.md)、
[根验收](../reports/fast_research/BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)。
原quote证据继续按Git `d7aaeb4`复现；新薄兼容层不覆盖旧引擎、合同或任何旧结果。

## 本版实现与保留范围

复用冻结 `quant.backtest` 和 ExecutionContractV2；统一资金、分钟输入、成本、风险、延迟、过去容量、订单/成交/净值账本。公开策略复用固定 commit 的原信号 hook 与官方 Donchian 指标，原 MIT 源码及许可证留存。1h、SMA200、COIN 资金风险和 sizing 是明确的适配，未宣称 Jesse 原生回测复现。固定规则批量计算复用官方 Polars，和旧九账本的 60 个工件数值一致；BH 目标生成从实测 117 秒变为 0.092 秒，未改冻结执行引擎。

第一次实际运行主动停止在 9 个账本，性能问题、NULL availability 反例及 np.int64 索引兼容失败均保留；新证据不覆盖旧失败。全量特征 cache 没有启动，模型拟合 0，发单 0。FrozenPredictor、STOP_v2、A07、holdout、旧工程及阴性结果继续保留。

24 份官方 funding/mark/index 月档的 CHECKSUM、来源格式与逐行 QA 已闭合；仅接受来源。它们不是现货/永续可成交价格，也不产生 carry 收益资格。153 日既有 Spot 分钟来源 QA 直接复用，无重复下载/全源 QA。见 [来源模块](MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md)。

## 资源、进度与同步

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,397,687,566B**，测量于 **2026-10-02 14:38:14.562193 UTC**，发生在本轮新账本产出前。是实际扫描时刻值，非当前瞬时值；native122/90日新工件79.25/62.11MB。
- 新native122/90编排进程峰值 RAM **536,633,344 / 491,397,120B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `d7aaeb4b1ec5e04908c341a8ab6a569ff81bfde1`，90d共同收益与Bybit费用标准模块已验收推送；[远程一致凭证](../reports/GITHUB_PUBLIC_STRATEGY_90D_SYNC_VERIFIED_20261002_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改任何冻结科研证据。旧2h同步凭证仍保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：六个native2h控制账户已根验收，GitHub模块同步中；hybrid只有信号合成验收，未启动经济运行。独立数学为122日三块复用＋90日三块新核，首轮整体exit1与恢复exit0如实保留；费用单位V1失败/仅复验两case、共同入口线程预检失败均保留，详见D017–D018。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
