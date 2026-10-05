# D089：零目标平仓持续重试的完整账户对照

决定：**PAUSE_THIS_FIXED_RECIPE**。投资候选仍 NONE/CASH，长期APR NOT_EVALUABLE。

一套10币共享XGBoost（120轮boosting、实际360棵分类树、depth3、CPU2、seed20261005），没有搜索、阈值挑选或逐币训练。
复用同一固定SHORT_ONLY XGB预测、状态与目标，仅DAILY_TARGET零目标持续重试至成交或被更新决策/风险/终止替代。4个新完整账户，24个旧账户SHA复用；金融/数据源码仅声明的调度器差异由改动前默认golden与4项实际回归绑定，其他原样。不删除旧成交/成本，不免费成交。
数据已见开发筛选；Binance USD-M价格/mark/资金费配用户Bybit手续费，是跨场所代理。
5日trade-open价格收益与37bp带比较，成本只进入边界一次；标签不含资金费/实际一分钟延迟。真实账户另外完整计费、容量、资金费与风险减仓。
同资本10k、单币abs30%/gross60%、过去30日协方差最多10%年vol目标、逐仓1x；相同caps不代表实际风险相同。

## 完整成本与方向账本

|策略|成本|资金费解释|净USDT|毛USDT|LONG|SHORT|费|点差+滑点|资金费|换手|年vol%|分钟DD%|日Sharpe|残仓USDT|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|XGB_LONG_SHORT|BASE27|RAW_AS_FRACTION|-919.83|-646.31|-135.76|-784.07|112.19|163.19|1.86|20.398|9.79|12.01|-2.90|226.21|
|XGB_LONG_SHORT|BASE27|RAW_AS_PERCENT|-921.57|-646.23|-128.94|-792.64|112.19|163.18|0.02|20.398|9.80|12.03|-2.90|226.15|
|XGB_LONG_SHORT|STRESS43|RAW_AS_FRACTION|-1069.43|-636.03|-215.50|-853.93|111.34|323.90|1.84|20.244|9.80|13.19|-3.40|220.39|
|XGB_LONG_SHORT|STRESS43|RAW_AS_PERCENT|-1071.15|-635.95|-208.73|-862.42|111.34|323.88|0.02|20.243|9.81|13.21|-3.41|220.33|
|XGB_REGIME_GATED|BASE27|RAW_AS_FRACTION|-46.81|1.02|0.00|-46.81|20.01|29.10|1.27|3.637|4.26|2.13|-0.31|190.78|
|XGB_REGIME_GATED|BASE27|RAW_AS_PERCENT|-48.06|1.03|0.00|-48.06|20.00|29.10|0.01|3.637|4.27|2.13|-0.32|190.77|
|XGB_REGIME_GATED|STRESS43|RAW_AS_FRACTION|-75.81|1.02|0.00|-75.81|19.98|58.12|1.27|3.633|4.27|2.16|-0.51|190.43|
|XGB_REGIME_GATED|STRESS43|RAW_AS_PERCENT|-77.07|1.02|0.00|-77.07|19.98|58.12|0.01|3.633|4.27|2.16|-0.52|190.42|
|HOLD|BASE27|RAW_AS_FRACTION|130.25|150.09|130.25|0.00|4.02|5.85|-9.97|0.731|10.56|6.58|0.42|192.80|
|HOLD|BASE27|RAW_AS_PERCENT|140.16|150.14|140.16|0.00|4.02|5.85|-0.10|0.732|10.57|6.57|0.45|193.15|
|HOLD|STRESS43|RAW_AS_FRACTION|124.36|150.05|124.36|0.00|4.02|11.70|-9.96|0.731|10.56|6.59|0.40|192.62|
|HOLD|STRESS43|RAW_AS_PERCENT|134.29|150.11|134.29|0.00|4.02|11.70|-0.10|0.731|10.57|6.58|0.43|192.97|
|DONCHIAN_EXIT10|BASE27|RAW_AS_FRACTION|-357.34|-343.46|-357.34|0.00|4.08|5.93|-3.88|0.741|4.54|3.63|-2.38|0.00|
|DONCHIAN_EXIT10|BASE27|RAW_AS_PERCENT|-353.58|-343.54|-353.58|0.00|4.08|5.93|-0.04|0.741|4.54|3.59|-2.35|0.00|
|DONCHIAN_EXIT10|STRESS43|RAW_AS_FRACTION|-363.17|-343.36|-363.17|0.00|4.07|11.85|-3.88|0.741|4.55|3.68|-2.41|0.00|
|DONCHIAN_EXIT10|STRESS43|RAW_AS_PERCENT|-359.40|-343.44|-359.40|0.00|4.07|11.85|-0.04|0.741|4.55|3.65|-2.39|0.00|
|XGB_TREND_GATED|BASE27|RAW_AS_FRACTION|-262.32|-155.31|-307.05|44.74|42.56|61.90|-2.55|7.738|5.43|5.22|-1.44|0.00|
|XGB_TREND_GATED|BASE27|RAW_AS_PERCENT|-259.85|-155.36|-303.11|43.26|42.56|61.90|-0.03|7.738|5.44|5.20|-1.42|0.00|
|XGB_TREND_GATED|STRESS43|RAW_AS_FRACTION|-323.22|-154.79|-349.05|25.83|42.44|123.46|-2.53|7.716|5.43|5.47|-1.78|0.00|
|XGB_TREND_GATED|STRESS43|RAW_AS_PERCENT|-320.76|-154.84|-345.13|24.36|42.44|123.46|-0.03|7.716|5.44|5.45|-1.77|0.00|
|XGB_TREND_SHORT_ONLY|BASE27|RAW_AS_FRACTION|45.03|75.44|0.00|45.03|12.99|18.89|1.46|2.361|2.89|1.94|0.48|0.00|
|XGB_TREND_SHORT_ONLY|BASE27|RAW_AS_PERCENT|43.56|75.42|0.00|43.56|12.98|18.89|0.01|2.361|2.90|1.95|0.46|0.00|
|XGB_TREND_SHORT_ONLY|STRESS43|RAW_AS_FRACTION|25.96|75.22|0.00|25.96|12.98|37.75|1.46|2.359|2.90|2.02|0.28|0.00|
|XGB_TREND_SHORT_ONLY|STRESS43|RAW_AS_PERCENT|24.50|75.20|0.00|24.50|12.97|37.74|0.01|2.359|2.90|2.03|0.27|0.00|
|XGB_TREND_SHORT_PERSISTENT_CASH|BASE27|RAW_AS_FRACTION|-21.50|9.59|0.00|-21.50|13.15|19.13|1.20|2.392|2.65|1.97|-0.23|0.00|
|XGB_TREND_SHORT_PERSISTENT_CASH|BASE27|RAW_AS_PERCENT|-22.69|9.59|0.00|-22.69|13.15|19.13|0.01|2.392|2.65|1.98|-0.24|0.00|
|XGB_TREND_SHORT_PERSISTENT_CASH|STRESS43|RAW_AS_FRACTION|-40.67|9.52|0.00|-40.67|13.14|38.24|1.19|2.390|2.66|2.05|-0.44|0.00|
|XGB_TREND_SHORT_PERSISTENT_CASH|STRESS43|RAW_AS_PERCENT|-41.85|9.51|0.00|-41.85|13.14|38.23|0.01|2.390|2.66|2.06|-0.46|0.00|

