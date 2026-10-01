# Coin Quant 工程审计与下一阶段执行指令 v3

日期：2026-09-30  
适用对象：Codex / 后续执行 agent  
审计范围：用户本次提供的 `coins.zip` 子集。未上传的目录/脚本不视为缺陷；本文件只评价已看到的实现与已生成证据。

---

## 0. 结论先行

当前工程**没有整体做歪**。相反，工程纪律、数据封存、资源守卫、故障恢复、订单状态机和 Testnet 默认拒绝机制做得明显好于普通个人量化项目。

但是研究路线出现了明显偏移：

1. 项目花了大量工作把 P05/P06/P07、订单状态机、不可变日志、Testnet 和故障恢复做深；
2. 真正的 alpha 研究只有 `10 个 15m/1h K线特征 + Logistic Regression`；
3. `Logistic 失败 => 停止 LightGBM/非线性模型` 这一门槛不合理；
4. 当前 collector 主要保存 1m kline 和 bookTicker 的分钟摘要，丢掉了最值得研究的实时交易流/盘口数量动态；
5. 历史回测与 live/shadow 的**成交时点语义不一致**，必须在任何新研究前修复。

因此从本文件开始，执行优先级改为：

> **停止扩张执行层 → 修复 execution parity → 建立强 baseline → 做一次受控的 nonlinear tabular 研究 → 同时开始轻量 microstructure 数据采集 → 只有 alpha 证据通过后再继续深度模型/Testnet 长期运行。**

现有 Logistic v1 的 STOP 结果必须保留，不删除、不改写；但它只能证明该具体模型和旧执行语义失败，不能证明 LightGBM/XGBoost/order-flow 路线失败。

---

# 1. 当前工程审计评级

基于上传内容：

| 模块 | 评级 | 结论 |
|---|---|---|
| 数据可追溯/封存 | A | SHA、dataset lock、holdout gate、质量隔离做得好 |
| 防未来信息 | A- | 主框架意识强；但历史/live execution timing 不一致需要修 |
| 回测可复现性 | A- | 有 deterministic replay、成本/故障情景；执行合同需统一 |
| 资源约束 | A | 40GB/5GB 守卫非常严格，远低于当前预算 |
| 实时 collector | B+ | 稳健，但采集的信息对 alpha 研究过粗 |
| Shadow/状态恢复 | A- | 状态机、不可变账本、恢复逻辑较完整 |
| Testnet/订单状态机 | A- | 工程质量高，但在无盈利候选时做得过早 |
| Baseline 研究 | C+ | Cash/BuyHold/EMA 有，但不足以代表“传统策略” |
| ML/Alpha 研究 | C- | 只有 Logistic；特征、标签、模型和决策规则过窄 |
| Microstructure | D+ | live 有 bookTicker，但没有形成可研究的 OFI/trade-flow 数据集 |
| 深度模型/RL | 未开始 | 当前不应开始 |

粗略判断：

- **交易软件工程完成度：约 70–80%**（仅指已上传范围）
- **可验证 alpha 研究完成度：约 15–25%**
- **达到“有竞争力策略”所需证据：仍处于早期**

不要用代码行数、测试数量或 P07 完成度代替 alpha 进展。

---

# 2. P0：必须先修的执行语义不一致

## 2.1 问题

当前历史 `BacktestConfig.latency_minutes` 默认是 `0`。

聚合 1h/15m bar 的 `available_us` 恰好等于 bar close，例如 09:00–10:00 的 1h bar 在 10:00 可用。历史回测把 target 调度到 10:00，并使用 10:00 那一分钟的 open 作为成交代理。

但 live/shadow/candidate 创建订单时使用：

```python
not_before_ms = (now // MINUTE_MS + 1) * MINUTE_MS
```

也就是收到 10:00 收盘信号后，至少等到 10:01 的 fresh quote 才允许成交。

所以现在存在：

```text
historical: signal 10:00 -> execution proxy 10:00
live:       signal ~10:00:00.xxx -> earliest execution 10:01
```

