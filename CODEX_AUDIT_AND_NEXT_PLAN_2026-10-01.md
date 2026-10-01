# Coin Quant GitHub 审计与下一阶段执行指令 v4

日期：2026-10-01  
审计对象：`https://github.com/snowycat1234/coin`  
审计基准：GitHub `main` 当前 HEAD `3b0f470cdbe40eaa51fabd6a0707fb4f03d9eb1f`

> 本文可以直接交给 Codex 执行。不要推倒重来，不覆盖旧实验，不消费当前锁定历史测试，不启用真钱。

## 1. 总体结论

当前工程**没有做歪**。和上一轮审计相比，几个关键问题已经真正修掉：

1. `ExecutionContractV2` 已统一成交时间/成本合同；
2. 正式历史回测默认 `latency_minutes=1`；
3. historical / shadow 有 cross-engine parity 测试；
4. `FrozenPredictor` 已从 Logistic 专用实现抽象为通用模型接口；
5. 40 个小时级因果特征共享同一 batch/incremental transition；
6. LightGBM / XGBoost 按严格预登记预算运行，没有无限调参；
7. 非线性 v2 未通过后正确记录 `STOP_v2`，没有追参数；
8. A07 已开始收集 `bookTicker + aggTrade` 紧凑微观结构数据；
9. 40 GB 磁盘、5 GB RAM、无 swap 的资源纪律保持良好；
10. 没有擅自启封 2026-03 ~ 2026-08 的 locked historical test。

当前最准确的状态：

```text
ENGINEERING_CORE = READY_FOR_RESEARCH
HOURLY_ALPHA_V2 = FALSIFIED
MICROSTRUCTURE_DATA = ACCUMULATING
ALPHA_CANDIDATE = NONE
COMPETITIVE_FORWARD = NOT_STARTED
```

这不是失败的工程，而是第一轮 alpha 假设被严格证伪后，进入第二类信息源。

## 2. 当前项目状态评估

| 维度 | 当前评价 | 说明 |
|---|---:|---|
| 可复现性 / 防数据泄漏 | 9/10 | hash、cutoff、protocol、purge、不可重跑状态较严格 |
| execution correctness | 8.5/10 | 上轮 latency mismatch 已修复 |
| 风控 / 故障恢复工程 | 8.5/10 | 已超过当前 alpha 研究实际所需 |
| 资源约束工程 | 9/10 | 当前约 9 GB 总占用、约 2.1 GB 历史峰值 RAM |
| 小时级 alpha 探索 | 已完成且失败 | `STOP_v2` 是有效结论 |
| 微观结构数据工程 | 约 70% | collector 已有，真实样本时间太短 |
| 微观结构 alpha 研究 | 0% | 尚未满足时间门槛 |
| 可冻结盈利 candidate | 0 | 当前没有 |
| TRUE_FORWARD | 0 天 | 没有 candidate，不能启动 |

## 3. A05 / A06 的 STOP_v2 不要复活

正式结果：

| 配置 | 净收益 | Sharpe | Fee×2 | Slippage×2 |
|---|---:|---:|---:|---:|
| LGB_A | -5.2064% | -0.599 | -12.7093% | -8.2724% |
| LGB_B | +1.5912% | 0.212 | -2.2161% | +0.0464% |
| LGB_C | +0.2429% | 0.052 | -1.6218% | -0.5095% |
| XGB_A | -2.7795% | -0.374 | -7.0314% | -4.5080% |
| XGB_B | +0.8951% | 0.141 | -3.3337% | -0.8187% |
| XGB_C | +2.4724% | 0.361 | -0.4639% | +1.2847% |

主动传统 baseline 中位数净收益约 `5.2035%`。最好的 XGB_C 虽然 base 为正，但 Sharpe 只有 0.361，落后主动基线中位数，而且 `fee×2` 转负。

因此禁止：

```text
- 再加大量 XGB/LGB 参数
- 反复改 threshold 直到变正
- 降低成本假设
- 改 hold time 后把已看历史重新称为盲测
- 直接用 Transformer “救”小时策略
```

旧结果原样保留。

## 4. 当前最值得立即修的微观结构问题：aggTrade gap 判定

