# D070：更快再入场的有限独立复核

日期：2026-10-05。复核者：`active_allocation_reference` 子 agent。

**结论：实现与保存证据可验收；固定 EXIT10/armed REENTRY10 配方不采用。** 相同十币、303 日连续共享 10,000USDT 账户下，四种既定成本/资金费解释的净增量全部为负，回撤和换手全部增加。保留 EXIT10/REENTRY20 研究参照，投资候选仍为 NONE、资金选择为 CASH。负结果不否定所有恢复入场或趋势策略。

## 独立性的实际边界

本复核者编写了 `multi_asset_financial_audit.py` 的直接 Donchian 再入场参考，因此不是该参考的独立作者。本次新 helper 不导入生产策略、金融 checker、诊断脚本或第三方账本：使用标准库、50 位 Decimal、独立键值解码和保存状态字段，复核报告算术及源码差异。没有重新读取市场原文件、计算生产目标、拟合、测试或回放账户；不会把保存报告相互一致提升为独立市场证据。

金融 V6 已另用直接窗口参考和既有独立账本核了四账户；其最大 cash 误差 `2.1827872842550278e-11 USDT`、ratio 误差 `1.6486811915683575e-14`，低于预定 `1e-7/1e-10` 容差。本次轻量复核在报告层的最大算术差为 **8.4e-13 USDT**。市场冻结订单意图的完整独立重建仍为 false，不声明全部执行控制器已从原始意图独立重建。

## 实际范围、身份与闭合

- 市场 V3 task `96bc4169e93c4c749671cc11c979a74d`：实际 completed/exit0；仅 LIQUIDITY_TEN 四账户，每账户 436,320 分钟、303 日、10 月，末持仓和标记名义额均为零，真实按既定末退出策略成交后成为现金，没有免费强制平仓。
- 金融 V6 task `771eb8ca12b14a9893b5d2ac67a192d5`：实际 completed/exit0，四金融 calls；43.008946 秒，RSS 1,244,696,576B；报告 1,382,422B。日历、实际资金费与跨月持仓延续分别保存，不拼接独立月度满资金账户。
- 保存配对诊断 V6 task `d99730fc143e4961b985b182bcb06180`：实际 completed/exit0，零市场重播；SHA256 `2299985c53738f20d7143c41c8aa1d658c20187f4486ba726ca2892ad54d7b29`。
- 本复核 task `cfe6524e3e314d378a417c60287fb457`，标题“D070独立无损证据与资金桥复核”：实际 completed/exit0；计算 0.233657 秒、RSS 39,383,040B，在 30 秒/256MiB/50KB 输出预算内。已有 shared5GB/swap0/GPU0 slice，CPU 与 POLARS 线程变量为 2，没有另建观察器。
- 市场 V3 实际 621.762246 秒、RSS 728,117,248B、共享组采样峰值 1,544,417,280B、所属新增工件 202,964,669B。采样峰值不冒称连续全过程最大值。

协议仍是 `protocols/DONCHIAN_REENTRY10_20261005_V3.json`，SHA `c79309438f9b9926829c7e8fa641fe1f84810c5b1504d2fbc12f92b53ccd858b`。实际市场报告 SHA `7b8e503fe2dc8afceac1a05d9c465d5bb218245c503c7e96db8177eeca95b66c`。十币有序身份逐账户匹配，未按收益重选 July 流动性/200 日预热池。

## 信号、报告编码与来源复核

首次 flat 入场仍为严格 `close > prior20 high` 且 `close > completed SMA200`；held 严格跌破 prior10 low 退出并 armed。退出日不重新入场；后续 flat/armed 日才使用 prior10 high + 同一 SMA200，成功入场清 arm。初始未 armed，pool/gap/CASH 重置；SMA 只过滤入场。当前 bar 不进入通道，SMA 使用当时已完成 bar，资金费不作信号。