CASH解析基准：净0、风险0、成本0，完整资本10k；不冒充模拟运行。上述净值包含全部残仓mark，残仓未删除；没有完成付费清仓的账户 **liquidated return NOT_EVALUABLE**。

## 持续平仓重试相对五次过期的增量

|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|预先任一改善|
|---|---|---:|---:|---:|---|
|BASE27|RAW_AS_FRACTION|-66.53|0.03|-0.24|False|
|BASE27|RAW_AS_PERCENT|-66.25|0.03|-0.24|False|
|STRESS43|RAW_AS_FRACTION|-66.63|0.03|-0.24|False|
|STRESS43|RAW_AS_PERCENT|-66.35|0.03|-0.24|False|

## 相对未门控方向的次要对照

|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|
|---|---|---:|---:|---:|
|BASE27|RAW_AS_FRACTION|898.33|-10.04|-7.14|
|BASE27|RAW_AS_PERCENT|898.88|-10.05|-7.15|
|STRESS43|RAW_AS_FRACTION|1028.76|-11.14|-7.14|
|STRESS43|RAW_AS_PERCENT|1029.30|-11.15|-7.14|

本轮SHORT_ONLY门控只在BEAR保留原short，BULL/SIDEWAYS/前一完成日崩盘状态与原long均请求零目标；不反转、不重分配被过滤预算。四种情景配对，不能拿旧61日独立账户净值当本轮增量。

## 过去可得的行情分层（描述性，不是HMM）

BTC close>SMA200且20d return>0为BULL，两者负为BEAR；单日<-5%且30d年vol>80%为HIGH_VOL_CRASH，其他SIDEWAYS。不使用未来行情定义状态。

