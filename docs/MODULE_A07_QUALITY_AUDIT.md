# A07 真实微观结构数据质量与容量诊断

## 范围与入口

`scripts/audit_microstructure_quality.py` 只诊断 `microstructure_l1_v1` 的原 native SQLite 与 D 盘特征库，不构造采集器、不连网络、不训练、不下单、不改写数据库、原始数据或旧凭证。`collector_public_v3` 的分钟线采用另一合同，不能混用来源或累计健康天数。

运行必须使用 `hpc_linux` 的 `scripts/bounded.sh`，共享 RAM ≤5GB、swap0、总磁盘 ≤40GB、无 GPU。示例：

```sh
source scripts/env.sh
scripts/bounded.sh .venv/bin/python scripts/audit_microstructure_quality.py \
  --output reports/generated/A07_QUALITY_新的UTC时间.json
```

报告用独占创建，已有路径拒绝覆盖。公共只读 API 为 `audit_quality(db_path, store, limits=None)`；未验证的文件/版本/来源/链或资源超界返回 `FAIL_CLOSED`。预算不足另标`failure_class=DIAGNOSTIC_BUDGET_EXCEEDED`、质量未判定。真实数据不足返回 `INSUFFICIENT_EVIDENCE`，工程代码通过不等于 24 小时实测通过。来源或时钟测试hook均明确标工程来源，不授真实资格。

## 一致性与有界读取

SQLite 使用 `mode=ro`、`query_only`、`BEGIN`，在最长 5 秒的短快照内验证 append-only triggers、完整审计 SHA 链、SESSION 来源/模式/版本/schema，读取 state、manifest 和未导出 outbox 计数。快照随后关闭，再扫描不可变 Parquet，避免长读事务妨碍实时采集回收 WAL。

manifest 最多二十万份且规范序列化元数据 ≤32MB；每文件 ≤64MB/十万行，每 row group 解压元数据 ≤64MB；Arrow 单线程、每批 ≤2048 行，全局 ≤一亿行、每流最多 4096 UTC 日。不拼接所有文件，不保存全部秒级键；按 interval/manifest 时间排序，八个流各保留最后时间及日计数，时间重复/回退拒绝。默认 600 秒 ×四频率的 180d 产生约 103,680 分片，文件计数上限包含重启余量；若未来 5 秒/32MB 等诊断预算不足，返回 `DIAGNOSTIC_BUDGET_EXCEEDED`，质量未判定，不能误称数据损坏或 180d 已全量审查。

逐 manifest 核对 FEATURE_EXPORT 审计、文件 SHA、字节/行数/起止与字段集合，核对版本、会话、模式、时间对齐和可得时刻。解码前还须核验列名唯一及固定Arrow字段类型，防止数值列被字符串等替换后才大量解码。SQL 快照后新 rename/未 commit 文件只记为 `concurrent or uncommitted`，不计数据时长；已提交特征文件缺失属于完整性失败。快照 head、manifest ledger SHA、asof 和 outbox 数量固定了本报告边界。后续文件清单仅为另一时点的库存观察。

## 覆盖和质量资格

按 BTC/ETH × 1s/5s/30s/60s 分别报告真实 UTC 首尾、已知/有效秒、缺桶、最大间隔、quality bits、合法空值、意外缺失、非有限值和完整特征行。时间不跨币或频率相加。

没有成交时 VWAP/成交方向指标为空、无新报价的 fresh carry 时报价均值为空、bookTicker 无交易所 event time、缺少前一有效 mid 时收益为空均属合法不可得统计。`valid_seconds=1` 不能代表 17 个值全部可用；报告单列完整 feature rows，合法空值不算损坏也不成为 feature-ready。非有限或意外缺失拒绝资格。

真实 24h 容量采用保守完整 UTC 日判据：同一日的八个流全部有唯一、对齐、完整已导出桶和 86400 已知秒；质量通过还要求全部桶有效。审计 `RESTART_GAP`、`OBSERVATION_GAP` 与断线 uncertain range 涉及的 UTC 日从严格 clean-day 诊断整体排除，不能靠旧行未及时写入的 quality=0 掩盖后发现的未知区间。完整已导出日计数不是健康行情时长。未导出 outbox、正在形成的窗口、进程墙钟及 first→last 日历跨度无时间 credit。部分 rolling 24h 暂不认证。

`AGG_ID_GAP`还须按上一已收到成交至检测出跳号的精确区间回溯隔离，包括已封存且原quality=0的秒。只读报告不修改旧特征；缺少此前收到时间边界时不能建立质量结论。

阶段门槛使用连续、八流共同完整已导出 UTC 日段，并要求该段内实际共同可用1秒行情达到14/30×86400秒，不能累加两个相隔数月的片段。只保留两个待配对行，按相同open_us严格匹配BTC/ETH；两边mid有限正值、无INVALID、且不与审计精确uncertain区间重叠才计1秒。分列配对、不可用、未配对及不确定秒，不能用两币各自有效秒的最小值代替交集，更不能靠全INVALID空壳桶累计年资。少量坏秒只扣对应秒，不清零整个UTC日，也不另设未经登记的质量百分比。这只授予数据审查阶段，质量标记/不确定区间必须在后续诊断隔离窗口。严格最长连续 fully-valid 日段另列：

| 连续完整导出日段内的共同可用行情量 | 可用范围 |
|---|---|
| <14d | QA_ONLY，只有工程诊断 |
| 14–29d | PREDICTIVE_DIAGNOSTICS_ONLY，预测诊断数据门槛 |
| ≥30d | PREREGISTRATION_REVIEW_ONLY，允许进入预登记数据审查 |

这些标签均不授权拟合、alpha、部署或真钱，具体研究质量门槛必须在后续独立预登记审查中确定。自 `2026-10-01T00:00:00Z` 起的 future 数据单列并决定报告顶部阶段，之前数据不充当前向证据。工程模式、测试来源 hook 或审计时钟回退不授真实时长资格。

## 容量与原始 ring

四频率 feature 字节合计；混币文件按行数分摊只是估计。报告分列编码列/page headers、Parquet container/footer、实际压缩合同、当前 native DB/WAL/SHM 开销。共同完整 UTC 日的字节分摊及峰值明确命名attributed estimate；另把每个含该日行的整个文件计一次，给出包含跨日行、页头与footer的保守上界，均不冒称精确按日压缩峰值。不足24h时的日均/180d 加30%余量投影仅供诊断，分母为八流最小已知时长，不重复加币或频率。原始ring和native未来增长未认证，投影不保证40GB或180d可存，更不能替代完整系统验收。

raw 是最多 4GB/24h 的可删除 debug ring，未保留逐文件预期 SHA/淘汰文件名。报告列审计 RAW_PRUNED 的计数、字节和范围及当前库存；淘汰不能误报成特征文件损坏。raw 未封口尾和已淘汰事件完整性均未知，不以 raw 库存认证健康时长或精确事件数量。最新 checkpoint 的 accepted/duplicate/rejected counters 仅覆盖当前会话，旧会话未保存的重复总数明确未知。

## 验收边界

独立测试使用小型工程库和聚合日计数，验证只读、短快照释放后允许 WAL 回收、并发未 commit 文件不计时长、版本污染/重绑定 SHA 后的无效特征仍被拒绝、缺文件/损坏、资源界限、合法 NULL、完整共同 UTC 日和连续阶段门槛。不会生成整月秒数据或冒充真实 14/30 天。

实际首报保存新的独立 JSON；结果和覆盖数字以该报告为准。本模块不修改 A07 原工程验收、事故证据或任一冻结研究来源。
