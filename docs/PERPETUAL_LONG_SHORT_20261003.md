# D040：真实模拟多空链路与同产品四方向比较

## 当前六项结论

1. **长期APR候选：NONE。** 采用signed永续钱包、真实模拟开空/回补和共同比较能力；不采用投资配方。
2. **净APR证据：未建立。** 独立10,000 USDT账户的122日LONG_SHORT净−3.0249%，90日净+6.4154%（BASE27、raw-as-fraction条件口径）。两窗已见、不得拼成账户曲线或长期APR；其他成本/单位结果全部列出。
3. **最大阻碍：gross机制与原生资格。** 122日双向仍亏，90日只做空；资金费单位/发布时间、原生执行、历史MMR及filters均未认证。相同caps没有使实现风险相等。
4. **本轮发现：short有增量，但不是纯短腿因果消融。** 122日双向比LONG_ONLY改善29.0486 USDT，其中短腿+42.3239、长腿改变−13.2753。90日收益主要来自价格gross，LONG_ONLY全期无成交，双向与SHORT_ONLY相同。
5. **下一步：补强同产品公开基准。** 固定原公开2h Donchian LONG_ONLY，不镜像造short；先补July两档官方2h预热，闭合SMA200所需400小时缺口，再共用费用、容量、资本和风险流程。尚未运行，不扫模型/参数。
6. **暂停与reopen：** 固定SMA投资采用及HPO暂停；同产品强基准、真正未来、单位/原生成交证据闭合后重开。双向能力保留，不因本窗亏损删除；D039仅metadata失败后暂停，未产生经济归因。

## 固定范围与资格

BTCUSDT、ETHUSDT USD-M perpetual；122日为`2025-08-01..<2025-12-01`，90日为`2025-12-01..<2026-03-01`。每窗fresh独立10,000 USDT，收益分母为完整资本，未用保证金余额放大。原MIT公开SMA50/200日线hooks、200完成日预热、过去30日协方差、10%年度目标波动、每币绝对0.3/总gross0.6、1倍逐仓；实际波动与漂移另行报告。

数据是Binance trade kline成交价格/mark/funding代理；费用是**Bybit VIP0 USDT永续费用反事实**，每侧taker 5.5bp。BASE27每侧spread/slip各4bp；STRESS43各8bp。不是Bybit原生价格、BBO或账户回放。假设MMR0.005、lot/filters、分钟close可见时点不获原生认证；容量为过去已闭合分钟quote volume的0.001，下一分钟trade open+1us成交，最多5次尝试。配置cap不能保证无瞬时越界，分钟mark＋fill/funding风险检查不认证分钟内极端mark或真实清算安全。

`raw-as-fraction=1`与`raw-as-percent=0.01`是两个事前有限单位假设；实际单位仍UNCONFIRMED，不因结果选择单位，不将未知率补零。CASH零效应来自已知零仓。全部无fit/HPO/locked消费、账户密钥、真钱或GPU。

## 统一32情景经济表

净收益为完整10,000 USDT的百分比；CASH全为0。F/P分别是假定原率为fraction/percent，均未认证。†使用新的完整纠错账户；其他单元引用原完整账户。

| 窗口 | 往返成本bp | 假设 | LONG_ONLY净% | SHORT_ONLY净% | LONG_SHORT净% | CASH净% |
|---|---:|---|---:|---:|---:|---:|
| 122日 | 27 | F | −3.3154 | +0.9167 | −3.0249 | 0 |
| 122日 | 27 | P | −2.9795 | +0.8837 | −2.7012 | 0 |
| 122日 | 43 | F | −3.4200 | +0.8719 | −3.2067 | 0 |
| 122日 | 43 | P | −3.0844 | +0.8389 | −2.8836 | 0 |
| 90日 | 27 | F | 0 | +6.4154 | +6.4154 | 0 |
| 90日 | 27 | P | 0 | +6.2378† | +6.2378† | 0 |
| 90日 | 43 | F | 0 | +6.3322 | +6.3322 | 0 |
| 90日 | 43 | P | 0 | +6.1547 | +6.1547 | 0 |

