# A10 因果微观结构特征视图

状态：`QA_ONLY / IMPLEMENTED_PENDING_ROOT_ACCEPTANCE`。依据根目录
`CODEX_AUDIT_AND_NEXT_PLAN_2026-10-01.md` 第 7 节实现独立数值视图。
不授予 24h/14d/30d/60d 数据资格、预测结论、alpha 或交易资格。
本模块无模型、拟合、标签、未来收益或采集器热路径变更。

## 固定输入与输出

实现：`src/quant/micro_features_v2.py`；版本
`microstructure_causal_features_v2.0`；输入版本只能为
`microstructure_l1_v2`。输入是 A09 `aggregate_seconds(rows, 5)` 的真实完整
5 秒行：UTC 对齐、`close_us=open_us+5_000_000`、`available_us>=close_us`、
`known_seconds=valid_seconds=5`。显式 `asof_us` 早于 `available_us` 被拒绝；省略时
使用该行的逻辑可用时点。输出记录原始可用时点与实际调用所给 `emitted_asof_us`。
读入器仍须先验证来源、1 秒完整性和排除未知/事故时间；行内元数据不是来源证明。

`INPUT_FIELDS` 冻结全部 27 个输入字段，包括 `mode/session/quality`、均值、5 秒
累计字段和 v2 尾部 `spread_bps_last/l1_total_depth_last`。拒绝 v1、字段缺失或
以 1 秒字段名称替代 5 秒均值名称；不得把 v1 重命名后混入 v2。允许 A09 聚合行中的
其他统计字段，但不消费它们。

| 派生字段 | 固定公式/来源 |
|---|---|
| `ofi_depth_norm` | `OFI_L1/(bid_qty_mean_mean+ask_qty_mean_mean+1e-12)` |
| `log_l1_depth` | `log1p(bid_qty_mean_mean+ask_qty_mean_mean)`；base quantity |
| `log_trade_notional` | `log1p(buy_notional+sell_notional)`；USDT |
| `trade_flow_imbalance` | `(buy_notional-sell_notional)/(buy_notional+sell_notional+1e-12)` |
| `vwap_offset_bps` | `(trade_vwap/mid_last-1)*10000`；无成交为空 |
| `log_quote_updates` | `log1p(quote_update_count)`；5 秒累计 count |
| `log_trade_count` | `log1p(agg_trade_count)`；5 秒累计 count |
| `quote_trade_ratio` | `log1p(quote_update_count)-log1p(agg_trade_count)` |

另外保留 `spread_bps`、`L1_imbalance_mean`、`L1_imbalance_last`、
`microprice_offset_bps_mean`、`realized_return_5s`。前三个 mean 字段分别来自
`spread_bps_mean`、`L1_imbalance_mean_mean`、`microprice_offset_bps_mean_mean`，
是等权 1 秒桶均值的均值；深度也是 1 秒均值的均值。OFI、成交量和 count 是
5 秒累计量，不再平均。`realized_return_5s` 仅保留 A09 的 `realized_return`，
即已发生的 1 秒 log return 之和，空值继续为空，不生成 horizon 标签。
尾部新列和 `mid_last/L1_imbalance_last` 必须来自真正末秒，不寻找更早的非空尾值。

`FEATURE_NAMES_V2` 枚举 20 个输出数值字段，仅表示输出视图。未来获准研究时的
默认 pooled 输入接口固定为 `MODEL_FEATURE_NAMES` 的 13 项：七个 `*_z1h`、
`trade_flow_imbalance` 和上述五项保留字段。七个未归一化派生量只用于 QA，
schema 标记 `QA_RAW_ONLY`，不得自动把全部 `RAW_FEATURES` 当 pooled 模型输入。
固定接口不授权当前训练或模型选择。

## 因果 EWM 与空值

BTCUSDT、ETHUSDT 使用各自独立状态；七个 scale-heavy 字段是除 bounded
`trade_flow_imbalance` 外的全部派生字段。它们同时输出原值和 `*_z1h`。
固定 half-life 为 3600 秒、epsilon 为 `1e-12`、warmup 为每字段 720 个过去
非空完整 5 秒样本；当前第 721 个样本才可能可归一化。warmup 不属于数据资格门槛。

