# 官方输入来源 QA 模块交付（2026-10-02，V1）

## 交付结论与边界

本模块仅接受**数据格式与来源完整性**。新增 BTCUSDT / ETHUSDT、2025-08-01 至 2025-12-01（右端不含）的资金费、1m mark/index 共 24 月档，独立 QA 核对 703,452 行（732 资金费事件、702,720 价格代理分钟）。官方 CHECKSUM、实际 ZIP SHA/CRC、原 CSV 与 Parquet 逐值一致、时间单位和完整月日历通过。未拟合、未回放 carry、未读取 locked、未产生 APR 或候选结论；P1 / 经济资格不变。

现有冻结 Spot 1m 数据可供主研究直接复用：BTC/ETH 2025-07-01 至 2025-12-01（右端不含），10 月文件、153 天/币种、440,640 分钟记录；7 月包含 31 天预热期。只核对选定文件的旧验收链、实际 SHA、schema/行数与保存的质量日历，不重新下载或重建来源。主 runner 应使用复用报告列出的 **10 个明确月 Parquet 路径**；现有无界 `load_minutes()` / `load_bars()` 会读取更广封存历史，不能直接调用。

mark/index OHLC 不是 BBO、真实 L5、可执行成交价或资金费扣款关联价格。carry 仍为 **NOT_EVALUABLE**：缺少两腿历史成交条件、费用/账户政策、资金费发布与扣款事件映射、保证金/清算/资本分母、借贷和转移摩擦等经济输入。当前停止来源扩张，资源让给简单策略公平收益比较。

## 精确证据（SHA-256）

| 工件 | SHA-256 |
| --- | --- |
| [固定协议](D:/codex/coin/protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json) | `2b3ef722ba3276c95d4a658d63ecdae12d92ae7a4f95a88de2918a4fd775d38a` |
| [producer](D:/codex/coin/scripts/research_v8/funding_price_source_v2.py) | `2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb` |
| [独立 auditor](D:/codex/coin/scripts/research_v8/audit_funding_price_source.py) | `edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c` |
| [producer 完成凭证](D:/codex/coin/reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_20261002_V1.json) | `f4970c14797dfeed367d8ba0d0a08c4649bc89e3adfa2d73ebd0ab76c5ff758a` |
| [独立逐行 QA](D:/codex/coin/reports/fast_research/V8_FUNDING_MARK_INDEX_INDEPENDENT_QA_20261002_V1.json) | `2f2b13b6be120a2db7e09abc24943f33b0892e53bfcc6b474f1bf3a53055ac74` |
| [格式 acceptance](D:/codex/coin/reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json) | `318622721ed9733d84ae66082f750e8b7d4ed960d7812c9e899c94b3cb5188aa` |
| [header 摘要追加更正](D:/codex/coin/reports/fast_research/V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_20261002_V1.json) | `9d529a13208b7bdd0fa31c9386dfe19d62d3947e9fd7789ca0281cff060726d9` |
| [source helpers 精确归档凭证](D:/codex/coin/reports/fast_research/V8_FUNDING_SOURCE_HELPER_ARCHIVE_20261002_V1.json) | `169e6ade2ede47953d982d0dcd7252b830f099e107c16fa0e91d82a8be79929b` |
| [已有 Aug–Nov 8 Spot ZIP 实际校验](D:/codex/coin/reports/fast_research/V8_EXISTING_SPOT_MINUTE_SOURCE_METADATA_20261002_V1.json) | `bbe5725e1355a94a8c19b1a199f703dd96e60c6d7fc19c6b5f6e9e4e16fdb1e5` |
| [Jul–Nov 冻结 Spot 来源复用](D:/codex/coin/reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json) | `a8b5389eced2ae4d9742d3e212e88562ca7bcc879990f3fa2b9632ebfdf1552e` |
| [Spot 来源复用精确源码归档凭证](D:/codex/coin/reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_REUSE_ARCHIVE_20261002_V1.json) | `aadf310322d510ad369bec77c10423426536afceb539ada8a5efaa28e8ff2792` |