当前 `src/quant/microstructure.py` 对 aggTrade 使用：

```python
if old and identity != old["id"] + 1:
    bucket["flags"] |= AGG_GAP
```

其中 `identity = a`，即 aggregate trade ID。

Binance 官方文档定义：

```text
a = Aggregate trade ID
f = First trade ID
l = Last trade ID
```

但没有把 `next a == previous a + 1` 写成正式数据完整性合同。因此不要仅凭 `a` 跳号就认定确定丢包。

### 新规则

保存：

```text
last_agg_id
last_raw_trade_id = previous l
```

确定 raw trade gap：

```text
current.f > previous.l + 1
```

此时才设置：

```text
AGG_GAP
RAW_TRADE_ID_GAP
```

若：

```text
current.f == previous.l + 1
but current.a != previous.a + 1
```

只记录：

```text
AGG_ID_JUMP_UNCONFIRMED
```

不要单独把 bucket 标成 INVALID。

若 `current.f <= previous.l`，按 duplicate / overlap / out-of-order 单独审计。

原则：不把官方没有承诺连续的字段当作唯一硬性丢包证明。

## 5. A07 schema 现在应做最后一次小修订

A07 真实数据尚未达到 24h/14d/30d 门槛，现在是最后一个低成本改 schema 的时点。

当前 1s 行保存 `mid` 和 bucket 内平均 `spread_bps`。未来为了构造更真实的可成交标签，需要 bucket 末端 BBO。

在长期行中只新增两个字段：

```text
spread_bps_last
l1_total_depth_last
```

这样：

```text
mid_last + spread_bps_last
    -> 可重构 best_bid_last / best_ask_last

L1_imbalance_last + l1_total_depth_last
    -> 可重构 bid_qty_last / ask_qty_last
```

不需要额外保存完整 BBO 四字段。

### 版本规则

不要修改已有 `microstructure_l1_v1` 文件。

新建：

```text
microstructure_l1_v2
```

新 database / store；v1 保留为 QA evidence，不拼接 v2 的 14/30/60 天资格。

## 6. bookTicker 用 receipt-time bucket 保持不变

Binance Spot `bookTicker` 当前提供：

```text
u,s,b,B,a,A
```

没有交易所事件时间 `E/T`。因此当前：

```text
receipt-time bucketing
+ monotonic/wall-clock incident detection
+ reconnect/session flags
```

是合理方向。不要人为造 exchange timestamp。

## 7. 不要把 raw-scale 特征直接喂 pooled BTC+ETH 模型

A07 当前保存的一些字段高度非平稳：

```text
OFI_L1
bid_qty_mean
ask_qty_mean
aggressive_buy_notional
aggressive_sell_notional
trade_vwap
quote_update_count
agg_trade_count
```

未来模型前固定派生：

```text
ofi_depth_norm = OFI_L1 / (bid_qty_mean + ask_qty_mean + eps)

l1_depth_total = bid_qty_mean + ask_qty_mean
log_l1_depth = log1p(l1_depth_total)

trade_notional = aggressive_buy_notional + aggressive_sell_notional
log_trade_notional = log1p(trade_notional)

trade_flow_imbalance =
    (buy_notional - sell_notional) /
    (buy_notional + sell_notional + eps)

vwap_offset_bps = (trade_vwap / mid - 1) * 10000

log_quote_updates = log1p(quote_update_count)
log_trade_count = log1p(agg_trade_count)
quote_trade_ratio = log1p(quote_update_count) - log1p(agg_trade_count)
```

已有的：

```text
L1_imbalance_mean
L1_imbalance_last
microprice_offset_bps_mean
spread_bps
```

继续保留。

对 scale-heavy 字段做**每个 symbol 独立、严格 causal** 的 EWM normalization：

```text
half-life = 1 hour
```

计算当前 z-score 时必须先使用过去状态，再用当前样本更新状态；禁止 global fitted scaler。

## 8. 微观结构研究的时间门槛

### 0–14 天

只做：

```text
data completeness
quality flags
range checks
storage projection
session continuity
feature distributions
```

禁止 model selection。

