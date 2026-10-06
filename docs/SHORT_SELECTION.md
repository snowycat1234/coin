# SHORT研究：经典基准与退出机制

D096：公开趋势内核复用后的最小适配；参数20/10与55/20沿用已冻结公开通道，没有训练或参数搜索。论文提供机制参考，不宣称完整复制论文策略。

## 实际改动与收益来源

每币独立判断：只有20日/55日两个虚拟趋势通道都处于空头状态才允许负目标；任何确认消失，取消新空头意图并按已有延迟/部分成交/持久reduce-only退出。正forecast保持原规则，资金竞争与signed covariance会使实际多头仓位和损益变化。不是把做多信号取反，也没有删除旧成本保留毛收益。

同一2024-09-01至2025-07-01、303日、10币、完整共享10k、abs30%/gross60%、逐仓1x、无自动加保证金；每日闭合信号、真实逐分钟账户。先两BASE情景均通过事前门槛，才按原政策补两STRESS情景。4个反事实账户分别用完整10k，不能相加钱包。

|成本|资金费解释|净USDT|原双周期净|LONG|SHORT|原SHORT|费+执行|vol%|分钟DD%|原DD%|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|BASE27|RAW_AS_FRACTION|1517.33|1011.00|920.36|596.97|-115.09|97.08|9.66|5.49|7.06|
|BASE27|RAW_AS_PERCENT|1578.24|1058.97|1005.66|572.59|-153.24|97.48|9.67|5.39|7.04|
|STRESS43|RAW_AS_FRACTION|1457.95|943.70|886.31|571.64|-147.62|154.20|9.66|5.54|7.22|
|STRESS43|RAW_AS_PERCENT|1518.30|990.40|971.34|546.95|-186.73|154.81|9.67|5.44|7.20|

BASE/PCT主要桥：价格毛损益1676.30；费用39.71；执行57.76；资金费-0.58；净1578.24。SHORT改善725.83，实际LONG减少206.55，组合净增519.27。新账户已实际付费平仓，残仓0；旧双周期含marked残仓186.86，按同一marked NAV比较，不能当作旧账户已清仓。

实际风险并非同caps即相等：新平均/峰值gross 15.31%/40.36%；平均net 4.76%；平均/峰值保证金占NAV 15.12%/39.19%；实际vol 9.67%；归一化换手7.22。新日收益正向前5日占比12.05%。不是事后风险缩放。

## 熊市问题仍未解决

旧账本实际40个连续空头episode按入场信号关联分组：FAST_ONLY34净-654.75、BOTH_SHORT5净369.85、SLOW_ONLY1净131.66；含残仓及实际费用，和原SHORT桥接。该关联用于提出新规则，不是删除交易后的可实现收益。新4账户全部独立完整重跑，独立Decimal资金/持仓/NAV核对及标的排序目标核对PASS。

既有过去BTC状态只是滞后描述，不是每币的真实熊牛周期；尤其BTC标BULL时部分币仍可下跌。不能从分组金额推断未来牛熊状态或机械BEAR gate。

|过去BTC状态|日数|原SHORT|新SHORT|新LONG|新组合净|
|---|---:|---:|---:|---:|---:|
|BULL|149|172.36|582.92|675.69|1258.61|
|BEAR|45|-522.10|-206.17|205.84|-0.33|
|SIDEWAYS|109|196.51|195.84|124.13|319.96|

BEAR分类的空头仍负，改善不等于已经实现熊市赚钱。只读逐币核对：8/10币SHORT增量正，未按事后收益换币。4月9日新SHORT -192.06 USDT，是BEAR分类最大亏损日；反弹退出时点需继续核对，当前不声称已能提前预测反弹。按原D093预定日历段的同钱包贡献如下（不是新风险匹配或独立账户）：

|日期|日数|LONG|SHORT|组合净|
|---|---:|---:|---:|---:|
|2024-09-01至2024-12-01|91|1472.51|-167.62|1304.89|
|2024-12-01至2025-03-01|90|-309.58|619.39|309.81|
|2025-03-01至2025-07-01|122|-157.27|120.82|-36.45|

## 采用范围、局限及下一步

RETAIN_DEVELOPMENT_SHORT_CHALLENGER_NOT_INVESTMENT。四情景事前门槛结果 True：净与SHORT贡献提高、成本/实际vol/DD不增、BEAR SHORT改善、BULL SHORT累计非负。该门槛只选择开发挑战者，不能证明长期收益或真钱资格。

保留DC_CONFIRMED_SHORT为已见开发主挑战者、原20/10仅多为稳定参照；投资NONE/CASH。下一有限工作先只读检查熊市分类下急反弹亏损的信号/订单时点，使用当时已知的单币价格而非BTC慢状态，识别每日确认退出是否过迟及可执行的有限改善空间；确认机制后才决定一个保护退出对照，不扫描倍数、不强制每段都做空。新的独立周期/原生规则仍是晋级证据缺口；不在当前303日继续优化入场阈值。

Binance USD-M交易/mark/funding配Bybit用户费用仍为跨场所代理；资金费原始单位UNKNOWN保留RAW_AS_FRACTION与RAW_AS_PERCENT，不选择更盈利的解释。MMR假设未原生认证；该已见窗口不包含完整独立2022熊市。特征/目标因果及minute reference不是原生成交证明；新SHORT已产生真实本地模拟开仓/加仓成交，独立资金流核对，不是发单。

## 复现与工件

