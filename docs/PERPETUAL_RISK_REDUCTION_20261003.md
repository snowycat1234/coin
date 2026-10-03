# D046：风险减仓正确性修复后的四个完整 LS 账户

## 结果与采用范围

四个固定 LONG_SHORT（LS）账户全部完成 **303 日 / 436,320 分钟**，0 停止、0 债务、终端零库存。全资本净收益为 **−9.76% 至 −9.32%**。独立金融四次核验及 ROOT/保存摘要比较都已真实退出 0。**采用风险减仓正确性能力；暂停固定 SMA LS 投资及 HPO，当前 CASH / NO_QUALIFIED_CANDIDATE。**

## 本轮唯一变更与原失败保留

| 变更 / 保留 | 范围 |
|---|---|
| 风险减仓 | 原已可执行 reduce-only 尝试中，Decimal40 ceiling 到 `1e-8` step，并满足假定 10 USDT min-notional；按因果当前方向报价计算，数量不超过库存 |
| 完成判据 | 精确到目标、同号且绝对库存不超过目标，或 flat；无 epsilon、未来报价、容量豁免或费用/caps/延迟放宽 |
| 其它路线 | DAILY_TARGET、TERMINAL、原 SMA 与金融体不变；未认证 Bybit 原生过滤器 |
| 原失败 | [D045](PERPETUAL_303_COMPARISON_20261003.md) 四个 LS 停于 95,229 分钟，减仓尾差小于 step/min-notional，原前缀与 NE 永久保存 |
| 元数据失败 | freezer V1 task `f0a835c209784613b92cb043bb39f0e7` 实际 exit 1、表达式锚 0、0 数组；V2 只修锚定位 |
| 新验收 | 唯一手算/容量/未来前缀合成用例 1 PASS；4 新完整 LS + 16 旧完整保存摘要，旧账户未重放 |

不拼接旧前缀，也不把停止前缀金额与全期金额的差归因于修复收益。

## 固定设计

评分 **2024-09-01..<2025-07-01 UTC**：303 已见日、10 完整月，BTCUSDT/ETHUSDT 同 USD-M。每账户 **10,000 USDT**、1× isolated；原 SMA50/200、fresh-flat、200 完成日预热、past-30 signed covariance/年化 365、10% intent 波动目标、单币绝对 cap 0.3/gross 0.6、0.99 sizing buffer 不变。

BASE27 为名义开平 27 bp：taker fee 5.5 bp/side，half-spread/slippage 各 4 bp/side；STRESS43 保留同 fee，两项各 8 bp/side。手续费、spread/slippage 按实际成交数量计。Funding 原始单位仍 **UNCONFIRMED**：F=`RAW_AS_FRACTION`（scale 1），P=`RAW_AS_PERCENT`（scale 0.01），两种均为事前条件，不选择表现好的解释。

来源原 94 档（54 复用/40 新，70 首次 QA/24 已接受能力），本轮不再 QA。实际 daily 复用 34；继承 `reused_daily_archives=12` 仅旧 D040 角色字段，冻协议不改。547 日源失败保留；303 日在新 PnL 前冻结，仍为已见 SCREENING，非 unseen/未来资格/长期 APR。

## 四条件完整经济表

金额 USDT；每条件 506 成交 legs。`net = same-quantity gross + funding − fee − spread − slippage`。期末 NAV 9,065.94/9,067.65/9,023.84/9,025.54，全部 free cash，isolated/库存/债务为 0。

| LS 条件 | Gross | Fee | Spread | Slippage | Funding | Net | 全资本净收益 | 总换手/10k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE27 / F | −859.46 | 30.04 | 21.85 | 21.85 | −0.8613 | −934.06 | −9.3406% | 5.4625 |
| BASE27 / P | −858.63 | 30.03 | 21.84 | 21.84 | −0.0086 | −932.35 | −9.3235% | 5.4607 |
| STRESS43 / F | −858.13 | 29.98 | 43.60 | 43.60 | −0.8383 | −976.16 | −9.7616% | 5.4507 |
| STRESS43 / P | −857.30 | 29.97 | 43.59 | 43.59 | −0.0084 | −974.46 | −9.7446% | 5.4488 |

