# A09 微观结构正确性与末端 BBO v2

## 来源溯源（复制前保存）

本模块按用户已授权的新审计
`CODEX_AUDIT_AND_NEXT_PLAN_2026-10-01.md` 实施，该审计原始 SHA256 为
`6845cf09cd21c9258d7e446e42327adc3b3864d699935915fc936f06fb664b91`。

`src/quant/microstructure_v2.py` 从冻结 `src/quant/microstructure.py` 的完整字节复制后，
仅作本模块明确的正确性/schema 修缮。复制前核验 v1 源 SHA256 为
`649a69c924cdcfc4e85dca37a2a6c4958993f3f3365e04b3f10372f8875ddbb4`。
v1 源码、数据、数据库、marker、验收凭证和当前运行进程保持原字节；v1 资格时间不拼接 v2。

## 独立版本与资源

版本 `microstructure_l1_v2`，默认 native数据库为
`/home/xflops/coin-state/microstructure_v2.sqlite3`，行情目录为
`/mnt/d/codex/coin/data/microstructure_v2`。旧 v1 默认库和目录直接拒绝；任意已有库须在
只读 `mode=ro/query_only` preflight 中证明 version/mode/store/source/compression 完全一致，
然后才可开启写 journal/schema/marker。旧 marker 不改写、不迁移。只读 status 也要求 v2。

数据库单写锁、原始ring保留上限/淘汰、资源守卫、原本地快照/实际磁盘异步刷新、事件
封桶/导出及断线/重启边界保留 v1 实现。测试核对这些方法的完整 AST 相同，未放宽守卫。
所有 Python和测试在 D 盘 `hpc_linux` 的共享 `scripts/bounded.sh` RAM≤5GB、swap0 下
运行；不使用 GPU、锁定价格、训练、真钱或交易所发单。

## aggTrade 原始 ID 合同

`f/l/E/T` 必须为非 bool 的非负真实整数，且 f≤l、E≥T。价格、数量和 m 类型在 replay
处理前验证；坏值不能假扮可接受重复。流ID a/u 保留原整数/non-bool/nonnegative 检查。

| 已有上一条接受状态后的新事件 | 行为 |
|---|---|
| f=previous.l+1，a=previous.a+1 | 接受，不记 gap |
| f=previous.l+1，a跳号或下降 | 接受，只记 `AGG_ID_JUMP_UNCONFIRMED`，不单独 INVALID |
| f>previous.l+1（即使 a连续） | 接受已收到量，置原 `AGG_GAP`，审计 `RAW_TRADE_ID_GAP` |
| 同上一 a、同完整原内容 | `AGG_TRADE_DUPLICATE`，拒绝重复计算量 |
| 同上一 a、完整原内容冲突 | 保留 `IDENTITY_CONFLICT` 停止原则 |
| f/l 等于上一接受范围但 a不同 | `RAW_TRADE_DUPLICATE`，整条拒绝重复量 |
| f≤previous.l，范围与上一接受范围相交 | `RAW_TRADE_OVERLAP`，整条拒绝，置原 `LATE` |
| f≤previous.l，范围早于上一接受范围 | `RAW_TRADE_OUT_OF_ORDER`，整条拒绝，置原 `LATE` |

Overlap 的聚合 q 不能按 raw ID 数量任意分摊；拒绝量不进入flow/VWAP/trade count，未见
尾部量单列 unknown。拒绝事件不推进或倒退最后接受的 f/l/a 高水位；下一事件若越过
最后已接受 l+1，会如实发现仍未知的 raw缺口。`last_agg_id` 保留上条 a，而
`agg_id_high_water` 独立保存 max a，不因允许 a下降而回退；`last_raw_trade_id` 等于已接受 l。
当前 f/l、原内容 hash 与 receipt边界随原每秒 checkpoint 保存。恢复核对严格整数和
各别名一致，重连不清空交易ID状态，重启从 checkpoint 恢复。未封存秒尾仍保持原
unknown/RESTART_GAP 边界，不能声称每事件实时持久化或把重启间隔补成健康时间。

不新增 quality bits。已知 mask仍2047，INVALID仍507；a跳号只审计，不制造新 INVALID位。
RAW gap记录 missing raw ID 首末、上一接受receipt与检测receipt，后续独立v2质量审查
必须识别该事件并回溯未知范围；旧 v1 `AGG_ID_GAP` 审计与旧质量报告保持原语义。

## 末端 BBO 语义和精度

长期行只新增 `spread_bps_last`、`l1_total_depth_last`。1s封桶末若原 previous quote满足
原receipt年龄≤2s的fresh条件，mid、原 `L1_imbalance_last` 和新两列全部从同一 previous
BBO计算；包括无新报价、`CARRIED` 情况。此时原 mean数量/mean imbalance仍为None，
不伪造桶内报价事件；v2的 lastimbalance 特意修正了 v1 carried桶为None的旧行为。
Stale末秒的 mid/lastspread/lastdepth/lastimbalance 全部None，不能混搭不同报价。

5/30/60s聚合直接取末1s的三项last状态，mid_last也来自该秒。即使尾秒无效/空值也不
跳回更早的非空报价。新两列与 lastimbalance 用Float64；原mid/mid_last本来也是Float64。
因此从compact Parquet行可一致重构：

```text
bid = mid_last * (1 - spread_bps_last / 20000)
ask = mid_last * (1 + spread_bps_last / 20000)
bid_qty = l1_total_depth_last * (1 + L1_imbalance_last) / 2
ask_qty = l1_total_depth_last * (1 - L1_imbalance_last) / 2
```

这些是对应末秒BBO状态，仍须结合原 quality/可得时间/年龄，不是对未来成交或发单的
保证。1s用 mid，其余频率用 mid_last；均不使用假的bookTicker交易所时间。

## 聚焦工程测试与验收边界

测试独立加载此新模块，只将该实例 ROOT/_layout_guard 替换为 native STATE 工程夹具。
数据库、文件、负面工件、短寿命目录和 pytest --basetemp 全部位于
`/home/xflops/coin-state`；不放入运行中collector的真实ROOT、不改全局quant.paths。

首轮72项 PASS/24.64s 保留在 `reports/A09_MICROSTRUCTURE_V2_TESTS_20261001_V1.xml`；
第二轮新增恢复、旧版本拒绝和资源方法AST验据，79项 PASS/61.63s 保留在 V2 XML。
最终修正测试导入排序后，V3 XML实际79项 PASS/15.29s，Ruff PASS；没有失败或跳过用例。
三轮XML均保存，正式工程凭证以主代理独立实际短采/验收绑定的新报告为准。
源码微调与复测保存新编号，不覆盖旧XML。

测试包含新审计七场景、a下降/raw连续和a连续/raw缺口、24种f/l/E/T坏类型、时间/range
先后、原同a内容冲突、raw重复/contained overlap、重启高水位、防混v1库/marker/status，
同末态fresh/carried/stale和全部聚合层重构/Float64，以及原OFI、边界、持久化导出、容量
停止、锁、raw淘汰、只读status等回归。原 v1测试文件不改，旧实际凭证不覆盖。

这些全部是工程合成证据。实际新版本短采、来源冻结、启动/停机/事故凭证、24h资源与
质量验收由主代理另行完成；本实现代理未运行、停止或重启任何真实采集器。v2的真实
24h→14d→30d→60d资格从v2新来源独立重新累计；v1不拼接，工程测试不计市场时间。
没有 alpha候选、最终拟合、180d存储保障或利润保证；TRUE_FORWARD 仍须合格候选冻结后开始。