这违反了 `PROJECT_PLAN_v2.md` 中“下一分钟执行”的本意，也让 historical/live 测的不是同一策略。

## 2.2 修复规则

创建唯一的 `ExecutionContractV2`，历史、shadow、candidate、未来 Testnet 全部引用同一合同，不允许分别写时间规则。

固定：

```text
decision_time = complete aggregated bar becomes available
historical earliest execution minute = ceil(decision_time to minute) + 1 minute
live earliest execution = first fresh bookTicker at/after that same minute
capacity proxy = immediately preceding complete 1m bar
max order wait = 5 minutes
```

历史 canonical backtest 必须使用：

```python
latency_minutes = 1
```

旧 `latency=0` 结果不删除，但改标签为 `legacy_execution_v1`，不得继续作为新模型的正式成绩。

## 2.3 必须新增验收测试

建立一个合成市场轨迹，同时喂给 historical executor 与 shadow executor，要求：

```text
same signal timestamp
same earliest eligible minute
same price/capacity source minute
same cost contract
same target position
```

对于确定性的 synthetic quote/path：

```text
execution minute 必须完全一致
```

允许 live 因 quote 到达延迟比历史更晚，不允许比历史更早。

### P0 验收

- [ ] `ExecutionContractV2` 成为唯一时间语义来源
- [ ] canonical P03 基线重新以 latency=1 生成
- [ ] 新研究只能调用 V2
- [ ] cross-engine parity test 通过
- [ ] 旧 P04 Logistic 结果保留，不用修复后的执行语义偷偷重写旧记录

---

# 3. P0：立即停止继续扩张 execution/mainnet 功能

当前没有合格 alpha 候选。

因此：

```text
G47/G50/mainnet/new execution features
```

除修复明确 correctness bug 外，全部暂停。

现有 P07/Testnet/ExecutionEngine 保留并回归测试，但不要继续增加：

- 主网真实交易入口；
- 更复杂 maker 执行；
- 多交易所订单路由；
- 更复杂账户权限；
- futures live trading。

理由：现在最大的项目风险不是“不会下单”，而是“没有证据表明值得下单”。

资源优先给 research/data。

---

# 4. Logistic v1 如何处理

## 4.1 保留 STOP

当前正式记录：

```text
1h Logistic OOS net return ≈ -8.99%
15m Logistic OOS net return ≈ -17.47%
B2 同期 ≈ -5.50%
```

且成本压力均失败。

这个结论不要删除、不要通过改 threshold 或重新跑同版本去“救”。

## 4.2 但不要把 Logistic 当成 nonlinear gate

删除以下研究规则：

```text
只有 Logistic > B2 才允许 LightGBM
```

Logistic 只能作为 sanity baseline，不能证明：

```text
无 nonlinear interaction
无 regime effect
无 cross-asset effect
无 order-flow alpha
```

因此允许**一次严格预登记的 v2 非线性研究**。

---

# 5. 关于原 2026-03-01 ~ 2026-09-01 holdout 的新定位

该区间虽然在文件级别仍未被程序揭晓，但今天已经是 2026-09-30。

对今天以后新设计的 v2 策略，它已经不是“真正未来”的时间段。人类研究者已经生活在这段市场历史之后，无法保证完全没有宏观记忆泄漏。

因此：

1. **不要删除原 holdout**；
2. 它仍然可以作为一次 `locked historical test`；
3. 但不得把它写成 v2 的最终“完全盲未来证据”；
4. v2 真正的 pristine evidence 从 2026-10-01 之后开始累计。

状态名称统一：

```text
2026-03..08 = LOCKED_HISTORICAL_TEST
2026-10-01 onward = TRUE_FORWARD_V2
```

原一次性消费机制可以保留，但报告必须区分两者。

---

# 6. Research v2：立即执行的非线性低资源路线

## 6.1 第一轮只做 1h

暂停 15m 主线。

原因：

- Logistic 15m 更差；
- 高频率使成本更敏感；
- 当前没有真实微观结构历史；
- 1h 更适合先验证“是否存在可交易 nonlinear alpha”。

