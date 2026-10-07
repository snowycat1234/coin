# 联合市场与成熟反馈：固定Ridge信息筛选

决定：PAUSE_EXACT_RIDGE_INFORMATION_RECIPE；投资NONE/CASH。12主fit＋12负对照fit，零新钱包。

|已见窗口|资金解释|输入|选择参考效用bp/周|比最佳单expert差bp|比过去赢家差bp|Oracle gap capture|错位负对照bp|
|---|---:|---|---:|---:|---:|---:|---:|
|seen-2024-first-half|1|FEEDBACK|39.211|0.516|0.516|0.76%|26.057|
|seen-2024-first-half|1|MARKET_INTENT|40.313|1.619|1.619|2.37%|2.678|
|seen-2024-first-half|1|COMBINED|40.313|1.619|1.619|2.37%|2.678|
|seen-2025-first-half|1|FEEDBACK|10.292|-29.188|20.108|-39.55%|-8.029|
|seen-2025-first-half|1|MARKET_INTENT|5.167|-34.312|14.983|-46.49%|9.413|
|seen-2025-first-half|1|COMBINED|-0.916|-40.396|8.900|-54.73%|31.566|
|seen-2024-first-half|0.01|FEEDBACK|49.593|4.712|4.712|7.26%|25.914|
|seen-2024-first-half|0.01|MARKET_INTENT|45.842|0.961|0.961|1.48%|4.296|
|seen-2024-first-half|0.01|COMBINED|45.842|0.961|0.961|1.48%|4.296|
|seen-2025-first-half|0.01|FEEDBACK|18.238|-21.069|27.207|-28.43%|-5.548|
|seen-2025-first-half|0.01|MARKET_INTENT|8.692|-30.615|17.661|-41.31%|-0.528|
|seen-2025-first-half|0.01|COMBINED|-0.431|-39.739|8.538|-53.62%|32.201|

这是零入场7日follow、执行价格端点估值、扣entry/internal turnover/funding但不强制退出的reference utility，不是共享钱包净PnL/APR。
所有资金解释都是同一市场路径的条件情景，不增加独立样本。验证周块不重叠；train日标签重叠，不把每日行数当独立样本。
一次错位/匹配频率random仅负对照，不支持placebo95%或显著性。CASH reference0不等于实际已有仓位能免费清仓。

Reference-only prediction study, not cost-after actual shared-wallet returns/APR or proof of real-time regime alpha.
Daily train labels overlap; two funding interpretations share prices and do not create independent samples. Validation windows are already-seen development.
Single-week net calibration does not certify all expert paths or ranking fidelity; daily proxy omits native quantity buffer, risk/partialfills/liquidation and observedmark.
Reference CASH0 does not mean existing actual positions can close free; actual soft mixture must pay net target switching once and preserve risk reductions.
One shifted fit and random control per cell cannot establish placebo95pct or statistical significance.
Binance USD-M data/Bybit cost assumptions remain cross-venue proxy; funding unit uncertified and both scales required.

复现：python -B scripts/research/joint_expert_information.py --protocol protocols/JOINT_EXPERT_INFORMATION_20261008.json --state /home/ubuntu/coin/execution-state/joint-information-NEW，须8GB/swap0/GPU0受限scope；完成/部分启动state不会自动重拟合。

## 研究判断：先解决熊市输入支持，暂停本配方

实际实现：相同四expert/CORE5/7日目标/共同掩码的成熟反馈、市场与当前意图、联合输入对照，源码和协议提交后才拟合。没有追加参数或新钱包。2024 COMBINED与MARKET_INTENT选择完全相同：25周中24周SMA200、1周HOLD。2025 COMBINED则19周HOLD、4周CASH、各1周SMA200/CSMOM；CSMOM真正胜HOLD有15周，模型仅预测4周。CSMOM−HOLD预测均值−104/−105bp/周，真实+49/+48bp。没有可靠联合选时增量。

独立只读复核重算12cell的选择、效用/Oracle/regret、成熟时钟、purge及门槛，结果一致。每窗25个不重叠验证周，均已见开发；训练266/632个重叠日，不作同等独立样本数。

关键覆盖限制：完整市场八特征在BTC/ETH/DOGE首日2022-07-21、SOL/XRP首日10-21；叠加12完整成熟周槽，共同训练首日2022-12-27，**几乎没有主要2022熊市训练**。2024实际训练仅2022-12-27..2023-02-17、02-25..27、05-23..12-18。2023-02-18..24参考标签缺7日，完整反馈槽使02-28..05-22再缺84日；没有压缩缺口或从验证删日。上游`feature_frame`用`complete_kline`掩码close，具体阻断日期/原字段仍待追踪，不能认定原始数据不存在。

由保存系数、原训练均值/总体方差与标签均值重建预测，误差<1e−8、零拟合。2024 CORE5平均200日动量验证最大3.184，训练最大0.956，最大训练标准分10.83；它对CSMOM−HOLD预测均差的代数贡献−452/−405bp，其他相关特征部分抵消。总预测−471/−465bp，真实−66/−73bp。2025偏差仍在，但这个特征没有同样极端外推。**代数分解不是单特征因果归因，不支持事后删列重跑。**

[共同掩码/动作诊断](JOINT_EXPERT_INFORMATION_DIAGNOSIS_20261008.json)、[预测重建/源特征支持](JOINT_EXPERT_INFORMATION_BIAS_20261008.json)。精确只读脚本保存于`docs/archive/JOINT_INFORMATION_DIAGNOSIS_20261008.py`与`JOINT_INFORMATION_BIAS_20261008.py`，默认读取本次外部STATE；无fit、标签重算或账户回放。

采用成熟时钟、共同掩码和薄公共库pipeline；没有采用新交易策略。本模块真实共享钱包PnL/APR、LONG/SHORT净贡献、波动/回撤均**NOT_RUN**，不能由周效用换算。暂停当前固定Ridge，保留SHORT与联合路由能力。reopen需有实际熊市支持的合法成熟面板和新的事前对照，不扫alpha/周期/特征。

下一主任务只追上述两个数据支持问题，零拟合/零钱包：逐币定位2022长周期阻断及2023标签缺口，判断可复用官方日线信号视图与原事件补齐的可能；分钟执行/mark/资金完整要求不变，不插值、补零或读locked。验收实际可恢复熊市训练日与非重叠成熟周数。若可恢复，再注册一次原容量检验；否则保持模型暂停。未被旧BTC组合覆盖的固定50/50绝对趋势＋CORE5相对强弱共享钱包暂列次选，不能平均独立expert效用冒充组合收益。

主阶段3.362秒、12主＋12错位拟合、零新钱包、1worker/1thread；8,000,000,000B RAM硬限制/swap0/GPU0，峰值UNKNOWN（内核无memory.peak）。295,315B是写最终JSON/报告前owned测量。7项相关回归2.757秒。主服务正常退出，当前无后台拟合/回放。Binance价格/Bybit成本代理、两未认证资金解释及既有资金风险边界保持，投资NONE/CASH。
