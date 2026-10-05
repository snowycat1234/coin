# D077：真实现货/永续产品对照与正常现货接口

D077正常Spot账户接入RECEIVED_ASSET及显式末5分钟有限退出，QUOTE默认原三夹具全字段实际差0、N=3共享钱包6实成交、最终8必要回归通过；旧AST入口不作为新活动依赖，旧报告按Git保留。36原源/244预热/303已见日、2真实Spot钱包与4保存永续完成产品比较，独立Decimal核714成交、872640分钟/606日现金库存NAV与gross/net，无实际close观测caps越界；仍非分钟强制减仓能力或intraminute风险认证。Spot基础marked净633.09，vs永续F541.09增92.00，vsP632.72仅增0.37；压力618.40，vsF增91.47/vsP减0.018，产品优势依赖未确认资金费单位，不能全归因资金费或认定稳健优胜。Spot实际vol8.469%、日DD8.158%/分钟DD8.926%，残仓0.00104/0.000464USDT真实保留，liquidated return NE，不免费清零。采用正常Spot/N/费用接口、保留SpotHOLD8产品参照，永续HOLD8/固定组合/十币能力保持；投资NONE/CASH、长期APR NE。主87.39s/RSS803.39MB/共享实采1.303GB、STATE59.15MB，实际整盘28.496GB@2026-10-05T03:10:44.713535+00:00（创建本轮工件前），5GB/swap0/GPU0/40GB与源锁资金边界不变。下一主任务复用现有固定50/50 HOLD10+EXIT10规则，在同Spot正常钱包/同输入/完整资本完成一项防御组合对照，隔离永续资金费单位不确定性之后检验防御收益/risk，不搜索权重或退出周期；尚未启动。

## 实际改变与经济解释

正常`src/quant/backtest.py`新增fee_settlement，默认QUOTE原算术/字段保持；RECEIVED_ASSET直接按收到的资产记费用。BUY只支出gross×fill USDT，收到gross×(1−fee)基础币；SELL库存减少gross，收到gross×fill×(1−fee) USDT。基础币费用按mid标价用于报告，不再另扣USDT；执行成本已在fill中，不重复扣。目标/现金/风险分母与周期成本一起修正，正tiny库存不自动清零。N资产固定两币禁止已去除，USDT产品身份/同一共享现金和caps仍保持。旧AST adapter不改但不用于本轮活动，旧原绑定必须按旧Git运行，不能拿旧绿测替代新入口。

新增terminal_exit_minutes默认1保持原默认；本轮事前固定5，与永续已有末5次容量尝试对齐。后续alpha不会在终止窗口重开仓，仍受原容量、min-notional/lot、时间和真实库存约束。现货两账户末各约1e−8 BTC/ETH，价值0.00104362/0.00046384USDT，不能执行满额清仓，marked收益与现金严格分开；liquidated return=NOT_EVALUABLE。独立银行式账本保留全部基础币、quote现金与未实现净值，不免费注销余额。

| 同完整10k/303开发日 | Spot BASE36 | Perp BASE27/F | Perp BASE27/P | Spot STRESS52 | Perp STRESS43/F | Perp STRESS43/P |
|---|---:|---:|---:|---:|---:|---:|
| 期末净USDT（Spot marked含真实残仓） | 633.09442182 | 541.09234383 | 632.72407445 | 618.40214703 | 526.92761022 | 618.42050814 |
| 实际日收益年波动 | 8.46913% | 8.39019% | 8.39378% | 8.46214% | 8.39142% | 8.39501% |
| 日终最大回撤 | 8.15820% | 8.30075% | 8.06818% | 8.18507% | 8.33596% | 8.10363% |

Spot BASE gross664.25、fee17.31、exec13.85、fund0→marked净633.09；vsPerp/F价格/实际仓位毛增7.76、fee多7.72、exec少0.095、fund少付91.87，桥合+92.00。vsPerp/P原资金费仅0.923，净差收窄至+0.370；压力下净差−0.018。不要选更盈利的单位解释，也不能删除旧资金费后保留旧价格PnL当作Spot。本轮价格、过去协方差目标、收到资产库存、现金/逐仓机制、目标数量冻结时点与mark均属于产品差异，不是资金费单因素或相同实际风险alpha估计。

Spot基础实际vol8.469%、分钟MDD8.926%，相对Perp/F8.394%/9.064%，不是收益/risk完全共同占优。两Spot共享全本金账户各357成交、turnover1.73125/1.72838倍本金，平均gross/net14.648/14.634%、峰gross/net22.158/22.137%、单币峰11.170/11.159%。Spot无保证金贷款/合约仓位，已付基础币库存占用约这些gross比例而不是虚构逐仓保证金。现货不借币不卖空；平台永续signed路径继续保留。

