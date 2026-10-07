# 恢复熊市训练支持后：原容量Ridge条件信息复验

决定：PAUSE_EXACT_RIDGE_INFORMATION_RECIPE；投资NONE/CASH。12主fit＋12负对照fit，零新钱包。

|已见窗口|资金解释|输入|选择参考效用bp/周|比最佳单expert差bp|比过去赢家差bp|Oracle gap capture|错位负对照bp|
|---|---:|---|---:|---:|---:|---:|---:|
|seen-2024-first-half|1|FEEDBACK|25.387|-13.307|-13.307|-19.49%|8.366|
|seen-2024-first-half|1|MARKET_INTENT|33.090|-5.604|-5.604|-8.21%|48.524|
|seen-2024-first-half|1|COMBINED|39.887|1.192|1.192|1.75%|42.795|
|seen-2025-first-half|1|FEEDBACK|-47.010|-86.489|-37.193|-117.19%|0.704|
|seen-2025-first-half|1|MARKET_INTENT|6.372|-33.108|16.188|-44.86%|-8.004|
|seen-2025-first-half|1|COMBINED|-5.532|-45.012|4.284|-60.99%|-1.663|
|seen-2024-first-half|0.01|FEEDBACK|28.778|-16.103|-16.103|-24.81%|39.788|
|seen-2024-first-half|0.01|MARKET_INTENT|41.974|-2.907|-2.907|-4.48%|9.864|
|seen-2024-first-half|0.01|COMBINED|45.902|1.021|1.021|1.57%|52.638|
|seen-2025-first-half|0.01|FEEDBACK|-25.144|-64.451|-16.175|-86.97%|-13.395|
|seen-2025-first-half|0.01|MARKET_INTENT|5.418|-33.890|14.387|-45.73%|-9.973|
|seen-2025-first-half|0.01|COMBINED|-4.337|-43.645|4.632|-58.89%|18.976|

这是零入场7日follow、执行价格端点估值、扣entry/internal turnover/funding但不强制退出的reference utility，不是共享钱包净PnL/APR。
所有资金解释都是同一市场路径的条件情景，不增加独立样本。验证周块不重叠；train日标签重叠，不把每日行数当独立样本。
一次错位/匹配频率random仅负对照，不支持placebo95%或显著性。CASH reference0不等于实际已有仓位能免费清仓。

Reference-only prediction study, not cost-after actual shared-wallet returns/APR or proof of real-time regime alpha.
Daily train labels overlap; two funding interpretations share prices and do not create independent samples. Validation windows are already-seen development.
Single-week net calibration does not certify all expert paths or ranking fidelity; daily proxy omits native quantity buffer, risk/partialfills/liquidation and observedmark.
Reference CASH0 does not mean existing actual positions can close free; actual soft mixture must pay net target switching once and preserve risk reductions.
One shifted fit and random control per cell cannot establish placebo95pct or statistical significance.
Binance USD-M data/Bybit cost assumptions remain cross-venue proxy; funding unit uncertified and both scales required.
Only input-source support changes. Two2024/25 scored windows are already seen development; restored2022 and previously omitted2023 dates do not create new unseen evaluation.
Reviewed scored labels unchanged<=1e-12; rolling features maxnumericdelta1.725e-12 with exact scored primitive windows. Outcomes cannot be promoted to native sharedwallet profit or stableAPR.
Only one repeat after data cause correction; no further Ridge alpha/feature/horizon search if unchanged gates fail.

复现：python -B scripts/research/joint_expert_information.py --protocol protocols/JOINT_EXPERT_INFORMATION_REPAIRED_20261008.json --state /home/ubuntu/coin/execution-state/joint-information-NEW，须8GB/swap0/GPU0受限scope；完成/部分启动state不会自动重拟合。

## 投资判断

恢复157日/22周成熟熊市训练支持后，同一Ridge容量仍没有稳定条件优势。2025联合模型25周选择HOLD19次、CSMOM零次；只补数据不足以解决相对优势识别。停止本配方，不增加alpha、特征、horizon或容量；这不否定SHORT能力或所有regime方法。

10个相关反例通过，独立零拟合复算PASS_WITH_LIMITATIONS。复验12主fit+12错位fit共0.710秒，零新钱包；8GB/swap0/GPU0、单worker/线程，峰值RAM因内核计数缺失为UNKNOWN。所有任务已完成，无后台训练。

下一主任务固定50/50 SMA200绝对趋势与CORE5相对强弱，使用一个完整10k钱包、原caps及成本。先检验互补是否在实际净订单、收费与共同风险后成立；增加同风险SMA控制，不平均独立账户收益，不再训练selector。新对照未运行。
