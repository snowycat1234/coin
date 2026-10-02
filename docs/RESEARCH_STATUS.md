# COIN — 当前科研状态（2026-10-03）

当前长期原则：[自主迭代、开源对标、投资质量优先](archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md)。目标是相同资本和明确风险约束下，扣除真实成本的长期净几何 APR。普通研发由研究负责人依据证据自主决定；旧固定模型顺序、P1 全方向禁令及大清单不是当前命令。

## 当前选择与证据

1. **当前APR候选**：投资主力／真钱候选仍 **NONE**；研究参照为原公开Donchian2h。D033固定547日／36bp共同账户已实际、独立与根验收；hybrid尚未获得主力升级。
2. **净APR证据**：2h净 **+7.601846%／760.184608USDT**，hybrid **+5.839993%／583.999316USDT**，现金0；10k起始资金、同BybitVIP0 Spot10bp/side，样本机械年化5.010455%／3.859977%仅描述。长期净APR **NE**，已见历史不称unseen；期末602.035934／1134.522099USDT实质持仓仍按市值计价。
3. **最大阻碍**：跨状态不稳定、交易成本消耗大量gross、尚未区分主动规则与简单市场暴露的贡献。2h分钟DD12.664746%／实际vol8.895901%，hybrid DD8.796848%／vol7.585553%；共用风险规则不代表实际风险完全相同。Binance分钟代理／Bybit当前费用仍非Bybit原生执行认证。
4. **本轮发现**：hybrid毛收益多108.124396USDT，却多284.309688成本，净少176.185292；395→578笔成交。2h8/18正月／hybrid6/18，两者2025前半年亏损；正月份集中度36.76%／52.93%。三个完整分钟账户与18月表已独立核对，逐成交Decimal最大现金误差1.976603e−11；minute/daily MDD分别核验，全部事件回撤仍未证明。会计通过不等于投资采用。
5. **下一步及理由**：D034补齐原VOL_MANAGED_BUY_AND_HOLD，同547日、同资金／源／36bp／原common风险，只新增一个固定基准账户，比较三份已保存D033，不重跑。先判断公开主动交易是否值得其周转与成本，再选方向；0 HPO，不放松成本或杠杆。当前D034尚未运行。
6. **暂停及reopen**：hybrid主力升级／原公开配方投资采用暂停，未来或原生证据显示同成本风险净稳定优势才重开；配方与benchmark能力保留。固定7日／1日滞后carry永久退出及窗口HPO暂停，新过去可得状态或真正时间外证据才重开。静态carry、RSI2、分钟／1h、maker依旧reopen；Bybit原生需合规可达输入及filters／MMR／成交条件，flow需过去可得优势与perp经济映射。403／451保留，locked／真钱／密钥／资源边界保持。

**D033完整证据**：[固定547日公开策略比较](PUBLIC_LONG_547D_COMPARISON_20261003.md)、[主体实际](../reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json)、[独立V3](../reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json)、[根验收](../reports/fast_research/PUBLIC_LONG_547D_ROOT_ACCEPTANCE_20261003_V1.json)。source／唯一新边界case／主体／独立／根均真实closed0；协议启动路径失败与独立V1/V2空现金兼容失败保持原字节。[实际源码闭合](../reports/GITHUB_PUBLIC_LONG_547D_SOURCE_BINDING_20261003_V1.json)真实session12160／chunke7a304 exit0，112个冻结文件、九个真实任务含失败记录保存；13个明确自有目录合计334,974,156B。主体RSS2.246GB、独立1.056GB，新增主体333,111,127B；共享5GB／swap0／GPU0及D40GB不变。
此前基差模块为 [固定全122日基差风险](BASIS_RISK_DIAGNOSTIC_20261003.md)、[实际结果](../reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json)。三主体任务真实closed0；采用诊断能力，该模块未计算cash NAV或APR。D028修正粗STOP，D029在carry新合成／市场回放前固定口径。

**此前已验收全平账户**：[D029连续条件carry](CONDITIONAL_CARRY_ACCOUNT_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json)、[唯一独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json)。主体session10927／chunk1714f6、独立session22783／chunkfa9bb0、根chunka0d87a均真实exit0。采用账本能力，暂停固定全平配方盈利采用；负结果／Windows元数据启动失败保留。单位与执行仍条件代理，长期APR NE；D030另事前冻结及完成，见下。

