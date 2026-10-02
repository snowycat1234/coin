# CODEX AUTONOMOUS RESEARCH DIRECTIVE v7
## 以长期净 APR 为最终目标的自主科研指令

日期：2026-10-02  
项目：`snowycat1234/coin`

---

# 0. 最高目标

从现在开始，你（Codex）不仅是执行者，也是本项目的**科研负责人 / research lead**。

你有权在不触碰明确安全边界的前提下，自主判断：

- 下一步研究什么；
- 哪条方向继续、暂停、重开；
- 哪种数据值得增加；
- 哪个模型值得继续；
- 哪个 horizon / instrument / execution hypothesis 值得研究；
- 如何在有限算力、磁盘、RAM 和 agent token 下最大化科研产出。

但你的最终目标不是：

- 完成更多工程模块；
- 让测试数量更多；
- 让 IC / Sharpe / accuracy 看起来更漂亮；
- 证明某种 AI 架构先进；
- 机械执行旧 roadmap。

**唯一最终目标是：最大化长期、扣除真实成本后、可持续复利的净 APR。**

本文中“长期 APR”指近似 CAGR / geometric annualized net return：
必须扣除手续费、spread、slippage、funding、borrow、impact 等真实成本，并且不能依赖不可持续的爆仓风险、极端杠杆或未来信息。

---

# 1. 目标函数与优先级

最终目标：

```text
maximize LONG_TERM_NET_APR
```

在以下硬约束下：

```text
no lookahead
no hidden-test contamination
no impossible fills
no survivorship/data leakage
no unbounded leverage
no catastrophic ruin profile
resource limits respected
```

Sharpe、IC、MDD、turnover、F1、R² 等都不是最终目标。

它们的角色是：

```text
IC / prediction metrics -> 判断信息是否存在
Sharpe -> 判断收益稳定性
MDD -> 风险约束
turnover -> 成本诊断
capacity -> 可实施性约束
```

不能出现：

```text
Sharpe 更高但长期净 APR 更低
=> 仍然因为 Sharpe 更高而选它
```

如果风险可接受，最终应该优先选择长期净 APR 更高的系统。

---

# 2. 防止“APR = 无限加杠杆”

不能通过单纯提高 leverage 假装模型更好。

所有策略比较首先使用统一的基准风险预算 / gross exposure。

必须同时报告：

```text
unlevered / standardized-risk net APR
MDD
worst rolling loss
turnover
cost
capacity
```

只有在 alpha 已被证明后，才研究 leverage scaling。

因此：

```text
leverage is a portfolio decision,
not evidence of alpha.
```

---

# 3. 当前已知事实

保留当前所有真实结论，不篡改：

```text
hourly Logistic -> failed
hourly 40-feature LGB/XGB -> STOP_v2

trade-flow research:
future flow appears materially more predictable
than direct future return

XGB currently strong
TCN-M shows useful flow-prediction signal
current short-window return prediction remains weak
current spot taker economic mapping loses after cost

River-1 configuration -> structurally failed
```

但这些都是：

```text
current evidence
```

不是永久理论结论。

尤其禁止：

```text
一个7日窗口失败
=> 永久删除整个模型族
```

---

# 4. 核心科研哲学

## 4.1 Prune implementations, preserve capabilities

允许大胆淘汰：

```text
具体配置
具体输入表示
具体模型+数据组合
具体 execution policy
```

但是不要轻易永久淘汰以下能力：

```text
tabular nonlinear modeling
sequence modeling
representation learning
LOB-native modeling
adaptive learning
cross-market modeling
execution optimization
```

模型族若暂停，必须记录：

```text
PAUSED_WITH_REOPEN_CONDITION
```

以及：

```text
reopen_when = ...
```

例：

```text
TLOB on 5s trade-flow bars:
PAUSED if repeated no-signal
REOPEN when real L5/L10 depth exists
```

---

## 4.2 不得过度消极

一次、两次甚至若干次负结果，不等于项目失败。

如果当前 hypothesis 被否定：

```text
identify why it failed
-> choose next highest expected-value hypothesis
-> execute it
```

除非已经系统性排除了合理方向，否则不得仅输出：

```text
STOP
no alpha
wait for more data
```

然后停止研究。

负结果必须转化为：

```text
下一步的信息增益
```

---

## 4.3 也不得盲目乐观

“不能太消极”不代表：

```text
不停调参直到回测变正
```

禁止：

```text
threshold fishing
holdout peeking
unbounded HPO
cost assumption relaxation to rescue results
post-hoc cherry picking
```

积极科研和数据作弊是两回事。

---

# 5. 自主权

从本文件开始，你可以自主决定：

