# D043：213日同产品多空及公开策略对照

## 投资选择、实际贡献与下一步

投资候选仍NONE，资金选择现金，长期净几何APR不可评价。研究主力保留固定公开SMA50/200完整双向能力；Donchian为少量挑战者，不按各窗赢家拼收益。新增窗口中SMA多空版实际等于仅多版，空头信号及成交均为0，做空净增量为0；此前D040真实SELL开空/BUY回补、资金流水、反手/部分成交及NAV验收继续有效。本轮不能当成新增空头成交证据，也不能据零空头否定做空能力。

本版完成原547来源失败后的最短可靠闭环：新完整213日USD-M输入、同账户四方向及具体公开参照、原始成交/资金费/净值独立核对与保存摘要配对比较。采用研究能力与固定参照，暂停投资采用及参数搜索。当前最大的科研缺口是**是否优于受控市场暴露**；资金费单位、Bybit原生价格/历史风险规则及真正未来证据也未认证。

下一主任务：一个固定低换手、始终多头、过去30日协方差控制的**同产品波动管理持有**基准，沿用原账户/费用/资金费/风险，在213、122、90日各独立10k账户，对保存的SMA和Donchian摘要比较。不开新模型、不调阈值或按月份换赢家；优先排除“公开策略利润只是上行beta”这一重要假设。共同caps不等于相同实际风险，比较同时报告vol/MDD，不按事后实现波动放大收益。

## 固定窗口和资本口径

2024-01-01 UTC至2024-08-01 UTC前，共213日、每币306720分钟、7个月。边界在新合约PnL前按官方来源完整性决定；该历史已见开发筛选，非unseen/封存集/完整547日。原2024-08-12缺两分钟与547来源83/148失败完整保留，未删坏日拼NAV或填未知事件。

BTCUSDT、ETHUSDT共享完整初始10,000USDT；独立策略账户仅作配对对照，不构成一份资金可同时持有的组合。USDT线性永续、带符号base数量、单向逐仓1x、无自动补保证金；单币abs .3、组合gross .6，past30完成UTC日有符号cov/10%年波动目标、原.99 sizing。Spot库存保护、账户核心cf47与原执行时钟未改。mark仅估值，trade作为成交代理。

两固定成本BASE27/STRESS43：taker5.5bp/边，half-spread4/8bp、slippage4/8bp；资金费使用所有真实有符号事件，RAW_AS_FRACTION和RAW_AS_PERCENT是两个未认证单位条件，不能按利润选单位。Binance数据＋BybitVIP0费用为场所代理，**不是Bybit原生回测**；MMR .005、精度/min-notional及分钟风险范围均为明确假设，未认证原生清算安全。

## 实际经济结果

下表取预登记BASE27/RAW_AS_FRACTION条件，净收益分母为完整10k；MDD为全观察点，不混用较小日端点MDD。完整4成本/单位条件见[保存比较](../reports/fast_research/PERPETUAL_213_ECONOMIC_COMPARISON_20261003_V1.json)。

| 固定方向/策略 | gross USDT | fee | spread+slippage | funding | net USDT / 完整收益 | 年波动 | 全观察MDD | 换手/初始资本 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SMA LONG_ONLY | 1250.67 | 11.55 | 16.80 | −194.05 | +1028.28 / +10.28% | 11.20% | 7.75% | 2.10 |
| SMA SHORT_ONLY | 0 | 0 | 0 | 0 | 0 / 0% | 0% | 0% | 0 |
| SMA LONG_SHORT | 1250.67 | 11.55 | 16.80 | −194.05 | +1028.28 / +10.28% | 11.20% | 7.75% | 2.10 |
| CASH | 0 | 0 | 0 | 0 | 0 / 0% | 0% | 0% | 0 |
| 原公开2h Donchian LONG_ONLY | 1066.83 | 85.57 | 124.46 | −126.76 | +730.05 / +7.30% | 8.80% | 6.36% | 15.56 |