## 6.2 模型只允许两个

```text
M1 = LightGBM
M2 = XGBoost
```

不做 Transformer、TCN、RL。

每个模型最多 3 个预登记配置，总共最多 6 个配置。

禁止 Optuna 大规模搜索。

## 6.3 模型任务

不要继续把主要任务定义为：

```text
future 4h net return > 0 ?
```

改为主任务：

```text
regression: predict future 4h gross executable return
```

其中 entry/exit 都必须使用 ExecutionContractV2 的下一分钟可执行代理。

同时保留一个诊断字段：

```text
profitable_after_cost = future_gross_return > estimated_roundtrip_cost
```

但不另训练大量 classifier。

## 6.4 决策规则

只做 long / flat。

固定三组候选阈值，不再搜索更多：

```text
A: enter > 45 bp, exit < 15 bp
B: enter > 60 bp, exit < 15 bp
C: enter > 75 bp, exit < 30 bp
```

这是 hysteresis，不允许一个阈值上下反复切换。

每次新开仓后至少持有 2 小时，除非 risk engine 强制退出。

position target：

```text
single asset <= 30% NAV
gross <= 60% NAV
```

继续使用已有 volatility scaling/risk contract。

目标不是提高分类 accuracy，而是显著降低：

```text
turnover
fees / gross alpha
```

## 6.5 新增 features（历史数据即可构建）

当前 10 个特征保留，扩展到约 30–45 个，禁止一次生成几百个指标。

### returns / trend

```text
log_return: 1,2,4,8,16,24 bars
ema_gap: 8/32, 20/100
rolling_high_distance: 24,96
rolling_low_distance: 24,96
```

### volatility / range

```text
realized_vol: 6,24,96
ATR-like normalized range: 14,48
close_location_in_bar
body_fraction
```

### volume / aggressor

```text
volume_z: 24,96
quote_volume_z: 24,96
taker_imbalance = 2*taker_fraction - 1
taker_imbalance rolling mean: 4,16
```

### cross-asset

对 BTC/ETH 同时生成：

```text
other_asset_return_1
other_asset_return_4
other_asset_return_16
relative_return_1
relative_return_4
rolling_corr_24
```

当前 Logistic 把 BTC/ETH 混合训练却没有明确 symbol indicator。v2 必须：

```text
增加 is_BTC / is_ETH categorical indicator
```

或训练独立模型；首选 pooled model + symbol indicator，避免模型数翻倍。

### seasonality

```text
hour_sin/hour_cos
weekday_sin/weekday_cos
```

只作为候选输入，不单独据此交易。

## 6.6 研究数据边界

由于旧 2024-04 ~ 2026-01 OOS 已经被查看，从现在起：

```text
2022-01-01 ~ 2026-03-01
```

整体视为 development history。

采用 purged expanding/rolling CV 做模型和阈值选择；这些 CV 结果只能写作 development evidence。

最后只冻结一个 v2 candidate。

然后：

1. 可一次消费 2026-03..08 locked historical test；
2. 无论结果如何，真正权威结果仍是 2026-10-01 之后 forward。

---

# 7. Baseline 必须加强

当前只拿 B2 EMA20/100 作为主要 comparator 太弱，不足以支持“打败传统策略”。

新增两个低成本固定 baseline：

## B3 Donchian Trend

```text
interval = 1h
entry = 55h high breakout
exit = 20h low breakout
long/flat
same vol target / same risk limits / same costs
```

## B4 Slow Momentum

```text
interval = 1h
signal = 7-day return > 0 AND price > EMA168
long/flat
same vol target / same risk limits / same costs
```

最终 v2 比较对象：

```text
Cash
BuyHold
EMA20/100
Donchian55/20
SlowMomentum
```

Grid 暂不放入 v2 acceptance，因为 1m OHLC 对网格的 intraminute fill order 有路径歧义。

后续若加 Grid，必须采用保守 intraminute ordering 或实时 shadow grid，不能使用“high/low touched = 免费成交”。

v2 candidate 至少要：