## 数据、因果与费用口径

仅复用原38份Spot源验收中的Jan2024..Jun2025共36文件，当前bytes/SHA精确匹配后读取；JanAug244个真实完整日作200日预热，SepJun303日评分。现货自身past30简单日收益协方差只下缩到8%，同一正常目标数学接口返回的USDM strategy_id仅表示复用来源，并不是Spot变成合约；本轮常多HOLD8/每日决策/下一分钟open代理成交，capacity使用先前完整minute quote_volume×.001。每日日期标签与真实day_end_us一并保存，按真实UTC次日00端点核606个日NAV，不从标签猜持仓归属。

行情来源分别是Binance Spot和USD-M，目标Bybit费用场景：用户快照Spot10bp/perp5.5bp每侧、无MNT；BASE摩擦4+4bp/side，合计36/27bp；STRESS8+8bp合计52/43bp。[Bybit官方说明](https://www.bybit.com/en/help-center/article/Bybit-Spot-Fees-Explained)支持按收到资产收费。本轮没有查询账户或修改快照，费率仍是当前用户场景用于历史代理，不证明历史账户/Bybit原生盘口、过滤器或成交；1e−8数量步长、10USDT开/平最低金额仍显式研究假设。永久holdout、keys/真实资金/orders/付费/GPU均未使用。

保存成交重建全分钟净值用于实际risk诊断，旧Spot账户无全分钟价格漂移强制减仓，不能冒称与永续完整risk实现相同；本轮两个轨迹在全部436320 close观测均未超abs.3/gross.6，若超限事前规则将其标为有限失败诊断，不删除日期/豁免上限。intraminute高低价、native risk/liquidation/BBO、精确历史publication仍未认证。

## 验收、资源与采用

三个子agent分别正常费用维护、独立参考、数据/时钟审查；根实际运行2钱包一次，独立真实2钱包一次。独立Decimal60从BUY/SELL gross与费用公式重建库存/cash/全部分钟与每日NAV，末NAV误差约1e−11USDT，无account/AST/主函数导入；市场mark值来源由主显式SHA源匹配与完整minute映射支持，独立复核不重做市场源QA。实际8必要fixtures通过，新增三币合成共享钱包6成交；精确import原4246975旧默认QUOTE三夹具，订单/成交/日NAV/cycle/原summary所有字段实际差0，容差1e−10。早先6项测试实际closed0元数据保存，其未保存旧6项测试源码哈希UNKNOWN，不拿它代替最终8项。

主87.386945s/RSS803393536B/共享采样1302818816B，STATE59152281B（约59.15MB），独立0.267388s；源schema/footer另一次小读，0新下载/API/模型/HPO/市场重复回放。整盘实扫28495712004B在03:10:44.713535Z，早于新工件与实时采集增长，不当作完成后精确总量；project+整个D VHD32warn/36stop/40hard与共享4999999488B/swap0/GPU0保持。8765仍显示实际任务进度，未新增观察器。

采用正常Spot接口和已有输入复用能力，新增SpotHOLD8产品收益参照，原PerpHOLD8/固定组合/十币挑战者保留；投资仍NONE/CASH、长期APR未建立。产品增益在小资金费假设和压力成本下近零，不能宣布Spot稳定优胜。下一唯一研究任务：已固定50/50 HOLD10+EXIT10规则在同Spot钱包上完整重放，与SpotHOLD8比较真实net/成本/风险及残仓；它去掉永续资金费单位这个输入不确定性，检验固定防御组合的实际价值，不搜索混合权重或退出参数。尚未启动，也不代表投资采用。

## 复现

本模块Git提交下使用原协议和新独占STATE/output即可；正常活动入口无旧日期AST依赖。旧D076及以前回放需按各原Git源码，历史证据不覆盖。

```bash
scripts/with_task_progress.sh --title '现货产品对照' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_PERPETUAL_PRODUCT_20261005_V1.json --run-dir /home/xflops/coin-state/OWN_NEW_DIRECTORY --output reports/fast_research/OWN_NEW_RESULT.json
scripts/with_task_progress.sh --title '独立现货金融复核' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/OWN_NEW_RESULT.json --output /home/xflops/coin-state/OWN_NEW_REVIEW/RESULT.json
```

真实task结束凭证、小源、独立报告与QUOTE/N参考随本模块保存；正常模块验收后才Git push，精确远端核验按后验凭证。原两路采集验收时实际存活，不将本轮有限观察认作72h或有效未来天。
