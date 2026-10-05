# D078：现货防御组合的真实收益、风险和成本

D078同Spot固定50/50 HOLD10+EXIT10/REENTRY20实际2共享10k钱包完成303已见日；缓存SHA复用不复制，正常recipe/Spot身份保留原mathID，无新模型/参数搜索。基础组合marked净630.73 vs HOLD8 633.09少2.37，gross增13.14而fee/exec多15.51；压力净609.23 vs618.40少9.18。实际日vol8.118% vs8.469%，分钟DD6.823% vs8.926%，turnover2.593 vs1.731，峰gross27.664%，全部close caps内；不是同风险alpha（原组件预算10% vs HOLD8 8%）。BTC净633.30/ETH净−2.57；101日差−4.01/+165.79/−164.14，不宣称时间稳定。独立核674成交/872640分钟/606日，606目标混合与过去cov/未来扰动通过；残仓0.000097/0.000804USDT保留，liquidated return NE。保留SpotHOLD8收益参照和Spot固定防御挑战者，投资NONE/CASH/APR NE。主79.38s/RSS756.94MB/采样共享1.253GB，新STATE26.90MB；整盘实扫28.568GB@2026-10-05T03:34:50.584997Z（新工件前）。旧protocol问题/parent文案误带D077，原件保存并在结果前补erratum，执行配方/预算未变。下一一项50USDT主动再平衡不交易区间完整新回放，保留信号退出/终止/风险强制减仓与caps；不能删旧成本保留旧毛收益，当前尚未启动。原N/signed/现金/源锁/资金/资源边界不变。

## 实际经济比较

同Spot价格/费率/库存账户/303日期/10k本金，只换为既有固定组合配方；组件各10%过去协方差先下缩再50/50组合，对照HOLD8为8%。这不是严格信号单因素或实际风险匹配。没有独立账户NAV平均、额外本金或后验倍乘。目标用自己的Spot过去日线，决策下一分钟open代理成交，资金费为0是自有现货无需借币的产品语义。

| 指标 | HOLD8 BASE | 固定组合 BASE | HOLD8 STRESS | 固定组合 STRESS |
|---|---:|---:|---:|---:|
| 期末marked净USDT | 633.094422 | 630.728149 | 618.402147 | 609.225754 |
| 成本加回gross诊断USDT | 664.250691 | 677.395373 | 663.328462 | 676.509136 |
| 费用USDT | 17.305844 | 25.921507 | 17.270520 | 25.865153 |
| 执行成本USDT | 13.850425 | 20.745717 | 27.655795 | 41.418229 |
| 实际日波动% | 8.469127 | 8.118275 | 8.462136 | 8.110882 |
| 日终MDD% | 8.158200 | 6.147015 | 8.185070 | 6.187058 |
| 分钟MDD% | 8.925862 | 6.822506 | 8.952561 | 6.862130 |
| 成交名义/完整本金 | 1.731251 | 2.593161 | 1.728382 | 2.588533 |
| 成交数 | 357.000000 | 337.000000 | 357.000000 | 337.000000 |
| 平均gross/net% | 14.648419 | 14.938183 | 14.634337 | 14.923753 |
| 峰gross/net% | 22.157504 | 27.663884 | 22.136502 | 27.637970 |

gross是同净收到库存轨迹在成交时加回费用/执行成本的诊断，不能称作独立无成本策略重跑。BUY费用扣base、SELL扣USDT一次，执行成本已含fill；共享NAV包括现金和真实库存。资产贡献是各资产现金流加终点库存价值之和，能桥到同一共享钱包，不能称为独立满资金账户组合。基础组合BTC净633.2964、ETH−2.5682；不因此事后删ETH。成交337少于HOLD357，但名义换手更大，不能用交易次数代替成本。

### 时间与原因诊断

三段真实连续101日相对HOLD8净变化−4.0145/+165.7861/−164.1379USDT，压力−7.4442/+164.1803/−165.9125；不重置资金、不拼赢家。基础月份差二月+122.54、六月−147.86，变化不是均匀优势。保存asset/month/cost桥全部通过；首入场和终止信号可以可靠识别，其余日调仓/组件信号/风险混合无法逐笔可靠拆解，明确UNKNOWN，不能把平仓整笔利润归给订单原因。

