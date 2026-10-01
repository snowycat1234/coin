# P07：Binance Spot Testnet REST 适配器

## 交付状态

本模块完成固定测试环境 REST 接口编码与离线 HTTP 协议验收。代码位于 `src/quant/testnet.py`，订单状态机、幂等账本和风控由 `quant.execution` 负责。工程验收通过不代表开始真实 Testnet 实测；没有读取用户密钥、没有发送交易所订单、没有建立真实 30 天记录，也不授权真钱。

D 盘项目与 WSL 总磁盘预算 40 GB，运行和训练共享 RAM 硬上限 5,000,000,000 字节、swap 为 0、禁止 GPU。验收均在 D 盘的 `hpc_linux` WSL 中，通过 `scripts/bounded.sh` 进入共享限制。

## 当前官方协议依据

2026-09-30 核对 Binance 官方仓库测试环境说明、REST API、错误码和过滤器文档。测试环境只使用虚拟资产，约每月无预告重置，原订单可能消失；重置不能解释为交易已撤销或失败。[测试环境说明](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/general-info.md)

固定原点为 `https://testnet.binance.vision`，端点限定 `/api/v3/`。HMAC SHA-256 签名使用实际发送的百分号编码参数串，API key 放在 `X-MBX-APIKEY`；时间戳采用毫秒，`recvWindow` 默认 5000、上限 60000、最多三位小数。[官方签名与时间规则](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/rest-api.md#signed-endpoint-security)

HTTP 5xx、`-1006`、`-1007` 不能证明下单失败；应按原标识查询。client order ID 仅在未完成订单间唯一，旧单成交后可能重新接受同 ID，所以它不能使盲重发安全。429/418 按 `Retry-After` 秒数冷却。[REST 状态与限频](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/rest-api.md#http-return-codes)、[错误定义](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/errors.md)

成交查询 `fromId` 为包含式游标，分页最多 1000 行，时间区间最多 24 小时；`orderId/fromId` 不与时间区间混用。原始佣金币种必须保留，不能假定 USDT。[账户成交查询](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/rest-api.md#account-trade-list-user_data)

## 可对接接口

`SpotTestnetAdapter` 的 `environment='spot_testnet'`，`network` 默认 `False`。构造函数没有 I/O；不查环境变量或密钥文件。离线注入仅接受 `httpx.MockTransport`。真实模式只有调用方明确传入 `enable_network=True`、Testnet 凭证，且外层执行授权全部满足时才可使用。当前交付和验收没有启用该模式。

| 异步接口 | 合同 |
| --- | --- |
| `server_time()` / `sync_time()` | 读取服务器时间 / 显式计算往返中点偏差；签名前必须同步 |
| `exchange_info(symbol=None)` | 返回原始交易规则和限频资料；首版订单币种限定 BTCUSDT/ETHUSDT |
| `submit(order)` | LIMIT/MARKET、BUY/SELL，要求数量、明确 client ID；强制 FULL 响应 |
| `validate_order(order)` | 独立 `/order/test` 协议，不作为已创建订单 |
| `query(symbol, client_order_id)` | 使用 `origClientOrderId`；明确 `-2013` 返回 `None`，不能据此重发 |
| `cancel(symbol, client_order_id)` | 使用原 ID，保留撤单响应中的 `origClientOrderId` 和部分成交字段 |
| `account()` / `balances()` | 原始账户 / 精确十进制字符串 free/locked 资产映射 |
| `trades(symbol, exchange_order_id)` | 完整分页后的原始成交列表；不完整则抛错，不交付可误认证列表 |
| `trades_page(...)` / `iter_trades(...)` | 显式页 / 包含式 ID 游标逐页推进，默认最多 20 页 |
| `all_orders_page(...)` / `open_orders(symbol)` | 原始订单页 / 单币未完成订单资料，供审计与恢复使用 |
| `close()` / 异步上下文管理器 | 关闭 HTTP 客户端 |

输入订单字段为 `symbol/side/type/quantity/newClientOrderId`，LIMIT 另须 `price/timeInForce`（GTC、IOC 或 FOK）。数量和价格只接受字符串、Decimal 或整数，拒绝二进制 float，避免精度改变。响应保持 Binance JSON 字段；校验订单状态、symbol、订单 ID、client ID、累计成交数量边界，身份或数量无法确认时作为 UNKNOWN。

签名同步超过 30 分钟、本地时钟倒退或收到 `-1021` 后拒绝继续签名，必须由调用方重新显式同步。没有自动同步、自动重试或自动网络启动。禁止跳转，关闭环境代理，不接受外部域名/路径参数；白名单内没有任何主网地址或写单入口。

## 错误和恢复合同

| 类型 | `status_known_rejected` | 执行模块处理 |
| --- | --- | --- |
| `ProtocolRejected`，含 `NetworkDisabled/ClockNotReady` | `True` | 本次请求明确未被接受；撤单拒绝不代表原订单拒绝 |
| `ExecutionUnknown(TimeoutError)` | `False` | 超时、传输错误、5xx、重定向、未知错误码或不可验证响应；冻结并查询原 ID |
| `RateLimited(ExecutionUnknown)` | `False` | 读取 `retry_after_seconds/cooldown_until_ms`，冷却期内接口拒发请求 |
| `PaginationIncomplete(ExecutionUnknown)` | `False` | 分页预算耗尽，禁止将已得到的部分页作完整费用凭证 |

适配器对每次写单只发一次 HTTP；不尝试“重试同 client ID”。查询未找到与测试环境重置无法单独消除未知状态。由执行模块记录事故、对比余额与订单历史、保留原账本并要求复核。

限频包含：保存交易所 weight/order-count 响应头、429/418 冷却，另设单实例 40 次/10 秒与 60 次/分钟保守请求上限。该本地请求数上限不能证明共享 IP 的权重或账户订单限制都满足；调用方应根据 `exchangeInfo` 最新 `rateLimits` 和响应头控制全局预算，出现限制立即冻结，不持续请求。

成交列表按 symbol/orderId 校验，trade ID 严格递增，包含实际 price、qty、quoteQty、commission、commissionAsset、time；缺证即 UNKNOWN。FULL 响应可能缺 trade ID，不能自行生成幂等键或补造费用，应查询 `myTrades`。累计订单成交与逐笔成交不符时由执行模块冻结对账；BNB、基础币或报价币佣金均保留原始资产。

精确数量、最低名义金额、PRICE_FILTER、LOT_SIZE、MARKET_LOT_SIZE、NOTIONAL 等的实际检查由执行模块在已取得规则后完成；适配器不把工程示例中的步长当当前交易所规则。[官方过滤器](https://github.com/binance/binance-spot-api-docs/blob/master/testnet/filters.md)

## 离线验收范围

验收采用注入 HTTP mock 和合成凭证。覆盖固定域名、不读取环境凭证、签名与实际发送参数一致、时间偏差、精确十进制、FULL 响应、错误码/5xx/超时不重发、未知错误保守分类、429/418 冷却、本地限频、主网跳转阻断、部分成交撤单、账户余额、规则、分页包含式游标、重复 ID/预算耗尽/缺时间拒绝、无效参数发送前拒绝、响应身份不符、`-1021` 后失效、独立 test-order 端点。

2026-09-30：21 项适配器测试通过，Ruff 通过。与真实 `ExecutionEngine` 的 HTTP mock 联调由执行模块验收补充。真实网络、真实测试账户及连续至少 30 天的重启、断线、时钟和费用对账实证尚未开始，不能以 mock 时长或历史回放代替。
