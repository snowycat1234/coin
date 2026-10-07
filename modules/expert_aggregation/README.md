# BTC 因果专家组合

用户提供的两份2026-10-07计划指导本有限模块。先登记完整脚本再执行：复用8个BTC连续专家的旧目标和净反馈，只让Hedge/FixedShare进入分钟确认，EWMA只诊断，无GPU训练。2022仅训练，2023独立10k同钱包，共28个账户；既有已见历史不能恢复成fresh OOS。参数、费用、预算与停止条件见[protocol.json](protocol.json)。

依次完成工程反例、只读字节迁移、共享只读缓存、冻结目标、逐分钟并行钱包/独立审计、研究报告与第二轮证据门槛。复用既有Decimal隔离钱包、调度器、目标混合、过去协方差验算和独立审计；没有另写资金会计或改写旧报告。

在已部署的Ubuntu服务器启动及查看：

```bash
bash /home/ubuntu/coin/run_expert_aggregation.sh
bash /home/ubuntu/coin/watch_expert_aggregation.sh
# 单次状态
bash /home/ubuntu/coin/run_expert_aggregation.sh --status
```

后台systemd用户服务与SSH/客户端生命周期分离；不设置CPU/RAM额度，默认8个账户进程以共享memmap利用10核服务器，实际磁盘保留15GiB。科学任务禁止在用户本机执行。运行目录默认`/home/ubuntu/coin/execution-state/expert-aggregation-v1-20261007`；查看完整异常为`FAILURE.json`，逐模块日志为`service.log`。重跑会校验源码及工件身份、复用已审计账户，保留中断的尝试目录；不会重新训练或重跑前置v3任务。

输入迁移须预先提供`reuse/RELOCATION_INDEX.json`及其列出的字节原件。本次从旧WSL仅迁移原始accepted清单的84份行情/资金费/暖身文件、原receipt和32份专家目标/日账本；索引保留旧绝对路径、SHA与原producer作用范围，不伪造旧机器任务完成凭据。实验自动交叉核验原manifest与expert report的SHA/bytes。

`delivery/REPORT.md`、`RESULTS.json`、`RESULTS.csv`、`NAV.png`为最终轻量交付。完整cache/分钟钱包留服务器；新路径索引与源码/协议绑定可复现。第二轮仅由登记的明确投影瓶颈触发，不为证明routing有效而追加池或模型。长期投资资格仍为NONE/CASH。
