# A07 公开采集退出与恢复记录

日期：2026-10-01（Asia/Shanghai）；审计存储时间为 UTC 微秒。

## 1. 已观察的事故

旧 Windows 前台客户端 PID 30640 已不存在，WSL 中没有对应采集进程，数据库和
store 的两个单写者锁均未占用。原 stdout/stderr 为零字节，未保存应用退出码或
异常栈。只读账本返回 `STALE_OR_DISCONNECTED`，不能把旧 checkpoint 内的
`connected=true` 当成当前仍在线。

| 本地时间（UTC+8） | 不可变审计或 Windows System 证据 |
|---|---|
| 02:56:12.640049 | 原会话 `2749c70ae7d74784861d79b1509c8f6c` 建立 |
| 02:57 / 03:00 | 两次 ConnectionClosedError，随后自动重连；四个 aggTrade ID 缺口已记录 |
| 03:10:39.283966 | Service Control Manager 7045：安装路径含 WindowsSubsystemForLinux_3.0.1.0 的 wslinstaller 服务 |
| 03:11:48.305024 | Service Control Manager 7040：WSL Service 由自动启动变为禁用 |
| 03:11:53.465857 | 旧会话末条审计为 DISCONNECTED，最后已接收事件为 03:11:48.461079 |
| 03:11:53.895922—54.438677 | Hyper-V VmSwitch：WSL 虚拟 NIC 断开、端口删除 |
| 03:15:02.571639 | Service Control Manager 7045：WSL Service 重新安装 |

这些记录直接证明采集末尾附近发生了宿主 WSL 服务变更和虚拟网络拆除。
因此宿主环境中断是当前最有依据的原因解释；未保存安装发起者、具体终止命令、
退出码或应用异常，不能进一步断言是谁操作或某条异常就是唯一根因。

此前磁盘扫描原子重命名竞态已经由父任务修复。末条记录约在首次 900 秒后台扫描
之后，时间本身也能符合该假说，但没有对应异常证据，不能把它认定为此次主因。
旧进程会保留启动时已导入的代码，文件修改时间也不能证明它热更新了磁盘模块。
恢复启动使用当前扫描代码；具体消失文件容忍、权限错误拒绝的四项既有测试通过。

WSL 调查期间出现不同 boot ID，当前 journal 只有当次 boot；历史进程和历史 OOM
状态没有完整留存。恢复后的 `oom_kill=0` 仅说明当前 cgroup 快照，不能倒推原进程
从未被系统终止。没有启动、停止或修改 legacy 采集器，也未更改 WSL 服务配置。

## 2. 原数据完整性

恢复前同一只读 SQLite 快照确认：

- `quick_check=ok`；17 条审计 hash chain 及禁止 UPDATE/DELETE 的触发器校验通过。
- 审计原 head 为 `cd4368d70871b81325ebd08f547beb9e92705e4672012388f963dbba0dbdc6b2`。
- 原 checkpoint 已接收 138,396 条事件；940.929780682 秒真实 monotonic 观察值不是
  健康时长认证，也不代表无缺口。
- 四个 manifest 对应 Parquet 的 SHA 均一致：194,546 字节、1,504 行。
- outbox 有 842 条已提交待导出记录；未提交 RAM 秒尾不补造，原 raw 尾段也不能
  自动当成完整 gzip 或永久灾备。
- 原会话没有 STOP；其正常封尾、最后未封秒和部分聚合窗不能认证完整。

证据目录：`reports/generated/A07_incident_20261001_0329/`。其中 `before.json`、
原 host ownership record、原零字节日志和含原始 XML/record_id 的
`windows-system-events.json` 都另存新文件，未改写原验收报告。

## 3. 授权恢复及连续性边界

确认不存在原进程和 writer 后，使用既有 `scripts/microstructure.ps1 start` 恢复
同一公开只读入口。新 owned host PID 为 8936，新 Linux PID 为 500；新会话为
`40c881d3ef8b484ba2ac36263517f8f6`。源码 SHA 保持：

`649a69c924cdcfc4e85dca37a2a6c4958993f3f3365e04b3f10372f8875ddbb4`

原 outbox 的 842 条记录已导出，manifest 累计变为 2,346 行；先前四个 Parquet
不删除、不覆盖。新会话追加 SESSION、RESTART 和两币真实 aggTrade 缺口，保留旧
17 条审计前缀。该中断不回补为实收，不拼成连续健康；恢复后的新收事件另计。

跨调用进程身份、boot ID、实时 checkpoint 增长、旧审计前缀和旧文件不变的检查
写入独立 `reports/A07_CONTINUITY_2026-10-01.json`。状态是采样时的观察结果，
不能保证之后一直存活；status 仍固定 alpha_eligible=false、real_time_days_certified=0。

公开连接只订阅两币 bookTicker / aggTrade，无凭证、账户或订单请求。原 40GB 总盘、
共享 RAM<=5GB、swap=0、无 GPU 限制继续生效。8GB long feature 写前硬限和 raw
<=24h/4GB 保留，不静默降频、不删既有 feature 证据。

实际 24h 容量/质量、14d/30d 数据门槛及 alpha 仍待验收。此次恢复和短段连续性检查
只证明工程入口能够恢复采集，不提升任何研究或交易准入资格。