全部Python通过hpc_linux的 `scripts/with_task_progress.sh` → `scripts/bounded.sh`，环境在D盘STATE，线程2。复现需新的独立run-dir/output，旧证据不覆盖。

```bash
scripts/with_task_progress.sh --title "SHORT确认复现" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_cta_leaderboard.py --protocol protocols/SHORT_CONFIRMATION_BASE27_20261006_V1.json --run-dir /home/xflops/coin-state/REPLACE_WITH_UNUSED_RUN_DIRECTORY --output reports/fast_research/REPLACE_WITH_UNUSED_REPORT.json
```

BASE与STRESS协议源哈希冻结；信号黄金与CASH/HOLD目标复用范围显式绑定，未重跑不受影响的钱包。4规则反例含下跌/反弹、未来扰动、顺序及独立目标；独立NAV最大误差约1.82e-12USDT，目标约5.56e-17。

`reports/SHORT_SELECTION_ACCEPTED_20261006_V1.json` SHA256 `500e81bd0cb24531601270bcafaee83e17b8ba0874f28de19d4cd3f2d34586fd`。
`reports/SHORT_CONFIRMATION_BASE27_REVIEW_20261006_V1.json` SHA256 `7139ca2d0b4fc82a000bf464ac4351d17921826f9cc997788edb4f8a21d41dd1`。
`reports/SHORT_CONFIRMATION_STRESS43_REVIEW_20261006_V1.json` SHA256 `f9fbb2e0054f250f2d792f64a88a9108dbb6044cceeae1434e3322875f5dc2a6`。
`reports/fast_research/SHORT_ENTRY_MECHANISM_20261006_V1.json` SHA256 `938362b3d9cfa897843ba0f1e12f1ce773eb2f18403ab09a0189d18a7bc577b9`。
`reports/SHORT_SELECTION_ATTRIBUTION_20261006_V1.json` SHA256 `0a6c011220e2a324439f40ecee41a3da44613c3a66e5573238132fcafd72efec`。

## D097：排除错误退出猜测，复用公开组件但暂不接账户

当前主候选仍为D096双通道SHORT确认，BASE/PCT净1578.24、SHORT572.59、分钟DD5.39%；本轮未改变账户、仓位、费用或已有收益证据。投资NONE/CASH、长期APR NOT_EVALUABLE。

只读重建五个最大BEAR分类空头亏损日共40个持仓资产日期：当日SHORT与保存的独立资金贡献桥接误差<1e-7。37/40全天都未越过既有prior10退出线；4月9日八币价格涨8.24%–16.31%，旧线全部未越过。独立复用原MIT Jesse Donchian核对全部40条线。故“原线从日检查改分钟就能救主要损失”的解释在这些反例上被否定；不宣称对所有日期无效。

直接安装并调用pandas-ta-classic0.8.32原生CE，无代码改动；MIT、22日/3ATR/rma/offset0/talibFalse、不补缺失。0.8.32 wheel SHA e8e1ede0c13d5927d28c91dce3d5ab2c71a1fb7f2e62fb61fe95178d4ab768e0；补充pandas2.3.3/dateutil2.9.0.post0/pytz2025.2/tzdata2025.2/six1.17只装STATE独立目录，冻结原环境不变。所有安装文件SHA见probe。未来价格扰动后截止前10币退出线完全相同；默认CE仅1/40触发，4月9日0/8。暂停把这套默认CE作为当前急反弹修复方案，不花预算做完整钱包；功能保留，reopen需不同已授权状态/窗口下有适用性机制，不能搜索倍数迎合这五天。

全303日保存账本另按真实fill_id区分初始逻辑订单及后续增仓，不把部分成交碎片当独立加仓；平仓与资金费按剩余数量比例分配。初开24逻辑订单38片段：毛521.27、费+执行25.09、funding+.20、净496.38；后续加空197订单207片段：毛91.77、费+执行15.64、funding+.08、净76.21。合计572.59，桥误差1.25e-12。分类只是会计归因，不证明删除加仓能增加收益；“加空整体有害”也不受当前证据支持。

这些五日是事后最差日诊断，不是新OOS、收益筛选或保护后的PnL。Chandelier无回放新钱包，净收益/回撤改善NOT_RUN；初开与加空是同一钱包贡献，不相加独立资金账户。两次技术失败（缺pandas、parquet不含order_id）任务日志保留，补齐依赖及使用真实JSON fill_id后完成，没有重跑旧账户。

复现：hpc_linux中经with_task_progress.sh/bounded.sh，以原v8-clean-env Python执行 short_rebound_timing.py、probe_chandelier_short.py、short_increase_attribution.py；输出要求未用路径/原证据不覆盖。补充组件由 environments/supplementary/pandas-ta-classic-0.8.32.txt 固定wheel校验，依赖安装版本如上，无源码修改。

工件：reports/SHORT_REBOUND_TIMING_20261006_V1.json、SHORT_CHANDELIER_PROBE_20261006_V1.json、SHORT_INCREASE_ATTRIBUTION_20261006_V1.json；源码、任务时刻与引用SHA、实扫和资源见 reports/SHORT_REBOUND_MODULE_CLOSED_20261006_V1.json。原账本以及独立finance证明按SHA复用，不复做旧验收。

下一有限主任务：在D096稳定SHORT确认上，只选择一个公开快慢周期冲突规则：单币已完成4h趋势转为上涨时把short降为现金，长周期仍共同看空才重新允许short；先固定公开周期与成本、核对可得性/清仓语义，再两个BASE完整账户，只有净/SHORT/实际风险门槛通过才补压力情景。避免只按BTC慢状态，也不因为五个最差日事后删交易。零模型搜索，不调ATR倍数；当前新规则及经济指标NOT_RUN。

