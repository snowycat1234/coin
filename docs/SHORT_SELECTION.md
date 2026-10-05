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
