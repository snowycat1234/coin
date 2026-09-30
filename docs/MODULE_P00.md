# P00 验收记录

验收日期：2026-09-30；状态：通过。

最新授权覆盖初始预算：磁盘硬限 40 GB（32 GB 预警、36 GB 停止新增），
全部运行和训练共享 RAM ≤5 GB，无 GPU。`coin-quant.slice` 已安装在 D 盘 WSL 原生配置中，
内核实测 `memory.max=4999999488`、`memory.swap.max=0`。
运行入口和测试统一使用 `scripts/bounded.sh`；实时子进程再限制 2 GiB。
初始 20 GB／15 GiB 可用物理内存描述保留为环境历史，不表示当前获准使用额度。
新增磁盘边界与缓存资格 3 项回归通过，最新总磁盘约 6.65 GB。
时钟故障、WSL 保活及资源证明见 `RUNTIME_ENVIRONMENT.md`。

- WSL 发行版 `hpc_linux`；Ubuntu 24.04，Python 3.12.3，18 逻辑 CPU、15 GiB 内存。发行版虚拟磁盘在 `D:\hpc\linux\ext4.vhdx`。
- 项目、虚拟环境、依赖缓存、临时文件、代码、报告均在 `D:\codex\coin`。uv 0.12.21 本地安装，`uv.lock` 固定 26 个包的解析结果；无 Docker 或 GPU 依赖。
- 磁盘守卫包含整个 D 盘 WSL 虚拟磁盘和项目文件。当前基线总量约 5.95 GB，20 GB 总上限；16 GB 预警、18 GB 停止新增，保留 2 GB 应急空间。
- 通过 7 项首批测试，覆盖磁盘预留越界／外部目录链接、毫秒／微秒解析、重复／坏时间戳、聚合缺口隔离与跨年月份。
- 针对 WSL 挂载盘修复：pytest 改为内存输出捕获；合法 Python 解释器链接指向 D 盘 WSL 中的系统 Python；磁盘扫描采用单次目录读取，避免重复查文件属性。
- 实际并发下载暴露 SQLite 在 Windows 挂载盘上的锁问题。数据库移至 `/home/xflops/coin-state`，仍位于 D 盘 WSL 虚拟磁盘内；Parquet、原始文件、模型及 JSON 数据锁仍在项目目录。每个数据库上下文显式关闭连接。

重跑方式：`bash scripts/check.sh`。完整模块集成后仍需重跑同一验收入口。