### D097生命周期范围补核

五日原始CE线1/40只描述当日触线，不能作为完整CE策略淘汰证据。随后实际沿24次原空头持仓，用未改动CE22/3原生线、按空头保护线只下移的状态规则、第一完整入场后分钟观察，得到11/24次有更早触发；3月11日和19日BTC/ETH/SOL持仓已有前期触发可能。4月9日、11日、12日的原八币持仓在当日前仍没有CE触发，故4月9日主损失仍不能靠这套默认状态保护解释为“已经可避免”。这是原轨迹影子时点，不是CE账户或再入场模拟，净收益/风险改善仍NOT_RUN。

据此更正过宽表述：不淘汰完整Chandelier能力，暂列备用；当前主任务仍是单币快慢趋势冲突。完整CE经济对照reopen条件为需要评价3月前期保护的净/风险增量，或出现不同授权周期的机制证据；不得从五日触线或11次触发推算盈利。原点截面收尾及第一绑定保留，最终同模块V2补核含生命周期报告并明确该范围修正，没有覆盖旧经济证据。

最终收尾另保留一次重复事件ID被append-only注册器拒绝的技术失败，改用独立纠偏事件后继续；没有覆盖旧注册记录。完整生命周期和当下资源最终见 reports/SHORT_REBOUND_MODULE_CLOSED_20261006_V2.json，V1只保留原点截面范围。

## D098：固定4小时确认的完整经济对照

每币已有日线双通道short须同时获4h20/10确认；先mask再daily signed covariance，日内失去确认只退出、下一日再入场。未训练/搜参/下载新行情。此适配不等于原论文或完整Turtle。

|成本/资金费解释|原净USDT|4h净USDT|原SHORT|4hSHORT|原DD%|4hDD%|4hvol%|费用+执行|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|BASE27/RAW_AS_FRACTION|1517.33|932.60|596.97|203.20|5.49|7.29|9.10|146.85|
|BASE27/RAW_AS_PERCENT|1578.24|1004.43|572.59|191.81|5.39|7.13|9.11|147.60|

PAUSE_FAST4H_RECIPE_RETAIN_D096。BASE两单位通过才做STRESS；实际2账户，均独立完整10k共享10币，不能相加。
BASE/PCT净变动-573.81、SHORT变动-380.78、LONG变动-193.03、毛价格变动-523.54、费用+执行变动50.12；这些来自实际新账本，不删成本保留旧收益。
SHORT毛价格损益 613.04 → 272.67；SHORT费用+执行 40.74 → 80.99。实际空头episodes 24 → 64，归一换手 7.22 → 10.93。因此不只是成本吃掉同一毛收益；该完整适配改变了持仓路径、降低SHORT毛收益并增加成本。
原/新BEAR标签SHORT -206.17/-155.45；BULL 582.92/282.24；SIDEWAYS 195.84/65.02。只是既有滞后BTC描述，不是每币真实牛熊、不能证明未来熊市赚钱。
实际SHORT保护退出成交片段184；原正forecast保持，实际LONG可因covariance与资金竞争变化。关闭原长仓的反手清理单独记录 0，不把其收益冒充short贡献。
首20个4h完成bar不足时SHORT空仓，未给未知补值。两个BASE完整303日；真实fee/滑点/容量/风险/资金费保留，marked和付费清仓口径分别记录。
公开fast信号独立标量reference与真实小型延迟/部分成交/硬风险反例通过；实际账户沿用独立Decimal钱包/NAV、ordered signed covariance核对。首轮测试字段范围错误保留V1，未为其修改财务内核。

停止本303日的快线周期/阈值调整；将已固定最佳SHORT规则移至另一个完整下跌及随后反弹周期，优先补最小必要历史与透明基准；先核已授权/已有输入、当时可知标的资格与费用，保留两币对照。目的是检验跨周期有效性，不能按当前303日事后赢家声称独立收益。不改变资金/数据封存/风险权限。

结果 `reports/SHORT_FAST4H_ACCEPTED_20261006_V1.json` SHA256 `2d78b365b63dd4b80623b1516211d34a54ebcb1404128334d3e29dddcd51285f`。
复现：经现有progress/bounded、2线程、D-hosted runtime运行 `scripts/investment/run_cta_leaderboard.py --protocol protocols/SHORT_FAST4H_BASE27_20261006_V1.json --run-dir /home/xflops/coin-state/REPLACE_WITH_UNUSED --output reports/fast_research/REPLACE_WITH_UNUSED.json`。原run/output不可覆盖。

## D099：区分单币弱趋势与BTC慢标签

复用原303日D096账本和已绑定的SMA200信号，3030资产日期只读资金桥接误差2.39e-12 USDT，0新钱包/训练。BTC BULL标签/单币自身低于SMA200：SHORT净529.02；BTC BULL/自身高于SMA200：53.91；SIDEWAYS/自身低于SMA200：156.21；SIDEWAYS/自身高于SMA200：39.62；BTC BEAR/自身低于SMA200：-206.17。这些相加572.59，只是同钱包归因，不是各桶独立策略或删除交易后的收益。

因此不能把BULL标签下的SHORT盈利解释为一贯逆势空强币，也不能据BTC慢BEAR桶亏损推断所有持续下跌周期不能赚。暂停“BTC牛市禁止所有SHORT”的全局gate构想，保留每币双通道确认；reopen需完整真实钱包证明该全局限制有净/风险增量。单币低于SMA200也不证明次日继续下跌，标签仍是过去状态，当前急反弹损失保留。

