# Transformer v2 最终研究报告



最终决定：**B. CONTINUE RESEARCH, NOT YET PROMOTED**。

Full locked experiment is NOT_EVALUABLE or has preserved engineering failures; no post-outcome rerun

投资状态继续为 NONE/CASH。本报告为研究证据，不授权实盘。

## 证据边界

开发集是已见历史的五折 walk-forward、六个独立满资金窗口；每个账户初始 10k USDT，收益不能相加冒充连续 APR。封存测试是 2026-03-01 至 2026-08-31 的一次正式连续 184 日实验。

固定候选来自开发集排名：{"family": "CROSS_ASSET_UTILITY", "mapping": "DIRECTIONAL", "seed_rule": "FIXED_THREE_SEED_AVERAGE", "pool_rule": "FIXED_THREE_READOUT_AVERAGE"}

封存状态：NOT_EVALUABLE_INCOMPLETE_LOCKED_CALENDAR。没有按封存 PnL 换候选、挑 seed、改 K、改 gate 或重跑赢家。

全部账户复用原分钟交易内核、费用、逐仓 1x、abs 单币 30% / gross 60% 边界及独立账本核验。价格源 Binance USD-M 与既有费用假设仍是跨场所代理；资金费原始单位未确证，1.0/0.01 两种解释并列保留。

## 十一个问题的明确回答

**1. v2 对旧 Transformer 的改善**

冻结候选开发集对旧冻结 Transformer 的配对中位收益差为 -1.4509 / -3.9976 pct（funding=1.0 / 0.01）；组合映射与旧方向基线不同的比较不能解释为单独的架构增益。

**2. 改善来自哪里**

cross-asset 与 readout 同时变化，attention 的独立贡献无法识别；multitask、patching 的配对差和实际 gross 差见架构表。ensemble 的稳定性 gate=False 所属开发综合 gate；单独稳定性见各 funding scenario。开发暴露预算配对对照=[{"window": "fold1-2024-01-02", "funding_scale": 1.0, "candidate_mean_gross": 0.26551910254800093, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.2654817086184124, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.26551366507915297, "EXPOSURE_MATCHED_BASE_HOLD": 0.265522073075016}, "delta_to_strongest_requested_budget_control_USDT": 166.5474073019186, "equal_realized_gross_certified": false}, {"window": "fold2-2024-07-02", "funding_scale": 1.0, "candidate_mean_gross": 0.3569971861290263, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3565334538179571, "EXPOSURE_MATCHED_BASE_HOLD": 0.3572396740990915, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.35711965170253124}, "delta_to_strongest_requested_budget_control_USDT": -260.6348011696113, "equal_realized_gross_certified": false}, {"window": "fold2-2024-08-13", "funding_scale": 1.0, "candidate_mean_gross": 0.30685941429922786, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.30679641907060945, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3063169166247719, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.30684544157256655}, "delta_to_strongest_requested_budget_control_USDT": -206.8429031916421, "equal_realized_gross_certified": false}, {"window": "fold3-2025-01-02", "funding_scale": 1.0, "candidate_mean_gross": 0.31041657325056066, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.31028646129099596, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3103240510948248, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.310366837741995}, "delta_to_strongest_requested_budget_control_USDT": -60.42030099010856, "equal_realized_gross_certified": false}, {"window": "fold4-2025-07-02", "funding_scale": 1.0, "candidate_mean_gross": 0.2797650506662195, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.28466312314099934, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.282516484004783, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.2832440509142974}, "delta_to_strongest_requested_budget_control_USDT": 778.3487620825023, "equal_realized_gross_certified": false}, {"window": "fold5-2026-01-02", "funding_scale": 1.0, "candidate_mean_gross": 0.3796108837517771, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.3747359248245098, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3746069339034297, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.3746069339034297}, "delta_to_strongest_requested_budget_control_USDT": -1860.6276227002686, "equal_realized_gross_certified": false}, {"window": "fold1-2024-01-02", "funding_scale": 0.01, "candidate_mean_gross": 0.27022340837407544, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.2702192668919306, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.2702069553574344, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.27016625492332375}, "delta_to_strongest_requested_budget_control_USDT": 173.60379794022174, "equal_realized_gross_certified": false}, {"window": "fold2-2024-07-02", "funding_scale": 0.01, "candidate_mean_gross": 0.3857533162781909, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.38606323324172087, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3846793811825753, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.38588706362485653}, "delta_to_strongest_requested_budget_control_USDT": -107.67037688942725, "equal_realized_gross_certified": false}, {"window": "fold2-2024-08-13", "funding_scale": 0.01, "candidate_mean_gross": 0.36534671815495484, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.3652861760566397, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3648045053414941, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.3652888905499177}, "delta_to_strongest_requested_budget_control_USDT": -82.61177716632119, "equal_realized_gross_certified": false}, {"window": "fold3-2025-01-02", "funding_scale": 0.01, "candidate_mean_gross": 0.37750971488548285, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.3774617243029972, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.37763660255728015, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.3776533161049791}, "delta_to_strongest_requested_budget_control_USDT": -78.69000537969589, "equal_realized_gross_certified": false}, {"window": "fold4-2025-07-02", "funding_scale": 0.01, "candidate_mean_gross": 0.21916339730508502, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.2236490941127132, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.22281762366378027, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.22210623827289083}, "delta_to_strongest_requested_budget_control_USDT": 760.8791022397189, "equal_realized_gross_certified": false}, {"window": "fold5-2026-01-02", "funding_scale": 0.01, "candidate_mean_gross": 0.3693043002023893, "baseline_mean_gross": {"EXPOSURE_MATCHED_BASE_HOLD": 0.3621239384664724, "EXPOSURE_MATCHED_BASE_SMA200_SIGNED": 0.3618592373504012, "EXPOSURE_MATCHED_BASE_STATIC_DIRECTION3": 0.3618592373504012}, "delta_to_strongest_requested_budget_control_USDT": -1840.367036266594, "equal_realized_gross_certified": false}]；封存 exposure 控制=[]。未证明实际 exposure 相等时，不宣称排除了降低 exposure 的解释。

