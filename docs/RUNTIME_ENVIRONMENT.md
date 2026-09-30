# 运行环境修复与资源验收

日期：2026-09-30。所有项目代码、数据、缓存与日志位于 D 盘；
SQLite 位于 D 盘 WSL 虚拟磁盘的 `/home/xflops/coin-state`。

## 时钟故障与修复

独立的 45 秒 REALTIME／MONOTONIC 采样发现来回约 22.2 秒的跳动。
Windows 原时钟服务停止，源为未同步的本地 CMOS；Linux NTP 报告偏移 −22.20 秒。
Ubuntu 24.04 的 timesyncd 和 WSL Hyper-V 宿主同步在争用不同的时间。
此机制与 [Ubuntu 官方时间同步说明](https://ubuntu.com/wsl/docs/stable/explanation/time-sync/) 一致。

保存原 Windows 时间设置到 `state/host_time_original.json`。
原生 W32Time 校时尝试未获得时间数据，因此从可达的 ntp.ubuntu.com 取三次独立偏移，
要求样本数为 3、差值不超过 0.1 秒、偏移不超过已审计的 30 秒范围，
按中位数校正宿主 −22.2103247 秒。
复测偏移 +0.0117／+0.0125／+0.0106 秒。
临时 NTP peer 和服务启停已恢复原配置；校准后的系统时间保留。
Windows 原生操作遵循 [Microsoft W32Time 文档](https://learn.microsoft.com/en-us/windows-server/networking/windows-time-service/windows-time-service-tools-and-settings)。

D 盘 `hpc_linux` 内已禁用 timesyncd，依宿主同步，防止双重校时。
修后 45 秒独立测试最大单步时钟差 0.000848 秒，无大跳；
Binance `/time` 三次 RTT 中点偏移 +588.5／−28.5／+121.5 毫秒，均在 5 秒以内。
记录：`reports/HOST_TIME_REPAIR.json`、`reports/P05_CLOCK_DIAGNOSTIC.json`；
原异常保留为 `reports/P05_CLOCK_DIAGNOSTIC_INITIAL.json`。
服务恢复方式为在该 D 盘发行版中重新 enable/start timesyncd；未修改 C 盘 WSL 配置。

修复证明本轮故障缓解，长期采集仍须逐小时核对 Binance 时钟并通过真实 72h 验收。

## WSL 存活与内存

Linux `nohup` 子进程没有保住 WSL 的生命周期，首次后台 PID 已消失，
尚未建立真实采集库，启动成功的初步状态已撤回。
[Microsoft 明确说明 systemd 服务本身不会保持 WSL 存活](https://learn.microsoft.com/en-us/windows/wsl/systemd)。
因此用隐藏 Windows `wsl.exe` 客户端前台运行应用，进程及日志在 D 盘管理。
`scripts/live.ps1` 核对 PID、命令和创建时刻，支持 start/status/graceful stop。
不把普通 nohup 的成功返回当作持续运行验收。

最新用户约束：磁盘扩展至 40 GB，但运行和训练合计 RAM 不超过 5 GB。
专用共享 `coin-quant.slice` 对所有项目 scope 施加 `MemoryMax=5000000000`、`MemorySwapMax=0`。
已实测内核按页向下取整为 4,999,999,488 字节；属于合计硬限，多个进程或 agent 不各领 5 GB。
所有测试、训练、报告、依赖安装和实时入口经 `scripts/bounded.sh`。
实时进程子 scope 再限制 2 GiB，`MemorySwapMax=0`。
已实测 `memory.max=2147483648`、`memory.swap.max=0`、`memory.swap.current=0`。
现有 WSL 系统 swap 使用量为 0，本应用不得借助默认的 C 盘分页空间。
该约束在 D 盘发行版运行期生效，不创建 C 盘项目缓存或分页文件。
项目 GPU 未使用。`quant resources` 检查真实 cgroup、RAM 当前/峰值、swap 和 OOM 计数，
启动前缺少共享限额即拒绝运行。
内存不足、磁盘守卫、时钟或行情健康失败均冻结执行并留下记录。

长期客户端需要电脑和 WSL 持续运行。停机／休眠／重启后，
采集会话的 72h 资格重新累计，旧证据和纸面账本保留；不补造停机期间的前向成绩。
