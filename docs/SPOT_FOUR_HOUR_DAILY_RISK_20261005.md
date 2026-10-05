# D080：4小时信号、日线风险与真实成本对照

D080正常N资产接口新增显式240min信号/独立200日资格与过去30日日风险，原1440默认与Git72e1a8b逐字段一致；HOLD10日target前向携带，EXIT10/R20原hook+COIN退出在4h上，整组合4h刷新，一个共享10k钱包。两成本303日真实回放：基础net642.13 vs日组合630.73多11.40，压力562.38 vs609.23少46.84；gross多141.34/139.68而费用执行多129.94/186.53，分钟DD7.997%/8.143%高于6.823%/6.862%，日vol7.849%/7.844%稍低。交易899/895 vs337，换手9.814/9.765 vs2.593/2.589；不采用4h当前配方，保留日线防御组合/HOLD8，投资NONE/CASH。约78%新总成本在信号component变化，重复intraday同target成本仅14.65/20.99（约8%），不是主要压力缺口；40完整component片段median96h/无<24h，不编造高频whipsaw，也不把片段当独立账户。3636目标scalar信号/centered日cov/手mix误差<6e-17；4008缓存4hOHLCV独立归约、1794成交Decimal/872640分钟/606日核账通过。旧测试7pass当时2581源码/当前ac19的两描述字段修订分别绑定，当前reference实跑通过，不冒用旧绿测。正残仓0.001065/0.000420USDT保留，liquidated return NE；缺组件资格不同整体STOP，未证明native/连续分钟风险/独立OOS/APR。主69.65s/RSS740.08MB/共享采样1.192GB，新owned27.43MB；整盘28.651GB@2026-10-05T04:26:47.474579Z（工件前）。本版不支持更快必然更好或重复调仓为主要失败机制。下一只一个COIN日SMA200宏观入场过滤对照，保留4h通道20/exit10/执行、过去日risk/成本/caps；比较本次4h控制，检验短趋势入场与费用失效，不改退出减仓、不搜周期网格；尚未实施/启动。暂停未过滤4h采用，reopen仅该明确macrofilter新证据或独立窗口，不永久删除方向。N/signed/十币/现货库存及40GB/5GB/swap0/GPU0/locked资金权限保持。

## 同产品真实经济结果

Binance Spot价格配用户Bybit VIP0费用是跨场所代理；303已见开发日/完整10k/abs30%与gross60%。不做原生/稳定APR声明。

| 指标 | 日线BASE | 4h BASE | 日线STRESS | 4h STRESS |
|---|---:|---:|---:|---:|
| marked净USDT | 630.728149 | 642.127556 | 609.225754 | 562.380961 |
| 成本加回gross诊断 | 677.395373 | 818.732724 | 676.509136 | 816.191826 |
| 费用USDT | 25.921507 | 98.096399 | 25.865153 | 97.571112 |
| 执行成本USDT | 20.745717 | 78.508769 | 41.418229 | 156.239753 |
| 日收益年化波动% | 8.118275 | 7.848688 | 8.110882 | 7.844475 |
| 日MDD% | 6.147015 | 7.364802 | 6.187058 | 7.535349 |
| 分钟MDD% | 6.822506 | 7.996713 | 6.862130 | 8.142597 |
| 成交数 | 337.000000 | 899.000000 | 337.000000 | 895.000000 |
| 换手/完整本金 | 2.593161 | 9.813534 | 2.588533 | 9.764862 |
| 平均gross/net% | 14.938183 | 13.762987 | 14.923753 | 13.750010 |
| 峰gross/net% | 27.663884 | 29.222133 | 27.637970 | 29.185491 |
| 峰单币% | 20.925345 | 20.896940 | 20.905711 | 20.876935 |

HOLD8额外参照净633.094422/618.402147；新4h分别多9.033134/少56.021186USDT。旧两币/十币/多空能力和负结果保留，不将本次long-flat配方推广为平台永久方向限制。

