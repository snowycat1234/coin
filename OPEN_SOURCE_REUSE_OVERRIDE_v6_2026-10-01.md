# OPEN-SOURCE-REUSE RESEARCH OVERRIDE v6
## 少造轮子、快速科研版

日期：2026-10-01  
目标仓库：`https://github.com/snowycat1234/coin`

---

# 0. 核心目标

从现在开始，项目遵循：

```text
REUSE FIRST
ADAPTER SECOND
CUSTOM MODEL LAST
```

任何模块开始编码前必须先回答：

```text
是否已有成熟开源实现？
```

如果有：

```text
优先依赖 / 包装 / 轻量适配
```

而不是重新实现。

项目真正允许自研的核心只剩：

1. Binance 数据转换与统一 schema；
2. 因果标签；
3. 成本感知的经济评价；
4. cross-market / participant-flow 研究逻辑；
5. 最后真正有必要的新模型结构。

---

# 1. 当前工程保持不动

以下已有内容继续冻结，不重写：

```text
ExecutionContractV2
backtest / parity
FrozenPredictor
risk / accounting
hourly STOP_v2 evidence
A07 live microstructure collector
locked historical holdout
```

本文件不要求迁移到 Nautilus、Freqtrade 或 Hummingbot。

原因：

```text
当前瓶颈已经不是 trading engine。
```

---

# 2. 开源复用总表

| 功能 | 采用项目 | 使用方式 | 是否自己重写 |
|---|---|---|---|
| Binance 历史数据下载 | `binance/binance-public-data` | 直接复用官方 URL / helper / CHECKSUM 规则 | 否 |
| TCN | `paul-krug/pytorch-tcn` | Python dependency | 否 |
| LOB Transformer / MLPLOB / DeepLOB | `LeonardoBerti00/TLOB` | MIT，固定 upstream commit，写 adapter | 否 |
| Representation learning | `zhihanyue/ts2vec` | MIT，vendor 最小核心并适配当前 Torch | 否 |
| Online learning / drift | `online-ml/river` | Python dependency | 否 |
| 通用时序备选模型 | `timeseriesAI/tsai` | 只在需要 PatchTST/TST 时启用 | 否 |
| LOB evaluation 思路 | `FinancialComputingUCL/LOBFrame` | 只参考方法，不复制代码 | 否 |
| LOB representation benchmark | `Financial-Simulation-Lab/LOBench` | 参考模型/任务设计，许可证确认前不 vendor | 否 |
| Hawkes | 现有开源 Hawkes 实现 | 只做 optional baseline；不自己写优化器 | 否 |

---

# 3. 许可证规则

## 可直接集成 / 适配

### Binance public data

官方仓库：

```text
https://github.com/binance/binance-public-data
```

MIT。

### TLOB

```text
https://github.com/LeonardoBerti00/TLOB
```

MIT。

允许：

```text
引用
修改
包装
保留 LICENSE / attribution
```

### TS2Vec

```text
https://github.com/zhihanyue/ts2vec
```

MIT。

允许将核心代码适配到当前 Python/Torch，但必须：

```text
保留 copyright
保留 LICENSE
记录 upstream commit
```

### River

```text
https://github.com/online-ml/river
```

BSD-3-Clause。

直接作为 dependency。

### pytorch-tcn

```text
https://github.com/paul-krug/pytorch-tcn
```

MIT。

直接作为 dependency。

---

## 不复制代码

### LOBFrame

```text
https://github.com/FinancialComputingUCL/LOBFrame
```

许可：

```text
CC BY-NC-ND 4.0
```

因此：

```text
只读论文 / README / 实验设计
不复制源代码
不修改后放入本项目
```

它主要用于提醒我们：

```text
预测 F1 高 != 可交易
```

并借鉴其交易层评价思想。

---

# 4. third_party 规范

如果需要 vendor MIT/BSD 源码，固定：

```text
third_party/
    tlob/
        UPSTREAM.md
        LICENSE
        ...
    ts2vec/
        UPSTREAM.md
        LICENSE
        ...
```

