# Interpretation correction: SAME_WINDOW_IMPACT_DIAGNOSTIC

V8纠偏生效。旧 `V7_ORACLE_FLOW_HORIZON_20261002_V1.json` 及相关报告均保留原字节。
其未来flow窗口和return窗口高度重叠；从现在起，研究名称统一为
**SAME_WINDOW_IMPACT_DIAGNOSTIC**，历史文件名只作来源标识。

旧ETH相关性约0.71–0.76及事后条件选择的毛edge只描述该开发样本的同窗口关联。
它们不能解释为可交易预测上限、非重叠预测、因果价格影响或净CAGR证据。
尚无V8非重叠signal→later-return结果，P1 gate未通过。

新验证将分别使用LEAD_LAG_5M_5M、EARLY_LATE_150S的5/10s gap，以及严格OOF
predicted-flow减train-only条件期望的FLOW_SURPRISE；matched direct基线必须使用
同端点、分割、features、成本、风险和频率。现有close/open价格proxy缺BBO，不能
申请真实ask/bid成交资格。当前 **NO_QUALIFIED_CANDIDATE**，≤180天仅 **SCREENING**。