**3. directional alpha 是否存在**

否，本轮未取得同时满足开发跨阶段与封存两单位成本后正收益的证据。开发中位收益=-1.7914 / -0.3479%；封存 NET=NOT_EVALUABLE / NOT_EVALUABLE USDT。它是固定对照，不能事后替换预注册候选。

**4. cross-sectional alpha 是否存在**

否，本轮未取得同时满足开发跨阶段与封存两单位成本后正收益的证据。开发中位收益=NOT_EVALUABLE / NOT_EVALUABLE%；封存 NET=NOT_EVALUABLE / NOT_EVALUABLE USDT。它是固定对照，不能事后替换预注册候选。

**5. oracle ceiling 多大**

封存三种未来知情诊断的最高 NET 为 NOT_EVALUABLE / NOT_EVALUABLE%；完整日历的严格最优经济 ceiling 未被识别。未来 horizon 不足时为显式现金，60日专家 proxy 也不等价于分钟钱包最优解。

**6. 捕获多少 oracle gap**

封存相对全日历 SMA 的诊断 gap 比率：NOT_EVALUABLE。支持范围不同，不能把此比率称为严格 ceiling 捕获率；非正分母不计算。

**7. 赚钱和亏钱的市场阶段**

1.0 盈利窗口=['fold1-2024-01-02', 'fold2-2024-08-13', 'fold4-2025-07-02']；亏损窗口=['fold2-2024-07-02', 'fold3-2025-01-02', 'fold5-2026-01-02']；0.01 盈利窗口=['fold1-2024-01-02', 'fold2-2024-08-13', 'fold4-2025-07-02']；亏损窗口=['fold2-2024-07-02', 'fold3-2025-01-02', 'fold5-2026-01-02']。封存月份分解见下表，不把独立窗口相加。

