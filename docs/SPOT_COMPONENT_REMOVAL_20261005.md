# D083_ORIGINAL：真实组件移除与收益集中度

D083在相同10k本金/费用/执行/日期下完成半份HOLD10组件的四个新钱包。303日完整组合相对半HOLD净多230.25/217.43USDT，但实际日波动5.30%→8.12%、分钟DD5.65%→6.82%；11月增量333.48/330.97，其余月份合计-103.23/-113.53，不能证明稳定择时alpha。另90日组合与半HOLD逐笔成交、全部分钟NAV完全相同，净-330.70/-333.92USDT，Donchian零参与。保留半HOLD诊断控制/日线组合防御参照/HOLD8，半HOLD不替换主力；投资NONE/CASH，长期APR不可评价。

## 同市场与完整资本对照

303已见开发日、共享10,000 USDT、Binance Spot价格配Bybit用户VIP0费用，非Bybit原生证据。

| 指标 | 控制 SPOT_BASE36 | 新配方 SPOT_BASE36 | 控制 SPOT_STRESS52 | 新配方 SPOT_STRESS52 |
|---|---:|---:|---:|---:|
| marked净USDT | 630.728149 | 400.474962 | 609.225754 | 391.792134 |
| 同数量成本加回gross诊断 | 677.395373 | 418.933527 | 676.509136 | 418.415843 |
| 费用USDT | 25.921507 | 10.252861 | 25.865153 | 10.234642 |
| 执行成本USDT | 20.745717 | 8.205704 | 41.418229 | 16.389068 |
| 日收益年化波动% | 8.118275 | 5.296748 | 8.110882 | 5.292370 |
| 日终MDD% | 6.147015 | 5.156499 | 6.187058 | 5.172409 |
| 分钟MDD% | 6.822506 | 5.652993 | 6.862130 | 5.668937 |
| 成交数 | 337.000000 | 273.000000 | 337.000000 | 273.000000 |
| 换手/本金 | 2.593161 | 1.025680 | 2.588533 | 1.024251 |
| 平均gross% | 14.938183 | 9.153909 | 14.923753 | 9.145110 |
| 平均net% | 14.938183 | 9.153909 | 14.923753 | 9.145110 |
| 峰gross% | 27.663884 | 13.919891 | 27.637970 | 13.906617 |
| 峰单币% | 20.925345 | 7.017103 | 20.905711 | 7.010404 |

当前两个新账户保留正库存价值0.001018923,0.000797549USDT，liquidated return=NOT_EVALUABLE,NOT_EVALUABLE。

## 两个窗口的组件增量

303日半HOLD净400.47/391.79USDT，原组合630.73/609.23；组合新增同数量成本加回gross258.46/258.09，额外fee+exec28.21/40.66。半HOLD273成交，组合337。这是两个完整共享资本账户的配对差，不是独立腿利润之和，风险不匹配，不将11月之外的描述诊断转成可执行日期过滤。各月份/逐币/连续资金分段/turnover/平均峰值gross与net详见绑定结果，原旧NAV不修改。

后段2025-12-01..<2026-03-01的90日两个新半HOLD账户，与D082组合全部分钟NAV差0、成交表精确一致；净-330.703786/-333.923746USDT，日vol6.137%/6.132%、分钟DD5.706%/5.708%，92笔成交。资金费为Spot不适用，未把永续费用或删资金费后的旧账本当Spot。两窗口各自10k、不拼接为长期资本记录，均已见开发筛选。CASH0为同USDT本金无利息参照，没有新增CASH账户或投资资格。

原303日半HOLD末库存0.001018923/0.000797549USDT，后90日9.505677849/8.964867032，仍在NAV；所有liquidated return=NOT_EVALUABLE。没有免费清仓/延长5次退出/删除库存。Bybit用户VIP0收到资产扣费profile与Binance Spot价格不变，数量/最低订单仍历史未认证代理，非Bybit原生或稳定APR。

正常target新增HALF_HOLD10：同日过去200预热/30协方差/10%组件预算后固定乘.5，保留完整10k资本；正常runner使用此目标再实际逐分钟回放，不把旧收益倍乘。独立scalar期望值无producer调用，原/后target误差1.39e-17/6.94e-18、正常producer未来扰动早期差0；独立Decimal与完整分钟资金/库存/费用一次/风险均通过，abs.3/gross.6/原Spot引擎字节不变。旧默认目标接口没有重建包装。

批次8阶段371.0s，主钱包内部74.53/83.18s；主峰RSS748.51/407.40MB，共享采样峰1219.64MB（cgroup历史峰1302.82MB不称本轮峰）。独立资金核验内部0.283/0.117s；参数尝试四钱包、0 fit/HPO/download/市场API。只读配对内部0.829s，不冒充整个阶段或整轮时间。两个钱包输出合计34.83MB；最后实际完整盘扫描28,819,782,555B@2026-10-05T14:21:49.348312+08:00，为后账户前测量，不冒称当前post总量。publisher只将多个绑定结果中最新实际扫描放回既有进度窗口，不新建观察器或省略守卫。两路collector验收时进程快照仍在，只证明该时点运维，不证明健康天/前向alpha。

D076资金费1818原事件/8钱包链已经核对，当前无新单位证据，不重复全核验、不绕过403/451。原始来源/单位限制保持；官方文档只作来源检查，不等于历史同事件单位认证。结构化配对 reports/SPOT_COMPONENT_COMPARISON_20261005_V1.json，后窗口验收 reports/SPOT_HALF_HOLD10_LATER_ACCEPTED_20261005_V1.json。

## 工件与可复现命令

- result: `/mnt/d/codex/coin/reports/fast_research/SPOT_HALF_HOLD10_ORIGINAL_20261005_V1.json`，SHA `e336c47063d8ee079569d5846fc1b2c4be50580403890ff36ba013a19a6d92fd`。
- protocol: `/mnt/d/codex/coin/protocols/SPOT_HALF_HOLD10_ORIGINAL_20261005_V1.json`，SHA `aa8ab49cc4ee807d1c1722cbd34fa0b5e46adb733780cfc3e7ebf53cbb7ce268`。
- financial: `/home/xflops/coin-state/d083-half-hold-component-20261005-v1/ORIGINAL_FINANCIAL.json`，SHA `4262dbfc4008c9ace54b8adf58049002847ac0a32e6c3912dc58753bd475cc31`。
- targets: `/home/xflops/coin-state/d083-half-hold-component-20261005-v1/ORIGINAL_TARGETS.json`，SHA `18cba8ff180d434a7b4ef6ebc202c264beda355a13fea2ba154d3b520fa2c8db`。
- diagnostic: `/home/xflops/coin-state/d083-half-hold-component-20261005-v1/ORIGINAL_DIAGNOSTIC.json`，SHA `cbad5965a7b2f59105f87195e03e6b19889586a483e0eea5e8c3ac4ce03fbb0f`。

```bash
scripts/with_task_progress.sh --title '组件移除四账户与独立核验' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_research_steps.py --config docs/archive/SPOT_COMPONENT_REMOVAL_USED_METADATA_20261005_V1/batch_config.json --output reports/NEW_BATCH.json
```