新2022–2023来源核对中：BTC2022-07月mark缺Jul31整日，已用官方原生日档补齐；2022-10和2023-02的缺口也用有CHECKSUM日档补齐，所有原月/日重叠字段数值一致、derived文件明确非官方完整月ZIP。原档与失败结果不覆盖。ETH2022-07日档仍不完整，停止其全周期依赖，不插值/补0、不通过删日期凑完整年度。普通公开FAPI请求遇WSL网络不可达，没有改主机/IP或读取账户权限。

下一经济检验改用预定BTC透明参照的完整730日，按数据完整性缩小范围、未查看新净收益；资本10k/单币abs30%/gross60%/1x及真实费用不增。BTC证据不能代表10币组合；原10币303日对照继续保留。ETH路径reopen为合法官方完整mark或有明确适用定义的原生替代输入，不据当前账本输赢选择修复日期。
## D099：固定规则完整2022–2023周期，未通过SHORT跨周期门槛

BTC单币透明参照、完整730日连续独立10k账户；三个方向及实际CASH/HOLD各两资金费单位情景，共10个完整账户。中断保存3个完整账户后，仅补7个，未接续/拼接半个钱包。ETH官方分钟mark不完整，未删日期/补零；不替代10币独立证据。

|BASE/PCT条件解释|净USDT|价格毛损益|费+执行|资金费|实际vol%|分钟DD%|换手/本金|
|---|---:|---:|---:|---:|---:|---:|---:|
|LONG_ONLY|39.33|102.50|61.61|-1.56|5.83|8.47|4.56|
|SHORT_ONLY|-545.09|-491.44|53.81|0.16|5.03|12.77|3.99|
|LONG_SHORT|-507.95|-392.97|113.60|-1.38|7.70|14.74|8.41|
|CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|风险管理HOLD|541.50|601.17|57.25|-2.42|10.71|17.06|4.24|

同一LONG_SHORT钱包2022 SHORT 169.58、2023 SHORT -674.93；2023自身SMA200上方/下方SHORT -281.13/-393.80。这只是实际钱包逐日归因，不能直接删掉这些损失当作过滤策略收益。
两资金费解释均失败：LS净收益、DD与实际vol均差于自己同规则LONG_ONLY；2022空头为正却被2023损失抵消。主要是价格损益，不是只调低成本便能修复。HOLD风险更高，不能把同caps说成风险匹配。
保留D096在原303日10币窗口的开发结果；不晋级或宣传可跨周期赚钱，BTC730日当前SHORT配方暂停采用，能力与旧证据保留。reopen：同成本的预先固定经典/具体持仓机制改善，随后另周期验证；不在本轮扫阈值救结果。
目标单币abs30%/组合gross60%未提高；价格跳变导致实际短暂超出目标cap，完整峰值、硬风险减仓与延迟分别保留risk_drift，不能声称瞬时风险保证。MMR/数量规则与资金费单位未原生认证；Binance价格配Bybit用户费是跨场所代理；投资NONE/CASH、长期APR NOT_EVALUABLE。
最关键独立复核：每个实际钱包均通过现有Decimal资金/NAV参考、目标/标的顺序与有符号covariance核对；新来源逐CSV独立参考和CHECKSUM、日界/缺失反例通过。HOLD与同策略LONG_ONLY按策略身份分别配对，未混用。

复用现有SMA200_SIGNED经典规则，先在相同BTC730日/产品/费用/资本/风险下比较三个方向，复用本轮CASH/HOLD完整控制；0训练/参数搜索/新行情。检验慢趋势持仓是否捕捉了Donchian反复进出漏掉的2022下跌，不先增加新gate或继续调快线。

工件 `reports/SHORT_FIXED_CYCLE_REVIEW_20261006_V1.json` SHA `2964779be260bbf71987bafab110e1fcb500895a183af7efff9255532074bbfe`；实际账本路径与SHA在生产结果中。
复现：经 `scripts/with_task_progress.sh` → `scripts/bounded.sh`、D-hosted runtime、2线程，运行 `scripts/investment/run_cta_leaderboard.py --protocol protocols/SHORT_FIXED_CYCLE_2022_2023_BASE27_20261006_V2.json --run-dir /home/xflops/coin-state/REPLACE_WITH_UNUSED --output reports/fast_research/REPLACE_WITH_UNUSED.json`。复核已完成3个完整钱包只依指定原字节与参考，不改原工件。

## D100：经典SMA200 signed完整周期，SHORT有净增量

D100复用固定SMA200：6新730日BTC完整账户、4同窗完整控制复用；两资金费解释SHORT总贡献均正、多空均提高净收益。BASE/PCT LS净2413.34、SHORT718.25、vol10.68%、分钟DD9.54%；同规则LO净1563.48、vol6.68%、DD6.23%。原Donchian确认LS净-507.95、vol7.70%、DD14.74%。净收益改善并伴随更高实际风险，不能说风险匹配。RAW通过、PCT仅Sharpe比LO低（1.065<1.121）使事前门槛未全部通过，不事后改成功标准、不晋级投资。