```text
净收益 > 0
且 risk-adjusted performance 优于三个主动传统 baseline 的中位数
```

不要只要求赢一个负收益 B2。

---

# 8. 立即启动 Microstructure Collector v1（与 Research v2 并行）

这是当前最重要的新数据工程。

## 8.1 不保存长期 raw full L2

40GB 磁盘约束下，不做 full-depth 永久存储。

第一版只增加：

```text
bookTicker
aggTrade
```

BTCUSDT、ETHUSDT。

当前 bookTicker 已收到：

```text
bid
ask
bid_qty
ask_qty
```

但长期 quote_minutes 只保存 spread 和 last bid/ask，必须把数量动态的聚合统计保存下来。

## 8.2 1-second feature buckets

每秒只保存聚合后的 compact features：

```text
mid
spread_bps
bid_qty_mean
ask_qty_mean
L1_imbalance_mean
L1_imbalance_last
microprice_offset_bps_mean
quote_update_count
bid_price_change_count
ask_price_change_count
OFI_L1
agg_trade_count
aggressive_buy_notional
aggressive_sell_notional
trade_flow_imbalance
trade_vwap
realized_return_1s
```

其中：

```text
L1 imbalance = (bid_qty - ask_qty)/(bid_qty + ask_qty)
```

microprice：

```text
(ask * bid_qty + bid * ask_qty)/(bid_qty + ask_qty)
```

OFI 使用 price/qty change 的标准 top-of-book event definition；必须写单元测试。

aggTrade aggressor side：按 Binance 字段 `m` 明确解释，不允许凭猜测写正负号。

## 8.3 聚合

从 1s feature 再生成：

```text
5s
30s
1m
```

统计：mean/std/min/max/last/sum，按 feature 语义选择。

## 8.4 存储预算

长期只保留聚合 feature Parquet。

raw WebSocket event 只保留 rolling debug buffer：

```text
<=24 hours
<=4 GB hard cap
```

超过自动删除最旧 raw 分片；不得删除 feature store 和审计记录。

microstructure 长期 feature 目标：

```text
180 days <= 8 GB
```

如果 24h 实测投影超过，减少存储字段/改 5s，不允许突破 40GB 总上限。

## 8.5 何时允许建模

```text
<14 days: 只允许数据质量/特征稳定性研究
14–30 days: 允许 predictive diagnostics，不允许宣称 alpha
>=30 days: 允许预登记 microstructure ML experiment
```

不要因为前几天 Sharpe 很高就提前上线。

---

# 9. Microstructure Model v1（30 天数据后）

仍然先使用：

```text
Logistic
LightGBM/XGBoost
```

而不是 DeepLOB/Transformer。

预测目标：

```text
5s / 30s future mid-price move
```

先测 predictive value，再测 trading value。

必须同时报告：

```text
R² / logloss / AUC（按任务）
net PnL
taker cost sensitivity
turnover
signal decay by horizon
fold-by-fold sign stability
```

如果简单模型都没有稳定 signal，不允许用更深网络“救结果”。

只有 microstructure LightGBM/XGBoost 在至少 30–60 天滚动 OOS 下显示稳定增量后，才允许进入 TCN/Transformer。

---

# 10. 模型运行层必须从 Logistic 专用改成通用 Predictor

当前 `candidate_paper.py` 手工读取：

```text
FEATURE_NAMES
scaler_mean
scaler_scale
coefficients
intercept
```

这把 live pipeline 与 Logistic 强绑定。

不要重写整个 shadow/execution 状态机，只抽象 predictor。

新增：

```python
class FrozenPredictor(Protocol):
    model_type: str
    schema_version: str
    feature_names: tuple[str, ...]
    decision_interval: str
    prediction_horizon: str
    def predict(self, features: dict[str, float]) -> dict: ...
```

实现：

```text
LogisticJsonPredictor
LightGBMPredictor
XGBoostPredictor (可选；如果最终未选中可以只用于研究)
```

模型 release hash 必须绑定：

```text
model bytes
feature schema
execution contract version
cost contract version
risk contract version
training cutoff
```

