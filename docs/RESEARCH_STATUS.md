# COIN 当前研究状态

Temporal two-expert单一四fit已完成保存，0 refit/0新增pool：GRU NO_CASH132、MLP NO_CASH143、MLP WITH_CASH522为原proxy STOP；GRU WITH_CASH349耗1200s为NOT_CONVERGED。62测试、5个只读semantic checks通过，778 dates/5真实wallets、64×CORE5×24+24 masks、共享train907 rows scaler，13k参数与exact原math保留。全部terminal model/Adam/RNG后才评分seen May–June；仅MLP NO_CASH完成61日proxy，net−517.39USDT/paid close，其余full-PnL不可得，未native/OOS认证。第一STOP已证为marked drift：target净58.5985%、legs59.0218%、fill58.0575%、次日mark60.0508%；原native返回REDUCTION_REQUIRED而非立刻HALT，并要求收费/容量受限risk order。proxy/native语义不一致，不能称target cap breach或selector不可能。未来受影响fit前应区分drift与opening/target硬界，并实现收费risk reductions及精确VJP；本轮未改math/未重跑。用户准许后按实际container4CPU/16GB能力仅并行最后两独立arm，实际环境peak1.84GB/swap0/OOM0。证据/权重/模拟paths见[result](../research/temporal-four-fit-20261009/results/RESULT.json)、[module](../modules/temporal_two_expert/README.md)。native验证与新Donch hypothesis由独立任务负责，不重复。

## 当前最佳研究方案与证据等级

**投资资格NONE/CASH，稳定净APR未知。** 研究控制保留原CSMOM21与SMA200；固定50%SHORT抵押物保护完成10账户后暂停，不调阈值救结果。附件开源思路已登记，重点是共享信息、净utility/成本、连续权重与完整组合最差阶段，不以新模型数量作进展。

## 本版实际结果

同一原targets/行情/完整10k资本，两资金解释各5seen窗，10新钱包、0fit/搜参。原XRP清算避免；2024H1/H2净改善约165/178USDT(scale.01)，但SHORT仍亏。2025H1净收益少146.66/146.94USDT，MDD增加约.76个百分点、成本反降；原门槛失败，PAUSE。41日原基线vol>12%继承，非保护造成；已有60.176%–60.966%峰值gross漂移未修复。不能宣称保护保证安全或熊市alpha。

零账户实际episode查明2025-05-11 DOGE强平式保护在反弹高位截断原仓，May12原策略已正常退出；原episode−538.53对保护−688.33，差−149.81几乎解释SHORT−153.04。封锁间没有原新空头开仓，不支持继续研究缩短cooldown。两个episode都亏，未把损失收复称赚钱，未编辑收益曲线。

完整结果/复现/风险/来源见[报告](../reports/SHORT_COLLATERAL_HALF_20261008.md)、[实际账本摘要](../reports/SHORT_COLLATERAL_HALF_20261008.json)、[共同输入及资金桥复核](../reports/SHORT_COLLATERAL_HALF_REVIEW_20261008.json)、[实际episode](../reports/SHORT_COLLATERAL_HALF_EPISODE_20261008.json)。原负结果保留。

## 决定与下一步

保留真实paid/persistent/reduce-only保护能力，暂停该配方；重开需独立tail utility证据，不扫描50%/ATR/reentry。日级absolute-sign gate与无条件半权mix仍暂停；selector重开需稳定ranking可预测性。下一选结构问题：相对LONG alpha与高挤压alt SHORT是否应分离，能否用流动市场对冲保留组合效用。先只读旧targets/真实SHORT episodes核集中度、past-only beta与对冲损失；还未冻结/运行新钱包或模型。BTC亦有挤压与1x尾部风险，不预设更安全或更赚钱。若无实质证据就保留最强冻结策略，不再加退出规则。

## 实际任务与边界

10/10服务器账户成功退出，346.077秒；capacity.237秒、review1.393秒、episode 0.341秒。7相关测试通过、旧default/no-trigger golden相同；20摘要/10k资本/完整分钟、10对输入targetSHA、实际保护收费成交和既定gate独立核对。无本轮后台研究，8765已同步完成，采集健康未重认证。共享8GB/swap0/GPU0；峰值UNKNOWN，最大采样2.994GB。

D最近实扫45,455,143,069B@1791408013.8738086，非当前重扫；server本轮state83,424,814B@2026-10-07T23:38:01Z，未增行情。150GB/120预警/135停止新增/15预留不变。原10k/30%abs/60%gross/1x逐仓；BinanceUSD-M+Bybit费用仍代理，资金单位/MMR/filter/CORE5与真实风险局限阻止晋级。无密钥/真钱/测试网/主网单/付费/GPU/locked。只读状态与当前代码优先；旧证据依Git/原路径复现。