每个 `UPSTREAM.md` 写：

```text
repository
commit SHA
retrieval date
license
local modifications
```

禁止：

```text
复制代码后删除来源
```

优先级：

```text
pip dependency
>
git submodule / vendor
>
自己重写
```

---

# 5. 历史数据下载：不要自己造 downloader framework

直接采用 Binance 官方 public-data 目录结构。

官方明确提供：

```text
daily
monthly
aggTrades
trades
klines
Spot
USD-M Futures
```

并为压缩包提供：

```text
.CHECKSUM
```

## 实现方式

我们自己只写一个很薄的 orchestration wrapper：

```text
hf_fetch.py
```

职责：

```text
1. 构造 Binance 官方 URL
2. 下载 ZIP
3. 下载 CHECKSUM
4. sha256 verify
5. stream unzip
6. 调 feature converter
7. 成功后删除 ZIP / CSV
8. 写 manifest
```

不要再写：

```text
复杂重试框架
自定义 HTTP cache
数据镜像系统
```

HTTP 直接：

```text
httpx
```

即可。

---

# 6. 数据主线

立即建立：

```text
BTCUSDT Spot aggTrades
ETHUSDT Spot aggTrades

BTCUSDT USD-M aggTrades
ETHUSDT USD-M aggTrades
```

研究历史：

```text
2025-01-01 <= t < 2026-03-01
```

至少先完成：

```text
>= 180 days
```

---

# 7. 数据长期格式

最终长期只保留：

```text
5s trade-flow bars
```

Optional：

```text
1s labels / diagnostics
```

不要保存长期 raw aggTrades。

每个 5s bar：

```text
market
symbol
timestamp

OHLC
VWAP

trade_count
buy_count
sell_count

base_volume
quote_notional

aggressive_buy_notional
aggressive_sell_notional
flow_imbalance

mean_trade_size
max_trade_size
large_trade_share

mean_interarrival
std_interarrival

return_5s
signed_price_impact
```

Spot / Perp 统一 schema。

---

# 8. Dataset 不再自写窗口 materialization

建立 streaming dataset：

```text
Parquet shards
-> index of valid sequence endpoints
-> __getitem__ loads only required row group / shard
```

不要生成：

```text
25M × 256 × F
```

巨大 `.npy`。

如果 PyTorch DataLoader 足够：

```text
IterableDataset
```

否则：

```text
memory-mapped Arrow / Parquet row groups
```

所有模型复用同一个 Dataset API。

---

# 9. 模型 API 固定

所有外部模型都包成：

```python
class SequenceEncoder(nn.Module):
    def forward(self, x, mask=None):
        # x: [B, T, F]
        # return representation [B, D]
        ...
```

预测层统一：

```python
class MultiTaskHead(nn.Module):
    flow_30s
    flow_5m
    return_30s
    return_5m
    logrv_30s
    logrv_5m
```

这样：

```text
TCN
TLOB
TS2Vec
未来 PatchTST
```

都使用相同：

```text
dataset
loss
split
metrics
economic evaluation
```

禁止每个模型拥有自己的数据/评价代码。

---

# 10. TCN：直接用 pytorch-tcn

删除“自己写 TCN block”的计划。

依赖：

```text
pytorch-tcn
```

直接：

```python
from pytorch_tcn import TCN
```

配置固定两组：

## TCN-S

```text
channels = [64,64,96,96]
kernel = 3
causal = true
dropout = 0.1
skip connections = true
```

## TCN-M

```text
channels = [64,96,128,128,128]
kernel = 3
causal = true
dropout = 0.1
skip connections = true
```

外面只加：

```text
pooling
+
MultiTaskHead
```

不重写 causal conv。

---

# 11. Transformer：优先复用 TLOB，不手搓普通 Transformer

TLOB 官方仓库已经包含：

```text
TLOB
MLPLOB
DeepLOB
BiNCTABL
```

而且输入接口本身是：

