# DC_TWO_SPEED：303日连续方向对照

已见2024-09-01至2025-07-01，共303日，10币固定历史池、完整10k共享钱包、abs30/gross60/逐仓1x。两个成本任务并行仅用于不同反事实账户，不相加账户。原122日结果仍为不同起点的独立回测工件，不能拼接或声称本窗unseen。

复用原20/10、55/20通道虚拟状态，先固定等权平均forecast再进行相同inversevol/signedcov，仅改变趋势速度组合；{-1,-.5,0,.5,1}不是两个满资金账户。12新账户实际执行，8原CASH/HOLD经完整目标golden、来源和工件SHA复用。无拟合/权重搜索/止损修改。BinanceUSD-M配Bybit成本仍为代理；funding单位UNKNOWN两情景、MMR假设，不能认证native或长期APR。

|策略|方向|BASE/PCT净|LONG|SHORT|毛价格|手续费+执行|资金费|vol%|DD%|换手|残仓|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|DC_TWO_SPEED|LONG_ONLY|879.98|879.98|0.00|936.14|55.33|-0.84|8.47|6.60|4.10|0.00|
|DC_TWO_SPEED|SHORT_ONLY|-174.74|0.00|-174.74|-128.58|46.53|0.37|8.16|7.59|3.45|151.42|
|DC_TWO_SPEED|LONG_SHORT|1058.97|1212.21|-153.24|1171.81|112.39|-0.45|9.76|7.04|8.32|186.86|
|CASH|CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|LONG_ONLY|573.08|573.08|0.00|600.84|26.88|-0.88|10.44|12.99|1.99|173.12|

## 两成本、两未知单位解释配对

|情景|完整配对|LS-LO净|DD差百分点|vol差百分点|LS内SHORT|仅空净|
|---|---|---:|---:|---:|---:|---:|
|BASE27/RAW_AS_FRACTION|True|212.83|0.25|1.30|-115.09|-137.84|
|BASE27/RAW_AS_PERCENT|True|178.99|0.44|1.30|-153.24|-174.74|
|STRESS43/RAW_AS_FRACTION|True|178.21|0.30|1.30|-147.62|-164.68|
|STRESS43/RAW_AS_PERCENT|True|143.34|0.49|1.29|-186.73|-202.93|

## 与原20/10同方向的真实账户配对

|方向|情景|净变化|SHORT变化|LONG变化|成本变化|DD差百分点|vol差百分点|
|---|---|---:|---:|---:|---:|---:|---:|
|LONG_ONLY|BASE27/RAW_AS_FRACTION|-47.53|0.00|-47.53|-10.15|-0.34|-0.06|
|LONG_ONLY|BASE27/RAW_AS_PERCENT|-47.11|0.00|-47.11|-10.19|-0.36|-0.06|
|SHORT_ONLY|BASE27/RAW_AS_FRACTION|13.19|13.19|0.00|-12.89|-1.67|-0.05|
|SHORT_ONLY|BASE27/RAW_AS_PERCENT|8.19|8.19|0.00|-12.90|-1.79|-0.05|
|LONG_SHORT|BASE27/RAW_AS_FRACTION|126.09|51.85|74.24|-28.33|0.38|-0.51|
|LONG_SHORT|BASE27/RAW_AS_PERCENT|134.59|52.73|81.86|-28.43|0.42|-0.51|
|LONG_ONLY|STRESS43/RAW_AS_FRACTION|-41.61|0.00|-41.61|-16.11|-0.36|-0.06|
|LONG_ONLY|STRESS43/RAW_AS_PERCENT|-41.38|0.00|-41.38|-16.13|-0.37|-0.06|
|SHORT_ONLY|STRESS43/RAW_AS_FRACTION|21.59|21.59|0.00|-20.49|-1.77|-0.05|
|SHORT_ONLY|STRESS43/RAW_AS_PERCENT|15.10|15.10|0.00|-20.53|-1.88|-0.05|
|LONG_SHORT|STRESS43/RAW_AS_FRACTION|145.02|62.68|82.33|-44.87|0.48|-0.51|
|LONG_SHORT|STRESS43/RAW_AS_PERCENT|150.52|60.77|89.75|-44.89|0.52|-0.51|

## 同一连续钱包的预定日历段（BASE/PCT）