本次解码完整 **3,030 条**有序证据、1 套键 schema，重新打包值与原报告逐项相等，canonical JSON SHA 为 `ff4d42bdecbffda7bf99f43371feba868e3afa2ac086f0979ee3dd0bb1e029fa`，与报告的 logical SHA 相等。逐币逐日核 state/arm 前后连续、全部严格谓词、channel 的前一日边界和实际 entry period：STAY_CASH 2,200、ENTER_LONG 32、KEEP_LONG 767、EXIT_TO_CASH 31；其中 23 次成功入场有 prior armed。这些是信号状态次数，不冒称实际订单、成交原因或持仓次数。

原冻结 checker `docs/archive/DONCHIAN_REENTRY10_PRE_COMPACT_FINANCIAL_SOURCE_20261005_V1.py` SHA `f8a753969337a2f86fc9932634d598e284b829a95a9fc8118ea37372c671e9d4`；当前 evaluator SHA `684166eafc9eafb37358bb747edccaa5a215fb272783a2d02211062e70f6a8a7`。独立将唯一新报告编码块还原后，**全文与原冻结源码相等**；18 个非 main 函数 AST 也全部相等。目标直接参考、输入、金融数学、精度及容差未变。

V6 正常使用已有 `source_archives` 接口：计划 source map 和市场原绑定 checker 都解析原 f8a753 副本，`checker_sha256/current_evaluator_source` 单独绑定当前 684166 evaluator；其他源约束保留。不是把原冻结旧针改写为当前针，也没有新增运行绕过代码。

## 实际经济配对

全部是同产品、同本金、同日期和同假设的独立比较账户；不能把四账户利润相加当组合。收益分母为完整 10,000USDT。

| 成本 / 未认证资金费解释 | REENTRY20 净 USDT | REENTRY10 净 USDT | 净增量 USDT | 原/新分钟 MDD |
|---|---:|---:|---:|---:|
| BASE27 / fraction | 497.1630 | 180.9758 | -316.1873 | 7.4271% / 10.2385% |
| BASE27 / percent | 565.7554 | 249.5797 | -316.1758 | 7.3151% / 10.0055% |
| STRESS43 / fraction | 463.5121 | 128.6673 | -334.8448 | 7.5987% / 10.5625% |
| STRESS43 / percent | 531.8811 | 196.8666 | -335.0145 | 7.4450% / 10.3308% |

独立 Decimal 核八个保存账户的 gross−fee−execution+fund=net、资产和、四个配对差额、市场精确金额终现金桥、十个月净损益和以及金融报告/市场摘要一致。它是保存金额的复核，没有重播实际 journal。

BASE27/fraction 新方案 gross 345.2212、fee 37.2182、execution 54.1358、fund -72.8915，net 180.9758。对原方案，gross 减少 **280.7472**，cost 增加 **33.6057**，fund 减少 **1.8343**，合计 net 减少 **316.1873**。主要失败来自价格毛损益，其次新增换手成本；低手续费不能解释或修复这项毛损益下降。

同情景实际年化日波动 8.3624%→8.4809%，总名义换手/初始资本 4.2776→6.7669，平均 gross/net 暴露 9.0878%→9.9633%，最大实际 gross 23.4280%→29.8526%。共同 abs30%/gross60%/逐仓1x caps 不代表实际风险匹配；新方案不是以更低实际风险换低收益。新四账户记录内最大 gross≤60%、逐币≤30%，不声明分钟观察以外的连续盘中安全。

全部四条件均有 66 决策日、232 个 target row、110 个非零信号 row 改变。BASE/fraction 的 BTC、1000PEPE、XRP 净增量分别约 -343.65/-138.50/-88.37USDT；ETH、SOL、DOGE 分别改善 +134.63/+69.12/+83.64，仍不能抵消总损失。这是两个实际共享账户的逐资产账本差，包含资金竞争/共同 risk 缩放影响，不能解释成隔离关闭某资产的可执行反事实。

