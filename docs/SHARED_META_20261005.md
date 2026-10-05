# D090：固定公开双向意图与共享execute/reject

决定：**PAUSE_THIS_FITTED_RECIPE**。投资资格NONE/CASH；长期APR NOT_EVALUABLE。

一个共享binary XGBoost120树depth3 CPU2、零搜参；固定SMA50/200第一层无fit，原should_long/should_short/update_position hooks复用。
第一层为从Sep2024准备的外部意图状态，独立于账户成交/过滤；不是Jesse全余额或原生执行复制。过滤逐日keep/cash，不反转，不重新分配拒绝预算；重新计算过去协方差并完整跑账户。
Sep2024–Feb2025训练，5d标签严格成熟于Mar1前；经济Mar–Jun2025连续122日、10币/完整10k共享资本，各账户重新初始化，不拼接。已见开发out-of-fit，不是unseen。
标签：signed intent×未来5d trade-open收益>37bp，27bp成本+10bp余量只进入边界一次；资金费单位/发布时钟UNKNOWN而排除标签/特征。实际账户另外完整计费/滑点/点差/实际资金费两个解释。
模型输入闭合日价量/ATR/vol/趋势/BTCETH/breadth/onehot symbol+固定方向；无第一层训练内概率，不需学习模型OOF。零意图/未知未来不训练；无early stopping、阈值调整或额外seed。
三策略×两成本×两资金费解释=12个实际账户；最后恢复阶段按SHA复用10个已完成账本、只新增2个，首轮含一个模型拟合。全部相同persistent cash-close、逐仓1x、abs30%/gross60%、过去协方差scale-down。HOLD/现金保留，实际风险不同。
Binance USD-M价格/mark/funding配Bybit用户taker5.5bp：跨场所代理，非Bybit原生。历史数量/保证金层级和瞬时mark极值未认证。

|策略|成本|资金费解释|净USDT|毛USDT|LONG|SHORT|费用/执行|资金费|换手|vol%|DD%|Sharpe|平均gross%|残仓USDT|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|PUBLIC_SMA_INTENT|BASE27|RAW_AS_FRACTION|NOT_EVALUABLE|-74.20|-28.66|-55.28|17.47|7.73|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|UNKNOWN|NOT_EVALUABLE|1182.14|
|PUBLIC_SMA_INTENT|BASE27|RAW_AS_PERCENT|NOT_EVALUABLE|-73.94|-28.79|-62.55|17.47|0.08|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|UNKNOWN|NOT_EVALUABLE|1181.29|
|PUBLIC_SMA_INTENT|STRESS43|RAW_AS_FRACTION|NOT_EVALUABLE|-73.49|-32.23|-61.32|27.78|7.72|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|UNKNOWN|NOT_EVALUABLE|1181.02|
|PUBLIC_SMA_INTENT|STRESS43|RAW_AS_PERCENT|NOT_EVALUABLE|-73.21|-32.35|-68.55|27.77|0.08|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|UNKNOWN|NOT_EVALUABLE|1180.17|
|PUBLIC_SMA_META|BASE27|RAW_AS_FRACTION|-14.44|88.01|180.44|-194.88|109.29|6.83|8.10|8.16|5.44|-0.01|7.44|416.58|
|PUBLIC_SMA_META|BASE27|RAW_AS_PERCENT|-21.06|88.12|180.30|-201.36|109.25|0.07|8.09|8.17|5.48|-0.04|7.45|416.58|
|PUBLIC_SMA_META|STRESS43|RAW_AS_FRACTION|-78.06|88.69|164.73|-242.79|173.57|6.82|8.07|8.16|5.80|-0.25|7.45|416.58|
|PUBLIC_SMA_META|STRESS43|RAW_AS_PERCENT|-84.26|89.15|164.60|-248.86|173.47|0.07|8.07|8.17|5.84|-0.27|7.45|416.58|
|HOLD|BASE27|RAW_AS_FRACTION|130.25|150.09|130.25|0.00|9.87|-9.97|0.73|10.56|6.58|0.42|10.30|192.80|
|HOLD|BASE27|RAW_AS_PERCENT|140.16|150.14|140.16|0.00|9.88|-0.10|0.73|10.57|6.57|0.45|10.30|193.15|
|HOLD|STRESS43|RAW_AS_FRACTION|124.36|150.05|124.36|0.00|15.72|-9.96|0.73|10.56|6.59|0.40|10.30|192.62|
|HOLD|STRESS43|RAW_AS_PERCENT|134.29|150.11|134.29|0.00|15.73|-0.10|0.73|10.57|6.58|0.43|10.30|192.97|

CASH解析参照：净0、成本0、风险0、完整资本10k，不冒称模拟账户。全部净值含未平仓mark，正残仓未删除；非实际付费平仓的liquidated return NOT_EVALUABLE。

## 市场状态与方向贡献（BASE27/PCT，描述性）

