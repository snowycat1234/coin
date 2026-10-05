# 固定Donchian20/10：303日连续方向对照

已见2024-09-01至2025-07-01，共303日，10币固定历史池、完整10k共享钱包、abs30/gross60/逐仓1x。两个成本任务并行仅用于不同反事实账户，不相加账户。原122日结果仍为不同起点的独立回测工件，不能拼接或声称本窗unseen。

固定日线前20高低突破、前10退出，过去30日inversevol与signedcov仅降低超过10%年化目标的仓位。开源Jesse通道核与现有财务/分钟执行原入口，无新止损、拟合、阈值或资产收益挑选。BinanceUSD-M配Bybit用户成本是跨场所代理，funding单位UNKNOWN两情景，MMR假设未成为native认证。

|策略|方向|BASE/PCT净|LONG|SHORT|毛价格|手续费+执行|资金费|vol%|DD%|换手|残仓|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|DONCHIAN20_10|LONG_ONLY|927.09|927.09|0.00|993.45|65.52|-0.84|8.53|6.96|4.85|0.00|
|DONCHIAN20_10|SHORT_ONLY|-182.93|0.00|-182.93|-123.81|59.44|0.32|8.20|9.38|4.40|96.11|
|DONCHIAN20_10|LONG_SHORT|924.38|1130.35|-205.97|1065.61|140.81|-0.41|10.27|6.62|10.43|121.62|
|CASH|CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|LONG_ONLY|573.08|573.08|0.00|600.84|26.88|-0.88|10.44|12.99|1.99|173.12|

## 两成本、两未知单位解释配对

|情景|完整配对|LS-LO净|DD差百分点|vol差百分点|LS内SHORT|仅空净|
|---|---|---:|---:|---:|---:|---:|
|BASE27/RAW_AS_FRACTION|True|39.20|-0.48|1.74|-166.95|-151.03|
|BASE27/RAW_AS_PERCENT|True|-2.71|-0.34|1.74|-205.97|-182.93|
|STRESS43/RAW_AS_FRACTION|True|-8.42|-0.54|1.74|-210.31|-186.27|
|STRESS43/RAW_AS_PERCENT|True|-48.56|-0.40|1.74|-247.50|-218.03|

## 同一连续钱包的预定日历段（BASE/PCT）

|策略|方向|日期段|完整日数|净USDT|LONG|SHORT|vol%|DD%|mean gross%|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|DONCHIAN20_10|LONG_ONLY|SEP_NOV|91|1460.47|1460.47|0.00|10.38|3.67|12.50|
|DONCHIAN20_10|LONG_ONLY|DEC_FEB|90|-271.94|-271.94|0.00|8.41|4.98|11.34|
|DONCHIAN20_10|LONG_ONLY|MAR_JUN|122|-261.44|-261.44|0.00|6.61|4.56|6.11|
|DONCHIAN20_10|SHORT_ONLY|SEP_NOV|91|-611.51|0.00|-611.51|6.44|6.78|6.88|
|DONCHIAN20_10|SHORT_ONLY|DEC_FEB|90|365.47|0.00|365.47|8.10|4.33|7.84|
|DONCHIAN20_10|SHORT_ONLY|MAR_JUN|122|63.10|0.00|63.10|9.33|6.60|8.13|
|DONCHIAN20_10|LONG_SHORT|SEP_NOV|91|786.16|1615.50|-829.34|9.86|3.98|21.52|
|DONCHIAN20_10|LONG_SHORT|DEC_FEB|90|164.37|-322.64|487.02|9.78|6.62|18.98|
|DONCHIAN20_10|LONG_SHORT|MAR_JUN|122|-26.15|-162.51|136.36|10.94|4.88|14.15|
|CASH|CASH|SEP_NOV|91|0.00|0.00|0.00|0.00|0.00|0.00|
|CASH|CASH|DEC_FEB|90|0.00|0.00|0.00|0.00|0.00|0.00|
|CASH|CASH|MAR_JUN|122|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|LONG_ONLY|SEP_NOV|91|1227.26|1227.26|0.00|10.06|3.49|14.90|
|HOLD|LONG_ONLY|DEC_FEB|90|-843.57|-843.57|0.00|9.96|10.05|13.33|
|HOLD|LONG_ONLY|MAR_JUN|122|189.39|189.39|0.00|10.84|6.60|12.09|

日历段不是事后择日或未来牛熊标签；起点资本为连续账户当时NAV，没有重新投入10k。过去BTC状态归因仅描述，结构化工件保留。same caps不等于risk matched；LS内short与独立SO账户不同。停止保持前缀，完整净指标NOT_EVALUABLE；残仓包含真实mark，非付费平仓的liquidated return不可评价。

## 资源与复现

20账户完整任务区间并集1551.62秒；采样共享RAM峰值6.437GB；最大进程RSS1.020GB；新工件1.416GB；GPU0。不是两个任务耗时相加；未单独计时的阶段UNKNOWN。

原规则测试按精确sourceSHA复用；本次每个账户都运行独立目标/逐分钟NAV/钱包/funding/方向参考验收，不以旧绿测替代303日入口。

```bash
for cost in BASE27 STRESS43; do
  scripts/with_task_progress.sh --title "Donchian303日 $cost" -- env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_cta_leaderboard.py --protocol protocols/CTA_DONCHIAN_303D_${cost}_20261005_V1.json --run-dir /home/xflops/coin-state/<fresh-${cost}-run> --output reports/fast_research/<fresh-${cost}-result>.json
done
```


## 本轮决定

D093同10币303日连续共享资本，20账户/20完整/0停止。BASE/PCT Donchian LO/SO/LS净927.09/-182.93/924.38 USDT。保留固定Donchian为公开方向benchmark；该303日配方未达到稳健多空投资晋级条件。 BASE/PCT仅多净927.09、DD6.96%/vol8.53%，HOLD净573.08、DD12.99%/vol10.44%；多空净924.38、DD6.62%/vol10.27%，费用加执行140.81（仅多65.52）。多空真实SHORT累计-205.97：SEP_NOV -829.34、DEC_FEB +487.02、MAR_JUN +136.36；空头能在部分下跌段赚钱，但前段损失占主导。四情景LS-LO仅1正/3负，且每个LS空头腿负；唯一正增量伴随LONG贡献变化，不能称short alpha。SHORT毛价格-135.55、手续费加执行70.81、资金费+0.40，交易成本加剧已为负的毛收益。整个多空账户DOGE贡献477.72、WIF308.05，收益集中度仍需另一个时期核验；这些是同一钱包的逐币归因，不是独立账户收益相加。多空终值仍有121.62名义残仓，HOLD173.12，都是marked NAV而非已付费全平收益；仅多已真实付费平仓。过去BTC状态不是未来牛熊标签，不能直接拿事后日期做交易gate。 Donchian20/10仅多为303日透明开发参照；TSMOM12M/LONG_ONLY仍保留原122日参照，不同起点与窗口不能直接排名或拼收益，投资NONE/CASH、长期APR NOT_EVALUABLE。

下一有限任务：复用现有公开20/10、55/20通道，固定等权平均forecast的双周期趋势挑战者；沿用303日价格、账户和成本，与现有20/10对照，只改变趋势速度组合，不搜索权重或止损。假设是减少快速空头在上涨/反弹阶段的错误持仓，同时保留下跌阶段捕捉能力；若四情景净增量和实际风险不稳，保留仅多/空仓开发参照、暂停该组合配方。short主力reopen需这一明确新机制或另一个有效周期的真实净/风险证据，不能由本窗失败永久删除short能力。
