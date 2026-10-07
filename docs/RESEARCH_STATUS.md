# COIN 当前研究状态

## 当前结论与投资资格

**NONE/CASH；长期稳定净 APR：NOT_EVALUABLE。** SHORT 保持主要研究方向，但目前没有经独立证据确认的多币投资候选。N 资产共享账户、signed 多空/现金、逐仓资金与风险能力保留；API 对接尚未推进到真实账户。

2026-10-08 已接上实际服务器。原本机 e17e113 状态落后；已读取服务器活动任务、实际分支与结果，从完成专家组合的 **5346a5c** 继续。没有重复 28 账户回放或 Transformer 拟合，也没有覆盖服务器另一份未提交报告测试。

## 本版实际改变：SHORT 路由诊断与广度机制完成

事前冻结的 leave-one-out 广度检验已完成。自身 SMA200/SMA50 皆负时，其他币多数下跌组未来30日空头价格成本代理均值−6.15%，多数上涨/持平组+6.78%；差−12.92个百分点，五项门槛全失败。49个固定市场块，符合自身条件25块；主要2022熊市缺足够已预热同伴，不能泛化否定SHORT。不是钱包收益、未含资金费或真实执行。实际0.259秒/RSS86.82MB，零拟合/零新账户。见 [机制结果与停止决定](../reports/SHORT_BREADTH_PROBE_20261008.md)。

新脚本只读核验旧 28 账户、资金费与 SHORT episodes；**零新模型、零新账户、零搜参**。112 份工件 SHA 和输入缓存绑定通过，独立 Decimal 现金桥最大误差 3.18e−12 USDT，三项手算/归属测试通过，独立只读复核通过。服务器实际计算 0.746 秒，单进程峰值 RSS 92.54MB；2 线程、8GB 限制、swap0/GPU0。

[本版经济解释与决定](../reports/SHORT_ROUTING_DIAGNOSIS_20261008.md)；[实际结果](../reports/SHORT_ROUTING_DIAGNOSIS_20261008.json)；[运行前协议](../protocols/SHORT_ROUTING_DIAGNOSIS_20261008.json)。本轮无新投资收益，旧结果不改。

## 钱赚在哪里、亏在哪里

2023 年完整 365 日、独立 10k 共享钱包、两条件资金费解释：

- FAMILY_EW 净 +749.20 / +859.62 USDT，全部来自 LONG，实际 SHORT 成交 0。冻结 prior 的 HOLD 权重会抵消六个趋势的负仓位；两种解释全部 730 日包络验证。结论不推广到动态权重或 N 资产系统。
- FixedShare 净 +762.98 / +904.09，也没有 SHORT。比 EW 仅多 13.78 / 44.47，同时提高 gross、波动和回撤；旧登记门槛失败。
- HEDGE 净 +239.54 / +399.45，SHORT 净 −274.47 / −253.60；三个空头 episode 均亏，年初反弹占空头亏损约 61%。毛价格亏损 −266.60 / −243.12，主要问题是方向而非费用。
- SMA200_SIGNED 的 SHORT 净 −830.52 / −845.80，但它在旧熊市证据中有盈利能力。三个反弹年事件不能证明 SHORT 没有 alpha。

固定 60 日、含切换成本的旧收益 shadow Oracle：加入 signed expert 相对 HOLD/CASH 的机会增量在 2022 为 +2049.48 / +1985.12，2023 只有 +0.05 / +0.07；2023 winner 中没有负目标日。该结果为非因果重定基诊断，**不是新共享钱包或纯 SHORT alpha**。大总 Oracle gap 不足以证明可预测的空头机会。

## 采用、暂停与下一主任务

保留 FAMILY_EW 作为 low-exposure long/cash 参照、公开 signed 趋势为方向参照、CASH/HOLD 为控制；不晋级任何方案。暂停当前 Hedge/FixedShare 配方的参数搜索及更复杂 ML selector，不降低 SHORT 优先级。

下一主任务：**固定公开三周横截面动量：做多相对强币、做空相对弱币**。先注册论文方法的等权K2永续适配、两个已见开发窗口和真实成本比较，复用既有排序/协方差/共享钱包与旧控制。无拟合、无周期扫描；不把失败的广度方向取反。新钱包尚未运行；下一模块 NOT_RUN，无后台训练。

暂停广度过滤配方；reopen需覆盖主要熊市且有新的过去可得信息与独立重复。用户要求优先高价值方向：停止围绕同一失效过滤器兜圈，选择有公开依据且能在有限真实账户里改变投资判断的收益来源。

reopen：Hedge/FixedShare 需要跨阶段稳定的成熟反馈优势或已验证投影瓶颈；ML selector 需要方向/排名超过强静态与 placebo。若方向信息不足，保留强公开策略并暂停新 controller 拟合。D106 人工 map 失败与全部旧负结果保留，不重复包装为新实验。

## 既有实际结果入口

- [28 钱包专家组合](../reports/expert_aggregation/REPORT.md)：STATIC_EDGE_ONLY，全部收费平仓及独立验收完成。
- [Transformer v3 最终报告](../reports/transformer_v3/TRANSFORMER_V3_FINAL_REPORT.md)：开发不晋级，保留已发布有限假设结果；本轮未访问原始封存输入或重跑。
- [Transformer v2](../reports/transformer_v2/TRANSFORMER_V2_FINAL_REPORT.md)及[归档模型完整窗口验证](../reports/COLLECTOR_COMPLETE_WINDOWS_20261007.md)：失败/不可评价范围保留。
- [D108 ML selector](../reports/SELECTOR_ML_REPORT.md)：LINEAR_H60 未胜强 HOLD，2023 SHORT 拖累；旧本机计划 D043 迁移核对本轮被最新服务器证据取代，未执行重复实验。

## 数据、产品、资金与资源

BTC 2022/2023 与已研究多币历史仍为 seen development；不重新命名 OOS，不拼接独立钱包。Binance USD-M 数据配 Bybit 费用是跨场所代理；资金费单位、历史费用与原生风险档位未认证，条件解释不能冒充原生 Bybit。完整资本 10k、单币绝对 30%/组合 gross60%、1x 单向逐仓、无自动追加保证金保持。

本会话按 8GB、swap0/GPU0 控制新研究；本机项目+整个 D 盘 WSL VHD 150GB，120预警/135停止新增/15预留。实际扫描时间与新工件增长见本版关闭证据，不用旧扫描冒充当前。无账户密钥读取、交易所发单、付费或新封存权限。

## 运维与真实任务

8765 服务已恢复，沿用现有窗口。本机 WSL 原采集进程缺失后先保存 39 份工件/闭合备份，再按原身份/原 5GB 子组恢复；见 SELECTOR_TRANSFER_COLLECTOR_PRESERVED_20261008.json 与 SELECTOR_TRANSFER_COLLECTORS_RESTORED_20261008.json。采集进程存活不等于连接正常：本轮连接采样失败，未证实新事件推进，退出与断档原因 UNKNOWN。该问题不改变已独立核验的离线历史结果，也不宣称连续健康数据。

科学诊断与测试已结束；没有后台模型训练。普通下一模块自主选择，扩资金、风险、资源或启封权限仍须用户明确授权。
