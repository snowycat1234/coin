# Coin Quant

在 D 盘的 `hpc_linux` WSL 中执行；工作目录 `/mnt/d/codex/coin`。

```bash
bash scripts/bootstrap.sh
bash scripts/check.sh
bash scripts/run.sh --help
```

Windows 调用方式：`wsl -d hpc_linux --exec bash /mnt/d/codex/coin/scripts/run.sh ...`。

全部运行数据、环境、缓存、临时文件和日志均在 D 盘。最新授权资源：40 GB 磁盘，
包含整个现有 D 盘 WSL 虚拟磁盘；32 GB 预警、36 GB 停止新增。
全部运行和训练共用 `coin-quant.slice` 的 5,000,000,000 字节 RAM 硬限，禁用项目 swap。
实时进程子限 2 GiB；所有重计算须通过 `scripts/bounded.sh`，GPU 暂不使用。

研究协议见 `PROJECT_PLAN_v2.md`；模块状态和验收记录见 `docs/PROGRESS.md`。仅提供公开行情与研究功能，账户密钥不属于首版配置。

完整目标清单和当前步骤见 `docs/GOALS.md`。
已完成的 Logistic v1 两项候选均 STOP，不部署盈利模型；最后六个月仍封存。
实际结果见 `reports/generated/P04/REPORT.md`。

持续采集与 B0/B2 参考纸面账户使用 Windows 的 `scripts/live.ps1 start/status/stop`。
运行发生于 D 盘 `hpc_linux`，隐藏 Windows WSL 客户端保持发行版存活。
仅参考账户，实际账户保持现金；不会发送币安订单。
WSL 内可执行 `bash scripts/run.sh live-status`、`collector-status` 和 `forward-report`。