### 14–30 天

允许：

```text
feature autocorrelation
future-return correlation
signal decay
missingness vs volatility
BTC/ETH stability comparison
```

状态固定：

```text
DIAGNOSTIC_ONLY
```

### 30 天

允许第一次 `MICROSTRUCTURE_PILOT`，只能判断方向是否值得继续，不能产生 `ALPHA_CANDIDATE`。

### >=60 天

才允许第一次 `FREEZE_ELIGIBLE_MICROSTRUCTURE_STUDY`。通过后才能冻结 candidate。

## 9. 30 天 Pilot 固定方案

collector 继续存 1s，模型输入使用 5s 聚合。

输入只使用：

```text
spread
imbalance
microprice
normalized OFI
normalized depth
trade-flow imbalance
trade activity
quote/trade intensity
short realized return
BTC/ETH cross signal
```

不引入整套 TA 指标库。

固定两个 horizon：

```text
30s  = predictive diagnostic
300s = economic horizon
```

模型仅：

```text
P0 = Ridge regression
P1 = LightGBM one fixed config
P2 = XGBoost one fixed config
```

无 Optuna，无大网格搜索。

Pilot 只回答：

```text
1. 是否存在可复现预测能力？
2. 信号衰减多快？
3. 成本前是否达到有经济意义的量级？
```

## 10. 60 天正式微观结构研究协议

达到至少 60 个真实 UTC 日后，先生成并冻结：

```text
configs/experiments/microstructure_v1.json
```

### Split

```text
train = 14 days
test = 7 days
stride = 7 days
embargo = 5 minutes
```

至少 6 个完整 OOS folds；不足则 `INSUFFICIENT_EVIDENCE`，不缩短 test。

### Primary label

主任务使用 5 分钟 executable gross return：

```text
decision_time = complete 5s feature bucket available
entry = first valid 1s best ask at/after decision + 1 second
exit_time = entry_time + 300 seconds
exit = first valid best bid at/after exit_time
```

entry/exit BBO 若超过 2 秒不可得，该样本 `INVALID_LABEL`。

标签：

```text
gross_exec_return = future_bid / entry_ask - 1
```

spread 已通过 ask/bid 自然进入标签。

### Cost

Base：

```text
entry fee = 10 bp
exit fee  = 10 bp
entry extra slippage/impact = 4 bp
exit extra slippage/impact  = 4 bp
```

额外 cost floor = 28 bp，再加固定 5 bp safety buffer。

唯一交易阈值：

```text
predicted_gross_exec_return > 33 bp
```

不要搜索 20/25/30/35/40。

压力测试：

```text
fee_x2
slippage_x2
```

### Trading policy

```text
long / flat
one position per symbol
fixed 5-minute hold
no overlapping trades on same symbol
single asset <= 30% NAV
gross <= 60% NAV
```

risk engine 仍可提前强制退出。模型不能自由决定 hold time。

### Models

只允许：

```text
Ridge
LightGBM
XGBoost
```

每类一个预登记配置。

禁止：

```text
Optuna
large grid search
Transformer
TCN
RL
```

## 11. Microstructure Gate M2

只有全部满足才可冻结：

```text
>= 6 complete rolling OOS folds
aggregate net return > 0
net Sharpe >= 0.6
>= 60 independent completed trades
positive net result in >=60% OOS folds
fee_x2 net >= 0
slippage_x2 net >= 0
MDD <=15%
no single fold contributes >60% of total positive PnL
all capacity/risk limits respected
```

同时报告：

```text
prediction correlation / IC
30s signal decay
300s regression R²
gross alpha
spread cost
fees
slippage
net alpha
```

三个模型全部失败：

```text
STOP_MICRO_L1
```

不追加大量 config。

## 12. L1 之后只允许一次 compact L5 分支

当前不要实现。

只有 A14 完成，且出现：

```text
有稳定 predictive structure
但 L1 economic edge 不够稳
```

才允许新增：

```text
partial depth 5 levels @100ms
```

实时只计算并长期保存 1s compact features：

```text
L5 bid depth
L5 ask depth
L5 imbalance
weighted microprice
depth slope
depth concentration
L1-vs-L5 imbalance divergence
```

