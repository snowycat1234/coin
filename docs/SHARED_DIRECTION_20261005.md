# D085：共享三分类方向基线与真实账户对照

决定：**PAUSE_THIS_FIXED_RECIPE**。投资候选仍 NONE/CASH，长期APR NOT_EVALUABLE。

一套10币共享XGBoost（120轮boosting、实际360棵分类树、depth3、CPU2、seed20261005），没有搜索、阈值挑选或逐币训练。
训练Sep2024–Feb2025、诊断Mar–Apr2025、经济May–Jun2025共61日；所有币相同时间切分，5日标签严格成熟。
数据已见开发筛选；Binance USD-M价格/mark/资金费配用户Bybit手续费，是跨场所代理。
5日trade-open价格收益与37bp带比较，成本只进入边界一次；标签不含资金费/实际一分钟延迟。真实账户另外完整计费、容量、资金费与风险减仓。
同资本10k、单币abs30%/gross60%、过去30日协方差最多10%年vol目标、逐仓1x；相同caps不代表实际风险相同。

## 完整成本与方向账本

|策略|成本|资金费解释|净USDT|毛USDT|LONG|SHORT|费|点差+滑点|资金费|换手|年vol%|分钟DD%|日Sharpe|残仓USDT|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|XGB_LONG_SHORT|BASE27|RAW_AS_FRACTION|-943.28|-818.22|-517.86|-425.42|51.60|75.05|1.60|9.382|9.39|11.19|-6.26|225.26|
|XGB_LONG_SHORT|BASE27|RAW_AS_PERCENT|-944.78|-818.15|-514.41|-430.37|51.60|75.05|0.02|9.381|9.40|11.20|-6.27|225.20|
|XGB_LONG_SHORT|STRESS43|RAW_AS_FRACTION|-1015.61|-816.17|-554.09|-461.52|51.43|149.61|1.59|9.351|9.38|11.75|-6.78|222.62|
|XGB_LONG_SHORT|STRESS43|RAW_AS_PERCENT|-1017.11|-816.10|-550.65|-466.46|51.42|149.59|0.02|9.350|9.39|11.76|-6.79|222.57|
|XGB_LONG_ONLY|BASE27|RAW_AS_FRACTION|-274.22|-196.50|-274.22|0.00|30.04|43.69|-3.99|5.462|7.46|7.53|-2.19|0.00|
|XGB_LONG_ONLY|BASE27|RAW_AS_PERCENT|-270.34|-196.55|-270.34|0.00|30.04|43.70|-0.04|5.463|7.46|7.51|-2.16|0.00|
|XGB_LONG_ONLY|STRESS43|RAW_AS_FRACTION|-317.22|-196.04|-317.22|0.00|29.98|87.22|-3.99|5.451|7.45|7.82|-2.55|0.00|
|XGB_LONG_ONLY|STRESS43|RAW_AS_PERCENT|-313.36|-196.10|-313.36|0.00|29.99|87.23|-0.04|5.452|7.45|7.80|-2.52|0.00|
|XGB_SHORT_ONLY|BASE27|RAW_AS_FRACTION|-485.15|-442.08|0.00|-485.15|19.42|28.24|4.58|3.530|8.23|6.22|-3.57|179.32|
|XGB_SHORT_ONLY|BASE27|RAW_AS_PERCENT|-489.62|-442.02|0.00|-489.62|19.41|28.24|0.05|3.530|8.24|6.26|-3.60|179.22|
|XGB_SHORT_ONLY|STRESS43|RAW_AS_FRACTION|-512.67|-441.48|0.00|-512.67|19.38|56.39|4.58|3.524|8.23|6.40|-3.78|178.67|
|XGB_SHORT_ONLY|STRESS43|RAW_AS_PERCENT|-517.13|-441.42|0.00|-517.13|19.38|56.37|0.05|3.523|8.24|6.45|-3.82|178.56|
|HOLD|BASE27|RAW_AS_FRACTION|158.46|170.69|158.46|0.00|2.48|3.61|-6.15|0.451|10.15|5.14|0.98|193.85|
|HOLD|BASE27|RAW_AS_PERCENT|164.49|170.64|164.49|0.00|2.48|3.61|-0.06|0.451|10.16|5.12|1.01|194.06|
|HOLD|STRESS43|RAW_AS_FRACTION|154.85|170.68|154.85|0.00|2.48|7.21|-6.14|0.451|10.16|5.15|0.96|193.76|
|HOLD|STRESS43|RAW_AS_PERCENT|160.88|170.63|160.88|0.00|2.48|7.21|-0.06|0.451|10.16|5.12|0.99|193.97|
|DONCHIAN_EXIT10|BASE27|RAW_AS_FRACTION|-229.90|-216.41|-229.90|0.00|3.16|4.60|-5.72|0.575|4.67|3.29|-2.95|0.00|
|DONCHIAN_EXIT10|BASE27|RAW_AS_PERCENT|-224.35|-216.53|-224.35|0.00|3.16|4.60|-0.06|0.575|4.67|3.27|-2.88|0.00|
|DONCHIAN_EXIT10|STRESS43|RAW_AS_FRACTION|-234.43|-216.34|-234.43|0.00|3.16|9.20|-5.72|0.575|4.68|3.31|-3.01|0.00|
|DONCHIAN_EXIT10|STRESS43|RAW_AS_PERCENT|-228.88|-216.46|-228.88|0.00|3.16|9.20|-0.06|0.575|4.69|3.29|-2.93|0.00|