这是**原30项完整＋两项新完整账户引用**的32情景证据，不是新跑32账户，也没有拼接前缀或NAV。原始32选择项对应24交易模拟＋2共享CASH工件，另做两项正确性复测。

以下仅展开BASE27/F的保存摘要，资金费收益仍为条件值。gross用相同真实模拟成交数量，不构造免费反事实数量；`net=gross+signed funding−fee−spread−slip`。

| 窗口／方向 | net USDT | gross | funding | fee | spread／slip各 | 换手 | 成交腿 | 实现年vol% | 分钟MDD% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 122／LONG_ONLY | −331.5353 | −278.3549 | −34.9582 | 7.4240 | 5.3991 | 1.3498 | 155 | 11.4436 | 9.1736 |
| 122／SHORT_ONLY | +91.6743 | +95.8863 | +3.3445 | 3.0785 | 2.2390 | 0.5597 | 13 | 3.3257 | 3.1656 |
| 122／LONG_SHORT | −302.4866 | −237.6082 | −33.6351 | 12.7288 | 9.2572 | 2.3143 | 178 | 11.4883 | 7.9918 |
| 90／LONG_ONLY | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 90／SHORT_ONLY | +641.5403 | +638.2907 | +16.6356 | 5.4534 | 3.9663 | 0.9915 | 131 | 12.1577 | 4.7009 |
| 90／LONG_SHORT | +641.5403 | +638.2907 | +16.6356 | 5.4534 | 3.9663 | 0.9915 | 131 | 12.1577 | 4.7009 |

成交腿来自`summary.trade_legs`及已审计`trades.parquet.rows`，包含开/平/部分成交，不称roundtrip或开空次数。SHORT_ONLY的13/131腿是真signed模拟交易。所有完整结果终端marked notional为0，经过有成本的容量受限退出，没有免费强平。90日P纠错gross636.9850、funding0.1662、fee5.4475、spread/slip各3.9620、net623.7797；价格收益没有依赖大额资金费解释。

## 实际风险、资金占用与集中度

BASE27/F，权重按各分钟NAV归一化；collateral与完整初始资本的分母不可混用。

| 窗口／方向 | gross平均／最大% | signed净暴露平均% | collateral/NAV平均／最大% | 最小free cash USDT |
|---|---:|---:|---:|---:|
| 122／LONG_ONLY | 19.8686／32.5804 | +19.8686 | 20.0418／33.2897 | 6835.46 |
| 122／SHORT_ONLY | 2.6471／25.1857 | −2.6471 | 2.7778／26.2917 | 7331.27 |
| 122／LONG_SHORT | 24.2918／59.5919 | +18.3197 | 24.5903／65.2296 | 3656.44 |
| 90／SHORT_ONLY或LONG_SHORT | 19.6381／35.1914 | −19.6381 | 20.8102／32.3285 | 6845.99 |

122双向signed净暴露范围−1.0475%..+32.5804%；collateral/初始10k平均24.6327%、最大62.7893%。其ETH权重最高30.0664%，发生4个减仓信号，记录首次减仓最长延迟60,000,001us；不能把0.3写成绝对无漂移护栏。90双向signed范围−35.1914%..0；collateral/初始10k平均21.0478%、最大31.3795%。同配置不是同实现vol/MDD/占用，更不是统一风险下的已胜者。

122 SHORT_ONLY全部净收益出自November，只有9个正收益日；top5正日占正日收益90.0170%。122双向为26.9789%，90双向为38.3832%；其最大绝对日占绝对日PnL分别4.4314%／6.9093%。无成交的90 LONG_ONLY不提供未来盈利资格或独立alpha证据。日指标只作描述，annual_return不是长期APR。

BASE27/F月度连续MTM（各窗独立、月间不reset）：