|策略|方向|日期段|完整日数|净USDT|LONG|SHORT|vol%|DD%|mean gross%|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|DC_TWO_SPEED|LONG_ONLY|SEP_NOV|91|1352.16|1352.16|0.00|10.10|3.48|11.81|
|DC_TWO_SPEED|LONG_ONLY|DEC_FEB|90|-398.61|-398.61|0.00|8.79|5.22|14.36|
|DC_TWO_SPEED|LONG_ONLY|MAR_JUN|122|-73.57|-73.57|0.00|6.41|3.77|6.54|
|DC_TWO_SPEED|SHORT_ONLY|SEP_NOV|91|-594.99|0.00|-594.99|6.07|6.68|6.27|
|DC_TWO_SPEED|SHORT_ONLY|DEC_FEB|90|598.62|0.00|598.62|8.27|2.86|8.25|
|DC_TWO_SPEED|SHORT_ONLY|MAR_JUN|122|-178.38|0.00|-178.38|9.26|7.59|8.34|
|DC_TWO_SPEED|LONG_SHORT|SEP_NOV|91|893.54|1602.12|-708.58|9.54|3.69|19.78|
|DC_TWO_SPEED|LONG_SHORT|DEC_FEB|90|390.06|-318.67|708.73|9.45|5.01|21.35|
|DC_TWO_SPEED|LONG_SHORT|MAR_JUN|122|-224.63|-71.24|-153.39|10.13|7.04|15.55|
|CASH|CASH|SEP_NOV|91|0.00|0.00|0.00|0.00|0.00|0.00|
|CASH|CASH|DEC_FEB|90|0.00|0.00|0.00|0.00|0.00|0.00|
|CASH|CASH|MAR_JUN|122|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|LONG_ONLY|SEP_NOV|91|1227.26|1227.26|0.00|10.06|3.49|14.90|
|HOLD|LONG_ONLY|DEC_FEB|90|-843.57|-843.57|0.00|9.96|10.05|13.33|
|HOLD|LONG_ONLY|MAR_JUN|122|189.39|189.39|0.00|10.84|6.60|12.09|

日历段不是事后择日或未来牛熊标签；起点资本为连续账户当时NAV，没有重新投入10k。过去BTC状态归因仅描述，结构化工件保留。same caps不等于risk matched；LS内short与独立SO账户不同。停止保持前缀，完整净指标NOT_EVALUABLE；残仓包含真实mark，非付费平仓的liquidated return不可评价。

## 资源与复现

12个新账户任务区间并集1046.46秒；采样共享RAM峰值7.359GB；最大进程RSS1.016GB；新工件0.965GB；GPU0。不是两个任务耗时相加；未单独计时的阶段UNKNOWN。

新增方向账户均运行独立目标/逐分钟NAV/钱包/funding/方向参考验收；若有复用控制，REUSED范围和完整target golden明确记录，不计为新账户运行。

```bash
for cost in BASE27 STRESS43; do
  scripts/with_task_progress.sh --title "CTA303日 $cost" -- env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_cta_leaderboard.py --protocol protocols/CTA_TWO_SPEED_${cost}_20261005_V1.json --run-dir /home/xflops/coin-state/<fresh-${cost}-run> --output reports/fast_research/<fresh-${cost}-result>.json
done
```


## 决定与下一步

D094一个固定20/10+55/20等权forecast配方，12新方向账户/12完整，8控制REUSED。BASE/PCT LO/SO/LS净879.98/-174.74/1058.97 USDT；LS对原20/10四情景净变化126.09/134.59/145.02/150.52。双周期多空未满足四情景净/实际风险晋级条件，暂停该配方晋级，保留公共benchmark及双向能力。 BASE/PCT双周期多空净1058.97、vol9.76%/DD7.04%，原多空924.38、vol10.27%/DD6.62%；成本140.81降112.39。四情景同向净改善126.09..150.52、vol约降0.51百分点，但DD升0.38..0.52百分点，事前风险不劣条件未通过。多空LONG1212.21、SHORT-153.24；比原多空LONG改善81.86、SHORT改善52.73，两者共同贡献净增量134.59，不能全部归为空头alpha。自身LS相对自身LO四情景均正，但SHORT累计仍负，signedcov/持仓竞争改变LONG暴露。连续日期段SHORT为-708.58/+708.73/-153.39，原20/10为-829.34/+487.02/+136.36；早段损失减轻、中段捕捉改善，但最后122日空头从盈利转亏，多空整段从-26.15恶化到-224.63。合计改善不代表各阶段稳定改善，不能用事后日期拼接赢家。双周期仅多879.98、DD6.60%/vol8.47%，原仅多927.09、DD6.96%/vol8.53%；这是收益与风险取舍，未出现所有指标占优的配方。多空残仓186.86，HOLD173.12，均为marked NAV；两种仅多已付费平仓。 新旧均为303日已见跨场所代理；价格、资金费未知解释、用户费用、共享10k、caps/1x保持。双周期多空保留为较高净收益的开发比较工件，不声称已通过晋级；原仅多保持稳定较低波动参照。投资NONE/CASH、长期APR NOT_EVALUABLE。

下一有限主任务：核对现有授权Binance funding原始来源、解析链与官方单位/结算时钟，争取把目前两UNKNOWN情景转为有来源支持的自洽资金费口径；不根据更高盈利选择解释，不改写D093/D094历史结果。若无法确认，仅保留UNKNOWN和有限筛选；之后再依据固定公开benchmark差距选择新机制或独立合法窗口。固定双周期配方reopen需另一个有效周期或新失效机制证据，不搜索period/权重救本窗。
