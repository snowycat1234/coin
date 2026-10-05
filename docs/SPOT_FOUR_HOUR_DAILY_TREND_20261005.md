# D081：日线趋势过滤负结果与快速工作流

D081日SMA200替换4hSMA200入场过滤（非双SMA AND），退出/risk/4h执行/本金/cost保持；两303日账户净350.81/281.85USDT，比原4h少291.31/280.53，省成本18.58/26.75却毛损益少309.89/307.28；分钟DD升至8.908%/9.118%，不采用。原日线防御组合/HOLD8保留，投资NONE/CASH；新配方不是低成本改善。当前工作流已按用户采纳收拢为单状态/薄证据引用与复用收尾，旧结果按Git/工件保留。

## 同市场与完整资本对照

303已见开发日、共享10,000 USDT、Binance Spot价格配Bybit用户VIP0费用，非Bybit原生证据。

| 指标 | 控制 SPOT_BASE36 | 新配方 SPOT_BASE36 | 控制 SPOT_STRESS52 | 新配方 SPOT_STRESS52 |
|---|---:|---:|---:|---:|
| marked净USDT | 642.127556 | 350.813006 | 562.380961 | 281.852250 |
| 同数量成本加回gross诊断 | 818.732724 | 508.840831 | 816.191826 | 508.909728 |
| 费用USDT | 98.096399 | 87.777542 | 97.571112 | 87.286563 |
| 执行成本USDT | 78.508769 | 70.250282 | 156.239753 | 139.770914 |
| 日收益年化波动% | 7.848688 | 7.939340 | 7.844475 | 7.942766 |
| 日终MDD% | 7.364802 | 8.286744 | 7.535349 | 8.516882 |
| 分钟MDD% | 7.996713 | 8.908450 | 8.142597 | 9.117683 |
| 成交数 | 899.000000 | 839.000000 | 895.000000 | 830.000000 |
| 换手/本金 | 9.813534 | 8.781248 | 9.764862 | 8.735608 |
| 平均gross% | 13.762987 | 13.441442 | 13.750010 | 13.428508 |
| 平均net% | 13.762987 | 13.441442 | 13.750010 | 13.428508 |
| 峰gross% | 29.222133 | 27.710943 | 29.185491 | 27.685193 |
| 峰单币% | 20.896940 | 21.320110 | 20.876935 | 21.299712 |

保存经济参照净630.728149,609.225754USDT；当前两个新账户保留正库存价值0.000578821,0.000413909USDT，liquidated return=NOT_EVALUABLE,NOT_EVALUABLE。

本次替换trend property上下文，原filter_trend/entry/channel及COIN exit10保持。hook只在200连续4h与200连续已完成日资格/availability核对后读daily6col，floor日端排除未完日；HOLD日target向前携带，全部risk用30日日收益，N身份顺序保持。默认None日/4h目标及完整旧meta与Git7a239eb一致。7最终fixtures通过；V1 5fail/1pass为synthetic prior20未严格突破，producer未改，V2 6pass、V3 7pass及各used字节/退出码保留。当前3636目标独立scalar日SMA/通道进出场/centered日cov/mix最大误差2.8e-17，BTC23入22出、ETH11/11；独立金融1669成交/872640分钟/606日通过。已接受日/4h/分钟缓存按SHA复用、不复制新行情，无新增数据/API/fits/HPO/资金权限。

实际源与参考/诊断由路径/SHA绑定，只归档一次，验收JSON不再嵌入完整多个结果。新通用收尾不要求正/负收益才能接受工程结果；现有研究采用标准仍是事前“双成本净改善且vol/分钟DD不恶化”，本轮保持，不为新提示词回改。其他取舍要在未来新实验前明确。collector仅当时进程运维快照，不是独立历史账户通过条件；两现有进程未停止。

新批处理单调时间只覆盖该命令；旧三轮按真实task时间区间并集汇总，不复造单调历史或全会话端到端，也不把未归因时间叫模型思考。精确model/推理配置UNKNOWN，未更改全局设置。该批验证原收尾与批收尾核心完全一致，再读资产经济桥，不重放市场。当前real-time进度服务沿用。硬资源规则不改：主84.43s/RSS765.28MB/共享采样1.265GB、新owned27.26MB；整盘28.697GB@2026-10-05T04:53:03.328414Z为工件前扫描，不是当前精确值。

代理Spot的数量/min10/末5次退出与原生历史过滤器仍未认证，positive dust保留，清仓收益NOT_EVALUABLE。无连续分钟漂移减仓或原生执行认证；全部保存minute-close未超caps。源已见开发角色不改，未启封holdout/keys/真钱/发单/付费/GPU。macro失败仅否定本配方/窗口，不能永久取消多周期/短仓/N币/开源模型能力。


## 工件与可复现命令

- result: `/mnt/d/codex/coin/reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json`，SHA `39942c22085f2835a3f72b6cd7b2fba3ebce9f8170e14d8e871a7b76e3ac81a5`。
- protocol: `/mnt/d/codex/coin/protocols/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json`，SHA `b6ccf04003b419c60f3d78226e85aae6d5d91fd80c6dd0cdbe4786ef10c94daa`。
- financial: `/home/xflops/coin-state/d081-spot-financial-independent-20261005-v1/RESULT.json`，SHA `6a6f5a11c24862b14540f3333ff486af77456389ecf577488638192040a2d882`。
- targets: `/home/xflops/coin-state/d081-actual-target-reference-20261005-v1/RESULT.json`，SHA `65f9a32ccc476a6dfc1ff76e0414f8c48e7d8d35b23020fc72cc613917e5bbcc`。
- diagnostic: `/home/xflops/coin-state/d081-spot-saved-diagnostics-20261005-v1/RESULT.json`，SHA `f35b1fdb60ba2eb162813994004f2de26d3d9e4600fdd3c13475bc33d4846813`。

```bash
scripts/with_task_progress.sh --title '固定macro回放' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_RUN --output reports/fast_research/NEW_RESULT.json
```
