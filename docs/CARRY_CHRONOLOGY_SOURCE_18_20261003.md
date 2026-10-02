# 固定90日carry输入：18份新来源已验收（2026-10-03）

## 投资判断

当前盈利主力／真钱候选仍为NONE，长期净APR未证明。较好的条件研究机制为部分配对减仓：此前122日净收益0.247449%、全观察最大回撤0.387572%，机械年化0.742143%不代表长期表现。本模块只补齐下一次固定时间比较的输入，没有计算新的收益或调参数。

## 本版改变

已获取2025-12、2026-01、2026-02的BTCUSDT／ETHUSDT官方USD-M fundingRate、markPriceKlines、indexPriceKlines共18月档。原6份现货档及旧Aug–Nov证据直接复用。新薄入口只调用已登记的 `binance/binance-public-data` 固定commit `f446ce3812bd4e5521f21faecd4ae3c6460e49fc` 的原 `utility.download_file`、既有下载／转换函数及独立 `audit_one`，不创建下载框架，不重复旧QA或绿色测试。

新的转换输出增加事前空间检查和文件大小限制，预留5MB给凭证／日志；压缩CSV流式读取，不落地解压文件。获取与独立QA为两个任务，后者在前者真实退出0后才开始。

## 实际证据

| 项目 | 实际结果 |
|---|---:|
| 官方ZIP及CHECKSUM | 18份，11,834,094B ZIP |
| 完整1m价格代理 | 12月档，518,400行 |
| 原始资金费事件 | 6月档，540次 |
| 新来源独占空间 | 30,797,249B |
| 声明解压CSV累计 | 50,874,984B，未写入磁盘 |
| 获取进程峰值RAM／耗时 | 89,952,256B／132.14秒 |
| 独立QA峰值RAM／耗时 | 137,170,944B／9.23秒 |

540次为实际计数，不是预设8小时模型。逐月原CSV与Parquet全值一致、完整EOF／CRC／CHECKSUM、价格分钟网格、资金费实际报告间隔及跨月邻接均通过。当前共享内核上限4,999,999,488B、swap0／GPU0／OOM0。

实际来源：[主体](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ACTUAL_20261003_V1.json)（session81115／chunk9b7e54／exit0）；[独立QA](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_INDEPENDENT_QA_20261003_V1.json)（session53040／chunk5178c7／exit0）；[根验收](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ROOT_ACCEPTANCE_20261003_V1.json)（chunk241650／exit0）。根验收只检查小凭证、闭合任务、源码和文件大小，未重读行情或重做QA。

首次启动的进度窗口参数错误在源脚本执行前退出1，HTTP／行情读取为0；[原失败](../reports/fast_research/CARRY_CHRONOLOGY_SOURCE_WRAPPER_LAUNCH_FAILURE_20261003_V1.json)保留，删错误启动参数后源码不变。没有把失败当成成功。

实际磁盘扫描结束于 **2026-10-03 03:49:33.484213 +08:00**，项目＋整个D盘WSL VHD为19,423,426,934B，预留200MB。这是获取前的扫描时刻值；30.8MB来源随后完成，不能称当前瞬时占用。8765已复用该扫描时刻，不另扫盘。

## 采用、边界与下一步

采用18档作为来源格式合格输入。`last_funding_rate`经济单位仍UNCONFIRMED，计费mark／发布时点、Bybit真实成交价格、filters、维护保证金与容量未认证；原403／451失败不重试绕过。标记和指数OHLC不是可成交价。没有行情原始文件、环境或数据库进入Git，也未读取March价格或locked。

下一步仅比较两个事前固定的90日账户：ALL_FLAT与PAIR_TRIM；资本10000USDT、BybitVIP0 taker Spot10bp／perp5.5bp、价差滑点、敞口caps与保证金规则保持，0调参。该时间已被Spot研究看过，标签为SCREENING，不称真正unseen OOS。它直接检验此前小净收益是否跨时间保留。新周期／来源／端点绑定验收后才运行账户数学。

暂停pair-target搜索及固定全平配方的盈利采用，保留控制；重开需新独立时间或原生信息在相同成本caps下显示净稳定性。原生映射需合规可达原生数据和真实执行保证金；maker需真实BBO／queue。其他暂停方向沿用当前状态中的reopen条件。
