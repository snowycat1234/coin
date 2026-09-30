# P05 前置模块：Binance 主网只读采集与数据资格

该模块只接收 BTCUSDT、ETHUSDT 的现货公共行情。没有 API 密钥、账户访问、订单提交或真实资金操作。72 小时资格只表示行情采集连续性达到门槛；它不表示策略盈利，不表示 P05 完整影子交易验收，更不授予 champion 资格。

## 实际交付

| 文件 | 职责 |
| --- | --- |
| `src/quant/collector.py` | 接收、校验、幂等持久化、缺口记录与回补、健康心跳、真实时长资格 |
| `scripts/collector.sh` | 在 WSL 中前台运行，或启动／查询／停止后台进程 |
| `tests/test_collector.py` | 合成事件、REST 模拟、磁盘故障、WAL 并发与单写锁验收 |
| `reports/P05_SMOKE.json` | 有界真实主网连接验收，记录实收数量与运行健康证据 |

执行环境为 WSL `hpc_linux`，项目在 `/mnt/d/codex/coin`。SQLite 主库默认在 `/home/xflops/coin-state/live.sqlite3`，这个 Linux 目录属于 `D:/hpc/linux/ext4.vhdx` 内部，计入用户更新后的项目 40 GB 上限。将库放到这里是为使用 Linux 原生的 SQLite WAL 锁；验收发现 DrvFs `/mnt/d` 上的 WAL 并发锁不可靠。项目 `state/collector.pid` 和 `logs/collector.log` 留在 D 盘项目目录。

训练与运行合计 RAM 上限为 5 GB，使用共享 `coin-quant.slice` 约束所有相关进程；新的重计算命令经 `scripts/bounded.sh` 执行。正式运行的子 scope 另设 2 GiB 内存上限，并受父 slice 的 5 GB 总限制。GPU 使用禁止；运行 scope 的 `MemorySwapMax=0` 防止项目分页到现有 C 盘交换空间。

## 来源与时间语义

接口依据核对日期为 2026-09-30。

