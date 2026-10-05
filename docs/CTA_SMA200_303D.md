# SMA200_SIGNED：303日连续方向对照

已见2024-09-01至2025-07-01，共303日，10币固定历史池、完整10k共享钱包、abs30/gross60/逐仓1x。两个成本任务并行仅用于不同反事实账户，不相加账户。原122日结果仍为不同起点的独立回测工件，不能拼接或声称本窗unseen。

复用既有SMA200 signed：完整日线close高于最后200个close均值为long，低于为short，相等为cash；每日更新，保留相同inversevol/signedcov。不是Faber原10月long/cash的完整复现。12新账户实际执行，8原CASH/HOLD经完整目标golden、来源和工件SHA复用。无拟合/权重搜索/止损修改。BinanceUSD-M配Bybit成本仍为代理；funding单位UNKNOWN两情景、MMR假设，不能认证native或长期APR。

|策略|方向|BASE/PCT净|LONG|SHORT|毛价格|手续费+执行|资金费|vol%|DD%|换手|残仓|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|SMA200_SIGNED|LONG_ONLY|126.32|126.32|0.00|220.75|93.61|-0.82|9.49|10.39|6.93|0.00|
|SMA200_SIGNED|SHORT_ONLY|NOT_EVALUABLE|0.00|-190.55|-134.07|56.98|0.51|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|1049.40|
|SMA200_SIGNED|LONG_SHORT|NOT_EVALUABLE|327.15|-213.15|279.81|165.51|-0.30|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|2997.34|
|CASH|CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|LONG_ONLY|573.08|573.08|0.00|600.84|26.88|-0.88|10.44|12.99|1.99|173.12|

## 两成本、两未知单位解释配对

|情景|完整配对|LS-LO净|DD差百分点|vol差百分点|LS内SHORT|仅空净|
|---|---|---:|---:|---:|---:|---:|
|BASE27/RAW_AS_FRACTION|False|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|-160.11|NOT_EVALUABLE|
|BASE27/RAW_AS_PERCENT|False|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|-213.15|NOT_EVALUABLE|
|STRESS43/RAW_AS_FRACTION|False|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|-208.58|NOT_EVALUABLE|
|STRESS43/RAW_AS_PERCENT|False|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|-260.74|NOT_EVALUABLE|

## 与原20/10同方向的真实账户配对

|方向|情景|净变化|SHORT变化|LONG变化|成本变化|DD差百分点|vol差百分点|
|---|---|---:|---:|---:|---:|---:|---:|
|LONG_ONLY|BASE27/RAW_AS_FRACTION|-798.11|0.00|-798.11|28.01|3.42|0.97|
|LONG_ONLY|BASE27/RAW_AS_PERCENT|-800.77|0.00|-800.77|28.09|3.43|0.96|
|SHORT_ONLY|BASE27/RAW_AS_FRACTION|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|SHORT_ONLY|BASE27/RAW_AS_PERCENT|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|LONG_SHORT|BASE27/RAW_AS_FRACTION|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|LONG_SHORT|BASE27/RAW_AS_PERCENT|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|LONG_ONLY|STRESS43/RAW_AS_FRACTION|-814.23|0.00|-814.23|44.38|3.38|0.97|
|LONG_ONLY|STRESS43/RAW_AS_PERCENT|-817.22|0.00|-817.22|44.56|3.39|0.97|
|SHORT_ONLY|STRESS43/RAW_AS_FRACTION|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|SHORT_ONLY|STRESS43/RAW_AS_PERCENT|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|LONG_SHORT|STRESS43/RAW_AS_FRACTION|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|LONG_SHORT|STRESS43/RAW_AS_PERCENT|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|

## 同一连续钱包的预定日历段（BASE/PCT）

|策略|方向|日期段|完整日数|净USDT|LONG|SHORT|vol%|DD%|mean gross%|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|SMA200_SIGNED|LONG_ONLY|SEP_NOV|91|864.17|864.17|0.00|9.60|4.32|11.83|
|SMA200_SIGNED|LONG_ONLY|DEC_FEB|90|-835.67|-835.67|0.00|10.30|10.39|15.65|
|SMA200_SIGNED|LONG_ONLY|MAR_JUN|122|97.81|97.81|0.00|8.60|4.57|12.41|
|SMA200_SIGNED|SHORT_ONLY|SEP_NOV|91|-696.02|0.00|-696.02|9.58|8.10|13.00|
|SMA200_SIGNED|SHORT_ONLY|DEC_FEB|90|853.38|0.00|853.38|9.06|2.37|8.17|
|SMA200_SIGNED|SHORT_ONLY|MAR_JUN|72|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|SMA200_SIGNED|LONG_SHORT|SEP_NOV|91|341.69|954.01|-612.32|10.25|7.85|29.54|
|SMA200_SIGNED|LONG_SHORT|DEC_FEB|90|74.09|-708.20|782.28|10.37|5.02|28.81|
|SMA200_SIGNED|LONG_SHORT|MAR_JUN|72|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|NOT_EVALUABLE|
|CASH|CASH|SEP_NOV|91|0.00|0.00|0.00|0.00|0.00|0.00|
|CASH|CASH|DEC_FEB|90|0.00|0.00|0.00|0.00|0.00|0.00|
|CASH|CASH|MAR_JUN|122|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|LONG_ONLY|SEP_NOV|91|1227.26|1227.26|0.00|10.06|3.49|14.90|
|HOLD|LONG_ONLY|DEC_FEB|90|-843.57|-843.57|0.00|9.96|10.05|13.33|
|HOLD|LONG_ONLY|MAR_JUN|122|189.39|189.39|0.00|10.84|6.60|12.09|

