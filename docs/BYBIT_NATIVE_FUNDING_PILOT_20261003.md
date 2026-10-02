# Bybit普通费用与原生资金费小窗口（2026-10-03）

## 科研结论

1. **当前APR候选**：NONE；保留carry研究能力，暂停原生carry投资映射。
2. **净APR证据**：本次无资金费记录／经济计算／账户NAV／APR。此前Binance条件coupon
   BTC179.6165／ETH153.6858bp仅在fraction假设下成立，不改称Bybit收入。
3. **最大阻碍**：实际唯一BTC请求HTTP403。96B错误body明确CloudFront国家访问限制，
   不是有效JSON，无法提取规范Bybit业务码；不推断用户所在地域。ETH未请求，0样本。
4. **重要发现**：普通费用口径可以采用，原生收入可用性仍需实际核对。接口FAIL不会降低
   已冻结成本，也不产生“无数据就是无alpha”的结论。
5. **下一项**：用既有全122日Spot与mark/index核基差风险尺度。原条件成本余量只有
   116.6165／90.6858bp；不利基差与额外资本占用可能消耗它。先核Spot价格／时间语义，
   再冻结来源、固定数量和完整期间；不与coupon简单相加制造净收益。
   [只读源接线](../reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json)已找到24准确路径／既有SHA；
   Spot是官方1m kline Close，proxy inclusive close+1ms与Spot逻辑bar end对齐，不是BBO或fill。
   此报告只读元数据，价数组／实际basis尚未运行；不算本轮经济成绩。
6. **暂停及重开**：Bybit完整历史采集／income adapter暂缓，合规可达原生输入后重开。
   固定RSI2／更多阈值暂停；新独立时间或信息给出毛优势／成本余量并事前冻结后重开。
   maker及真实carry仍需可成交价格、收费mark、数量／费用资产和资本／保证金闭合。

## 已采用费用

| 普通产品／VIP0 | maker每边 | taker每边 | 费用资产边界 |
|---|---:|---:|---|
| 常规crypto Spot | 10bp | 10bp | 买入扣base，卖出扣USDT |
| 常规perpetual/futures | 2bp | 5.5bp | 不可借用到Spot；资金费等另算 |

[冻结费用profile](../protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json) SHA
`d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f`不改。
Spot费用资产薄adapter和六账户经济影响已经验收；本轮复用证据，不重跑。
当前历史行情仍是Binance来源，当前Bybit基础费率不认证历史账户／地区或Bybit成交。
见[原费用资产结果](BYBIT_SPOT_NATIVE_FEE_ECONOMICS_20261002.md)。

## 唯一原生运行

[请求前协议](../protocols/BYBIT_FUNDING_HISTORY_PILOT_20261003_V1.json) SHA
`8d8efd1c5af9f9b8b788715f0142f2a7f178fa1653dc650ca3327e8598281062`，
HEAD `6d46fc8bb9d90a65f2262fb544f1de1a328dc4aa`。主API只读，无密钥或订单操作。
事前固定linear BTCUSDT、ETHUSDT，2025-08-01 UTC半开一天、双边ms参数、limit200；
最多2请求，每响应20s／64KB，任一失败停止。源路径／SHA及旧费用／失败／数学证据绑定。

[实际失败报告](../reports/fast_research/BYBIT_FUNDING_HISTORY_PILOT_ACTUAL_20261003_V1.json) SHA
`eac907e172ac401dd05546645bf67c7dc724e3968afd62ad661cd885eb9d2765`；
实际host session **76274**最终exit **1**（`chunk:f1a912`），task
`5ac8dbb781d849ce8a42e51d162fbd65`为failed／exit1。唯一BTC HTTP403，未请求ETH；
无重试／重定向／域名／通道切换。原始body仅D承载STATE，SHA
`7ef856c945703d5772f1b1f2a8c65913247c9b0769302b10facfe14fa1e2083c`。

实际操作1.849s、WSL Python SELF peak56,283,136B，Windows bytes传输进程peak86,396,928B
单列。Linux共享当前333,799,424B、历史累计peak3,236,868,096B／硬限4,999,999,488B；
这些scope不能冒充整机同时峰值。swap0／GPU0／OOM0；STATE阶段计量8,955B。
新产物预算2MB，合计磁盘最近实际扫描19,413,115,004B（2026-10-02 17:00:09.997777UTC），
不是本次瞬时扫描。全部Python／校验在bounded hpc_linux，Windows只取字节。

## 实现与验收范围

新增薄runner及既有系统HTTP封装；复用JSON／Decimal、来源凭证与registry，不装SDK、
不造下载框架。严格校验retCode整数0、重复JSON key、非finite常量、非空且未触分页cap、
symbol／category、字符串ms边界与重复事件、有限Decimal率。未假定8h或每天3次；
未触cap也不认证完整历史／收费日历。官方文档只支持Bybit ratio惯例，不认证Binance单位。

[唯一新增合成核验](../reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_SYNTHETIC_20261003_V1.json)
实际exit0：非8h正例及boolean retCode／重复key／越界日期三负例；0网络／市场输入。
真实接口FAIL与合成parser成功分别记录，旧funding QA／统计／绿色测试／Spot回放未重跑。
[独立失败源审计](../reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_FAILED_RESPONSE_AUDIT_20261003_V1.json)
真实exit0（`chunk:e09a3c`），SHA `cb8c43f5…9abf83f`；只核唯一96B失败body／绑定／停止边界。
[根验收](../reports/fast_research/BYBIT_FUNDING_PILOT_ROOT_ACCEPTANCE_20261003_V1.json) SHA
`b9388498…b111202`，真实exit0（`chunk:e0c282`），task`9994290a86b347d7a30f47260058ef9f`。
[闭合task与29文件绑定](../reports/GITHUB_BYBIT_FUNDING_PILOT_SOURCE_BINDING_20261003_V1.json)
SHA `370055c0…a02f3b2`，核根completed／0，未重做任何市场QA／统计／测试。
合成、审计和根验收通过只证明边界，原pilot仍failed／1，native data／unit gate **NOT_PASSED**。

请求START／RESULT真实追加registry；独立操作完成后导入记录明确为post-completion，不虚构预注册。
冻结失败／旧数学报告不覆盖，raw响应／STATE不入Git。模块验收并修文档后正常commit／push，核远程一致。
8765窗口保留，实际exit1可见；本次短任务的最终进度计数未提供，报告明确1次请求／0样本，不造百分比。

官方参考：[接口格式](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)、
[主机及访问范围](https://bybit-exchange.github.io/docs/v5/guide)、
[资金费公式／符号／结算边界](https://www.bybit.com/en/help-center/article/Funding-fee-calculation)。
NO_QUALIFIED_CANDIDATE；locked／真钱／密钥／付费／GPU边界保持。