该情景全十个月差额都保存：最差增量为一月约 -140.45、四月 -115.16、六月 -90.91USDT，部分月正向；没有只选失败月份。正收益日 103→109、top5 正收益日份额 19.5472%→18.3717%，仍与净损益和回撤恶化同时发生，不能用胜率或分散度代替投资质量。

## 失败与真实计算预算

| 尝试 | 实际任务 / 退出 | 范围与处理 |
|---|---|---|
| 准备 V1 | `94f444f5d69e4a7db85bc12e21d093de` / process0 | OWN/helper 旧身份语义拒绝；0 tests、0 market，不算成功科研运行 |
| 市场 V2 | `31b55392af8c4ffca669683c1167cacf` / progress -2、host1 | 漏 pool flag；2 完整 TWO_ASSET 账户及第三前缀，42,948,606B，精确自有 PID SIGINT；不是十币结果 |
| 金融 V3 | `00d746b7f6044411a289545ad33a6ca7` / failed1 | 遍历 4 calls 后报告 LIMIT2MB 拒绝，无最终 FIN 文件；0 验收，不伪称通过 |
| 金融 V4 | `0d9095813e634f28bc9e31bc8a6ffa9c` / failed1 | old checker/source archive 绑定拒绝，input0/calls0 |
| 金融 V5 | `057725d9898149e3a9c009fae76cc55d` / failed1 | 两 map 的计划 digest 与 archive 不匹配，input0/calls0 |
| 金融 V6 | `771eb8ca12b14a9893b5d2ac67a192d5` / completed0 | 无损编码后新独占绑定；最终 4 calls 验收 |

因此新十币市场账户是 4 个，另有真实误启动 2 个两币账户和第三前缀；金融实际 calls 合计 **8**（首次 4 未验收 + 最终 4），不能只统计成功最终 4。已通过的唯一新增机制测试 V2 未重跑；金融编码修复没有市场重播。上述失败报告、协议、日志、task 与源副本均保留。

## 声明限制与研究决定

这是已反复查看的 2024-09-01 至 2025-07-01 之前开发筛选，不是 unseen/OOS 或长期净 APR。Binance USD-M price/mark/funding 配 Bybit 普通用户 taker 5.5bp/side 及既定 4+4/8+8bp 摩擦，是跨场所情景；历史 BBO、Bybit native filter/费区/规则/清算与发布可得性未认证。资金费 fraction/percent 二解释都保留，单位不能按盈利选择。固定 caps 与低 gross 不保证无盘中跳空或 native 清算；末现金是本模拟规则结果。

暂停这一个 EXIT10/armed REENTRY10 配方，保留已经正确的能力和负结果。重开条件应是具体新信息或不同、事前记录的恢复机制有可检验依据，不能继续在相同已见数据无限搜 reentry 周期。下一项优先做适用强基准的风险可比经济对照：当前毛价格优势和独立证据不足，比再追求更频繁恢复更值得核实。CASH 仍是资金选择，不授予真钱、keys、发单、锁定测试或资源扩大。

## 可复现轻量复核

STATE helper：`/home/xflops/coin-state/d070-reentry10-independent-20261005-v1/independent_review.py`，SHA `7419fa4932ba968179254b0fd3f448c4c84a87b859b25989d49d84697275dd1e`。结果同目录 `result.json`，SHA `056fed352a72e0626906ee97cc5e3d0f63a0eca493ce330bcff9b490ae9f2cab`；闭合任务 `STATE/task-progress/task-cfe6524e3e314d378a417c60287fb457.json`。helper 使用 exclusive output，复现应先另建独占 STATE 目录并复制 helper，不能覆盖已保存 result。

实际命令（`hpc_linux`，未请求 GPU）：

```sh
bash scripts/with_task_progress.sh --title 'D070独立无损证据与资金桥复核' -- env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 POLARS_MAX_THREADS=2 timeout 30 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /home/xflops/coin-state/d070-reentry10-independent-20261005-v1/independent_review.py --run-dir /home/xflops/coin-state/d070-reentry10-independent-20261005-v1
```