| 条件 | 日收益描述性年化波动率 | 全观察点 / 分钟 MDD | 日端点 MDD | 分钟最大 gross 权重 | 最低实际 free cash |
|---|---:|---:|---:|---:|---:|
| BASE/F | 10.4548% | 14.3969% | 12.8904% | 60.2275% | 2,737.89 |
| BASE/P | 10.4622% | 14.3038% | 12.7951% | 60.2275% | 2,740.78 |
| STRESS/F | 10.4475% | 14.5696% | 13.0660% | 60.2278% | 2,734.36 |
| STRESS/P | 10.4549% | 14.4766% | 12.9710% | 60.2279% | 2,737.25 |

BASE/F 最大 BTC/ETH 权重 30.0871%/30.2610%；31 次风险 signal、首次最大观察延迟 60.000001 秒。相同 caps 非连续硬上限或匹配实际风险；全观察点 MDD 覆盖保存的 close/fills/funding，非分钟内极值或原生清算安全。

## BASE/F：新 LS 与旧完整账户

F 仅统一展示，非正确单位认证。旧四账户引用已接受 D045 JSON，未读数组。共同 10k，但实际风险/路径不同，不事后波动匹配、不把 LS−LO 全归因于 short。

| 完整账户 | Gross | Funding | Fee | Execution cost | Net | 净收益 | Legs | 总换手/10k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 新 LS | −859.46 | −0.86 | 30.04 | 43.70 | −934.06 | −9.3406% | 506 | 5.4625 |
| 旧 LO | −77.60 | −88.43 | 14.03 | 20.41 | −200.46 | −2.0046% | 202 | 2.5510 |
| 旧 SO | −1,203.30 | +62.62 | 12.21 | 17.76 | −1,170.65 | −11.7065% | 234 | 2.2200 |
| 旧 HOLD | +817.50 | −116.37 | 11.82 | 17.19 | +672.12 | +6.7212% | 378 | 2.1486 |
| 旧 CASH | 0 | 0 | 0 | 0 | 0 | 0% | 0 | 0 |

| 实测 BASE/F 风险/资金 | 新 LS | 旧 LO | 旧 SO | 旧 HOLD | 旧 CASH |
|---|---:|---:|---:|---:|---:|
| 年化波动率 | 10.4548% | 8.8925% | 8.9386% | 10.4987% | 0% |
| 全观察点 MDD | 14.3969% | 11.9831% | 15.1925% | 11.2380% | 0% |
| 日端点 MDD | 12.8904% | 10.9488% | 14.5665% | 10.3064% | 0% |
| 分钟平均 / 最大 gross 权重 | 27.3281% / 60.2275% | 13.6117% / 30.0571% | 11.2044% / 28.3489% | 18.1467% / 27.3856% | 0% / 0% |
| 分钟平均 signed net 权重 | −0.6484% | +13.6117% | −11.2044% | +18.1467% | 0% |
| 平均 / 最大 isolated collateral / NAV | 26.9225% / 66.4357% | 13.4598% / 32.4535% | 10.5613% / 25.8545% | 17.0739% / 25.6648% | 0% / 0% |
| 最低实际 free cash | 2,737.89 | 6,772.09 | 7,301.11 | 7,443.60 | 10,000 |

净暴露近零仍占用双腿 gross/保证金/成本。SO 是真实 short fills/负库存，非 LO 曲线反号。

## 方向贡献与月度损伤

新 BASE/F 保存的方向贡献为：

| 方向 | Gross | Fee | Execution cost | Funding | Net contribution |
|---|---:|---:|---:|---:|---:|
| LONG | −35.55 | 13.94 | 20.28 | −80.22 | −149.9955 |
| SHORT | −823.91 | 16.10 | 23.42 | +79.36 | −784.0668 |

