# D084_ORIGINAL：HOLD过去趋势门控的收益与防御取舍

D084完成唯一HOLD腿过去close>SMA200门控的四个真实Spot钱包。原303日净330.09/307.83USDT，比原日线组合少300.64/301.40；日vol约8.12%→6.33%、分钟DD约6.82%→4.64%（stress4.75%）。后90日HOLD及Donchian皆零目标，真实全程CASH：净/fee/turnover/vol/DD均0，比原组合少亏330.70/333.92，但这不是新增价格alpha。事前两窗联合净改善标准未通过，不替换日线组合/HOLD8；门控能力保留、固定配方暂停，投资NONE/CASH。两路采集在WSL进程丢失后已保存三件套并单次恢复，新会话/断档真实记录，两次观测推进，非有效天认证。

## 同市场与完整资本对照

303已见开发日、共享10,000 USDT、Binance Spot价格配Bybit用户VIP0费用，非Bybit原生证据。

| 指标 | 控制 SPOT_BASE36 | 新配方 SPOT_BASE36 | 控制 SPOT_STRESS52 | 新配方 SPOT_STRESS52 |
|---|---:|---:|---:|---:|
| marked净USDT | 630.728149 | 330.091501 | 609.225754 | 307.825940 |
| 同数量成本加回gross诊断 | 677.395373 | 379.361137 | 676.509136 | 378.841618 |
| 费用USDT | 25.921507 | 27.367088 | 25.865153 | 27.300091 |
| 执行成本USDT | 20.745717 | 21.902548 | 41.418229 | 43.715586 |
| 日收益年化波动% | 8.118275 | 6.334026 | 8.110882 | 6.327851 |
| 日终MDD% | 6.147015 | 4.117657 | 6.187058 | 4.227049 |
| 分钟MDD% | 6.822506 | 4.638541 | 6.862130 | 4.746840 |
| 成交数 | 337.000000 | 210.000000 | 337.000000 | 210.000000 |
| 换手/本金 | 2.593161 | 2.737789 | 2.588533 | 2.732166 |
| 平均gross% | 14.938183 | 10.668510 | 14.923753 | 10.658259 |
| 平均net% | 14.938183 | 10.668510 | 14.923753 | 10.658259 |
| 峰gross% | 27.663884 | 22.588634 | 27.637970 | 22.567075 |
| 峰单币% | 20.925345 | 21.065978 | 20.905711 | 21.046079 |

当前两个新账户保留正库存价值0.000117092,0.000037875USDT，liquidated return=NOT_EVALUABLE,NOT_EVALUABLE。

## 两窗经济与机制

只改变HOLD腿可得日close严格大于过去200日均值时允许原目标；相等或低于均值时该腿为现金。原full HOLD过去30协方差预算10%先缩，再乘gate与.5，不重新分配空闲预算；Donchian prior20/SMA200入场、prior10退出/20再入场、.5权重完全保持。不是原公开Jesse策略的完整复刻，SMA reduction与既有Donchian/正常账本复用，无新依赖或模型。

原303日新gross379.36/378.84、fee+exec49.27/71.02USDT，净330.09/307.83。相对原组合gross少298.03/297.67、费用执行额外2.60/3.73，主要差距是机会损益，不能归因于交易成本；成交数337→210，但成交名义换手2.593→2.738，笔数下降并不等于成本下降。分钟DD6.82%→4.64%（stress6.86%→4.75%），日vol8.12%→6.33%，相同caps不称相同实际风险。月份配对中Feb2025少亏132.62/132.35，Sep/Nov/May净增量均负；逐币/月/连续101日资金桥见绑定DIAGNOSTIC，不删日期、不把门控退出标签称为因果PnL。

后90日门控策略真实全程现金（两资产所有target0，全部分钟NAV=10k，0真实成交/0库存/0成本/0波动）。原日线组合仍净-330.70/-333.92，其gross价格损失约322.52/322.11、费用执行8.19/11.81；门控改善是避免暴露，不能称主动价格alpha，更不能与原303日策略事后拼赢家。后窗单独条件通过，但原303失败，因此按事前四情景联合标准不采用；能力与防御取舍证据保留。投资NONE、USDT现金参照无利息、长期APR NOT_EVALUABLE。

原303新账户末库存0.000117092/0.000037875USDT仍在NAV、liquidated return NOT_EVALUABLE；后90新账户库存0、COMPLETE_CASH_RETURN。完整10k本金、received-asset fee、Bybit用户VIP0与Binance Spot输入、原5次退出/1e-8数量/min10/abs.3/gross.6保持，非Bybit原生、数量/最低订单历史规则未认证。原副本/旧失败/locked正文均未改或启封。

独立scalar期望值不调用producer，original目标误差5.55e-17、later0；两窗future扰动早期0，修改后正常默认target/raw与保存旧组合golden差均0。独立Decimal现金/收到资产费/库存/完整分钟caps真实通过（内部0.218/0.070s）；必要回归不重跑旧模型或无关账户。正常验收新增显式paired acceptance，原窗口经济决定引用后窗口已接受身份/非重叠日期/相同核心producer/cost，再按两个窗口全部条件决定；后窗局部pass不是整版采用。

