# A07 — Microstructure Collector v1

依据根目录 `CODEX_AUDIT_AND_NEXT_PLAN_2026-09-30.md` v3。此模块独立于旧
collector/runtime、参考账户和执行模块；旧证据不改写，旧实时进程不停止。
功能是公开行情数据工程，不能据此宣布 alpha、真实 30 天建模资格或交易准入。

## 1. 数据合同

BTCUSDT / ETHUSDT，固定 `data-stream.binance.vision` 官方主网市场数据域名；
同一连接订阅 `bookTicker` 和 `aggTrade`。不读取凭证，不调用账户或下单接口。
官方将 `m` 定义为买方是否为 maker，所以 `m=true` 是主动卖出、`false` 是主动买入。
Spot bookTicker 只有 L1 价格/数量及更新 ID，不能伪造它的交易所事件时间。
[官方市场流文档](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)。

所有分桶按**实际接收 UTC 时间**，右开区间 `[open_us, close_us)`。同时保存
`received_first/last_us`、aggTrade 的 E/T 首末时间、`available_us`、版本、session、
live/engineering 来源。`available_us >= close_us`，计算延迟也如实保留；写盘延迟
不能被解释成当时文件已经可用。训练/在线消费不得早于真实特征可用时刻。
调试 raw 保留完整原始字段、接收时间和来源；live API 禁止外部提供接收时间。

bookTicker 的 u 只检查递增/重复，不假定相邻 u 连续。aggTrade 的 a 跳跃保守记为
`AGG_ID_GAP`，保存前后实际接收时间；不把 REST 或重新播放写成原始实时接收。
相同最近 ID/相同内容幂等；相同 ID 改内容立即停止；更旧 ID 不改写已封秒，记录
乱序质量。缺失/旧报文不能因当前连通就获得完整数据资格。

## 2. 1s 指标及 OFI

保存 v3 的全部 17 个指标：mid、spread_bps、bid_qty_mean、ask_qty_mean、
L1_imbalance_mean、L1_imbalance_last、microprice_offset_bps_mean、quote_update_count、
bid_price_change_count、ask_price_change_count、OFI_L1、agg_trade_count、
aggressive_buy_notional、aggressive_sell_notional、trade_flow_imbalance、trade_vwap、
realized_return_1s。

数量、点差、盘口不平衡和 microprice 均按**已接收 quote 事件**等权平均，非时间加权。
mid 是秒末最新且不超过 2s 的实际 L1 mid；短暂 carry 明示 CARRIED，不能补造
quote 数量均值。超过 2s 无报价，相关状态为 null 并标 STALE_QUOTE。
无事件秒有计数 0 / 无成交 VWAP null；断线零值必须结合质量标志，不能当完整流。
realized_return_1s 是相邻有效秒末 mid 的 log return；缺口/未知基准时 null。

OFI 按逐个已接收 L1 状态变化计算，单位为 base quantity：

```text
e = 1[b >= b_prev]*bid_qty - 1[b <= b_prev]*bid_qty_prev
  - 1[a <= a_prev]*ask_qty + 1[a >= a_prev]*ask_qty_prev
OFI_L1 = sum(e)
```

