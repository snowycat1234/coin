# D045：303 日同产品 SMA 方向与 HOLD 参考

## 科研结论与当前选择

当前选择为 **CASH / NO_QUALIFIED_CANDIDATE**。固定 SMA 多头在四个预登记条件下净收益为 **−2.20% 至 −1.18%**，空头为 **−12.45% 至 −11.71%**；HOLD 参考为 **+6.55% 至 +7.88%**。HOLD 是必须保留的强参考，尚无原生市场或长期净 APR 资格。四个 LONG_SHORT（LS）账户均提前停止，**303 日收益、完整期间波动率及与完整账户的收益差均 NOT_EVALUABLE**。

本模块完成了 20 个固定选择器的条件式账本验收，包含 16 个完整期间结果和 4 个已核实停止前缀；这不表示 20 个账户完成全期。下一步 D046 仅修复风险减仓目标与数量步长/min-notional 的正确性，并在同一数据与原四条件下重放四个 LS 账户。不得新增 HPO、择月、改变信号或把工程修复解释为 alpha 改善。

## 固定设计与公平边界

- 评分：**2024-09-01 00:00 UTC 至 2025-07-01 00:00 UTC（不含）**，303 日、每账户 436,320 分钟、10 个完整月。历史已见，仅作 SCREENING，不能称 unseen 或真正未来记录。
- BTCUSDT、ETHUSDT，USD-M 成交/mark/funding 来源；每个独立账户初始资本 **10,000 USDT**，1×、isolated。相同 past-30 完成日收益协方差、年化 365、10% 波动目标、单币绝对权重 0.3、gross 0.6、0.99 sizing buffer。200 个完成且已可用日线预热；暖启动不带仓。
- SMA 50/200 使用固定公开 hooks 的日线状态规则：严格大于/小于，等号保持原状态。LO、SO、LS、CASH 是方向许可消融，内部状态与实际成交时点可能不同；SO 是真实负库存与 SELL/BUY 回补账本，并非把多头曲线取反。HOLD 固定 raw 多头 `[0.3, 0.3]`，沿用同一风险算法和可用性门槛。
- BASE27：名义一次开平 27 bp（费用 5.5 bp/side，half-spread 4 bp、slippage 4 bp/side）；STRESS43：费用相同，half-spread/slippage 各 8 bp/side。按实际成交量收费，不以名义成本直接扣资本比例。
- 原始 funding 单位 **UNCONFIRMED**。F=`RAW_AS_FRACTION`、scale 1；P=`RAW_AS_PERCENT`、scale 0.01。两者均为事前冻结条件，不能从收益选择“正确单位”。本页 BASE/F 主表只是统一展示口径。
- trade-mid 与 mark 分离；过去已完成分钟容量、至少一分钟并加 1 μs 的执行延迟、资金费先于同点 reductions/increases、永久停止而非救援。MMR 0.005、step `1e-8`、min-notional 10 USDT 是假定，**Bybit 原生过滤器、风险阶梯、清算、资金费发布/准确扣费时刻均未认证**。

## 完整期间结果

以下金额为 USDT。保存的 bridge 为 `net = same-quantity gross + funding − fees − execution_cost`；gross 不是免成本重新模拟的策略。完整 LO、SO、HOLD 和 CASH 均终端零库存、零 isolated balance、零债务，终端成交仍受容量与费用约束。

### BASE27 / F 主表

| 完整账户 | Gross | Funding | Fee | Spread | Slippage | Net | 全资本净收益 | 成交 legs | 总换手/10k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SMA LO | −77.60 | −88.43 | 14.03 | 10.20 | 10.20 | −200.46 | −2.0046% | 202 | 2.5510 |
| SMA SO | −1,203.30 | +62.62 | 12.21 | 8.88 | 8.88 | −1,170.65 | −11.7065% | 234 | 2.2200 |
| HOLD | +817.50 | −116.37 | 11.82 | 8.59 | 8.59 | +672.12 | +6.7212% | 378 | 2.1486 |
| CASH | 0 | 0 | 0 | 0 | 0 | 0 | 0% | 0 | 0 |