首次非空值初始化 `mean=x, variance=0, count=1`。之后以该字段上次非空样本的
`close_us` 到当前 `close_us` 的真实秒差 Δt，计算
`alpha=1-exp(-ln(2)*Δt/3600)`，采用 `adjust=False` population variance：

```text
z_current = (x_current - mean_past) / sqrt(variance_past)
mean_new = mean_past + alpha * (x_current - mean_past)
variance_new = (1-alpha) * (variance_past + alpha * (x_current-mean_past)^2)
```

先计算所有当前 z，再更新全部当前非空值。过去样本不足返回 `WARMUP/null`。
过去 variance≤epsilon² 时，当前值严格等于过去 mean 则返回
`ZERO_VARIANCE_CONSTANT/0`；变化则返回 `ZERO_VARIANCE_CHANGE/null`，随后仍更新。
不裁剪异常值，不通过当前值减小当前 z，不做全局 fitted scaler。

零成交时，notional/log-notional/trade-count/flow-imbalance 的零有经济定义；
VWAP/offset 无定义，保留 `NULL_CURRENT/null` 且不更新该字段。下次非空样本的
alpha 使用完整流逝时间。Backward return 空值也保留；两者不重置其他 scaler。
`feature_ready` 只在 13 项固定接口字段全非空时为 true；它不表示 alpha 合格。

## 质量、连续性、重启

`INVALID=507` 和 known quality mask `2047` 与 A09 合同固定一致。INVALID、
非完整计数或必需 quote/深度/累计数值为空时，输出全部数值 null，并清空该 symbol
scaler；仍记下该行时间，重复桶不能重入。已知 informational flags
`NO_QUOTE/BASELINE_RESET/CARRIED` 本身不 invalidate，仍须满足完整/非空要求。
缺失 5 秒桶或 session 变化会在当前桶前重置该 symbol，当前有效桶重新作为首样本。
另一 symbol 不受影响。非有限数、未知质量位、不合法量纲/count、成交数量与
notional/VWAP 不一致、溢出、重复/倒序 close 或倒退 availability 原子拒绝，状态不变。

每 symbol 首次绑定 `live` 或 `engineering` mode，随后即使换 session 也不能
换 mode；拒绝把工程 warmup 借给 live。状态版本为
`microstructure_causal_ewm_state_v2.0`。`export_state/from_snapshot` 包含两 symbol
独立 timing/session/mode、每字段 count/last_us/mean/variance、schema/definition/
implementation SHA 与 canonical SHA 校验；错版本、改源、错 symbol、坏 checksum
或不可能的 moments 被拒绝。JSON float64 round-trip 保持 transition 完全一致；
导出副本不能改内部状态。接口仅返回/恢复 dict，由调用方保存 native STATE 文件。

## 执行与证据

`MicroFeatureState.ingest` 为唯一 transition；流式
`iter_micro_features_v2` 与 batch `build_micro_features_v2` 直接复用它，严格保持
调用方顺序，不排序、不做跨币连接或补值。生产状态只保留两币七组 moments；
stream 输出无需保存完整历史。batch wrapper 仅在调用方明确需要时返回完整 list。

所有 Python/pytest/Ruff 在 D-hosted `hpc_linux`，经 `scripts/bounded.sh` 共用
5,000,000,000 bytes RAM、swap0，无 GPU。测试 fixture/state/basetemp 全部在
`/home/xflops/coin-state/` 独立目录。仅合成输入，不读真实市场库、锁定历史或采集热路径。

首次测试 `reports/A10_MICRO_FEATURES_V2_TESTS_V1.xml`：44 项通过，3.71 秒。
首次 Ruff `reports/A10_MICRO_FEATURES_V2_RUFF_V1.json` 保存 1 个 E501 失败；
初版 source/test SHA 与两份实际报告 SHA 在
`reports/A10_MICRO_FEATURES_V2_INITIAL_RECEIPT.json`，不覆盖。修复、mode 隔离、
model whitelist 与 A09 聚合接口合成测试后，V2 focused 测试 46 项通过，12.06 秒，
0 失败/错误/跳过；`A10_MICRO_FEATURES_V2_TESTS_V2.xml` 与
`A10_MICRO_FEATURES_V2_RUFF_V2.json`（空诊断数组、退出 0）独立保留。
最终实际测试、输出、输入 fixture SHA 和当前 source/test/doc SHA 由新收据绑定。
根侧独立实测验收与模块推送另行完成，本文件不代替该验收。