两方向均亏损。新 BASE/P long/short net −72.37/−859.98，STRESS/F −169.22/−806.94，STRESS/P −91.74/−882.72。各账户 NAV/尺寸/状态不同，不能证明新增 short 的纯因果收益。

保存比较的 BASE/F **LS−LO = −733.60**：LS short net **−784.07** 加 long 路径差 **+50.47**；LS−HOLD 为 **−1,606.18**。这不是纯 short 因果效应，实际暴露/波动/MDD 不匹配；LS 相对 HOLD 波动略低，MDD 更高。

BASE/F 连续月表直接取保存字段，费用/funding 按流水归月，不重置资本或每月重扣开平门槛；旧列为 D045 月净额。

| 月份 | 新 LS gross | 新 LS net | 新 LS funding | 旧 LO net | 旧 SO net | 旧 HOLD net |
|---|---:|---:|---:|---:|---:|---:|
| 2024-09 | −158.20 | −157.79 | +5.15 | 0 | −157.79 | +146.48 |
| 2024-10 | −170.05 | −164.78 | +16.23 | +10.82 | −103.00 | +110.48 |
| 2024-11 | −179.68 | −185.28 | +3.87 | +683.48 | −598.80 | +707.55 |
| 2024-12 | −179.62 | −199.06 | −13.60 | −169.01 | −25.53 | −155.69 |
| 2025-01 | +86.59 | +70.70 | −14.13 | +79.91 | 0 | +82.04 |
| 2025-02 | −523.12 | −531.20 | −6.05 | −601.31 | 0 | −617.51 |
| 2025-03 | +566.62 | +555.55 | +0.02 | +19.62 | +113.16 | −65.90 |
| 2025-04 | +40.32 | +30.50 | +0.29 | −91.03 | −44.46 | +86.89 |
| 2025-05 | −407.90 | −408.21 | +4.76 | −191.58 | −364.58 | +366.24 |
| 2025-06 | +65.60 | +55.51 | +2.59 | +58.62 | +10.34 | +11.53 |

新 LS 四条件 **4/10 正月**。BASE/F 三月 +555.55 未抵销二月 −531.20、五月 −408.21 及其它损失。top-5 正日份额 13.6679%，分母为全部正日净增量 **5,174.49**，非全期净亏损；绝对日增量分母 11,283.03。旧 LO/SO/HOLD 正月 5/10、2/10、7/10，top-5 正日份额 23.4832%/19.1067%/16.8035%，各自正日分母 4,032.02/3,226.84/6,401.28。没有选月或新增金融指标。

## 金融、因果与资源边界

复用原 1c4b 金融体、HandLedger Decimal、NumPy minute/day/month assertions，现金容差 `1e-7 USDT`/ratio `1e-10` 不变。仅 4 新调用，max error cash `2.1827872842550278e-11`/ratio `8.43769498715119e-15`；核 targets/availability、funding/成交/钱包/NAV/统计。**全市场 frozen intent sizing 未独立重建**，本轮未全市场 future-poison 重放。Funding 单位/发布时间与原生 Bybit filters/MMR/清算未知；Binance 历史+Bybit 费用假定仅条件研究，不认证原生收益、稳定 APR 或未来资格。

研究实际 227.05 秒、峰值 RSS **622,755,840 B**、新 owned **161,716,459 B**；独立 12.78 秒、563,417,088 B。最近真实磁盘扫描 **22,649,980,545 B @ 2026-10-03 09:50:41.507780 UTC**，发生在新 161.716 MB 工件之前，未计这些后续输出，不冒称当前总量。共享约 5 GB RAM、swap 0、GPU 0；无 locked、订单、密钥或真钱。

## 实际完成凭证

四任务均只读 `task-progress` 核实 **completed / exit_code 0**；本次文档无 Python/数组/测试。

