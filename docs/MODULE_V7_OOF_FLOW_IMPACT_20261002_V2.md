# v7 OOF flow→impact：开发机制诊断

## APR、阻碍与结论

**当前无合格长期净APR候选。** 已查看July开发窗口中，15m DIRECT七天条件
净收益+0.0335%，仅3次往返；不能据此年化认定候选或继续筛阈值。
当前两阶段没有改善matched DIRECT；关键障碍是可预测flow经过impact映射后
只剩小于成本的毛edge，且较长horizon的Perp-flow预测更弱。

| 周期 | DIRECT七天净收益 | OOF两阶段七天净收益 | 两阶段往返 | 两阶段break-even往返成本 |
|---|---:|---:|---:|---:|
| 5m | 0，无交易 | 0，无交易 | 0 | 不适用 |
| 15m | +0.0335% | −0.4221% | 6 | 1.79bp |
| 30m | −1.4676% | −2.0994% | 26 | 1.65bp |
| 60m | −5.2729% | −5.8463% | 99 | 5.43bp |

表为原30bp成本情景：20bp fee＋8bp slippage＋2bp假设spread；4/8bp
spread敏感性另留完整账本。未降成本、改35bp阈值、加杠杆或启用真钱。
每次新买单原30%单币/60%总持仓风险预算保持，期末平仓和因果NAV真实核对。

M1测试Perp BTC flow Pearson 5/15/30/60m约 .186/.111/.088/.0003；
Perp ETH约 .092/.022/.066/−.014。强未来flow oracle关联尚未被历史输入转化
为有效预测。两阶段M2也受到早期3/6/9日OOF模型与最终12日模型输入分布差异影响。
这不是“不存在flow信息”或“某模型族永久无用”的结论。

零fit组件诊断进一步发现：SpotBTC5/15m的预测flow自身IC .177/.176，预测
组件与同资产return Pearson仅−.0034/.0054；真实futureflow对应 .492/.516。
价格关系大部分仍在相对当前M1的未来误差中。不能把该误差当可用预测输入，也
不能称作已识别的结构因果创新；它说明仅增加flow IC未必改善APR。
因此下阶段要同时检查预测组件的price relevance、直接return、真实成本与
模型间残差独立性。DIRECT15m在32/36bp压力下七天净+0.0155%/−0.0205%，余量不足。

## 共同实验与实际证据

只使用原oracle共同frame、相同train/validation/test及5/15/30/60m标签。
M1以原past256的204统计特征＋6个closed past-state预测四流；M2只接
严格chronological OOF预测flow＋相同past-state。DIRECT与M2使用同一
8,607拟合行、相同past-state scaler/return scaler；共同测试9,281端点。
三个expanding OOF块Jul4..<7、Jul7..<10、Jul10..<13，所有M1拟合标签
必须在该块开始前满足最大3610s成熟及3600s embargo。没有in-sample flow注入M2。

一个固定XGB-S配方、24个拟合调用（多输出），130.91秒，进程RSS551.55MB，
共享原5GB硬限/swap0/GPU0。每个模型、scaler、原单位预测、索引、来源与账本
留在独占STATE v2，不入库真实模型/行情。

必要核验：24保存模型全预测精确复现；6个原past204/state窗口探针；全部
输入/目标scaler及4个OOF-flow scaler官方参数与拟合行来源精确核对；24个
费用/滑点/spread情景现金、持仓、原价NAV、换手、MDD和期末平仓核算通过。
没有为核验重拟合模型。主数值凭证
`V7_OOF_FLOW_IMPACT_CORRECTNESS_20261002_V2.json` 与独立语义review
`V7_OOF_SEMANTIC_READ_ONLY_REVIEW_20261002_V1.json` 分别保留。

## 报告口径与失败留证

主报告 `V7_OOF_FLOW_IMPACT_20261002_V2.json` 的M1 flow统计误用了通用
`signed_return_mean_bps`字段名：该字段实际为signed flow imbalance×10000，
**不能解释为收益bp/edge**。独立单位addendum纠正解释，原报告不覆盖；财务表
使用真实price-return及账本，未受该字段影响。新实验必须区分flow与return单位。

首次OOF目录父路径缺失在fit前失败，真实fits=0；修复后独立v2重跑。
核验器两次失败分别为手写float64运算不遵循官方StandardScaler float32路径、
把旧账本单个observed price误作tuple；均留旧源与退出日志，只修核验器，
不放宽容差、不改科学源码/模型/原报告。

所有结果仍受共同future-valid筛选约束，不能作为在线过滤器；单一已查看7日
regime不足以推断长期净APR，缺BBO、真实冲击、实际账户费率/永续funding。
没有locked消费、发单、模型候选冻结或未来资格。

## 下一实验价值与暂停条件

优先对三个预登记unseen时间段做有限模型族比较，检验是否是当前统计表示/
模型容量损失，或flow信息跨regime不稳定；新配置在查看首fold结果前固定。
具体已冻结5/15m×Ridge/XGB-S/TCN-S六recipe、1seed，统一四flow＋两Spot return
primary、共同past256＋state6信息/归一化，成熟910s/embargo900s。协议为
`research_v7_family_screen_20261002_v1.json`，开始A后B/C沿相同配方继续。
并行核对Spot与USD-M经济映射，禁止给Spot-return套较低永续费率冒充结果。
暂缓长horizon两阶段调参；若unseen的M1/残差信息及扣费结果改善，或新的
历史状态/信息源提供独立增益再重开。保留flow、adaptive、representation和LOB能力。
