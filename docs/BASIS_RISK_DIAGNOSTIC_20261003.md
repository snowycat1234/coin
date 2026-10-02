# 固定全122日基差风险诊断（2026-10-03）

当前盈利主力／真钱候选 NONE，长期净 APR NE。Bybit普通用户费用标准继续采用；本模块只检查币安既有价格的标记风险，费用和资金费尚未进入账户。

## 范围及定义

- BTC／ETH，2025-08-01..<2025-12-01，全部24份既有Spot／mark／index分钟文件，每币175680分钟。
- 同币每腿固定q=1：B=M−S，change=(B−B0)/首Spot close×10000；正变化不利于longSpot／shortMark，valuation=−change。回撤从包含初始0的历史峰值计算。
- 全期以及四个全部月份各自基准只作描述；不能择月、相加成策略收益或按月重开账户。M−I与I−S使用同一分母，并检查分解恒等式。
- Spot规范化逻辑bar end与mark/index inclusive毫秒端点+1ms严格对齐；无填补、坏行删除、重采样或期外价格。最后Nov30 bar逻辑收盘Dec1属于该bar，不读取Dec1 open。
- 封存source QA与coupon数学直接复用。没有新API、locked、模型拟合、HPO、发单或原始ZIP／CRC重复。

事前决策为D028，协议为 `protocols/BASIS_RISK_DIAGNOSTIC_20261003_V1.json`。新手算仅一个综合case，覆盖符号、prefix回撤、月份局部基准、未来扰动与时间／缺值拒绝；独立复核使用Decimal.from_float／80位精度，绝对容差事前1e−7bp，不调用runner数学函数。

## 实际执行与限定修复

运行前两次metadata freezer失败分别为cfd56b／exit1和b89b50／exit1：抄写的SHA分别多一位／少一位，来源本身与HEAD blob相同。原执行V1／V2源码和失败凭证保留；Native GetFileHash与WSL sha256sum实际一致后，将真实64位值写入未运行runner及新V3 freezer。V3实际f61d8e／exit0，19个源码／凭证绑定冻结。未修改原来源或降低守卫。

同一未运行综合case增加Spot valid_day／symbol NULL拒绝，避免Polars all忽略NULL。随后源码／测试／协议保持冻结。

实际手算任务 `ea2272ace0164c19a9a3ac2b30d4d403` 已completed／exit0，1case PASS，报告SHA `3bfdf7067ce90136b8ae7a80574ea5a8995492cff117e3e07bd004d1f1502387`。不是市场盈利证据。完整诊断于该任务真实闭合后启动。

## 结果与验收

| 全期，bp／初始Spot close | BTC | ETH |
|---|---:|---:|
| 终点不利基差变化 | 3.0661 | 2.1805 |
| 最大不利变化 | 77.4899 | 113.5435 |
| 最大有利变化 | 37.0252 | 312.4669 |
| 标记估值最大回撤，含初始0 | 114.5151 | 344.1374 |

全部四个月局部回撤Aug／Sep／Oct／Nov：BTC21.7862／21.0851／116.1500／23.8799bp，ETH62.4447／66.0207／306.7307／42.4688bp。October中途风险较大，终点小变动不能代表整个持有过程；局部月份及分量的回撤不能相加成为组合回撤。

- [完整主体](../reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json)：真实host session21964／chunk16b8cd／exit0，task`478408bc34694489b6fbbbc01a164b2a` completed／0；24／24价格文件、351360共同分钟，67.292s、进程峰值279,302,144B、新独占STATE3,721B。
- [独立Decimal](../reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)：真实session13576／chunk7d224d／exit0，task`37294ed6da394f7ea8cf7e34c536808e` completed／0；两个全期＋八个月、三分量、90极值见证。最大误差9.09555e−14bp低于固定1e−7；17.969s、80,076,800B。仅回读本次24价档close／时钟，不重做旧QA、资金费数学或绿色测试。
- [根验收](../reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json)：chunk2daa72／exit0，task`dbfaa1b56db44e929b979d67e066a6b4` completed／0。只查小凭证、来源字节和真实退出，未重算行情；[闭合来源绑定](../reports/GITHUB_BASIS_RISK_SOURCE_BINDING_20261003_V1.json)保存33个ROOT文件绑定。
- 两次root metadata freezer失败与独立audit metadata准备失败均保留；独立准备失败未运行Python／价数组。实际用到的独立代码／ACTUAL_BINDING／失败记录精确归档于 `docs/archive/BASIS_RISK_USED_INDEPENDENT_SOURCES_20261003_V1/`。

最新实际盘扫描结束2026-10-03 02:21:55.586777 +08:00，项目4,379,890,855B＋整个D WSL VHD15,028,191,232B＝19,408,082,087B，10MB预留、状态OK；不是当前瞬时容量。共享硬上限4,999,999,488B、累计峰值3,236,868,096B、swap／GPU／OOM0。

模块采用其风险尺度能力，不产生盈利资格。下一版D029连续账户已明确单成本、C0、netbase对冲、钱包和因果风险退出；准备中的代码尚未合成验收／历史运行，不能登记为完成。

## 如何使用结果

max adverse代表中途资本／保证金压力，不能仅因接近旧coupon余量而自动宣称亏损或STOP。旧coupon是固定事件名义∑r；本次是固定q／S0的价差变化，两者不能直接相加。

下一步直接做一个事前固定的连续条件carry账户：相同总资本，Spot received-asset费用、perp quote费用、净数量对冲、全部signed funding、现金／隔离保证金及因果退出。Binance价格／未认证fraction funding加Bybit当前费用只叫CONDITIONAL_PROXY；真实fill、filters、收费mark、维护保证金／清算／ADL尚未核准，不能变成Bybit收入或真钱候选。

本次只读复核官方 [资金费公式与结算边界](https://www.bybit.com/en/help-center/article/Funding-fee-calculation)和 [USDT订单费用](https://www.bybit.com/en/help-center/article/Order-Cost-USDT-Contract)：按持仓数量及收费mark计算，funding先可用余额、不足再减isolated initial margin，开平资金费时刻前后5秒归属不保证；USDT合约交易费用以USDT结算。这些文档不认证币安历史rate单位或close代理收费价格。该口径已用于未运行D029草案，之后另冻结协议。

所有长任务通过既有进度窗口与共享5GB边界；新STATE独占≤10MB、单任务≤600秒、swap0／GPU0／D盘40GB。窗口实际结束码可信；现有wrapper结束时清除细进度计数，因此最终文件完成数以封存报告为准，不修改冻结观察器。

复用既有已完成扫描发布 helper，仅把本次报告的真实19,408,082,087B及02:21:55测量时刻发布到窗口，未新扫描／改观察器；真实chunk60de9c／exit0。不会把发布时刻误写为测量时刻。