```text
[B, seq_len, num_features]
```

因此本轮先适配两个：

```text
MLPLOB
TLOB
```

不要先自己写 vanilla Transformer。

## 使用方式

写：

```text
src/quant/research_fast/adapters/tlob_adapter.py
```

负责：

```text
our [B,T,F]
-> upstream model
-> latent / output
```

如果 upstream 模型强绑定 3-class head：

```text
只替换最后 head
```

保留：

```text
backbone
attention blocks
normalization
```

本轮实验明确写：

```text
TLOB architecture transferred from LOB setting to trade-flow feature matrix
```

不能声称等价于论文原设定。

---

# 12. 为什么必须跑 MLPLOB

TLOB 论文一个很重要的结论是：

```text
简单 MLP-based LOB model
可以非常强
```

所以我们不应该默认：

```text
Transformer > MLP
```

本轮 sequence benchmark 固定：

```text
XGBoost
TCN
MLPLOB
TLOB
```

四个主要模型。

---

# 13. Representation：直接复用 TS2Vec

删除自己设计：

```text
masked reconstruction v0
CPC v0
```

作为第一版 representation baseline。

直接采用：

```text
TS2Vec
```

官方实现支持：

```text
timestamp-level representation
causal sliding representation
```

非常适合我们的任务。

## 兼容策略

TS2Vec 官方依赖较老。

不要：

```text
安装它完整 requirements.txt
```

而是：

```text
vendor MIT 核心：
ts2vec.py
models/
必要 utils
```

适配当前：

```text
Python 3.12
current torch
numpy 2.x
```

只做兼容性修改。

所有改动记在：

```text
third_party/ts2vec/UPSTREAM.md
```

---

# 14. TS2Vec 使用方式

输入：

```text
[B,T,F]
```

先用 development train period 自监督预训练。

得到：

```text
z_t
```

然后做三个测试：

## R1 Linear Probe

冻结 encoder：

```text
Ridge / linear head
```

预测 F1-F4。

## R2 LightGBM on representation

冻结 encoder：

```text
TS2Vec latent
-> LightGBM
```

## R3 Fine-tune

只允许一个 fine-tune config。

比较：

```text
raw XGB
TCN
TLOB
TS2Vec+linear
TS2Vec+LGB
TS2Vec fine-tune
```

---

# 15. Online learning：直接用 River

删除自己实现：

```text
online scaler
ADWIN
incremental regression
rolling drift detector
```

直接使用 River。

第一版只做：

```text
StandardScaler
LinearRegression
ADWIN
```

可再增加一个官方增量树模型。

## Historical replay

严格：

```text
predict
-> 等 label 成熟
-> learn_one
```

不允许：

```text
learn then predict same sample
```

比较：

```text
Static
River online linear
weekly batch refit
```

---

# 16. River 在本项目中的定位

River 不负责：

```text
最终深度模型
```

它负责快速回答：

> 连最便宜的在线适应是否有价值？

如果 River online 已经比 static 改善：

```text
说明 drift adaptation 值得进一步研究
```

如果没有：

```text
不要立即发明复杂 continual-learning system
```

---

# 17. tsai：只作为可选 model zoo

当前不要求安装。

如果：

```text
TCN / MLPLOB / TLOB / TS2Vec
```

跑完以后仍需一个独立 generic time-series transformer baseline，

才增加：

```text
tsai
```

优先使用：

```text
PatchTST
TST
```

不要使用：

```text
20个 tsai architecture 全跑
```

最多一个 PatchTST。

---

# 18. LOBFrame：只拿研究方法，不拿代码

必须阅读它的思路：

```text
Deep Limit Order Book Forecasting
```

核心不是复制模型。

借鉴：

```text
forecast metric
与
operational/trading metric
分离
```

因此每个模型报告都同时包含：

```text
Prediction metrics
Economic metrics
```

不能只比较：

```text
accuracy
F1
MSE
```

---

# 19. LOBench：作为第二阶段 representation checklist

当我们真的有：

```text
L1/L5
```