所有4条件：SMA LO/LS净+1011.35..1224.57、vol11.20..11.23%、MDD7.51..7.78%；Donchian净+604.29..856.57、vol8.80..8.85%、MDD6.00..6.69%；SO/CASH均0。增大预定执行成本不改变此窗排序，但资金费单位仍 明显改变金额，不能删去较不利条件。

BASE/F条件，SMA mean/max gross及net均 .20088/.37673，单币max BTC.18869/ETH.18851；Donchian mean/max gross及net .10976/.31746，max单币均低于.3。SMA mean/max逐仓collateral/NAV .18014/.36905，完整初始资本保证金占用mean/max .19534/.40814，最低现金7012.47；Donchian相应 .10584/.32373、.11210/.34245、7186.02。末端均有成本平仓，无残仓/欠款；此为分钟/成交/资金费观察风险，不声称瞬时caps或原生清算安全。

SMA多头净贡献+1028.28、空头0；Donchian多头+730.05、空头0。新增多空收益并未来自空头或降低净暴露。SMA收益较高同时实际vol、暴露和MDD更高，不能称风险匹配赢家；Donchian成本更大也不能将全部差距归因成本，gross本就不同。

| UTC月 | SMA LO/LS净USDT（BASE/F） | Donchian净USDT（BASE/F） |
|---|---:|---:|
| 2024-01 | +16.46 | −67.60 |
| 2024-02 | +1008.13 | +915.22 |
| 2024-03 | +224.61 | +24.58 |
| 2024-04 | −264.58 | −202.35 |
| 2024-05 | +412.07 | +136.52 |
| 2024-06 | −262.97 | −169.36 |
| 2024-07 | −105.45 | +93.03 |

两者各4/7正月，2月贡献全期净约98%/125%；这只是保存月度归因，账户全213日连续、未月重置。Apr/Jun扣费前也负，不能只靠减成本解决。SMA top5正日占总正日gain19.35%、最大绝对日占全绝对日变动3.17%；不将213日描述性年化数称稳定长期APR。

此前122/90日D040 SMA short条件净+83.89..91.67/+615.47..641.54，D041 Donchian均负。各独立账户和所有旧负结果保留；本轮揭示固定SMA跨状态方向暴露不同，并未证明能事前挑到各窗最好方向。两个教学公开策略不能代表整个开源市场水平。

## 来源、核算和真实任务

72官方档：51个D042已完整逐文件producer工件只读复用，另21个新档（ETH mark7、BTC/ETH funding14）；旧failed父仍失败。全72首次独立原CSV/CHECKSUM/CRC/Parquet、UTC月/跨月事件核对通过，funding共1278原事件（每币639），不假定固定8h或填零；每币214日daily预热/213评分日、372根December2h预热。来源完整性不认证资金费单位或发布/charge。

| 阶段 | 实际任务/退出 | 小型报告 |
|---|---|---|
| source72/新21 | 75a60d098c2b42b3835ea9a109ad65d7 / 0 | PERPETUAL_213_SOURCE_ACTUAL_20261003_V1.json |
| 首次独立72 QA | 6c1e949fda0d4edc8ccef61b9e358d20 / 0 | PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json |
| source根 | 见source根binding / 0 | PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json |
| 唯一新接线/未来扰动case | 5601512ea09d4915b855c0b89147dd07 / 0 | PERPETUAL_213_WIRING_SMOKE_20261003_V1.json |
| 主体20选择器 | 805bb12e2d24437fa27bda237e08f890 / 0，session21880/chunk28b895 | PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json |
| 独立金融V3 | 119339dad8b74157a7f0df18de72bef9 / 0，session31814/chunk6a774e | PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V3.json |
| 保存配对比较 | 00a866db6309442993d8e194cab8e522 / 0，chunke8e5e5 | PERPETUAL_213_ECONOMIC_COMPARISON_20261003_V1.json |
| 本版根接受 | 见[根实际binding](../reports/fast_research/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json) / 0，chunkeac9e4 | PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json |

