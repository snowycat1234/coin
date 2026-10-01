# FR69 V2 30日连续回放独立只读验收

实际结论：三方向工件绑定、完整共同indices、原单位预测字节、同batch、初始统一scaler、weekly真实窗口与River最终成熟状态核验通过；未发现实际correctness blocker。

共同测试端点19,144；XGB首周9,774、次周9,370，无重复或丢失。真实07-22内部周界前最后310秒只有一个共同有效端点：2025-07-21 23:55:00 UTC，label于07-22 00:00:10 UTC成熟；该端点实际保留。不能把此前内存探针理论五点写成真实市场五点。全局终点前最后310秒共同maturity规则排除，不计作内部周界删除。

Ridge/River/XGB均绑定相同batch SHA f021f5c01077a60e935d909605f461a2e4101a3ec7eb14b85f3adb675a073e70；三者均19,144×2×4原单位finite预测，所有登记工件SHA匹配。三套2/4/8bp场景均为一次初始10,000 NAV、连续14日。代码只一次建立全局EvaluationBatch，每方向一次evaluate，周循环只分配XGB预测，不重置经济状态。账本成本/风控算术由根另行复核，本审计没有重新计算九账本。

River可信绑定checkpoint只读load通过，queue空、predicted=learned、final clock是全局终点；initial validation不learn、cross-week state reset=0。外部scaler完整receipt保持初始真实fit时点，feature available与target maturity均不晚于初始fit cutoff。

30d来源07-01至07-31前，OOS07-15至07-29前，SMOKE_ONLY。180d静态入口为07-01至12-28前来源、07-15至12-28前166日OOS；没有把本次30日结果记作180日通过或六fold/top-3资格。

本次仅读取指定run的既有工件与8个关键source，未拟合、未重算模型预测、未扫描项目、未改源码/旧凭证、未消费locked。对应JSON：INDEPENDENT_READONLY_REVIEW_20261002_V1.json。