后，再参照 LOBench 的任务拆分：

```text
reconstruction
prediction
imputation
transferability
```

当前 trade-flow sprint 不需要完整导入其框架。

不要因为看到一个 benchmark 就再迁移一套工程。

---

# 20. Hawkes：降级为 optional

Hawkes 不是当前主线。

规则：

```text
不自己实现 Hawkes optimizer
```

若找到许可清晰且能直接运行的开源 implementation：

```text
最多花 1 小时集成
```

否则：

```text
SKIP_HAWKES
```

它不能阻塞：

```text
TCN/TLOB/TS2Vec
```

---

# 21. 训练框架也不要造大系统

我们只需要一个：

```text
trainer.py
```

提供：

```text
AMP
gradient accumulation
early stopping on validation
checkpoint best
seed
gradient clipping
metrics
```

控制在：

```text
~300 LOC
```

以内。

不要造：

```text
自定义 Lightning
自定义 Hydra
自定义 experiment platform
```

已有 repo 的 protocol JSON 已够。

---

# 22. 模型搜索预算重新优化

原 v5 计划仍偏多。

现在有成熟 model zoo 后，第一阶段重点应该是：

```text
model diversity
>
parameter search
```

第一轮固定：

| 模型 | 配置 |
|---|---:|
| Ridge | 1 |
| XGBoost | 2 |
| TCN | 2 |
| MLPLOB | 1 |
| TLOB | 1 |
| TS2Vec + linear | 1 |
| TS2Vec + LGB | 1 |
| River online | 1 |

总计：

```text
10 directions/configs
```

不要 23 个。

第一轮只跑：

```text
1 seed
```

只有 top-3 才补：

```text
3 seeds
```

---

# 23. Target 也要减

第一轮不要六个 multitask target 全都拿来选模型。

Primary：

```text
future signed aggressive flow 5m
future executable return proxy 5m
```

Auxiliary：

```text
RV 5m
flow 30s
```

也就是说：

```text
2 primary
2 auxiliary
```

先不要 6 个同权 loss。

---

# 24. 为什么把 Flow 当主任务之一

我们的原始研究思想是：

```text
预测其他参与者下一步行为
```

所以不能只预测：

```text
return
```

核心行为标签：

```text
future net aggressive buy/sell flow
```

直接衡量：

> 未来 5 分钟主动买单还是主动卖单占优？

这是对“参与者行为”的可观测代理。

---

# 25. 新的模型结构

```text
                     historical Binance
                           |
           official binance-public-data pipeline
                           |
                    5s unified dataset
                           |
           +---------------+---------------+
           |               |               |
        tabular        sequence        representation
      XGB/Ridge      TCN/MLPLOB/TLOB       TS2Vec
           |               |               |
           +---------------+---------------+
                           |
                 SAME evaluation harness
                           |
              flow / return / RV metrics
                           |
                 conservative economics
                           |
                      model ranking
                           |
                    online replay
                           |
                         River
```

---

# 26. 绝对不要再写这些

删除/禁止新实现：

```text
custom TCN convolution
custom transformer encoder
custom attention implementation
custom online scaler
custom ADWIN
custom generic contrastive framework
custom Binance download protocol
custom model zoo
custom experiment tracker
```

---

# 27. 仍然必须自己做的核心科研代码

真正值得我们写：

```text
binance -> unified trade-flow schema

spot/perp synchronization

participant-flow labels

cross-market lead-lag features

causal rolling normalization

economic cost evaluator

model adapter layer

representation evaluation

historical online replay protocol
```

这些才是项目的研究价值。

---

# 28. FR-v6 执行工单

---

## FR61 — Open-source registry

建立：

```text
docs/OPEN_SOURCE_REGISTRY.md
```

记录：

```text
name
repo
commit/version
license
how used
local modifications
```

验收：

```text
所有第三方代码来源可追踪
```

时间预算：

```text
<= 1 hour
```

---

## FR62 — Official Binance historical pipeline

使用：

