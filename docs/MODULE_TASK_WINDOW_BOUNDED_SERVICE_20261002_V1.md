# 8765 持续运行与实际故障恢复

用户报告窗口挂起后，确认旧viewer进程已不存活，API无法使用；原采集与历史任务的
异常退出另记，不声称已查明WSL重启/OOM原因。页面现显示“已连接”，保留在Codex浏览器。

生产为 enabled user service `coin-task-progress-window-v7-v3.service`：
原 `bounded.sh` 启动原只读wrapper，仍归入共享coin-quant.slice、5GB RAM/swap0。
Restart=on-failure、3秒重试；KillMode=mixed向被移入受限scope的真实MainPID停止，
避免服务停止后遗留端口占用。没有修改原viewer、runner、UI、bounded、资源守卫或采集源。
这里只显示训练/测试/扫描实际状态，不扩市场dashboard或观察器。

## 实际验收

- 真正viewer SIGKILL后4.639秒API恢复，PID更换、NRestarts实际+1。
- 显式stop后原PID不存在、8765不能连接；start后API恢复，无scope孤儿/残留listener。
- 两路采集PID 746/776、start_ticks和命令前后相同。
- 实际cgroup约5GB、swap0；unit enabled、source与安装字节相同。
- 浏览器刷新后“已连接”，显示正在运行的OOF实验和官方月档任务。

首次缺少WSL_DISTRO_NAME导致守卫拒绝的尝试、直接启动Python的v2过渡服务均留证。
v2已disable/stop，生产只使用v3。没有为验收重启WSL；enabled只证明配置了用户
systemd启动，不声称已经跨WSL重启验证。原正在运行任务不注入进度或改源。

凭证：`reports/fast_research/V7_TASK_WINDOW_BOUNDED_SERVICE_ACCEPTANCE_20261002_V1.json`。
安装unit位于 `/home/xflops/.config/systemd/user/coin-task-progress-window-v7-v3.service`；
生产wrapper在D盘 `.cache/serve_task_progress_v2.py`，与已入库
`docs/archive/TASK_PROGRESS_RESTART_WRAPPER_20261002_V2.py` 字节一致。
重建该本机服务时须先确保STATE日志目录存在、恢复上述wrapper，并使用v3 unit；
不启用旧v2。原异常会话/失败日志不会被当作正常完成或新的健康时间。