| 凭证 | Task ID | SHA256 |
|---|---|---|
| [四 LS 实际](../reports/fast_research/PERPETUAL_RISK_REDUCTION_RESEARCH_ACTUAL_20261003_V2.json) | `72d233d63f4241b7ab3c8c04de64746c` | `017cbc4049d778d0447028cd9ca42bbd1ffe44bb8febdbcd6ddff0db8a2fbc54` |
| [独立四次金融](../reports/fast_research/PERPETUAL_RISK_REDUCTION_INDEPENDENT_20261003_V1.json) | `d5370e8769bb44b1ace2269cf44bd2e2` | `6aadb699e038ce479d1a3dc343aef26825494ff0b819284b6a7ef1993b5eb22d` |
| [唯一合成用例](../reports/fast_research/PERPETUAL_RISK_REDUCTION_SMOKE_20261003_V2.json) | `a13d8363bd204a22a1917d2fc7319151` | `de070975a9e92585678c9e2106b4214c5a90c7c02bcabf937e7972821b939d02` |
| [ROOT / 保存摘要比较](../reports/fast_research/PERPETUAL_RISK_REDUCTION_ROOT_ACCEPTANCE_20261003_V1.json) | `053f42ed6c254a029a475dc1c0f1cafe` | `feb63187abafc1ae3b8a52c5a9404cd74aff6354abf0404812cc2242e276858c` |

研究协议为 `PERPETUAL_RISK_REDUCTION_RESEARCH_20261003_V2.json`，SHA `344fd9fa81f93ee2e10d1490c2edb441a794a069fbb4069142c53acc668baf16`。旧完整摘要引用 [D045 保存比较](../reports/fast_research/PERPETUAL_303_ECONOMIC_COMPARISON_20261003_V1.json)，SHA `77b1872abcc1b049ca5e04c85db2ce186830cbf81f96d56d5708642d382e097f`；旧接受凭证 SHA `841a525d41162bbcbaedb14b0be0c3696bcf3356cfdb76542a864662797c4f58`。这不是一次新跑 20 账户；仅 4 新 LS + 16 原完整结果的保存摘要参考。

ROOT 接受 20 完整保存摘要：4 新 LS + 16 旧完整；没有旧金融调用，原 4 停止前缀另存。Git 来源凭证 SHA `4e62ee2cbcc0aa1ef03687c917e4a962a913180593056926365e15a4f4bb51f8`。ROOT JSON 的 `LIVE_CALLER_NOT_SELF_CERTIFIED` 是写报告时状态，实际任务随后已独立查到 completed/0。

## 科研选择

固定 SMA LS 投资/HPO 暂停，reference 与正确性能力保留；负的 **gross signal** 是当前瓶颈。不永久删除做空。根已在 [D046 决策追加](RESEARCH_DECISION_LOG.md) 选择唯一下一任务：MIT Jesse `TurtleRules`，repo pin `7c91e0a37bf62165790120d730442e4f6eb00364`，事前固定 **4h**、双向 20-bar 突破/10-bar 退出、ATR20×2 止损、最多 4 层 0.5ATR 加仓及真实 fill callback。4h 是本研究选择，不称原作者固定周期或完整经典 Turtle。

先验最小兼容测试的止损/加仓/partial/恢复回调及共享 caps，不能盲套 signed target。语义不能保留则停止，明确解决兼容性后重开；**Turtle 市场未运行**。后续净增量须跨状态挑战同产品 HOLD，并列实际风险，不挑窗口/降低成本/改 unit/HPO，不升级 Candidate。

实际命令完整记录在各报告 binding，原运行经 WSL clean CPU2、`with_task_progress`/`bounded.sh`。以下是已执行研究入口参数；复现必须另建独占目录/输出并重新冻结绑定，禁止覆盖：

```text
perpetual_risk_reduction_research_v2.py --protocol protocols/PERPETUAL_RISK_REDUCTION_RESEARCH_20261003_V2.json --run-dir /home/xflops/coin-state/d046-perpetual-risk-reduction-research-20261003-v2 --output reports/fast_research/PERPETUAL_RISK_REDUCTION_RESEARCH_ACTUAL_20261003_V2.json --experiment-id D046-RISK-REDUCTION-FOUR-LS-V2 --period 303D
```