**已验收机制**：[D030部分减仓控制](CONDITIONAL_CARRY_PAIR_TRIM_20261003.md)、[完整实际](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)、[根验收](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json)、[closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SOURCE_BINDING_20261003_V1.json)。原主体、独立及根实际exit0继续保留。

**此前经济验收**：[D031固定90日两控制](CONDITIONAL_CARRY_90D_20261003.md)、[ALL_FLAT实际](../reports/fast_research/CARRY_90D_ALL_FLAT_ACTUAL_20261003_V1.json)、[PAIR_TRIM实际](../reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json)、[独立V3](../reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json)、[根验收](../reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json)、[实际闭合绑定](../reports/GITHUB_CARRY_90D_SOURCE_BINDING_20261003_V1.json)。两个实际分别chunk66dec8／61416e，独立chunk17c029、根chunkc5523e均exit0。原simulation代码不改，只隔离日期／来源／计数；新1case检查来源与端点。V1／V2独立适配失败、部分已核结果与源码保持原字节，最终两账户V3复核完成；不重放122日旧经济／旧QA／绿测。候选NONE／长期APR NE。

**D032已验收**：[固定过去资金费退出](CARRY_PAST_FUNDING_EXIT_20261003.md)、[122日实际](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_122D_ACTUAL_20261003_V1.json)、[90日实际](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_90D_ACTUAL_20261003_V1.json)、[独立Decimal](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json)、[经济比较](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_ECONOMIC_COMPARISON_20261003_V1.json)、[根验收](../reports/fast_research/CARRY_PAST_FUNDING_EXIT_ROOT_ACCEPTANCE_20261003_V1.json)、[实际闭合绑定](../reports/GITHUB_CARRY_PAST_FUNDING_EXIT_SOURCE_BINDING_20261003_V1.json)。采用因果退出／统一比较能力，配方经济门槛false，暂停并保留负结果。两个实际、独立、比较、根任务均实际closed0；初次import启动exit1保留，后修环境；唯一新1case、原金融循环和费用守卫未改。条件归因不是现金流，单位与availability没有获认证。

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

- 最新实际容量扫描：项目＋整个D盘WSL VHD **19,435,050,907B**，结束于 **2026-10-02 21:16:28.859933 UTC**；预留370MB，原守卫OK。主体333,111,127B及小验收工件在扫描后写入，非当前瞬时盘量。窗口复用此实际时刻，未新增可选全盘扫描；共享5GB／swap0／GPU0／OOM0保持。
- 新RSI2 122/90编排进程峰值 RAM **626,372,608 / 526,163,968B**，独立审计 **409,174,016B**；共享 cgroup 历史峰值 **3,236,868,096B**，硬上限 **4,999,999,488B**，swap 0、GPU 0、OOM 0。总盘上限 40GB/32GB 预警/36GB 停新增不变。
- [本机任务窗口](http://localhost:8765/)显示实际任务状态与测量时间；不造未知百分比。公开采集保持原来源，未因历史研究重启或合并健康时间。
- 当前已核对远程HEAD为 `1ae03efa853934e645ce71386417de301bcaa95e`，D032两完整新账户／独立／经济负结果／根验收、协议与文档已推送；[远程一致凭证](../reports/GITHUB_CARRY_PAST_FUNDING_EXIT_SYNC_VERIFIED_20261003_V1.json)。此前[D031同步](../reports/GITHUB_CARRY_90D_SYNC_VERIFIED_20261003_V1.json)及全部旧同步凭证保留。本行与后验同步凭证推送后本机追加，在下一个正常模块checkpoint纳入Git，不改冻结科研证据。
- 固定90日外推已完成并根验收。保留首轮3CASH后exit1和独立初次IPC失败；只修signal-close过去信息视图、针对新增边界复测，旧绿测试及旧账户未重跑。详见D014–D016。
- 当前步骤：D033来源／一新增边界case／三个547日账户／独立V3／根验收均实际完成；完整项目目标继续，源码／文档已闭合，正在模块推送。下一D034补齐原波动管理买入持有基准，先冻结再运行；非已执行结果。

**NO_QUALIFIED_CANDIDATE。** 不消费 locked historical test、不使用真钱/账户密钥/付费服务、不启用 GPU。已见窗口和当前历史 proxy 不产生未来竞争资格。

原状态的完整字节保存在 [本版之前的状态](archive/RESEARCH_STATUS_PRE_INVESTMENT_COMPARISON_20261002.md)；科研选择只追加 [决策日志](RESEARCH_DECISION_LOG.md)，实际运行只追加 `reports/experiment_registry.jsonl`。
