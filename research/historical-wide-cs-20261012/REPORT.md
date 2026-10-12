# 历史资产池重建及严格下一日开盘筛查：本固定配方 STOP

分支 `research/historical-wide-cs-20261012`。没有采用今日交易名单或2024July池回选2023。先冻结2022Nov8选池时点、October真实quote-volume排序、Aug–Oct92日完整历史和Nov6实际成交存在，固定TOP20；在2023价格读取前公开POOL。后来退出/更名的旧符号没有因今天名单而被删除。**当前档案母集合、历史版本和完整退市处置仍不能认证。**

原b00183d目录880唯一符号，July可排名279、July UNKNOWN601、资格UNKNOWN2（NOT/ZRO已在279中），全部UNKNOWN603：279+603−2=880。598个July404和GAL/RNDR/RENDER的3个网格错误不是不可交易证据。原生产字节恢复于同提交的docs/archive/MULTI_ASSET_DATA_PRE_ROLE_DIRECTORY_FIX_20261004_V1.py，SHA6f10671c；没有冒充后续scripts版本。

本次官方页面明确指向其S3目录；沿用原inventory分页解析，两页1056prefix筛成880历史档案名称。2022October151完整可排名，729排名UNKNOWN；1000LUNC资格额外UNKNOWN与排名交叉，合计730未知记录且151+730−1=880。UNKNOWN包括缺档、部分月份和过去资格缺口，不转写为不可交易、上市或退出。按排序检查21名得到20个合格名称，规则和池规模不随2023结果改变。

固定集合：BTC、ETH、DOGE、XRP、SOL、MATIC、ETC、BNB、ADA、1000SHIB、CHZ、SUSHI、LINK、RSR、GMT、ATOM、EOS、REEF、KLAY、LIT（全部USDT）。后续仅作描述的目录观察中，MATIC最后档案月2024Sep、EOS2025May，REEF/KLAY/LIT目录仍有2026Sep对象。**文件存在/缺失或名称更改均不能证明实际持续交易、清算日期或结算价**；未读取这些2026价格正文，也未把这项后见元数据用于选池、目标或交易。先前概括这些名称“后来退出”不能代替合约证书，精确限制见evidence/lifecycle。

当前对象LastModified有晚于Nov8的例子：MATIC Aug档2023Jun、Oct档2022Nov17、Nov6日档Nov30。真实历史成交日期支持过去交易存在，但这些版本无法确证选池时已有相同公开字节；最新版本并非PIT。所有source记录保留这项差异，`full_historical_universe_certified=false`与`selection_complete_within_supplied_historical_universe=false`保持。没有补造历史exchangeInfo或无偏认证。

## 实际筛查

只做一个冻结TOP20/CS21配方，对照CORE5，均是独立10k共享数量参考。原weekly top2 long/bottom2 short、past30协方差、.10年风险/.30单资产/.60gross规则和BASE27交易成本保持。旧同收盘成交草案**未运行**；按父线程只读审查，在首个经济评分前改为**信号前一日已可得→次日实际1d OPEN**，完整365执行日2023Jan1–Dec31，最终2024Jan1 OPEN边界，保守标签成熟Jan2。只限量取得额外Jan1日档的OPEN，其他2024/2026价格未因此启封。

这是下一日开盘全成交的**价格减交易成本代理**。资金费明确未建模，逐仓、容量、最小数量、分钟时序和原生venue均未模拟；不能称完整成本、真实钱包或可交易净收益。严格时序改正不使其自动成为原生回测。

| 完整365日参考 | CORE5 | 历史TOP20 |
|---|---:|---:|
| 价格减交易成本代理USDT | −190.011836 | −1455.540254 |
| 日收益年化波动 | 13.437919% | 10.172438% |
| 日级参考最大回撤 | 14.191492% | 16.738289% |
| 最差30日 | −9.016846% | −8.583056% |
| cap-bound天数 | 109 | 28 |
| 平均预测年风险 | 9.330635% | 9.925443% |
| 平均风险短缺 | .669365百分点 | .074557百分点 |

