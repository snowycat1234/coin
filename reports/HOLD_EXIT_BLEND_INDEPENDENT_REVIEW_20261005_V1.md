# D073 固定半 HOLD／半 EXIT10：独立复核

日期：2026-10-05。结论：**4 个新混合账户、12 个保存控制账户及 12 组金额差额通过核账；固定 50/50 目标混合在四个已声明情景下未被同池控制同时在净收益、实际波动和分钟 MDD 支配，符合事前“保留研究挑战者”标准。它比 HOLD8 少赚钱且成本更高，但波动/回撤更低；比纯 EXIT10 多赚钱，也承担更高风险。无 alpha、原生成交或投资晋级。**

## 复核范围与独立性

本复核者是新测试 `tests/test_hold_donchian_blend.py` 的作者，也编写了轻量金额 helper，不能把本报告称为该测试的作者独立复核。新人工合成用例真实 1 项通过；它核独立窗口状态、逐组件过去协方差缩减后的固定混合、未用预算保留现金、缺失/成员退出/恢复、排序和未来扰动，不替代实际账本。

金额核对是另外的标准库 JSON/Decimal 实现：逐笔累加保存交易的已实现损益/手续费/执行损失、事件资金费和逐币末持仓损益，核 16 个账户 gross/net/完整资本 NAV，再核 12 组配对金额差及保存风险字段。没有调用生产账户或经济 measures 实现金额运算。实际 half targets、raw targets、过去协方差、因果与有序映射由已闭合独立 financial 和 root diagnostic 核 parquet；**轻量 helper 只核 JSON 金额/目标 meta，不再次独立重算 parquet 信号或风险序列**。

父任务唯一 bounded/progress 运行 helper，输出仅 STATE。本轮复核未新增运行、市场回放、训练、API、采集或 Git 查询，只读闭合工件并新增本报告。

## 实际完成的变化

新正常 thin adapter 复用同一有序 BTCUSDT/ETHUSDT 的两个组件：恒定多头 HOLD10/EQUAL，及 EXIT10/REENTRY20/ACTIVE_EQUAL。各组件先按其正常 past30 协方差预算缩减，然后 `target=.5*HOLD_target+.5*EXIT10_target`；raw 也以固定半权相加。没有再对混合 raw 做一次风险缩放、没有权重搜索、没有把执行后的混合持仓当成组件信号状态。择时组件 flat 时，其半份预算保留现金。

混合目标进入**一个共享账户**，不是两笔独立满资本账户的 NAV 平均。每日组件与组合 targets 经实际新金融核验；四情景目标与保存组件的 exact halves 经 root diagnostic 核对。正常账户、金额会计和费率语义不改。

评价窗口为 **2024-09-01 00:00 UTC 至 2025-07-01 00:00 UTC（右开）303 日**；每账户 436320 分钟。固定完整投入及预留资本 10000USDT、单币 abs.3/组合 gross.6、逐仓1x、每日信号/分钟成交与 mark/事件资金费。四情景使用原 BASE27/STRESS43 与 F/P 两种未认证资金费解释。16 个账户完整日历、正常付费末现金，逐币数量/保证金/负债/未实现损益为零；没有删库存、免费强平、资本重复占用或事后缩旧 NAV。

HOLD10 旧协议没有 `strategy_rules`；旧 10% 依据 hash-bound 实际 `target_meta.rules`，不捏造协议字段。新混合 meta 固定权重/组件身份/10% 组件预算/after-component-risk/非 NAV 平均均核对。保存旧源由已闭合 root diagnostic 对当前未变字节或接受提交的精确 Git 字节解析；本 helper 核保存协议/报告 SHA，未自行再获取旧 Git blob。

## 净收益、成本与风险结果

F/P 分别是 RAW_AS_FRACTION/RAW_AS_PERCENT，仍 UNKNOWN，不能按较高收益选单位。净收益为 303 日完整资本 USDT；波动为实际日收益年化描述，MDD 为完整分钟 NAV。

