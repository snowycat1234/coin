# D072 两币 EXIT10：独立金额与比较范围复核

日期：2026-10-05。结论：**4 个新两币账户、12 个保存控制账户及 12 组配对金额桥通过。两币择时减少回撤与实际波动，但比同池 HOLD 少赚钱且交易成本更高；扩成十币后收益增加，同时实际波动和回撤增加。保留各研究角色，投资候选仍 NONE、资金仍 CASH。**

## 范围与独立性

本复核者编写了 `tests/test_donchian_two_asset_reference.py`，也编写本轮独立金额 helper；因此不是该合成测试的独立作者。新测试真实 1 项通过，不能代替真实金融账本。**金额核对使用单独标准库 JSON/Decimal 实现**，从已保存交易/资金费逐笔累加已实现价格损益、手续费、执行损失与资金费，计入终末持仓损益，再与 gross、net、完整资本 NAV 核对；没有调用生产账户或经济 measures 作为金额计算实现。

该轻量核对不读取 parquet 重算信号或风险。共同 BTC/ETH 信号状态、过去协方差/有序映射与独立目标/分钟资金流水依赖已闭合 root diagnostic 和独立 financial runner，本报告明确区分这些来源。本复核未额外运行测试、市场、模型、API、Git 或采集；只读闭合证据并写本报告。父任务唯一 bounded/progress 运行 helper，输出只在 STATE。

## 实际变更与固定口径

活动策略仍为 `COIN_JESSE_DONCHIAN20_SMA200_EXIT10_1D_USDM_CONFIGURED_POOL_VARIANT`：初次及恢复入场 prior20 high/SMA200、exit prior10 low、reentry20、long-flat、ACTIVE_EQUAL；没有改变信号引擎或退出/持仓规则。独立金融入口仅解除该策略的写死十币门槛，实际正常两币目标与直接窗口参考经必要合成反例和实际账户核验。当前 financial 源 SHA 为 `f345f270332cc48230d2a6ad616e0080267ceb3170c2cdf9e14951898f107832`。

时间为 **2024-09-01 00:00 UTC 至 2025-07-01 00:00 UTC，右开 303 日**。每个账户完整 10000USDT 投入及预留资本，共享逐仓1x、单币 abs.3/组合 gross.6；按分钟成交/mark、事件资金费，日线决策。比较账户各自独立，不能将它们的 NAV 或利润相加当组合。所有 16 个账户均有 436320 分钟/303 日，末数量、逐仓抵押物、负债、未实现损益为零，并通过正常付费末平仓；无免费填平或删库存。

四个比较角色各保留 BASE27/STRESS43 × RAW_AS_FRACTION/RAW_AS_PERCENT：

- `EXIT10_TWO`：本轮实际新两币账户，预算 10%。
- `HOLD10_TWO`：保存两币恒定多头 10% 控制。
- `HOLD8_TWO`：保存两币恒定多头 8% 风险参照。
- `EXIT10_TEN`：保存同一 EXIT10/REENTRY20/ACTIVE_EQUAL 十币账户。

HOLD10 旧协议没有 `strategy_rules` 字段；旧 `.10` 由 hash-bound 实际 target meta 验证，不捏造协议字段。各角色实际 meta 规则与 covariance 顺序按 N=2/10 分别核对。共同 BTC/ETH 的 long/flat 信号状态在两池相同，由闭合诊断核 targets 证明；仓位大小可因池、活跃预算、协方差与共享资金竞争而不同。

## 钱赚亏在哪里

净损益均为 303 日完整资本口径 USDT。F/P 是尚未认证的资金费解释，不得按净收益选择单位。实际波动为日收益年化描述，DD 为分钟 NAV 最大回撤。

| 情景 | EXIT10_TWO 净 | HOLD10_TWO 净 | HOLD8_TWO 净 | EXIT10_TEN 净 |
|---|---:|---:|---:|---:|
| BASE27/F | 371.337966 | 670.630697 | 541.092344 | 497.163018 |
| BASE27/P | 466.220011 | 786.361956 | 632.724074 | 565.755447 |
| STRESS43/F | 346.568339 | 652.765678 | 526.927610 | 463.512106 |
| STRESS43/P | 441.436787 | 768.305939 | 618.420508 | 531.881125 |

