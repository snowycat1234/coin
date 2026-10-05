# COIN 当前研究状态

投资资格：**NONE/CASH**；长期APR **NOT_EVALUABLE**。

研究参照：Spot HOLD8与日线固定50/50 HOLD10+EXIT10；多空/N资产共享资本能力保留。本轮XGBoost固定配方未采用。

## 最新证据与决定

D085已完成一个共享10币XGBoost三分类fit和20配对账户（May–Jun2025共61日、资本10k）。BASE27/RAW_AS_PERCENT：双向净-944.78、同模型多头-270.34、HOLD 164.49、DonchianEXIT10 -224.35USDT；双向SHORT净-430.37，vol9.40%/DD11.20%高于同模型多头7.46%/7.51%。四成本/资金费口径均未通过任一净/DD/风险调整改善；固定配方暂停，不作为研究主力或投资候选。45日BULL、16日SIDEWAYS、0日BEAR/CRASH；CASH预测0，不称已学会现金或稳定熊市short alpha。账户有真实空头成交、部分成交与资金费；实际残仓保留，净值为marked，未清仓账户liquidated return NOT_EVALUABLE。首次终值断言与重复registry启动失败保留，原唯一模型及首账户复用、概率/预测完全相同；独立全部分钟NAV/钱包/费用/funding验收通过。

报告：[D085](SHARED_DIRECTION_20261005.md)；结构化验收：`reports/SHARED_DIRECTION_ACCEPTED_20261005_V1.json`。旧D084结果与资金费D076单位审计按Git保留，不重复。

## 下一研究选择

下一有限主任务为Phase2过去信息clustering，复用已装scikit-learn，不上Transformer：只读覆盖检查已完成：训练181日中BEAR20日，3—4月验证61日中BEAR25日，三段皆无HIGH_VOL_CRASH（见 reports/SHARED_DIRECTION_REGIME_COVERAGE_20261005_V1.json）；这是相关日数，不是独立样本。接下来固定训练期模型与状态映射、在已见开发窗口作bull允许long/bear允许short/sideways可cash的单因素对照。不以零熊市的当前61日窗口判定熊市short alpha；需要覆盖时先选已有合法开发窗口并统一时间切分。目标是检验行情条件能否识别当前无CASH/牛市错误做空，而非继续扫XGBoost树深、horizon或阈值。当前5d日方向argmax配方暂停；reopen须不同信息/状态机制及成本后配对收益或实际风险增量，不能只改seed重复。Spot约10币扩池数据任务尚未启动，被本次用户明确三分类任务让位；现有HOLD/Donchian/RSI2、永续多空能力不删除。HMM、meta labeling、独立候选验证尚未执行，本版不冒充完成；资金费单位UNKNOWN，仅实际事件两情景，未认证derivatives特征不补造。

## 边界与运行

市场回放已结束。两个既有采集是否仍活动另核进程状态，不将存活称有效证据天数。Binance行情+Bybit用户费用是跨场所代理；原历史过滤、数量规则、瞬时清算/缺口限制保留。无locked正文/账户keys/发单/真钱/付费/GPU；共享5GB、swap0、D总40GB、资本10k/abs30%/gross60%/1x保持。实际资源/时段/SHA见验收和本模块收尾凭证；此前状态按Git，所有尝试和负结果见实验registry与决策日志。
