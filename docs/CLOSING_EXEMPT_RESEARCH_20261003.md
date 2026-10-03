# D048：平仓规则修正与同产品投资比较（2026-10-03）

## 当前结论

投资选择仍为 CASH/NONE，长期净几何 APR 不可评估。研究强基准保留过去30日协方差管理的 HOLD；固定 Turtle4h 双向配方四个条件全负，不采用为投资主力，也不开展该配方 HPO。本版采用已手算验证的小额平仓能力；独立完整财务验收以最终报告及真实退出为准。

## 本版补齐什么

原 cf47 永续账户全部开平仓都受10USDT最低名义金额约束。官方当前 [Bybit Futures Trading Rules](https://www.bybit.com/en/help-center/article/Futures-Trading-Rules) 规定平仓豁免该最低金额，仍须满足最低数量。新增薄账户仅在实际减仓时豁免 minimum notional；反手开仓仍单独守卫10USDT。原手续费、数量取整、容量、延迟、逐仓1x、资金费、margin/PnL/NAV及暂停规则保留。新快照身份拒绝与旧账户交叉恢复。原Spot库存保护与源码不改。

公开规格探测V1网络不可达；V2经既有正常HTTPS、同 api.bybit.com 实际403后停止，BTC1请求/0profile，未再请求ETH，无改host/区域/proxy/证书/keys。保留两失败、响应SHA和真实任务。**quantity/minqty1e-8、opening min10、MMR .005均是未认证代理假设；当前平仓规则也不能追认2024原生过滤器。** Binance USD-M行情/mark/资金费是来源代理，Bybit VIP0费用5.5bp/side；不是Bybit原生回测或安全清算认证。

独立新手算用例实际0：100-mid开空1，90-mid分批全平；同量毛赚10，实际点差/滑点.152、费用.1044956，终NAV10009.7435044。小额纯平仓/容量partial/reduce-only超量/反手新仓under10拒绝/恢复去重/未来quote与源身份均验证。此例有真实成本，未把mid当成实际成交价。

## 固定经济对照

2024-09-01..<2025-07-01 UTC，303实际日、每账户436320分钟，固定BTC/ETH，完整10,000USDT资本含预留。独立新账户不拼接，已见开发筛选，不称unseen。原94金融来源及4官方4h预热只复用接受凭证，不旧QA；Turtle原MIT代码7c91e0a3、固定4h/20突破/10退出/ATR20/2stop/4层.5ATR与真实回调保持。HOLD为常数多头(.3,.3)经同past30 signedcov约束，信号daily。单币abs30%、共享gross60%、1x逐仓/无补保证金、past-vol目标10%/.99buffer、原一分钟延迟/容量/真实费用及五次减仓限制保持。

两成本 BASE27/STRESS43 × 两未认证资金费解释 FRACTION/PERCENT，两个recipe共8独立账户。全8完整303、终端实际成交清仓，无先前小额残仓停机。HOLD比旧D045还复用已验D046风险量化两锚，相对旧HOLD不能声称纯账户变化；本轮Turtle/HOLD采用当前共同规则。

| 策略 | 成本 | 资金费条件 | 毛PnL USDT | 净PnL USDT | 全资本净收益 | 实际年化波动 | 分钟MDD | 换手/资本 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| TURTLE_LONG_SHORT | BASE27 | RAW_AS_FRACTION | 388.03 | -576.69 | -5.7669% | 9.0104% | 11.1215% | 69.941 |
| TURTLE_LONG_SHORT | BASE27 | RAW_AS_PERCENT | 393.44 | -555.35 | -5.5535% | 9.0195% | 11.1595% | 70.2652 |
| TURTLE_LONG_SHORT | STRESS43 | RAW_AS_FRACTION | 366.93 | -1118.37 | -11.1837% | 9.0638% | 14.2722% | 68.1619 |
| TURTLE_LONG_SHORT | STRESS43 | RAW_AS_PERCENT | 374.12 | -1097.92 | -10.9792% | 9.0824% | 14.1885% | 68.4573 |
| HOLD_LONG_ONLY | BASE27 | RAW_AS_FRACTION | 816.48 | 670.63 | 6.7063% | 10.4896% | 11.2296% | 2.1912 |
| HOLD_LONG_ONLY | BASE27 | RAW_AS_PERCENT | 817.3 | 786.36 | 7.8636% | 10.4941% | 10.9495% | 2.2047 |
| HOLD_LONG_ONLY | STRESS43 | RAW_AS_FRACTION | 816.02 | 652.77 | 6.5277% | 10.4912% | 11.2733% | 2.1894 |
| HOLD_LONG_ONLY | STRESS43 | RAW_AS_PERCENT | 816.84 | 768.31 | 7.6831% | 10.4957% | 10.9933% | 2.2029 |
CASH已知完整零持仓收益0；不重放旧现金分钟账户。相同caps不等于相同实际风险，不做事后风险放大或匹配。没有把303日开发年化值说成长期APR。

Turtle毛+366.93..393.44USDT，但手续费374.89..386.46、点差+滑点559.53..1095.32、资金费−20.52..−.20，净−11.18..−5.55%。BASE/PERCENT多头净−77.07、空头−478.27；其余三个条件两方向净贡献也负。方向贡献是原LS账户归因，**不是与LONG_ONLY配对的做空因果增量**。Turtle仅2/10正月、正日115..117/303、top5正日收益占21.5..22.6%；HOLD7/10正月、158/303正日、top5约16.7..16.8%。不能挑盈利月或有利单位。

Turtle平均gross13.86..13.90%/net1.79..1.85%，平均逐仓抵押/NAV13.81..13.85%，gross峰值49.45..49.66%；HOLD平均gross=net18.13%、抵押/NAV17.06..17.08%、gross峰27.39%。无净敞口抵消gross，完整资本分母保持。两者实现风险不同，详情见保存报告含极值/保证金/费用/多空/月贡献；低敞口不能证明原生安全清算。

旧D047四条件只BASE/PERCENT完整，本次该条件PnL完全相同；另3原342005/342725分钟失败前缀保持NE，不与新303拼接、填零或算伪全期改善。修正解决执行缺陷，未制造正收益。真实策略入口产生正/负成交、现金流水与净值，不靠旧曲线取反。

## 验收范围与失败

新smoke真实completed0，report09a5d8bc…。市场真实completed0 task0b0337c02d1b4967b61e555fbcdc4a42，report85da71ba…。独立V1 task19e3a3f...实际failed1：旧financial_journals仍所有leg>=10，误拒新CLOSE。V1源码/report2f966a.../协议/STATE永久保留；V2只将该唯一predicate改为q*fill>=10 OR leg==CLOSE，规范化整函数AST证明其余qty/step/held/no-cross/capacity/clock/fee/margin/PnL数学/容差全不变。原HandLedger与财务跨度复用，不能将旧失败悄改PASS。

独立范围是记录成交/资金费、wallet/margin/NAV、分钟/日/月/真实risk与终端，不完整独立重建Turtle/HOLD目标、策略状态或intent-sizing，也不认证native filters/发布时间/清算/资金费单位。V2实际退出及误差以下文后验更新为准。

市场449.78s，峰值RSS656,769,024B，自有新输出306,163,182B；共享硬4,999,999,488B/swap0/GPU0。最近完整项目+整个D盘WSLVHD扫描22,938,409,109B@2026-10-03T12:31:19.709266Z，先于上述输出，8765按原时刻发布，非当前总量。新任务均经进度窗口与bounded，既有公开采集未改。

为保留原始尝试，Git静态预检新增版本仅允许append-only experiment_registry单文件≤8MB，其他blob仍≤4MB；原记录前缀和原preflight源保留，秘密/冻结字节/运行文件门槛及D40GB硬预算不变。无需新库；既有开源登记未改，不重建交易或下载框架。

## 采用与下一步

采用closing语义与完整条件对照能力；不采用固定Turtle/SMA为投资主力。HOLD保持研究强基准，投资现金/NONE。下一唯一科研问题：用同固定Turtle信号的方向消融，独立LONG_ONLY/SHORT_ONLY与已保存LS/HOLD/CASH比较，检验空头是否提供净增量，或仅long+cash是否减少过高换手成本。方向归因不足以替代配对账户；固定risk/cost/capital/窗口，禁止阈值/成本/杠杆调参、选择资金费倍率或拼窗口。先薄mask兼容性，再执行必要新账户；不直接采用结果或承诺正收益。

暂停Turtle/SMA HPO与投资；reopen需可信完整执行、低成本路径在强基准之外有净增量及独立证据。数量/原生过滤与资金费桥暂停，reopen需合法官方规格/原历史响应或archive语义；403/451不绕过。复杂模型需明确额外信息价值；DUAL_THRUST需厘清作者实际column/缓存语义；547缺口需真实缺记录，禁止插值凑数。原能力和负结果保留，资金/locked/风险/资源边界保持。

## 复现

市场入口：`scripts/investment/closing_exempt_research.py --protocol protocols/CLOSING_EXEMPT_RESEARCH_20261003_V1.json --run-dir /home/xflops/coin-state/d048-closing-exempt-research-20261003-v1 --output reports/fast_research/CLOSING_EXEMPT_RESEARCH_ACTUAL_20261003_V1.json --experiment-id D048_CLOSING_EXEMPT_RESEARCH_20261003_V1 --period 303D`，完整命令/CPU环境/source SHA保存于实际RUN_BINDING。独占目录已存在不可直接覆盖；新复测须独立新冻结协议和输出。预热与既有来源若缺失则停止，不下载或补零隐藏缺口。smoke/财务命令分别见对应报告binding与runwrapper archive。
### 最终实际验收

独立V2真实completed/exit0 task2d0e5a22788c438da1d3b34214501e5d，report0cc4c9db0b068a04c7c7b0ac48925036b2496cbc7ec106de1a77964b7a4424fb：8金融调用/8完整日历，金额误差3.2741809263825417e-11USDT、比率2.2537527399890678e-14，原1e-7/1e-10容差。23.268s/RSS547,794,944B。V1失败保持，V2独立journal仅一个closing谓词不同，完整其他AST一致；记录财务通过不扩大为完整策略/native/稳定APR。

保存比较真实exit0 task0630cd295bbf4fd38cf68ba9ec2f5458，reportef992eb11d764d0571da5733584051e0aadebb8a52a74cff8d9f97e59b6776e6：4条件新Turtle-HOLD完整配对，旧Turtle3prefix均NE/null，BASE/PERCENT完整before-after净差0；无旧市场/QA重放或曲线拼接。采用账户修正及对照能力，研究强基准HOLD，投资仍现金。ROOT与精选Git验收/同步另绑定真实后验，未自证caller完成。