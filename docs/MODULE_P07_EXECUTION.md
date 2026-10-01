# P07：可恢复订单执行与账户对账

## 验收定位

本模块完成可离线验收的订单执行工程。它不把合成成交、签名 mock 或历史重放作为真实订单、72 小时运行、180 天前向收益的证据。真实网络默认禁用，当前没有真实 Testnet 或主网订单，没有读取用户密钥。

交付文件：`src/quant/execution.py`、`tests/test_execution.py`。REST 协议由 `src/quant/testnet.py` 独立实现；跨模块签名事故演练由 `quant.acceptance` 和 `tests/test_execution_integration.py` 验收。

## 1. 持久状态与恢复

| 状态 | 含义 | 是否保留未成交预占 | 后续动作 |
|---|---|---|---|
| PREPARED | 风险检查通过，意图已经落库，尚未发送 | 是 | 发单前再次检查；可本地取消 |
| SUBMITTING | 发送开始前已提交持久记录 | 是 | 只有明确响应能确认；进程恢复时转 UNKNOWN |
| NEW / PARTIALLY_FILLED | 已确认订单及累计成交 | 按剩余数量保留 | 查询、撤单、补齐详细成交 |
| CANCEL_PENDING | 撤单请求开始前已提交记录 | 是 | 等待确认；不能假定已撤销 |
| UNKNOWN | 请求超时、响应缺失、查询暂不可见、重启待恢复 | 是 | 查询原 client ID，禁止再次提交该订单 |
| FILLED / CANCELED / REJECTED / EXPIRED | 已确认终态 | 否 | 详细成交或费用仍缺失时全局禁止新单 |
| RESET_INVALIDATED | 经审查确认 Testnet reset 后的旧世代活跃订单 | 否 | 永久保留旧证据，不能计入新账户 |

订单 ID 使用 `cq_` 加 32 位 UUID，共 35 个 ASCII 字符；数据库唯一约束确保本地永久不复用。策略 `intent_key` 也永久唯一：重复决策返回同一订单；经济字段变化则拒绝。即使旧单已成交、已取消或发生 reset，也不会换 ID 再提交同一意图。币安允许某些已成交 ID 再次使用，本工程采取更严格的永久不复用规则。[币安订单 REST 规范](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md)

发送、撤单的持久状态都先于网络 await 提交。任何写请求丢失响应都转 UNKNOWN；明确新单拒绝才转 REJECTED，`-2010` 可能包含重复 ID，因此保守转 UNKNOWN。撤单 `-2011` 仅代表该撤单未成功，原订单继续待查。`-2013` 查不到也维持 UNKNOWN，不释放资源、不再次下单。

