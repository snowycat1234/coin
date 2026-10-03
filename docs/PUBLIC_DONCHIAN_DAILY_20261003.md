# D037：固定公开 Donchian 日线筛选（2026-10-03）

**当前 `NO_QUALIFIED_CANDIDATE`，长期净 APR 不可评价。** 三个已见历史窗口的独立账户、独立资金/因果核验、保存指标共同比较及根侧V2验收均实际closed0。本轮不是 unseen 验证、原生 Bybit 成交证明或投资采用；三个账户不拼接净值，也不把样本描述性 CAGR 当作长期净 APR。

## 主要发现与科研处置

固定日线 Donchian 在 547 日窗净赚 577.024120 USDT，但后来 122 日窗净亏 598.097288 USDT，90 日窗没有交易、全程现金。122 日的同净持仓数量 gross 为 **−558.338202 USDT**，全部费用、点差与滑点为 **39.759086 USDT**：主要瓶颈是这套固定入场/持有机制的价格损益，不能靠费用降低解释或消除负结果。90 日保留现金只证明该窗口没有触发可成交交易，不证明稳定 alpha。

保留官方日线来源、因果预热、薄 target adapter、共同分钟账户和核算能力；**暂停固定日线 Donchian 的投资采用及同配方扩展**。重开须有不同、过去可得且事前固定的因果入场机制，或预登记的真正未来同成本风险有效证据。不能通过调整 20/200、事后挑月份、降低成本或增加杠杆制造重开理由。

下一项确定固定公开 `SMACrossover50/200` 日线long-only，检验慢趋势状态能否改善gross稳定性。官方语义是fast>slow允许入场、fast<slow退出，相等保持当前状态，不强制当日发生交叉；原short/wholebalance不移植。该改变同时涉及入场/退出，不冒称纯入场消融；同属多头趋势，未证明独立alpha。复用现成日档与分钟输入，同资本/风险/36bp，零搜索。**该新策略尚未实施或运行**。

## 配方、数据角色与边界

- 原开源 `jesse-ai/example-strategies`，commit `7c91e0a37bf62165790120d730442e4f6eb00364`，MIT；复用原 Donchian class hooks 与官方非序列 channel 函数。20 日 channel 排除当前日，SMA200 含当前已完成日；固定 UTC 日线、只做多、0/.3 每币目标，不进行 HPO。[原始来源与许可证](../third_party/jesse_example_donchian/UPSTREAM.md)
- 官方 Binance Spot 月档 `1d`：2023-06-01..<2026-03-01，共 66 个币种月档、每币 1004 日、共 2008 行。评分前至少 200 连续已完成日，首次评分前来源提供 214 日；指标预热不建仓，每评分窗 fresh flat。`available_us=open_us+DAY` 仅为闭合代理，不认证交易所实际发布时间。[实际来源](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ACTUAL_20261003_V2.json)、[来源根绑定](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ROOT_BINDING_20261003_V1.json)
- 日线只产生信号。执行价格、过去 30 日/最少 20 日风险、前一分钟容量、lot 和终端估值继续使用各窗已接受的分钟来源。day close==decision 可用，下一分钟闭合后 +1µs 才执行；最后评分 minute=end−1minute，不使用 end 日线收盘生成信号。缺日/延迟使整个成对评分窗不可评价，晚期无效不回写早期意图。
- 每账户初始 10,000 USDT；原 10% 年波动目标、.3 单币/.6 gross cap 与执行机制不变。相同风险规则不代表相同实现波动或持续再平衡限额；122 日 BTC 被动标记最大权重约 31.2139%，保留原机制并披露。
- **Bybit 普通用户/VIP0 Spot 10bp/side，按收到资产扣费**（买入扣 base、卖出扣 USDT）；点差 8bp round trip，滑点 4bp/side，名义往返共 **36bp**。不是永续 5.5bp 费率。当前费用规则反事实应用于 Binance 历史代理数据，不认证 Bybit 历史账户费、行情、BBO、过滤器或成交容量。[费用标准](../protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json)
- 原分钟/native 金融循环和原 Jesse hooks 字节不改；新日线 adapter、私有 namespace 与来源目录薄适配接入旧共同 runner，不另写账户引擎。锁定历史、真实资金、账户密钥与 GPU 均未使用，模型拟合/HPO 为 0。

