# Transformer v3 当前阶段成果（中途快照）

抓取时间（UTC）：2026-10-07T10:02:40.070426+00:00。这是静态快照，服务器继续后台执行。

| 模块 | 完成数 | 状态 |
|---|---:|---|
|旧模型逐仓强平回放|864/864|完成|
|旧模型半仓位对照|348/348|完成|
|新 policy 开发训练|60/60|完成|
|固定过去数据最终训练|12/12|完成|
|新模型开发账户|190/576|进行中，仅发布已完成账户|
|开发汇总与冻结|—|待执行|
|五种补值假设的后续账户测试|0/400|待执行|
|最终报告与旧证据完整核验|—|待执行|

旧111个停机账户恢复108个：96个强平停机、12个旧破产停机均恢复完整回放；3个风险减仓受限仍保留N/E。
864项中861项完整日历且终端现金结算；原720模型账户717项完整。753项原完整且未强平账户完成经济结果一致性核对，没有新增强平触发。
旧neutral稳定性门槛：False。修好回放不代表策略通过投资门槛。

两种新模型的60次开发训练及12次固定过去数据最终训练完成，发布训练记录和权重/scaler SHA；行情、权重及分钟账本仍留服务器。
已完成的预测诊断及新旧regret差异均附表。regret使用日频expert代理，IC、未来价差和命中率不等于真实账户净收益。
半仓位结果和与全仓位配对表已发布；新模型账户表仅是已完成子集，不能用该子集做最终选择或认定盈利。

官方risk档位仍不可得，MMR=.005/MMD=0为明确条件假设；原v2正式封存N/E保留。补值测试尚未运行。投资资格仍NONE/CASH。

索引：

- [真实阶段进度与来源SHA](PROGRESS_SNAPSHOT.json)
- [旧模型强平回放报告](V2_BYBIT_LIQUIDATION_REPORT.md) / [完整864行分析](V2_REPLAY_ANALYSIS.json)
- [348项半仓位账户](HALF_CONTROL_COMPACT_RESULTS.json) / [全仓位与半仓位配对](OLD_MODEL_FULL_HALF_PAIRS.json)
- [60次开发训练记录](POLICY_DEVELOPMENT_FIT_RECEIPTS.json) / [12次最终训练记录](POLICY_FINAL_FITS.json)
- [新模型预测诊断](POLICY_PREDICTION_METRICS.json) / [新旧预测对照](POLICY_COMPLETED_PREDICTION_COMPARISON.json)
- [新模型已完成账户子集](POLICY_DEVELOPMENT_PARTIAL_RESULTS.json)
- [全部已发布账户的独立核验与来源SHA](WALLET_EVIDENCE_INDEX.json)
- [训练前协议提交凭据](PROTOCOL_COMMIT_RECEIPT.json) / [47项已提交源码测试](COMMITTED_AUTONOMOUS_TESTS.log)

服务器查看动态进度：`bash /home/ubuntu/coin/watch_transformer_v3.sh`。退出查看器不停止后台任务。