| UTC月 | LONG_ONLY net USDT | SHORT_ONLY net | LONG_SHORT net |
|---|---:|---:|---:|
| 2025-08 | +200.8023 | 0 | +200.8023 |
| 2025-09 | −73.9407 | 0 | −73.9407 |
| 2025-10 | −69.2833 | 0 | −69.2833 |
| 2025-11 | −389.1136 | +91.6743 | −360.0650 |
| 2025-12 | 0 | +27.8020 | +27.8020 |
| 2026-01 | 0 | +311.6872 | +311.6872 |
| 2026-02 | 0 | +302.0511 | +302.0511 |

122短腿与长腿共享NAV/covariance/容量，加入short也改变long数量/成本，因此双向增量不是把独立SHORT_ONLY净收益相加。90 LONG_SHORT与SHORT_ONLY全部相同来自没有long交易，不是两路分散alpha。

## 实际验收与失败保留

- [原固定合同](../protocols/PERPETUAL_DIRECTIONAL_20261003_V1.json) SHA `750fb5f1a17482fce44a5a77c24c6295e3b1bcdc9948ee2e176efe907e045280`；[原32实际](../reports/fast_research/PERPETUAL_DIRECTIONAL_ACTUAL_20261003_V1.json) SHA `c643c6ae5542dc049595a8c2e21b7281ef5ce46ac7f026a3c845126f05bfb445`，task `ffc696e06eb249d893552aad42e9a8d6`，session43673/chunk0838e4真实0。
- [原独立审计](../reports/fast_research/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT_20261003_V1.json) SHA `876fce2558757f797e1d0f9d5b923c5858427ecfd721926afe4926355ffef53d`，task `030a2b570edb40eb98a1b1ea56bdac70`真实0；保存原30完整/2错误前缀，不静默改成32完整。
- [纠错合同](../protocols/PERPETUAL_SETTLEMENT_REPLAY_20261003_V1.json) SHA `a771717fe44ba3c4030967ea885567b3c323ff25429cca6670f9f36cb57ac7bb`；[两新实际](../reports/fast_research/PERPETUAL_SETTLEMENT_REPLAY_ACTUAL_20261003_V1.json) SHA `4a9dbcef25381d4909d640ea582e69b58342f137f538dbd2840e49e0a2bf89ff`，task `cd8a4c50e2364fe0afc30c91bf6bb7de`真实0。
- [两新独立审计](../reports/fast_research/PERPETUAL_SETTLEMENT_TWO_CASE_INDEPENDENT_AUDIT_20261003_V1.json) SHA `0132514ae4cd8b9a1f65318ba4c7b06c47b1fb257fc5caa001a59f1f5445e3f1`，task `056ab9a8df674f93afe1cc6a61e3d5bf`、session13722/chunk675328真实0。逐项90日/129600分钟/3月/540事件、终端flat/债0。最大金额误差`3.64e−12`、比例`2.22e−15`，原容差1e−7/1e−10未放宽。
- [根最终验收](../reports/fast_research/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_20261003_V1.json) SHA `5b6fa633f14e976e75babb1405bedb97dfb91af9ed7cc25ae0363fa62ca5e89c`；[portable绑定](../reports/GITHUB_PERPETUAL_DIRECTIONAL_SOURCE_BINDING_20261003_V1.json) SHA `962647497be3c526b261e41c16b870a02d259875db61248b5c12d37b1d29f7cb`，task `1b11a04998844f838174bc73af22df73`、session78036/chunkec583c真实0。10角色、源码canon、JUnit与保存金融摘要闭合；只采用条件比较能力，非unit/native/投资资格。Git预检、提交、推送与远程一致由根另填真实凭证，此页不预声明成功。