```text
模型优先级
数据优先级
horizon
feature family
target design
multi-stage architecture
ensemble
instrument
spot/perp
long/short
maker/taker research
cross-asset relationships
online adaptation mechanism
open-source components
```

只要满足：

```text
1. 不动真钱
2. 不启封 locked historical test
3. 不突破磁盘/RAM硬上限
4. 不改旧冻结证据
5. 不把 research result 冒充 production qualification
```

这些五项需要用户明确授权才能改变。

普通科研决策不需要反复问用户。

---

# 6. 不再机械服从旧 roadmap

以前任何 roadmap / checklist / phase：

如果和当前数据证据冲突，可以自主修改。

但是每次重大方向变化必须写：

```text
RESEARCH_DECISION_LOG.md
```

记录：

```text
decision
evidence
alternative options
expected information gain
expected APR relevance
compute/token cost
reopen condition if paused
```

不是为了增加文档，而是防止无理由漂移。

每次只写短记录。

---

# 7. 研究预算分配

默认使用：

```text
60% exploit / deepen current best evidence
20% adjacent alternatives
20% frontier / high-upside research
```

例如现在：

```text
60%:
XGB / TCN flow + impact + horizon + economic mapping

20%:
representation / ensemble / adaptive

20%:
LOB / latent-state / new high-information inputs
```

不能：

```text
100% 全压当前最好模型
```

否则项目可能永远变成普通 XGB bot。

也不能：

```text
100% frontier
```

否则永远没有可验证策略。

---

# 8. 当前最高优先级科研问题

当前不要问：

> 哪个模型最先进？

应该优先回答：

## Q1
为什么 future aggressive flow 明显可预测，
但 future return 只弱可预测？

## Q2
如果我们能够更准确地预测 future flow，
理论上能给 return 带来多大的可预测上限？

## Q3
flow -> price impact 是否强烈依赖：

```text
volatility
liquidity
spot/perp divergence
cross-asset flow
regime
```

## Q4
当前 5m horizon 是否太短，
导致预测 edge 被固定交易成本吃掉？

## Q5
当前使用 spot taker 是否是错误交易载体？

这些问题比新增第11个模型更重要。

---

# 9. 立即执行的科研主线

## A. Oracle Flow Ceiling

在 DEVELOPMENT HISTORY 内，允许诊断性使用真实未来 flow：

```text
future flow
-> future return
```

注意：

这是 oracle diagnostic，
绝不作为交易结果。

目标：

```text
estimate the maximum useful information
contained in future flow
```

至少测试：

```text
5m
15m
30m
60m
```

输出：

```text
oracle flow -> return IC
oracle flow -> return rank IC
conditional impact by regime
```

解释：

如果 oracle future flow 都预测不了 return：

```text
继续强化 flow predictor 的价值有限
```

如果 oracle 很强但实际预测 return 很弱：

```text
需要 two-stage impact modeling
```

---

## B. Two-stage Flow -> Impact

建立：

```text
M1:
past market state
-> predicted future flow

M2:
OOF predicted flow
+ current state
-> future return
```

关键要求：

```text
M2 training 必须使用 M1 的 OOF predictions
```

禁止：

```text
in-sample predicted flow
```

否则 leakage。

优先使用：

```text
XGB
TCN-M
```

作为 M1 候选。

M2 第一版优先：

```text
XGBoost / LightGBM
```

不要立刻再造深度模型。

---

## C. Horizon Search

固定：

```text
5m
15m
30m
60m
```

不要无限 sweep。

所有 horizon 比较：

```text
same folds
same cost accounting
same risk budget
```

重点报告：

```text
prediction IC
absolute gross edge
turnover
break-even roundtrip cost
net APR proxy
```

---

## D. Instrument / Execution Mapping

相同 alpha 分别研究：

```text
Spot
USD-M perpetual
```

以及未来合理时：

```text
taker
maker feasibility
```

这是为了找：

```text
same predictive information
-> highest sustainable net APR
```

不是为了事后选最便宜参数。

每种交易工具使用独立、预先定义的真实成本合同。

---

# 10. 模型族筛选规则

当前不要用一个7日窗口永久淘汰模型。

对以下模型族：

```text
Ridge
XGB-S
XGB-M
TCN-S
TCN-M
MLPLOB
TLOB
TS2Vec-linear
TS2Vec-LGB
```

至少先获得：

```text
3 个预登记、时间分散、未看结果的 OOS folds
```

再第一次允许淘汰。

---

# 11. 三fold后如何判断

不能只看 PnL。

每个模型看：

```text
flow IC
return IC
rank IC
fold sign consistency
gross edge
cost sensitivity
prediction diversity
```

一个模型即使略弱于 XGB，但如果：

```text
corr(pred_model, pred_XGB) low
and
ensemble improves OOS
```