**8. long / short 贡献**

封存冻结候选：；完整日历失败时这些是局部诊断，不是完整期贡献。

**9. cost 占 gross alpha 多少**

冻结候选封存交易成本/正毛价格、包含净资金费负担/正毛价格：。毛价格非正时比率不可评价。

**10. locked 2026-03~08 表现**

NOT_EVALUABLE；无完整封存账户。

**11. 最终决定**

B. CONTINUE RESEARCH, NOT YET PROMOTED；Full locked experiment is NOT_EVALUABLE or has preserved engineering failures; no post-outcome rerun

## 1. v2 比旧 Transformer 改善多少

|模型/组合|funding|开发集窗口收益中位数 %|对旧冻结 Transformer 配对中位差 pct|胜 SMA 窗口|最差窗口 %|

|---|---:|---:|---:|---:|---:|

|TRANSFORMER_SHARED/DIRECTIONAL|1.0|-5.4753|0.1930|4/6|-8.8111|

|TRANSFORMER_SHARED/DIRECTIONAL|0.01|-4.8520|-1.6852|4/6|-9.7020|

|CROSS_ASSET_UTILITY/DIRECTIONAL|1.0|-1.7914|-1.4509|3/6|-9.1100|

|CROSS_ASSET_UTILITY/DIRECTIONAL|0.01|-0.3479|-3.9976|4/6|-9.4369|

|CROSS_ASSET_MULTITASK/DIRECTIONAL|1.0|-3.1555|-4.2754|4/6|-10.1331|

|CROSS_ASSET_MULTITASK/DIRECTIONAL|0.01|-0.3229|-5.8836|4/6|-12.1096|

|PATCH_CROSS_ASSET_MULTITASK/DIRECTIONAL|1.0|-2.7210|-3.7767|4/6|-14.8012|

|PATCH_CROSS_ASSET_MULTITASK/DIRECTIONAL|0.01|-4.9956|-6.5955|4/6|-12.7282|

## 2. 改善来源与 exposure

下表是同窗口配对差。cross-asset utility 与本轮重训旧架构的差同时含 cross-asset attention 和 readout 变化，不能单独归因给 attention。multitask 与 patch 比较使用固定 seed、协议和组合。

|变化|组合|funding|配对中位收益差 pct|配对中位实际 gross 差|

|---|---|---:|---:|---:|

|cross_asset_plus_readouts|DIRECTIONAL|1.0|-0.1750|-0.0230|

|cross_asset_plus_readouts|NEUTRAL|1.0|-5.8128|-0.0011|

|cross_asset_plus_readouts|COMBINED|1.0|-0.2392|0.0235|

|cross_asset_plus_readouts|DIRECTIONAL|0.01|-0.2284|-0.0100|

|cross_asset_plus_readouts|NEUTRAL|0.01|-8.0859|-0.0008|

|cross_asset_plus_readouts|COMBINED|0.01|-1.3190|0.0102|

|multitask|DIRECTIONAL|1.0|-1.3820|0.0423|

|multitask|NEUTRAL|1.0|5.0468|-0.0016|

|multitask|COMBINED|1.0|0.8562|-0.0182|

|multitask|DIRECTIONAL|0.01|-0.1704|0.0229|

|multitask|NEUTRAL|0.01|2.3028|-0.0005|

|multitask|COMBINED|0.01|0.1623|0.0199|

|eight_day_patching|DIRECTIONAL|1.0|0.4987|0.0655|

|eight_day_patching|NEUTRAL|1.0|-3.1516|-0.0011|

|eight_day_patching|COMBINED|1.0|-1.6069|-0.0021|

|eight_day_patching|DIRECTIONAL|0.01|-0.3016|0.0268|

|eight_day_patching|NEUTRAL|0.01|-1.5231|-0.0035|