HTTP 5xx 或 `-1007` 不证明撮合失败；查询可能因异步 Memory / Database 可见性而滞后。这是持续查询和冻结的依据。[币安 Testnet REST 规范](https://developers.binance.com/en/docs/products/spot/testnet/rest-api)

进程重启将所有已发送活跃单转 UNKNOWN，并要求查询及账户对账。PREPARED 未发单可保留，但重启后的账户对账未通过前不发单。`recover()` 只查询、补成交、对账，绝不自动重新提交。

## 2. 发单前风险检查

`prepare()` 和 `submit()` 各执行一次检查，且把当时风险输入、报价 received 时间和 update ID、过滤器 SHA256 写入审计。

基础检查包括：BTCUSDT / ETHUSDT 白名单、当前 TRADING 元数据、真实新鲜 bid/ask、采集健康和磁盘健康、价差、限价偏离、精确十进制数量、未预占账户资产、交易所 free 余额、账户对账新鲜度、单笔金额和本地订单数。只接受数量型 MARKET 或 LIMIT GTC；不支持杠杆、做空、冰山、条件单、订单列表、SOR 或修改订单。

冻结组合规则如下，配置只允许收紧，不允许放宽：

- 单币潜在仓位 ≤ 30% 的保守 NAV。
- BTC 与 ETH 潜在总仓位 ≤ 60% 的保守 NAV。
- 因果、当前的拟执行组合年化波动估计 ≤ 10%。
- 本分钟已成交 quoteQty，加所有该币活跃买卖单的剩余保守金额，加拟新增单金额，≤ 上一已闭合分钟 quote_volume × 0.001。

潜在仓位使用实际库存，加所有活跃买单可能全部成交的数量；挂卖单没有提前从库存扣除。NAV 使用现金和新鲜 BTC/ETH mark，减所有潜在订单手续费准备。第三手续费资产价值不加入 NAV，避免虚构其换算价。持仓或潜在买入币种缺少新鲜 mark 即拒绝。两个单币上限也使 60% 总上限形成一致的第二道检查。

波动估计和分钟量来自外层策略及市场数据管线，执行模块检查因果时刻、完整性和上限，不在发单时用不完整报价临时拟合协方差。外层必须给出拟执行组合的估计，不能把当前轻仓的估计用于新敞口。上一分钟边界必须恰为当前分钟之前的 60 秒，不能选择较大历史成交量替代。分钟容量使用交易所成交 time 持久记录，不因新 tick 或进程重启清零。

手续费准备金不是固定费率证明。`RiskContext` 必须带 `conservative_fee_bps`、`fee_asof_us` 和 `fee_source`，且新鲜实际总费率上限不高于准备金。未来真实接入需要独立查询并合并标准、特殊、税费等账户适用费率；当前合成 fee 字段只用于工程测试。真实网络拒绝 synthetic 来源。BUY 在 quote 预留费用；SELL 在 base 预留可能的 base 手续费；实际佣金始终以详细成交为准。

离线事故模拟可显式 `portfolio_checks=False` 省略组合估计器输入，但该标记会被记录。`adapter.network=True` 时不允许关闭组合检查。默认完整组合检查，不能用绝对金额上限代替比例、波动或容量上限。

## 3. 交易所过滤器支持范围

已实现 PRICE_FILTER、LOT_SIZE、MARKET_LOT_SIZE、MIN_NOTIONAL、NOTIONAL、PERCENT_PRICE、PERCENT_PRICE_BY_SIDE、MAX_POSITION、MAX_NUM_ORDERS 与 EXCHANGE_MAX_NUM_ORDERS。需要账户或币种订单数的过滤器缺少当前计数时拒绝。百分比或 MARKET notional 的 `avgPriceMins` 需要外层提供相应官方参考价格及新鲜时刻，不能以当前 mid 伪造参考价格。0 表示停用的标准 price/lot 条件按官方语义处理。[币安过滤器规范](https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/filters.md)

与本模块不允许的冰山、algo、trailing 或 order-list 类型有关的过滤器不适用。其他未知限制性过滤器，包括当前未建模的账户 MAX_ASSET，默认拒绝。外层需要查询适用账户过滤器，不能把未查询的信息当作空列表认定真实资格。规则快照只表示该次验收输入；真实联网前必须更新。

## 4. 成交、现金与账户对账

累计订单成交与已记账详细成交分开存储，二者不能用 0 佣金或估算成交填平。详细成交必须有 symbol / orderId / trade id / qty / price / quoteQty / commission / commissionAsset / exchange time。唯一键为世代、币种、trade ID；重复成交不重复扣钱；同 ID 的经济字段冲突时整批回滚并熔断。

BUY：quote 减 quoteQty，base 加 qty；SELL 反向记账；佣金从真实 commissionAsset 扣除。BTC、ETH、USDT、BNB 及其他已有资产都可精确记账。未知资产的正佣金造成负余额则回滚并熔断，不伪造初始资产。未知 zero 佣金资产不会引入虚构资金。所有金额用 Decimal，拒绝二进制 float。

撤单确认允许部分成交；后续查询或详细成交可补入撤单期间的成交。FULL 响应不一定带完整时间和费用字段，因此以完整 myTrades 结果补账。查询累计数暂时落后于 myTrades 时保留原账本并冻结，等待较新订单查询；不把这种合法异步延迟当永久成交冲突。

对账比较每个资产 free + locked 总额和账本预期，默认绝对误差容忍 1e-8 资产单位。预占不会增加或减少账本总资金；交易所 free 已包含已知锁仓时不重复扣同一锁仓。本地未发送或较新的订单预占仍限制 free 可用量。锁定余额不能用于新单。

任何未解释资产差异都是 BALANCE_MISMATCH，不能自动覆盖本地账本。正确快照恢复一致后，还需显式审查证据并确认事故，才解除持久熔断。缺详细成交、UNKNOWN 和失败的账户查询都禁止继续开新单。币尘仍属于资产余额，不自动写成收益或费用。

## 5. Testnet reset

官方说明 Testnet 会不预告地周期性清空订单并重新分配虚拟资产；通常约每月，密钥会保留。[币安 Testnet General Info](https://developers.binance.com/en/docs/products/spot/testnet/general-info)

`detect_reset()` 要求至少两个不同的已确认订单消失，且余额改变，才记录 RESET_SUSPECTED。单次 `-2013` 不构成 reset 证明，查询异常也不能当 reset。自动判定结果永远 `confirmed=False`。

只有记录了 reset 嫌疑，明确给出审查证据并 `approved=True`，且新基线与观察余额一致，`acknowledge_reset()` 才开启新 generation。旧订单、成交、审计链保留，旧 generation 的成交不能修改新余额；client ID 和 intent 仍永久不复用。真实 reset 证据需要运维审查，本次仅合成测试。

## 6. 存储、审计与资源

数据库默认 `/home/xflops/coin-state/execution.sqlite3`，位于 D 盘发行版原生 ext4；拒绝 DrvFs 项目路径或 C 盘路径。WAL、同步 FULL、单进程 fcntl 写者锁；一个 engine 的异步请求由锁串行执行。同步 API 属于同一事件循环线程，不允许外部线程直接调用。连接和锁显式关闭。

每笔变更、发送、确认、冻结、对账、reset 都在同一事务追加审计，包含 SHA256 前后链和物化状态摘要。数据库触发器禁止修改/删除审计；启动校验整链，每次提交也检查此前状态摘要，避免静默带入未审计修改。凭证、请求对象、异常消息不入库，只记录异常类型与错误码。该链能发现意外修改；没有外部可信锚时不宣称抵御恶意管理员重写整个库。

磁盘 40 GB 硬限制、32 GB 警戒、36 GB intake 停止、4 GB 应急余量。启动申请 50 MB 预算，数据库自增接近 45 MB 时要求刷新；共享 VHD 被其他任务增大只计入全局磁盘门槛，不消耗本写者的局部预算。完整磁盘 ledger 超过 15 分钟就冻结，调用异步 `refresh_disk()` 后继续；真正 guard 失败保持本进程冻结。

所有命令在 `hpc_linux` 运行，并通过 `scripts/bounded.sh` 进入共享 `coin-quant.slice`；训练、研究和运行总 RAM ≤ 5,000,000,000 字节，MemorySwapMax=0，无 GPU。项目、缓存、临时文件、SQLite 及发行版 VHD 均在 D 盘。数据库按订单事件记录，没有高频原始盘口写入。

## 7. 模块 API 与外层门槛

```python
with ExecutionEngine(adapter, gate=NetworkGate()) as engine:
    engine.bootstrap(initial_balances)  # 仅新账户账本一次
    client_id = engine.prepare(
        decision_key, symbol="BTCUSDT", side="BUY", quantity="0.001",
        price="10000", rules=current_rules, context=current_risk,
    )
    await engine.submit(client_id, rules=current_rules, context=current_risk)
    await engine.recover()  # 查询、trades、余额，不重发
```

外层 adapter 默认 network=False，只注入 MockTransport 才可离线走完整 HTTP。真实模式须先显式同步时钟，并持有只允许 Spot Testnet 的传输授权。

engine 的 NetworkGate 也是默认拒绝。真实发单要求外层独立验证候选门槛、真实 72 小时资格、真实 180 天前向证据、资源门槛、对应证据 hash 和显式 Testnet 授权。Gate 字段是外层已核验的声明，不负责把字符串 hash 变成真实证明。外层未核验时不得构造 enabled gate。本模块没有主网下单路径，环境不匹配立即拒绝。

## 8. 工程验收记录

验收日期：2026-09-30。独立测试覆盖超时未知、查不到仍未知、重启、唯一意图、并发写者拒绝、WAL 只读并发、审计修改检测、撤单与成交竞态、晚到成交、交易重复与冲突、四类费用资产、未知佣金资产、余额不一致与审查解冻、reset 世代、缺失/过期风险证据、过滤器、容量累计、持仓与挂买最坏敞口、网络双门槛、磁盘失效与共享 VHD 增长。

最终短回归：独立 57 项、跨适配器集成 1 项，共 58 项通过，耗时 5.39 秒；Ruff 通过。全部在共享 5 GB、无 swap 的 WSL scope 内执行。网络请求数为 0，签名请求由 MockTransport 在内存模拟。

运行命令：

```bash
bash scripts/bounded.sh .venv/bin/pytest tests/test_execution.py tests/test_execution_integration.py -q
bash scripts/bounded.sh .venv/bin/ruff check src/quant/execution.py tests/test_execution.py
```

最终测试数量及当前源 hash 由跨模块 P07 正式验收报告记录；该报告必须重新生成以匹配最终冻结源码。这里的成功只表示可恢复执行工程与事故处理通过合成验收。真实网络订单、实际账户过滤器与完整费率管线、真实 72 小时 / 180 天及未来收益资格仍需各自证据，当前不能开启交易。
