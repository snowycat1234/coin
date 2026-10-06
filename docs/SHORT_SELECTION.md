# SHORT选择：双通道确认，单一配方

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