```text
binance-public-data conventions
CHECKSUM
```

实现薄 wrapper。

不要 fork/重写官方项目。

验收：

```text
任意一天：
download
checksum PASS
convert
raw deleted
feature parquet produced
manifest saved
```

时间预算：

```text
<= 3 hours
```

---

## FR63 — Build 180d+ dataset

BTC/ETH × Spot/Perp。

至少：

```text
180 complete days
```

目标：

```text
2025-07-01 ~ 2026-02-28
```

若完成很快再向前扩。

验收：

```text
no missing date silently ignored
5s unified schema
<= 8GB persistent historical feature budget
```

---

## FR64 — Common sequence dataset API

只实现一次：

```text
Parquet -> [B,T,F]
```

所有模型复用。

验收：

```text
same sample index
same tensor
same label
across all adapters
```

---

## FR65 — Baseline

运行：

```text
Ridge
XGB-S
XGB-M
```

必须当日出结果。

---

## FR66 — pytorch-tcn integration

```text
uv add pytorch-tcn
```

写 wrapper。

不要自己实现 TemporalBlock。

跑：

```text
TCN-S
TCN-M
```

---

## FR67 — TLOB integration

固定上游：

```text
LeonardoBerti00/TLOB
```

记录 commit。

只导入/适配：

```text
MLPLOB
TLOB
```

第一阶段不要 DeepLOB。

跑：

```text
MLPLOB-1
TLOB-1
```

---

## FR68 — TS2Vec

vendor MIT 最小核心。

做：

```text
TS2Vec linear probe
TS2Vec -> LightGBM
```

不要自己写 CPC。

---

## FR69 — Online replay via River

```text
uv add river
```

运行：

```text
static linear
River online linear
weekly XGB refit
```

同 chronological replay。

---

## FR70 — Unified model leaderboard

自动生成：

```text
reports/fast_research/MODEL_LEADERBOARD.md
```

每个模型：

```text
flow IC
flow sign accuracy
return Pearson IC
return Spearman IC
RV rank IC
gross economic return
estimated cost
net return
turnover
Sharpe
MDD
GPU time
peak RAM
```

禁止只给 loss。

---

# 29. 第一轮晋级规则

Top 模型不是按单一 Sharpe。

每个方向先检查：

## Predictive Gate

至少满足一个：

```text
flow IC >= 0.03
or
return rank IC >= 0.02
```

且：

```text
>= 60% OOS folds same sign
```

阈值只是 sprint 筛选，不是生产标准。

## Stability Gate

不能：

```text
一个 fold 提供 >60% positive signal
```

## Economic diagnostic

记录：

```text
gross edge vs cost
```

即使 net <0，

如果：

```text
gross predictive edge clearly stable
```

仍保留为：

```text
PREDICTIVE_BUT_COST_LIMITED
```

---

# 30. 第二轮只保留 3 个

第一轮结束后：

```text
最多保留 3 个方向
```

例如：

```text
XGB
TLOB
TS2Vec
```

或者：

```text
TCN
MLPLOB
River
```

由实际结果决定。

只有 top-3：

```text
跑 3 seeds
做 ablation
做 regime split
```

其他停止。

---

# 31. 什么时候使用 DeepLOB

只有拿到真实：

```text
L5/L10 depth tensor
```

后。

不要把 DeepLOB 强行用于只有 trade-flow bar 的输入。

那时直接复用 TLOB repo 已有 DeepLOB。

---

# 32. 什么时候使用 LOBench / LOBFrame

有 L5 以后：

```text
LOBFrame = evaluation design reference
LOBench = representation task reference
TLOB = model zoo
```

不要再从头设计所谓：

```text
LOB benchmark v1
```

---

# 33. 什么时候使用 PatchTST / tsai

仅当：

```text
TCN 和 TLOB 结果都值得继续
```

且希望加一个 generic transformer。

 wtedy：

```text
uv add tsai
```

只跑：

```text
PatchTST
```

一个配置。

不要变成架构动物园。

---

