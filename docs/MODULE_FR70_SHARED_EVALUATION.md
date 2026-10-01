# FR70：共同预测指标与条件性价格代理评价

状态：实现与独立工程测试，等待根侧模块验收；尚无正式首轮排行榜或top-3结论。
依据已登记v6协议，历史180共同完整日、六个事前固定OOS fold尚未齐备。
实现为`src/quant/research_fast/evaluation.py`；测试为
`tests/test_fast_research_evaluation.py`。既有dataset、labels、协议、registry、
daily metrics、旧backtest源码未修改。无真钱、locked读取、GPU或execution扩建。

## 复用与共同绑定

复用既有登记的SciPy 1.18.1（BSD-3-Clause）`pearsonr/spearmanr`，
`quant.metrics.daily_metrics`计算UTC日度Sharpe及MDD；不重新实现相关系数或
统计年化。Polars承接原有共同数据/标签列。代码只有研究政策与会计薄adapter，
没有订单、撮合、交易所客户端或execution框架。上述第三方库零修改。

`EvaluationBatch.from_dataset(dataset, indices, fold=fold)`要求indices精确等于
`dataset.split_indices(fold, "test")`，不能删掉表现差、预测缺失或非有限的样本。
按有界日块读取同一`joint_rows`、`label_table`，统一保留八目标、entry/exit价格及
实际trade时点。truth先转换为FR64 `y_raw`的float32值，再提升到float64做统计。
sample ID沿用FR64的dataset SHA+decision canonical hash。批次fingerprint绑定
dataset、fold、完整IDs、truth、QA价格/时点、成熟时点与独立估值观测。

全部预测必须同序完整IDs、同`[N,2,4]`形状且有限；错位/缺行/NaN直接失败。
`units="standardized"`要求同dataset、fold且test之前已冻结的共同target normalizer，
统一逆变换后评价。`units="original"`接收trainer已逆变换的预测。

每币分别报告5m flow Pearson IC、符号准确率（包含真实/预测0符号）、
5m return Pearson/Spearman IC、5m logRV rank IC，另列30s flow辅助IC。
少于3行或恒定预测/标签的IC保留null，不把null或行静默删除，也不补造零IC。

## 因果时序和条件性经济限制

协议endpoint已经通过未来标签/质量有效性筛选；当前预测文件因此没有覆盖所有
原始决策时刻。结果始终标为
`CONDITIONAL_FUTURE_VALID_ENDPOINT_TRADE_PRICE_PROXY`，
`implementable_strategy=false`、`real_bbo=false`、
`production_or_candidate_qualification=false`。此条件性回放不证明可实施策略、
alpha、候选或未来资格。无法从aggTrades恢复当时真实bid/ask。

历史价格序列独立于endpoint筛选，从同一raw joint rows提取每个Spot币已闭合的
close及bar available_us。决策和日末只查询available_us≤当前时间的真实观察；
无价格且无仓位时可保持现金，缺决策可观察价则明确计数并阻止该信号。
持仓估值缺观察价直接失败。entry/exit的QA价格仅在其历史trade事件到达时成为
已观察的事件价，不能提前影响NAV、现金、币数量或下单金额。

唯一信号为预测gross return≥35bp；flow/RV不控制交易。Spot long/flat，
entry anchor=decision+5s、exit anchor=decision+305s，每侧2s内真实first trade，
持有约300±2s。每币pending intent和已持仓均阻止同币重叠。事件使用stdlib
heapq，时间相同先日末估值，再退出、决策、进入；UTC边界时的新日活动不进入
上一日NAV。实际每一笔都保留原sample ID。

决策时按可观察NAV确定USDT reference-notional预算，并保留预计两币成本空间。
entry时只允许依据当时可观察NAV、现金和风险限制缩小预算；数量=预算/当时
历史entry trade-price proxy。单币30% NAV、总60% NAV为**新买入后净NAV约束**，
沿用既有backtest的资金约束语义。固定持有期间价格和后续费用可能使权重漂移；
摘要列出实际最大观察权重，不添加连续再平衡来改变预登记约5m hold。

成本分别在entry和exit按该侧reference notional扣：fee单侧10bp，extra
slippage单侧4bp，base assumed spread单侧1bp；双侧名义20+8+2=30bp。
固定spread stress为双侧4/8bp。exit价格变化会使实际退出notional与进入不同，
所以成本金额按两侧真实代理notional之和计算，不简单用进入金额乘30bp。
价格本身保持gross trade-price proxy，不重复把spread写进价格再另扣一次。

同一场景的同一持仓数量满足`gross_pnl - cost = net_pnl`；
`gross_proxy_return - estimated_cost = net_proxy_return`。
gross是这些已成交数量的成本前盈亏，并非单独重新投资的无成本策略。
daily_nav记录NAV、现金、币数量、估值时点、两币mark可得时点及价格、当日
费用/额外成本/换手；turnover为当日双侧reference notionals / 上次日末净NAV。
Sharpe、MDD直接复用UTC日度统计，初始现金计入回撤；首尾不足整日也算日观测，
不能把日内/未观察极值称为已知最大回撤。

