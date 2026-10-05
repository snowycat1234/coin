# D082_BLEND：来源角色与固定后段开发经济验证

D082复用已接受May2025-Feb2026两币月源，完整200日预热；Dec2025-Feb2026为已见90日开发验证。固定HOLD8净-525.58/-530.83USDT，日线防御组合净-330.70/-333.92，少亏194.88/196.91、分钟DD约9.00%→5.71%；但两者均落后同USDT资本CASH0。两币Donchian90日零入场/零敞口，防御组合只是半份HOLD10，降低暴露不是新增alpha。保留研究参照、投资NONE/CASH；不拼接此前303日钱包。

## 同市场与完整资本对照

90已见开发日、共享10,000 USDT、Binance Spot价格配Bybit用户VIP0费用，非Bybit原生证据。

| 指标 | 控制 SPOT_BASE36 | 新配方 SPOT_BASE36 | 控制 SPOT_STRESS52 | 新配方 SPOT_STRESS52 |
|---|---:|---:|---:|---:|
| marked净USDT | -525.581007 | -330.703786 | -530.830289 | -333.923746 |
| 同数量成本加回gross诊断 | -512.038309 | -322.517271 | -511.294478 | -322.111751 |
| 费用USDT | 7.522475 | 4.547315 | 7.510327 | 4.541002 |
| 执行成本USDT | 6.020223 | 3.639200 | 12.025484 | 7.270993 |
| 日收益年化波动% | 9.824893 | 6.137025 | 9.816875 | 6.132140 |
| 日终MDD% | 8.373732 | 5.304422 | 8.377171 | 5.306449 |
| 分钟MDD% | 8.994013 | 5.705515 | 8.997821 | 5.707743 |
| 成交数 | 119.000000 | 92.000000 | 119.000000 | 92.000000 |
| 换手/本金 | 0.752569 | 0.454927 | 0.751675 | 0.454490 |
| 平均gross% | 15.862476 | 9.898244 | 15.847237 | 9.888726 |
| 平均net% | 15.862476 | 9.898244 | 15.847237 | 9.888726 |
| 峰gross% | 27.321476 | 17.116098 | 27.295700 | 17.099827 |
| 峰单币% | 13.836662 | 8.635085 | 13.823561 | 8.626855 |

当前两个新账户保留正库存价值9.505677849,8.964867032USDT，liquidated return=NOT_EVALUABLE,NOT_EVALUABLE。

来源20个唯一月文件（May2025-Feb2026）来自三份已接受Spot来源；Oct/Nov重复catalog成员核SHA一致，未拼接钱包。私有lock只核SHA，正文未读。源QA标REUSED，当前完整字节SHA与footer重验；V1因旧凭证没有normalized_bytes停止第三文件、没有回放；修复只把大小记为当前测量值，旧SHA仍逐个匹配，失败源码/任务和未运行模板V1保留，实际两模板绑定V2。没有download/API/模型训练/参数搜索，源报告和旧协议证明这些日期已有选择使用；无法据此认证任何unused或unseen历史。

正常Spot runner去掉303日/36源/两币账户硬编码，按配置整UTC日、唯一来源/有序标的计算，旧默认仍303日/原窗口、4h研究仍限已有单独warmup路径。HOLD8可作无永续peer的完整Spot参照，第二配方复用其SHA缓存；原现货库存、received-asset fee、quant backtest字节、5次末退出/1e-8数量/min10、abs.3/gross.6保持。日信号与完整分钟成交/mark分开；两资产并行身份进入同一10k钱包。四钱包是对照而非叠加40k组合，日账连续分三30日，不平均/事后缩放原NAV。

独立Decimal逐成交、费用一次与末库存/完整分钟风险，以及独立scalar prior20/SMA200/prior10、centered past30日Gram、两种预算/组合目标全部真实执行。未来扰动在正常producer也执行，早期目标不变。信号计算没有调用producer生成期望值；未来扰动才单独调用producer。日线防御90日EXIT10 raw与scaled全零，保存目标与数学派生5%过去风险HOLD的差6.94e-18；这是只读目标机制诊断，HOLD5钱包NOT_RUN，不提供其净值/收益。改善约189USDT来自不同持仓价格损益，约5.36/7.72来自低成本；不把不同实际风险称匹配alpha。原gross为同数量成本加回诊断，不是可交易无成本收益。

四账户皆marked、未完整cash清仓；防御末库存约9.51/8.96USDT仍在NAV，liquidated return=NOT_EVALUABLE，未免费删除或延长退出。CASH是相同USDT资本、无利息/无交易参考，不是实际账户资格。实际日vol约HOLD8 9.82%/防御6.14%，预算不是实际波动保证；保存分钟close无观测caps违约不认证intraminute或连续漂移风险控制。Bybit用户成本配Binance Spot价格、min/lot未原生历史认证，投资/APR仍NONE/NOT_EVALUABLE。

批次八阶段全0/单调时间343.11s，仅此命令；主wallet内部73.54/79.56s包含守卫/hash/save，最大阶段112.55s（防御账户）。来源成功87.61s另计，源首次失败与上下文/实现/文档未包含，不宣称整轮5.72分钟。主进程RSS410.22/405.97MB、共享采样932.17MB；最后账户前整盘28,779,163,108B@2026-10-05T05:48:44.806157Z是实测pre-scan，不冒充当前值。collector只运维快照，不是历史通过门槛。Git核验改为可选既有native binary、一次tracked清单、60s单调用超时；新post耗时待实际测量，不先声称提速。
复现须使用本模块Git原字节与已保存D盘来源/STATE；上面的命令重跑两个防御钱包，并引用原HOLD8控制缓存。HOLD8另用protocols/SPOT_LATER_HOLD8_20261005_V1.json与独立NEW_LATER_HOLD目录/输出重跑；旧成本/控制钱包不被覆写。已关闭batch_config仅为实际argv记录，不能原路径重复执行。


## 工件与可复现命令

- result: `/mnt/d/codex/coin/reports/fast_research/SPOT_LATER_BLEND_20261005_V1.json`，SHA `af1d89f9ca5cdf6180c431eb17a426a99cfc7ec513896374ad3e698dd02080c8`。
- protocol: `/mnt/d/codex/coin/protocols/SPOT_LATER_BLEND_20261005_V1.json`，SHA `af38a62b8c16e1f09622360fe710c0b2ca4cf8a38587e14394ace9ba85db0a56`。
- financial: `/home/xflops/coin-state/d082-later-spot-20261005-v1/BLEND_FINANCIAL.json`，SHA `f4d4dc42b4a804ef99d80c02432eb55ec63e7b2259a99e4e9196dce579b409eb`。
- targets: `/home/xflops/coin-state/d082-later-spot-20261005-v1/BLEND_TARGETS.json`，SHA `576ce8b344bb29cc3db78e20dc7fc2e665d94f89b953d68dee82c499c00fcbc8`。
- diagnostic: `/home/xflops/coin-state/d082-later-spot-20261005-v1/DIAGNOSTIC.json`，SHA `f3e447ec1be14dde4e08549468acdb3905cc8dbb4e553ec908f4b8b648cfedff`。

```bash
scripts/with_task_progress.sh --title '复现固定后段防御账户' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_LATER_BLEND_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_LATER_BLEND --output reports/fast_research/NEW_LATER_BLEND.json
```