相同价格正确保留数量增减；更好 bid 为正、更好 ask 为负。跨秒维持基准，
重连/拒绝/重启清空基准，首 quote 不跨缺口差分。
这是观测到的 top-of-book OFI，不是全 L2 或逐委托事件重建。
[Cont/Kukanov/Stoikov 原论文，式 2](https://arxiv.org/pdf/1011.6402)。

## 3. 5s / 30s / 1m 语义聚合

| 指标类型 | 聚合规则 |
|---|---|
| mid、spread、数量均值、不平衡均值、microprice offset | 对非 null 的 1s 状态 mean/std/min/max；last 为实际最后一秒，不能跳过尾秒 null |
| quote/trade/价格变化次数、OFI、买卖 notional | sum 已接收值 |
| L1_imbalance_last | last |
| trade_flow_imbalance | 用合计买卖 notional 重新计算 |
| trade_vwap | 合计 notional / 合计 base quantity，不能平均秒 VWAP |
| return | 仅全部已知秒 return 有值才 sum；否则 null |

std 为已知秒状态的总体标准差（ddof=0）。每窗有 known_seconds、valid_seconds、
质量 OR；少秒为 MISSING，多 session 为 RESTART。前缀/尾部不完整窗口不伪装成
完整窗口；STOP 审计记录未封秒事件和未闭合聚合窗。重启后这些边界保持缺口，
已提交的 1s 基础记录仍可单独核验/重新研究聚合。

## 4. 质量及真实时间边界

| 位 | 含义 |
|---:|---|
| 1 / 2 | PARTIAL / DISCONNECTED |
| 4 / 8 | NO_QUOTE / STALE_QUOTE |
| 16 / 32 | AGG_GAP / LATE 或乱序 |
| 64 / 128 / 256 | CLOCK / RESTART / MISSING |
| 512 / 1024 | BASELINE_RESET / CARRIED |

valid_seconds 排除 PARTIAL、DISCONNECTED、STALE_QUOTE、AGG_GAP、LATE、CLOCK、
RESTART、MISSING。NO_QUOTE 或 carry 仍须由具体研究协议约束，不能自动当 fresh quote。
断线审计从最后收到数据至检测时刻保留不确定范围；训练前须同时处理该范围和
随后检测到的 aggTrade 缺口，不能只过滤当前秒的 bit。
>120s 的跳跃写 OBSERVATION_GAP 范围，不生成数千秒假数据。wall/monotonic
偏离 >1s 停止；会话真实 monotonic 观察值保留，但不补健康、不替代数据完整性。

现阶段所有 status 固定 alpha_eligible=false、real_time_days_certified=0。
<14 天仅质量/稳定性研究；14–30 天仅预测诊断；>=30 天才可另行预登记 M1。
mode=live 也不等于 TRUE_FORWARD_V2；候选冻结及 2026-10-01 之后的真正未来资格
须由独立研究协议验证，不拼接模型版本或 synthetic 数据。

## 5. 持久化和硬上限

- SQLite 位于 `/home/xflops/coin-state`（D 盘 WSL ext4），WAL + synchronous FULL；
  默认 `microstructure.sqlite3`。数据库和 store 各有 native 单写者锁。
- D 盘默认 store `/mnt/d/codex/coin/data/microstructure_v1`。ownership marker 绑定
  唯一数据库/来源；native binding 绑定实现 SHA、Polars 版本及压缩合同。
- 每秒封桶和 checkpoint/outbox 同一事务提交；每 600s 批量导出。Parquet 先在
  有界内存编码，**按准确分片大小预检 8,000,000,000 字节上限后**才落临时文件。
  fsync 后原子更名；manifest + 删除 outbox 同事务。崩溃 orphan 的原内容 SHA
  必须完全相符，不能覆盖不同内容或重复记录。
- 达上限立即 FEATURE_CAP_STOP、停止接收并保留 pending rows；不删已存 features、
  不静默改 5s。不完整尾段明确记未知，不能宣称无损恢复未提交事件。
- long Parquet 为 Zstd level=3；研究字段 mean/std/min/max 保留，重复 Parquet
  列统计元数据关闭。按 native manifest 的时段筛文件。
  mid/VWAP/OFI/notional 使用 Float64，其余研究浮点用 Float32，时间 Int64；
  counts UInt32、质量 UInt16。精度合同只供研究，不替代执行模块的 Decimal。
- raw 是 gzip level=1 的 <=60s / <=4MB 未压缩分片。仅本模块 raw 队列自动清最旧；
  **<=24h 且实际字节 <=4,000,000,000**。当前 gzip 缓冲按未压缩上界预留，
  删除汇总写 RAW_PRUNED 审计；不删 feature/审计。raw 不是永久灾备。
- 全项目硬限仍 40GB、32GB预警、36GB停止新增、保留4GB缓冲；共享 RAM<=5GB、
  swap=0、不用GPU。不能把 v3 文档中的更大 RAM/VRAM 当本次新授权。
  startup/full disk 检查后台线程执行；运行中 ledger 刷新不停止接收。
  hot path 不递归扫描全部文件，内存只留当前秒和最多 60 秒聚合数据。

长期目标是 180d Parquet<=8GB。高熵工程投影及短段实收见独立 acceptance receipt；
**投影不是 24h 真实容量认证**。必须继续实测 24h 的字节增量、质量、CPU/RSS。
若真实投影超过目标，应暂停并另立 5s schema；旧文件不删不改。

## 6. API 与启动

```python
config = MicrostructureConfig()  # live，native DB + D store
await collect_microstructure(config, run_seconds=None, stop_event=stop)
snapshot = read_microstructure_status(config.db_path)  # 同一只读 SQLite 快照
```

启动和状态均在 hpc_linux，并经过共享 cgroup 包装：

```bash
bash scripts/bounded.sh .venv/bin/python -m quant.microstructure --run
bash scripts/bounded.sh .venv/bin/python -m quant.microstructure
# 短段可加 --seconds 60；自定义 native DB/store 可用 --db / --store
```

默认 CLI 仅只读状态；`--run` 才启动公开行情。SIGINT/SIGTERM 设置 stop_event，
完成已提交 outbox 导出及 STOP 审计后退出。重启同 DB/store 需原来源/实现/压缩绑定
一致；变更实现用新版本/路径。状态读者无构造器、writer lock、guard 或网络动作。
状态只证明账本/heartbeat 快照；建模前还要逐 manifest 校验 Parquet SHA 和质量。

## 7. 验收

工程测试覆盖标准 OFI 六分支、m 买卖方向、跨秒/四频聚合、时间可用性、重复和
冲突、trade ID 跳跃、无事件与陈旧、断线基准重置、大间隔稀疏 gap、重启/压缩绑定、
orphan 原子恢复、raw TTL/硬cap、不删已有 feature、写前预算、磁盘拒绝、单写者、
只读状态无 writer/network，以及拒绝资源别名指向 C 盘。

首个 60s 原型实收 14,778 事件，遇一次 ConnectionClosedError 后重连；两币 ID
缺口和 >5s 迟到如实标记，0拒绝/0重复。旧短测证据保留，不能改写为连续健康。
冻结版的最终测试、短测、schema/trigger/compression/source SHA 见
`reports/A07_MICROSTRUCTURE_ACCEPTANCE.json`。实际 24h/14d/30d 与 alpha 尚未验收。

长期启动由 root 在冻结 receipt 确认后负责；该模块交付没有启动另一个长程进程，
也没有操作 legacy Live PID31240。