日历段不是事后择日或未来牛熊标签；起点资本为连续账户当时NAV，没有重新投入10k。过去BTC状态归因仅描述，结构化工件保留。same caps不等于risk matched；LS内short与独立SO账户不同。停止保持前缀，完整净指标NOT_EVALUABLE；残仓包含真实mark，非付费平仓的liquidated return不可评价。

## 资源与复现

12个新账户任务区间并集930.00秒；采样共享RAM峰值8.000GB；最大进程RSS0.997GB；新工件0.986GB；GPU0。不是两个任务耗时相加；未单独计时的阶段UNKNOWN。

新增方向账户均运行独立目标/逐分钟NAV/钱包/funding/方向参考验收；若有复用控制，REUSED范围和完整target golden明确记录，不计为新账户运行。

```bash
for cost in BASE27 STRESS43; do
  scripts/with_task_progress.sh --title "CTA303日 $cost" -- env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_cta_leaderboard.py --protocol protocols/CTA_SMA200_303D_${cost}_20261005_V1.json --run-dir /home/xflops/coin-state/<fresh-${cost}-run> --output reports/fast_research/<fresh-${cost}-result>.json
done
```


## D095结果与自主决定

D095复用已有SMA200 signed，完成同303日12个新方向账户（完整4、停止8），另8现金/HOLD控制严格REUSED，0训练/搜参/下载。LONG_ONLY净126.32；价格毛损益220.75，费用+执行93.61，资金费-0.82，vol/DD9.49%/10.39%；SHORT_ONLY净NOT_EVALUABLE；停止前净-190.55，不是完整收益；停止见证{"event_us": 1747031040000000, "phase": "MARK_OBSERVATION", "symbol": "WIFUSDT", "isolated_equity": 0.5883377932590951, "maintenance_margin": 0.5908088549102142, "mark_price": 1.17500765, "quantity": -100.56255462, "NAV": 9809.454681853047, "unpaid_liability": 0.0, "decimal_strings": {"isolated_equity": "0.58833779325909506016759051128975354665", "maintenance_margin": "0.5908088549102142150", "mark_price": "1.17500765", "quantity": "-100.56255462", "NAV": "9809.454681853047142004399703960000000008", "unpaid_liability": "0"}}；LONG_SHORT净NOT_EVALUABLE；停止前净114.00，不是完整收益；停止见证{"event_us": 1747016460000000, "phase": "MARK_OBSERVATION", "symbol": "WIFUSDT", "isolated_equity": 0.40196231058527915, "maintenance_margin": 0.8408884561091301, "mark_price": 1.04434312, "quantity": -161.03681635, "NAV": 10113.995411039576, "unpaid_liability": 0.0, "decimal_strings": {"isolated_equity": "0.40196231058527912628133523789099442063", "maintenance_margin": "0.8408884561091300600", "mark_price": "1.04434312", "quantity": "-161.03681635", "NAV": "10113.99541103957585165469914878999999998", "unpaid_liability": "0"}}；事前四成本/单位情景净/风险均不劣于同方向20/10及HOLD门槛：{"LONG_ONLY": false, "SHORT_ONLY": false, "LONG_SHORT": false}。全部为已见开发、Binance价格配Bybit成本代理，funding单位仍UNKNOWN，MMR假设；marked残仓不当作免费清仓。投资NONE/CASH、长期APR NOT_EVALUABLE。

下一有限主任务：先盘点已授权历史中覆盖完整牛熊周期的 trade/mark/funding 可用性，不触及 locked 正文、不下载、不重试受限API；确定可执行共同窗口和当时上市/流动性可知的池规则，再让固定20/10（稳定参照）与双周期（挑战者）及 CASH/HOLD 在完整共享资本下对照。当前303日和122日结果均已见且起始持仓不同，不能回答长期熊市空头是否稳定获利。暂停这套SMA200配方晋级；reopen需新的独立周期或有证据支持的有限风险机制对照，不调参救同窗。先完成采集断档恢复验收与本模块发布，以上历史盘点尚未运行。


表中停机行的LONG/SHORT、毛损益、费用、资金费与残仓均为停止前缀，不是完整303日收益。有限独立复核：保存的原子agent机制证据核对共同122日1220行目标完全相同；但303日起始持仓、成本基础和NAV不同。原122日WIF空头于05-12 02:02触及假设MMR，新账户同分钟equity18.72高于MMR0.50，仍在06:24停机，只延后262分钟。不得称作规避清算。原机制stdin源码NOT_RETAINED；有限只读源本轮真实运行，复核公式、目标、四LO净桥和八停机范围，不重跑账户。子agent最终复核因额度失败，主agent只接管未完成有限核验；两次检查失败（时间列名、REUSED元标签）保留任务记录，成功task f49cdc8de1294e67bfe02eb80b47e512。源码默认静态核对与synthetic golden不证明完整历史代码因果相等。

采集恢复已保留原库/WAL/SHM、checkpoint、audit head及闭合备份；旧public库绑定扩容前源码，原库不重写，新独立collector_public_v3_20261006.sqlite3绑定现行8GB/150GB并沿用原公开来源范围。micro原库按同一实现新会话续写，RESTART_GAP保留；实际前后两次同PID/start_ticks、heartbeat/事件进展见 reports/CTA_COLLECTOR_RECOVERY_ACCEPTED_20261006_V1.json。退出原因UNKNOWN，断档不计健康时间；8765服务已恢复。不是连续72h/alpha资格。