- WebSocket：`wss://data-stream.binance.vision/stream?streams=btcusdt@kline_1m/btcusdt@bookTicker/ethusdt@kline_1m/ethusdt@bookTicker`。该官方入口只提供行情流；联合消息由 `stream`、`data` 包装。见 [Binance 官方 WebSocket 说明](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)。
- REST：`https://data-api.binance.vision/api/v3/klines`，仅 GET、`interval=1m`、每页最多 1000 行；`/api/v3/time` 仅做时钟核对。见 [Binance 官方仅市场数据入口](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#general-api-information) 和 [Kline 接口](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints#klinecandlestick-data)。
- 本模块使用 WebSocket 和 REST 默认毫秒时间戳，与 2025 年起历史现货 ZIP 的微秒时间戳分别处理。

`closed_bars` 只接收 `k.x=true`、1 分钟边界正确、OHLCV 合法且已收盘的蜡烛。按 `(symbol, open_ms)` 唯一约束去重；保留首次 `received_ms` 和 `source`。WS 行记录交易所 `E` 与真实应用接收时间 `websocket_received_ms`。REST 行明确 `source=rest`，其 `received_ms` 为 REST 响应被收到时刻，`exchange_event_ms` 和 `websocket_received_ms` 初始均为空。后来真实收到同一闭合 WS 事件时，只补充 WS 证据，不覆盖首次来源。

Spot `bookTicker` 官方事件没有交易所事件时间 `E` 或 `T`。因此 `quote_minutes.exchange_event_ms=NULL`，明确按本机收到时间所在的 UTC 分钟分组。保存每分钟的样本数、点差 bps 总和／最小／最大、首末收到时间、首末 update ID、最后 bid／ask；平均点差用 `spread_bps_sum/samples` 计算。这是收到更新的样本平均，不是时间加权平均。所有原始高频报价只存在于当前分钟内存缓冲中，不落盘。

## 持久化、缺口和运行健康

数据库使用 WAL、`synchronous=FULL`、约 1 MB 自动 checkpoint，关闭时显式 checkpoint 和 close。Linux `fcntl` 锁保证同一库只有一个活跃采集进程；状态查询使用独立只读连接，查询结束显式关闭。

闭合 Kline 相邻时间不连续会立即记录 `gaps`。每分钟维护也检查内部和尾部缺口，覆盖连接静默导致的缺失；REST 回补成功后记录 `repaired_ms` 及 `repair` 事件。回补不改变实收时间，不能补造报价，不贡献真实在线秒数。REST 失败留待后续维护重试，缺口保持未解决。

`events` 持久记录启动、连接尝试、连接成功、断线错误、重连、服务器停机通知、24 小时连接重建、缺口、回补、心跳、健康变化、时钟变化、磁盘预算刷新和停止原因。重连采用 1、2、4、8、16、32、60 秒的有界指数退避，稳定连接满 60 秒后重置退避。23 小时 50 分钟主动重建连接，避免在官方 24 小时强制断开时刻才处理。客户端自动响应服务端 Ping；不额外发送客户端定时 Ping。

每 15 秒检查两个币种的新鲜 Kline、报价、已闭合蜡烛、未解决缺口和本地时钟。缺任一币种 Kline、网络报错、时钟异常、磁盘不足均不能累计健康时间。Kline 交易所时间领先本地超过 5 秒或滞后超过 15 秒，会拒绝并重连；启动时立即核对交易所时钟，之后每小时核对。检测本机大幅时钟跳变后立即使原同步失效，并在本轮维护重新同步；同步仍异常则继续计为不健康并重试。磁盘完整扫描较慢，不能放在实时消息路径中。

磁盘启动时异步线程完成完整核算并预留 100 MB。运行中每 15 秒只检查 VHD 和库增长、D 盘剩余空间，保守估计已用空间并调用 `quant.disk.enforce`；完整扫描每 15 分钟在线程中刷新。按更新后的资源预算，32 GB 开始预警，36 GB 为 intake 提前停止门槛，40 GB 为硬上限，并保留 4 GB 紧急空间。增量达到本次 100 MB 预算、总量达到 36 GB intake 上限或侵占 4 GB 紧急空间，即记录失败、冻结资格并停止采集。完整扫描不会阻塞 WS 收包或心跳。历史 smoke 报告记录其运行时使用的 20 GB 旧预算，保留原始证据。

## 真实 72 小时资格规则

`qualified_72h` 只有全部条件满足才为真：

1. 最近会话由真实 `collect()` 启动且仍在运行；最近心跳不超过 45 秒。
2. 当前真实会话至少被观察 259200 秒，并且 `healthy_seconds/observed_seconds >= 99.9%`。两个计时均以 `time.monotonic()` 为依据。健康时间只累计相邻两个健康心跳之间不超过 30 秒的区间；不健康、时钟跳动、连接轮换和进程挂起会增加真实观察时间中的 downtime，保留已健康累计。72 小时内 downtime 预算为 259.2 秒。进程重启会建立新会话窗口。直接调用消息处理器或历史回放不创建真实会话，也不累计秒数。
3. 两币种最新 72 小时各有 4320 个连续闭合分钟，且完整报价分钟覆盖率各至少 99.9%：4320 分钟中至少 4316 条完整报价记录。断线或停机刷出的 partial 分钟不作为完整分钟；partial 和 missing 数量分别报告。报价缺失不会通过 REST 回补伪造。
4. 没有未解决蜡烛缺口，并且两个币种都有 90 秒内真实收到的闭合 WS 蜡烛。
5. 当前完整磁盘守卫通过。

计划的每日连接重建会计入 downtime 和 partial 分钟，但不会将 72 小时计时清零，因此正常轮换仍然可能合格。若 downtime 或报价缺失超过 0.1%，资格为假。状态同时报告已观察秒数、健康秒数、downtime、uptime、连接轮换次数，以及 clock_jump／clock_unhealthy／clock_sync_error 的本会话事件数量。

短时网络 smoke、合成测试、历史数据回补不能满足真实 72 小时要求。本模块不会把这些材料报告为“已通过 72 小时运行验收”。该规则是对原方案 72 小时运行可用率 >=99.9% 的执行定义，避免每日正常连接轮换导致门槛永久无法达到。

## 操作

在 WSL 中 `cd /mnt/d/codex/coin` 后执行：

```bash
bash scripts/collector.sh run 90
bash scripts/collector.sh start
bash scripts/collector.sh status
bash scripts/collector.sh stop
```

Python 接口为 `await quant.collector.collect(run_seconds=None, db_path=None, tick_callback=None, stop_event=None)` 和 `quant.collector.status(db_path=None)`。`stop_event` 可传入同一事件循环的 `asyncio.Event`，启动前或启动中设为 true 都会请求正常结束，避免外部进程猜测信号处理器注册时序。有界 smoke 使用独立的测试库，不把它拼接成长期运行的资格。Linux 后台 PID 存在项目 `state/collector.pid`；停止会核对 `/proc/<pid>/cmdline` 是否属于采集器再发送 SIGTERM。用户的 WSL 或电脑休眠会影响连续性，并在真实健康规则中反映。

长期运行使用 `scripts/live.ps1 start` 的 Windows 隐藏前台 WSL 客户端，它通过 `scripts/live.sh` 执行一体采集／模拟运行程序；状态与停止分别使用 `scripts/live.ps1 status`、`scripts/live.ps1 stop`。仅从短暂 WSL 命令启动 Linux `nohup` 无法保证这个设备的发行版生命周期：第一次启动产生 PID 1274，随后进程消失且 live 库尚未创建，因此没有生成真实会话。Microsoft 官方说明 [systemd 服务不会保持 WSL 实例运行](https://learn.microsoft.com/en-us/windows/wsl/systemd)。`collector.sh start` 只适合已有持续 WSL 客户端维持的环境，正式入口以 Windows 前台客户端为准。

## 单进程新鲜行情回调

`tick_callback` 是同步轻量观察回调，接收每个新报价 update ID 或首次收到的闭合蜡烛。未闭合蜡烛、重复闭合蜡烛、重复／倒退报价 ID 不触发新的模拟成交输入。回调失败会记录 `callback_stop` 并以 `CALLBACK_STOP` 停止会话，避免采集继续但模拟账本静默漏写。

回调字典包含 `kind`（`quote` 或 `closed_bar`）、`symbol`、真实 `received_ms/received_us`、`exchange_event_ms/us`、`quotes`、`bar` 和 `health`。微秒字段由默认毫秒乘 1000，是单位对齐，不声称具有额外时间精度。`bar` 包含 `open_us`、`close_us`、真实信号可用时刻 `available_us`、浮点 OHLCV、交易笔数和 WS 来源，供共用研究／模拟接口。`close_us=(T+1)*1000` 为与历史研究一致的右开边界；交易所原始含终点毫秒独立保留为 `source_close_us=T*1000`。如果同一蜡烛先经 REST 回补、随后首次真实收到闭合 WS，仍只在首次 WS 证据到达时发出一次 bar 回调，同时保留表内最初 REST 来源与收到时间。

每币 `quotes` 快照含浮点 `bid/ask/bid_qty/ask_qty`、真实 update ID、收到时间、当前年龄及 `fresh` 标志（年龄 0 至 2000 毫秒）。报价交易所时间仍为空，原始价格字符串留在采集持久表。回调拿到独立复制快照，不能通过修改它污染内部缓冲。报价来源为真实 WS，分钟聚合不用于成交填价；模拟端应等待信号可用时刻之后的新报价，核对收到时间与 update ID。

`health` 包含瞬时状态／理由、连接与真实会话状态、每币新鲜度、未解决缺口、时钟偏移、`heartbeat_ms`、真实 `disk` 守卫快照，以及 `qualification`。磁盘快照包含最近检查的 status、asof_ms、check_kind 和实际核算／增量字段，拒绝时明确 STOPPED；模拟端无需硬填 OK。资格在心跳中轻量更新并附 `asof_ms`、observed／healthy／uptime；瞬时故障立即使快照资格为假。模拟端应拒绝超过 45 秒的心跳或资格快照。每报价回调只处理两个币种的内存快照，不完整扫描磁盘或遍历历史数据。完整 `status()` 仍是人工／验收查询接口。

## 本轮验收

32 项测试通过，覆盖未闭合不写、闭合幂等、首次收到证据、蜡烛缺口和 REST 回补、静默尾部缺口、报价按分钟聚合、重复 update 去重、磁盘故障停止、历史回放无法生成资格、进程挂起／陈旧心跳无法通过、报价原始数据不落盘、非法行情拒绝、未收盘 REST 蜡烛不写、原生 WAL 并发状态读取和单写锁，以及陈旧交易所事件拒绝、时钟同步记录和 C 盘路径拒绝。新增验收模拟验证每日轮换两次仍可能通过、72 小时内 259 秒 downtime 可接受而 260 秒不可接受、报价缺失独立拒绝、时钟跳变使同步失效并明确报告，并验证在两个健康心跳之间发生的快速轮换仍计入 downtime。回调验收覆盖去重、复制快照、新鲜度、无慢磁盘扫描、回调失败冻结、无效深度拒绝、真实 disk／heartbeat／资格证据、启动前 stop_event 正常结束、右开时间边界及 REST 先到后首次 WS 仍正确回调。这些测试使用合成会话，不替代真实 72 小时实测。

真实网络 smoke 验收结果由 `reports/P05_SMOKE.json` 保存。85 秒有界测试收到 BTC／ETH 各 1 根闭合 Kline、8234 个报价更新，聚合为每币 3 条分钟记录，SQLite 为 40960 字节。最新记录 observed=81.37 秒（至最后心跳）、healthy=0 秒，记录一次本机时钟跳变和四次陈旧事件拒绝／重连，资格正确为假。该结果证明持久化与降级处理可工作，尚不能证明长期 99.9% 可用率。

随后直接连接同一公开 WS 20 秒定位行情来源：两个币种各收到 9 次 Kline 更新，首次事件收到时间比交易所 E 晚 57 毫秒，报价共 2782 条。说明端点与订阅正确，短测异常需在持续运行中继续观察时钟与网络事件。首次 smoke 暴露的“WSL 启动不足一小时未立即同步交易所时钟”缺陷已修正，启动即同步的验收通过。初次异常样本保留为 `reports/P05_SMOKE_INITIAL.json`。

## 时间与启动环境修复实测

独立 45 秒 Python CLOCK_REALTIME／MONOTONIC 采样排除了 collector 计时算法问题：修复前第 15 秒墙钟前跳 22.204 秒、第 30 秒回跳 22.214 秒；Windows W32Time 状态为未同步的 Local CMOS Clock，WSL 的 Ubuntu NTP 偏移为 -22.201362 秒。宿主 Hyper-V 时间和发行版 NTP 的目标不一致，产生真实系统时钟竞争。修复前原始证据保存为 `reports/P05_CLOCK_DIAGNOSTIC_INITIAL.json`。

项目主执行器以三个 Ubuntu NTP 独立样本校正宿主时间，原偏移约 -22.21 秒，修后约 +0.01 秒；细节保存为 `reports/HOST_TIME_REPAIR.json`。D 盘发行版 `systemd-timesyncd` 当前 inactive／disabled，避免与 Hyper-V 宿主校时竞争；需要恢复时可执行 `sudo systemctl enable --now systemd-timesyncd`，并重新验证不会出现竞争。

修复后相同独立 45 秒采样无大跳变，最大单步 REALTIME／MONOTONIC 差为 0.000848 秒。Binance `/time` 三次请求中点偏移为 +588.5、-28.5、+121.5 毫秒（RTT 为 1437、359、541 毫秒），均满足现有 5 秒门槛。修后报告为 `reports/P05_CLOCK_DIAGNOSTIC.json`。现有守卫与 99.9% 要求没有降低；实际 72 小时与长期可用率仍需持续观察验收。

本轮实现完成的是 P05 所需的数据采集和观察基础，后续策略候选仍必须通过 P04 的独立统计门槛，以及 P05 完整影子组合、订单模拟、账户对账和风控验收。正式一体程序由主执行器在回调与模拟账本集成后启动；本模块验收没有另外启动或停止采集进程。
