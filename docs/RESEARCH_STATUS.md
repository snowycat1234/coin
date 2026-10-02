# COIN — 当前权威科研状态（2026-10-02）

**目标：risk-constrained net CAGR。候选：NONE / NO_QUALIFIED_CANDIDATE。**

1. **成本前／后证据**：旧14日XGB proxy净−0.1591%；July开发15m DIRECT
   仅3往返、七天净+0.0335%，36bp压力为负。这些均SCREENING，不能年化作长期证据。
2. **最强基准增量**：尚未运行共同风险基准套件，NOT_EVALUABLE；单独净正不能晋级。
3. **平衡成本**：旧30/60m DIRECT约5.34/8.31bp，低于原30bp现实情景。
   15m约33.72bp但交易过少；现货结果不能换永续费率重新命名。
4. **校正统计**：全量旧工件已开始只追加登记，未知运行元数据保留UNKNOWN。
   工件数不是独立试验数；DSR/PBO/CSCV/SPA、有效区块bootstrap目前NOT_EVALUABLE。
5. **最大失败模式**：同窗口flow/return重叠，预测flow的价格相关信息弱，真实成本、
   收益集中度和独立可成交价格证据不足。旧oracle改称SAME_WINDOW_IMPACT_DIAGNOSTIC。
6. **集中度**：旧15m仅3笔，不足以支持稳定性；新V8四时间段尚未运行。
7. **数据／执行限制**：Jul1至Nov1前123日四流492档已只读来源验收；≤180天仅SCREENING。
   BBO/depth/mark/margin/适用历史费率不足时不得申请执行、carry或maker资格。
8. **下一最高信息增益实验**：非重叠5m→5m与150s→150s、5/10s gap、严格OOF
   FLOW_SURPRISE，对同端点direct及risk-matched基准；只用固定线性/树模型。
   四段预登记为Aug20–27、Sep25–Oct02、Oct24–31、Nov18–25；November四流官方来源
   正串行获取／校验，未完成独立QA前仍不计入共同来源。
9. **gate**：P1 NOT_READY，标签实施不等于经济／统计通过。P1失败时暂停交易流方向，
   仅真实L1/L5/BBO增量信息或carry/basis/慢速组合可重开。TCN及深度族继续暂停。
10. **执行状态**：旧V7队列已留证停止；A六配方、B两配方保留且无V8资格。
    不消费locked、无真钱／密钥／GPU；仍共用5GB RAM、swap0、D盘40GB上限。

## 本轮已完成与待验收

- V8原文精确留存，AGENTS优先级及决策日志登记。
- 标签V1／V2均已隔离：V2修复了首轮反例，但独立复审确认导出／split入口
  可接受锁定日期的合成时间戳，另有数组广播、时戳截断及flow单位缺口。没有读取真实holdout。
  第三版已通过预绑定源码的clean检查，独立复审待完成；此前绿色检查不代替反例验收。
- 八基准及三成本合同已写，未实现策略明确PENDING，carry/maker NOT_EVALUABLE。
- 旧队列146件工件SHA留存，无删除或覆盖；执行污染史如实登记。
- 统一完整CPU依赖锁及独立clean环境／合成artifact跨进程精确复现已验收。
  只追加登记机制及旧621工件记录前缀已验收；全历史trial元数据仍不完整，不能作统计通过。
  原D盘Windows缓存rename失败、并行扫描临时目录消失均留证；复测采用D盘WSL
  native cache且锁字节不变，未改磁盘守卫。完整研究集成／费用和不可能成交mutation仍待验收。
- 478共同特征已一次固定，复用原68特征与官方统计函数；独立审计发现已交易条缺失价格／
  成交大小会被原fill-null转换静默补零，前两版守卫保留拒用；第三版只增强primitive守卫，
  不改冻结特征定义或合法未定义观测mask。验收／复审完成前不拟合行情。
  八基准固定信号适配进行中，实际策略经济回放仍PENDING，不把target输出当净收益证据。
- 8765窗口已恢复、显示实际进度；保持WSL连接与原viewer恢复分别有实际凭证。
  显式WSL关闭/Windows重启仍会中断，时钟事件如实留证，新会话不拼接健康时间。

窗口：[本机任务进度](http://localhost:8765/)。最近完整容量扫描18.740GB，实际
北京时间16:52:40，另预留4.970GB仍在界限内，非当前瞬时值。动态RAM和任务计数以窗口时间戳为准。

已验收的窗口／123日来源／venue模块已推送，远程精确提交
`d46e2ad5545773b5c3735ba237fd2fce14349f21`。后续只在模块验收与文档修缮后推送。

历史状态文档保留，不继续同步多套进度；当前状态读本页，选择理由读只追加
`RESEARCH_DECISION_LOG.md`，实际运行读 `../reports/experiment_registry.jsonl`。