candidate engine 只读取统一输出：

```text
expected_return
confidence(optional)
target_weight
```

不再知道底层是线性模型还是树。

### 验收

同一 feature vector：

```text
research inference == exported artifact inference == live predictor inference
```

浮点容差固定并测试。

---

# 11. 资源策略更新（用户硬上限：40GB disk / 8GB RAM / 24GB VRAM）

当前 5GB cgroup 非错误，只是保守。

推荐：

```text
always-on collector/shadow aggregate <= 2 GB RAM
bounded training <= 5.5 GB RAM
combined hard ceiling <= 7 GB
leave >=1 GB margin
swap = 0
```

若现有 5GB 总硬限没有阻塞训练，可以继续保持；不得为了“用满资源”而改。

GPU：

```text
Research v2 LightGBM/XGBoost: GPU optional
Microstructure tabular: GPU optional
TCN/Transformer: only after gate
```

GPU 使用时：

```text
VRAM soft target <= 20 GB
stream batches from Parquet
不要把全数据加载进 8GB host RAM
```

---

# 12. 新的停止/推进门槛

## Gate R2：Nonlinear historical

LightGBM/XGBoost v2 只有同时满足：

```text
development CV aggregate net return > 0
median active-baseline excess return > 0
net Sharpe >= 0.6
2x fee scenario >= 0
2x slippage scenario >= 0
MDD <= 15%
fees / positive gross alpha < 60%
>= 30 independent round trips
```

才允许冻结一个 candidate 去做 locked historical test。

如果失败：

```text
不要调 100 次参数
不要上 Transformer
```

进入 Microstructure data 路线。

## Gate M1：Microstructure tabular

至少 30 天数据，滚动 OOS：

```text
predictive lift signs stable across >=60% folds
net result after conservative taker cost > 0
2x cost scenario not catastrophically negative
```

若失败：继续收集到 60–90 天后只允许一次复验。

如果 60–90 天仍无稳定 signal：停止短周期 microstructure 深模路线。

## Gate DL：Deep model

只有：

```text
LightGBM/XGBoost microstructure OOS Sharpe >= 0.8
and net positive after cost
```

才允许 TCN/Transformer。

RL 继续禁止，直到 execution alpha/short-horizon signal 已被证明。

---

# 13. 本轮 Codex 工单，严格按顺序执行

## A01 — Execution parity

- 实现 `ExecutionContractV2`
- historical canonical latency 改为 1m
- historical/live parity test
- 旧报告标记 legacy，不覆盖

**完成前不得启动新 alpha 研究。**

## A02 — Strong baselines

- B3 Donchian55/20
- B4 SlowMomentum
- 全部用 V2 execution contract
- 生成统一 baseline report

## A03 — Generic predictor interface

- 从 CandidatePaperEngine 抽离 Logistic 专用 inference
- 旧 Logistic predictor 保持兼容
- 不改 execution/account state machine

## A04 — Research v2 feature library

- 只实现本文约 30–45 个历史 causal features
- historical/live 可复用的 feature definitions 写单元测试
- 不安装 Torch

## A05 — LightGBM/XGBoost v2

- 最多 3 configs/model
- 1h only
- 4h gross return regression
- 三组预登记 hysteresis threshold
- 输出完整 CV 和成本归因

## A06 — Freeze or STOP

若 R2 Gate 通过：

```text
freeze exactly one candidate
```

若失败：

```text
record STOP_v2
```

禁止结果驱动扩大参数搜索。

## A07 — Microstructure collector

与 A04/A05 可并行，但不能影响采集稳定性：

- aggTrade
- persistent bookTicker quantity aggregates
- 1s compact features
- 24h raw ring buffer
- 180d storage projection

## A08 — True forward v2

无论 historical locked test 结果如何：

```text
true_forward_start >= 2026-10-01
```

不同 model version 的 forward record 绝不拼接。

---

# 14. 现在不要做的事情

明确禁止 Codex 下一轮自行扩展：

