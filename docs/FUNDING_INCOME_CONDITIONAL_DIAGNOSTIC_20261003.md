# 资金费收入与Bybit普通用户双腿成本：条件诊断

## 当前选择与发现

盈利主力及真钱候选仍为 **NONE**，长期净APR没有新证据。保留carry研究方向；下一步优先核Bybit原生公开历史资金费，再决定是否值得补基差、成交和资本模型。

本版实际读完既有Binance BTC/ETH、2025-08-01至2025-12-01前的全部8个资金费月档，共732事件、每币366。按事前明确的“原始rate为fraction”假设，全部正负事件的条件coupon仍超过固定全期一次开平仓的名义成本门槛。未选正费窗口、调参、建账户或年化。

**单位未认证。** 官方交叉核对V1因WSL网络不可达退出1；V2同官方URL的已有Windows系统HTTPS通道收到BTC HTTP451，立即停止，ETH未请求、0/6匹配。两次失败保存，不重试或规避。条件分支按D024在读732事件前明确登记，不能改称单位核对成功。

## 全122日条件结果

所有bp数值均是每个事件固定单腿单位名义金额的条件换算，不是固定币数量的实际现金收入。1bp=0.01%。两资产单独报告，不相加成组合收益。

| 项目 | BTCUSDT | ETHUSDT |
|---|---:|---:|
| 原始带符号rate和，Decimal | 0.01796165 | 0.01536858 |
| 条件coupon，bp | 179.6165 | 153.6858 |
| 正事件coupon，bp | 190.3167 | 167.9389 |
| 负事件coupon，bp | −10.7002 | −14.2531 |
| 负事件数 / 全事件 | 45 / 366 | 57 / 366 |
| 最长连续负事件数 | 10 | 4 |
| 最差负序列coupon，bp | −2.5472 | −2.0328 |
| 含初始0的累计coupon最大回落，bp | 5.8003 | 2.6547 |
| 扣31bp门槛后的条件余量，bp | 148.6165 | 122.6858 |
| 扣51 / 55 / 63bp后的条件余量，bp | 128.6165 / 124.6165 / 116.6165 | 102.6858 / 98.6858 / 90.6858 |

累计coupon回落不是NAV最大回撤。连续负事件只报告实际事件数，不推断持仓时长、风险概率或独立交易样本数。

## 全部月份

| UTC月份 | BTC条件coupon，bp | ETH条件coupon，bp | 每币事件数 |
|---|---:|---:|---:|
| 2025-08 | 60.4522 | 53.8840 | 93 |
| 2025-09 | 43.7436 | 27.9144 | 90 |
| 2025-10 | 30.7351 | 29.5345 | 93 |
| 2025-11 | 44.6856 | 42.3529 | 90 |

月表是描述性和，没有每月重开账户或重复扣开平仓成本。跨月负序列和回落在全期另算；严格负rate<0，0及正值打断负序列。

## Bybit普通费率与经济边界

