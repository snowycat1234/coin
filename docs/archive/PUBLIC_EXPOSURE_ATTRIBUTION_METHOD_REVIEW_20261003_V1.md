# D039 分币归因方法独立审查（执行前）

范围：三个已见窗口各自保存的 SMA、VM、2h，固定9账户；只新增归因数学，不重放策略、账户、来源QA或价格。尚未读取数组，没有实际数值验收结论。

## 资金恒等式

每币初始持仓为0。令已保存成交净持仓变化为 Δq（买入已扣base fee，卖出为负的实际卖量）、成交mid为 m、终端该币标记资产价值为 V。

- `gross_coin = sum(-Δq * m) + V`
- `net_coin = gross_coin - sum(fee_USDT_mid) - sum(execution_cost)`
- 同时用 `sum(cash_delta) + V` 独立核对 net；两币加总分别核对保存的 gross/net、费用和执行成本摘要。

逐币不各分配一个10000初始现金，否则账户资本重复。买base fee以成交mid估值，卖quote fee已为USDT；spread/slip使用gross成交量的原execution_cost。以当前固定halfspread4/slip4拆分各一半，必须先核保存config。不能把gross buy quantity当Δq，不能从gross再次扣base资产数量，不能免费视为fee-free重新优化账户。此gross是“与实际净收到持仓相同数量的shadow”归因。

终端V纳入MTM，不假设已卖出或免成本清仓；逐币净PnL属于同一共享现金账户的加总贡献，不是两个独立资本收益率。

## 暴露和持续性

使用已验收minute_nav_inventory的逐币marked_notional和NAV，完整评分minute close从start+1min至exclusive end；不读warmup库存，不丢零暴露分钟。NAV必须有限且正值。

- material mask严格 `marked_notional >= 10 USDT`（冻结原min_notional）；positive aux严格 `marked_notional > 0`，两者分别报告。
- 全期时间加权平均weight为完整等距分钟的 `mean(marked_notional/NAV)`；max和`weight > .3`分钟数也是完整窗口。若另报material条件均值，必须标清分母，不能替换全期均值。
- active streak按material mask在完整连续minute grid上的连续True段，不拼接缺口/月份。报告段首末close、observed_minutes；`minute_occupancy_seconds=observed_minutes*60`仅离散分钟占用，`snapshot_span_seconds=(last_close-first_close)/1e6`另列，禁止混为精确成交持仓时长。终端仍active的段标记右截断。
- positive aux可含长期dust。低于10的残余不能使“策略持有全期”成为主结论。material段也可能仅由价格穿越10阈值形成，不等同于成交round-trip。

## 最薄独立核验及门槛

复用原small-file/hash/actual-task守卫；9账户每个只读trade选定字段和inventory选定字段，不调用原financial循环或simulate。小成交表用Decimal对原float精确转换后的分币现金/费用/cost加总；暴露用Polars表达式，与producer的NumPy计算形成独立路径。金额绝对误差建议沿用已接受1e-7 USDT、weight绝对误差1e-12；计数、窗口、streak端点必须exact。

执行前需冻结9个唯一period/strategy/spread8选择、已接受report/audit SHA、trade/inventory SHA、完整日历边界、公式/分母/threshold/streak定义及预算；不能预设fills、持有期或归因赢家。数学失败保留原报告与真实退出。

没有从当前冻结公式/账本字段发现数学blocker。若producer将gross quantity当净变化、重复分配初始资本、遗漏终端库存、把positive dust作为material，或不明确streak时间口径，则必须拒绝。

结论仅历史代理保存账本的归因诊断；不做收益加权、事后风险归一化、共享资本组合回放或APR/alpha资格认证。`NO_QUALIFIED_CANDIDATE`。
