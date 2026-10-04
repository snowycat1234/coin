# D071 HOLD 8% 过去风险预算：独立复核

日期：2026-10-05。复核结论：**完整新账户和金额桥通过；8% 预算降低了收益、暴露、回撤与换手，保留为风险参照。未证明 alpha 或投资资格，不替代 10% 控制，也不把十币 EXIT10 描述性参照当成同池、严格匹配风险的因果对照。**

## 范围与独立性

接手 HEAD 由父任务提供为 `d82ac37415d099cd8d408424a81505bc85c0ca66`。本复核只读当前活动接线、已闭合报告/JSON/任务记录，未调用 Git、市场回放、API、训练或新增测试。仅写本报告；辅助工具在运行前草拟于 `.cache/d071_independent_review.py`，由父任务唯一通过既有 bounded/progress 运行，输出仅在 STATE。

复核者同时是 `tests/test_hold_risk_budget.py` 的作者；该反例不算作者独立复核。**金额核对是另外的标准库 Decimal 实现**：逐笔累加交易已实现损益、费用、执行损失和资金费，加入末持仓损益，核对八账户 gross/net/NAV，再核四个配对增量。没有调用生产账户、风险核函数或经济 measures 作为金额计算实现。目标与完整分钟资金流水的另一来源核验由已闭合 financial runner 提供；本轻量工具不重放市场、不读取 parquet 重算风险序列。

## 实际接线与可比范围

评价日期为 **2024-09-01 00:00 UTC 至 2025-07-01 00:00 UTC（右开）**，303 日、每账户 436320 分钟。每个比较账户各自使用完整投入及预留资本 10000USDT，BTCUSDT/ETHUSDT 同一共享钱包；不是相加多个满资本账户，也没有逐月清零或拼接独立账户。

唯一新配方是恒定多头 HOLD/EQUAL 的 past30 协方差缩减预算由 10%→8%。`public_sma_perpetual.fixed_targets`、HOLD thin adapter、活动 runner 和独立 `target_reference` 均传入事前参数；非法 0/NaN/>10% 在入口拒绝。默认 10% 保持，原规则字典没有被修改。固定 abs.3/gross.6/逐仓1x、已选池、数据、费用、资金费双解释、终末平仓尝试与完整资本不变，没有事后缩放旧 NAV 或风险预算网格。

旧 D064 协议**没有** `strategy_rules` 字段；不能捏造旧协议字段绑定。旧 10% 规则证据是保存、绑定哈希的实际 `target_meta.rules.annual_volatility_target=.10`。新协议及实际 target meta 为 `.08`；目标与协方差资产顺序、raw 信号都保持。诊断显示 303 决策日/606 目标行发生变化。

账户 contract 中 `annual_vol_target` 仍是旧外部 controller 默认说明 `0.10_EXTERNAL_SIGNED_COVARIANCE_CONTROLLER_NOT_ENFORCED_HERE`。该账户本身不执行协方差预算；本次真实 8% 接线依据上述 protocol→runner→target/meta→独立目标核验。不得把这段账户说明当成此次实际 10% 或 8% 波动保证。

旧控制来源依 D071 协议中的接受提交 `55798a1` 解析。已闭合 root diagnostic 对未变源核当前字节，对已变源核接受提交中的精确 Git 字节；本复核核保存协议/报告 SHA 与这条诊断，**没有独立再次获取 Git blob**，没有强迫旧源码成为当前运行依赖。

## 真实金额与风险结果

F 表示 RAW_AS_FRACTION；P 表示 RAW_AS_PERCENT。两种资金费单位均未认证，不能按结果挑一个。下表收益为 303 日完整资本净损益；波动为实际日收益年化描述，MDD 为完整分钟 NAV 回撤，换手为成交名义额/初始完整资本。

| 情景 | HOLD10 净损益 USDT | HOLD8 净损益 USDT | 净增量 USDT | 实际波动 10→8 | 分钟 MDD 10→8 | 换手 10→8 |
|---|---:|---:|---:|---:|---:|---:|
| BASE27/F | 670.630697 | 541.092344 | -129.538353 | 10.4896%→8.3902% | 11.2296%→9.0635% | 2.19124→1.74317 |
| BASE27/P | 786.361956 | 632.724074 | -153.637882 | 10.4941%→8.3938% | 10.9495%→8.8317% | 2.20475→1.75399 |
| STRESS43/F | 652.765678 | 526.927610 | -125.838067 | 10.4912%→8.3914% | 11.2733%→9.0993% | 2.18939→1.74198 |
| STRESS43/P | 768.305939 | 618.420508 | -149.885430 | 10.4957%→8.3950% | 10.9933%→8.8677% | 2.20289→1.75279 |

四个新账户均完成实际日历并正常付费平仓至 CASH；旧控制四账户也完整且末现金。独立金额核对确认终末数量、逐仓余额、未付负债与未实现损益均为零，没有漏掉持仓，也没有免费强平。

BASE27/F 独立金额桥：

- HOLD10：`816.477509 gross −12.051802 fee −17.530417 execution −116.264594 funding =670.630697 net`。
- HOLD8：`656.492328 gross −9.587416 fee −13.945753 execution −91.866815 funding =541.092344 net`。
- 配对：`−159.985181 gross −(−2.464386 fee) −(−3.584664 execution) +24.397779 funding =−129.538353 net`。

