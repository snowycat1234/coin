# 同caps部分减仓机制对照（2026-10-03）

盈利主力／真钱候选NONE，长期净APR NE。当前较好的carry研究机制为只减仓、继续持有：全122日条件净收益+0.247449%，机械样本年化+0.742143%；完整独立金融及根验收已通过，采用研究机制，不授予投资资格。这不是Bybit原生历史收益或unseen OOS。

## 本版改变与依据

前版全平账户净亏11.011349USDT／初始10000USDT。ETH名义敞口达到0.3使两币约11.65日后全部退出，68次资金费合计5.621259，成本16.680241；保证金并未触及625。这是持有截断机制，不证明整个carry能力无效。

D030事前固定一个控制：原0.3每币／0.6总gross、C0、初始数量、1250每币reserve、625权益guard、Bybit VIP0费用、最高既有spread／slip完全相同。敞口触发后q_keep=min(held,0.25×signalNAV/(signalSpot+signalMark))；下一严格较晚closed分钟只减该币等量Spot／short、保留另一币，不增仓／重入／补资。margin guard仍全平，isolated≤0仍FAIL。

2026-10-03复核[官方费用表](https://www.bybit.com/en/help-center/article/Trading-Fee-Structure)，常规币币Spot maker／taker均0.1%，普通perp maker0.02%／taker0.055%，与已冻结d6c profile相同；本实验仍使用taker，未假定maker成交或账户／地区折扣。原fee profile和历史证据不改。

部分short盈利只入freecash，亏损先freecash再扣本币isolated，不借款／跨币救援；不按减仓比例释放、重置或补足reserve，不重置剩余short入场价。funding在partial精确同刻只排closing chunk，continuing chunk沿原entry计费；full due优先，新margin信号不倒撤已到期trim。开平／减仓±5秒真实归属仍未知，报告见证而不事后删事件。

复用已验收d29源码和native._replace；7组、11个exact AST anchor各必须一次，原38KB循环、来源／IO、received-asset费、metrics及旧源码字节不改。新适配器14,631B／SHA `753b1653ff2db46a0e827ba6929b3dabccbb69d1ef98e278b82ccc6c84ca1130`；新手算6,155B／SHA `619c13fa0c10020949dd77fca15989a9fad857a7148bc71d603877848dc62387`。并行静态金融review未发现具体blocker，不代替实际验证。

[新协议](../protocols/CONDITIONAL_CARRY_PAIR_TRIM_122D_20261003_V1.json)真实session99239／chunk4d0419／exit0，53来源在新数学前冻结，SHA `5c13850c48e0cbd86bf2ae3629284f6b14d61803b0c299fef3796582ae5eba49`。仅一个已见同窗机制控制，不搜索参数；旧control仅复用原摘要，不重放旧账本／QA／绿测。

## 实际新回放与验收

[唯一新手算](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_TINY_20261003_V1.json)真实session36184／chunk67e76c／exit0，task`c89291f8662a4e3ca4d40e7132ef25a3` completed0；1case／26.13s、0历史数组，SHA `2d659162c2594b72b9e1f7408a66ce9979272ee7d2f69f4d82ae1fffc86239d4`。独立Decimal手算费用／qty／partial损益与NAV桥、同刻继续qty资金费、future-prefix与625全平guard，不调用旧control.simulate_account。

[唯一完整122日](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json)真实session26970／chunk172b5e／exit0，task`b2c62d11b4d242c7a1111770545c21cc`，SHA `71a910d1da8ae9a5ca68411693f14b6f82b43ed992ac33ee50a6dcf321a6b651`。32原档／175680账户分钟／732事件／122日；730持有期计入、2开仓前排除。

| 固定10000USDT资本、同最高成本 | 条件模拟USDT |
|---|---:|
| 期末NAV | 10024.744852 |
| 净PnL | +24.744852 |
| signed资金费合计 | +39.512100 |
| 同量成本回加gross PnL | +39.134908 |
| 手续费 | 7.080385 |
| 假设spread | 3.654835 |
| 假设slippage | 3.654835 |

仅一次ETH pair trim：signal`1755012780000001`，下一分钟`1755012840000001`，q0.338209869→0.281688214，减0.056521655；signal决定目标，成交时不重新sizing。两fill令NAV下降0.790665USDT，reserve仍1250，目标成交后gross0.250283为真实漂移。之后持有至预定端点，10fill，无margin全平。全期BTC／ETH最低isolated权益1136.42／893.40；最大总gross0.559401、ETH0.300480，caps是退出／减仓触发而非保证从不超限。

完整月份净PnL分别+5.745487／+9.202667／+7.197826／+2.598872USDT，账户不按月重开。分钟／全观察MDD **0.387572%**；daily MDD0.076569%不能替代。daily机械年化+0.742143%、Sharpe3.90804只描述已见条件样本；turnover0.913709。真实funding单位／native标价、filters／容量／MMR未认证，不能把高daily Sharpe变成长期净APR证明。

[唯一完整独立Decimal审计](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json)真实session63938／chunkb5d81d／exit0，task`56874a63f4a0457185146b0cc7244463`，SHA `ffe8f92f9ec7c9e39757ca673e77d4ddc06e2780f54b1d0dd7d38f68931c6086`。32来源／175680分钟／732事件／10fill／122日／4月／1trim，cash最大误差1.45053e−11＜事前1e−7，ratio5.90639e−13＜1e−10，终点桥差−8.06e−14USDT。复用旧独立Decimal核心与原source reader，只核新timeline，不调用adapter.simulate或重做旧control数学；control仅读d036报告摘要。

[根验收](../reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json)真实chunkf18de7／exit0，task`6b5c1d9e48bc4894a53160bf09a8c93b`，SHA `3274d27bcc5b2a9809030ce30d16a25a9a47b97a06a142d968489aeff9bb30e6`；[真实closed0源码绑定](../reports/GITHUB_CONDITIONAL_CARRY_PAIR_TRIM_SOURCE_BINDING_20261003_V1.json)chunk5105d4／exit0，67ROOT来源。根侧不重放数学／数据，仅核实际任务／证据／源码及4输出字节。实际audit／delta／ACTUAL_BINDING、未运行pre-schema及两次静态元数据失败精确归档；失败为PowerShell语法拒绝与Windows参数长度拒绝，均在Python／数组之前，不隐藏或算金融失败。

对照净损益改善+35.756202USDT，**全观察MDD同时从0.110113%增至0.387572%**；相同caps不能写成实现风险完全相等或收益风险占优。采用减仓维持持有的研究能力，并保留低APR与真实执行缺口，不因daily Sharpe较高升级候选。

实际75.335s、主体RSS534,798,336B、独立约28s／RSS123,215,872B、新独占STATE8,483,079B；四份真实账本留STATE，不入Git。扫描结束2026-10-03 03:17:10.157572 +08:00：project4,392,245,194B＋D VHD15,028,191,232B＝19,420,436,426B，50MB预留／OK；原metadata publisher真实chunk0442cf／exit0发布原测量时刻。共享历史峰值3,236,868,096B／hard4,999,999,488B，swap0／GPU0／OOM0。扫描为测量时刻值，不是当前瞬时容量。

## 采用、暂停与下一步

采用减仓维持持有的研究机制，约0.742%机械年化的收益仍低；不因正结果增加杠杆、降成本、择月或继续target HPO。下一项D031固定2025-12-01..<2026-03-01时间外推，pair-trim与ALL_FLAT两个控制规则／费用／资本／caps完全冻结；先补缺的18个官方funding／mark／index月档并核新来源，6个Spot月档直接复用已有接受证明。12–2月曾用于Spot策略研究，称时间稳定性SCREENING，不叫真正unseen OOS。当前尚未开始新下载／QA／carry数学。

具体选择见[独立一页判断](archive/CONDITIONAL_CARRY_PAIR_TRIM_NEXT_DECISION_20261003_V1.md)；[实际输入元数据清点](../reports/fast_research/CARRY_TIME_EXTENSION_INPUT_METADATA_20261003_V1.json)明确6个Spot现有文件及旧saved SHA、已检查路径中未接受的18目录。只读小凭证与file stat，不读行情／Parquet metadata，不扫遍D或重算旧SHA；下载体量、资金费事件总数与周期均UNKNOWN，不能假设540次或8h。

旧ALL_FLAT盈利配方暂停并保留控制；reopen须新独立时间／原生信息在同成本与caps下显示净稳定性。完整Bybit映射暂缓至合规可达输入、真实收费mark／资金费单位／filters／保证金。其他暂停方向沿RESEARCH_STATUS的reopen保留。locked／真钱／密钥／付费／GPU及D40GB、共享5GB边界不变。
