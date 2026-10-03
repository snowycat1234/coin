# D044：同产品受控持有与固定公开多空策略

## 当前选择、证据与发现

投资候选仍为 **NONE／现金，长期净几何APR不可评估**。研究主力保留原固定公开SMA50/200完整多空；新增一个始终多头、使用同过去30日协方差控制的强基准。接受本版比较能力，不因较好历史窗口改成投资采用，不事后选择LONG_ONLY／SHORT_ONLY或拼接窗口赢家。

本版问题是公开策略是否优于受控市场暴露。实际新跑12个独立账户，引用60条原先接受的公开策略／方向／现金摘要，形成72行与60个配对。三个窗口、两成本和两资金费单位条件均事前固定；没有重新回放旧账户或来源QA。

**核心发现**：213日SMA LO／LS与受控持有的净／毛／费用／资金费／换手／波动／回撤逐项相同，该窗口没有证明额外择时收益。122日LS较持有少亏38.98..49.18USDT，但本身仍亏270.12..320.67；90日LS相对持有改善1268.32..1302.98USDT，实际年波动约12.16%对12.17%，回撤明显降低。条件结果支持保留做空能力，尚不能认证跨状态长期alpha。

主要阻碍是独立跨状态证据，以及资金费单位、事件估值和原生Bybit执行／风险资格。现有收益均是已见开发筛选、Binance USD-M来源代理＋Bybit VIP0费用假设，不是Bybit原生回测。共同caps不等于相同实际风险；没有事后放大仓位来配波动。

## 完整日期、资本与经济比较

每个账户独立投入并预留完整10,000USDT，BTC／ETH共享钱包；单向逐仓1倍，无自动追加保证金。目标仓位单币绝对30%、组合gross60%，过去30完成日signed covariance／365和10%年波动目标。受控持有raw(.3,.3)，保留200完成且当时可用的日线warm guard；没有SMA alpha过滤、Spot EWMA移植或新模型。

|完整评分窗口（UTC，右端不含）|实际日数|HOLD净USDT，四条件范围|SMA LONG_SHORT净USDT，四条件范围|LS－HOLD净增量USDT|
|---|---:|---:|---:|---:|
|2024-01-01～2024-08-01|213|+1011.35～+1224.57|+1011.35～+1224.57|0|
|2025-08-01～2025-12-01|122|−361.25～−317.73|−320.67～−270.12|+38.98～+49.18|
|2025-12-01～2026-03-01|90|−668.46～−645.81|+615.47～+641.54|+1268.32～+1302.98|

范围是全部BASE27／STRESS43×RAW_AS_FRACTION／RAW_AS_PERCENT条件，不是置信区间或择优单位。原始资金费单位仍UNCONFIRMED；两scale未依据收益认证。窗口不是连续全资本曲线，不能将三条独立NAV拼成长APR。

下表为BASE27／fraction条件示例，收益以完整10,000USDT计算；全四条件见[保存比较](../reports/fast_research/PERPETUAL_HOLD_ECONOMIC_COMPARISON_20261003_V1.json)。

|日数|HOLD|SMA LONG_ONLY|SMA SHORT_ONLY|SMA LONG_SHORT|CASH|公开Donchian LONG_ONLY|
|---|---:|---:|---:|---:|---:|---:|
|213|+10.28%|+10.28%|0|+10.28%|0|+7.30%|
|122|−3.52%|−3.32%|+0.92%|−3.02%|0|−0.21%|
|90|−6.61%|0|+6.42%|+6.42%|0|−1.69%|

90日实际空头成交／资金／NAV已在D040接受，本版引用其接受摘要；新12账户是受控多头基准，没有冒称新跑空头。D040的90日LS131条成交腿、空头净贡献641.54USDT并非旧多头曲线取反。122日LS空头净贡献42.32、多头−344.81；LS－LO仅29.05，不能把SHORT_ONLY独立账户的91.67直接加到LONG_ONLY。

## 费用、风险、敞口和集中度

BASE27：taker5.5bp／side＋half-spread4bp＋slippage4bp／side；STRESS43：相同fee、spread／slippage各8bp。成交fill已含spread／slippage，账本未二次扣款。真实全部有符号资金费事件、过去mark估值、容量／精度／部分成交、风险减仓和付费终端平仓沿用原引擎。开空名义卖款不变成可投资现金；完整资本分母不改成保证金。