|策略(BASE27, RAW_AS_PERCENT)|状态|日数|LONG USDT|SHORT USDT|净 USDT|
|---|---|---:|---:|---:|---:|
|XGB_TREND_SHORT_PERSISTENT_CASH|SIDEWAYS|41|0.00|-0.37|-0.37|
|XGB_TREND_SHORT_PERSISTENT_CASH|BEAR|25|0.00|-20.85|-20.85|
|XGB_TREND_SHORT_PERSISTENT_CASH|BULL|56|0.00|-1.47|-1.47|
|XGB_TREND_SHORT_ONLY|SIDEWAYS|41|0.00|65.95|65.95|
|XGB_TREND_SHORT_ONLY|BEAR|25|0.00|-20.86|-20.86|
|XGB_TREND_SHORT_ONLY|BULL|56|0.00|-1.52|-1.52|
|XGB_LONG_SHORT|SIDEWAYS|41|-199.14|38.88|-160.26|
|XGB_LONG_SHORT|BEAR|25|531.48|-235.88|295.60|
|XGB_LONG_SHORT|BULL|56|-461.28|-595.63|-1056.91|
|XGB_REGIME_GATED|SIDEWAYS|41|0.00|-64.71|-64.71|
|XGB_REGIME_GATED|BEAR|25|0.00|-2.51|-2.51|
|XGB_REGIME_GATED|BULL|56|0.00|19.16|19.16|
|XGB_TREND_GATED|SIDEWAYS|41|-8.77|64.69|55.92|
|XGB_TREND_GATED|BEAR|25|-0.74|-19.90|-20.65|
|XGB_TREND_GATED|BULL|56|-293.60|-1.52|-295.12|
|HOLD|SIDEWAYS|41|-302.94|0.00|-302.94|
|HOLD|BEAR|25|232.12|0.00|232.12|
|HOLD|BULL|56|210.98|0.00|210.98|
|DONCHIAN_EXIT10|SIDEWAYS|41|-265.58|0.00|-265.58|
|DONCHIAN_EXIT10|BEAR|25|121.05|0.00|121.05|
|DONCHIAN_EXIT10|BULL|56|-209.05|0.00|-209.05|

## 固定状态覆盖与真实敞口

固定规则只描述上一闭合日当前趋势，不是未来牛熊收益真值；收益分桶含旧持仓与退出成本，不是因果贡献。零目标不保证容量受限时立即现金。

状态日数：{"BULL": 56, "BEAR": 25, "SIDEWAYS": 41, "HIGH_VOL_CRASH": 0}

|策略(BASE27, RAW_AS_PERCENT)|状态|平均gross%|峰值gross%|平均net%|精确零仓分钟/总分钟|
|---|---|---:|---:|---:|---|
|XGB_TREND_SHORT_ONLY|BULL|0.00|9.70|-0.00|80638/80640|
|XGB_TREND_SHORT_ONLY|BEAR|7.42|12.77|-7.42|7200/36000|
|XGB_TREND_SHORT_ONLY|SIDEWAYS|0.29|12.07|-0.29|53271/59040|
|XGB_TREND_SHORT_PERSISTENT_CASH|BULL|0.00|9.34|-0.00|80638/80640|
|XGB_TREND_SHORT_PERSISTENT_CASH|BEAR|7.32|12.77|-7.32|8642/36000|
|XGB_TREND_SHORT_PERSISTENT_CASH|SIDEWAYS|0.00|12.07|-0.00|58941/59040|

## 资产贡献与成交成本（双向BASE27、RAW_AS_PERCENT）

|币|毛USDT|净USDT|手续费USDT|执行USDT|资金费USDT|成交腿|
|---|---:|---:|---:|---:|---:|---:|
|BTCUSDT|-11.95|-43.29|12.77|18.57|-0.00|162|
|ETHUSDT|-11.82|-43.05|12.72|18.51|-0.00|159|
|SOLUSDT|49.53|21.04|11.60|16.88|-0.00|154|
|1000PEPEUSDT|-97.14|-124.30|11.07|16.10|0.01|154|
|XRPUSDT|77.52|50.38|11.06|16.08|-0.01|150|
|WIFUSDT|-152.77|-184.60|12.96|18.85|-0.01|243|
|WLDUSDT|-255.86|-283.23|11.15|16.23|0.01|290|
|DOGEUSDT|-34.88|-66.33|12.81|18.63|-0.00|173|
|1000SATSUSDT|-50.81|-67.38|6.76|9.83|0.01|369|
|ORDIUSDT|-158.04|-180.80|9.28|13.49|0.01|339|

日方向贡献是资金流+当日持仓mark变化的净增量，不把平仓整笔利润任意归给订单原因；按状态分层是关联描述，不是因果证明。缺少的状态没有造样本。

## 实际验证与局限