```text
MARL
world model
LLM trading agent
news sentiment
on-chain model
full L2 permanent storage
Nautilus migration
mainnet real-money route
multi-exchange arbitrage
large Optuna sweep
hundreds of TA indicators
```

这些都不是当前瓶颈。

---

# 15. 对当前几个具体实现的评价

## 做得好的，保留

### `research.py`

- development-only filtering
- purge/embargo
- scaler 只 fit train
- validation-only config selection
- immutable research state
- holdout 不自动消费

这些都保留。

### `holdout.py`

一次消费 ticket + receipt 的思路很好，继续使用。

但 v2 报告里把 2026-03..08 改称 `LOCKED_HISTORICAL_TEST`，不能把它和真正 forward 混写。

### `execution.py` / `testnet.py`

UNKNOWN 状态不盲重发、Decimal、默认 deny、账户对账等都值得保留。

不要因为暂时停止执行层开发而删除这些代码。

### resource/disk guard

保留。40GB 预算下目前占用很低，有足够空间增加 compact microstructure features。

## 需要修的

### `backtest.py`

默认 `latency_minutes=0` 与 live 的 next-minute contract 不一致。

这是最高优先级。

### `candidate_paper.py`

模型 inference 与 Logistic 强绑定，需要抽象 predictor。

### `collector.py`

实时收到 bid/ask quantity，但长期聚合没有保留足够的数量动态；没有 aggTrade。

当前 collector 对执行健康很好，对 alpha 研究不够。

### `PROJECT_PLAN_v2.md`

删除/修改：

```text
Logistic 不胜 B2 -> 停止所有模型升级
```

替换为本文的“允许一次严格受控 nonlinear v2；失败后转 microstructure，而不是大搜参”。

---

# 16. 成功定义更新

近期目标不要写“完成交易系统”。

定义三个独立状态：

```text
ENGINEERING_READY
ALPHA_CANDIDATE
COMPETITIVE_FORWARD
```

### ENGINEERING_READY

当前已经接近/部分达到。

### ALPHA_CANDIDATE

至少一个冻结策略通过 R2 或 M1 Gate。

### COMPETITIVE_FORWARD

同一个冻结版本，在真正部署之后的未来数据中：

```text
>= 180 days
net return > 0
Sharpe >= 1.0
MDD <= 12%
2x cost nonnegative
beats active baseline median on risk-adjusted basis
```

只有第三个状态才允许称“有竞争力”。

---

# 17. 研究依据（用于方向校验，不作为收益承诺）

1. Binance Spot WebSocket 官方目前支持实时 `bookTicker`（包含 best bid/ask price 与 quantity）以及 top-5/10/20 partial depth，可用于低存储成本的 microstructure features。  
   https://developers.binance.com/zh-CN/docs/products/spot/testnet/web-socket-streams

2. 2025 年针对 BTC/USDT LOB 的公开研究比较 Logistic/XGBoost/DeepLOB 等，报告输入预处理和特征质量可能比继续堆深层网络更重要，因此本项目仍应先做 tabular/microstructure baseline。  
   https://arxiv.org/abs/2506.05764

3. 2026 年一项 BTC/USDT OFI 实证在约 7、9、17 天样本扩展时 OOS 结论多次变化，说明短样本 microstructure 结果必须反复 falsify，不能几天数据就宣布成功。  
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7227998

---

# 18. 最终执行指令

Codex 收到本文件后，不要解释，不要重新规划整个项目，也不要推倒现有代码。

直接：

```text
1. 阅读现有 PROJECT_PLAN_v2 / DELIVERY_STATUS / PROGRESS
2. 将本文件登记为 v3 override（只覆盖冲突部分）
3. 从 A01 开始执行
4. 每完成一个工单更新独立 acceptance report
5. 不覆盖旧报告
6. 不消费原 holdout，除非 v2 确实冻结且用户另行明确授权
7. 不启用真实资金
```

如果发现本文件与已有实现有冲突，优先保持旧证据不可变，然后为新版本另开 schema/protocol/version；禁止通过修改历史记录“修复”冲突。