## 六fold筛选与方向归组

`sprint_screen`只能接受单dataset合同。正式screen要求恰好事前固定
`rolling_00/04/09/13/18/22`六fold、各正式dataset且真实日期边界匹配、每fold至少
3个共同endpoint，不能把短smoke变成正式OOS。

对每币每primary独立检查：各fold IC等权均值flow≥.03或return rank≥.02，
正IC fold比例≥.6，最大正IC / 全部正IC之和≤.6。最后一项是**正IC贡献**
集中度，不是样本pool或资金PnL；不按fold样本数量改变权重。每币任一primary
通过才能screen pass。undefined IC不产生该task通过。正式screen也永不授生产
或candidate资格。成本受限状态要求已过预测screen、gross fold等权均值为正、
正gross fold≥.6且最大正gross贡献≤.6，net fold等权均值为负；记录
`PREDICTIVE_BUT_COST_LIMITED`。

`first_round_screen`必须十个固定config均有同批次的六fold才输出排行榜；
不足返回`INCOMPLETE_NO_LEADERBOARD`，leaderboard/top_directions为空。
排名值固定为已通过primary的最大（等权fold平均IC / 预登记门槛），不调阈值。
XGB-S/M共属XGB、TCN-S/M共属TCN、TS2Vec两probe共属TS2Vec，其余为独立方向。
最多三个不同方向，每方向保留排名最高的config；相同分数按config ID确定顺序。
此处只有接口和合成门槛测试，没有市场leaderboard/top-3结果。

## 接线与持久化

```python
batch = EvaluationBatch.from_dataset(dataset, test_indices, fold=fold)
result = evaluate_fold(batch, original_predictions, batch.sample_ids,
                       resources=training_receipt)
receipt = result.receipt()  # JSON-compatible metadata/metrics/economics summaries
# resources保留调用者实际运行/峰值RAM收据，不猜测独立模型峰值。
for spread, value in result.economics.items():
    value.daily_nav.write_parquet(owned_state / f"daily_spread{spread}.parquet")
    value.trades.write_parquet(owned_state / f"trades_spread{spread}.parquet")
screen = first_round_screen({config_id: fold_results})
```

`FoldEvaluation`字段为metadata、metrics和economics；economics整数键2/4/8对应
`EconomicsResult(daily_nav, trades, summary)`。`receipt()`将经济键转为JSON字符串
`"2"/"4"/"8"`，不把真实预测/交易明细写进小JSON。单fold预测摘要另绑定逆变换
预测字节SHA。要从各worker的小JSON聚合，可恢复
`FoldEvaluation(metadata, metrics, {int(k): EconomicsResult(None,None,summary)})`；
仅aggregation不需加载明细。真实行情、预测及模型留D/WSL，不入Git。

## 实际工程验收

全部Python/tests在hpc_linux，经`scripts/bounded.sh`共享RAM5GB、swap0，
`PYTHONDONTWRITEBYTECODE=1`、独占native STATE basetemp，无GPU。
专项11个独立case覆盖SciPy/原单位逆变换、错位/缺预测/非有限拒绝、
手算费用恒等式、同币重叠、两币净NAV资金限额、固定spread敏感性、
未来entry/exit变化不改变决策预算、跨UTC日手算现金/NAV/Sharpe/MDD、
缺可得价计数、六fold门槛、方向归组，以及FR64工程dataset逐端点八目标和
entry/exit QA精确一致。

V1测试11通过；Ruff V1记录3处测试行宽问题。V2在标签单位精确化后10通过、
1失败：测试把float32标准化逆变换的有限舍入误差错误要求为1e-12。
修复为显式float64往返验证，模型和归一化实现没有变更。
复测凭证、最终源码SHA与冻结复用来源绑定由独立FR70 acceptance报告记录；
失败与复测凭证分别保留，不覆盖。

最终V4测试11/11通过（18.167秒），Ruff V4通过；凭证为
`reports/fast_research/FR70_TESTS_20261002_V4.xml`、
`FR70_RUFF_20261002_V4.txt`及`FR70_SHARED_EVALUATION_ACCEPTANCE_20261002_V1.json`。
文件名采用本地日期2026-10-02；实际XML时点为2026-10-01 16:12:02 UTC。
最终evaluation源码SHA256
`f23d37ede10aa1ed3a3e1d7336d2a7c85884fc2e62dc6cb2ddfdf91e798d171e`，
测试源码SHA256
`28a0b212e38ed717e1282a0f6f4f39c2dbbc33348093291175d9caa5b24b110e`。