所有分钟signed数量、现金流净值桥、资金费归属/正负/严格过去mark、手续费与已实现钱包=free+逐仓抵押物独立复算；检查全部122日，不只是期末。数量仍精确Decimal，独立gross/net统计见结构化验收。
独立验证是记录成交的会计，不是独立重建订单选择、原生保证金层级或全盘价格来源认证；瞬时风险/跳空及历史规则未认证范围沿用原账户。
funding物理单位仍UNKNOWN，两种情景均报告，不能挑更盈利解释。资金费/basis/OI未作为特征；日线可得性是已闭合时间代理，非原生发布认证。
末尾50个未知5日标签保留缺失；重叠标签不是独立交易；原方向模型CASH预测0，状态门控的零目标不等同模型学会现金择时。HMM/MLP/meta未跑。
本轮新fit=0；4项相关退出/容量/费用/资金费/未来扰动/风险停止和旧默认golden回归实际通过。第一次2失败为合成风险例尚未满仓及旧test stub遗漏N资产symbols关键字，保留V1失败，修正输入/接口后V2通过，未迁就测试更改风险。24个旧账户按SHA复用，新4目标/全部分钟NAV/钱包/费用/funding独立复算。

共享RAM采样峰值 1.877GB，进程RSS峰值 0.564GB，输出增长 43.50MB，GPU0，swap0。磁盘实际扫描 2026-10-05T10:12:02.018785+00:00：30.029GB，不能当收尾扫描。

## 复现

```sh
scripts/with_task_progress.sh --title "共享方向模型" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_direction.py --protocol protocols/CASH_CLOSE_RETRY_20261005_V1.json --run-dir /home/xflops/coin-state/d089-independent-reproduction --output reports/fast_research/CASH_CLOSE_RETRY_INDEPENDENT_REPRODUCTION.json
```

从WSL项目ROOT运行；新独占目录，新运行4账户，不覆盖原证据。所有实际工件位置/SHA、贡献/暴露/保证金/集中度与假设见结构化验收。
验收：`reports/CASH_CLOSE_RETRY_ACCEPTED_20261005_V1.json`，SHA `73c91ca917b2017da9fc37c76aef6e2ee190179ab5f00d5cb5f9e4839c6a2421`。实际运行：`reports/fast_research/CASH_CLOSE_RETRY_20261005_V1.json`，SHA `770e28f7175eac42d89f25a6bca734ac7184c3b6225aef716422bd60fdbac209`。

## 现金目标与实际平仓诊断

|策略(BASE27/PCT)|零目标仍有仓位的资产分钟|零目标平仓成交腿|超过五分钟的平仓腿|最长signal至成交分钟|
|---|---:|---:|---:|---:|
|XGB_TREND_SHORT_ONLY|13059|144|0|5.000000016666666|
|XGB_TREND_SHORT_PERSISTENT_CASH|210|210|86|52.00000001666667|


## 机制结论与下一决定

D089只改变日常零目标的平仓重试，4个新完整122日/10币共享10k账户，24旧控制逐artifacts SHA复用；zero fit/search。BASE27/PCT净-22.69（旧5次过期43.56），毛9.59、费用/执行32.29、资金费0.01USDT；旧/新DD 1.95%/1.98%，vol 2.90%/2.65%，平均gross 1.62%/1.50%。四解释净范围-41.85至-21.50；新BEAR桶SHORT -20.85。零目标仍持仓的资产分钟旧13059/新210，新超五分钟真实平仓腿86；新零目标平空5次过期0，全部新q<=0/LONG=0；新4账户实付清仓=True。容量/费用/风险/终止覆盖不变；改动前默认完整账户golden、4项实际相关回归以及每分钟独立NAV/钱包/目标复核通过。第一次2项合成测试失败已保留，修正风险例未满仓及旧stub缺N资产关键字后4项通过；未按收益修改验收。

采用可选持续平仓重试能力，不因它比过期退出少赚钱而退回旧机制；短策略决定 PAUSE_THIS_FIXED_RECIPE。已见开发/跨场所代理/资金费UNKNOWN及小样本收益集中保留，投资资格NONE/CASH、长期APR NOT_EVALUABLE。旧延迟退出结果不篡改，状态和现金成交归因仅关联描述，含风险/终止替代可能，不能作因果alpha。

下一有限研究选择：共享execute/reject元标签，对既有固定双向公开信号作成本可交易性过滤；主问题是原方向模型未预测CASH和价格信号净收益弱，而非继续改变执行以挑利润。先核已登记公开信号完整语义与数据成熟，再预登记一个配置、共同时间切分、成本一致的完整账户对照。元模型只用闭合特征与固定公开signal，若使用方向模型概率须时间OOF/out-of-fit，不把训练内概率当独立链路；所有标签先成熟，已见评价仍是开发。不无限扫本XGB/state阈值；现固定多空配方暂停，reopen需不同可得预测机制带来真实净/风险改善并补独立证据。
