# 并行写入预算修复与实测版本迁移

2026-09-30。旧参考进程已确认终止，随后才迁移并启动v2；不因观察超时盲目重启。

## 故障证据

旧进程`paper_baselines_runtime_v1`的collector session 2在约2442.56真实观测秒后
以`CALLBACK_STOP`终止：`shadow 100 MB writer budget exhausted; refresh full disk ledger`。
当时保守总磁盘6,797,500,561字节，低于40GB；真实账户/纸面参考账户均现金。
旧最终状态原样保存于`reports/RUNTIME_V1_INTERRUPTION.json`，旧shadow库及契约不覆盖。

原因是旧守卫把整个共享WSL VHD的增长用于单写者100MB额度判断。
182天历史回放在独立库写入时使VHD增长，但这不是实时参考账户自身写入。

## 修复与隔离

新增`concurrent_budget.py`，分别继承冻结Collector/ShadowEngine：

- 单写者100MB额度只衡量自己的SQLite/WAL/SHM增长。
- 全VHD增长仍进入保守总占用，32GB预警、36GB停止新增、40GB硬限保持。
- 全盘后台核验仍执行，真实剩余空间的4GB缓冲仍保持。
- 未减少统计缺口或复用停止期间的健康时间。

新runner为`runtime_v2.py`，契约`paper_baselines_runtime_budget_v2`，
冻结新旧依赖源哈希；仍只公开采集+B0/B2参考，无获准模型或交易所写单。
新参考库`STATE/shadow_budget_v2.sqlite3`，配置绑定并行预算适配器SHA。
原`STATE/shadow.sqlite3`及v1契约保留；collector行情库保留原数据，但新session
重新计算连续72h观察，REST修复不补造历史WS接收或报价证据。

Windows隐藏前台WSL客户端仍使用`live.ps1`，Linux`live.sh`已切v2。
CLI `live-status`和`forward-report`现在读取v2参考运行/库。

## 验收

3项边界回归覆盖：其他任务使VHD增长200MB、实时单库仅1KB时继续；
同样增长触及36GB则拒绝；单库自身100MB仍拒绝。
Collector回归调用真实`guard(force=True)`虚方法入口，不以不存在的`_guard`模拟替代。
与P07真实HTTP签名mock串联一起4项测试通过，5.94秒，静态检查通过。

v2客户端已启动（host PID31240）。独立跨工具核验已确认实际进程存在，
新collector session 3为RUNNING，两币quote/kline/closed价格新鲜，healthy=true，
无未解决缺口，时钟中点偏差-108.5ms。实际连续观察约146.74秒，72h仍未通过。
同期回放与实时总RAM约401MB、峰值435MB、swap0，无OOM；保守磁盘约7.17GB。
同时写入场景现在已观察到全VHD增长约67MB，而实时库自身约676KB，分别记录。
超过100MB全局增长的接受与36GB全局边界拒绝由回归覆盖；不提前称连续72h合格。

## 后续实际观测：中断记录保留

截至下一次独立核验，PID仍实际存在，session3 RUNNING，两币新鲜且无未解决缺口。
但真实事件记录了wall间隔6445.727秒与monotonic间隔15.4887秒偏离；
这可能来自宿主暂停或墙钟调整，不能仅凭日志认定具体原因。
恢复时先冻结，4次时钟查询失败后重新健康。8个数据缺口已通过REST修复，
137根/币修复bar不具有实收WebSocket历史报价。它们不补造报价或健康时长。
当时observed1467.01秒、healthy1225.30秒，uptime83.52%，仍明确不合格。
摘要见`reports/RUNTIME_V2_OBSERVATION_GAP.json`。这一真实故障与工程预算修复分开判断。

历史全程回放已完成。同期全项目RAM峰值660,930,560字节、swap0、无OOM；
结束完整磁盘7,368,603,354字节。没有修改v2冻结源码，也没有重启该实际进程。
