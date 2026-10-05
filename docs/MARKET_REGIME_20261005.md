# D086：训练期状态门控与同窗真实账户对照

决定：**RETAIN_FOR_RESEARCH_NOT_INVESTMENT**。投资候选仍 NONE/CASH，长期APR NOT_EVALUABLE。

一套10币共享XGBoost（120轮boosting、实际360棵分类树、depth3、CPU2、seed20261005），没有搜索、阈值挑选或逐币训练。
复用D085固定模型，实际fit与标签成熟均早于2025-03-01；训练期一套GMM与标准化，连续经济账户Mar–Jun2025共122日。回溯研究复用，不声称当时已部署；所有币相同时间切分。
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

CASH解析基准：净0、风险0、成本0，完整资本10k；不冒充模拟运行。上述净值包含全部残仓mark，残仓未删除；没有完成付费清仓的账户 **liquidated return NOT_EVALUABLE**。

## 状态门控相对同窗未门控的增量

|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|预先任一改善|
|---|---|---:|---:|---:|---|
|BASE27|RAW_AS_FRACTION|873.03|-9.88|-5.53|True|
|BASE27|RAW_AS_PERCENT|873.51|-9.90|-5.53|True|
|STRESS43|RAW_AS_FRACTION|993.61|-11.03|-5.53|True|
|STRESS43|RAW_AS_PERCENT|994.08|-11.05|-5.54|True|

门控只保留原方向或置零：BULL允许long、BEAR允许short、SIDEWAYS/前一完成日崩盘状态请求零目标；不反转、不重分配被过滤预算。四种情景配对，不能拿旧61日独立账户净值当本轮增量。

## 过去可得的行情分层（描述性，不是HMM）

BTC close>SMA200且20d return>0为BULL，两者负为BEAR；单日<-5%且30d年vol>80%为HIGH_VOL_CRASH，其他SIDEWAYS。不使用未来行情定义状态。

|策略(BASE27, RAW_AS_PERCENT)|状态|日数|LONG USDT|SHORT USDT|净 USDT|
|---|---|---:|---:|---:|---:|
|XGB_LONG_SHORT|SIDEWAYS|41|-199.14|38.88|-160.26|
|XGB_LONG_SHORT|BEAR|25|531.48|-235.88|295.60|
|XGB_LONG_SHORT|BULL|56|-461.28|-595.63|-1056.91|
|XGB_REGIME_GATED|SIDEWAYS|41|0.00|-64.71|-64.71|
|XGB_REGIME_GATED|BEAR|25|0.00|-2.51|-2.51|
|XGB_REGIME_GATED|BULL|56|0.00|19.16|19.16|
|HOLD|SIDEWAYS|41|-302.94|0.00|-302.94|
|HOLD|BEAR|25|232.12|0.00|232.12|
|HOLD|BULL|56|210.98|0.00|210.98|
|DONCHIAN_EXIT10|SIDEWAYS|41|-265.58|0.00|-265.58|
|DONCHIAN_EXIT10|BEAR|25|121.05|0.00|121.05|
|DONCHIAN_EXIT10|BULL|56|-209.05|0.00|-209.05|

## 训练期拟合状态（相对趋势分群）

状态仅按训练中心过去20日收益、SMA200距离与breadth的标准化趋势排序命名；不是绝对牛熊真值、未来预测标签或未来收益选状态。

|状态|20d收益中心|SMA200距离中心|日vol中心|breadth中心|评价日数|
|---|---:|---:|---:|---:|---:|
|SIDEWAYS|0.04483|0.15404|0.02285|0.50643|90|
|BULL|0.24950|0.43525|0.03122|0.93876|0|
|BEAR|-0.05177|0.22047|0.02251|0.00000|32|

|策略(BASE27, RAW_AS_PERCENT)|拟合状态|日数|LONG USDT|SHORT USDT|净 USDT|
|---|---|---:|---:|---:|---:|
|XGB_LONG_SHORT|SIDEWAYS|90|-541.31|-819.45|-1360.76|
|XGB_LONG_SHORT|BEAR|32|412.38|26.81|439.19|
|XGB_REGIME_GATED|SIDEWAYS|90|0.00|15.82|15.82|
|XGB_REGIME_GATED|BEAR|32|0.00|-63.88|-63.88|
|HOLD|SIDEWAYS|90|-134.11|0.00|-134.11|
|HOLD|BEAR|32|274.28|0.00|274.28|
|DONCHIAN_EXIT10|SIDEWAYS|90|-276.27|0.00|-276.27|
|DONCHIAN_EXIT10|BEAR|32|-77.31|0.00|-77.31|

状态分桶按收益日开始时上一已完成日状态，包含既有仓位和退出成本，不是入场状态的因果收益。CASH是零目标请求；容量/精度限制可能使实际持仓延续，不声称立即逃过崩盘或立即现金。HIGH_VOL_CRASH实际日数 0，没有伪造第四拟合类。

|策略(BASE27, RAW_AS_PERCENT)|状态|实际平均gross%|实际峰值gross%|实际平均net%|精确零仓分钟/总分钟|
|---|---|---:|---:|---:|---|
|XGB_LONG_SHORT|BEAR|18.82|50.82|0.80|0/46080|
|XGB_LONG_SHORT|SIDEWAYS|15.61|53.35|-1.88|1/129600|
|XGB_REGIME_GATED|BEAR|7.81|14.30|-7.81|5768/46080|
|XGB_REGIME_GATED|SIDEWAYS|0.10|14.15|-0.10|120936/129600|

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
本轮新direction fit=0，GMM=1、StandardScaler=1；相关因果回归额外2个GMM+2个Scaler拟合均计入，不作经济参数选择。原共同窗口概率和三个方向目标精确golden通过；独立目标审计另算状态过滤、标的顺序和过去协方差。

共享RAM采样峰值 1.781GB，进程RSS峰值 0.584GB，输出增长 520.93MB，GPU0，swap0。磁盘实际扫描 2026-10-05T08:38:47.374544+00:00：29.341GB，不能当收尾扫描。

## 复现

```sh
scripts/with_task_progress.sh --title "共享方向模型" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_direction.py --protocol protocols/MARKET_REGIME_GATE_20261005_V1.json --run-dir /home/xflops/coin-state/d086-independent-reproduction --output reports/fast_research/MARKET_REGIME_INDEPENDENT_REPRODUCTION.json
```

从WSL项目ROOT运行；新独占目录，运行16账户，不覆盖原证据。所有实际工件位置/SHA、贡献/暴露/保证金/集中度与假设见结构化验收。
验收：`reports/MARKET_REGIME_ACCEPTED_20261005_V1.json`，SHA `3649ee454bf33f997159e0823f818737924add7816cdd38e955190f9f25ebab9`。实际运行：`reports/fast_research/MARKET_REGIME_20261005_V1.json`，SHA `73db6e5078e925470bdd00bdd64702980208a11fe8ac14ee9c305dfa8eacb7e6`。
