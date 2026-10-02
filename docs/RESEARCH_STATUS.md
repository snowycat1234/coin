# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。采用Bybit普通现货费用资产语义和官方RSI研究能力；暂停固定RSI2配方。2h/hybrid保留为研究参照，没有统一盈利赢家或长期净APR证明。
2. **实际净收益**：固定RSI2六新账户真实exit0，30/32/36bp下122日净 **−5.7930% / −6.1457% / −6.8512%**，90日 **−7.3942% / −7.5818% / −7.9569%**，均弱于现金及两种旧参照。旧native2h/hybrid仅复用保存摘要。两段单独10k连续资金、均已见SCREENING；不拼接、不选赢期、不年化成长期证据。
3. **最大阻碍**：回撤入场与SMA5退出组合缺少成本余量及稳定毛优势。30bp下122日同净库存毛诊断−31.28USDT、总成本548.01；90日−450.81／288.61。前段主要费用耗损，后段扣费前也显著负，不能仅用降费解释。Binance分钟价格/容量/lot代理仍非Bybit原生执行。
4. **本轮发现**：7个自然月净额全负，只有9月月度gross为正且被成本吃穿。换手37.53／20.01、成交544／396，显著高于2h；实际年化波动仅3.005%／3.849%，分钟MDD反而5.896%／7.528%。共同约束不代表等实现风险；入场与退出同时改变，不是单因素因果识别。官方scalar RSI必须保留240根初始化窗口，不能换full-prefix算法。
5. **下一实验及原因**：更换收入机制，先核资金费rate单位／符号／事件定义，做一次全122日、两资产funding-only收入对两腿成本门槛诊断。现存24档Binance来源只覆盖8–11月；它可低成本排除不足以覆盖成本的静态harvest假说，决定是否值得补可成交basis／资金模型。不把诊断称回测、Bybit收入或净APR；Spot10bp与perp5.5bp每side分别使用，名义fee-only门槛31bp／匹配单腿金额，资本占用另计。
6. **暂停与重开**：固定RSI2盈利配方及更多周期／阈值HPO暂停；新独立时间或信息提供毛优势与成本余量，事前冻结后可重开。旧1h/2h/hybrid及分钟trend/MR盈利路线按既有条件暂停，保留能力与阴性证据。maker需真实BBO/depth/queue；carry净收益需资金费可用／收费时点、保证金／总资本和可成交basis闭合。普通科研自主继续，locked／资金／资源边界不变。

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

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,411,953,280B**，测量于 **2026-10-03 00:03:30.909543 +08:00**（2026-10-02 16:03:30.909543 UTC），发生在RSI2新账本产出前。是实际扫描时刻值，非当前瞬时值；本轮122/90日独占工件79,875,016／63,472,357B，官方kernel增量约2.54MB。
- 新RSI2 122/90编排进程峰值 RAM **626,372,608 / 526,163,968B**，独立审计 **409,174,016B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `6b0ff707f6d47ab81425ad3e5d01818f2eec4f23`，固定hybrid共同经济与六新账户模块已验收推送；[远程一致凭证](../reports/GITHUB_HYBRID_BYBIT_SYNC_VERIFIED_20261002_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改冻结科研证据。[旧Bybit费用模块同步](../reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json)、旧90d和2h同步凭证保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：官方RSI依赖／初始化语义、新集成、固定RSI2六新账户与独立会计／完整因果目标核验、根验收均完成，当前保存与同步本模块。旧4+7+hybrid1及两组六控制不重跑，不称一次合并新测试。失败原字节保留；科研决定见D021–D022。下一项资金费两腿成本可行性诊断。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