## 三个独立账户结果

金额单位 USDT；gross 是同实际净收到持仓数量的 gross shadow，不是另跑的无费用账户。各窗资本分别为 10,000，不将期间结果拼接。

| 完整 UTC 评分窗 | 天数 | Gross | Fee | Spread | Slippage | Net | 期间净收益 | 分钟 MDD | 实现年波动 | 原引擎期间 turnover | 成交 fills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024-01-01..<2025-07-01 | 547 | 658.594573 | 45.308748 | 18.130853 | 18.130853 | 577.024120 | +5.770241% | 13.378820% | 8.678012% | 4.333524 | 48 |
| 2025-08-01..<2025-12-01 | 122 | −558.338202 | 22.084555 | 8.837266 | 8.837266 | −598.097288 | −5.980973% | 9.345781% | 10.371579% | 2.233504 | 26 |
| 2025-12-01..<2026-03-01 | 90 | 0 | 0 | 0 | 0 | 0 | 0% | 0% | 0% | 0 | 0 |

547/122 日终端残余实际持仓市值分别为 1.157490/0.728489 USDT，保留标记估值，不能记作免费完全清仓；90 日完全现金。分钟 MDD 与原 daily MDD 是不同观测口径，all-event MDD 未认证。turnover 是原引擎期间累计字段，不是日均周转。`trade_count` 是 fills，不把 legacy `round_trip_count=0` 解释成没有完成卖出。

实际结果与字节身份：

| 窗口 | 小报告 / SHA256 | 实际 task |
|---|---|---|
| 547d | [ACTUAL](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_547D_ACTUAL_20261003_V1.json) / `f5fbd1a9c252074c5d84fcafc5928c608b33d12a22a2e9cd55d1336cbf655b7b` | `6b3d5481cd204d9898ef4a1b769badc0` |
| 122d | [ACTUAL](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_122D_ACTUAL_20261003_V1.json) / `acccf019dae603a9e38b19001596b249b8a6645544241aa565c10dbc540381b6` | `1cfa2d0376744b97bbaaefd3fce5d123` |
| 90d | [ACTUAL](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_90D_ACTUAL_20261003_V1.json) / `1d1414a235978b24bb3568ad7c36579c3b0a30f36049eb4a38cbe04564b8f656` | `f6af45e8578141d19bc762307c5af477` |

三份生成器报告均 `COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING`、1/1 完整，来源字节未变。此前未合格候选、旧负结果和旧账户不重放。

## 运行与资源证据

| 角色 | 报告耗时 | 主进程峰值 RSS | 实际 owned bytes |
|---|---:|---:|---:|
| 日线来源 | 245.8676s | 131,182,592 | 1,112,774 |
| 唯一新增贯穿 case | 113.0829s | 191,320,064 | 2,110,108 |
| 547d | 80.2114s | 2,019,340,288 | 261,617,010 |
| 122d | 71.2566s | 644,255,744 | 68,823,202 |
| 90d | 71.7615s | 540,950,528 | 50,379,658 |

以上五角色已记录工件合计 **384,042,752B**；该数只统计五角色实际报告工件；最终七个专属STATE目录合计 384046803B≤450MB，由根V2逐目录核验。共享 WSL RAM 5GB、swap0、GPU0；表中 RSS 是各主进程峰值，不是共享同时总峰值。

三次实际磁盘扫描结束时刻/项目+VHD值（不重新扫描、也不把旧值标为当前）：