|eight_day_patching|COMBINED|0.01|-1.3050|-0.0130|

三 seed 全部列在 DEV_RESULTS / LOCKED_SUMMARY；ensemble 是预测的固定平均。开发集每个模型的 seed dispersion、ensemble 标准差和最差窗口稳定性检查在 DEV_RESULTS。CLS / attention / last 的开发集独立 readout 账户保留，未选优。

封存期 equal-requested-gross 对照：[]

同一 requested gross 不保证同一 realized gross，成交容量和风险减仓会造成差别。未证明实际 exposure 相等时，不能宣称排除了 exposure 解释，也不能通过对应 gate。

## 3–4. 方向与横截面 alpha

下表分别列方向、中性、组合的封存 ensemble；中性组合固定 top2 / bottom2，每腿 0.15，净 dollar target=0，不宣称 beta 中性。毛价格 PnL、费用、执行、资金费及多空贡献同时呈现。

|模型/组合|funding|NET USDT|毛价格 USDT|fee|spread|slippage|funding|long NET|short NET|MDD|Sharpe|实际 gross|

|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

跨阶段 relative 证据：[{"funding_scale": 1.0, "stable_IC": false, "stable_relative_utility": false, "development_median_IC": 0.17575757575757575, "locked_IC": null, "development_median_utility_rank": 0.129394341361843, "locked_utility_rank": null}, {"funding_scale": 0.01, "stable_IC": false, "stable_relative_utility": false, "development_median_IC": 0.23636363636363633, "locked_IC": null, "development_median_utility_rank": 0.2026973808721873, "locked_utility_rank": null}]

稳定诊断使用五个开发 fold 至少四个正 IC（或正 utility rank）及封存期同向，两个 funding interpretations 均保留；它不是新增模型选择规则。所有预测指标及有效 IC 日数列在 FINAL_DECISION.json。

## 5–6. Oracle ceiling 与 gap 捕获

三个 oracle 永远 NONCAUSAL / NONDEPLOYABLE，使用同本金、成本、资金费、风险和成交。专家 oracle 的 60 日 utility 是日频 quantity proxy；方向和排序 oracle 为未来 30 日价格信息。

开发期 oracle 使用独立 DEV_ORACLE_RESULTS 的逐 horizon 支持修正；原36个联合掩码诊断和开发候选报告均保留，不改变候选或 gate。各 oracle 的有效资产日与有效日数在补充 JSON 和 LOCKED_ORACLE_SUPPORT 中明确列出。

终端未来 horizon 不足和中间缺口明确现金，因此以下是有限支持的策略空间诊断，无法证明严格完整日历最优 ceiling。gap 分母只有正值才报告比率；基线和模型为全日历账户，支持差异使比率只能作诊断，不是可推广捕获率。

|窗口|funding|oracle|NET %|相对 SMA gap USDT|诊断捕获率|

|---|---:|---|---:|---:|---:|

|fold2-2024-07-02|1.0|DIRECTIONAL_ORACLE|14.4944|2824.1412|0.2740|

|fold2-2024-07-02|1.0|CROSS_SECTIONAL_RANK_ORACLE|13.6890|2743.5962|0.2820|

|fold1-2024-01-02|1.0|EXPERT_ORACLE|32.8166|2164.3227|-0.0260|

|fold2-2024-07-02|1.0|EXPERT_ORACLE|10.8752|2462.2181|0.3142|

|fold1-2024-01-02|1.0|DIRECTIONAL_ORACLE|111.4006|10022.7259|-0.0056|

|fold2-2024-08-13|1.0|EXPERT_ORACLE|73.5556|5155.5223|-0.0102|

|fold1-2024-01-02|1.0|CROSS_SECTIONAL_RANK_ORACLE|34.3620|2318.8685|-0.0243|

|fold2-2024-08-13|1.0|DIRECTIONAL_ORACLE|84.4590|6245.8613|-0.0084|