TOP20净代理增量−1265.528418USDT；14日联合日期循环bootstrap1000次、seed811741，日收益增量95%区间[-.0010622328304258502,.00019903244951480903]，跨零。仅机器来源/成员/掩码/时序及完整日历门槛通过；正收益、正增量、CI下界和风险门槛均失败。**STOP_FIXED_ARCHIVE_TOP20_DAILY_SCREEN**，新分钟/资金费/原生钱包阶段0，不补大档、不改池、方向、窗口或门槛救援。结论只否定这个覆盖有限的TOP20/CS21/lag1冻结配方，不否定整个宽池或做空。

同风险策略不等于实际风险匹配：原API在最多4个持有腿的协方差上投影，以结构性未分配CASH补齐旧5维接口，未编造价格/估计。N资产投影独立测试通过。两臂现金天数0，最大风险短缺6.405104/1.786553百分点；这不是仅换宽度的精确同风险alpha。365日全部目标改变，没有复跑旧原生账户。

## 保存、检查与实际访问

7项来源/投影/缺价格保留库存反例测试PASS。真实输入上的原成员集合、SOURCE与INPUTS SHA、允许年份、严格signal<opening、未来价格**与NaN掩码**不改变过去权重/eligibility检查全部PASS。CORE5在364重叠日期与现有native intents最大误差5.551115e−17；首个Dec31信号用原full5 API单独核验，没有捏造不存在的旧日期golden。

215个选池原1dZIP+225个评价原ZIP及校验和公开保留，CORE5评价价格/开盘沿用已公开e33cc15b/be48数据，0新CORE5评价下载。选择来源238.040700秒、最终串行接续228.108484秒、成功准备.676596秒、实际2个参考评分.090761秒。零学习拟合、0原生钱包、0旧原生重放。预算始终1400metadata/1500archive GET、2MiBmetadata/12MiBarchive、单ZIP64KiB，1CPU/4GBAS/2GB采样RSS/8GBhost/swap0/GPU0/15GiB磁盘；没有扩资源。当前reported计数与载荷为含在途预留的保守上界，实际逐响应记录可复核；不把它们伪称精确请求数。

工程失败完整保存：CORE5 NPZ无内嵌symbol_order，先在0请求时停下，绑定原外部PREPARATION SHA后接续空目录；BNB元数据/CHZ ZIP两个不同503分别保留收据，恢复时使用已验真54/63原档，未重新下载完成ZIP。串行、每URL只补一次、事件上限，未绕403/451或改来源。一次Git远端读503随后同端点核验成功。prior-day P1无匹配日期的golden检查在0经济评分时失败，改用原full5 API且保留364旧日期比较。没有静默替换任何实际经济结果。

源码/规则33319f08与严格时序fec4bbb7；池3fd41b77先于2023来源；全部原来源92a4bfc5、目标0867dbef先于首个评分；结果ed885d21519d7727e3894c6571dd93288717a3a6均普通push并核远端。四个公开包合计2473961B。公开冷恢复重新核验440个原ZIP的SHA/CRC/原CSV解析，所有源、输入、目标、risk/membership proof、730保存行和NAV连续性逐字/数值一致，4.167616秒，原STATE读取尝试0、provider0、拟合0、价格代理重跑0、native0。其限定是保存来源和数学代理的恢复，未冒称重建历史交易资格。

最小零重跑复现（当前已安装环境，全新STATE）：

```bash
COIN_CPD_STATE=/workspace/historical-wide-cs-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/historical-wide-cs-state \
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
research/historical-wide-cs-20261012/persist.py restore \
 --state /workspace/historical-wide-new-public-recovery \
 --artifact-commit ed885d21519d7727e3894c6571dd93288717a3a6 \
 --kinds SELECTION EVAL_SOURCE TARGETS SCORES
```

项目仍ACTIVE。全母集/历史版本/退市处置证据尚缺；当前锁文件仍缺失、不作授权或SHA核验声称；封存2026/未知保留价格正文未读。原高点STOP、原19+2真实账户和额外收费退出、另一研究目录均保留。不使用Library、密钥、凭证、付费、实盘、部署、main或force。
