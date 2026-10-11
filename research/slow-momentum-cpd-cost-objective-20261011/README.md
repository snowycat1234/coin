# 成本目标执行：真实日历预检阻塞，未拟合

用户已批准执行8ae13d1d中的唯一冻结方案。已完成训练日历、完整价格成本目标、
分块输出VJP及独立Decimal/模型读回审计实现；**31项数学/反例测试PASS**。
随后真实日历预检失败，严格按冻结STOP结束；没有科学模型初始化、训练、
历史LSTM预测、验证导出或钱包。本项成本假设尚未检验，不能报告经济成功/失败。

| 真实训练预检 | 结果 |
|---|---|
| 严格成熟连续日历 | 729日 |
| 当时输入/vol可用的因果端点 | 2528 |
| 原未来标签完整的监督端点 | 2526，原SHA983baa27保持 |
| 缺失收益决策 | SOL/XRP，2022-02-26 00:00 UTC |
| 缺失标签结束 | 2022-02-27 00:00 UTC |
| 原档案证据 | 两币raw dt2022-02-26至28均closeNULL/complete_klinefalse |

原bar的可用时间为dt+1day。两个缺口决策的63日输入及当前vol有限，但下一日
价格收益未知。[因果诊断](prefit/CALENDAR_FAILURE_DIAGNOSTIC.json) 和
[原成员SHA/原始行](prefit/RAW_SOURCE_GAP.json) 证实是数据缺口，不是时钟或VJP错误。
旧sample_index因未来标签缺失排除两行；这适用于其监督样本完整性，不能替代
完整交易成本路径的因果mask。冻结方案明确要求缺失收益即停、同2526轴身份；
两条件在此档案上不兼容。没有补零、前填、按未来标签置现金、改日期/源SHA/端点。

[最终配置](CONFIG.json) SHA `58cdef3f429187b9486515ecb2859356f3c005432a1f3616cff4dfa9d21e7793`
逐个绑定最终源码；金融/64步/六fresh/种子/预算均未修改。固定BASE27系数1，
entry/drift/mask/paidterminal；训练全路径输出VJP与全自动微分/损失有限差分一致。
现金/零方差不可成功，训练终端INVALID按STOP；最终所有所需评分必须有效。
near-cash只作披露/禁止成功，不引入策略dead-zone或损失变更。

只读审阅修复：真实optimizer返回即计步后检查有限性；审计核源vol/label/边界及
独立增量/门槛/现金/决定，包含篡改拒绝反例。原数据预检失败和rawsource只读
过滤器literal设置失败各一次，后者修复后确认缺口；记录/早期测试均保留。
没有科学训练重试。[完整预检状态](PREFIT_STATUS.json)；[最终31测试](prefit/TESTS_FINAL_RELEASE.xml)。
旧185文件/4fit源码/12旧模型及额外24份诊断交付字节保持。
科学训练累计仍3尝试/12freshfit/13824updates，拟议尝试4未开始。
六64拟合/最终验证/独立实绩审计NOT_RUN，实际资金费/native/netProfit/APR UNKNOWN。
collector2026Mar–Sep锁、不可访问2026Q1/Q2账本和另一研究均未动。

复现数学测试与预检（后者应以eligible missing return退出1；先按原公开特征
恢复步骤取得相同2.2MB档案，不需要旧模型，禁止自动下载其他行情）：

```bash
COIN_CPD_STATE=/workspace/slow-momentum-cost-check bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python -m pytest modules/slow_momentum_cpd/test_cost_training.py \
  modules/slow_momentum_cpd/test_objective_diagnostic.py modules/slow_momentum_cpd/test_cost_feasibility.py \
  --basetemp=/workspace/slow-momentum-cost-check/pytest -q
COIN_CPD_STATE=/workspace/slow-momentum-cost-check bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.cost_training check \
  --state /workspace/slow-momentum-cost-check \
  --config-sha 58cdef3f429187b9486515ecb2859356f3c005432a1f3616cff4dfa9d21e7793
```

在当前冻结输入下保持PREFIT_DATA_BLOCKED。没有新实验、搜参或重开旧gross配方；
若将来恢复数据/改变端点身份，须另行核对，不能计作本次已经训练。
