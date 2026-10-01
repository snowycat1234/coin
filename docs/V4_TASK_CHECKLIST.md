# v4 长目标清单与当前工单

更新2026-10-01。总目标持续进行；v3旧64项/57项证据保留，不能作为新v2进度或盈利概率。
本清单已由用户直接指定的v6优先级覆盖，当前见`FAST_RESEARCH_TASK_CHECKLIST.md`。
A09/A10工程已验收并保留，A11切换未启动；执行/观察器新工程冻结。
当前22/45项有旧阶段工程证据；计数不是盈利概率或总项目完成率。容量资格未通过。

## 前置与纪律

- [x] 01 保存新审计原字节及SHA
- [x] 02 用户明确采纳v4并登记增量override
- [x] 03 保留小时研究STOP_v2，不追加参数或降成本
- [x] 04 保持旧v1/验收/故障/数据来源不可变
- [x] 05 核对官方a/f/l和bookTicker字段定义
- [x] 06 GitHub登录及初次模块检查点远程一致性核验
- [ ] 07 新完成模块提交/推送并核对远程一致性（持续）

## A09 正确性与v2 schema

- [x] 08 新模块、版本、原生库和store隔离
- [x] 09 f/l整数范围验证与真实raw范围缺口审计
- [x] 10 a跳号且raw连续仅记未确认跳号
- [x] 11 duplicate/overlap/out-of-order不重复计量、高水位不回退
- [x] 12 重启保存与恢复raw high-water和来源
- [x] 13 同一末端BBO的spread/depth/imbalance/mid可重构
- [x] 14 carried/stale及5/30/60聚合末态一致
- [x] 15 原资源/持久性/单写者/导出边界保持
- [x] 16 隔离合成回归、真实公开短测及正确性最终验收；容量失败如实保留，24h容量仍待项28/29

A09凭证 `reports/A09_MICROSTRUCTURE_V2_ACCEPTANCE_20261001.json`：79项通过，
90秒短测实际11,579事件；180d合成高熵投影9,076,725,216B，超过8GB特征子预算。
只授予v2公开数据资格采集范围；不授予24h/14/30/60d容量、质量或alpha资格。

## A10 因果归一化

- [x] 17 固定派生输入、输出、epsilon及无效/空值规则
- [x] 18 每symbol独立EWM half-life3600s
- [x] 19 当前z-score只用过去状态，随后更新
- [x] 20 batch/incremental同源逐元素一致
- [x] 21 symbol交错、时间单调与状态恢复验收
- [x] 22 实际v2已导出样本只做描述性验证
- [ ] 23 模块最终验收、文档完成；普通推送待核验

A10正式凭证 `reports/A10_MICRO_FEATURES_V2_ACCEPTANCE_20261001.json`：46项通过，
36行实际v2样本batch/incremental/JSON恢复完全一致；真实warmup-ready=0如实保留。

## A11 v2真实资格重计时

- [ ] 24 保存v1停机终态/原库/来源和部分资源窗口
- [ ] 25 v2来源验收绑定的独立启动器
- [ ] 26 新会话实际接收、同进程跨调用存活核验
- [ ] 27 新版只读质量/资源报告的schema与来源绑定
- [ ] 28 实际24h无silent gap、存储投影与schema稳定性报告
- [ ] 29 raw24h/4GB、180d特征8GB、native/整盘增长独立验收

## A12/A13/A14 真实时间研究门槛

- [ ] 30 足额真实有效14天数据，QA/stationarity/单变量及衰减DIAGNOSTIC_ONLY
- [ ] 31 足额30天，只固定Ridge/一LGB/一XGB及30s/300s Pilot
- [ ] 32 Pilot仅方向结论，不冻结alpha，不追加搜索
- [ ] 33 >=60真实UTC日，先冻结正式协议及不可重跑预算
- [ ] 34 14d训练/7d测试/7d stride/5m embargo，>=6完整OOS fold
- [ ] 35 可成交标签：decision+1s ask、300s后bid、>2s等待即INVALID_LABEL
- [ ] 36 固定费用/滑点、安全垫及33bp阈值；成本压力与财务归因
- [ ] 37 固定long/flat、5m hold、不重叠、单币30%/gross60% NAV
- [ ] 38 M2全部门槛独立复核；三模型均失败即STOP_MICRO_L1

## A15/A16 候选与条件分支

- [ ] 39 只有A14通过冻结一个候选版本
- [ ] 40 候选启动前联合容量expected≤32GB/stress≤36GB/hard≤40GB及1GBtemp
- [ ] 41 锁定历史另获用户明确授权，仍不可自动启封
- [ ] 42 真正候选未来数据从freeze后累计，不回填研发期数据
- [ ] 43 真正竞争性前向与长期测试环境门槛逐阶段验收
- [ ] 44 A14后才按条件审查compact L5或独立maker feasibility
- [ ] 45 最终风险复核与单独资金授权；当前真钱未授权

14/30/60天必须按实际版本证据，不拼v1、不用历史回放替代，不以calendar标签补有效秒。