BASE27/F 的独立交易/资金费桥：

| 角色 | gross | fee | execution | signed funding | net |
|---|---:|---:|---:|---:|---:|
| EXIT10_TWO | 508.273492 | 16.816824 | 24.461160 | -95.657542 | 371.337966 |
| HOLD10_TWO | 816.477509 | 12.051802 | 17.530417 | -116.264594 | 670.630697 |
| HOLD8_TWO | 656.492328 | 9.587416 | 13.945753 | -91.866815 | 541.092344 |
| EXIT10_TEN | 625.968449 | 23.526900 | 34.221346 | -71.057185 | 497.163018 |

每行满足 `net = gross − fee − execution + signed funding`；执行损失已包含在实际 fill，gross 是相同数量的 mid 价格诊断，拆报告不重复扣款。末未实现损益虽然本次为零，核账依然逐币计算。

三类配对必须分开解释：

1. **同池择时 vs HOLD10**：四情景净收益少 299.29–326.87USDT；毛价格收益少约 308.20–308.64USDT，成本更多，F 下少付资金费约 20.61USDT 仍不足补回。这否定该已测配方在此历史窗口的同预算净收益优势，不否定全部择时能力。
2. **同池择时 vs HOLD8**：四情景净收益少 166.50–180.36USDT。BASE27/F 差额为 `−148.218836 gross −7.229408 fee −10.515407 execution −3.790726 funding =−169.754378 net`。亏差主要是毛价格收益与额外交易成本，而不是宣称低费率可自动修复。两方案预算不同，实测风险仍未完全匹配。
3. **固定策略扩池 TWO→TEN**：十币四情景净收益多 90.44–125.83USDT。BASE27/F 增量 `+117.694956 gross −6.710076 fee −9.760186 execution +24.600357 funding =+125.825051 net`。两池同策略/相同 caps，不代表实际风险一致；不能把全部收益差叫分散收益或新 alpha。

## 实际风险、暴露与成本

BASE27/F 的完整账户观测：

| 角色 | 实际日波动年化 | 分钟 DD | 成交换手/完整资本 | 平均/峰值 gross | 平均/峰值抵押物/初始资本 |
|---|---:|---:|---:|---:|---:|
| EXIT10_TWO | 7.0985% | 4.8502% | 3.05760 | 11.4637%/29.7199% | 11.0282%/28.4387% |
| HOLD10_TWO | 10.4896% | 11.2296% | 2.19124 | 18.1307%/27.3856% | 17.8665%/26.3765% |
| HOLD8_TWO | 8.3902% | 9.0635% | 1.74317 | 14.4975%/21.9831% | 14.1391%/20.8334% |
| EXIT10_TEN | 8.3624% | 7.4271% | 4.27762 | 9.0878%/23.4280% | 9.2182%/23.7665% |

以上均 long-flat，net=gross。两币择时四情景波动约 7.0984%–7.1039%、DD4.7868%–4.8892%；防守效果存在，但净收益更低、换手较 HOLD8 高约 1.31 倍完整资本名义额。十币同配方波动约 8.3624%–8.3804%、DD7.3151%–7.5987%，更高收益伴随更高风险；平均 gross 更低也不能单凭暴露平均值推断更安全。峰值瞬时风险与原生盘中清算仍受观察范围限制。

过去 covariance 目标是缩减器，不保证未来实际波动等于预算。不能事后缩放曲线形成风险匹配业绩。本次 12 组诊断均显式 `actual_risk_matched=False`。

## 真实闭合与可追踪来源

新市场 task `9a93f1eab8d841bc8a0a42d2d8aa6ee7`、新金融 `05f1bb012976413db29c703a58c78b89`、诊断 `1f3ddbdf29774c3987e13c0b556ee78a` 均 closed0。独立金额 task **`117dd3cfe048470bae4558e3bcd34380`** 实际 completed/exit0，已直接读对应任务记录。保存 HOLD10 市场/金融 `1a2691bfe09d4a64834d2c4b5b434a31`/`6cfb867cfc2949e69da41d99d21f5dc4`，HOLD8 `450cb87ea39b482cb04bbbee12abce95`/`bd07a4eedfb44b56ab8f42a6d0344934`，EXIT10_TEN `5811d4e61b6048a1a23be92686f3f95c`/`2a6d808fe9a2408fb4c809abf609e6a2` 的真实 closed0 由 helper 检查。