不长期保存 raw full-depth，不做 diff-depth 永久归档。

## 13. 如果 predictive signal 存在但 taker 成本杀掉，单开 maker feasibility

以后必须区分：

```text
NO_PREDICTIVE_EDGE
```

与：

```text
PREDICTIVE_EDGE_BUT_TAKER_UNECONOMIC
```

只有在 60d 研究中满足：

```text
predictive lift stable
gross strategy positive
net failure 主要来自 fee/spread/slippage
```

才允许建立独立：

```text
E1_MAKER_FEASIBILITY
```

研究 post-only fill probability / adverse selection / cancel-reprice。

如果连 predictive signal 都没有，禁止靠更乐观 maker 假设“救”策略。

## 14. 任何 TRUE_FORWARD candidate 启动前重新做联合容量投影

A03 的旧投影：

```text
normal ~27.832 GB
stress ~35.752 GB
```

已非常接近 36 GB stop-new，而且未来 A07 还会增长。

启动任何 candidate 前必须重跑：

```text
COMBINED_180D_CAPACITY_PROJECTION
```

同时计入：

```text
current VHD
current project files
A07 feature projection
A07 raw 4GB ring cap
candidate ledger
shadow state
reports
model artifacts
1GB working temp allowance
```

要求：

```text
expected <=32GB
stress <=36GB
hard <=40GB
```

如果超限，先缩 raw retention / report verbosity / feature representation；不得删除 frozen feature history 或审计证据。

## 15. RAM / GPU 策略保持不变

当前 5 GB RAM hard limit 没有阻碍研究，所以不要为了“有 8 GB 可用”主动放宽。

继续：

```text
5GB total hard limit
swap = 0
```

GPU 暂时不用是正确决定。

只有 tabular microstructure 在真实 rolling OOS 同时表现出 predictive + economic edge 后，才允许 TCN / Transformer。

## 16. 明确停止扩张的模块

下一阶段不要新增：

```text
mainnet execution
Testnet orchestration feature expansion
extra order-state abstractions
multi-exchange router
futures live execution
Nautilus migration
MARL
world model
LLM trader
news sentiment
on-chain model
full L2 archive
large hyperparameter search
```

现有 execution/testnet 代码保留和回归，但不扩展。

## 17. 下一轮 Codex 工单

### A09 — Microstructure correctness patch

1. aggTrade gap 使用 `f/l` raw trade IDs 判定确定缺口；
2. `a` 跳号单独审计，不单独 invalidate；
3. 新增 `spread_bps_last`、`l1_total_depth_last`；
4. schema/version -> `microstructure_l1_v2`；
5. v1 完全保留。

Synthetic tests 必须覆盖：

```text
a连续 + raw连续
a跳号 + raw连续
a跳号 + raw缺口
duplicate
overlap
out-of-order
reconnect
```

### A10 — Normalized feature view

实现独立：

```text
src/quant/micro_features_v2.py
```

不改 collector 热路径；实现第 7 节派生特征和 causal per-symbol EWM normalization。

验收：同一 source events 的 batch / incremental feature vector 一致。

### A11 — Restart A07 qualification under v2

v1 资格时间不拼接。重新启动：

```text
24h -> 14d -> 30d -> 60d
```

24h 先验收无 silent gap、资源/存储投影和 schema 稳定性。

### A12 — 14-day diagnostic

只做 QA、stationarity、signal decay 和 univariate diagnostics；状态固定 `DIAGNOSTIC_ONLY`。

### A13 — 30-day pilot

固定 Ridge + 1 LGB + 1 XGB；30s diagnostic + 300s economic horizon；只能输出 `PROMISING/NOT_PROMISING`。

### A14 — 60-day preregistered study

先冻结 protocol；按 14d/7d/7d、5m embargo、至少 6 OOS folds；使用固定 cost/policy/Gate。

结果只能：

```text
ALPHA_CANDIDATE
STOP_MICRO_L1
INSUFFICIENT_EVIDENCE
```

### A15 — Candidate handling

只有 A14 为 `ALPHA_CANDIDATE` 时冻结一个模型。之后才由用户另行决定是否消费 locked historical test。

