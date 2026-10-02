# 固定连续条件carry账户（2026-10-03）

当前盈利主力／真钱候选NONE，长期净APR尚无证据。本版将费用、数量、资本和资金费放进一个连续账户，回答成本后的净收益问题。采用Bybit普通用户费率；Binance价格／funding及未认证fraction单位仍为条件代理，不能称Bybit原生回测。

## 本版改变

复用现有来源／价格对齐、Bybit received-asset Spot结算、Polars及quant.metrics。原Spot单腿引擎没有perp钱包／funding，新增一个最小双腿状态循环；原backtest、ExecutionContractV2、FrozenPredictor／STOP_v2／A07、原采集、环境及冻结来源均未改。

- 2025-08-01..<2025-12-01全部24价档＋8funding档；每币175680分钟、全732原始signed事件，不择月、删负值、月重开或拟合／搜索。
- C0=10000USDT，首次闭合Spot价确定每币1250USDT／腿净base数量；下一分钟close+1µs代理fill。Spot买入费扣收到base，再按实际netbase建立同量short；fractional quantity／dust0是固定代理，不虚构Bybitfilters。
- 每币1250USDT独立reserve，其余freecash。short名义卖款不记现金。funding／perp fee先freecash，不足只扣本币isolated余额；每次资金费／fill前后都进入NAV峰谷。平仓只释放余额与realized一次。
- 单成本：Spot taker10bp／side、perp taker5.5bp／side；每腿RTspread8bp、每side slip4bp，代理成交相对mid±8bp，保留最高既有假设。
- 资金费按held q×严格过去close mark×原signed rate，strict entry<event<exit；不能收开仓前事件或借未来close。报告开平±5s事件见证，真实归属仍不保证。
- gross≥0.6／每underlier两腿≥0.3或isolated权益≤初始50%触发下一分钟全平并永久CASH，晚一bar超限如实记录。isolated权益≤0直接FAIL并保留资金／事件见证，不模拟未知清算或跨腿救援。最终固定端点强平是事前已知模拟约定。

D029在新carry数学／数组回放前已追加；协议 `protocols/CONDITIONAL_CARRY_ACCOUNT_122D_20261003_V1.json` 真实metadata freezer session10376／chunk4a5752／exit0，45来源冻结，SHA `7d6a03f7d74225bb66f86dd1e4f84108cc2dcf1cc21d234ec3e8672f94e6f5b0`。新STATE≤50MB／600s，共享5GBRAM、swap0／GPU0／D盘40GB，测试工件仅独立STATE。

## 实际验证与执行状态

未运行draft静态金融审查发现负isolated权益仍可等下一bar卖Spot偿补，形成隐含信用。冻结前已修为明确FAIL＋见证；同一新手算case改用仍有正权益的合法stop例，并增加破产拒绝、END−1合法／END拒绝和smoke task身份检查。未执行草稿不存在市场结果，不算旧绿色复测。

[唯一新综合合成验收](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_TINY_20261003_V1.json)实际chunk4eff5d／exit0，task`847ddb7a6d284a36ae81bb009d1fd40a` completed／0，1case PASS。覆盖费用资产／netbase／手算现金、全部正负funding、严格过去mark、因果退出、未来扰动、隔离破产与端点拒绝；0历史数组。报告SHA `dcfe7aafa049e1f8f366ce2873b133fb7ea7882fc9c0894d63442cb60b92a0a4`。

完整122日账户在上述真实闭合之后启动：[实际主体](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json)host session10927／chunk1714f6／exit0，task`3d8becf9dd934cb5989def1c1b007c80`。报告SHA `d036745c61ce30203d6c941af863979591425604b7cea879277a2e22f0a57bbf`。独立金融复核与根验收已完成，采用条件代理账户的会计能力，暂停该全平配方的盈利采用。输出为小JSON及STATE minute／daily NAV、funding和fill四份账本，不提交真实行情或账本数据到Git。

| 初始资本10000USDT，固定整个122日期间 | 条件模拟USDT |
|---|---:|
| 期末NAV | 9988.988651 |
| 净PnL | −11.011349 |
| 正负资金费合计 | +5.621259 |
| 同量成本回加gross PnL | +5.668891 |
| 手续费 | 8.207217 |
| 假设价差 | 4.236512 |
| 假设滑点 | 4.236512 |

