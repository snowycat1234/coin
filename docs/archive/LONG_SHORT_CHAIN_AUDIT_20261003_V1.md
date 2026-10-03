# LONG_SHORT 链路独立静态审计

执行范围：HEAD `4bf2bc1c521835c22598482900329c96a0564d4f` 及当前工作树的小型源码。没有运行 Python、读取价格/账本数组、修复 D039、改变冻结 Spot 引擎或执行交易。结论只说明已接通的产品与信号语义，不能解释历史亏损的成因。

## 已有链路

| 环节 | 实际实现与边界 |
|---|---|
| 上游公开 SMA | `smacrossover_original.py` 有 `should_long: fast>slow`、`should_short: fast<slow`、`go_long/go_short`，`update_position` 可关闭两种方向的仓位。谓词不是必须发生当天 crossing。 |
| 本地 SMA 信号 | `public_sma_daily.py` 明确 `long_only=True`；上下文固定 `is_short=False`，只接长仓进入/退出。它复用原类但不调用 `go_short` 或整余额 sizing，不是完整 Jesse 双向策略运行。 |
| 公开 Donchian | 固定上游 `should_short()` 本身返回 `False`、`go_short()` 为 `pass`。本地 1h/2h/daily 的 long-only 范围与该上游方向一致；添加对称空头需要明确登记新的策略语义。 |
| targets | daily/小时循环只产生 `0/+0.3`；`benchmark_targets._plan` 要求 `weights>=0`、逐币/总权重上限。warmup 不带仓，终端 `0` 只是退出意图。 |
| risk | `run_backtest` 将 raw target `clip(0,max_weight)`；总量用 `weights.sum()` 与正库存价值，随后按过去协方差缩放。该 gross/cash 风险合同适用于长现货，不能直接用于正负仓抵消后的组合。 |
| fill | 共同 runner 把信号送入 `execute(...plan.targets...)`；原一分钟延迟/历史容量约束保留。Spot sell 数量不能超过现有 base；buy 受可用 quote cash 限制，成交后拒绝负现金/负现货持仓。 |
| wallet/NAV | Bybit Spot adapter 只派生收到资产费用语义：买入扣 base fee、卖出扣 quote fee，保持原 Spot 单向库存限制。NAV 为 quote cash 加实际净 base 的标记价值，没有空头保证金、借币或永续未实现损益。 |
| reports | `account_inventory/write_ledger` 仍描述 long Spot 实际库存、同净收到数量 shadow gross、费用与执行成本、未平终端库存。可验收该产品下的代理账本，不能成为完整双向公开策略或永续交易验收。 |

## 已有 carry 空腿真正范围

`conditional_carry_account.py` 是独立、固定的 long-Spot/short-mark 代理账户：short 数量匹配收到的净 base；不把卖空名义本金计入现金；空腿未实现损益为 `short_q*(entry_fill-mark)`；NAV 为 free cash + Spot 价值 + isolated balance/未实现损益。实际开平收取冻结假设的永续费用，条件 funding 使用严格事件归属；部分减仓版本另有已验收的 realized/debit 处理。

该账户是固定 hedge/risk-exit 路径，未接 SMA/Donchian 双向信号、一般多空反转或共享方向目标。其历史 funding 单位与真实结算归属未认证，自定义 isolated stop 不是交易所 MMR/清算/ADL，不能称原生 Bybit carry 或完整永续引擎。`execution.py` 的双资产 `commissionAsset` 记账复用也不等于已接通永续保证金产品。

## 必要正确性边界

1. **只让 target 变负再调用旧 Spot 引擎不可接受。** 工厂会拒绝负权重；直接绕过工厂，`backtest.py:421` 又会静默 clip 为0。去掉 clip 仍不足：gross 要改为绝对暴露，卖空不能领取现货销售本金，signed position、保证金、已实现/未实现损益、费用和 funding 必须贯通到报告。
2. SMA 双向连接应明确 fresh-flat、equal-hold、反向信号的先平后开/延迟/容量及两段费用；不得借修连接改变原谓词或成本。Donchian 原源没有空头信号，不能宣称对称空头是原策略复刻。
3. 新永续账户需独立新合同/入口/证据。保留原 Spot 字节与历史验收；真实费用/MMR 来源、funding 单位/归属、价格与执行代理限制逐项明确，未知不猜测。

当前没有接通的通用 `public signed signal -> perpetual wallet -> NAV -> reports` 链路。本发现支持必要的新研究入口，**不支持“亏损因不能 short”或“连接后必盈利”**。已见窗口仍为 SCREENING；`NO_QUALIFIED_CANDIDATE`。

## 读取字节

| 文件 | SHA256 |
|---|---|
| `src/quant/backtest.py` | `ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a` |
| `scripts/investment/compare_simple_strategies.py` | `3dfa0e3176791980de51e5bc990b1998f93eb24c02bdc1261a074eab92fb52f1` |
| `scripts/investment/bybit_spot_adapter.py` | `8c8852bf70813ada5720c210f50c9038a5ecaadee1b4f38b77a71aa9e8b038ca` |
| `scripts/investment/public_sma_daily.py` | `a675428941dbae1fe07dbab5f6edd33597475bda5df4c2b1bf9f0a0c74048be3` |
| `scripts/investment/public_donchian_daily.py` | `82796e9dac68089a24a6d4bd61c561672043e446c806cbe87a6737a459d35c4a` |
| `scripts/research_v8/public_donchian_adapter.py` | `169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2` |
| `scripts/investment/conditional_carry_account.py` | `d29cf6ba9ec48c27f6b21eaab2167ff9ca7c39be2d762a9178f5e7dc2c6c001e` |
| 上游 SMA | `453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae` |
| 上游 Donchian | `fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe` |
