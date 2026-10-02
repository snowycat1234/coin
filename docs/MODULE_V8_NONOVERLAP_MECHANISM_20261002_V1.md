# V8 非重叠机制与新信息路线证据验收

候选 **NONE / NO_QUALIFIED_CANDIDATE**；目标 risk-constrained net CAGR；P1 **NOT_READY**。
研究范围仅 SCREENING。没有行情模型拟合、交易 ledger 或经济资格。

## 实际科学发现

四个已预登记 OOS 段：Aug20–27、Sep25–Oct02、Oct24–31、Nov18–25。
全部三种非重叠标签、四路 flow／两路 Spot return，共 96 个描述性配对，不等于 96 个
独立试验。方向只由 TRAIN Spearman 冻结，OOS 不翻转；IID p-value 未用于显著性。

24 项主要配对 OOS Spearman 范围 **−0.0626013～+0.0163353**，绝对值最大 0.0626013。
TRAIN／OOS 方向相同 17／24，这些共享日期和标签，不能当 24 次独立支持。TRAIN方向的
平均后续响应 **−0.122768～+0.429106 bp**，不是可成交 edge、平衡成本或净收益。
此前“所有绝对值低于0.06”的近似描述已更正。旧同窗口 oracle 来自不同窗口，
不能直接当本轮的匹配对照或预测上限。

这组统计削弱强非重叠影响的假设，但尚未完成严格 OOF、matched DIRECT、共同风险成本
和最强基准，因此不冒称 P1 已经济失败或通过。用有限固定第一层实验进一步证伪；不扩深度族。

## 实际执行及日历修复

- V2：session 98389 exit 0；76 TRAIN／OOS UTC日，305.99 秒，peak RSS 919.10MB。
- 独立检查 session 40429 exit 0，重算96汇总／672日统计相符；发现每fold／variant缺20个
  未拟合TRAIN分钟，240行 scope gap；原 FAIL 保留。
- V3：session 95905 exit 0；只读32来源档补齐240行、全部不评分；13.49秒，RSS515.70MB。
- 独立复审 session 79759 exit 0：完整 TRAIN17280／OOS10080分钟；原全部行及 scored
  IDs／浮点位保持，96／672统计 canonical SHA不变。
- 审计第一次记录的 task 路径缺失也原样保留；独立短复核从实际 `task-progress/`
  路径核对五项任务字段及两个 checker completed/0，没有再跑行情或统计。

独立复审报告 SHA `13c3b879be4a3bd0c20fc25e569ceb1d5b47126f056a31d98568c13c1bcabf53`。
根侧验收 `V8_MECHANISM_ROUTE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json` SHA
`5b33c1a67f19e03d79c13fa6898154aa4fbf2cc48aa71cf2c4b763c6a2277317`。
原源码、协议、来源、报告与 Parquet不改；新小型 checker／输出及RUN_BINDING精确归档。

## Frontier 数据可行性

官方 2025 Aug–Nov 两币 funding／mark／index 月档24份的压缩总量约16.26MB，HEAD及小
CHECKSUM可得，尚未下载正文或作来源接受。bookTicker测试对象无可用完整凭证，不伪造
最后发布日期。官方协作者说明 bookDepth 为30秒采样的百分比距离汇总，不是逐价位L5/BBO。
相关原回复、URL、metadata和精确脚本已绑定在 `V8_OFFICIAL_INPUT_FEASIBILITY_20261002_V1.json`。

下一步为独立 funding+mark/index 来源 QA；需要事件时点、真实资金费间隔、双腿成交成本／
历史保证金和资本映射后才可评价 carry。mark/index OHLC不能代替BBO或资金费charge mark。

## 下一步及界限

共用缓存只生成一次478特征和完整TRAIN／VAL／OOS日历；固定第一层 strictOOF surprise
与 matchedDIRECT使用同样行、scaler、标签、风险和成本。旧端点索引按未来标签删行，
不得复用作新预测资格；只复用四流 `joint_rows` 读取接口。新缓存先合成与独立检查。

长期净CAGR、最强基准增量、平衡成本、DSR／PBO／SPA／bootstrap及收益集中度均未知。
缺实际BBO／depth／latency／size和历史适用费率时不能执行资格。TCN／深度族继续等待P1；
maker等待queue/fill；真正L5等待真实价位输入。P1失败后aggTrades方向暂停，重开仅按V8。