全部四对净收益下降 125.84–153.64USDT，主要来自毛价格收益降低约 159.81–159.99USDT。较少成交节约费用及执行成本约 6.05–9.68USDT；较小持仓降低资金费支出，在 F 解释下约节约 24.37–24.40USDT，在 P 下约 0.246USDT，均不足补回毛收益。不能把更低成本单独解释成经济收益提升。

BASE27/F 平均/峰值 gross 为 18.1307%/27.3856%→14.4975%/21.9831%；HOLD 为正仓，net 与 gross 相同。平均/峰值逐仓抵押物占完整初始资本为 17.8665%/26.3765%→14.1391%/20.8334%。四情景实际波动下降约 2.10 个百分点、MDD 下降约 2.12–2.17 个百分点。**过去协方差的 8% 目标不是实际波动硬上限**；实测仍为约 8.39%。

十币 EXIT10 仅作不同池、不同择时策略的描述性参照：四情景净损益 463.51–565.76USDT，实际波动 8.3624%–8.3804%，分钟 MDD 7.3151%–7.5987%，换手 4.2710–4.2943。HOLD8 四个情景分别比该参照多约 43.93–86.54USDT，回撤也更高；波动接近但不完全匹配，且资产池和信号不同。不能据此证明择时 alpha 为负、HOLD 全面优胜，或将差额全部归因于风险预算。

## 工件与真实闭合

| 角色 | 实际 task ID | 结果 |
|---|---|---|
| 新 HOLD8 市场 | `450cb87ea39b482cb04bbbee12abce95` | completed/exit0；4 完整账户 |
| 新独立金融核验 | `bd07a4eedfb44b56ab8f42a6d0344934` | completed/exit0；4 金融核验调用 |
| 保存 HOLD10 市场 | `1a2691bfe09d4a64834d2c4b5b434a31` | 保存 completed/exit0 |
| 保存 HOLD10 金融核验 | `6cfb867cfc2949e69da41d99d21f5dc4` | 保存 completed/exit0 |
| 保存账本诊断 | `9dce50b3399c4f23b82e469598b01d20` | completed/exit0 |
| 本轮独立 Decimal JSON 核对 | `592fb8b276ae48c58bf2cfb63b818ca0` | 已直接读取任务记录：completed/exit0 |

单个新合成反例实际通过，runner 总耗时 43.63s；不以这条目标能力验证替代真实账户。新市场报告耗时 301.71s、进程峰值 RSS419717120 字节、共享组采样峰值1292685312 字节、工件161468590 字节；共享峰值为采样观察，不冒充精确全时峰值。未新增模型/GPU/API/交易权限。

| 工件 | SHA256 |
|---|---|
| protocols/HOLD_RISK8_20261005_V1.json | `20c5333fca52b9bcf9e4165f06cf86cc05b2da3dde9567ae54486acbf5697e03` |
| reports/fast_research/HOLD_RISK8_20261005_V1.json | `56fb6a04e3d342011173409b7f965edca61b4f2c9c5feb8fe3ad5c6bf7c6aafb` |
| reports/fast_research/HOLD_RISK8_20261005_V1_FINANCIAL.json | `1d0d3a6d4f00cec3f8a36cc98c3d04029cf07c8cda49ddd51f21038c27c05bea` |
| reports/fast_research/HOLD_RISK8_20261005_V1_DIAGNOSTIC.json | `f68e140e34285a9a1bec739cb13f0acf4c5e3ac644dc043c75ec162b48ace9e5` |
| reports/fast_research/HOLD_RISK8_20261005_V1_SYNTHETIC.json | `020d0aa9d9be0ba16406b547863f42dddac689691da19e6daace4433ad294844` |
| STATE/d071-independent-review-20261005-v1/RESULT.json | `16e73bcb3c21764c3c48a14aac62bcfc3c7498175b4ad9784545ef77a7010056` |
| .cache/d071_independent_review.py | `dc39988a9abfea809117db39b2fa9c43ba5c5ea5bf0b5c9d36b05f0f0f28dca8` |

独立工具仅一次运行的可复现入口：`scripts/with_task_progress.sh --title 'D071独立Decimal金额复核' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B /mnt/d/codex/coin/.cache/d071_independent_review.py --output /home/xflops/coin-state/d071-independent-review-20261005-v1/RESULT.json`。输出为独立新文件，重复执行需新的 STATE 输出路径，不能覆盖本证据。本报告没有再次执行该命令。

## 采用范围与剩余限制

未发现阻止本固定开发对照解释的金额或风险接线 blocker。保留 HOLD8 为较低风险研究参照，保留 HOLD10 为原控制、EXIT10 为择时挑战者；投资候选仍 `NONE`、资金仍 `CASH`。下一步应利用此较接近实际波动的参照解释择时是否有价值及其回撤/成本来源，保持池和策略变化贡献分开，不继续风险预算搜参。

所有历史已见，仍为开发筛选；Binance 数据配 Bybit 成本是跨场所代理。资金费单位/发布时间、历史费区、原生数量过滤器、实际 BBO/冲击、维持保证金/盘中清算边界仍未认证。共同 caps 不等于相同实际风险，四种资金费/成本情景不是四条独立市场证据；303 日描述性年化不能作为稳定长期 APR 或真钱资格。
