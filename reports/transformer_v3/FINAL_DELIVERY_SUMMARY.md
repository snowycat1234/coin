# Transformer v3 最终交付

**B. CONTINUE RESEARCH；不晋级，投资状态 NONE/CASH。**

发布抓取时间（UTC）：2026-10-07T14:42:24.722455+00:00。所有后台模块正常完成，服务器不再训练或回放。

|模块|实际执行|完整日历且收费终值现金|
|---|---:|---:|
|旧模型强平回放|864/864|861/864|
|旧模型HALF对照及新开发账户|348/348、576/576|与旧回放合计1782/1788|
|开发训练／固定过去数据最终训练|60/60、12/12|训练完成不代表盈利|
|五种补值×两种资金费口径后续账户|400/400|395/400|

未完整账户均保留N/E，不把停机前缀当完整收益。执行完成数与经济完整数分别报告。

冻结候选：ORACLE_POLICY_CROSS_ASSET / NEUTRAL / FULL。模型及仓位选择在后续测试前冻结。

|资金费scale|五方案净收益率 min / median / max|五方案净USDT min / median / max|
|---:|---|---|
|0.01|-4.4108 / -4.4108 / -4.4102|-441.0788 / -441.0779 / -441.0203|
|1.0|-6.5786 / -6.5778 / -6.5778|-657.8600 / -657.7847 / -657.7772|

两个资金费口径下均亏损，五种补值方案均未通过经济门槛；开发期候选门槛也未通过。LONG为正、SHORT为负，封存期所选每个独立账户均有一次1000SATS强平并在正常时点重新入场。
B来自事前登记的描述性排名信号，不能解释为策略已合格；新policy的日频expert代理regret改善未通过预设跨fold门槛。

旧111个停机账户恢复108个：96个强平与12个旧破产停机均恢复，3个容量受限风险减仓保持N/E。
最终重新核对16,025个旧v2保护文件、33,182,604,674字节，全部SHA保持不变。旧正式封存N/E和负结果永久保留。
官方risk档位缺失，MMR=.005/MMD=0为条件假设。五种补值只是敏感性实验，没有恢复精确交易所事件；未执行真实订单或paper部署。

- [最终报告：11个问题](TRANSFORMER_V3_FINAL_REPORT.md)
- [全部400行后续结果及五方案范围](TRANSFORMER_V3_FINAL_RESULTS.json) / [CSV](TRANSFORMER_V3_LOCKED_ROWS.csv)
- [开发比较报告](TRANSFORMER_V3_DEV_REPORT.md) / [1788行开发结果](TRANSFORMER_V3_DEV_RESULTS.json) / [CSV](TRANSFORMER_V3_DEV_ROWS.csv)
- [不可评价账户原因](FINAL_NOT_EVALUABLE_ROWS.json)
- [2188项账户摘要、独立审计、目标身份校验](FINAL_WALLET_EVIDENCE_INDEX.json)
- [后续测试前冻结凭据](LOCKED_DEVELOPMENT_FREEZE.json) / [旧证据最终完整性](FINAL_V2_PRESERVATION_AUDIT.json)
- [本次发布逐文件SHA](FINAL_PUBLICATION_MANIFEST.json)

行情、模型权重、环境和分钟大账本留服务器；本次发布没有重跑任何训练或经济账户。先前190/576静态阶段快照保留供追溯。