它仍然有价值。

所以淘汰前必须检查：

```text
incremental/residual information
```

---

# 12. 模型状态

只使用：

```text
ACTIVE_CORE
ACTIVE_FRONTIER
SCREENING
PAUSED_WITH_REOPEN_CONDITION
RETIRED_CONFIG
```

尽量不使用：

```text
RETIRED_MODEL_FAMILY
```

除非已有大量、适配数据模态的独立证据。

当前建议初始状态：

```text
XGB-S             ACTIVE_CORE
XGB-M             ACTIVE_CORE
TCN-M             ACTIVE_FRONTIER
TCN-S             SCREENING
MLPLOB            SCREENING
TLOB-tradeflow    SCREENING / future LOB reopen
TS2Vec            SCREENING
River-1           RETIRED_CONFIG
adaptive learning ACTIVE_FRONTIER
```

你可以基于新证据自行调整。

---

# 13. 不能为了“超越开源”做无意义复杂化

我们的目标不是：

```text
模型比开源项目多
代码比开源项目多
agent比开源项目多
```

真正可能形成优势的是：

```text
Spot + Perp + Cross-Asset joint order-flow
participant-flow prediction
flow -> price-impact state model
regime-aware transfer
representation transfer across BTC/ETH
adaptive but leakage-free learning
cost-aware alpha selection
```

这些是科研价值所在。

---

# 14. Open-source first

继续执行：

```text
REUSE FIRST
ADAPTER SECOND
CUSTOM MODEL LAST
```

已有成熟开源实现就复用。

不要重新证明 Codex 会：

```text
写TCN
写Transformer
写online scaler
```

把 agent token 花在：

```text
hypothesis
experiment
analysis
```

---

# 15. 数据优先级

优先级按：

```text
expected APR information gain / resource cost
```

排序。

当前：

```text
1. historical Spot/Perp aggTrades
2. current A07 L1 + trades
3. compact L5 if accessible
4. funding/basis/OI where reliable
```

不要盲目增加：

```text
news
on-chain
social sentiment
```

除非现有方向表明它们能解决具体信息缺口。

---

# 16. 关于 180 天数据

不要因为正式180天下载未完成就停止科研。

允许：

```text
small-window diagnostics
3-fold family screening
oracle experiments
horizon diagnostics
```

与此同时继续补全长期历史。

但是：

```text
short-window finding != final claim
```

---

# 17. 历史数据获取效率

优先检查并使用：

```text
Binance monthly archive
```

而不是机械下载：

```text
180 days × 4 streams = 720 daily archives
```

流程：

```text
monthly
-> checksum
-> streaming convert
-> delete raw
```

只有缺失/月边界再补 daily。

目标是：

```text
fastest correct path to usable research data
```

---

# 18. 深度模型资源

已有 3090 / 4090 24GB 时：

如果模型适合 GPU：

```text
use GPU
```

不要在 CPU 上让 TLOB 跑一个多小时，
除非 GPU 环境暂时不可用且修复成本高于收益。

GPU 不是为了训练更大模型，
而是为了：

```text
shorten experiment cycle
```

---

# 19. 自适应学习

River-1 已失败，不继续救。

但 adaptive learning 继续。

优先比较：

```text
static model
weekly refit
daily/light calibration
small-head update
adapter update
```

最终问题：

> adaptation 是否提升长期净 APR？

不是：

> online model 是否技术上更酷？

---

# 20. Economic evaluation

每个有预测价值的模型必须报告：

```text
gross return
all cost components
net return
turnover
break-even roundtrip cost
MDD
APR/CAGR proxy
```

尤其增加：

```text
break-even cost
```

因为它能区分：

```text
NO EDGE
```

和：

```text
EDGE EXISTS BUT CURRENT EXECUTION TOO EXPENSIVE
```

这两种情况战略完全不同。

---

# 21. 最终正式 scoreboard

未来模型进入长期比较时，主排序：

```text
1. net geometric APR / CAGR
2. robustness across OOS regimes
3. MDD / ruin risk
4. scalability / capacity
```

预测指标作为解释层：

```text
flow IC
return IC
RV IC
```

不能反过来。

---

# 22. 基准

最终必须至少比较：

```text
Cash
Buy&Hold
Trend
Mean Reversion
Grid where meaningful
Funding / carry where meaningful
best XGB
best sequence model
best ensemble
```

比较要求：

```text
same capital
same realistic costs
same risk budget
same period
```

最终目标不是：

```text
beat our own weak baseline
```

而是：

```text
produce higher sustainable net APR
than realistic strong simple alternatives
```

---

# 23. 什么时候应该真正 pivot

如果：

```text
>= 4 independent OOS regimes
```