Candidate 的 TRUE_FORWARD 必须从 candidate **freeze 后**开始，不能把 2026-10-01 到 freeze 日期之间的数据事后补成 forward。

### A16 — Conditional compact L5

只有 A14 完成且满足本文第 12 节条件才启动。

## 18. locked historical test 继续封存

```text
2026-03 ~ 2026-08 = LOCKED_HISTORICAL_TEST
```

当前没有 candidate：

```text
DO NOT OPEN
```

holdout 的价值来自只给真正冻结、预先过 gate 的候选一次机会。

## 19. PRISTINE_RAW_DATA 与 CANDIDATE_FORWARD_DATA 分开

从 2026-10-01 起收到的数据可以叫：

```text
PRISTINE_RAW_DATA
```

但某 candidate 若在日期 F 才冻结，则它自己的：

```text
CANDIDATE_FORWARD_DATA
```

只能从 `>=F` 开始。

不能把 freeze 前已经看过/用于研发的数据事后纳入其 forward record。

## 20. 路线图

```text
小时 OHLCV Logistic
    -> FAIL

小时 40-feature LightGBM/XGBoost
    -> STOP_v2

实时 L1 + trades compact data
    -> CURRENT

30d pilot
    -> predictive feasibility

60d prereg tabular microstructure
    -> candidate / STOP

if predictive but cost-limited:
    -> maker feasibility

if L1 information insufficient but useful structure exists:
    -> compact L5

only if tabular proves edge:
    -> TCN / Transformer

only after short-horizon alpha + execution value proven:
    -> RL execution
```

## 21. Codex 执行要求

收到本文后：

```text
1. 不重新规划整个项目
2. 不覆盖任何 STOP_v2 / v1 / acceptance evidence
3. 登记本文为下一版本 override
4. 从 A09 开始
5. A09 完成并验收后重新启动 v2 微观数据资格计时
6. 不消费 locked historical test
7. 不启用真钱
8. 不扩执行层
9. 每个工单完成才提交 GitHub
10. 所有失败结果同样保存
```

若本文和冻结旧证据冲突：旧证据不可变，新版本另开 schema/version/store。

## 22. 本次审计依据

主要核对：

```text
README.md
PROJECT_PLAN_v2.md
docs/GOALS.md
docs/PROGRESS.md
CODEX_AUDIT_AND_NEXT_PLAN_2026-09-30.md

src/quant/backtest.py
src/quant/execution_contract.py
src/quant/execution_parity.py
src/quant/predictor.py
src/quant/features_v2.py
src/quant/research_v2.py
src/quant/microstructure.py

configs/experiments/nonlinear_v2.json

reports/generated/A05_NONLINEAR_V2/REPORT.md
reports/generated/A05_NONLINEAR_V2/summary.json
reports/A06_NONLINEAR_RESEARCH_ACCEPTANCE.json
```

本次是 GitHub source + acceptance artifact audit，不是在用户 WSL 上重新独立执行整套 test suite。

## 23. 官方资料

Binance Spot WebSocket Market Streams：

https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams

当前文档明确：

- `aggTrade` 定义 `a/f/l/E/T/m`；
- `m` 表示 buyer 是否为 maker，因此 `m=true` 时 taker/aggressor 是卖方；
- `bookTicker` 提供 best bid/ask price/quantity；
- `bookTicker` payload 没有 exchange event timestamp；
- Partial Book Depth 支持 5/10/20 levels，100ms 或 1000ms。

## 24. 最终结论

当前工程不需要“救”。下一阶段应该：

```text
少写基础设施
多积累真实新数据
控制研究自由度
把真实 BBO 和成本直接放进标签/决策
先证明简单模型有 edge
再允许复杂模型
```

截至本次审计：

```text
工程方向：正确
研究纪律：很好
小时级 alpha：失败，应接受失败
微观结构方向：正确，值得继续
当前可交易 candidate：没有
现在是否该上 GPU/Transformer：否
现在是否该启封 holdout：否
下一步：A09 -> A10 -> A11，然后按真实 14/30/60 天门槛推进
```