沿用已冻结 [普通用户费用参考](../protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json)：普通crypto现货maker/taker单边10bp；普通永续maker2bp、taker5.5bp。本次使用taker，两个产品分别计价。[官方费率](https://www.bybit.com/en/help-center/article/Trading-Fee-Structure)

全期一次两腿开平的名义fee-rate门槛为2×10+2×5.5=31bp；假设每腿每side滑点4bp，另加两腿各2/4/8bp往返点差，得到51/55/63bp。全部档位报告，未降低旧成本来制造通过。

这些是固定匹配单腿名义金额的成本假设，不是实际净PnL。Bybit现货买入从收到的币扣费；真实净对冲数量、两腿价格变化、费用资产及再平衡尚未建账。原生现货费用适配已验收，本诊断未借它暗示完整carry会计闭合。[现货收费规则](https://www.bybit.com/en/help-center/article/Bybit-Spot-Fees-Explained)

尚缺Bybit原生历史费率、收费对应mark、提前可用时间、可成交basis/BBO、两腿完整成交、总资本／抵押／保证金、清算／ADL、融资及转账摩擦。Binance funding加Bybit当前基础费率是条件映射；不是Bybit历史账户收益。NAV、净结果、换手、Sharpe、资本MDD与净APR均 **NOT_EVALUABLE**，不能以0替代。

## 实现、复用和实际运行

- 复用已接受官方Binance月档、CHECKSUM／逐行来源QA、已锁Polars／PyArrow、原bounded／progress／registry；未重扫24档来源QA、重下载、读取mark/index/Spot价格数组或新建carry执行框架。
- 薄 [诊断入口](../scripts/investment/funding_income_diagnostic.py)保留严格六样本认证分支；条件分支必须显式选择且绑定唯一HTTP451失败SHA，无自动fallback。原未运行严格准备版源码／测试精确归档，未称失败实验。
- 唯一新合成数值case实际exit0；完整732事件实际exit0；旧绿色测试、Spot参照及RSI2账户直接复用，不重跑。
- 实验前 [协议](../protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json)固定全部时期、源、假设、成本、统计与预算；[数值验收](../reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_TINY_20261003_V1.json)、[实际结果](../reports/fast_research/FUNDING_INCOME_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)、[V1网络失败](../reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V1.json)、[V2限制停止](../reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json)均保留。主任务事前START与事后RESULT已登记；独立审计／根验收结果在完成后如实追加IMPORTED_OPERATIONAL_RESULT，不伪造事前START，原ACTUAL_BINDING／RECOVERY_BINDING保留。
- 原CSV字符串的独立Decimal核验：[首轮失败](../reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)已完成全期／月／负序列／回落／成本对照，因错误只接受Arrow string而拒绝等价large_string停在prefix明细前。原失败及source字节保留。
- [限定恢复与组合验收](../reports/fast_research/FUNDING_INCOME_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json)仅修逻辑字符串类型断言、独立补验全部732条prefix，不重算已过聚合；prefix最大差1.4188e−14假定bp，小于事前1e−9容差。不是一次全套新测试。组合报告移除未用月度门槛字段，原月统计／成本不改。
- [根验收](../reports/fast_research/FUNDING_INCOME_ROOT_MODULE_ACCEPTANCE_20261003_V1.json)实际exit0：数学闭合、单位仍未认证。单位任务failed1、主诊断completed0、审计首轮failed1与剩余明细恢复completed0分别核对，未将失败洗成通过。
- [提交源码出口](../reports/GITHUB_FUNDING_INCOME_SOURCE_BINDING_20261003_V1.json)仅核40个已接受小凭证／源码字节并精确归档实际STATE checker，不重复统计或QA。未运行的较大出口准备工具留本机，本次采用薄出口；源码、协议、失败和原resource字段均保留。

最新实际容量扫描结束于2026-10-03 **01:00:09.997777 +08:00**：项目加整个D盘WSL VHD **19,413,115,004B**，预留10MB，40GB上限／32GB预警／36GB停新增不变。扫描发生在本次coupon输出前，不是当前瞬时值。实际诊断68.695s，WSL进程峰值209,637,376B，独占新工件17,470B；合成编排101.242s，进程峰值183,013,376B，其中case27.98s，含容量扫描。

共享WSL cgroup历史峰值3,236,868,096B、硬上限4,999,999,488B，swap0／OOM0／GPU0。prefix独立恢复进程峰值84,561,920B、3.624s。单位V2的Windows网络搬运进程另测峰值88,535,040B，WSL探针55,939,072B；不是同时总峰值，也不把Windows搬运称cgroup内计算。所有Python、测试和统计均在bounded WSL，原env/uv.lock不变。

复现入口（hpc_linux；数据与env在D承载STATE；冻结输出不能原路径覆盖，复核必须新实验ID及新目录）：

```sh
scripts/with_task_progress.sh --title '条件资金费诊断 · 复核' -- \
  env PYTHONPATH=.:src POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python \
  scripts/investment/funding_income_diagnostic.py --research \
  --protocol protocols/FUNDING_INCOME_DIAGNOSTIC_122D_20261003_V1.json \
  --run-dir /home/xflops/coin-state/funding-income-owned-review-20261003-v1 \
  --output reports/fast_research/FUNDING_INCOME_REVIEW_20261003_V1.json \
  --experiment-id FUNDING-INCOME-REVIEW-20261003-V1
```

这是独立复核命令示例，本轮未再执行；示例目录／报告／ID已存在时必须另取新名称。真实源码、命令、task和输入SHA见各报告binding；原归档不变。

## 采用、暂停与下一步

采用条件统计能力和完整负事件证据，**不采用资金费投资候选**。目前不足以判断长期收益；条件成本余量有价值，值得用Bybit原生公开输入作下一次窄验证。

优先固定BTC/ETH各一个2025-08-01历史小窗口，核官方V5资金费接口的真实覆盖与字段，再决定是否补完整122日。复用已锁httpx与既有来源小报告；HTTP403/451或地区限制立即停止。官方文档未保证历史留存、排序与边界包含规则，不补造缺事件，也不将当前interval回填历史。[官方历史接口](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)、[资金费说明](https://www.bybit.com/en/help-center/article/Funding-fee-calculation)

完整carry净APR研究暂停，重开需Bybit原生单位／收入及basis／资本／成交边界闭合。固定RSI2配方与旧短周期路线按旧reopen条件继续暂停；保留实现能力与全部证据。真钱、账户密钥、locked及资源边界不变。