新金融核验 4 调用、完整 1212 账户日，最大 cash 误差约 `2.18e-11` USDT、ratio 误差 `2.38e-14`，不能把累计账户日称 1212 个独立市场日。新市场耗时 283.99s、进程峰值 RSS411389952 字节、共享组采样峰值1220890624 字节、市场工件75379092 字节；这里不是全模块最终容量结算，root 另行核资源。

保存来源接受提交按协议为 HOLD10 `55798a1`、HOLD8 `e9608b808478d8f433d6b0b7230396abf7449b21`、EXIT10_TEN `33fa0de74cc9fb9d86420d2f1ad0d6d48b49d998`。root diagnostic 对旧协议未变源核当前 SHA、已变源核该提交精确 Git 字节；helper 核保存协议/市场/金融 SHA，本复核没有重新获取 Git blob。历史代码不成为当前多层运行依赖，旧结果未覆盖。

| 工件 | SHA256 |
|---|---|
| protocols/DONCHIAN_TWO_20261005_V1.json | `4a3525f9ce33ef851859307e906a14a6b31e0559a360166f019f814dafa3ad46` |
| reports/fast_research/DONCHIAN_TWO_20261005_V1.json | `9e1cefaae23fc0ec184190d914d2f704ff628bfa643d1a834e725d6d531826a2` |
| reports/fast_research/DONCHIAN_TWO_20261005_V1_FINANCIAL.json | `29ca03806465fcfbeafdb1837ac36d3ffad2c987e421e8063a10808761651edf` |
| reports/fast_research/DONCHIAN_TWO_20261005_V1_DIAGNOSTIC.json | `4a8089e53378df6883243ff7c5d84943e337202d5e98f25e377d337d6aeb3717` |
| reports/fast_research/DONCHIAN_TWO_20261005_V1_SYNTHETIC.json | `116412844b1a66d95ff6c75515a395679939cb25bb950b626442ba70cc8b1e29` |
| STATE/d072-independent-review-20261005-v1/RESULT.json | `1e1a9b4aae89876239d7a12d4a22dce16e6d99345fe78c18404d339ce1aae2c5` |
| .cache/d072_independent_review.py | `fed779556f2fa44f07b884c96c19c3e6ee8290cfa9f2770cb32fd8aebe3ad68f` |

独立核账唯一实际命令为 `scripts/with_task_progress.sh --title 'D072独立16账户Decimal核账' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B /mnt/d/codex/coin/.cache/d072_independent_review.py --output /home/xflops/coin-state/d072-independent-review-20261005-v1/RESULT.json`。工具要求新 STATE 文件，复现使用新的输出路径，不覆盖此证据；本报告未再运行。

## 采用范围与下一步

本固定开发比较无新的金额/接线 blocker。保留两币 EXIT10 为防守控制、十币 EXIT10 为挑战者、HOLD8 为风险参照、HOLD10 为原控制，不因支持择时而强行采用。长期投资候选 `NONE`，资金 `CASH`。

下一项为有限、事前固定 **50/50 恒定 beta 与择时目标混合**，同 BTC/ETH、一个共享账户、原费用/风险/数据口径，检验是否保留部分价格收益并减少回撤；不相加现有 NAV、不搜索组合权重。它只是下一项假设，**尚未开始**，没有声称可保持收益或改善风险。

已查看 303 日仍为开发筛选。Binance 来源配 Bybit 成本为跨场所代理；历史费区、实际盘口/冲击、资金费单位和发布时间、native filters/维持保证金/盘中清算仍 UNKNOWN。四情景与 12 配对不是额外独立市场历史，年化描述不是稳定长期 APR，未证明 alpha、原生 Bybit 可执行性或真钱资格。
