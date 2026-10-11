# 复现差距与结论边界（2026-10-11；无新增训练）

**关键目标错配成立。** 原文学习有界仓位、直接优化捕获收益的 Sharpe；
本次学习下一日标准化收益的条件均值，以 MSE／排序门槛筛选。
因此原门槛可以决定停止已注册的预测适配，不能否定论文的策略主张，
也不能据此断定 CPD 或短期反转在加密市场无用。
本核对新增训练／GP 拟合／推断／钱包均为 **0**；原结果保留。
唯一后续方案是 [冻结提案](SHARPE_CORRECTION_PROPOSAL.json)，状态 **NOT_RUN**，
当前没有实现或启动其 runner。

## 身份与引用

原文为 [arXiv 2105.13727v3](https://arxiv.org/abs/2105.13727v3)
（PDF SHA `2b1906296d29b41dbb1792b3a2c44d6626d66162fc91e2160cac3780c7778353`）。
下列页码按 PDF 从 1 起计数。官方公开代码固定为
[`e0352cb0`](https://github.com/kieranjwood/trading-momentum-transformer/tree/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624)，
它同时含后续 Transformer 工程，不能假定它就是 2021 论文实验的历史版本。
我们的实际拟合源码固定为
[`abea0de9`](https://github.com/snowycat1234/coin/tree/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb)；
本核对不修改源码、原协议、模型或结果。

## 七项对照

|维度|原文／官方公开代码|本次已执行内容及结论限制|
|---|---|---|
|目标函数|原文 pp.5–6，Eqs.11/13/14；官方 [SharpeLoss L37–48](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/deep_momentum_network.py#L37)：`X × vol_scaled_return` 的负 Sharpe。|我们的 [run L167–175](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L167) 是 MSE；[L344–345](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L344) 标签为下一日 `r/vol_t`。原 [L441–451](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L441) 的 MSE／rank 门槛不构成论文 Sharpe 主张的必要条件。|
|CPD 估计|原文 pp.3–4，Eqs.2/7/9/10，p.6 IV.A；官方 [每窗标准化 L218–220](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/changepoint_detection.py#L218)、[Matérn 优化 L85–96](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/changepoint_detection.py#L85)、[连续变点位置／双核优化 L136–155](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/changepoint_detection.py#L136)。|我们的 [core L190–243](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/core.py#L190) 一次训练全局标准化、320 窗混合拟合；[L266–280](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/core.py#L266) 验证只算固定协方差、6 位置网格后验。severity 使用网格边际证据，区别于各窗最优点似然；location 是后验均值。用户要求验证期不拟合归一化／变点／参数，因此未照搬在线每窗优化；它利用当时已知窗口本身并不等于未来泄漏。|
|输入与窗口|原文 p.6、p.13 App.B／Exhibit7；官方 [data_prep L82–113](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/data_prep.py#L82)。63 步 LSTM；CPD 长度可选 10/21/63/126/252；训练非重叠序列。|同 63 步，CPD 固定 21（22 个收益）；使用滑动重叠窗口、8 个 return/MACD 特征；[core L60–92](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/core.py#L60)、[run L135–136](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L135)。不 winsorise，不 bfill，缺失重置；官方 [daily_vol L123–128](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/classical_strategies.py#L123) 含 bfill，未原样照搬。|
|模型容量|原文 p.13 Exhibit7；官方 [hp_grid L3–8](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/settings/hp_grid.py#L3)、[LSTM／tanh／dropout L508–535](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/deep_momentum_network.py#L508)。hidden 候选 5/10/20/40/80/160，dropout 0.1–0.5。|[run L122–132](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L122)：hidden16、无 dropout、最后隐藏状态加无界 linear；每臂名义 1809 参数。baseline 的两零输入对应 `4×16×2=128` 个无梯度系数，活跃参数 1681，treatment 1809。相同参数轴／初始化不是严格相同有效容量。原文最终选中模型／权重未知，不能声称容量一致。|
|训练与收敛|原文 p.6 IV.A、p.13 App.B：最多 300 epochs、patience25、训练内 90/10、50 次随机超参尝试；官方 [Sharpe 验证／早停 L87–119](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/deep_momentum_network.py#L87)。|固定 256 updates、batch128、有放回抽样、3 seeds，无早停或超参搜索。[run L147–206](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L147)。只留完整训练 MSE 起终点和每64步单 minibatch loss，不能验证收敛。GP 的 23/51 次优化成功不提供 LSTM 收敛证据。当前官方全局默认还有 TFT/252 设置，不能拿它替代原文 63。|
|金融决策层|原文 pp.5–6 Eqs.11/13/14、p.14 App.C；官方 [time-distributed tanh L529–535](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/deep_momentum_network.py#L529)、[vol scaling L131–137](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/classical_strategies.py#L131)。仓位策略；附录以固定 bps×换手考察成本。|没有仓位／交易目标；[run L468–472](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L468)：钱包0、PnL/APR未知。下一日 close 标签不是可得成交价。费用、滑点、实际资金费、共享资金／gross、风险与收费终端平仓均未测试；排序亦不能替代这些。|
|数据及时间角色|原文 p.7 IV.B：50 个 Pinnacle CLC 传统期货，1990 起训练、1995–2020 的5年滚动测试；当前官方 [README L20–22](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/README.md#L20) 则提供另一个 Quandl／100 ticker 入口。|CORE5 加密公开历史；2020 warmup、2021–22 train、2023H1/H2 和 2024Jan–Apr 已见开发验证。[run L63–88](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/run.py#L63) 仅读白名单原表，不用旧24特征；[core L96–116](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/core.py#L96) 标签严格成熟／边界 purge。不是全新 OOS；未检验原传统期货结果。|

两个细节不应误当主要机制缺失：原文 gamma 与官方代码 age 方向相反
（官方 [L297–300](https://github.com/kieranjwood/trading-momentum-transformer/blob/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624/mom_trans/changepoint_detection.py#L297)，
我们 [core L170–175](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/core.py#L170) 跟随官方 age）；
相同位置估计下 `age=1-gamma` 是可逆仿射变换，本身不损失信息。
原文 p.6 的 256 年收益窗／MACD(16,28) 与官方 252／(16,48) 不同；
本次预先明确跟随代码，未事后改配方。真正大差距是目标函数、CPD 估计和训练充分性。

## 为什么 MSE 不构成 Sharpe 的必要门槛

MSE 的最优预测是条件均值；策略可以从条件风险变化获益，即使条件均值不变。
以下是**闭式数学反例**，没有运行仿真、拟合或市场回测，也不声称真实 CPD 识别了该风险。

决策前可观测状态 L/H 各概率 1/2。
L 中收益 `Y=1±1`，H 中 `Y=1±3`，各正负分支等概率。
两状态条件均值都为1，因此有无状态信息的最佳预测都是1，MSE 都是5。
固定仓位0.5的捕获收益均值0.5、方差1.25，Sharpe=`1/sqrt(5)≈0.4472`。
状态仓位 L=0.5、H=0.1 的捕获收益均值0.3、二阶矩0.3、方差0.21，
Sharpe=`0.3/sqrt(0.21)≈0.6547`。两种策略都只用事前信息，仓位在 tanh 范围内。
故 MSE 无增量并不蕴含 Sharpe 无增量；反之 MSE 增量也不保证净 Sharpe／利润。
这一非等价性与原文 p.6 III.B 的策略目标相符；推导是本核对自身的分析。

短期反转也不是另一个 oracle 输出或 selector：本次没有学习原文仓位序列，
不能根据两个 CPD 特征或收益方向排序声称已学到盈利反转。
未来即使 policy Sharpe 改善，也可能主要来自风险缩放；须另审仓位行为和原生净账本。

## 已经排除和仍未排除的范围

[原 RESULT](results/RESULT.json) 精确排除了“**这个固定配置在这些已见块上
达到全部五个事先规定的晋级门槛**”：三个块的 MSE skill 为
−0.249523%、−0.088108%、+0.106121%，三个 seed 仅一个整体改善；
它支持停止这项具体预测筛选。原成本更高的钱包阶段按事先计划没有启动。

它**没有在统计上排除小的真实 MSE 增益**：date-mean loss improvement
−0.000969767，14日 bootstrap95% 区间 [−0.003615307,+0.001896265] 跨零，
加上已见历史、有限种子、重叠序列，不能解释为总体效应不存在。
也没有排除：

1. Sharpe／仓位学习目标下的 CPD 增益、风险条件化或短期反转收益；
2. 原始逐窗在线 GP 的增益，其他原文模型容量／dropout／收敛配置；
3. 原传统期货结果，或别的加密时期／数据域中的效应；
4. 原生钱包扣费、滑点、资金费及风险后的增益或亏损——本次都没有测量。

上述未排除事项不是建议逐项搜参，也不允许事后把此阴性结果改成成功。

## 唯一最小公平修正：冻结提案，先不运行

[完整冻结 JSON](SHARPE_CORRECTION_PROPOSAL.json) 是**新尝试2**，状态 NOT_RUN；
没有 executable runner，不能把 README 中旧 MSE 命令当成修正命令。
原尝试1仍为6 fits／1536 updates；若未来实施，合计将是2 attempts／12 fits／7680 updates。

- 复用相同 Git 行情、切分、63日 last-head／hidden16、8+2 特征、已发布 scaler／GP
  的确切 SHA；不新增 GP／归一化拟合。两臂共同改为 tanh 仓位及 pooled captured-return
  负 Sharpe。crypto 使用365日年化、15%目标波动常数、epsilon1e−9。
- 3固定种子2001/2002/2003，精确配对初始权重和 minibatch；6 fits×1024 updates，
  Adam0.001／batch128／clip1，无超参搜索，无早停或事后延长。每128步保存全 train
  Sharpe、捕获收益矩、仓位方差／饱和率与梯度诊断；只用最后一步，预算不等于收敛。
- 原 MSE／IC仅作诊断。固定5资产分母的每日 raw policy proxy 算 Sharpe；
  可用掩码只能依赖决策时已知输入。当前不可用资产分配为现金；
  当前可用但下一真实收益缺失则该块 INVALID，不事后删除该资产或补零。
  原 [sample_index L110–112](https://github.com/snowycat1234/coin/blob/abea0de9ec9f2e69d8d6212f10b89313bfb9cabb/modules/slow_momentum_cpd/core.py#L110)
  检查未来标签有限性，不能拿它生成新 policy 的 CASH 掩码；必须另建事前掩码。
  计分为 `sqrt(365)*mean(U)/std(U,ddof=0)`，零／非有限方差记 INVALID，
  不把训练 epsilon 混入计分。
  14日／1000次／seed9901 同日期、同资产联合抽块，逐次重算非线性的 ΔSharpe，
  不复用 MSE-loss 区间作策略结论。
- 晋级要求四项全部成立：至少2/3块 ΔSharpe>0，至少2/3seed整体 ΔSharpe>0，
  ensemble整体 ΔSharpe>0，整体配对 bootstrap95% 下界>0。
  三个种子等权平均仓位，不挑赢家；历史仍已见，不称独立确认或全新 OOS。
- 仅 raw captured-return policy probe；成本、资金费和可得成交尚未绑定，
  不输出金融净PnL/APR。原生阶段需另一份具体输入／执行冻结和原有共享钱包，
  仍完整10k、单币abs30%／gross60%、逐仓1x及收费终端平仓。
  本提案没有安排或运行任何钱包。

成本：新训练总6144 updates，为原更新数4倍；按旧完整实验13.018秒作粗估，
训练／计分约1–5分钟 CPU，**未实测**；单命令1200秒硬停止，不扩预算。
沿用1线程、GPU0、swap0、共享RAM8GB／原守卫；额外输出最多10MiB，
市场下载／付费／新凭证／钱包均0。
在未来执行前必须实现独立 runner/state、验证 Sharpe／tanh／因果掩码／非线性 bootstrap，
发布源码／冻结／测试提交并核远端。当前这些执行检查为 **NOT_RUN**。

这项修正只消除主要目标错配，保留在线CPD、time-distributed输出、
非重叠训练、dropout／超参选择及原 CLC 数据差距；
因此无论成败，都只能判断这个冻结 GP 的加密 policy 适配。

## 本核对的交付与阻塞

独立只读复核确认上述目标差距与最小设置。本核对仅新增说明、冻结提案及字节核验 receipt，
不重跑14个已通过的模型测试、不新增合成市场结果。
[核验 receipt](GAP_REVIEW_RECEIPT.json) 对旧交付清单和4个实际拟合源码逐字节核对，
验证本提案计数／NOT_RUN状态／引用代码锚点。
最小核验命令（只读旧模型字节，不载入模型或推断；首次写 receipt，后续只核对）：

```bash
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/slow-momentum-cpd-20261011/verify_gap_review.py
```

原论文精确复现仍缺原 CLC 数据、对应历史源码和选中模型／超参工件；
原2026 Q1/Q2账本不可访问。collector 2026-03-01–2026-09-01 锁未开，
没有改另一收益分布研究、访问 Library、账户密钥、创建凭证、付费、部署或交易。