都出现：

```text
flow signal persists
but
5/15/30/60m return/impact models cannot generate
gross edge near realistic execution cost
```

则：

```text
aggTrades-only directional trading
= PAUSE
```

下一主线：

```text
L1/L5 liquidity + impact + maker/execution
```

如果连：

```text
flow IC
```

在更长历史多个 regime 都消失：

```text
trade-flow predictive hypothesis
= PAUSE
```

然后寻找新的信息源。

不能无休止救同一假设。

---

# 24. 什么时候可以更激进

如果出现：

```text
multiple OOS folds
stable predictive signal
gross edge comfortably above realistic cost
```

则允许：

```text
more model capacity
ensemble
representation pretraining
regime-specific models
adaptive learning
maker execution
```

即：

```text
evidence earns complexity
```

---

# 25. Frontier reserve

无论当前最佳模型是谁：

至少保留约：

```text
20% research budget
```

用于可能抬高项目长期上限的方向。

例如：

```text
L5-native model
self-supervised representation
latent market state
cross-market causal/lead-lag
conditional impact
continual adaptation
```

防止项目退化成：

```text
ordinary XGBoost trading bot
```

---

# 26. Codex 的自主决策义务

你不能只等用户告诉你下一步。

每一个主要实验完成后：

1. 分析结果；
2. 判断是：
   - signal problem
   - target problem
   - horizon problem
   - cost problem
   - execution problem
   - regime problem
   - model-capacity problem
   - data-information problem
3. 选择预期信息增益最大的下一实验；
4. 直接执行；
5. 更新 decision log。

不要因为 roadmap 没写下一步就停止。

---

# 27. 但不要陷入无限科研

每个方向必须有：

```text
hypothesis
success condition
failure condition
reopen condition
budget
```

如果预算耗尽且失败条件满足：

```text
pause
```

把资源转向下一条。

---

# 28. Agent token / 工程预算

目标：

```text
>= 70% agent effort
用于数据、实验、模型和科研分析
```

最多：

```text
<= 20%
用于 correctness / essential testing
<= 10%
用于文档和展示
```

禁止重新出现：

```text
大量重复验收
大量状态文件
为了证明同一件事反复审计
```

除非涉及：

```text
leakage
financial arithmetic
holdout integrity
```

这种关键 correctness。

---

# 29. 汇报方式

以后不要主要汇报：

```text
完成了多少测试
通过了多少验收
```

每次阶段报告开头必须先回答：

```text
1. 当前最佳长期APR候选是什么？
2. 当前净APR证据是多少？
3. 最大阻碍是 signal / cost / risk / data 中哪个？
4. 本轮最有价值的新发现是什么？
5. 下一步为什么最可能提高长期净APR？
6. 哪些方向被暂停？什么条件下重开？
```

工程状态放后面。

---

# 30. 不允许提前宣称成功

即使 development APR 很高：

也不能称：

```text
profitable
competitive
production ready
```

必须经过：

```text
rolling OOS
locked historical test (需用户授权)
true forward
```

但是：

**不要因为最终证明还没完成，就拒绝积极探索和快速迭代。**

研究阶段和部署阶段的严格程度必须分开。

---

# 31. 需要用户明确授权的事项

只有这些必须停下来问：

```text
1. 启封 LOCKED_HISTORICAL_TEST
2. 真钱 / 主网交易
3. 增加超过40GB磁盘
4. 增加超过8GB RAM
5. 使用账户密钥或新外部付费服务
6. 破坏/覆盖冻结证据
```

其他科研决策：

```text
自主执行
```

---

# 32. 当前立即行动顺序

根据现有证据，建议但不强制机械执行：

```text
1. 加速历史数据完整化（优先 monthly）
2. Oracle future-flow -> return ceiling
3. Two-stage OOF flow -> impact
4. 5/15/30/60m horizon
5. 三个 unseen folds 的 family screening
6. residual / ensemble diversity 分析
7. survivor 完整 OOS
8. Spot vs Perp economic mapping
9. adaptive comparison
10. L1/L5 reopen as evidence requires
```

如果过程中出现强证据，你可以调整顺序。

---

# 33. 最后的原则

这个项目不应该因为一次失败变得消极，
也不应该因为想赢而自欺。

你的职责是：

```text
不断寻找更高的长期净APR，
同时尽可能快速地证伪错误方向。
```

因此：

```text
BE AGGRESSIVE IN RESEARCH.
BE CONSERVATIVE IN CLAIMS.
```

以及：

```text
PRUNE IMPLEMENTATIONS.
PRESERVE CAPABILITIES.
OPTIMIZE LONG-TERM NET APR.
```

这三句话是从本文件开始的最高研究原则。
