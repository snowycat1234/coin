# D079：50USDT主动调仓区间，能力通过但配方不采用

D079正常Spot主动调仓门槛默认0，显式50只允许同信号/资格且组件风险target未下降的主动调整；原入场/信号变化/必要减仓/实际caps/终止/已开始partial保持。真实2共享10k/303日账户，606原目标值不变；每账户246成交/246拒主动goal，独立核492成交/872640分钟/606日及全部拒单/无费用桥。基础净626.52 vs原组合630.73少4.21，省费用执行2.26而gross少6.47；压力净605.60 vs609.23少3.62，省3.26而gross少6.88。日vol8.077%/分钟DD6.676%略降，但事前双成本net提升标准失败，不采用BAND50。保留原Spot防御组合/HOLD8收益参照和门槛默认关闭能力，投资NONE/CASH/APR NE。原失败fixture顺序14pass/1fail与旧字节保留，修正仅测试身份后15pass，账户源未变，QUOTE/received默认逐字段同旧Git。残仓0.000486/0.000299USDT保留，liquidated return NE；无分钟自动漂移减仓/原生/独立OOS认证。主79.41s/RSS767.59MB/共享采样1.252GB，新STATE26.86MB，整盘实扫28.608GB@2026-10-05T04:01:56.827989Z（工件前）。停止门槛网格；reopen需新的具体成本或执行证据。下一有限4h信号Donchian挑战者，沿用同Spot价格/成本/共享本金与过去日协方差，比较现日线防御组合，回答信号节奏是否为主要阻碍；只一个固定配方/两成本，无新池/下载/HPO，尚未启动。原N/signed/风险caps/资源/锁数据/资金边界保持，两采集验收时实际存活。

## 真实净收益与风险

同Spot固定50/50 HOLD10+EXIT10/REENTRY20，所有606原目标值与D078精确相同，只换主动执行区间。对照保存原完整钱包；HOLD8额外参照，两者不重跑、不平均独立NAV。完整本金10k/303已见日，Binance Spot价格配用户Bybit VIP0 10bp/侧费用。

| 指标 | 原组合 BASE | BAND50 BASE | 原组合 STRESS | BAND50 STRESS |
|---|---:|---:|---:|---:|
| marked净USDT | 630.728149 | 626.517969 | 609.225754 | 605.604585 |
| 成本加回gross诊断USDT | 677.395373 | 670.922758 | 676.509136 | 669.628798 |
| 费用USDT | 25.921507 | 24.664824 | 25.865153 | 24.612247 |
| 执行成本USDT | 20.745717 | 19.739966 | 41.418229 | 39.411966 |
| 实际日收益年化波动% | 8.118275 | 8.077115 | 8.110882 | 8.069534 |
| 日终MDD% | 6.147015 | 6.032694 | 6.187058 | 6.070718 |
| 分钟MDD% | 6.822506 | 6.675626 | 6.862130 | 6.712775 |
| 成交数 | 337.000000 | 246.000000 | 337.000000 | 246.000000 |
| 成交名义/完整本金 | 2.593161 | 2.467443 | 2.588533 | 2.463143 |
| 平均gross/net% | 14.938183 | 14.857186 | 14.923753 | 14.841597 |
| 峰gross/net% | 27.663884 | 27.681249 | 27.637970 | 27.655340 |
| 峰单币% | 20.925345 | 20.924975 | 20.905711 | 20.905340 |

### 损益、原因与时间解释

**SPOT_BASE36**资产贡献：BTCUSDT净629.789408USDT、成本29.682907；ETHUSDT净-3.271439USDT、成本14.721883。

| 已保存目标原因 | 成交数 | 名义USDT | 费用+执行USDT |
|---|---:|---:|---:|
| DISCRETIONARY_REBALANCE | 47 | 4202.609790 | 7.558651 |
| FIRST_ENTRY | 2 | 631.405872 | 1.135622 |
| SIGNAL_COMPONENT_CHANGE | 19 | 11356.482131 | 20.437420 |
| VOLATILITY_RISK_REDUCTION | 174 | 7329.099267 | 13.193657 |
| TERMINAL_EXIT | 4 | 1154.833143 | 2.079439 |

**SPOT_STRESS52**资产贡献：BTCUSDT净615.513380USDT、成本42.790436；ETHUSDT净-9.908795USDT、成本21.233776。

| 已保存目标原因 | 成交数 | 名义USDT | 费用+执行USDT |
|---|---:|---:|---:|
| DISCRETIONARY_REBALANCE | 47 | 4204.048563 | 10.913065 |
| FIRST_ENTRY | 2 | 631.406078 | 1.639033 |
| SIGNAL_COMPONENT_CHANGE | 19 | 11336.958795 | 29.467982 |
| VOLATILITY_RISK_REDUCTION | 174 | 7308.376143 | 19.009526 |
| TERMINAL_EXIT | 4 | 1150.636988 | 2.994607 |

SPOT_BASE36 三连续101日净增量：-6.421611, 2.179178, 0.032253USDT；起点为各账户真实当时NAV，不重置/拼接。

SPOT_STRESS52 三连续101日净增量：-5.948919, 1.876340, 0.451410USDT；起点为各账户真实当时NAV，不重置/拼接。

减少91笔成交并没有删除245笔旧小额交易，也没有省下旧小额cost全部9.53USDT。目标执行改变了整个库存路径；本次实际成本只省2.262434/3.259170USDT，价格/实际数量毛损益少6.472615/6.880339，净桥−4.210180/−3.621169。gross为同净收到数量路径成交时成本加回诊断，不是另外的无费用策略。新账户BTC仍贡献主要收益、ETH贡献按真实金额保留，不按结果删币。目标原因是当时策略意图/风险类别，不能把一笔平仓利润全归给原因；第一实际入场可重新标记FIRST_ENTRY，其余以真实target_reason或UNKNOWN汇总。没有声称原因统计证明因果alpha。

