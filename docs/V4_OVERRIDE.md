# v4 增量纠偏登记

用户于2026-10-01明确选择“按新审计执行”。原附件逐字节复制为根目录
`CODEX_AUDIT_AND_NEXT_PLAN_2026-10-01.md`，SHA256
`6845cf09cd21c9258d7e446e42327adc3b3864d699935915fc936f06fb664b91`。
审计依据远程旧HEAD `3b0f470c`；当前本地已另外完成A07诊断和异常凭证工程，
逐份验收仍有效，不反向改写。

新审计仅覆盖冲突部分，保持已有执行合同、小时研究STOP_v2、锁定历史封存和旧
v1来源/数据/验收不变。主线转到A09→A10→A11，再按真实14/30/60天阶段推进。

## 当前执行

- A09：独立`microstructure_l1_v2`模块、数据库和store。以`f/l`原始成交范围判断缺口；
  `a`跳号单独审计。新增末端spread/depth两个字段；原v1保持QA证据。
- A10：独立归一化视图，5s输入、每币因果EWM half-life1h；先用过去状态输出，再更新。
- A11：A09工程/真实短测及来源验收后切换v2长期采集，v1不拼接新版本资格。
  切换前保存v1终态/partial资源链，旧24h窗口不假称完成。
- A12：真实有效14天后只做DIAGNOSTIC_ONLY。
- A13：30天固定三模型Pilot，仅PROMISING/NOT_PROMISING，不产生alpha候选。
- A14：至少60个真实UTC日，预登记14d/7d/7d、5m embargo、至少6完整OOS fold，
  执行型ask/bid标签、33bp固定阈值、固定风险与M2 Gate。
- A15：只有正式Gate通过才冻结唯一候选；未来记录从冻结后开始。留出需另获明确授权。
- A16：L5及maker分支仅满足审计各自条件后另立研究，当前不实现。

全部项目磁盘≤40GB（整个项目＋整个D盘WSL VHD），合计RAM≤5GB/swap0，无GPU。
Candidate启动前联合容量必须expected≤32GB、stress≤36GB、hard≤40GB，包含1GB临时预算。
不扩执行层，不消费留出，不启用真钱；仅每完成工单并验收、文档修缮后提交和推送。

## 证据边界

官方接口当前定义`a/f/l`，未把`a+1`连续写成合同；参见
[Binance Spot Market Streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams)。
新版本仍按实际收到的编号与缺口审计，不能承诺网络绝不丢失或收益必达。
旧finally断开原因模糊，不能仅凭时间恢复健康秒。

先前额外数据证据解释consumer草稿停止扩展，协议和草稿原字节保留为未验收WIP；
没有测试/实际运行或资格。这项停止对应新审计“少写基础设施、优先A09”的要求。
已闭合诊断和异常凭证工程继续保留，但不授予新v2时间证据。