|策略|状态|日数|LONG|SHORT|CASH|净USDT|
|---|---|---:|---:|---:|---:|---:|
|PUBLIC_SMA_INTENT|SIDEWAYS|25|-134.76|633.99|0.00|499.23|
|PUBLIC_SMA_INTENT|BEAR|25|119.32|-357.64|0.00|-238.32|
|PUBLIC_SMA_INTENT|BULL|22|-13.35|-338.90|0.00|-352.25|
|PUBLIC_SMA_META|SIDEWAYS|41|71.18|188.28|0.00|259.46|
|PUBLIC_SMA_META|BEAR|25|109.04|-174.49|0.00|-65.45|
|PUBLIC_SMA_META|BULL|56|0.08|-215.15|0.00|-215.07|
|HOLD|SIDEWAYS|41|-302.94|0.00|0.00|-302.94|
|HOLD|BEAR|25|232.12|0.00|0.00|232.12|
|HOLD|BULL|56|210.98|0.00|0.00|210.98|

BTC上一闭合日SMA200/20d方向与过去崩盘定义复用，仅描述性分层；收益含既有头寸与成本，不作入场因果归因。CASH不会产生虚构利息，费用仍属于实际多/空腿。

## 验收与复现

原公开状态独立scalar50/200窗口重算；公共raw目标与共有风险目标权重一致1e-12；每新账户独立复算全部分钟NAV/钱包/资金费/目标，所有工件SHA逐一验。
2项新因果/label/identity回归通过；首次合成末尾未知label计数误写12而实际10的失败V1保留，修正fixture后V2通过。清算停止不得被完整日历断言遮蔽；新停止参考支持前缀与最后真实mark，全部缺口与残仓保留，不模拟免费清算。
预测方向计数：{"raw_LONG": 187, "raw_SHORT": 1026, "raw_CASH": 7, "meta_LONG": 53, "meta_SHORT": 295, "meta_CASH": 872}
fit/account wall 225.957s；共享RAM采样2.309GB/RSS0.573GB、工件101.63MB/GPU0。磁盘运行前扫描2026-10-05T11:13:52.963795+00:00：30.371GB。
源码commit/protocol/输入/全部工件SHA、保证金/敞口/集中度/逐币贡献见结构化验收；收益只有这122日，不能年化成长期APR。

```sh
scripts/with_task_progress.sh --title "共享元标签复现" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_meta.py --protocol protocols/SHARED_SIGNAL_META_20261005_V1.json --run-dir /home/xflops/coin-state/d090-independent-reproduction --output reports/fast_research/SHARED_META_INDEPENDENT_REPRODUCTION.json
```

## 实际停止与完整性

停止账户费用、毛损益和方向贡献只属于停止前缀，不能与122日完整账户相减；停止后的日子没有补零。停止时mark独立账本核的是绑定summary声明价格，不冒充独立行情采样/清算成交。

|策略|成本/资金费解释|完成分钟|停止时净损益USDT（不是全窗）|状态|残仓USDT|
|---|---|---:|---:|---|---:|
|PUBLIC_SMA_INTENT|BASE27/RAW_AS_FRACTION|103804|-83.94|LIQUIDATION_REQUIRED_HALT|1182.14|
|PUBLIC_SMA_INTENT|BASE27/RAW_AS_PERCENT|103804|-91.34|LIQUIDATION_REQUIRED_HALT|1181.29|
|PUBLIC_SMA_INTENT|STRESS43/RAW_AS_FRACTION|103804|-93.54|LIQUIDATION_REQUIRED_HALT|1181.02|
|PUBLIC_SMA_INTENT|STRESS43/RAW_AS_PERCENT|103804|-100.90|LIQUIDATION_REQUIRED_HALT|1180.17|


## 证据决定与新主线

D090固定公开SMA50/200原双向意图+一个共享execute/reject拟合；4原SMA账户均在103804分钟逐仓清算要求处停止，全122日净收益NOT_EVALUABLE，不补零。4过滤账户完整122日，净-84.26至-14.44USDT，BASE/PCT净-21.06、毛88.12、成本109.25、资金费0.07，DD5.48%、vol8.17%；同口径HOLD净140.16。原fit1次，恢复阶段fit0；最终恢复只新增2账户、10账本按SHA复用，整个实验实际独立账户12，未拼钱包。V1完整性断言错误和V2工件250MB停止保留，V3在同预算仅补缺两项。固定intent独立窗口参考、目标/每分钟NAV/资金费/钱包及停止参考通过；停止mark只核声明价格。

暂停本拟合配方与旧固定XGB门控配方，保留模型、多空和退出能力；本轮没有合格投资方案NONE/CASH。旧XGB负结果不能外推short无alpha，更不能外推所有公开CTA。重新开放ML需经典benchmark明确且提出可证伪的净/风险增量假设。

当前主线转为公开、冻结参数、零训练经典CTA leaderboard：真calendar12m TSMOM、SMA200 signed trend、Donchian20/10与20/10+55/20+12m等权forecast。各币独立信号，past30 inverse-vol和原signed covariance缩放进入同一个10币/10k账户。同Mar–Jun122日、两成本与两资金费解释，LONG_ONLY/SHORT_ONLY/LONG_SHORT/CASH/HOLD，最多56真实账户，零拟合/零搜参。有预热不足则UNKNOWN，不冒充短窗12m；本金/caps/逐仓1x/持续平仓/风险停止保持。先验证short增量与状态机制，再允许ML挑战。