## 变化与护栏

正常BacktestConfig新增discretionary_rebalance_min_notional，默认0关闭。开启时只接受显式Boolean discretionary_rebalance/String target_reason，缺失为False/UNKNOWN保护。目标flags仅依赖当前/上一可用组件：首次、资格变化/丢失、任一整个池组件raw向量变化、当前资产任一组件风险target严格下降均不允许skip。实际606flags：INITIAL2/SIGNAL20/RISK292/DISCRETIONARY292。所有原target/raw/时间身份值与D078完全一致。

执行时先遵守原expiry/gap/min-hold/因果，再对当前open价格/NAV及真实base数量计算完整请求，只有严格<50的明确主动goal可不交易。首次真实库存、零目标/终止、risk_forced、当前risk_limited、任何当前asset/gross超cap、已开始partial均豁免；容量截断的小fill不是small-goal。skip写order但无trade/fee/cash/inventory变化，等待下一原目标，不延长退出次数。0门槛保留原字段/数值，实际两费用模式小输入与精确Git6ef2256旧源码所有trades/orders/daily/roundtrips/summary相等；旧源码仅小型独立测试reference，活动实现没有版本/日期AST包装。

## 实际验收、失败与限制

第一次fixtures14pass/1fail：新增另一资产超限反例让BTC先完成减仓，轮到ETH时cap已恢复，错误预期ETH仍豁免。原source/XML/实际exit1保留；只换测试identity为ZZZ，使ETH先处理时其他币仍超cap。第二次15pass/33.59s，账户source8672bcd8保持；反例包括skip不变现金库存、protected小额减仓、自己/其他币caps、首次entry、partial残额继续、zero/terminal、unknown/非法声明、全池signal变化/1e−15风险缩减和旧默认精确一致。未重跑无关旧验收。

实际2新账户一次完整回放。独立Decimal核492成交、872640分钟/606日资金与NAV、fees/execution一次扣款；旧D078组件手动mix/cov/未来OHLC×1.17扰动reference在新目标上实跑通过，早406目标不变/晚106改变。独立band检查不调用活动flag/account：读取受SHA固定原minute open、保存order/trade顺序，逐条重建当时现金/数量/NAV、拒单<50/无fill/未越cap/非started，两个账户各246拒goal和200受保护/已开始fill，末NAV误差0。target值全同旧D078。金融/timing通过不是native/alpha认证。

Spot仍没有连续minute漂移主动减仓调度，不能把本轮band保护冒称新能力；两个全minute-close轨迹均未超abs.3/gross.6。数据缺口/实际caps超限依事前规则停止投资评价。quantity/min10仍历史研究假设，Bybit原生盘口/过滤器未认证。真实正残仓0.000485758/0.000298608USDT保留，marked账户日历完整而现金清仓收益NOT_EVALUABLE。不启封heldout，不使用keys/เงินจริง/交易所订单/API/下载/付费/GPU；维持5GB/swap0/40GB。

主79.405424s、RSS767594496B、共享实际采样1251946496B，新owned26863220B；独立金融0.273243s、target0.551513s、band0.218482s。全ROOT+整个D VHD实扫28607639240B在2026-10-05T04:01:56.827989Z，早于本轮工件与采集增长，不当作结束后的精确总量。8765实际进度和扫描时刻沿用原服务，两采集验收时真实存活；未认证72h/真实有效前向日。两个子agent权限中断后root接手其未完成的小验证，未声称它们完成全部审查，也未重新启动市场任务。

## 采用与下一步

事前要求两成本净提高且波动/minuteDD不恶化。风险略降但净均降低，BAND50不采用；保留正常门槛能力默认关闭、旧防御组合和HOLD8。拒绝网格寻找事后赢家；reopen需新的具体执行/成本证据或独立窗口先验假设，不因这个单窗口删除整个低换手能力方向。投资NONE/CASH、长期APR未建立。

主要阻碍继续是价格参与时机与时间稳定性，成本局部优化不足以解释长时段差距。下一项只选一个固定4h Donchian信号挑战者，复用已登记公开hook和原分钟缓存，完整同Spot账户对照日线防御组合/HOLD8；过去日协方差/总资本/成本/caps不变，日risk与4h信号/分钟执行明确分开。4h改变的是信号信息节奏，事前固定一个配方/两成本，禁止周期网格/按币选择/新数据资格。旧Turtle结果保存，不把这个研究宣称全市场bot水平；若成本/风险/净无有价值增量就保留主力。下一尚未实现或启动，无后台科研承诺。

## 可复现

本模块Git与原协议，原受SHA缓存可用，使用独占新STATE/output。旧D078及以前按各原Git，历史证据不覆盖。

```bash
scripts/with_task_progress.sh --title '50USDT主动调仓' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_DISCRETIONARY_BAND50_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_ACCOUNT_DIRECTORY --output reports/fast_research/NEW_RESULT.json
scripts/with_task_progress.sh --title '独立金额' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_FINANCE_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立目标与拒单' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_DISCRETIONARY_BAND_USED_METADATA_20261005_V1/d079_band_independent.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_BAND_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立过去目标' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_DEFENSIVE_BLEND_USED_METADATA_20261005_V1/d078_target_reference.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_TARGET_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '保存经济诊断' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_saved_economic_diagnostics.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_DIAGNOSTIC_DIRECTORY/RESULT.json
```