|BASE27／fraction|毛PnL USDT|交易费用＋spread／slippage USDT|资金费USDT|换手／初始资本|实际年波动|全部观察MDD|
|---|---:|---:|---:|---:|---:|---:|
|213 HOLD＝SMA LS|1250.67|28.35|−194.05|2.100|11.20%|7.75%|
|122 HOLD|−299.55|16.75|−35.36|1.241|11.49%|9.66%|
|122 SMA LS|−237.61|31.24|−33.64|2.314|11.49%|7.99%|
|90 HOLD|−631.84|12.51|−17.09|0.927|12.17%|11.09%|
|90 SMA LS|638.29|13.39|+16.64|0.992|12.16%|4.70%|

90日改善主要来自方向性价格损益及正负持仓，不是更换产品／费率或增加实际波动；funding只解释其中一部分。122日改善同时增加gross、保证金占用与换手，且依然亏损，不能称无代价优胜。213日收益相同反证该段择时alpha主张。四成本／单位条件的改善符号一致，仍未做独立风险匹配或高级统计资格。

|BASE27／fraction|平均／最大gross|平均net signed|平均／最大保证金÷NAV|平均／最大保证金÷初始资本|最小实际free cash USDT|
|---|---:|---:|---:|---:|---:|
|213 HOLD＝LS|20.09%／37.67%|+20.09%|18.01%／36.90%|19.53%／40.81%|7012.47|
|122 HOLD|20.30%／32.58%|+20.30%|20.69%／33.29%|20.83%／33.08%|6835.46|
|122 LS|24.29%／59.59%|+18.32%|24.59%／65.23%|24.63%／62.79%|3656.44|
|90 HOLD|19.66%／33.74%|+19.66%|20.96%／31.78%|20.68%／31.95%|6808.50|
|90 LS|19.64%／35.19%|−19.64%|20.81%／32.33%|21.05%／31.38%|6845.99|

caps是开／加仓后费用与绝对名义检验；行情跳动后的风险漂移如实保留并在下一可成交时刻减仓。旧122日LS单币最大ETH30.0664%，发生4次风险减仓信号，首次实际减仓最大延迟60.000001秒；不能声称全时刻绝不越30%或瞬时无成本减仓。新HOLD均无此类减仓信号。原逐仓MMR0.005／过滤器为假设，完整分钟和fill／funding观察不能证明分钟内极值或原生清算安全。

集中度：213日Feb贡献1008.13USDT，约98%全期净额；122日LS相对HOLD的全部BASE／fraction改善发生Nov，其余月相同；90日LS Jan＋Feb约占全期净额95.67%。不把单月赢家做成可实时选策略。全部12新账户完成完整日历、无halt、终端flat／债务0；若将来真实halt仍保留前缀而不补零。

## 实际验收与保留失败

|角色|真实task／退出|凭证|
|---|---|---|
|156已有来源元数据复用|4df24947…／0|PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json|
|唯一新增因果／共享风险接线case|21ebc65b…／0|PERPETUAL_HOLD_TARGET_SMOKE_20261003_V1.json|
|实际冻结协议私有编译|4b7e5a0c…／0|PERPETUAL_HOLD_CONTEXT_COMPILE_20261003_V1.json|
|12物理账户市场回放|6a41c703…／0；303.97s，RSS499,220,480B，owned225,727,721B|[主体](../reports/fast_research/PERPETUAL_HOLD_RESEARCH_ACTUAL_20261003_V1.json)|
|12账户独立金融V3|05c9786c…／0；24.60s，RSS452,460,544B|[独立](../reports/fast_research/PERPETUAL_CONSTANT_LONG_REFERENCE_INDEPENDENT_20261003_V3.json)|
|72摘要／60配对|65345f2c…／0；5.70s，RSS25,313,280B|[保存比较](../reports/fast_research/PERPETUAL_HOLD_ECONOMIC_COMPARISON_20261003_V1.json)|
|根接受V2|1ee73d1c…／0；SHAefc44e8a…|[根凭证](../reports/fast_research/PERPETUAL_HOLD_ROOT_ACCEPTANCE_20261003_V2.json)|