| BASE/F 实测风险与资金 | LO | SO | HOLD | CASH |
|---|---:|---:|---:|---:|
| 日收益描述性年化波动率 | 8.8925% | 8.9386% | 10.4987% | 0% |
| 所有已记录观察点 MDD / 分钟 MDD | 11.9831% | 15.1925% | 11.2380% | 0% |
| 日端点 MDD | 10.9488% | 14.5665% | 10.3064% | 0% |
| 分钟平均 gross 权重 | 13.6117% | 11.2044% | 18.1467% | 0% |
| 分钟最大 gross 权重 | 30.0571% | 28.3489% | 27.3856% | 0% |
| 分钟平均 signed net 权重 | +13.6117% | −11.2044% | +18.1467% | 0% |
| 分钟平均 / 最大 isolated collateral / NAV | 13.4598% / 32.4535% | 10.5613% / 25.8545% | 17.0739% / 25.6648% | 0% / 0% |
| 最低实际 free cash（所有观察点） | 6,772.09 | 7,301.11 | 7,443.60 | 10,000 |

相同 intent caps 不等于匹配实测风险，也不等于连续硬上限。LO 的 BTC 最大实际权重为 30.0571%；保存的风险减仓首次最大延迟为 60.000001 秒。MDD 只覆盖保存的分钟 close、fills、funding 等观察点，不证明分钟内极值或原生清算安全。

### 全部四条件：不选择 funding 单位

每格为 **净收益 / 描述性年化波动率 / 全观察点 MDD**。CASH 四条件均为 0 / 0 / 0，LS 四条件均 NE。

| 条件 | SMA LO | SMA SO | HOLD |
|---|---:|---:|---:|
| BASE27 / F | −2.0046% / 8.8925% / 11.9831% | −11.7065% / 8.9386% / 15.1925% | +6.7212% / 10.4987% / 11.2380% |
| BASE27 / P | −1.1751% / 8.8960% / 11.6065% | −12.2874% / 8.9458% / 15.7170% | +7.8824% / 10.5028% / 10.9541% |
| STRESS43 / F | −2.2016% / 8.8887% / 12.0870% | −11.8741% / 8.9409% / 15.3243% | +6.5461% / 10.5002% / 11.2800% |
| STRESS43 / P | −1.3736% / 8.8922% / 11.7108% | −12.4538% / 8.9482% / 15.8480% | +7.7077% / 10.5046% / 10.9963% |

四条件实际费用/资金费明细继续保存，单位为 USDT：

| 条件 | LO gross / fee / exec / funding / net | SO gross / fee / exec / funding / net | HOLD gross / fee / exec / funding / net |
|---|---|---|---|
| BASE/F | −77.60 / 14.03 / 20.41 / −88.43 / −200.46 | −1,203.30 / 12.21 / 17.76 / +62.62 / −1,170.65 | +817.50 / 11.82 / 17.19 / −116.37 / +672.12 |
| BASE/P | −82.02 / 14.10 / 20.51 / −0.89 / −117.51 | −1,199.50 / 12.17 / 17.69 / +0.62 / −1,228.74 | +818.62 / 11.90 / 17.31 / −1.17 / +788.24 |
| STRESS/F | −76.99 / 14.02 / 40.78 / −88.37 / −220.16 | −1,202.29 / 12.20 / 35.49 / +62.57 / −1,187.41 | +817.05 / 11.81 / 34.35 / −116.29 / +654.61 |
| STRESS/P | −81.41 / 14.09 / 40.98 / −0.89 / −137.36 | −1,198.49 / 12.15 / 35.36 / +0.62 / −1,245.38 | +818.42 / 11.89 / 34.59 / −1.17 / +770.77 |

## LS：经核实的停止前缀，不是完整亏损曲线

四条件均在 **2024-11-06 03:09:00.000001 UTC** 停止，完成 **95,229 / 436,320** 个分钟快照，139 个成交 legs。状态为 `NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION`，不是模拟清算。原减仓目标未量化到 step；已成交库存与目标留下小于 `1e-8` 的尾差，剩余订单又无法满足 min-notional，重试后停止。不得补零、延长原 NAV、称全期收益或以停止前缀比较 303 日优劣。

| LS 条件：仅截至停止点 | Gross | Fee | Exec | Funding | 已记录 Net | 剩余 gross MTM | 前缀全观察点 MDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE/F | −274.89 | 7.28 | 10.59 | +21.36 | −271.41 | 5,836.43 | 6.3666% |
| BASE/P | −274.73 | 7.27 | 10.58 | +0.21 | −292.36 | 5,823.86 | 6.5625% |
| STRESS/F | −274.89 | 7.28 | 21.18 | +21.35 | −282.00 | 5,830.11 | 6.4424% |
| STRESS/P | −274.72 | 7.27 | 21.15 | +0.21 | −302.93 | 5,817.56 | 6.6381% |