原90 BASE27/P两项全平时`1.000E−37`残债被误标BANKRUPT，NAV>10k/freecash>9k，属于数值恒等错误，不是经济爆仓。[旧2bae账户原字节](archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py) SHA `2bae17b6351dec5c632e3af42fed2a6a5cf91293dba0a08c06a7aa81f4df58fb`保持；新账户SHA `cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261`只修两个settlement方法。旧原32/controller不改，唯一新增[恒等反例](../reports/fast_research/PERPETUAL_SETTLEMENT_TEST_ACTUAL_20261003_V1.json) SHA `dcd321c34958a36c9a14dfae5b6df043645bc0db7b527051e092aa2b45085715`，task `2330741be7774b6b82af475bfd3e823e`实际1case通过。独立比较停止前129成交腿、540资金费、129595分钟的政策/数量/价格/时序，以及180目标表；金额与ratio最大差0。新两完整账户各自从10k重放，不拼旧prefix。

首controller的字典语法collection失败为0科学case/0数组：[失败报告](../reports/fast_research/PERPETUAL_CONTROLLER_TEST_ACTUAL_20261003_V1.json)、[原71bc源码](archive/PERPETUAL_DIRECTIONAL_FAILED_COLLECTION_SOURCE_20261003_V1.py)保持；[controller V2](../reports/fast_research/PERPETUAL_CONTROLLER_TEST_ACTUAL_20261003_V2.json)唯一1case实际通过。旧source初始化失败保留，旧绿测/旧QA/其他30金融账户不重放。D039 [失败实际](../reports/fast_research/PUBLIC_EXPOSURE_ATTRIBUTION_ACTUAL_20261003_V1.json)停于0数组的18个UTC字符串差异；[已执行metadata诊断](archive/PUBLIC_EXPOSURE_ATTRIBUTION_METADATA_DIAGNOSTIC_20261003_V1.json) SHA `e08615351a10ad2b91f8dbb2b321f3c95c4d8885da4a980d7679f4eab4523fa1`，未认证新的经济归因。

## 复现入口与资源

以下来自实际RUN_BINDING的原命令，不是可以直接覆盖旧输出的重跑指令。复现须新的冻结协议/独占STATE/输出；原32的旧account要在隔离环境按2bae归档复现，不能覆盖当前已修复normal账户。

```text
/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /mnt/d/codex/coin/scripts/investment/perpetual_directional.py --protocol /mnt/d/codex/coin/protocols/PERPETUAL_DIRECTIONAL_20261003_V1.json --run-dir /home/xflops/coin-state/d040-perpetual-directional-20261003-v1 --output /mnt/d/codex/coin/reports/fast_research/PERPETUAL_DIRECTIONAL_ACTUAL_20261003_V1.json --experiment-id d040_perpetual_directional_20261003_v1 --period BOTH
/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /mnt/d/codex/coin/scripts/investment/perpetual_settlement_replay.py --protocol /mnt/d/codex/coin/protocols/PERPETUAL_SETTLEMENT_REPLAY_20261003_V1.json --run-dir /home/xflops/coin-state/d040-perpetual-settlement-replay-20261003-v1 --output /mnt/d/codex/coin/reports/fast_research/PERPETUAL_SETTLEMENT_REPLAY_ACTUAL_20261003_V1.json --experiment-id d040_perpetual_settlement_replay_20261003_v1
```

实际均在hpc_linux、clean CPU2环境，经`with_task_progress.sh`及bounded运行。主实际405.234s/RSS382,803,968B/owned238,580,600B；两项复测100.654s/RSS336,613,376B/owned23,929,053B；新独立10.151s/RSS267,264,000B。主预算400MB/RSS1.5GB/3600s；共享5GB/swap0/GPU0、D40GB保持。主任务原实际容量扫描21,017,503,043B，完成时刻`2026-10-03T02:55:53.206681+00:00`；后续工件不包含在旧扫描中，不将其冒称当前磁盘值。

最新完成扫描来自两项复测：21,256,028,075B，于2026-10-03 11:31:35.351906+08完成；随后23.93MB复测及后来元数据不在该测量内。已发布8765准确测量时刻，未新做全盘扫描。