全期净收益率−0.110113%，全观察MDD0.110113%；daily机械样本年化−0.329077%、Sharpe−1.63817，只描述该已见条件窗口，不叫长期净APR。账户处理全部732事件，其中68属于真实模拟持有期、664明确排除；开仓前／全平后不收券息。ETH双腿gross触及0.3后，下一分钟全平、其后9–11月CASH未再收funding；最大ETH gross0.300602是信号与成交期间实际漂移，未声称cap从不突破。

风险触发时ETH isolated权益约997USDT，高于625阈值；触发来自名义敞口增长，而非保证金破产。只有约11.65天持有，资金费5.62不足以覆盖16.68成本，basis成本回加残差仅约0.048USDT。不据此永久删除carry能力。

[唯一完整独立Decimal审计](../reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)真实host session22783／chunkfa9bb0／exit0，task`0dd64023f7044304b233794fcfc7ee9d`；SHA `7c1c82b52c7f95b29d861c2c902dd91400d66a6ca912671f3be281219bd651d0`。不调用主体simulate_account，独立核32来源、175680分钟、732事件、8fill、122日、4月、首次risk信号及下一分钟全部退出。最大现金误差1.42027e−11USDT＜事前1e−7，ratio误差7.28306e−14＜1e−10；终点桥差−8.06e−14USDT。独立净损益与全部月份一致，9–11月确实零资金费／零收益增量；16.770s、RSS119,386,112B。

[根验收](../reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json)真实chunka0d87a／exit0，task`79e5521f9e1843799d8be986c2cdac76`，SHA `42c499ea7f362da2518fa22ebadb6146f1a180b5cd5bc42faaa0b0a348fa3b83`；[已闭合源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json)真实chunk24ec32／exit0，56ROOT来源。根侧仅检查原证据／closed0任务／工件字节，未重做行情数学、旧QA或绿色测试。实际checker、ACTUAL_BINDING、元数据准备脚本及其首轮Windows签名策略拒绝（chunk20071b／exit1、0Python／0数组）精确归档；随后普通元数据命令成功，不修改执行策略，不隐去失败。原funding单位任务failed1继续保留。

实际70.830s、主体RSS539,357,184B、独占新STATE1,856,955B；175680账户分钟／122日／8fill／732funding账本。最新扫描2026-10-03 02:47:10.171751 +08:00，project4,386,135,686B＋D VHD15,028,191,232B＝19,414,326,918B，50MB预留／OK，既有helper真实chunkafb615／exit0发布原测量时刻到窗口。共享历史峰值3.24GB／硬上限约5GB，swap／GPU／OOM0。

## 使用与经济边界

同资本、费用、exposure caps可以作描述对照；原30d covariance／10%vol、perp真实容量／MMR／ADL／lot与原生收费mark未核，不能宣称完整风险等价。daily年化仅样本机械复利描述，不是可持续长期APR。旧coupon与基差统计不能代替该账户。

下一项D030仅一个同caps／同成本／同资本的matched pair部分减仓机制控制：敞口信号触发后，按signal NAV与两腿价格冻结目标qty到0.25NAV，下一闭合分钟只减超限币的等量Spot／short，保留另一币；不增仓／重入／补资／调原0.3与0.6门槛。原1250reserve与625margin阈值保留，margin guard仍全部退出。它检验持有长度能否摊薄成本；已见同窗只能机制对照，不能变成unseen OOS。当前尚未运行该控制，需另冻结协议与验收。

本全平配方暂停盈利采用并保留控制；reopen为新独立时间／原生信息在相同成本与caps下显示可覆盖成本的持有及净稳定性。carry能力不永久删除。原生Bybit映射需合规可达价格、funding单位、实际收费mark、filters／容量与保证金；不提高杠杆、降成本或事后择窗制造APR。

官方结算参考：[Bybit资金费](https://www.bybit.com/en/help-center/article/Funding-fee-calculation)、[USDT订单成本](https://www.bybit.com/en/help-center/article/Order-Cost-USDT-Contract)。这些文档不能认证Binance历史rate单位或close代理收费mark。locked、真钱、账户密钥／新付费、GPU权限边界保持。