BASE/F 停止点：NAV 9,728.59、free cash 4,104.55、isolated balance 5,638.30、债务 0；BTC `+0.03892261`、ETH `−1.11480112`，ETH pending target 为 `−1.114801117451247757033590220`。gross weight 59.9926%，signed net notional −17.42 USDT。这是重大未平库存，不是 dust、现金已实现利润或完成账户；完整波动率/换手率为空，不能自行外推。

## 方向贡献、月份与集中

BASE/F 保存的方向贡献：LO 的 long gross/net 为 −77.60/−200.46；SO 的 short gross/net 为 −1,203.30/−1,170.65，long 为 0。HOLD long gross/net 为 +817.50/+672.12。LS **前缀** long gross/net +84.68/+73.63、short −359.57/−345.05。这些是真实 signed 库存归因；LS−LO 完整差分未成立，不能把策略差异全部归因于 short。

下表直接复制 BASE/F 保存的连续月归因，格内为 **gross / net USDT**。各月不重置资本或重扣一次名义开平成本，费用/funding 已随实际流水归因；CASH 全月为 0。LS 只保存九月、十月及十一月前五个完整日，不能进入完整月表。

| 月份 | LO | SO | HOLD |
|---|---:|---:|---:|
| 2024-09 | 0 / 0 | −158.20 / −157.79 | +156.18 / +146.48 |
| 2024-10 | +17.16 / +10.82 | −114.73 / −103.00 | +131.73 / +110.48 |
| 2024-11 | +712.42 / +683.48 | −616.08 / −598.80 | +737.53 / +707.55 |
| 2024-12 | −142.80 / −169.01 | −28.10 / −25.53 | −131.41 / −155.69 |
| 2025-01 | +97.90 / +79.91 | 0 / 0 | +100.50 / +82.04 |
| 2025-02 | −592.16 / −601.31 | 0 / 0 | −608.11 / −617.51 |
| 2025-03 | +28.34 / +19.62 | +114.82 / +113.16 | −61.44 / −65.90 |
| 2025-04 | −86.30 / −91.03 | −42.77 / −44.46 | +92.12 / +86.89 |
| 2025-05 | −183.11 / −191.58 | −367.58 / −364.58 | +375.91 / +366.24 |
| 2025-06 | +70.96 / +58.62 | +9.33 / +10.34 | +24.47 / +11.53 |

LO/SO/HOLD 保存的正收益月数为 5/10、2/10、7/10；HOLD 的十一月 +707.55 大于全期净额 +672.12，二月 −617.51 明显抵销，不能称均匀盈利。未新增月度收益份额或以全期净额作集中度分母。已保存的 **top-5 正收益日份额**分别为 23.4832%、19.1067%、16.8035%，分母是各账户全部正收益日净增量 4,032.02、3,226.84、6,401.28 USDT；不是全期净利润。全部绝对日增量分母另为 8,264.50、7,624.33、12,130.45 USDT。

## 来源、复用与验收范围

94 档 = trade 1m 20 + mark 1m 20 + funding 20 + daily 34；54 档物理复用、40 档新获取。独立 QA 首次检查 70 档，24 档使用精确既有独立能力凭证，不重复旧 raw/PQ scan。父 D042 完整 547 日来源失败及其缺口证据保留；本窗口是在新 PnL 前冻结，仍是已见开发窗口。

**元数据 scope 勘误：** 冻结协议继承的 `reused_daily_archives=12` 指旧 D040 十二档角色；本模块实际 daily 复用为 34 档，总来源仍 94。此处只解释角色与实际计数，不改冻结协议/来源/QA。

生产复用原 daily SMA target、HOLD 风险 target、controller/settlement core；本次只是固定 303 日/date/input 路由。核心 `src/quant/perpetual_account.py` SHA `cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261`。独立复用原 HandLedger Decimal margin/fills 与 NumPy minute/day/month assertions，**17 次金融调用 + 3 个相同 CASH 工件别名验证**，未重放旧账户或旧 QA。最大 cash 误差 `3.2741809263825417e-11` USDT、ratio `1.9206858326015208e-14`，分别小于原 `1e-7` / `1e-10` 容差。

