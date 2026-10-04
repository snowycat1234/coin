# D066：原公开采集实际恢复

## 本版改变与验收范围

D065已推送 `b6b517710a29406bbb46e2142cba64dc1a57a38e` 后发现原两路采集实际无进程。旧任务文件仍写running；没有真实退出码、退出原因或最终STOP，因此保留UNKNOWN，不推断OOM。

先保存原DB/WAL/SHM、空日志、任务、来源/环境、审计链与闭合数据库副本，在D盘STATE留原字节。副本quick_check与审计链通过，2008份原L1清单文件共96,171,882B全部大小/SHA一致。这是原文件身份核对，不是重跑数据QA或新的资格认证。

随后按原`.venv`、默认数据库/store与公开端点单次detached启动，使用新独占日志和原资源守卫。原collector、执行与资金账户源码未修改。V1观察helper也匹配含模块参数的启动wrapper；V2只加实际Python可执行文件路径过滤，V1留存，无第二次启动。没有新服务、v2采集、密钥、发单、付费或访问绕行。

## 两次实际观测

|项目|第一次|第二次|结论|
|---|---:|---:|---|
|public真实PID/start ticks|890568 / 20387105|相同|原资源组下存活|
|L1真实PID/start ticks|890567 / 20387105|相同|原资源组下存活|
|public会话|6|6|原会话5后新会话|
|BTC/ETH各自WebSocket闭合分钟线|4890|4893|各新增3根|
|public heartbeat增量|—|165,528ms|持续推进|
|L1新会话accepted事件|2753|10114|新增7361|
|L1 checkpoint增量|—|163,029,166us|持续推进|
|共享组当时RAM|241,995,776B|219,688,960B|硬上限4,999,999,488B|

L1新会话 `a1cb5a053be046b193906f3b4a011d91`；旧会话 `6ba28c2935bc4c858f988ac62cd5a6da`。public `UNGRACEFUL_PREVIOUS_SESSION` 明确 `unobserved_time_not_credited=true`，其最后心跳至发现间隔7139.314秒；L1 `RESTART_GAP` 9874.619301秒并保留未提交尾部UNKNOWN。public原REST恢复分钟记录不成为WebSocket连续健康证明；L1缺口没有填造。

四个新日志当时0B，样本无网络/来源错误。两个样本L1 feature rows/bytes未增长，因此仅验收实时事件与检查点推进，不宣称新feature持久化/完整有效日。独立复核见[报告](../reports/PUBLIC_COLLECTOR_RESTORE_INDEPENDENT_REVIEW_20261004_V1.md)。短时恢复不认证72h、14/30/60有效天或alpha；旧资格不拼接。静态PID仅代表捕获时刻，后续须重新核真实句柄。

## 资源与下一科学选择

启动前实际扫描ROOT+整个D盘WSLVHD为27,362,549,923B，时间2026-10-04T15:31:26.316122Z，加1GB预留仍低于32GB预警；这不是模块结束后扫描。共享生命周期峰3,263,008,768B不作为D066模块峰。swap0/GPU0、5GB/40GB及32/36GB守卫不变，8765进度窗口保留实际任务与扫描时间。

D065原经济结果不变：完整10k、303开发日，ACTIVE_EQUAL相对EQUAL净多67.62–88.34USDT，但BASE/F波动8.18%→9.91%、换手3.01→4.76；研究挑战者保留，HOLD_TWO仍收益主参照，投资NONE/CASH、长期APR不可评价。代理场所/资金费单位UNKNOWN与独立市场证据不足仍阻止投资晋级。

下一项有限科学对照拟保持prior20入场/SMA200、池、风险、成本与资本，只把退出通道从20日改10日。问题是更早退出能否减少主要毛亏，而非删成本或挑币。尚未冻结新协议、未运行、无后台科学任务；不把它设永久路线。

## 工件与只读复现

五份实际报告为 `reports/PUBLIC_COLLECTOR_{PRESERVATION,MANIFEST_IDENTITIES,RESTORE_LAUNCH,RESTORE_SAMPLE1,RESTORE_SAMPLE2}_20261004_V1.json`；来源helpers和五closed0/两running时点任务副本位于 `docs/archive/PUBLIC_COLLECTOR_*`。原始数据库/日志不入Git。registry为真实事后OPERATIONAL_RESULT，不伪造事前科研START。

当前状态只读检查，在hpc_linux、项目目录执行：

```bash
scripts/with_task_progress.sh --title '原公开分钟采集当前状态' -- .venv/bin/python -m quant.collector_public_v3
scripts/with_task_progress.sh --title '原L1当前状态' -- .venv/bin/python -m quant.microstructure
```

上述不含`--run`，不再次启动。保存/身份/单次launch helper是当时证据源码，其排他输出与现有进程检查会拒绝重用；禁止为复现而覆盖原报告或重启。模块正常Git同步只据后验 `GITHUB_PUBLIC_COLLECTOR_RESTORE_SYNC_VERIFIED_20261004_V1.json`，提交前不预造push成功。