原 acceptance 的 `accepted_format.price_proxy_headers` 摘要误写为 “Absent”。**实际 16/16 价格代理 CSV 均有精确 12 列 header**，原逐档 `observed_header` 和独立 QA 的 `header` 从一开始正确；producer/auditor 已校验并排除 header 后再核对数值。上述独立 correction 只追加纠正摘要，原文件与验收代码保留；源格式 PASS 和经济 NOT_EVALUATED 不变。更正源码为 [独立归档 helper](D:/codex/coin/docs/archive/V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_SOURCE_20261002_V1.py)，SHA `c89684124ad950ae0b3b6c553fa1a48c475c4e8db1d4415e2f6aced0a0446927`；追加 ledger record SHA `667dd3ad4588b3e046289b4665f36efa2fb804d0c5875c5603c8e10e2ad78dab`。

### 薄复用与前置证据

下载实际调用未修改的官方 `binance/binance-public-data/python/utility.py::download_file`，固定 upstream commit `f446ce3812bd4e5521f21faecd4ae3c6460e49fc`。软件复用按现有 registry 的 MIT 项目登记；数据条款与软件许可分别保留。原 aggTrades V1/V2 downloader/converter 未改动。

| 前置工件 | SHA-256 |
| --- | --- |
| [首次官方组件下载失败凭证](D:/codex/coin/reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_FAILED_20261002_V1.json) | `2ea6ffdd9486dbd05c9920c52645c312f21b5e4dc85068fb2ed075dbc916f13b` |
| [GitHub Contents API 原字节组件绑定 V2](D:/codex/coin/reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json) | `8a2ae22bd5bbf60763df352abb50d380763ba1fe19ac6545cc398f8d45d3ce96` |
| [资金费单档预检](D:/codex/coin/reports/fast_research/V8_FUNDING_PRICE_PREFLIGHT_20261002_V1.json) | `71effb598f32991408d0b8013d7e431acef4644c7ff90218ea1aa42410c449cf` |
| [预检协议](D:/codex/coin/protocols/FUNDING_PRICE_SOURCE_PREFLIGHT_V8_V1.json) | `36f2ab4bec81be8660f1574c7f15afeb171696890103acea4de3af31dd3e62a9` |
| [原 V1 预检源码](D:/codex/coin/scripts/research_v8/funding_price_source.py) | `4620631c3ce4e3eb529b7b468df522617a05728aadd6a0e9136d8184d7017a8f` |

单档实际 header 为 `calc_time,funding_interval_hours,last_funding_rate`，epoch milliseconds；实际 calc_time 存在毫秒抖动。独立 V2 协议在全批次开始前固定 nominal interval 1000ms QA 容差，原 timestamp/delta 不修改。实际 732 行报告 8 nominal hours；不推定所有历史事件恒为 8h，不将 calc_time 自动认证为精确扣款或发布时间。

Spot 复用核对旧 [dataset lock](D:/codex/coin/state/dataset_lock.json) SHA `29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d`、[质量报告](D:/codex/coin/reports/generated/DATA_QUALITY_REPORT.json) SHA `27aa56b33b12c1e6085230318bef6bd41cb3d95b23ca8714a35fc9a5b62125cf`、[数据政策](D:/codex/coin/configs/dataset_policy.json) SHA `3e1adcfbed86d0cc2414d37934126dcc2ddcdfcbe52b4e74ec58ff3447a7d880`。仅选定 10 月档的旧质量记录和实际文件 SHA/schema/行数；July 两 ZIP 完整 CRC，Aug–Nov 8 ZIP 复用已完成 CRC。时间为 microseconds，每完整 UTC 日 1440 分钟，选定档 missing/duplicate/quarantine 为 0。无需载入更广封存历史。

## 实际运行与资源

全部 Python 在 `hpc_linux`、clean env、原 bounded 共享 5GB cgroup 内运行；长任务经原进度 wrapper，无 GPU、swap 0。