- 122d：2026-10-03 08:02:56.708498+08:00，20,179,966,734B。
- 547d：2026-10-03 08:03:25.189572+08:00，20,247,208,738B。
- 90d：2026-10-03 08:05:06.540887+08:00，20,515,858,910B；这是上述经济运行中最后一次实际扫描，后续工件不在该旧值内。

## 验收边界与保留的失败

[唯一新增日线/native 贯穿 case](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_BOUNDARY_TINY_20261003_V1.json) 实际 1 case、0 errors/failures/skips，task `20591a88df7348a59082bc6b20a562f9`，报告 SHA256 `4ccd151019c3942b846c89e1d4e2ad06ac2ccd28d483672e265fe0acbcfbc1bf`。覆盖 Jan2024 日期路由、200 连续日、UTC日界可用性、future poison、缺日/延迟、NULL key、warmup 不持仓、原 hook 和真实 native→共同账本；不重跑旧绿色套件。

两个实际来源启动失败均保留：

1. [selector V1](../reports/fast_research/PUBLIC_DAILY_OFFICIAL_SOURCE_SELECTOR_SMOKE_20261003_V1.json)，SHA `466370ceae3cd5386e75779c8ff510c86c639bbb40b25178cb289fc1fbe88de2`，task `b1e1a0c167714c2f98d82fe827ddb726`：`NameError: hashlib`，无网络/行情行。新薄版只修私有 namespace 缺失绑定。
2. [formal startup V1](archive/PUBLIC_DAILY_OFFICIAL_SOURCE_FORMAL_STARTUP_FAILURE_20261003_V1.json)，SHA `b678b5d6fbb0e1b792a8a5a25b46fcc60d63efcc534ba37bbc2e549c232d174e`，session67831/chunk5c48cf/exit1、task `169b4a609efd4398b1ca60d36d79875f`：原 SHA 函数要求 Path，收到 `__file__` 字符串。STATE 已创建但 0 文件，无 RUN_BINDING/registry/network/数据行；新薄版仅 normalize Path 并使用新独占目录，原失败目录保留。

## 实际验收与共同经济判断

[三账户独立审计](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json) task9d84239e5f7143c19facb4818c02accf，session81108/chunkdc1406真实exit0；报告SHA f49cc375…、RUN_BINDING158cf605…，759日/1,092,960分钟/25月、66日档与58条已接受分钟来源引用。新核算耗时64.8722s、峰RSS983,588,864B，原账户、ZIP/旧QA不重放。Sparse Decimal仅核每笔收到资产结算，最大金额误差1.7648563e−11 USDT；分钟/日/月验收复用原NumPy断言，不宣称全事件MDD或逐时Decimal收益比率。原独立target文件保留生成时UNRUN注释，真实调用以该实际PASS为准。[实际退出与依赖绑定](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_ACTUAL_EXIT_20261003_V1.json)记录全部原字节。

[保存摘要共同比较](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_ECONOMIC_COMPARISON_20261003_V1.json)真实exit0，未再读行情数组或重跑旧金融循环。复用既有net≥、实现vol≤、分钟MDD≤且至少一项严格的描述性Pareto规则：547日hybrid支配daily；122日2h和hybrid都支配daily；90日daily零交易避损，只是现金。相同风控不等于相同实际风险，这些比较不是显著性/未来资格认证。

[根V2验收](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V2.json)实际核七个closed0角色、全部源字节、专属目录预算、两来源失败和一个根metadata失败。根V1误拒绝pytest内部current目录链接，实际只读检查确认唯一链接指向同一独占STATE中的对应test0目录；V2只接纳此精确路径/目标，仍拒绝外部或其他链接，磁盘守卫和金融代码不改，旧失败/helper/protocol保留。根V2自身最终closed0在Git后验凭证再次绑定，生成报告时LIVE标记如实保留。

8765显示已完成实际扫描20,515,858,910B于2026-10-03 08:05:06.540887+08，来源绑定90日实际报告；不是新增扫描，后续小工件不在该值内。标准Git源码字节门槛/模块提交/正常推送/精确远程一致仍待最后闭合。