|BASE/PCT条件解释|净USDT|LONG|SHORT|价格毛损益|费+执行|资金费|vol%|分钟DD%|Sharpe|换手/本金|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|LONG_ONLY|1563.48|1563.48|0.00|1611.41|46.09|-1.83|6.68|6.23|1.12|3.41|
|SHORT_ONLY|735.15|0.00|735.15|800.98|66.76|0.93|8.36|10.32|0.47|4.95|
|LONG_SHORT|2413.34|1695.09|718.25|2532.95|118.55|-1.07|10.68|9.54|1.07|8.78|
|CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|风险管理HOLD（复用）|541.50|541.50|0.00|601.17|57.25|-2.42|10.71|17.06|0.30|4.24|

同一LS钱包SHORT：2022 +1703.98，2023 -985.73。2023年1月 -636.53，8/9/10月 -349.20；1月约占全年SHORT损失64.6%。这是同一钱包逐日贡献，不把平仓利润归因给订单理由，也不是移除损失的过滤反事实。
经典慢趋势确实捕捉到本完整2022下跌的正空头贡献，不能从先前XGB/Donchian失败推断short没有alpha。两年正结果同样不是整个crypto、10币或未来的证据；已有10币SMA200停止前缀与负结果不删除。
控制按产品/全资本/日期/费用/源码/实际工件哈希绑定，且重算目标相等；不是独立满资金钱包相加。6新账户各自通过独立Decimal钱包/NAV与标量目标核对；新增2项元数据拒绝测试只证明复用身份，不冒充会计测试。汇总扩展对旧D099逐行结果与原门槛完全一致。
仅在已见开发窗口保留SMA200 family供研究；按事前两单位全通过规则，本轮未晋级。不声称多空降低相对SMA200仅多的DD/vol。费用为Binance价格配Bybit当前用户场景，funding单位/数量/MMR未知；实际瞬时cap漂移、真实减仓、保证金/敞口/集中度均在结构化结果中，投资NONE/CASH，长期APR NOT_EVALUABLE。

保留SMA200仅多为本BTC窗口研究参照、正贡献多空为有条件挑战者；下一有限实验仅改变SHORT：200日弱势仍需50日价格趋势确认，确认解除去CASH，LONG保持200日原规则。50是预先指定经典尺度，0拟合/网格/新数据；针对2023年1月快速反弹损失，完整重跑实际账本，不用删旧交易的假想收益。阶段门槛不改，失败保留负结果。

结果 `reports/SMA200_FIXED_CYCLE_REVIEW_20261006_V1.json` SHA `8cebd052853d5317caa7c2f0278f6595048d47638b9801015de68e3566ca4047`；损失诊断 `reports/SMA200_SHORT_LOSS_DIAGNOSIS_20261006_V1.json` SHA `4ef6ed2e5cddd6ec48fdc8033c884001d5013be525384058b0f472683cf38d50`。
复现：D-hosted runtime经现有progress/bounded，2线程，分别运行 `run_cta_leaderboard.py --protocol protocols/SMA200_FIXED_CYCLE_DIRECTIONS_20261006_V1.json`（4案例）和 `protocols/SMA200_FIXED_CYCLE_LONG_SHORT_20261006_V1.json`（2案例），显式提供未使用STATE `--run-dir`及未使用reports/fast_research `--output`。复核用 `review_short_cycle.py --producer <4案例报告> --producer <2案例报告> --strategy SMA200_SIGNED --output <未使用报告>`。原文件不得覆盖。

## D101：固定50日空头确认，少亏反弹却损失更多熊市收益

D101固定50日空头确认未通过两资金费情景门槛：BASE/PCT多空净1661.82（原2413.34），分钟DD9.25%（原9.54%）、vol9.64%、Sharpe0.846（原1.065/仅多1.121）。SHORT2022 292.02（原1703.98），2023 -214.61（原-985.73）；两年SHORT净77.42。

|BASE/PCT，同10k BTC730日|净USDT|LONG贡献|SHORT贡献|价格毛损益|费+执行|资金费|vol%|分钟DD%|Sharpe|换手/本金|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|SHORT_ONLY / SMA200_SHORT50|85.50|0.00|85.50|200.57|115.62|0.54|6.96|9.25|0.10|8.56|
|LONG_SHORT / SMA200_SHORT50|1661.82|1584.40|77.42|1827.05|163.91|-1.32|9.64|9.25|0.85|12.14|
|CASH / CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|LONG_ONLY / HOLD|541.50|541.50|0.00|601.17|57.25|-2.42|10.71|17.06|0.30|4.24|
|原SMA200仅多（完整复用）|1563.48|1563.48|0.00|1611.41|46.09|-1.83|6.68|6.23|1.12|3.41|

2023年1月SHORT从-636.53降至-61.62，但2022趋势收益损失更大。LS费+执行从118.55升至163.91，并非免费避开反弹。LS净减少751.52，其中SHORT贡献减少640.83、LONG因同钱包资本路径减少110.68；LONG信号和独立LONG_ONLY全部730日目标逐项一致，不把钱包路径差异说成多头规则变化。
4新完整真实成本账户（仅空/多空×2单位）+6历史完整控制；不相加钱包。原所有信号列完整golden相等，旧SMA200报告逐行与事前门槛相等；新入口每个账户独立Decimal资金/NAV与标量目标验收。两条件解释都降低净收益与Sharpe，暂停此实际配方，不永久否定快反应/SHORT能力。
仍是已看BTC730日开发、Binance USD-M行情配Bybit费用代理；单位/MMR/历史数量规则未知，锁定集未读，无真钱、发单、GPU或新数据。完整资本10k、abs30/gross60/1x保持，真实瞬时漂移与必要减仓不隐藏。
暂停SMA200_SHORT50硬过滤，保留原SMA200仅多参照与有条件多空挑战者。下一项只读检查已登记pandas-ta-classic CE22/3有状态空头保护在本BTC周期的触发和重入语义；只有明确提前保护反弹且未破坏主要熊市持仓的机制证据才接完整账户。固定公开默认，不扫ATR倍数/周期；影子触发不代表净收益。该不同授权周期检验满足D097 reopen条件。