| 操作 | 实际 session / exit | elapsed | peak RSS |
| --- | --- | --- | --- |
| 官方组件首次 raw host 获取 | 80155 / 1 | TLS ConnectTimeout，失败工件保留 | 未作成功资源声明 |
| 单资金费档预检 | 48974 / 0 | 67.793s | 74,473,472B |
| 24 档 producer | 68971 / 0 | 125.997s | 88,207,360B |
| 24 档独立逐行 QA | 98615 / 0 | 8.555s | 135,421,952B |
| 现有 8 Spot ZIP metadata 校验 | 实际工具 exit 0 | 约 4.36s（外层工具） | 未作独立 RSS 声明 |
| 10 Spot 月档旧封存 QA 复用 | 实际工具 exit 0 | 1.571s（验证）；8.96s（外层工具） | 未作独立 RSS 声明 |
| 摘要追加更正 | 实际工具 exit 0 | 2.18s（外层工具） | 未作独立 RSS 声明 |

24 档原 ZIP 总量 **16,260,808B**；声明解压 CSV **70,101,444B**（流式读 ZIP，未逐档落地解压 CSV）；来源独立 STATE 完成时 **42,121,633B**，低于新增 1GB 硬界限。启动前实际项目+WSL VHD **19,359,144,540B**，扫描时刻 **2026-10-02 11:00:12.070944 UTC**，预留 1GB；没有执行或宣称最终总盘扫描。producer 完成时共享 cgroup RAM current 665,235,456B、历史累计 peak 3,236,868,096B、limit 4,999,999,488B、OOM 0；该累计 peak 不是本任务独占 RAM。

资金费/价格代理原 ZIP、CHECKSUM、receipt、Parquet 留在 `/home/xflops/coin-state/v8-funding-mark-index-source-20261002-v1`；独立 QA STATE 为 `/home/xflops/coin-state/v8-funding-mark-index-independent-qa-20261002-v1`。原封存 Spot 行情留在既有 data / STATE。行情、数据库、日志、环境和缓存不进入 Git。

## 根代理可精确 stage 的新增文件

以下是本模块的明确小型源码/协议/报告清单；`reports/experiment_registry.jsonl` 的已有追加记录由根代理按统一 checkpoint 纳入，本次短文档任务不修改它。旧官方 metadata 可得性模块已先行验收，未混入本清单。

```text
docs/MODULE_OFFICIAL_INPUT_SOURCE_QA_20261002_V1.md
scripts/research_v8/funding_price_source.py
scripts/research_v8/funding_price_source_v2.py
scripts/research_v8/audit_funding_price_source.py
protocols/FUNDING_PRICE_SOURCE_PREFLIGHT_V8_V1.json
protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json
docs/archive/V8_OFFICIAL_DOWNLOAD_COMPONENT_STAGE_FAILED_SOURCE_20261002_V1.py
docs/archive/V8_OFFICIAL_DOWNLOAD_COMPONENT_STAGE_SOURCE_20261002_V2.py
docs/archive/V8_FUNDING_MARK_INDEX_ACCEPTANCE_SOURCE_20261002_V1.py
docs/archive/V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_SOURCE_20261002_V1.py
docs/archive/V8_EXISTING_SPOT_MINUTE_METADATA_SOURCE_20261002_V1.py
docs/archive/V8_EXISTING_FROZEN_SPOT_MINUTE_REUSE_SOURCE_20261002_V1.py
reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_FAILED_20261002_V1.json
reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json
reports/fast_research/V8_FUNDING_PRICE_PREFLIGHT_20261002_V1.json
reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_20261002_V1.json
reports/fast_research/V8_FUNDING_MARK_INDEX_INDEPENDENT_QA_20261002_V1.json
reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json
reports/fast_research/V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_20261002_V1.json
reports/fast_research/V8_FUNDING_SOURCE_HELPER_ARCHIVE_20261002_V1.json
reports/fast_research/V8_EXISTING_SPOT_MINUTE_SOURCE_METADATA_20261002_V1.json
reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json
reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_REUSE_ARCHIVE_20261002_V1.json
```

本交付未改 RESEARCH_STATUS、Decision、AGENTS、共享 registry 或旧来源工件，未自行提交或推送；根代理负责模块验收与 Git checkpoint。

根侧已只读核对上述producer／独立QA／摘要更正／分钟QA复用摘要及两个实际退出记录，
接受来源格式和既有QA复用范围，未重新跑来源QA。
凭证：[根侧验收](../reports/fast_research/OFFICIAL_INPUT_SOURCE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)
SHA `55e507e4408b54091887e9cfe5e80aa350c2c13f252874e1adad1c930b35e62b`。
