# D087：固定过去趋势状态与相对分群门控对照

决定：**PAUSE_THIS_FIXED_RECIPE**。投资候选仍 NONE/CASH，长期APR NOT_EVALUABLE。

一套10币共享XGBoost（120轮boosting、实际360棵分类树、depth3、CPU2、seed20261005），没有搜索、阈值挑选或逐币训练。
复用D085固定模型，全部1220行概率和标签与D086精确一致；固定过去BTC SMA200/20d规则，无方向/状态/标准化拟合。只新增4个Mar–Jun2025连续122日账户，16个D086同窗对照按SHA复用。旧GMM状态桶保留，报告统一按固定规则重新分桶；回溯已见研究，不声称历史部署。
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

CASH解析基准：净0、风险0、成本0，完整资本10k；不冒充模拟运行。上述净值包含全部残仓mark，残仓未删除；没有完成付费清仓的账户 **liquidated return NOT_EVALUABLE**。

## 固定趋势门控相对同窗GMM门控的增量

|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|预先任一改善|
|---|---|---:|---:|---:|---|
|BASE27|RAW_AS_FRACTION|-215.51|3.09|1.17|False|
|BASE27|RAW_AS_PERCENT|-211.78|3.07|1.17|False|
|STRESS43|RAW_AS_FRACTION|-247.40|3.31|1.17|False|
|STRESS43|RAW_AS_PERCENT|-243.70|3.29|1.17|False|

## 相对未门控方向的次要对照

|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|
|---|---|---:|---:|---:|
|BASE27|RAW_AS_FRACTION|657.52|-6.79|-4.36|
|BASE27|RAW_AS_PERCENT|661.73|-6.83|-4.36|
|STRESS43|RAW_AS_FRACTION|746.21|-7.72|-4.37|
|STRESS43|RAW_AS_PERCENT|750.38|-7.76|-4.37|

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
|XGB_REGIME_GATED|BULL|0.14|10.64|-0.14|73439/80640|
|XGB_REGIME_GATED|BEAR|3.50|11.97|-3.50|20156/36000|
|XGB_REGIME_GATED|SIDEWAYS|3.98|14.30|-3.98|33109/59040|
|XGB_TREND_GATED|BULL|6.09|18.74|6.09|30240/80640|
|XGB_TREND_GATED|BEAR|7.39|12.80|-7.37|7198/36000|
|XGB_TREND_GATED|SIDEWAYS|0.29|12.07|-0.29|53259/59040|

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
本轮所有新fit=0；2个相关趋势状态回归无拟合，既有GMM回归未重跑。新4账户各自独立复算目标、全部分钟NAV/钱包/费用/funding；16对照仅按原证据SHA与相同金融/数据源码绑定复用，不称重新运行。

共享RAM采样峰值 1.256GB，进程RSS峰值 0.565GB，输出增长 78.33MB，GPU0，swap0。磁盘实际扫描 2026-10-05T09:17:18.322126+00:00：29.887GB，不能当收尾扫描。

## 复现

```sh
scripts/with_task_progress.sh --title "共享方向模型" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_direction.py --protocol protocols/PAST_TREND_GATE_20261005_V1.json --run-dir /home/xflops/coin-state/d087-independent-reproduction --output reports/fast_research/PAST_TREND_INDEPENDENT_REPRODUCTION.json
```

从WSL项目ROOT运行；新独占目录，新运行4账户，不覆盖原证据。所有实际工件位置/SHA、贡献/暴露/保证金/集中度与假设见结构化验收。
验收：`reports/PAST_TREND_ACCEPTED_20261005_V1.json`，SHA `a08daed8ef0d2ce90b73770fe8024777687888d4c5752e3cd01b87ee12e9f15b`。实际运行：`reports/fast_research/PAST_TREND_20261005_V1.json`，SHA `d6cb2593e671fbc2cf3e28bf2562ad5336398659815a0c4c6056cab301fca055`。
