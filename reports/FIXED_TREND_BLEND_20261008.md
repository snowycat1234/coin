# 固定绝对/相对趋势：同一钱包的实际互补检验

决定 NO_ALL_STAGE_BLEND_QUALIFICATION；投资NONE/CASH。两个已见窗口/两资金情景；8新钱包、4控制复用、0fit。

|窗口|资金解释|策略|净PnL|LONG净|SHORT净|年化vol|分钟MDD|手续费/执行/资金|换手|
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
|fold1-2024-01-02|0.01|FIXED_HALF_SMA_CSMOM|156.68|598.56|-441.88|7.41%|6.12%|40.62/59.09/-0.63|7.39|
|fold1-2024-01-02|0.01|PUBLIC_CSMOM21_WEEKLY|-604.93|448.02|-1052.94|9.56%|10.17%|66.09/96.13/0.18|12.02|
|fold1-2024-01-02|0.01|SMA200_10PCT|942.46|1079.38|-136.91|10.81%|5.64%|24.04/34.97/-1.50|4.37|
|fold1-2024-01-02|1|FIXED_HALF_SMA_CSMOM|95.90|457.25|-361.34|7.40%|6.46%|40.47/58.87/-62.53|7.36|
|fold1-2024-01-02|1|PUBLIC_CSMOM21_WEEKLY|-587.38|276.86|-864.24|9.56%|10.12%|66.13/96.19/17.69|12.02|
|fold1-2024-01-02|1|SMA200_10PCT|791.42|899.37|-107.95|10.75%|5.76%|23.81/34.64/-148.48|4.33|
|fold3-2025-01-02|0.01|FIXED_HALF_SMA_CSMOM|160.66|-39.36|200.01|8.38%|6.30%|45.93/66.81/0.04|8.35|
|fold3-2025-01-02|0.01|PUBLIC_CSMOM21_WEEKLY|838.90|523.69|315.21|9.70%|4.16%|73.97/107.60/0.04|13.45|
|fold3-2025-01-02|0.01|SMA200_10PCT|-517.70|-589.82|72.12|10.45%|10.32%|33.10/48.15/0.04|6.02|
|fold3-2025-01-02|1|FIXED_HALF_SMA_CSMOM|164.49|-54.06|218.55|8.36%|6.27%|45.93/66.81/3.98|8.35|
|fold3-2025-01-02|1|PUBLIC_CSMOM21_WEEKLY|842.85|493.53|349.32|9.68%|4.11%|73.99/107.62/3.88|13.45|
|fold3-2025-01-02|1|SMA200_10PCT|-513.94|-604.07|90.13|10.44%|10.28%|33.09/48.13/3.50|6.02|

固定半权不再放大。相反意图先净成同一one-way目标，完整10k共享资本，分腿贡献只来自实际净持仓；不把平均独立钱包收益当mix。
较低波动/gross本身会降低回撤，不作为新SHORT alpha证据。实际gross漂移/延迟风险按旧引擎报告，不声称瞬时caps已认证。
Two previously-seen half-year development windows, not complete2022bear or freshOOS; independent fullcapital wallets never stitched.
BinanceUSD-M market+Bybitcost crossvenue proxy; funding units not certified, both1/.01 interpretations retained.
Reviewed frozen intent panel is causal but label/proxy prediction quality irrelevant; no future outcome used to select weights.
Equal halfweight lowers actualgross/vol and may reduceDD mechanically; this is not regime prediction or independent shortalpha.
Originalgross drift/risklatency remains; targetswithinlimits do not certify instantaneous livecaps.
Core5 is retrospective limited survivor panel; zero newpools/fits/parametersearch, no stableAPR/nativeBybit claim.

复现：python -B scripts/research/fixed_trend_blend.py --protocol protocols/FIXED_TREND_BLEND_20261008.json --state /home/ubuntu/coin/execution-state/fixed-trend-blend-NEW；源码需事前commit，8GB/swap0/GPU0受限scope。

## 采用与下一步

保留固定组合为透明静态研究对照，不晋级全天候投资候选，也不改变冻结失败门槛。所有四组合账户净正，但2024同风险设置SMA净+791至+942、MDD5.64–5.76%，比mix+96至+157、MDD6.12–6.46%更好；2025 CSMOM净+839至+843、MDD4.11–4.16%，比mix+161至+164、MDD6.27–6.30%更好。两阶段分别有强expert，但现在仍不能事前可靠选择。

组合改善的是跨两个独立窗口的最差结果，不是每个窗口的最强结果。不得把两账户拼成一年。2024主要LONG净+457至+599、SHORT净−442至−361；2025 LONG净−54至−39、SHORT净+200至+219。SHORT可以赚钱，但尚无牛市不多亏的稳定证据。

实际gross平均26.50%/27.23%、峰值47.18%/52.06%；实际vol7.40–8.38%。资本完整10k，不用保证金分母放大收益。组合实测gross在本四账户低于60%，不认证引擎所有输入下的瞬时caps。交易费用+执行约99–113，毛价格PnL约257–273，成本仍消耗较大比例；资金单位条件解释保留。

独立12账户算术复核PASS_WITH_LIMITATIONS，现金/方向/逐月桥误差≤1.14e−13；8新账户的独立分钟NAV最大误差1.82e−12，全部收费终平，无清算。实际mix净收益减去半权独立single收益算术，2024为−6.11/−12.09、2025约+0.04/+0.06；实际净单成本相对半权single成本算术少约11–19。这只是结果对照，不是用平均独立账户代替回测，也没有额外selector收益证据。

581.840秒，新增完整state实测54,215,006B；8GB/swap0/GPU0、2worker/每进程1线程。观察到的memory.current最高1,956,753,408B，不是真实peak计数（UNKNOWN）。5目标映射/净仓/caps/未来扰动反例通过；第一次本机测试收集因无torch失败，随后把未使用训练依赖移入main后通过，错误及修正保留，没有安装包/重跑钱包。

下一项只核其他现有合法开发窗是否真实完整，再延展同一冻结专家/组合；先核分钟/mark/funding与当时币池，不删缺口日期，不把已见数据称unseen。当前PANEL截至2025-07-02，不能ffill为后续仓位。若数据可用再注册有限对照；不调权重、不训练更复杂selector。投资资格NONE/CASH，稳定净APR未知，服务器任务已完成。