| 情景 | 混合净收益 | 相对 HOLD8 净增量 | 实际波动 | 分钟 MDD | 成交换手/完整资本 | 未被同池控制支配 |
|---|---:|---:|---:|---:|---:|---|
| BASE27/F | 526.197094 | -14.895250 | 8.042965% | 7.016190% | 2.598586 | 是 |
| BASE27/P | 632.031335 | -0.692740 | 8.047334% | 6.747659% | 2.614717 | 是 |
| STRESS43/F | 505.204009 | -21.723601 | 8.043487% | 7.062605% | 2.595989 | 是 |
| STRESS43/P | 610.814170 | -7.606339 | 8.047842% | 6.794352% | 2.612095 | 是 |

BASE27/F 的独立金额桥：

`667.193581 gross −14.292223 fee −20.789115 execution −105.915149 funding =526.197094 net`。

相对 HOLD8：

`+10.701253 gross −4.704807 fee −6.843362 execution −14.048334 funding =−14.895250 net`。

四情景混合毛收益均高于 HOLD8 约 10.64–11.07USDT，新增手续费/执行成本约 11.55–18.48USDT；F 下额外资金费约 14.00–14.05USDT，P 下约 0.141–0.142USDT，因此**没有形成净收益优势**。相对 HOLD8，实际波动下降约 0.346–0.348 个百分点、分钟回撤下降约 2.04–2.08 个百分点，换手增加约 0.854–0.861×完整初始资本成交名义额。

BASE27/F 相对纯 EXIT10：净收益增加 154.859128USDT、波动增加约 0.9445 个百分点、MDD 增加约 2.1660 个百分点；相对 HOLD10：净收益少 144.433603USDT、波动低约 2.4466 个百分点、MDD 低约 4.2134 个百分点。相同资产/caps 不能使实际风险自动相同，所有配对仍标 `actual_risk_matched=False`。

BASE27/F 混合平均/峰值 gross 为 14.7854%/27.3573%，net 与 gross 相同；平均/峰值逐仓抵押物/初始资本为 14.6511%/25.6301%。这不是未来风险保证，盘中跳空/原生清算仍受数据与规则边界限制。

独立 HOLD10/EXIT10 账户净收益的算术平均为 520.984332USDT；实际共享混合账户为 526.197094USDT，多 5.212762USDT。四情景差额约 5.21–5.94USDT，证明本工件不是账户曲线平均；订单阈值、资金竞争与实际复利路径各贡献尚未单独分离，不能把这点差额称为独立 alpha。

## 事前保留标准

协议规定：准确账本后，仅当未被已有同池控制在净收益、实际波动与 MDD 三项同时支配，才保留混合挑战者；不晋级 alpha/APR。root diagnostic 与 Decimal helper 按原 cash `1e-7`、risk `1e-10` 容差重算同一支配条件，12 配对均未出现支配，`all_scenarios_undominated_by_existing_same_pool_controls=True`。本复核没有追加更难或更松的事后成功门槛。

“未被支配”只表示这组已见样本中的描述性取舍，**不表示三个指标全面改善、统计显著、Pareto 前沿稳健或可投**。净收益较 HOLD8 的负结果完整保留。

## 工件、任务与资源

| 角色 | 实际 task | 闭合结果 |
|---|---|---|
| 新混合市场 | `9104f8154f7743738048a990ed1dc309` | completed/exit0，4 完整账户 |
| 新完整金融核验 | `b52fc6ec92f1496cbe038231e59b5726` | completed/exit0，4 调用，blend targets/meta verified |
| 保存比较诊断 | `38d5f31326874aefbeea707588390263` | completed/exit0，16 rows/12 pairs |
| 独立 Decimal JSON 核账 | `a7d479b3f23a4a8d8a316bf79d72a865` | 已直接读取任务记录：completed/exit0 |

