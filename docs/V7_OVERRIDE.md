# 当前最高科研指令：v7 自主科研

用户于2026-10-02明确要求立即执行
`CODEX_AUTONOMOUS_RESEARCH_DIRECTIVE_v7_2026-10-02.md`。原附件按字节保存在根目录，
登记SHA见本次原文登记凭证。v7优先于此前v6/v4的冲突部分。

最终目标是扣除全部真实成本、统一风险预算下的长期净几何APR/CAGR。
IC、Sharpe、工程清单只是诊断；短窗口年化、oracle和研究proxy都不能成为生产结论。

自主执行普通科研决策，重大变化仅写短`RESEARCH_DECISION_LOG.md`。保留原冻结证据、
ExecutionContractV2/FrozenPredictor/STOP_v2/A07/holdout和开源组件；不覆盖旧报告。
保留40GB磁盘边界。v7授权RAM上限为8GB；目前仍使用原共享5GB硬限，尚未扩大。
GPU按实际可用性和周转价值决定；尚未启用。锁定测试、真钱/发单、账户密钥、
新付费服务、超过40GB/8GB、破坏冻结证据仍须明确授权。

不再以180日齐档作为oracle、horizon诊断和三个未看结果OOS fold筛选的启动条件。
历史获取优先官方monthly URL/格式/CHECKSUM与流式转换，保留已接受daily证据。
新来源/标签/预测实验另建版本；所有模型使用同一研究数据合同和经济合同。

当前预算60%深化flow→impact/horizon/经济映射，20%相邻OOF/残差/适应，20%frontier。
先执行oracle未来flow→return的5/15/30/60m机制诊断，然后按结果选下一项实验。
旧固定首轮与排行榜证据保留；新筛选不按旧IC总榜自动淘汰整族或机械跑完所有配置。
River-1作为具体配置退役；adaptive能力保留。暂停路线必须有可检查的reopen condition。

每阶段先汇报候选、净APR证据、阻碍、发现、下一实验理由、暂停/重开条件。
所有长脚本仍通过`with_task_progress.sh`，仅完成并验收模块后提交推送GitHub。
