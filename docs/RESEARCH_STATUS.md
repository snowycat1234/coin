# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前选择**：盈利主力与真钱候选均为 **NONE**。Bybit普通用户费用资产语义已采用；当前研究优先固定carry条件账户，原生投资映射暂缓。2h/hybrid只是参照，没有统一盈利赢家或长期净APR证明。
2. **净APR证据**：基差主体与独立审计完成，现金NAV／净APR仍 **NE**。固定q／首Spot close的终点不利变化BTC3.0661／ETH2.1805bp，标记回撤114.5151／344.1374bp。旧条件coupon及63bp名义成本余量是不同单位，不相加成为净收益。旧固定RSI2负结果不重复回放／拼接年化。
3. **最大阻碍**：需把净qty、Spot base／perp quote费、全部signed资金费、共同资本／保证金和因果退出闭合。Bybit历史唯一请求HTTP403／0样本与Binance单位失败继续保留；当前价格／funding假设加Bybit费用不能称原生收入或投资资格，不绕过接口限制。
4. **本轮发现**：全351360分钟与全10窗口独立复核，终点基差变化小而中途风险显著，尤其October。max adverse／回撤主要是资金及保证金压力，不能仅因接近旧coupon自动STOP；也不能用终点小变动忽略持有风险。最大数学误差9.09555e−14bp，非账户盈利认证。
5. **下一实验及原因**：直接一版D029固定全期连续条件carry账户，C0=10000、每币首signal定额1250USDT／腿，netbase对冲、每币1250独立margin／freecash。仅最高既有spread／slip成本，gross0.6／每underlier0.3／margin50% guard触发下一分钟全平并永久CASH。它最短闭合资本净收益问题；不再增加碎片hurdle、降成本、杠杆或HPO。旧vol／容量／真实MMR尚不可等价，明确proxy边界。
6. **暂停与重开**：Bybit完整原生采集暂缓，合规可达原生输入后重开；完整carry资格需真实可成交basis／收费mark／filters／保证金证据。固定RSI2及阈值HPO暂停，独立新时间或信息提供毛优势与成本余量并事前冻结后重开。其他分钟／1h／2h／hybrid能力依原reopen保留；maker需真实BBO/depth/queue。普通科研继续，locked／资金／资源边界不变。

最新模块为 [固定全122日基差风险](BASIS_RISK_DIAGNOSTIC_20261003.md)、[实际结果](../reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json)。三主体任务真实closed0；采用诊断能力，未计算cash NAV或APR。D028修正粗STOP，D029在carry新合成／市场回放前固定口径。

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

- 最新实际容量扫描：项目 + 整个 D 盘 WSL VHD **19,408,082,087B**，扫描结束于 **2026-10-03 02:21:55.586777 +08:00**；project4,379,890,855B＋VHD15,028,191,232B，预留10MB、状态OK。是本次实际扫描时刻值，非当前瞬时值。基差主体进程峰值279,302,144B／独立80,076,800B；旧kernel资源凭证保留。
- 新RSI2 122/90编排进程峰值 RAM **626,372,608 / 526,163,968B**，独立审计 **409,174,016B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对的远程 HEAD 为 `1fdfd7d6ef23610ee7d1202646a6eb0fab4ad75d`，Bybit原生小窗口实际失败、独立审计／根验收与费用边界模块已推送；[远程一致凭证](../reports/GITHUB_BYBIT_FUNDING_PILOT_SYNC_VERIFIED_20261003_V1.json)。本行与后验同步凭证在推送完成后本机追加，下一个正常模块checkpoint纳入Git，未改冻结科研证据。[旧条件资金费同步](../reports/GITHUB_FUNDING_INCOME_SYNC_VERIFIED_20261003_V1.json)、[旧RSI2同步](../reports/GITHUB_RSI2_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧hybrid同步](../reports/GITHUB_HYBRID_BYBIT_SYNC_VERIFIED_20261002_V1.json)、[旧Bybit费用模块同步](../reports/GITHUB_BYBIT_NATIVE_FEE_SYNC_VERIFIED_20261002_V1.json)、旧90d和2h同步凭证保留。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：全122日基差风险主体、唯一新手算、独立Decimal及根验收已完成，固定24价档／351360分钟／10窗口。两次root metadata hash抄写失败与独立metadata准备失败保留，来源字节未改，最终绑定实际64位SHA。已有条件资金费及阴性证据保留，旧QA／绿测试／Spot账本不重跑；下一项D029固定连续条件carry完整账户正在实现，尚未合成／市场验收。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
