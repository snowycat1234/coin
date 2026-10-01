# 独立公开分钟行情采集 v3

## 用途及边界

A05 实际 54 fit 已结束为 STOP_v2，没有获准候选。旧 B0/B2 runtime 的来源合同与
数据库保留。本模块恢复独立分钟行情积累，供以后按真实可用时间构造小时特征。
不创建金融账户，不调用策略、ShadowEngine、Testnet 或任何订单接口，不读取凭证。
`concurrent_budget.py` 会导入 ShadowEngine 类，但本入口只实例化 ConcurrentCollector；
工程测试禁止构造金融类并检查新数据库的全部表名。

仅新增 `collector_public_v3.py`、两个启动脚本、本模块测试及文档。不修改既有
collector/concurrent_budget、research_v2 SOURCE_FILES、旧 shadow 合同或原证据。
A07 是独立采集进程，保持原进程/数据库/store，不把两者的运行时长拼接。

## 来源和采集合同

复用已验收的冻结 Collector 与 ConcurrentCollector，包括两币 1m Kline、按收到
分钟聚合的 bookTicker、闭合幂等、缺口检测、REST 回补、真实时钟/健康心跳及
全盘/本写者分离的预算逻辑。没有新撮合、信号或研究逻辑。

币安官方 [WebSocket Streams](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)
列出 `data-stream.binance.vision` 为仅行情域名；订阅 BTCUSDT/ETHUSDT 的
`@kline_1m` 与 `@bookTicker`。只持久 `k.x=true` 的闭合 Kline，bookTicker 保存
分钟聚合，不存全量原始更新。bookTicker 无交易所 E/T，不伪造交易所时间。
REST 仅使用 [公开行情 REST](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
的 `data-api.binance.vision` `/api/v3/time`、`/api/v3/klines`；没有订单或账户请求。

Kline 表保留 close_ms 为官方含终点毫秒，小时研究右开边界须使用
`(close_ms+1)*1000`，available 时间按真实 received_ms。REST 行保留 source=rest，
exchange_event_ms=NULL、websocket_received_ms=NULL；之后首次收到 WS 的处理继续
遵从原 Collector 合同。回补不变成实时收到、不补健康、不能补造报价。

默认 native DB：`/home/xflops/coin-state/collector_public_v3.sqlite3`，位于 D 盘 WSL VHD。
不读取、迁移或覆盖旧 live.sqlite3、影子账户库或 A07 库。只允许 native STATE 下
`collector_public_v3*.sqlite3` 独立文件名；已有文件无本模块 registry 时拒绝使用。
ROOT/STATE/WSL_DISTRO_NAME 必须为固定 D 盘项目、native STATE、hpc_linux，拒绝
通过环境别名指向 C 盘。Linux fcntl 锁覆盖绑定、全盘预留、运行及关闭全程。

每个数据库 `public_contract` 保存唯一不可修改的来源合同：runner、冻结 collector、
concurrent_budget、其 shadow 导入依赖、当前 disk/resources/paths、env/bounded、
两个新 launcher、pyproject.toml/uv.lock 的 SHA；并绑定实际 Python/SQLite/httpx/
websockets/numpy 版本、scope、路径及资源限制。来源/依赖变化拒绝原库重启，
原绑定及其生命周期账本不修改。改版必须另立来源/数据库。

`public_lifecycle` 追加 RUN_REQUEST、RUN_FINISHED、RUN_ERROR 和
UNGRACEFUL_PREVIOUS_SESSION；hash chain 与 UPDATE/DELETE 阻断触发器校验。
冻结采集器的 events/sessions 原语义保持：收到时间和回补标志必须据实读取。
新 registry 保护来源/生命周期，不声称给旧式 bars/events 表新增了全表防篡改链。

## 恢复和状态

正常停止完成原采集器的 quote partial flush、sessions ended_ms、stop 事件、WAL
checkpoint/close，再释放单写锁。崩溃后旧 session 的 ended_ms 为空：新入口另记
UNGRACEFUL_PREVIOUS_SESSION 和最后 heartbeat；不改旧 session 结束时刻、不计入
停机期间的 observed/healthy 秒数，原缺口由冻结采集器按原规则检查/回补。
启动新真实 session 后重新开始 72h 观察窗口，不跨进程拼接。

默认 `read_public_v3_status()` 是同一只读 SQLite BEGIN 快照，校验 registry 与
来源匹配并返回最新 session、heartbeat、两币 WS/REST 数量及未解决缺口。无 writer
构造器、网络、全盘扫描或金融动作；RUNNING 但心跳超过 45s/在未来时返回
STALE_OR_STARTING。短时启动尚未有心跳也按该状态报告。

该廉价状态快照 `qualified_72h=null`，scope=NOT_CERTIFIED_BY_THIS_SNAPSHOT，
不自行授予 72h 资格。需要完整数据准备验收时显式调用原 `quant.collector.status`
对新库进行正式 72h/99.9%/quotes/gaps/disk 检查；该检查会完整盘点且较慢。
`collect_public_v3()` 完成有界运行时返回原采集器的完整检查结果。工程注入必须
显式 engineering=True 且使用没有网络 loop 的 fixture，并强制 qualified_72h=false；
工程库不能改成 live 来源重启，CLI 没有工程绕过选项。

本模块一直 alpha_eligible=false，没有任何候选或策略获准。日期按 UTC 存储；
需要 `2026-10-01T00:00:00Z` 之后的研究材料时须显式按真实 received/available
筛选，不能把本地 10 月 1 日或 REST 旧蜡烛自动称为 TRUE_FORWARD_V2。

## 资源和操作

总盘 40GB，32GB 预警、36GB 停新增、保留 4GB；单次采集器预留100MB，自己的
DB 增量消耗自身额度，其他作业 VHD 增量只参与全局检查。完整扫描启动及每15分钟
使用后台线程，15秒廉价检查不阻塞网络；原 bounded.sh 强制共享 coin-quant.slice
RAM<=5,000,000,000 bytes、swap=0。无GPU，训练和全部采集共同受该5GB限制。

API：

```python
await collect_public_v3(seconds=None, db_path=None, stop_event=None)
read_public_v3_status(db_path=None)
```

Windows 前台 WSL 隐藏入口（长期运行默认 native 新库）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/collector_public_v3.ps1 start
powershell -ExecutionPolicy Bypass -File scripts/collector_public_v3.ps1 status
powershell -ExecutionPolicy Bypass -File scripts/collector_public_v3.ps1 stop
```

start 先核验独立正式验收 receipt 及全部来源 SHA；owned host PID+CreationDate+
runner+distro 判断当前身份。原日志带毫秒时间戳归档，保留旧记录。stop 只写本模块
stop 文件，由入口协作停止；不会匹配/停止旧 runtime 或 A07。SIGINT/SIGTERM 也
使用同一 stop_event，启动盘点阶段已注册处理器。

有限短测和只读状态：

```bash
bash scripts/bounded.sh .venv/bin/python -m quant.collector_public_v3
bash scripts/bounded.sh .venv/bin/python -m quant.collector_public_v3 --run --seconds 90 \
  --db /home/xflops/coin-state/collector_public_v3_smoke_unique.sqlite3
```

## 验收

20 项独立离线工程测试通过；涵盖无金融表/构造、旧库及 unowned 库拒绝、依赖变化
在 writer/network 前拒绝且旧账本不变、offline/live 隔离、非法时长、fcntl 与实际
双 async writer 竞争、不可改写 registry、只读状态无扫描/网络、异常 session 重启
缺口及不补计时、磁盘失败释放锁、trigger 缺失、C 盘别名、真实冻结 loop 在预先
stop 时不发任何 HTTP/WS 请求。实际网络短测与来源/资源凭证另存
`reports/PUBLIC_COLLECTOR_V3_ACCEPTANCE.json`，短测不等同实际72h或研究获准。

长期启动只在离线与真实短测验收 receipt 完成后进行。未来实际72h健康、长程缺口、
数据日历覆盖须继续按真实证据验收；STOP_v2 未被本数据修复改变。