CASH解析基准：净0、风险0、成本0，完整资本10k；不冒充模拟运行。上述净值包含全部残仓mark，残仓未删除；没有完成付费清仓的账户 **liquidated return NOT_EVALUABLE**。

## 双向相对同模型多头的增量

|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|预先任一改善|
|---|---|---:|---:|---:|---|
|BASE27|RAW_AS_FRACTION|-669.06|3.66|1.94|False|
|BASE27|RAW_AS_PERCENT|-674.44|3.69|1.94|False|
|STRESS43|RAW_AS_FRACTION|-698.39|3.93|1.93|False|
|STRESS43|RAW_AS_PERCENT|-703.75|3.96|1.93|False|

SHORT_ONLY、LONG_ONLY为同预测消融，独立账户不得相加成为伪组合；LONG_SHORT是唯一同步共享资本双向账户。

## 过去可得的行情分层（描述性，不是HMM）

BTC close>SMA200且20d return>0为BULL，两者负为BEAR；单日<-5%且30d年vol>80%为HIGH_VOL_CRASH，其他SIDEWAYS。不使用未来行情定义状态。

|策略(BASE27, RAW_AS_PERCENT)|状态|日数|LONG USDT|SHORT USDT|净 USDT|
|---|---|---:|---:|---:|---:|
|XGB_LONG_SHORT|BULL|45|-383.32|-526.47|-909.79|
|XGB_LONG_SHORT|SIDEWAYS|16|-131.09|96.10|-34.99|
|XGB_LONG_ONLY|BULL|45|-214.76|0.00|-214.76|
|XGB_LONG_ONLY|SIDEWAYS|16|-55.57|0.00|-55.57|
|XGB_SHORT_ONLY|BULL|45|0.00|-496.52|-496.52|
|XGB_SHORT_ONLY|SIDEWAYS|16|0.00|6.90|6.90|
|HOLD|BULL|45|229.15|0.00|229.15|
|HOLD|SIDEWAYS|16|-64.66|0.00|-64.66|
|DONCHIAN_EXIT10|BULL|45|-169.71|0.00|-169.71|
|DONCHIAN_EXIT10|SIDEWAYS|16|-54.64|0.00|-54.64|

## 资产贡献与成交成本（双向BASE27、RAW_AS_PERCENT）

|币|毛USDT|净USDT|手续费USDT|执行USDT|资金费USDT|成交腿|
|---|---:|---:|---:|---:|---:|---:|
|BTCUSDT|-35.93|-50.70|6.02|8.75|0.00|81|
|ETHUSDT|-82.96|-98.74|6.43|9.35|-0.00|82|
|SOLUSDT|-58.00|-71.40|5.46|7.94|-0.00|77|
|1000PEPEUSDT|-70.02|-81.91|4.85|7.05|0.01|74|
|XRPUSDT|-82.80|-96.24|5.48|7.96|-0.00|78|
|WIFUSDT|-125.65|-138.20|5.11|7.43|-0.01|92|
|WLDUSDT|-108.81|-121.97|5.36|7.80|0.00|133|
|DOGEUSDT|-105.44|-120.82|6.27|9.12|0.00|86|
|1000SATSUSDT|-29.95|-36.65|2.73|3.98|0.01|180|
|ORDIUSDT|-118.59|-128.15|3.89|5.66|0.01|162|

日方向贡献是资金流+当日持仓mark变化的净增量，不把平仓整笔利润任意归给订单原因；按状态分层是关联描述，不是因果证明。缺少的状态没有造样本。

## 实际验证与局限

所有分钟signed数量、现金流净值桥、资金费归属/正负/严格过去mark、手续费与已实现钱包=free+逐仓抵押物独立复算；检查全部61日，不只是期末。数量仍精确Decimal，独立gross/net统计见结构化验收。
独立验证是记录成交的会计，不是独立重建订单选择、原生保证金层级或全盘价格来源认证；瞬时风险/跳空及历史规则未认证范围沿用原账户。
funding物理单位仍UNKNOWN，两种情景均报告，不能挑更盈利解释。资金费/basis/OI未作为特征；日线可得性是已闭合时间代理，非原生发布认证。
末尾50个未知5日标签保留缺失；重叠标签不是独立交易；模型没有CASH预测不能称已经学会现金择时。HMM/MLP/meta未跑。
首次账户因为严格全额平仓断言而停止：原模型/成交/负结果/225USDT残仓与原退出码保存；修正的是验收范围，模型与原预测逐字一致并复用，首账户未重跑。

共享RAM采样峰值 1.545GB，进程RSS峰值 0.439GB，输出增长 336.78MB，GPU0，swap0。磁盘实际扫描 2026-10-05T08:04:24.970787+00:00：28.965GB，不能当收尾扫描。

## 复现

```sh
scripts/with_task_progress.sh --title "共享方向模型" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_direction.py --protocol protocols/SHARED_XGB_DIRECTION_20261005_V1.json --run-dir /home/xflops/coin-state/d085-independent-reproduction --output reports/fast_research/SHARED_DIRECTION_INDEPENDENT_REPRODUCTION.json
```

从WSL项目ROOT运行；新独占目录，重新一拟合20账户，不覆盖原证据。所有实际工件位置/SHA、贡献/暴露/保证金/集中度与假设见结构化验收。
验收：`reports/SHARED_DIRECTION_ACCEPTED_20261005_V1.json`，SHA `ac72412883040db491169e0a8e474283783387a0023963aacbc60005ac3efd3b`。实际运行：`reports/fast_research/SHARED_DIRECTION_20261005_V3.json`，SHA `150d6507d6b90b2a509ae35d856a08ffcee87e1cc98d4165dbf9847688e92946`。