独立验收包括实际全决策 targets/availability、成交/funding/资金/NAV/完整或停止前缀。没有独立重建所有市场 frozen order-intent quantity sizing，没有本轮全量 future-poison 重放；因果病例与旧接受能力按 SHA 复用。验收不是原生 Bybit、真实 funding 单位、匹配风险或长期 APR 认证。旧 213/122/90 报告只是分别保存的参考，不拼接 NAV、不择月选赢家。

资源：实际研究 573.73 秒、峰值 RSS **614,354,944 B**，独立 35.77 秒、563,146,752 B。最近真实磁盘扫描 **22,250,374,621 B @ 2026-10-03 08:59:03.491955 UTC**，发生在本轮经济工件之前；之后新增工件约 0.446 GB，不能把旧扫描值当当前总量。共享 RAM 约 5 GB、swap 0、GPU 0；未触 locked、密钥或真实发单。

## 实际凭证与复现

以下四任务均已直接核 `task-progress` 为 **completed / exit_code 0**。ROOT 接受了条件式数学与研究比较能力，采用字段为 `RESEARCH_COMPARISON_CAPABILITY_ONLY; INVESTMENT_NONE_CASH`。

| 凭证 | 实际 task ID | 报告 SHA256 |
|---|---|---|
| [研究实际](../reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json) | `4224ed31fe284be2abb7c38ddc4af103` | `de350689cdfa86a40ee1d083795578d215c657e627d6d18b2885b2e59c1dfca3` |
| [独立金融](../reports/fast_research/PERPETUAL_303_RESEARCH_INDEPENDENT_20261003_V1.json) | `aad8082ec12b47749f5478267eff702e` | `f2d3a9402b9606f30243caf6c274be2ae0e45af41b43ac173822f4ea72d79699` |
| [保存摘要比较](../reports/fast_research/PERPETUAL_303_ECONOMIC_COMPARISON_20261003_V1.json) | `caebbbd0de344cd99cf0f1afc7049c5b` | `77b1872abcc1b049ca5e04c85db2ce186830cbf81f96d56d5708642d382e097f` |
| [ROOT 接受](../reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json) | `e25cdf0803a74facb5f5f9676d3811f0` | `841a525d41162bbcbaedb14b0be0c3696bcf3356cfdb76542a864662797c4f58` |

研究协议 SHA `08686880ca77118e3c4a18bd44c203bed7d21e2e0641f01d2e5b95add64c9e81`。来源/独立 QA/来源 ROOT SHA 分别为 `021808d7880552283efa30dac25666a6032042a43fbfd425ba7d42d57f2a926e`、`a72c265bc821f6256600333a3fc64c9b5a738c63e3bf758e386e3a15c8287592`、`3df702c3147b10c606ba92391cff39d251247b170bea502a1b2ffc8d6a7e9ad6`。

原实际入口命令保存在每份 `binding`，均经 WSL `with_task_progress`/`bounded.sh`、clean env、CPU 2 运行。复现需新独占 run/output 和新冻结绑定，禁止覆盖本凭证；下列显示已执行的入口参数，**本文未运行这些命令**：

```text
perpetual_303_research.py --protocol protocols/PERPETUAL_303_RESEARCH_20261003_V1.json --run-dir /home/xflops/coin-state/d045-perpetual-303-research-20261003-v1 --output reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json --experiment-id D045-303-RESEARCH-V1 --period 303D
audit_perpetual_303_research.py --protocol protocols/PERPETUAL_303_RESEARCH_20261003_V1.json --actual reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json --run-dir /home/xflops/coin-state/d045-perpetual-303-financial-independent-20261003-v1 --output reports/fast_research/PERPETUAL_303_RESEARCH_INDEPENDENT_20261003_V1.json
compare_perpetual_303_results.py --binding protocols/PERPETUAL_303_ECONOMIC_COMPARISON_BINDING_20261003_V1.json --run-dir /home/xflops/coin-state/d045-perpetual-303-economic-comparison-20261003-v1 --output reports/fast_research/PERPETUAL_303_ECONOMIC_COMPARISON_20261003_V1.json
accept_perpetual_303_research.py --binding protocols/PERPETUAL_303_RESEARCH_ROOT_BINDING_20261003_V1.json
```

**下一步边界：** D046 只处理 step/min-notional 与 risk-order 完成判据，保留 D045 四个 LS NE 及原前缀字节。修复后同四条件完整账本再次独立核验；不降低 caps、费用、容差，不改变 funding 假定，不以结果驱动信号调参。SMA 的完整 LO/SO 负结果和 HOLD 强参考继续保留；投资行动仍 CASH/NONE。
