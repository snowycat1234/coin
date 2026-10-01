# P04 预登记 Logistic 外层研究结果

状态：**STOP**。最终六个月仍锁定，未计算绩效。

训练 24 个月、验证 3 个月、测试 3 个月、步长 3 个月；不完整 fold 跳过。
C 仅根据当轮验证集选择，scaler 和模型仅拟合训练集。

| 候选 | 状态 | OOS 净收益 | 日度 Sharpe | B2 净收益 | 未过门槛 |
|---|---|---:|---:|---:|---|
| 1h | STOP | -0.089938 | -2.026940 | -0.055006 | positive_net_return, daily_sharpe, exceed_B2, quarter_concentration, fee_x2_nonnegative, slippage_x2_nonnegative |
| 15m | STOP | -0.174707 | -2.971857 | -0.055006 | positive_net_return, daily_sharpe, exceed_B2, drawdown, quarter_concentration, fee_x2_nonnegative, slippage_x2_nonnegative |

详见 summary.json、各 fold 的 selection.json/model.json 和三种成本报告。
未通过时保留失败记录，停止模型升级；门槛和成本不降低。
INSUFFICIENT_DATA 表示无法形成有效检验；INVALID_RUN 表示技术或数据合同异常。
技术修复须保持协议、配置、锁定数据相同，并记录显式恢复原因；完成结果不重跑。
HOLDOUT_REQUIRED 仅表示开发集通过，须冻结一项策略后单次揭晓留出。
置信区间为配对日度收益差的 7 日区块自助法，不能保证未来盈利。