# 34. GPU 预算进一步压缩

第一轮：

```text
TCN-S/M      <= 4 GPU-hours total
MLPLOB       <= 2
TLOB         <= 4
TS2Vec       <= 6
---------------------
target       <= 16 GPU-hours
```

实际 4090 可能远低于此。

只有 top-3 多 seed：

```text
追加 <= 20 GPU-hours
```

整个 sprint：

```text
<= 36 GPU-hours
```

---

# 35. Agent 额度预算

Codex 不得花大量上下文：

```text
重复审计已有 execution
```

建议：

```text
60% 数据 + 模型 + 实验
20% 结果分析
10% 核心 correctness tests
10% 文档
```

任何工单如果开始产生：

```text
>30 个新 unit tests
```

必须停下来检查是否又在工程膨胀。

---

# 36. 开源代码接受规则

不能因为开源就直接信。

任何外部模型必须通过 4 个 smoke tests：

```text
1. shape
2. causal input
3. deterministic eval
4. no future normalization
```

再训练。

不需要给每个 upstream 写几十项测试。

---

# 37. 预期最大的效率提升

旧方法：

```text
自己写 architecture
-> 调 shape
-> 写 test
-> 修 trainer
-> 跑模型
```

新方法：

```text
安装 / vendor mature implementation
-> adapter
-> smoke test
-> experiment
```

目标：

```text
把 60–80% Agent 时间从工程移到实验。
```

---

# 38. 本阶段真正的新研究价值

我们不需要宣称：

```text
发明 Transformer
发明 TCN
发明 contrastive learning
```

项目真正可能有价值的点是：

```text
1. Spot / perp / cross-asset order-flow joint representation
2. participant-flow prediction
3. flow -> price impact state dependence
4. representation transfer across BTC/ETH
5. adaptive vs static model comparison
6. cost-aware selection
```

这是应该投入思考的地方。

---

# 39. 最终执行顺序

固定：

```text
Official Binance data
    ↓
5s Spot/Perp synchronized dataset
    ↓
Ridge/XGB
    ↓
pytorch-tcn
    ↓
MLPLOB/TLOB
    ↓
TS2Vec
    ↓
River online replay
    ↓
unified leaderboard
    ↓
select top 3
    ↓
3-seed + ablation
    ↓
research conclusion
```

禁止中途再次开：

```text
mainnet
RL
world model
new dashboard
new audit framework
```

---

# 40. 参考开源项目

## Binance public data
https://github.com/binance/binance-public-data

## pytorch-tcn
https://github.com/paul-krug/pytorch-tcn

## TLOB
https://github.com/LeonardoBerti00/TLOB

## TS2Vec
https://github.com/zhihanyue/ts2vec

## River
https://github.com/online-ml/river

## tsai
https://github.com/timeseriesAI/tsai

## LOBFrame
https://github.com/FinancialComputingUCL/LOBFrame

## LOBench
https://github.com/Financial-Simulation-Lab/LOBench

---

# 41. Codex 最终指令

不要重新规划整个系统。

直接：

```text
1. 登记本文件为 OPEN_SOURCE_REUSE_OVERRIDE_v6
2. 保留现有 STOP_v2 和所有冻结证据
3. 冻结 execution 工程
4. 建 OPEN_SOURCE_REGISTRY
5. 用 Binance 官方 historical pipeline 开始 180d+ HF dataset
6. 依次接 Ridge/XGB/pytorch-tcn/MLPLOB/TLOB/TS2Vec/River
7. 所有模型共用同一 dataset/splits/labels/evaluator
8. 第一轮最多 10 configs
9. 先出结果，不做大搜索
10. 最终输出统一 leaderboard 和研究结论
```

如果成熟开源库已有功能：

```text
优先使用它
```

除非有明确的：

```text
兼容性
正确性
资源
许可
```

理由，否则禁止重复实现。

---

# 42. 一句话原则

```text
不要证明 Codex 会写神经网络。
要尽快证明市场里有没有可预测结构。
```