## 钱赚亏在哪里

SPOT_BASE36资产净贡献：BTCUSDT净613.617821/成本110.807653USDT；ETHUSDT净28.509736/成本65.797514USDT。

SPOT_STRESS52资产净贡献：BTCUSDT净562.475208/成本159.229194USDT；ETHUSDT净-0.094246/成本94.581671USDT。

SPOT_BASE36三连续101日真实NAV净增量：28.452523, -159.101323, 142.048208USDT。并非三份重置资金；排序反转不是稳定优势。

SPOT_STRESS52三连续101日真实NAV净增量：6.329642, -168.778605, 115.604171USDT。并非三份重置资金；排序反转不是稳定优势。

| 成本情景 | 实际目标意图 | 成交数 | 名义USDT | 费用+执行USDT |
|---|---|---:|---:|---:|
| SPOT_BASE36 | INITIAL_TARGET | 2 | 631.405872 | 1.135622 |
| SPOT_BASE36 | INTRADAY_IDENTICAL_COMPONENT_TARGET | 496 | 8141.671372 | 14.652447 |
| SPOT_BASE36 | DAILY_RISK_HOLD_REFRESH | 251 | 9826.558854 | 17.683497 |
| SPOT_BASE36 | SIGNAL_COMPONENT_CHANGE | 146 | 76790.089286 | 138.189727 |
| SPOT_BASE36 | TERMINAL_EXIT | 4 | 2745.619549 | 4.943874 |
| SPOT_STRESS52 | INITIAL_TARGET | 2 | 631.406078 | 1.639033 |
| SPOT_STRESS52 | INTRADAY_IDENTICAL_COMPONENT_TARGET | 492 | 8076.106578 | 20.993612 |
| SPOT_STRESS52 | DAILY_RISK_HOLD_REFRESH | 252 | 9798.944688 | 25.468305 |
| SPOT_STRESS52 | SIGNAL_COMPONENT_CHANGE | 145 | 76421.358223 | 198.628853 |
| SPOT_STRESS52 | TERMINAL_EXIT | 4 | 2720.801712 | 7.081061 |

信号变化时的全部组合成交是实际目标意图分组；不能把整笔平仓PnL归因某原因，也不能删除这些cost保留原gross。同目标重复成交不保证可免费删除：需要风险、真实库存和partial状态。其14.65/20.99成本即使全假想节省也不是主要压力缺口，故不直接重开重复调仓门槛网格。组件40闭合信号片段中BTC21/ETH19，median均96h、<24h均0、<48h分别2/4，BTC末片段右删失。不宣称快速whipsaw已经证明，也不视其为真实独立账户贡献。

## 活动接口与因果

正常public_sma_perpetual.fixed_targets新增signal_interval_minutes=1440默认、240显式与risk_bars。240要求200连续信号bar及独立200连续日bar：决策d风险结束日floor(d/DAY)*DAY，全部available<=d，最近31日close产生30日returns，centered sample covariance×365、原10%只下缩。缺口/迟到重置该信号并flat；blend两组件资格不一致直接STOP整比较，不声称一般缺失组合flatten已完成。N身份与协方差顺序一致，不重建平台。Donchian复用登记MIT原prior20通道/SMA200入场，COINprior10退出/R20再入场；本版周期200×4h约33日，HOLD日risk权重前向携带。目标刷新包含HOLD重复再平衡，因此变动是信号跨度+组合执行cadence，不是signal-only或相同实际风险alpha。

已接受36月Spot源SHA保持；仅多读既有July BTC/ETH两个暖期月，不新增下载或私有lock解析。July+August共3724h暖bar，原minute缓存继续执行/mark，原daily缓存日risk。归约逐block240分钟、first/last/available完整、OHLCV按首高低末和；warm/scoring不删日期、不补收益或资金费。换成4h完整bars建立决策资格而非日线bar冒充4h时钟。原received-asset fee/5minute退出/min10/quantity1e-8研究profile/容量/迟延/caps/完整资本不变，band0。

