# FR62：官方历史高频数据薄接线

依据根目录 `OPEN_SOURCE_REUSE_OVERRIDE_v6_2026-10-01.md`（SHA256
`bc650cda80b6f6478a3bd81f28d0971dfe8183a72e330a443e8b1c741290b86a`）。

## 来源与复用决策

上游：[binance/binance-public-data](https://github.com/binance/binance-public-data)。
仅复用官方 URL、CSV 列、时间单位和 SHA256 CHECKSUM 合同，下载使用已有 httpx，
解压/CSV 使用标准库 ZipFile/csv，持久格式使用已有 PyArrow Parquet；不复制下载框架、
不新增安装包、不修改旧环境、冻结采集器或交易执行系统。

官方软件仓库的 MIT 与数据许可分开。数据条款为官方
[TERMS_AND_CONDITIONS.md](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)，
根侧 FR61 保存的版本 SHA256 为
`dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1`。
manifest 固定声明 `personal_nonproduction_research` 并记录条款 URL/hash。
当前工程验收用于个人非生产历史研究，不授予生产使用资格。

## 最小 API

- `official_url(market, symbol, day)`：market 仅 spot/perp，symbol 仅 BTCUSDT/ETHUSDT。
- `fetch_day(..., previous_day_last_raw_id=None)`：官方 HEAD→CHECKSUM→限量流式 ZIP→
  转换→独占发布 Parquet 与 manifest→删除本次 owned ZIP/转换临时文件。
- `convert_zip(zip_path, output_path, market=..., symbol=..., day=...,
  previous_day_last_raw_id=None)`：单桶状态＋512 行 Arrow 批，逐 ZIP 行转换，不展开 CSV。
  这是内部转换合同；合成夹具直接调用不取得真实市场资格。
- CLI：`scripts/hf_fetch.py --market spot --symbol BTCUSDT --day 2025-07-01
  --output reports/<独立新验收报告>.json`，须经既有 bounded 入口在 hpc_linux 运行。

请求在文件/网络访问前硬拒绝 `day<2025-07-01` 或 `day>=2026-03-01`。
日文件独占发布，不覆盖、静默跳过或自动修复现有日文件。长批次由根侧串行驱动；
本模块不启动长期任务、不训练、不使用 GPU。

## 5 秒统一合同

版本 `trade_flow_5s_v1`，每 UTC 日 17,280 行；market、symbol、date、version 逐行绑定。
timestamp 为桶开 UTC 微秒；close_us=available_us=timestamp+5,000,000。
available_us 是成交桶的因果闭合约定，不代表原始数据当时的网络到达时间、买卖报价或可成交价格。
Spot 2025 起原始 timestamp 为微秒，USD-M Perp 为毫秒，统一转换为微秒。

| 字段 | 合同 |
| --- | --- |
| open/high/low/close/vwap | 原始聚合成交价构成的 Float64 OHLC/VWAP |
| first_trade_us/last_trade_us | 本桶真实首/尾聚合成交时点；空桶 null |
| trade_count/raw_trade_count | Σ(last_raw_id-first_raw_id+1)；两字段同值 |
| buy_count/sell_count | 按 maker=false/true 划分的上述原始成交笔数 |
| agg_count | 原始 CSV 聚合成交行数，不是原始笔数 |
| base_volume/quote_notional | Σquantity / Σprice×quantity |
| aggressive_buy_notional/aggressive_sell_notional | maker=false/true 的成交额 |
| flow_imbalance | (买主动成交额−卖主动成交额)/总成交额 |
| mean_trade_size/max_trade_size | 聚合成交 quote USD notional 均值/最大值 |
| large_trade_share | 单聚合成交额 >=10,000 USD 的成交额占比；固定先验阈值，无全期分位数 |
| mean_interarrival/std_interarrival/interarrival_count | 相邻聚合成交间隔秒/总体标准差/间隔数；跨桶保留前条，每日首条无跨日间隔 |
| return_5s | log(本桶 close/前桶 close)；本桶或紧邻前桶为空则 null |
| signed_price_impact | 平均 signed log(价格/前聚合成交价)；主动买+、主动卖−；每日首条无前价项 |
| empty_bin | 经日文件完整读取确认无成交；计数/量额为0，不伪造 OHLC/VWAP/return/impact |
| quality | 发布流程通过 CHECKSUM、日内原始 ID 连续与排序时为0；不授实时质量/alpha/报价执行资格 |

可接受聚合 a 跳号但要求 a 严格增加、timestamp 不回退。原始 f 必须等于上条 l+1；
真实缺口、重叠、重复、非排序均显式失败并保留证据，不对整条聚合成交任意拆分。
跨日只在显式提供前日 last_raw_id 时核对首 f；manifest 单列
`cross_day_raw_boundary_verified`。首日/独立日未知跨日边界不冒充健康连续窗口。
各日首条间隔/return/impact 未计算跨日贡献，后续建模必须遵守 null/mask。

## 资源与失败证据

共享 RAM 上限5,000,000,000字节、swap0，不使用 GPU。沿用原磁盘守卫检查完整项目＋
整个 D 盘 WSL VHD，36GB 停止新增/40GB 硬限；转换前预留 ZIP 大小＋25MB，发布前
预留转换结果＋1MB。每次全局磁盘扫描耗时单独记录，不以虚构投影保证吞吐。
HEAD ZIP 硬限512MB，缺 content-length 时按512MB预留，下载累计硬限512MB；
CHECKSUM 响应≤4096字节，单 CSV≤4GB、单行≤16KB，不展开落地 CSV。

本次原始 ZIP/转换 staging 仅位于 `/home/xflops/coin-state/hf-official-*`（D VHD）。
仅在完整转换、Parquet SHA核对、独占且 fsync 的 manifest 成功后删除字面 owned 文件。
manifest 的 `raw_deleted=false` 是删除前的耐久授权状态；CLI 的独立终报记录删除后
`raw_deleted=true`、raw 文件不存在和 manifest SHA。失败保留 owned raw/staging 与
独立 `FAILURE.json`；已发布但未完成 manifest 的 Parquet 不接受，不自动覆盖重试。
脚本 CLI 在执行前独占预留输出报告，失败也保存独立终报；失败版本不覆盖旧证据。

## 工程验收与限制

首轮隔离测试 V1：12 PASS，9.38s，`reports/FR62_FOCUSED_20261001_V1.xml`。
Ruff 首轮发现1处合同字符串超长，修缮后独立 V2：12 PASS，8.75s，
`reports/FR62_FOCUSED_20261001_V2.xml`（SHA256
`167ac36b54429477b8809a43b21a24cce89faca0cac61523a6984dd9187b8943`）；
聚焦 Ruff 检查通过。
所有测试夹具、pytest basetemp 和假下载均在 STATE，不修改真实 ROOT 或冻结守卫。
工程夹具不提供真实行情资格；一日真实验收仅证明该日链条，不证明四路180日完成、
未来预测收益、成本后 alpha 或真实交易可用。

## 真实一日验收（V1，已闭合）

`reports/FR62_REAL_SPOT_BTC_20250701_20261001_V1.json`，exit0，
SHA256 `2054ef61e37645755a080c9f0f459e69fab619746afbc7dfb3307f1d0464462f`。
实际请求仅 BTCUSDT Spot 2025-07-01；`engineering_fixture_hook=false`。
官方 ZIP SHA256 `69308ceec2c05dd17739f378327dfe13bd536546e5772d10e1b283b060766501`，
与官方 CHECKSUM 相等；下载11,611,012字节，接受转换后本次 owned raw/staging/temp 均删除。

产物为 `data/research_fast/trade_flow_5s_v1/spot/BTCUSDT/2025-07-01.parquet`：
17,280行，802,159聚合成交行、2,013,289原始成交，2个已知空桶，大小2,720,619字节。
Parquet SHA256 `038729f900c1923917977dbef41315f2a8196083130a726fe2ad5d80fbd2a795`；
对应 manifest SHA256 `6c1614222b6a1c5c74474b0b871d869b51dfee87a3f0da2c3b00bbcf62e5ada3`。
首次独立日跨日原始 ID 边界为 unknown，不冒充跨日连续。
独立只读回算确认 raw/aggregate总数、buy+sell=count、raw alias同值、5s整日cadence、
available_us=close_us、quality全0，以及 owned temp不存在。

总耗时377.298秒，转换6.318秒；两次完整磁盘扫描137.300秒、226.407秒，
占总耗时约96%。扫描成本是长批次实际性能限制，未新增或绕过磁盘守卫。
发布前项目＋整个WSL VHD实测10,702,326,668字节（磁盘守卫OK）。
共享RAM初始270,721,024字节、终点370,429,952字节；共享历史peak为2,083,442,688字节，
该peak不等于本次独立实测峰值。内核5GB上限有效、swap0、OOM/OOM-kill0、GPUfalse。
没有声称稀疏资源快照覆盖整个运行峰值。

本次终报实际绑定且闭合后重新核对两来源不变：

- `scripts/hf_fetch.py`：`b515610fefcbf8ad18209c12da27b8c98fb38162a95137bc816a7a2bd80d23c3`。
- `src/quant/research_fast/trade_flow.py`：`be07e53ad9c2f1590c1ca8e7c6332f3953d53a79cd869bdc36052c0a24003439`。
- 测试来源：`fbbff7b0bc834ba46ed0bdd1b52d1f02b4d38ae25f212e6b728285439265e83d`。

该日历史数据薄接线工程通过；四stream、跨日、>=180天、实际全部持久文件容量与后续
train/validation/test实验仍由各自真实清单验收。首日大小不保证其它日期/市场容量；
无锁定期读取、无GPU、无训练、无真实交易。