helper 另核三组保存控制的市场/金融真实 completed/exit0：HOLD10 `1a2691bfe09d4a64834d2c4b5b434a31`/`6cfb867cfc2949e69da41d99d21f5dc4`，HOLD8 `450cb87ea39b482cb04bbbee12abce95`/`bd07a4eedfb44b56ab8f42a6d0344934`，EXIT10_TWO `9a93f1eab8d841bc8a0a42d2d8aa6ee7`/`05f1bb012976413db29c703a58c78b89`。旧源接受提交分别 `55798a1`、`e9608b808478d8f433d6b0b7230396abf7449b21`、`f1d19a6ca9b071b375b3bfa943a47213facf0062`。

新金融最大 cash 误差约 `4.37e-11`USDT、ratio 误差 `1.39e-14`。市场耗时 307.88s，进程峰值 RSS420532224 字节、共享组采样峰值1290727424 字节、市场工件161863420 字节；共享采样不是精确全时峰值，全模块容量由 root 另行结算。无模型/GPU/额外市场回放或发单权限。

| 工件 | SHA256 |
|---|---|
| protocols/HOLD_EXIT_BLEND_20261005_V1.json | `bf23a2cedf75fd8f21d9a401f955d0b9f777a1759bb12ff31130ad65d50513dd` |
| reports/fast_research/HOLD_EXIT_BLEND_20261005_V1.json | `37c79336605489be7d9d41c145e3077f87536fc5ebed670c9bb50702facc7cea` |
| reports/fast_research/HOLD_EXIT_BLEND_20261005_V1_FINANCIAL.json | `f87bdec267e586a78a6d918355bc34c5aa32b0f713bdddb31071a6ce399dfbd6` |
| reports/fast_research/HOLD_EXIT_BLEND_20261005_V1_DIAGNOSTIC.json | `e407def7c2c6a4f12a8a2972fc5459a17ed14596cc5b97b4f2bb8ce1d41ef124` |
| reports/fast_research/HOLD_EXIT_BLEND_20261005_V1_SYNTHETIC.json | `8750284cdfe8302ca8ab048995155f475a5f4e435980719d2122b917bc0ac145` |
| STATE/d073-independent-review-20261005-v1/RESULT.json | `d94695cbad6dbaa4c9a329b49d38b29164d3050290fe2c59d39001a891ef3bb1` |
| .cache/d073_independent_review.py | `cc4d3df6e6a1bf26ca98c8b4a2e7ad6950e5a2a56cd45b72cac7d65c6aff7e73` |

独立核账实际入口：`scripts/with_task_progress.sh --title 'D073独立混合账户Decimal核账' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B /mnt/d/codex/coin/.cache/d073_independent_review.py --output /home/xflops/coin-state/d073-independent-review-20261005-v1/RESULT.json`。输出仅写新文件；复现应另选 STATE 路径，不能覆盖本工件。本复核未再执行。

## 采用与下一步边界

本固定开发比较未发现新的金额/目标接线 blocker。保留混合作为防守挑战者，HOLD8 为收益/风险参照、HOLD10 为原控制、EXIT10 为防守控制；候选 `NONE`，投资 `CASH`，长期 APR `NOT_EVALUABLE`。

下一步有限地对保存混合/HOLD8 日收益与风险做一次稳定性及配对不确定性诊断，核防守效果是否集中于少数月份/下跌期，**不重新搜索权重、不新增市场回放、不把已见历史改名 unseen**。这是下一交接点，尚未运行。

Binance 行情/资金费配 Bybit 成本仍是跨场所代理；资金费单位/可得性、历史 fee zone、BBO/冲击、原生 filter/维持保证金/盘中清算仍 UNKNOWN。四情景与 12 配对没有增加独立历史长度，303 日年化描述不等于稳定长期 APR；收益、风险取舍及保存挑战者不授权真钱或证明可执行优势。
