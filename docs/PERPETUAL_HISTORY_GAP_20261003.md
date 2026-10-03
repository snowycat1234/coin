# D042：官方完整历史假设的实际否证（2026-10-03）

## 当前投资选择

现金；投资候选NONE，长期净APR不可评价。原SMA空头只保留研究挑战者；此前90日条件净收益615.47..641.54/完整10k，不能据此认定跨市场状态有效。本版没有新策略收益或新空头成交；D040已有真实模拟SELL开空/BUY回补、资金流水和NAV证据继续保留。

## 实际完成与否决

评分日历在查看新合约PnL前固定为2024-01-01..<2025-07-01（547日）。旧Spot同日历已见，不称unseen。复用官方binance-public-data固定f446ce3812bd4e5521f21faecd4ae3c6460e49fc和既有下载/转换；新148对象包括trade1m36、mark1m36、funding36、daily38、2h2，另12旧日档只准备凭证复用。

| 实际环节 | 结果 | 实际任务与退出 |
|---|---|---|
| 148官方HEAD/CHECKSUM | 全部可用；ZIP合计104,898,965B，未读ZIP正文 | 8b31107bb5c847d3a2636968f9bba9d8；session47091/chunkc4cd9e；0 |
| 新源下载/原格式月历 | 83档完成producer格式，84档已下载；BTC mark2024-08缺分钟，拒绝 | c1f09725d84349068d0cfff9327c3033；session99178/chunke73f5e；1 |
| 单坏月独立raw时钟 | 44,638/44,640，恰缺UTC10:02、10:03；SHA/CHECKSUM/CRC真通过，无重复/倒序/越界/shift | 6cb5ab0eb32c43df88e40a242a7b4e13；chunke8356d；0 |
| 同官方日档实测 | 2024-08-12也是1,438/1,440，同缺两分钟，不存在可直接恢复记录 | 见日档实际binding；session22871/chunk611c15；0 |
| 根接受 | 只接受失败机制和官方日/月共同缺口；原全547输入仍拒绝 | 见根实际binding；chunk96d769；0 |

原失败源码、ZIP、CHECKSUM、partialPQ、receipt、83完成工件及全部任务保留；partialPQ只读footer确认16384行/4groups，不当完整来源。没有补零、前值填价、删坏日、降低完整日历守卫或换host绕过限制。独立只诊断坏月，没有重跑83档QA。148全源独立QA、完整来源根接受和547日经济均未执行，已准备入口/未运行草稿不当后台工作。

## 发现与采用决定

CHECKSUM证明对象字节正确，不能证明分钟日历完整。官方日档也缺相同两分钟，排除了单纯月档拼装错误；当前无法把整547日称为完整回放。接受严格来源拒绝及诊断能力，暂停此完整547分钟配方。reopen：合法可审计的真实缺失记录出现，或事前明确的缺失风险方法获得独立验证；不以未知价格插值或零收益解决。

下一主任务改为**事前固定2024-01-01..<2024-08-01，213日**的同产品SMA四方向＋公开Donchian对照。按源完整性决定边界，没有查看新合约PnL或按收益择日；ETH mark及真实funding尚待补齐和独立接受，不提前称完整。后续若2024-09-01..<2025-07-01的303日也完整，可另建独立10k账户；原August缺失仍公开、各窗不拼NAV、不包装547日/长期APR。原547尝试保留影响后续选择记录。

这一步能直接检验近期short优势是否依赖跌市，信息价值高于新模型/HPO。仍共同产品/资本/1x、单币绝对.3/组合gross.6、27/43bp成本、两funding单位条件；Binance代理输入与BybitVIP0费用反事实，非Bybit原生回测。原生MMR/filters/charge/publication和未来独立资格未认证。

## 资源与实际入口

source实际265.70秒、RSS170,442,752B，原新工件165,967,471B；日档4.35秒/RSS107,606,016B/40,426B，独立月档0.98秒/RSS89,710,592B。共享硬4,999,999,488B、swap0/GPU0不变。最近实际ROOT+整个D-hosted VHD扫描21,402,704,833B，于2026-10-03T05:41:59.842960Z/13:41:59+08完成，之后source输出不在扫描内；已按真实时刻发布8765，未伪报新扫描。来源启动2GB预留（1GB source＋1GB工作）低于32GB；D40GB不变。公开collector PID540保留运行，不改其来源或资格。

所有长任务经with_task_progress/bounded；窗口 http://localhost:8765/ API健康，浏览器打开返回queued，不宣称当前已经可见。

原实际入口（用于定位，不覆盖已有专属目录；复现须新独立目录及相应路径冻结）：

```text
scripts/with_task_progress.sh --title 'D042 ...' -- env PYTHONPATH=/mnt/d/codex/coin:/mnt/d/codex/coin/src POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/perpetual_history_source.py --mode source --protocol protocols/PERPETUAL_HISTORY_SOURCE_20261003_V1.json --run-dir /home/xflops/coin-state/d042-perpetual-history-source-20261003-v1 --output reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json --experiment-id D042-PERPETUAL-HISTORY-SOURCE-20261003-V1
scripts/investment/diagnose_perpetual_mark_gap.py --protocol protocols/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_BINDING_20261003_V1.json --run-dir /home/xflops/coin-state/d042-mark-gap-independent-20261003-v1 --output reports/fast_research/PERPETUAL_HISTORY_MARK_GAP_DIAGNOSTIC_20261003_V1.json
scripts/investment/probe_official_mark_day.py --protocol protocols/PERPETUAL_HISTORY_OFFICIAL_DAY_PROBE_20261003_V1.json --run-dir /home/xflops/coin-state/d042-official-mark-day-probe-20261003-v1 --output reports/fast_research/PERPETUAL_HISTORY_OFFICIAL_DAY_PROBE_20261003_V1.json
```

主要实际凭证：METADATA cbfde5a1、SOURCE失败82cae26a、单月独立c0be5f1e、官方日ce6bfef6、根ed248a0b。代码/小型协议/失败和验收报告入Git；raw行情/PQ/STATE日志留D。无发单、真钱、密钥、付费、GPU或locked访问。本模块提交推送与远程一致尚待最后门槛。
Git首次字节门槛真实失败（task1f345a7d751c4854a09bc989c734f7fd、session55686/chunke0f707/exit1），原因仅实际experiment_registry尚未加入index；补齐同一真实登记文件后用V2独立门槛，不覆盖旧失败、不重做来源/经济。

V2已真0；其检查期间补充上述模块失败说明，故最终固定index另用V3验证，之后仅追加门槛本身小凭证。来源/诊断/经济不重跑。