独立参考没有调用原账户／simulate／target函数；直接复用原Decimal参考会计和audit_case金融体，新增独立常量目标＋sample covariance参考。原cash1e−7／ratio1e−10容差，实际误差≤1.82e−11USDT／3.11e−14。市场全部订单数量sizing没有另外全量独立重建；范围由原冻结controller、精确目标可用时钟和唯一新扰动case支撑，不扩大为原生执行认证。

失败均保留，不覆盖：V1 freezer未引号窗口名被PowerShell当数字（host f9450e／1，无协议／STATE）；随后独立V1 task1beee6f5…／1在排他入口拒绝，无数组／RUN_BINDING／金融报告；独立V2 a5dab7ab…／1在额外index元数据role守卫拒绝，0金融数组／调用，保留9ba980…失败报告。V3仅允许原122／90已接受而不读取的index元数据，继续逐值核原完整window／156条输入，金融数学／容差／成本不变。根V1 ff0e4ec7…／1对旧已冻结D043普通文档路径过严；V2仅对精确SHA511d5ce8…的该文档允许核哈希，保留原守卫及失败报告。市场、旧账户、QA未重跑。

原547来源83／148、官方2024-08-12缺两分钟仍失败，不填价格／删坏日／伪造恢复；三完整独立窗口不能替代原完整547承诺。

## 资源、复用、复现与下一步

共享RAM硬4,999,999,488B／swap0／GPU0，D40GB／32GB预警／36GB停止新增保持。主体实扫ROOT＋完整D盘WSL VHD **21,953,852,770B**，结束于2026-10-03T07:49:30.744251Z（15:49:30＋08）；后来225.728MB研究工件不在此扫描数，8765发布原时刻，不声称新扫描。没有新依赖或框架，原SMA／Jesse／官方数据／NumPy／Polars／风险与账本均复用，版本许可见OPEN_SOURCE_REGISTRY。

主体可复现命令如下；专属原路径已存在，重放必须冻结新独立路径／版本，不能原地覆盖：

```bash
bash scripts/with_task_progress.sh --title 'D044受控持有 · 三窗口十二账户真实经济回放' -- env PYTHONPATH=/mnt/d/codex/coin:/mnt/d/codex/coin/src POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/perpetual_hold_research.py --protocol protocols/PERPETUAL_HOLD_RESEARCH_20261003_V1.json --run-dir /home/xflops/coin-state/d044-perpetual-hold-research-20261003-v1 --output reports/fast_research/PERPETUAL_HOLD_RESEARCH_ACTUAL_20261003_V1.json --experiment-id D044-HOLD-THREE-PERIOD-20261003-V1 --period BOTH
```

采用研究基准和真实配对能力；固定SMA保留为主力，HOLD为强基准，Donchian保留为少量挑战者，投资现金。官方文档静态核查已完成：历史REST说明fundingTime／fundingRate及charge关联markPrice，archive README未说明CSV calc_time／last_funding_rate倍率映射；CHECKSUM只证文件字节。项目已有FUNDING_SEMANTICS_PROBE_20261003_V2.json（SHA54febc06…，task94a04f7c…真exit1）：该同一官方历史REST请求451、零匹配／零重试，没有新合法访问条件，故不再次请求或改通道。单位桥暂停，reopen为官方archive明确字段说明或合法可得的原始历史响应；即使样本一致也不升级全部事件／发布时间／过去分钟mark为真实charge price。依据为[官方历史REST](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)、[官方资金费公式与结算说明](https://www.binance.com/en/support/faq/detail/360033525031)、[官方archive README](https://github.com/binance/binance-public-data)。当前FAQ不能追认历史归属。下一唯一主任务选事前固定2024-09-01..<2025-07-01（303日）独立完整USD-M窗口，先核源完整性，再同SMA多空／现金／HOLD强基准，检验转折状态下能否维持增量；它是独立开发筛选，不补缺August或拼547NAV，不新HPO。当前尚未运行303来源或账户。

暂停／reopen：SMA／Donchian投资与搜索，需强基准跨状态增量、风险与真正未来证据；完整547需真实合法缺记录或事前独立验证的缺失风险方法；新模型需基准不能解释且明确预期信息增益；未接入D039归因仅具体决策需要时开启。保留多空／空仓能力，不永久删方向。本模块研究验收已完成，正常源码／敏感／大小与Git同步以随后实际凭证闭合。