工件 `reports/SMA200_SHORT50_REVIEW_20261006_V1.json`、`reports/SMA200_SHORT50_MECHANISM_20261006_V1.json`。复现：现有progress/bounded下分别运行 `run_cta_leaderboard.py --protocol protocols/SMA200_SHORT50_SHORT_ONLY_20261006_V1.json` 与 `protocols/SMA200_SHORT50_LONG_SHORT_20261006_V1.json`，显式给未使用STATE `--run-dir` 与未使用reports/fast_research `--output`。统一复核 `review_short_cycle.py --strategy SMA200_SHORT50 --producer <仅空报告> --producer <多空报告> --output <新文件>`。

## D102：CE22/3完整原持仓轨迹，不是新策略收益

D102公开CE22/3只读轨迹：原SMA200 BTC730日3段SHORT均有更早触发，其中2段下一日原趋势仍要求SHORT；不能把退出线直接挂入账户宣称净改善。第一段2022-01-01入空，2022-02-04已触发，原仓直到2023-01-14才平；第三段2023-08-31几乎开仓即触发，原负趋势仍在。

|原开空 UTC|首次CE触发 UTC|原平仓 UTC|下一日原信号仍SHORT|
|---|---|---|---|
|2022-01-01 00:01|2022-02-04 15:21|2023-01-14 00:01|True|
|2023-08-18 00:01|2023-08-29 14:21|2023-08-30 00:01|False|
|2023-08-31 00:01|2023-08-31 00:03|2023-10-17 00:01|True|

CE在本周期触发很早，首次触发不能直接推成2023反弹损失已避免；退出后价格与仓位路径、重入和成本均未模拟。2022第一段会在主要后续熊市前触发，2023第三段初始保护线已低于入场价格，简单接入更接近入场否决。这里只确认语义风险，不淘汰完整CE/ATR能力。
原24段D096持仓提取golden一致；当前全warmup/730日CE线通过独立标量Wilder22种子参考（最大相对误差4.05e-16）与未来价格扰动。已安装MIT pandas-ta-classic0.8.32文件哈希全绑定，不复制/改其代码。
0新账户/0训练/0下载；新CE净收益、交易费、DD、Sharpe均NOT_RUN，不删除原交易再扣成本做伪反事实。BTC来源/Bybit费代理及资金费/MMR假设不改变，已见开发不是unseen。
不接无重入规则的CE保护，也不靠优化ATR周期/倍数救配方。下一主任务复用已登记MIT Jesse SMA50/200完整多空入/退出hook，在相同BTC730日、资本、成本与风险下做固定公共family对照；优先直接复用现有public_sma_perpetual接口，先核完整策略语义/标的顺序，再跑有限方向账户。它是独立公开family，不把全部变化归因于SHORT退出；0训练/网格/新行情。原SMA200研究参照保持，投资NONE。

复现：现有progress/bounded、2线程，`trace_chandelier_short_episodes.py --producer reports/fast_research/SMA200_FIXED_CYCLE_LONG_SHORT_20261006_V1.json --protocol protocols/SMA200_CHANDELIER_TRACE_20261006_V2.json --output reports/REPLACE_WITH_UNUSED.json`。工件 `reports/SMA200_CHANDELIER_TRACE_20261006_V2.json` SHA `29d4e2ba6cdde149361487dfe6de8c1baa6645bea99f91b1af7d513559f7238d`。

## D103/D104：完整公开50/200与冻结expert机会诊断

D103公开完整SMA50/200多空：BASE/PCT净-1.62，毛价格93.96，费用+执行95.12，SHORT-360.32，vol10.70%、DD17.29%；RAW净-48.03。两情景不满足替换原SMA200的门槛；保留为冻结expert，不加exit/filter搜参。

10新完整730日账户（50/200三方向×2、DC20/10和双通道各×2）；4原Cash/Hold完整账户严格复用，不相加钱包。下表是实际完整账户，收益分母10k；与归一化oracle诊断分开。
|冻结expert / BASE-PCT|净USDT|LONG|SHORT|费+执行|vol%|分钟DD%|
|---|---:|---:|---:|---:|---:|---:|
|CASH|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|541.50|541.50|0.00|57.25|10.71|17.06|
|SMA200_SIGNED|2413.34|1695.09|718.25|118.55|10.68|9.54|
|DONCHIAN20_10|-432.46|275.61|-708.07|138.24|8.88|16.09|
|DC_TWO_SPEED|-529.63|-2.71|-526.92|121.57|8.38|17.65|
|DC_CONFIRMED_SHORT|-507.95|-2.60|-505.35|113.60|7.70|14.74|
|PUBLIC_SMA50_200|-1.62|358.70|-360.32|95.12|10.70|17.29|
|SMA200_SHORT50|1661.82|1584.40|77.42|163.91|9.64|9.25|

### 非可交易oracle诊断：只测机会，不计投资证据

|资金费条件|事后best single|oracle增量USDT|切换数|额外切换成本|shadow LONG|shadow SHORT|
|---|---|---:|---:|---:|---:|---:|
|RAW_AS_FRACTION|SMA200_SIGNED|3363.62|6.00|39.11|3766.89|1948.73|
|RAW_AS_PERCENT|SMA200_SIGNED|3414.99|7.00|39.11|3979.76|1887.68|