首次batch前四阶段正常，后窗口在source guard因我修改acceptance helper停止，尚未创建后钱包或读取回放输入；25.64s失败完整保留在SPOT_HOLD_TREND_BATCH_20261005_V1.json。实际失败时helper完整字节SHA未记录为UNKNOWN，不伪造精确失败源码；V1原绑定与Git旧helper保持，V2仅更新该辅助SHA/operational_rebind说明，策略/数据/日期/费用不变。原303成功钱包不重复，remaining batch只执行尚未运行四阶段。两批命令单调时间219.10+175.45=394.54s（不重叠、含失败），不冒充整轮/model/并行运维总耗时；主账户内部95.94/83.99s，RSS768.85/399.34MB、共享采样峰1210.73MB，wallet owned26.83MB。没有HPO/fit/新市场下载或API；采集恢复是原授权公开WS独立运维活动，不伪称全轮零网络。

## WSL断档与原采集有限恢复

当前boot6a60eca0-0809-4173-aca8-3f0ffac188be与D075保存boot不同，检查时仅启动约1分钟，旧两进程缺失；具体退出码和重启发起原因UNKNOWN，不猜OOM。原日志/host/task、检查点、audit、DB+可用WAL/SHM先保存50.81MB；仅SQL打开衍生副本，闭合备份quick_check均ok、原源绑定一致。原L1 catalog2368文件/113,562,485B逐个流式bytes/SHA一致（234.30s、RSS20.40MB），不是重新认证数据有效性/健康天。

单次用原.venv/默认DB/store/public_v3/L1_v1启动，不新建采集服务或改冻结source。public旧session7留下UNGRACEFUL_PREVIOUS_SESSION并开新会话；L1记录RESTART_GAP与未知未提交尾。两次实际PID/start_ticks/cgroup、新heartbeat推进120,140ms、每币closed bars推进、micro checkpoint推进107,008,758us/accepted事件16,623，errors[]；只是这两时点恢复活跃，不拼旧running JSON或有效天，alpha资格0。host已有holder已失效，恢复一个隐藏bounded WSL连接helper维持原运行，未改系统电源/自动登录/资源规则；8765 api errors[]。运维副本与原库留D，不入Git。归档metadata只保存必要凭证。恢复准备与科学任务部分并行，时间不能相加冒充整体。

最新实际扫描按绑定的恢复launch容量与两科学结果时间比较，进度窗口显示最晚一次的真实扫描时间，非当前post总量；守卫每次仍实扫，原5GB/swap0/GPU0/D40GB不变。报告绑定结果与验收是代理开发证据；本轮不认证长期稳定收益。

## 工件与可复现命令

- result: `/mnt/d/codex/coin/reports/fast_research/SPOT_HOLD_TREND_ORIGINAL_20261005_V1.json`，SHA `1b55aae2955a4ca2a584760b232a1b826753fa3b0cd017b0a0c172f4d3b202df`。
- protocol: `/mnt/d/codex/coin/protocols/SPOT_HOLD_TREND_ORIGINAL_20261005_V1.json`，SHA `82a7588bea2e8b2dd9cebee52127ec22ff9ea34125376f1b3ebf823a6c010713`。
- financial: `/home/xflops/coin-state/d084-hold-trend-gate-20261005-v1/ORIGINAL_FINANCIAL.json`，SHA `c70034a4639e65da04d9c7a36f7a0f18a4cd80cadd39967bd50e5a32b715bca2`。
- targets: `/home/xflops/coin-state/d084-hold-trend-gate-20261005-v1/ORIGINAL_TARGETS.json`，SHA `3ad72b6bf80dd9faa12ba75640cd1a08204f371f1ed8922ee3386128fda86d38`。
- diagnostic: `/home/xflops/coin-state/d084-hold-trend-gate-20261005-v1/ORIGINAL_DIAGNOSTIC.json`，SHA `04dbc8cc24687506a6d8c7fe4b2b51003d6b1f75878e397a02dd5c9c7175fa0b`。
- paired_acceptance: `/mnt/d/codex/coin/reports/SPOT_HOLD_TREND_LATER_ACCEPTED_20261005_V1.json`，SHA `858d76364084c32475b0a8e22ffbc3588703657673ea8b7529990ebfdbc554cc`。

实际完整回放的逐阶段命令与原失败/续跑配置保存在本模块archive。重放时为钱包及报告指定新的STATE目录，并同步修改消费者input，不能覆盖已接受工件。当前可直接复核保存钱包及目标因果性（不回放市场）：

```bash
scripts/with_task_progress.sh --title '保存门控钱包独立核账复核' -- env PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/SPOT_HOLD_TREND_ORIGINAL_20261005_V1.json --output /home/xflops/coin-state/NEW_GATE_FINANCIAL.json
scripts/with_task_progress.sh --title '保存门控目标因果与旧默认复核' -- env PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/audit_daily_spot_targets.py --input reports/fast_research/SPOT_HOLD_TREND_ORIGINAL_20261005_V1.json --output /home/xflops/coin-state/NEW_GATE_TARGETS.json
```

后90日用对应LATER结果及不同新output路径。协议父HEAD属于实际原运行，不把新复核或重放身份写成旧实验。