|fold2-2024-08-13|1.0|CROSS_SECTIONAL_RANK_ORACLE|58.2071|3620.6734|-0.0145|

|fold5-2026-01-02|1.0|EXPERT_ORACLE|0.0000|-1668.9101|NOT_EVALUABLE|

|fold3-2025-01-02|1.0|EXPERT_ORACLE|30.5608|5213.3702|0.2588|

|fold3-2025-01-02|1.0|DIRECTIONAL_ORACLE|87.4234|10899.6303|0.1238|

|fold3-2025-01-02|1.0|CROSS_SECTIONAL_RANK_ORACLE|72.5134|9408.6320|0.1434|

|fold4-2025-07-02|1.0|EXPERT_ORACLE|49.2468|6005.4583|0.2204|

|fold2-2024-07-02|0.01|DIRECTIONAL_ORACLE|14.2362|2789.4237|0.3218|

|fold1-2024-01-02|0.01|EXPERT_ORACLE|38.8088|2290.8646|-0.1453|

|fold1-2024-01-02|0.01|DIRECTIONAL_ORACLE|111.7989|9589.8838|-0.0347|

|fold2-2024-07-02|0.01|EXPERT_ORACLE|10.4142|2407.2243|0.3729|

|fold1-2024-01-02|0.01|CROSS_SECTIONAL_RANK_ORACLE|34.5028|1860.2710|-0.1789|

|fold2-2024-07-02|0.01|CROSS_SECTIONAL_RANK_ORACLE|13.6731|2733.1192|0.3285|

|fold3-2025-01-02|0.01|DIRECTIONAL_ORACLE|86.9482|10849.9249|0.1117|

|fold2-2024-08-13|0.01|DIRECTIONAL_ORACLE|85.4286|6182.4827|0.1416|

|fold3-2025-01-02|0.01|EXPERT_ORACLE|29.9236|5147.4689|0.2353|

|fold3-2025-01-02|0.01|CROSS_SECTIONAL_RANK_ORACLE|72.8919|9444.2992|0.1283|

|fold2-2024-08-13|0.01|EXPERT_ORACLE|76.9989|5339.5117|0.1640|

|fold4-2025-07-02|0.01|EXPERT_ORACLE|46.7018|5748.0097|0.2568|

|fold5-2026-01-02|0.01|EXPERT_ORACLE|0.0000|-1669.4218|NOT_EVALUABLE|

|fold2-2024-08-13|0.01|CROSS_SECTIONAL_RANK_ORACLE|57.9358|3433.2018|0.2550|

|fold5-2026-01-02|1.0|DIRECTIONAL_ORACLE|4.6498|-1203.9286|NOT_EVALUABLE|

|fold5-2026-01-02|1.0|CROSS_SECTIONAL_RANK_ORACLE|9.6373|-705.1757|NOT_EVALUABLE|

|fold5-2026-01-02|0.01|DIRECTIONAL_ORACLE|4.4985|-1219.5713|NOT_EVALUABLE|

|fold5-2026-01-02|0.01|CROSS_SECTIONAL_RANK_ORACLE|9.6190|-707.5179|NOT_EVALUABLE|

|fold4-2025-07-02|0.01|DIRECTIONAL_ORACLE|98.9326|10971.0805|0.1346|

|fold4-2025-07-02|1.0|DIRECTIONAL_ORACLE|99.5086|11031.6432|0.1200|

|fold4-2025-07-02|0.01|CROSS_SECTIONAL_RANK_ORACLE|54.3883|6516.6567|0.2265|

|fold4-2025-07-02|1.0|CROSS_SECTIONAL_RANK_ORACLE|54.0248|6483.2665|0.2041|

## 7. 哪些市场阶段赚钱或亏钱

冻结候选开发阶段：

|独立窗口|funding|NET %|long NET|short NET|实际 signed exposure|

|---|---:|---:|---:|---:|---:|