基础组合245/337成交名义小于50USDT、直接成本9.5335USDT，压力13.7501；这是描述分布，不是删除这些成本仍保留原毛收益的可执行结果。它支持下一项有限机制检验：固定50USDT主动再平衡区间，保留信号退出/终止与所有必要风险减仓，重新跑完整策略与账本。只有真实新净/risk/成本才能决定采用；不搜阈值、不提高caps。若不能安全区分主动再平衡和必要减仓，先做最小正常reason接口修复，而不盲删订单。

### 验收与限制

实际独立Decimal从674新成交重建cash/base/收到资产fee、872640分钟与606日NAV，全部close资产abs.3/gross.6内；不是新增连续minute漂移减仓实现或intraminute安全认证。独立目标复核手动50/50 target/raw差0，606过去centeredGram协方差误差<1.2e−16；未来OHLC×1.17扰动后早406目标不变、晚106实际改变。复用normal信号组件，不伪称独立重写vendor。正常account源码和成本不改，旧8项不重复全套，新入口由真实2账户+目标/金额/时钟独立证据覆盖。

两个末端残仓仍真实标价，现金清仓收益NOT_EVALUABLE；日历/marked NAV完成不能改叫现金已清仓。价格是Binance Spot，费用是用户Bybit VIP0当前场景10bp/侧，数量步长1e−8/minimum10仍研究假设，未取得Bybit历史原生过滤器/盘口/账户认证。已见历史不是unseen，长期APR/投资优势资格未建立。无下载/API/fit/HPO/locked body/keys/真钱/发单/GPU。

主79.377172s、RSS756944896B、共享采样1252630528B、新STATE26899470B；输入minute/daily缓存只读复用，独立额外小工件另计。整盘28567806550B实扫03:34:50.584997Z，早于新工件及采集增长，不称完成后精确总量。原5GB/swap0/GPU0/D40GB守卫仍启用，两原采集验收时实际存活；不把有限观察升级72h或未来有效日。

准备协议误带两旧文案字段question/parent，运行配方/控制/假设/预算正确。保留原protocol，结果出现前写独立metadata erratum；actual git_commit正确c789881，不用后验改写掩盖原错误。归档原准备脚本与审查。

### 采用与下一决策

固定组合两成本都净略低但波动/回撤较低，保留为开发防御挑战者；HOLD8仍收益参照，投资NONE/CASH。未知永续资金费输入从这项同Spot比较中移除后，防御效果仍存在，但时间反转和成本阻碍没有消失。暂停权重/退出网格和无新官方证据的资金费单位调查；reopen分别是具体可验证机制/新完整验证窗口，以及明确归档单位定义或合法官方同事件来源。保留十币/N资产与signed永续能力，不按当前BTC结果改资产池。

下一主任务是单一50USDT主动调仓区间的同配方完整重放；从真实小额成本与15.51USDT额外总成本出发检验，而非继续增加策略族。若净未改善或防御破坏则不采用，保留本版配方。尚未启动，无后台科研运行承诺。

### 复现

本模块Git代码、原协议加metadata说明，保持原受SHA缓存可用；用独占新STATE/output运行。旧D077及以前按对应原Git字节，不用本版替换原源哈希。

```bash
scripts/with_task_progress.sh --title '固定Spot防御组合' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_EXCLUSIVE_DIRECTORY --output reports/fast_research/NEW_EXCLUSIVE_RESULT.json
scripts/with_task_progress.sh --title '独立Spot金额核对' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/NEW_EXCLUSIVE_RESULT.json --output /home/xflops/coin-state/NEW_INDEPENDENT_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立目标核对' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_DEFENSIVE_BLEND_USED_METADATA_20261005_V1/d078_target_reference.py --input reports/fast_research/NEW_EXCLUSIVE_RESULT.json --output /home/xflops/coin-state/NEW_TARGET_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '现货经济诊断' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_saved_economic_diagnostics.py --input reports/fast_research/NEW_EXCLUSIVE_RESULT.json --output /home/xflops/coin-state/NEW_DIAG_DIRECTORY/RESULT.json
```