仅60日、13段（尾部10日保留），无horizon搜索。各expert完整账户日收益只归一化到一个10k诊断财富，未相加满资金钱包；已付内部费用保留，仅另扣13.5bp/side×边界目标距离。独立穷举验证DP与单资本归因、费用不二扣。包含日历年/过去趋势状态winner、LONG/SHORT贡献与选中expert的内部费用/执行/换手。
**它不是实际切换账户，也不是严格认证的全局可交易收益上界。** 边界实际持仓、拒单/最低金额/资本路径未重新模拟，真实oracle/静态ensemble/可行selector/placebo收益全部NOT_RUN。不可宣称regime alpha或稳定APR。

机会的结构：PCT路径只有SMA200/HOLD/CASH，2023年shadow SHORT为0；RAW另选1段公开50/200。DC20/10、DC_TWO_SPEED、D096、D101在本次oracle均未选中，不能推广为永久无用。PCT shadow2022净2000.65、2023净3827.68，LONG3979.76/SHORT1887.68/额外切换成本39.11；内部费用28.62、执行41.64已包含源收益，未二扣，总shadow换手/初始资本8.10。原有BEAR状态下也有未来赢家HOLD，因此不是简单已有regime标签已经有效；优先真实重放和简单方向配置，不从大上界直接上复杂八专家classifier。
冻结expert60日近似机会增量足够，先将同一oracle路径在既有共享资本账户真实重放，补equal/static合集真实成本对照；诊断不作为投资证据。随后只用过去slow×fast×vol少量状态、非重叠60日标签做排名可预测性与常数/错位/打乱/同频随机placebo，0交易模型拟合，不扫分类器。仅12个完整60日标签，尾部10日保留收益但不能充作60日训练标签；单BTC旧周期仅机制筛选，稳定性/独立证据不足，不晋级。

工件 `reports/PUBLIC_SMA50_200_REVIEW_20261006_V1.json`、`reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V2.json`。复现：progress/bounded下 `run_cta_leaderboard.py --protocol protocols/PUBLIC_SMA50_200_DIRECTIONS_20261006_V1.json`、`PUBLIC_SMA50_200_LONG_SHORT_20261006_V1.json`、`FROZEN_EXPERT_LIBRARY_COMPLETE_20261006_V1.json`，每次明确未使用STATE目录/reports输出。统一复核 `review_short_cycle.py --strategy PUBLIC_SMA50_200 --producer <directions> --producer <long-short> --output <新文件>`；oracle使用 `oracle_expert_opportunity.py --protocol protocols/FROZEN_EXPERT_ORACLE_20261006_V3.json --producer <D099完整10账户> --producer <D100多空> --producer <D103多空> --producer <D104expert补齐> --producer <D101多空> --output <新文件>`。

## D105：冻结expert真实共享账户重放

D105把冻结expert目标放入真实单10k钱包。两资金费条件oracle相对最佳单expert增量3335.69/3386.30，比shadow诊断低27.93/28.69，机会门槛保留，但oracle未来知情始终不算候选。八expert等权弱于原仅多；固定SMA200/HOLD/CASH=.5/.25/.25降低实际波动/回撤、提高Sharpe，但净收益低于原仅多，两条件均未达替换门槛。投资NONE/CASH，原SMA200仅多风险效率参照及多空正SHORT挑战者保留。

同BTC2022-01-01至2024-01-01、已见730日、每个反事实完整10k/caps30/60/1x。6新完整账户、4Cash/Hold完整复用；组合先合成有符号目标，再真实账户成交/资金费/钱包，不拼独立钱包收益。既有必要风险减仓与持仓清理保持。
|账户 / BASE-PCT|净USDT|LONG|SHORT|价格毛PnL|费+执行|资金费|vol%|分钟DD%|Sharpe|换手|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|ORACLE60D **未来知情，非候选**|5799.64|3936.43|1863.21|5910.20|109.07|-1.49|10.37|6.62|2.26|8.08|
|EQUAL_EXPERTS|425.14|432.03|-6.90|504.57|78.29|-1.15|5.41|6.80|0.41|5.80|
|STATIC_DIRECTION3|1377.58|1188.08|189.50|1427.88|49.14|-1.16|5.42|5.11|1.22|3.64|
|CASH|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|
|HOLD|541.50|541.50|0.00|601.17|57.25|-2.42|10.71|17.06|0.30|4.24|

Oracle PCT实际净5799.64，2022净1977.59（SHORT1863.21），2023净3822.05（SHORT0）。6/7次expert切换沿已冻结诊断路径，两情景分别真实重放，不重优化成全局最优；存在未来输入，不能列入可交易leaderboard。额外shadow切换扣费在真实账本不再扣，实际成交费和执行成本一次记账。
固定三expert PCT毛价格1427.88、费+执行49.14、资金费-1.16，主要赚钱来自LONG1188.08；SHORT2022 +413.32、2023 -223.81，合计+189.50。净1377.58比原LO1563.48少185.90，DD5.11%比6.23%低、vol5.42%比6.68%低；不是risk-matched超越，不事后加杠杆缩放。
等权8expert PCT净425.14、SHORT-6.90、Sharpe0.412；机械保留所有expert未形成净分散优势。它不否定其他窗口/币种条件优势，暂停该固定等权配方作为主力；reopen需真正互补收益来源/独立证据，而不是已见窗口删输家调权重。
独立标量逐730日重构六账户的原expert目标和组合权重/赢家边界；实际费用交易表逐项求和，最大目标误差2.78e-17；原有Decimal一分钟资金/NAV/多空归因继续通过。资源/时刻/源SHA见module close。所有新帐户实际平仓费用支付，未删除残仓。
真实oracle机会足够，但仍非因果/不能投资。下一有限主任务只用过去slow-trend×fast-trend×vol状态检验60日未来expert相对排名/赢家可预测性，先固定可解释状态映射，再chronological walk-forward与标签成熟，12个完整非重叠60日标签、尾部10日不充样本；固定/错位/打乱/同频随机placebo与oracle可行差距必须报告。0交易模型拟合、参数扫描或权重救配方。若不优于静态/placebo则暂停本selector配方，保留单策略与SHORT能力；reopen需新独立周期/合法多币机制。