|fold1-2024-01-02|1.0|10.6099|1067.0638|-6.0780|0.2653|

|fold2-2024-07-02|1.0|-6.0097|-505.6146|-95.3548|0.3436|

|fold2-2024-08-13|1.0|21.4751|2150.6679|-3.1588|0.3041|

|fold3-2025-01-02|1.0|-8.0816|-807.3271|-0.8342|0.3089|

|fold4-2025-07-02|1.0|2.4269|-307.8130|550.5035|-0.0509|

|fold5-2026-01-02|1.0|-9.1100|-943.2623|32.2652|0.3744|

|fold1-2024-01-02|0.01|12.5724|1259.3377|-2.1006|0.2702|

|fold2-2024-07-02|0.01|-4.6807|-467.6152|-0.4535|0.3836|

|fold2-2024-08-13|0.01|32.3588|3241.7212|-5.8456|0.3647|

|fold3-2025-01-02|0.01|-9.4369|-943.6880|0.0000|0.3775|

|fold4-2025-07-02|0.01|3.9849|-145.3487|543.8384|-0.0695|

|fold5-2026-01-02|0.01|-9.1885|-939.2927|20.4405|0.3675|

封存期各月是同一连续账户的可核对分解，不是每月重置：

|月份|funding|NET USDT|毛价格|fee|执行|funding|

|---|---:|---:|---:|---:|---:|---:|

## 8–9. 多空贡献和成本

多空贡献由原始成交、持仓和资金费逐笔归属，long NET + short NET 与账户 NET 的误差小于 1e-6 USDT。资金费为 signed cash flow：正数为收入，负数为支出；NET=毛价格−fee−spread−slippage+funding。交易成本比率与包含净资金费的负担比率分别保留；毛价格非正时比率为 NOT_EVALUABLE，不能拿负分母制造“低成本”。

|冻结候选 funding|NET %|毛价格 USDT|交易成本/正毛价格|含净资金费负担/正毛价格|turnover USDT|long NET|short NET|

|---:|---:|---:|---:|---:|---:|---:|---:|

## 10. 封存 2026-03~08 与 causal 对照

|策略|funding|NET %|MDD|实际 gross|完整日历且付费清仓|

|---|---:|---:|---:|---:|---|

## 11. 最终决定与 gate

{
  "choice": "B",
  "decision": "CONTINUE RESEARCH, NOT YET PROMOTED",
  "promotion": false,
  "reason": "Full locked experiment is NOT_EVALUABLE or has preserved engineering failures; no post-outcome rerun",
  "gates": {},
  "relative_evidence": [
    {
      "funding_scale": 1.0,
      "stable_IC": false,
      "stable_relative_utility": false,
      "development_median_IC": 0.17575757575757575,
      "locked_IC": null,
      "development_median_utility_rank": 0.129394341361843,
      "locked_utility_rank": null
    },
    {
      "funding_scale": 0.01,
      "stable_IC": false,
      "stable_relative_utility": false,
      "development_median_IC": 0.23636363636363633,
      "locked_IC": null,
      "development_median_utility_rank": 0.2026973808721873,
      "locked_utility_rank": null
    }
  ]
}

旧冻结 Transformer / XGB 是最后开发 fold 的权重与 scaler，未伪装成最终全量重训；本轮新旧架构均按相同 past-only median-epoch 规则重训。即使其他封存组合较好，也不会事后替换开发候选或晋级。

## 复现与完整工件

Git 分支 research/transformer-v2 保留 fit 前协议、源代码、哈希和精简报告。大型行情、模型、检查点和原始账本保存在独立 external STATE。协议 SHA：8f7cdc763cd068b3c0ff1a4030fa0edc8d65838dd276c047427848f08378f4c7

TRANSFORMER_V2_FINAL_DECISION.json 保留全部 gate、配对架构诊断、预测指标、oracle gap 和账户表；LOCKED_RESULTS 原始分钟账户 summary / 独立账本审计引用不可变。