## 必要验收与局限

7fixtures通过/24.21s，覆盖N3/reverse顺序、200signal/200daily双暖、intraday日cov常量与独立Gram、未来未完成日价扰动、late日线flat、信号和日risk缺口/reset、独立dailyrisk必需。原fixture/prior运行绑定当时2581源码；后来只改240等待时钟的两描述字段，精确旧bytes/SHA保留并说明重建来源。当前ac19源码增强reference新实际运行5.441823s/RSS460.71MB，原日默认3allocation/各18target与Git72e1a8b所有旧meta逐字段一致，当前240描述字段通过；不重复整个旧测试集。

真实3636目标由独立scalar prior20/SMA200、持有prior10低退出/下一4h才再入场、每日centeredGram、manual .5日HOLD+.5四小时Donchian核对；max target误差2.78e-17、sigma5.55e-17/raw0。4008个缓存minute×240 reshape独立OHLCV块一致，volume累加顺序误差9.313e-10在事前rtol1e-12/atol1e-10内；July暖期仍依已接受原SHA/QA，不冒充fresh全源QA。独立Decimal60无producer账户import核1794成交/606日及872640分钟cash/basefee/USDTfee/exec/NAV；费用一次扣、点差已进fill不再次debit。全minute-close无caps违规，不认证盘中尖峰或连续漂移减仓实现。marked与cash清仓分别评价，正dust不归零，清仓收益NOT_EVALUABLE。诊断旧通用输出键HOLD8本次实际是spot_control日线组合，当前报告明确该映射，不冒充HOLD8重新回放。

主任务69.645563s（不含进程启动/import外层等待）、RSS740081664B、共享采样1192181760B、新owned27431466B；disk_before28650749911B在2026-10-05T04:26:47.474579Z，早于工件增长。不使用GPU/swap/keys/orders/paid/newAPI/locked；两采集关闭验收时动态实际进程确认，仅证明当时存活，不伪称72h前向资格。全部必要任务真实exit0。参考/诊断不是新市场样本。

## 采用与下一选择

事前双成本net改善且vol/分钟DD不恶化标准失败：基础略好但压力净差/两个DD均高，未过滤4h配方不采用。保留原Spot日线防御组合与HOLD8收益/风险参照，投资NONE/CASH/长期APR未建立；已看历史不改unseen，不搜索周期/权重/阈值，不按资产收益改池。旧D079及以前按原Git源码/协议/工件复现。

下一主任务由本次信号变化成本主导选择：只一个COIN宏观入场过滤假设，将4h Donchian入场SMA200从200个4h改为200个已完成日，保持4h通道20/退出10、4h执行、日risk/成本/10k/caps，完整新钱包对照当前未过滤4h。问题是较短趋势入场是否产生高成本且跨月份不稳的参与；这还未被证明。无需关闭任何必要退出/减仓，不声明过滤必赚钱，不做周期网格；两成本risk与net核后自行采用/暂停。尚未实现或启动，未声称后台任务。该有限单因素实验是4h方向reopen condition；无证据继续保留日线主力，不永久删除微观/ML/多空/十币能力。

## 可复现

使用本版Git、原受SHA绑定缓存和独占新STATE/output；不覆盖历史工件。

```bash
scripts/with_task_progress.sh --title '4h日风险完整回放' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_ACCOUNT_DIRECTORY --output reports/fast_research/NEW_RESULT.json
scripts/with_task_progress.sh --title '独立金额' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_FINANCE_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立4h信号与日风险' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_FOUR_HOUR_USED_METADATA_20261005_V1/d080_reference.py --input reports/fast_research/NEW_RESULT.json --output-dir /home/xflops/coin-state/NEW_TARGET_DIRECTORY
```