BinanceUSD-M价格配Bybit用户费用仍为代理；资金费单位、历史数量与MMR假设未原生认证。已看开发不改名unseen；未启封locked。测试、oracle高Sharpe与两年外推均不证明长期APR或真钱资格。
结果 `reports/FROZEN_EXPERT_MIXTURE_REVIEW_20261006_V1.json`，独立核对 `reports/FROZEN_EXPERT_MIXTURE_INDEPENDENT_20261006_V1.json`。复现：progress/bounded下 `run_cta_leaderboard.py --protocol protocols/FROZEN_EXPERT_MIXTURE_ORACLE_20261006_V1.json` 或 `FROZEN_EXPERT_MIXTURE_STATIC_20261006_V1.json`，各给新的STATE `--run-dir`、新的reports/fast_research `--output`；`review_expert_mixture.py --producer <oracle生产报告> --producer <静态生产报告> --output <新文件>`。

## D106：固定状态的排名可预测性筛查

D106单一slow×fast×vol固定软映射未通过事前排名门槛：RAW/PCT平均加权排名0.67049/0.69400，静态三expert0.63839/0.66518，最佳单expert与只用成熟过去排名均0.64286/0.69643；虽胜同频随机和滞后60日特征，未超过打乱状态95%对照0.67637/0.70124，两年相对优势也不一致。仅8个评价标签，不声称regime alpha；暂停这个映射，保留SHORT与专家库。

12个完整不重叠60日标签；前4段成熟后评价8段（2022年3段、2023年5段）。所有输入由当时完成201日日线计算；慢/快为价格与200/50均线距离符号，vol30>vol200为固定高波动条件，ddof1。soft映射与每次L1≤.5的平滑在运行前固定，0交易模型拟合/网格/新账户。尾部10日不当60日标签，原730日实际账户经济结果未删日期。
|资金费条件|固定状态排名|固定三expert|最佳单expert/成熟过去排名|滞后状态|打乱95%|同频随机95%|到完美排名差距|
|---|---:|---:|---:|---:|---:|---:|---:|
|RAW_AS_FRACTION|0.67049|0.63839|0.64286|0.61344|0.67637|0.60059|0.32951|
|RAW_AS_PERCENT|0.69400|0.66518|0.69643|0.64290|0.70124|0.59622|0.30600|

得分是未来专家净NAV相对排名的权重平均（0–1），不是收益率/准确率/投资业绩；source labels来自已付费用/执行/资金费的完整独立expert账本，只是相对排名标签，不把它们加成组合收益。过去均值排名对照仅使用截至决策已成熟标签，16次统计更新完整记录；无随机CV。
32打乱状态、32同频随机权重路径各在两资金费解释下评分，固定seed、不选赢家；同频随机保留固定映射的实际12次权重变化时刻及L1大小（含初始从CASH变化），未来变化时序条件化，故明确是不可部署的诊断控制。打乱对照也不可部署，重复次数不增加市场历史。
2022年固定映射相对强参照有小优势，2023年落后；超过随机但不超过打乱，说明尚不能把少量收益排序改进归为有用的状态时序信息。未运行这个adaptive映射的真实账户，net/Sharpe/DD均NOT_RUN；D105的真实oracle与静态经济结果保留，不把排名失败改写为所有selector失败。
独立标量复核全部过去201日特征、12组relative标签、SciPy平均tie排名、8个成熟fold及权重路径；特征最大误差3.33e-16、权重/标签误差0。生产rankdata直接复用SciPy1.18.1 BSD-3-Clause；无本地修改。
不再在BTC同窗口改状态/阈值/权重，也不训练交易classifier。下一主任务先只读核现有授权历史manifest、完整专家账本及选择影响记录，明确可增加哪些合法完整周期或多币横截面标签；只在授权非locked范围补足有效样本，冻结专家原样做跨窗口条件优势迁移核对，已看历史仍标开发，不冒称unseen。当前映射reopen需多个周期的稳定相对排名信息或新增可解释past-only信息；仅8标签不足升级学习控制器。既有资金费单位/数量/MMR不确定继续限制投资结论。

结果 `reports/REGIME_RANKING_SCREEN_20261006_V1.json`，独立核对 `reports/REGIME_RANKING_SCREEN_INDEPENDENT_20261006_V1.json`。复现：progress/bounded下 `regime_ranking_screen.py --protocol protocols/REGIME_RANKING_SCREEN_20261006_V1.json --output <未使用reports文件>`；独立参考见archive/FROZEN_REGIME_RANKING_INDEPENDENT_SOURCE_20261006_V1.py（默认旧输出应改为新文件）。0新市场数据/模型/钱包，核心计算与真实任务时间分开记录；不是把核心0.65秒称整轮时间。
