# 固定Donchian 2h入场 / 1h退出 · 2026-10-02

## 当前范围

已接受**合成目标与因果处理**；尚未运行经济账本，净收益、长期APR与Candidate资格均未证明。唯一策略ID为`COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER`。这是固定机制challenger，不新增参数搜索或平台。

## 规则与开源复用

[薄适配器](../scripts/investment/public_donchian_hybrid.py)直接调用冻结169d的`closed_hours`与`_load_public_hooks`，复用原MIT Jesse Donchian策略/指标，不重写channel、SMA或交易规则。原169d字节未变；upstream pin与许可证沿[既有登记](../third_party/jesse_example_donchian/UPSTREAM.md)。COIN负责共同TargetPlan、账户风险和代理执行，不能称原Jesse平台收益复现。

- **入场**：仅在新闭合2h bar、当前flat时，原`should_long`要求close严格大于前20个2h bar的upper；原filter同时要求close>SMA200。
- **退出**：held时，仅在新闭合1h bar调用原`update_position`，close严格低于前20个1h bar的lower则退出。SMA只用于入口，不新增SMA退出规则。
- **同刻优先**：held先判断退出，退出后禁止该刻再次入场。下一根新闭合2h bar立即恢复入场资格；没有额外cooldown，不在中间分钟补做旧入口。
- 每币目标权重仅0或0.30，复用共同资金/风险/时延意图接口；目标不是实际持仓或fill。

出口从20×2h=40h回看改成20×1h=20h，同时检查频率2h→1h。因此是**联合退出时间尺度诊断，不是纯退出时延的因果识别**；不能把结果自动归因于“快退出”。

## 闭合、availability与完整fold

每个决策要求200个连续、完整、当时已available的2h bar，并要求200个同条件1h bar。1h的200 bar只是共同warmup守卫，出口规则仍是前20个bar。整分钟/两币日历沿既有验证；未完成分钟不进入信号聚合，不填补缺bar、未知availability或无效分钟。

缺失/延迟/invalid使整个paired fold不可经济评估，不能以某段有效信号继续计算可比收益。这个hybrid保留已产生的因果历史targets，后续断档不反向把过去全部清零；失败处理差异写入receipt，**旧169d不修改**。未知availability直接拒绝。接口使用者必须先守住`paired_comparison_allowed`。

最后一刻权重0沿既有预先terminal政策，明确是待执行退出意图；仍需要真实可行、付费的fill。不能据此假定期末已清仓或补免费卖出。

## 已有合成验收与绑定

[唯一tiny凭证](../reports/fast_research/PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1.json)由同一原任务/JUnit归档，未重跑绿色测试：真实session92586退出0，task`369681b4d20d4a3eb6219421adc45faa`完成0；7 tests、0 failures/errors/skips，JUnit49.343s，任务63.119s。

7项覆盖原hooks入口/退出、同刻冲突与下一事件恢复、未来OHLC扰动/未完成分钟、未来missing/delayed/invalid保留过去targets、初始warmup及null availability拒绝。仅内存合成输入，没有市场文件、来源QA、fit、locked或发单。原测试RSS未捕获，保持UNKNOWN；WSL共享5GB/swap0/无GPU。

| 凭证 | SHA256 |
| --- | --- |
| adapter | `80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68` |
| [tests](../tests/test_public_donchian_hybrid.py) | `43f75ddce8301962638a4b215b00486e1e79b1925423af47643b5e5ac82ffdc5` |
| tiny receipt | `32086aa3f4d1e331da1dc4f3e1f242b433500690a65e53d98f08b6eeb534a808` |

原JUnit、task和MIT字节SHA均在receipt中精确绑定；[归档操作源码](archive/PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_RECEIPT_SOURCE_20261002_V1.py)SHA`9d295474…`，只核元数据，不重复执行测试。

## 下一项

在已验收Bybit费用/资产和共同engine内，与固定1h、2h在同日期、资本、风险约束与成本情景对照。只运行这个配置，不调阈值、不做HPO、不降费或增加杠杆。重点判别gross是否恢复、额外成本是否抵消改善，以及月度负尾/分钟回撤/实际暴露；共同约束不等于相同实际风险。当前没有经济结果，不预选盈利结论。
