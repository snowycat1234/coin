# 前30日历史来源与结构独立诊断（2026-10-02）

状态：`FR_HISTORY_FIRST_30D_INDEPENDENT_DIAGNOSTIC_QA_PASS`。
仅核对 `2025-07-01 <= t < 2025-07-31` 的 BTC/ETH × Spot/Perp 120档，
30个共同完整UTC日；不是180日正式验收、6完整OOS验收、候选或生产准入。

新独立凭证：`reports/fast_research/FR_HISTORY_FIRST_30D_QA_20261002_V1.json`，
SHA256 `b922ea4f7412e06a3cdf9fecd7941da4b827a99ed61ff3d0d098d0b5702f33b0`。
本次不修改来源代码、manifest、已有报告或主进度文档，不启动/重启下载器。

## 来源与实际文件

直接复用 `scripts/hf_fetch_history.py:resume_day` 和 `scripts/hf_fetch.py:official_url`，
按明确日期逐档读取，不扫描locked。冻结V1核心、V2适配器和历史循环来源SHA
与两日既有验收、当前V3批次及120档manifest精确一致；开始/结束核对源码未变化，
逐档及结束核对manifest SHA未变化。每档Parquet SHA、字节数、schema和17,280行
均与清单相符，current batch快照中已登记的120个manifest SHA全部相符。

重新只读请求120个官方 `.CHECKSUM` 小文件，HTTP全部200，格式、ZIP文件名及SHA
全部与冻结下载清单的source_checksum一致；响应本身的SHA保存在逐档凭证。
本次未重新下载ZIP，成功日的原始ZIP已按既有流程清理，不能声称重新逐个计算其原始ZIP字节SHA。
官方repo、数据条款URL/哈希、研究用途及官方URL构造均核对通过。

实际文件合计334,449,702字节，manifest合计821,563字节；实际共2,073,600行。
逐批检查5秒cadence、当天完整范围、close/available时刻、market/symbol/version/date、
quality=0、trade_count=agg_count、buy/sell分区、成交量/名义金额分区、OHLC/VWAP、
流不平衡/大成交份额/到达间隔的边界与空值语义，并独立重算每个桶的日内return_5s。

| 路 | 文件数 | 实际行数 | Parquet字节 | 已知空桶 | 观察聚合数 |
|---|---:|---:|---:|---:|---:|
| Spot BTCUSDT | 30 | 518,400 | 80,816,905 | 32 | 24,533,507 |
| Spot ETHUSDT | 30 | 518,400 | 84,590,920 | 834 | 38,414,601 |
| Perp BTCUSDT | 30 | 518,400 | 81,999,632 | 20 | 30,293,252 |
| Perp ETHUSDT | 30 | 518,400 | 87,042,245 | 3 | 60,537,656 |

预期日期文件缺失0。889个已知空桶是档案内已核对的空观察桶，保留零计数/零量及
相应价格/统计空值；没有把它们填成成交或一般未知缺失。
120个成功来源的owned temporary directory实测均不存在。
旧manifest中的`raw_deleted=false`是发布耐久清单时的删除前状态，保持原字节；
本次以实际目录不存在和既有删除授权字段证明成功来源暂存已清理。
旧V1失败来源的raw仍保留，不属于这120个成功来源暂存。

## 原始编号范围与缺口分类

下面均为真实原始编号范围，不是适配器内部聚合计数序号。

| 路 | 首a → 末a | 首f → 末l | 内日raw范围跳号处数 | 未覆盖raw编号 |
|---|---|---|---:|---:|
| Spot BTCUSDT | 3,615,218,818 → 3,639,752,324 | 5,055,476,813 → 5,121,118,021 | 0 | 0 |
| Spot ETHUSDT | 1,602,078,552 → 1,640,493,152 | 2,578,526,055 → 2,671,667,824 | 0 | 0 |
| Perp BTCUSDT | 2,774,578,371 → 2,804,871,622 | 6,440,230,568 → 6,514,979,177 | 11,830 | 14,698 |
| Perp ETHUSDT | 2,280,663,413 → 2,341,201,068 | 5,898,989,748 → 6,080,638,587 | 14,105 | 15,046 |

29个跨日边界×4路，116个边界由前日last_l/last_a与后日first_f/first_a
独立重算；raw和agg跨日差额全部0，原边界验证字段与重算一致。
120档各自的`last_a-first_a+1-observed_aggregate_count`均为0；真实编号跨度、
观察计数及冻结有序验证相符。Spot原始raw范围相邻；Perp原始raw范围不重叠，
聚合编号连续，raw范围跳号单独保留。

25,935处、29,744个未覆盖raw编号是**原始编号范围跳号**，不是普通5秒桶缺失，
也不是已证明漏掉了相同数量的市场聚合记录或原始执行。
官方永续观察范围排除保险基金/ADL，但这不能证明每个跳号的具体成因。
全部保持`UNCONFIRMED`，不声称已全部归因。
内日a/f/l及gap计数由冻结转换器、manifest哈希和保存样例的算术绑定核对；
成功raw清理后，Parquet不保存这些逐条原始编号，本次不能独立重建每处内日gap。

## 失败证据与资格限制

原V1 BTC Perp 2025-07-01的官方CHECKSUM通过后触发
`RAW_TRADE_ID_GAP_OR_OVERLAP`，失败报告、原生FAILURE.json和对应profile仍保留；
两份失败报告SHA均为`4cc3bf3f8d68a2eff275cace4ed168a3521ac1c1ff76c4f6ec8589dea54695bf`，
与profile绑定相符，原生raw ZIP仍存在。原V1批次失败状态未改写为通过。
V2在22共同日/88档保留最后RUNNING检查点，WSL中断/恢复另有既存独立凭证；
当前V3仍运行，本次仅绑定其快照，不把运行计数当完整批次或正式验收。
本次120档诊断失败0，未发现新的correctness blocker。

执行位于`hpc_linux`，通过`scripts/bounded.sh`进入共享5GB、swap0预算；
使用既有research-env-v6 Python，禁止pyc写入、CPU单线程、未用GPU。
每批512行，最大Arrow批140,032字节，审计进程RSS峰值104,644,608字节
（低于256,000,000字节），实测131.49秒；没有全数据materialize或模型训练。
共享资源前后swap0、oom/oom_kill0；共享峰值包含并行工作，不归因于本审计。
审计临时代码留在独立STATE目录，只有本小报告和模块文档作为新增入库工件。

quality=0与官方CHECKSUM只证明已登记的官方聚合观察范围，不能证明所有原始执行、
历史bid/ask、成本后盈利或真正未来记录。无locked消费、真钱、候选资格或新执行工程。