20选择器实际为16交易账户＋1恒定CASH工件，独立金融实际17次全核＋3个现金工件/全部经济字段等价证明，不包装20次独立现金重放。原Decimal独立会计、原target references和容差cash1e−7/ratio1e−10保持；实际最大误差1.82e−11USDT/2.03e−14。真实资金归属、价格/capacity/费用/partial/目标/分钟NAV及日月MDD通过；独立没有重建全市场订单数量sizing或再跑future-poison payload，因果范围由精确目标/可用时钟与旧冻结fixture＋本次新日期扰动覆盖，不能扩大声明。旧金融账户/QA/无关测试未重放。

### 三个真实元数据失败与修复范围

1. freezerV1（86718b12…，ea29b3/1）仍指向历史registry当前路径，冻结字节不同；V2仅将旧SHA解析到原逐字节archive、沿用已有环境metadata，发生在新市场数组前。V1原源保留。
2. 独立金融V1（5b8fb00e…，24d1a1/1）进度unit重复；已读取输入/构建target，但0账户/0金融调用，**不是0 arrays**。
3. 独立V2（5432665f…，8e23ea/1）输出/STATE常量仍指V1，被独立路径守卫正确拒绝，尚无新RUN_BINDING/报告。V3仅修显示kw、新独立路径与登记ID，金融体/条件/容差不改；主体市场无需重放。V1报告和V2真实失败任务分别保持原字节，见[实际失败及扫描凭证](../reports/fast_research/PERPETUAL_213_METADATA_FAILURES_AND_SCAN_20261003_V1.json)。

## 资源、窗口、复现与暂停

source121.95s/RSS119,967,744B/new18,019,334B；独立source21.75s/RSS188,493,824B；主体518.66s/RSS503,869,440B/owned336,293,742B；独立金融33.42s/RSS459,382,784B。共享硬4,999,999,488B、swap0/GPU0、D40GB/32warn/36stop仍保持；collector540未更改。最新完成实际ROOT+整个D-hosted VHD扫描21,609,669,564B，于2026-10-03T06:53:37.111144Z/14:53:37+08结束，**随后市场工件不在此值**，已以原实际时刻发布8765，未假称新扫描。

所有长任务经with_task_progress/bounded；http://localhost:8765/ API健康。原命令以各actual.binding.exact_command、协议及RUN_BINDING归档为准。主体实际入口：

```bash
bash scripts/with_task_progress.sh --title 'D043 213天 · 四方向加公开策略真实经济对照' -- env PYTHONPATH=/mnt/d/codex/coin:/mnt/d/codex/coin/src POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/perpetual_213_research.py --protocol protocols/PERPETUAL_213_RESEARCH_20261003_V1.json --run-dir /home/xflops/coin-state/d043-perpetual-213-research-20261003-v1 --output reports/fast_research/PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json --experiment-id D043-PERPETUAL-213-RESEARCH-20261003-V1 --period 213D
```

已有专属目录/报告排他，不能原地重放；重复实验须新独立路径、协议及源绑定。采纳原开源SMA/Donchian与官方下载/原核算能力，无新依赖/模型/HPO/下单/keys/paid/locked；第三方版本/许可与本地用途见OPEN_SOURCE_REGISTRY。

暂停：完整547分钟（reopen真实合法缺记录或事前独立验证缺失风险方法）；SMA/Donchian投资采用与搜索（reopen同产品强基准的跨状态净增量、合理实际风险及未来证据）；D039归因草稿（只有具体决策需要时再开）；新模型（受控暴露基准仍不能解释、已有信息增益理由时再开）。不是永久删除空头或模型能力。

模块已研究验收；源码字节门槛、敏感/大小核对及正常GitHub同步另以实际凭证闭合，不提前声称推送。
