# D041：同产品公开2小时策略与多空账户的真实比较

## 当前结论

投资/真钱候选仍为NONE，长期净几何APR不可评估。D040已补齐实际模拟开空、回补、反手、部分成交、资金费、保证金与NAV；本版将原公开2h Donchian接到同一个USDT线性永续账户，完成与SMA四方向的共同经济比较。采用比较能力，暂停固定Donchian的投资采用；SMA空头只保留为研究挑战者，现金仍是资金选择。

两个窗口各独立投入完整10,000 USDT，不拼NAV；以下范围覆盖全部两成本×两资金费单位条件，不挑胜出单位或成本。均为已见开发筛选，非unseen/原生Bybit/稳定APR；Binance成交/mark/资金费来源与Bybit VIP0费用反事实明确分开。

| 净损益USDT范围 | 122日：2025-08-01..<12-01 | 90日：2025-12-01..<2026-03-01 |
|---|---:|---:|
| 原SMA LONG_ONLY | −341.9975..−297.9481 | 0 |
| 原SMA SHORT_ONLY | +83.8944..+91.6743 | +615.4731..+641.5403 |
| 原SMA LONG_SHORT | −320.6681..−270.1232 | +615.4731..+641.5403 |
| 原SMA CASH | 0 | 0 |
| 新公开2h Donchian LONG_ONLY | −75.4066..−3.5811 | −212.8846..−159.7839 |

122日Donchian比SMA多头和多空亏得少，同时实际波动/回撤更小；90日SMA空头净收益更高，也承受更高实际波动/回撤。不同策略间不能把全部差额解释为做空贡献；隔离方向的证据仍是D040同一SMA信号四方向对照。公开Donchian原should_short=False，不镜像空头，不代表整个开源市场。

## 本版补齐的实际链路

复用原MIT Donchian strategy/indicator，prior20通道排除当前bar，SMA200含当前已完成2h bar；趋势过滤只用于入场，持有时仅lower-channel break退出。每窗fresh-flat，不继承预热持仓。过去30个完整UTC日协方差仍用真正日线，不换成30根2h。signal -> 正/零目标 -> 已验收signed钱包 -> 下一分钟+1us成交代理 -> 实际资金/费用 -> 完整本金NAV -> 共用日/月评价。

仅私有适配原547 controller四处：2h决定时钟、2h信号与daily-risk双输入、数量冻结分母为已闭合2h成交close、诊断order-kind名称。原金融、容量、mark、资金费、风险减仓、五次尝试和有成本终端规则不改。Spot库存保护与所有旧报告/失败保持。SMA结果直接复用原30完整+正确性修复新2完整的独立引用，不重跑旧32、不拼接错误前缀。

预热新增BTC/ETH官方July2025 USD-M2h两档各372行，CHECKSUM/CRC及raw12→normalized16全行独立核验通过。其余用已验收AugFeb分钟和原closed_hours+Polars first-open/sum-volume合成完整2h；90日包含AugNov过去预热，不借Spot/daily或删评分日期。每档严格120分钟、UTC闭合可得时间为明确代理。

## 新八账户经济结果

F=原CSV是fraction条件，P=原CSV是percent条件；单位仍UNCONFIRMED。费用5.5bp/side；base halfspread4+slip4/side、往返27bp；压力只翻倍spread/slip、往返43bp。price已含spread/slip，费用与执行成本各只记一次。

| 窗口/成本/单位 | gross价格PnL | fee | spread | slip | funding | net | 年度实现vol | 全观察MDD | 成交legs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 122/Base/F | 90.0335 | 37.9100 | 27.5709 | 27.5709 | −17.9223 | −20.9407 | 6.1102% | 4.6663% | 219 |
| 122/Base/P | 89.7529 | 37.9518 | 27.6014 | 27.6014 | −.1794 | −3.5811 | 6.1206% | 4.6382% | 220 |
| 122/Stress/F | 90.1208 | 37.7699 | 54.9382 | 54.9382 | −17.8811 | −75.4066 | 6.1534% | 4.8640% | 213 |
| 122/Stress/P | 89.8408 | 37.8116 | 54.9988 | 54.9988 | −.1790 | −58.1472 | 6.1635% | 4.8360% | 214 |
| 90/Base/F | −85.5216 | 30.1889 | 21.9555 | 21.9555 | −9.7973 | −169.4190 | 6.5306% | 3.6931% | 138 |
| 90/Base/P | −85.5509 | 30.2032 | 21.9659 | 21.9659 | −.0980 | −159.7839 | 6.5367% | 3.6866% | 138 |
| 90/Stress/F | −85.3950 | 30.1132 | 43.8009 | 43.8009 | −9.7744 | −212.8846 | 6.5919% | 3.7956% | 137 |
| 90/Stress/P | −85.4237 | 30.1273 | 43.8214 | 43.8214 | −.0978 | −203.2917 | 6.5976% | 3.7891% | 137 |

主要发现：122日gross为正但约93 USDT的base成交成本已经超过价格gross，资金费进一步拖累；90日gross本身为负，不能只靠费用解释或修复。两个窗口所有成本/单位条件净负；不降低成本、挑日期或改阈值包装盈利。

### 实际风险、资本与集中度（Base/F；其余全部见小报告）

| 指标 | 122日 | 90日 |
|---|---:|---:|
| 平均gross/NAV = 净有符号敞口 | 7.7421% | 7.7222% |
| 最大gross/NAV | 30.0714% | 32.9862% |
| 平均/最大逐仓抵押物÷完整10k | 7.6159% / 30.0413% | 7.5254% / 31.9022% |
| 平均/最大逐仓抵押物÷NAV | 7.5342% / 30.1078% | 7.5957% / 32.5064% |
| 最低分钟free钱包USDT | 7015.5800 | 6669.6140 |
| 绝对成交换手USDT / 完整资本倍数 | 68927.2611 / 6.8927 | 54888.9341 / 5.4889 |
| 正收益日数 / 总评价日数 | 20 / 122 | 16 / 90 |
| top5正日占全部正日收益 | 45.9288% | 71.9798% |
| 最大绝对单日占绝对日损益 | 6.6374% | 12.4460% |
| 月净损益USDT | Aug115.0612 / Sep−103.0246 / Oct100.3570 / Nov−133.3343 | Dec−227.9862 / Jan165.0315 / Feb−106.4644 |

全8账户flat/无未支付债务，但没有认证安全未清算。默认单向逐仓1x、绝对单币30%/共享gross60%、无自动补保证金、目标annualvol10%未提高。价格漂移/容量延迟可能短暂越目标；配置caps不等于连续hardcap或同实际风险。MMR=.005/数量精度与过滤器为既有假设，mark只为因果分钟闭合+成交/资金费观察，非原生历史tier/盘中mark极值；未知资金费未补零。收益分母始终完整10k而不是小保证金。

## 验收证据与可复现入口

- 源实际：bca7be97，task0fb929...，session50121/chunk747393，真实exit0；独立新源2754e68b，taskf6ad1d...，session96388/chunk548348，真实exit0。
- 两项新causal/时钟/价格分母case：90c45cd3，task474919...，session93489/chunk03d18e，真实exit0。只新增2case，旧绿色不重跑。
- 新8经济：bc89b62a，taskf07194...，session19436/chunk546e15，真实exit0；181.39s/RSS598.5MB/newSTATE70,982,924B。
- 独立：bf13af35，task5e9cf0...，session45167/chunka9646d，真实exit0；11.015s/RSS333.2MB。完整8×逐分钟、资金腿、日/月与独立2h目标；最大金额1.09e−11 USDT、比例3.51e−14。金融函数原1c4b原字节复用。全市场冻结order intent sizing没有独立重建，范围为pinned controller+新causal case，不扩大认证。
- 根：b50ba298，tasked85157...，session39950/chunk6c198b，真实exit0；5新closed0角色与原已验收6先决能力、8完整/原32保存比较、冻结字节/资源/资本/成本/单位范围闭合，不读/hash市场工件、不重复旧金融。独立audit registry为真实后登记，明确未冒充事前START；经济实验协议与START在读新数组前固定。

核心工件：[新8经济](../reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ACTUAL_20261003_V1.json)、[独立金融](../reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_INDEPENDENT_AUDIT_20261003_V1.json)、[根与公平小摘要比较](../reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ROOT_ACCEPTANCE_20261003_V1.json)、[冻结协议](../protocols/PERPETUAL_PUBLIC_BENCHMARK_20261003_V1.json)。大行情/真实账本仍STATE，不进Git。

实际已执行命令如下；冻结输出不能覆盖。要新复现实验须新的protocol/run/out，原参数/来源不变，并执行相同依赖核验。

```bash
bash scripts/with_task_progress.sh --title 'D041 公开2小时策略 · 八个永续经济账户' -- env PYTHONPATH=.:src POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/perpetual_public_benchmark.py --protocol /mnt/d/codex/coin/protocols/PERPETUAL_PUBLIC_BENCHMARK_20261003_V1.json --run-dir /home/xflops/coin-state/d041-public-perpetual-benchmark-20261003-v1 --output /mnt/d/codex/coin/reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ACTUAL_20261003_V1.json --experiment-id D041_PUBLIC_PERPETUAL_BENCHMARK_20261003_V1
```

ROOT+整个D盘WSL VHD真实扫描21,296,913,232B，于2026-10-03 12:40:08.465729+08结束；后来新账户输出不在此scan。源额外118KB、经济71MB、共享硬5GB/swap0/GPU0，原40GB/32预警/36停新增+1GB临时预算继续。8765健康并显示实际完成与扫描时刻；Codex打开操作为queued，不宣称用户已看到。

## 自主选择下一项

主要缺口是市场状态覆盖与独立投资证据：SMA短腿在两个相近已见窗口都正，122日收益却集中November，90日风险更高；不能据此事后采用固定SHORT_ONLY。下一唯一主任务是先核现有合法合约输入，补齐上涨/震荡的完整共同窗，再用固定SMA方向对照与公开参照检验空头增量是否跨状态存在。这比继续调Donchian或堆模型更能排除“最近跌市就是长期alpha”的错误假设。仍用完整资本/同成本/实际风险，旧Spot长窗只作产品参照，不偷换合约收益。

Donchian固定投资采用/HPO暂停，保留hooks/同产品adapter；reopen为事前固定的经济机制（信号/必要换手/风险）改进或新共同窗口提供净增量，随后独立未来验证。SMA投资采用/HPO暂停，保留多空挑战与现金，reopen为跨状态净增量、合理实际风险与真正未来证据。D039仅确需分币解释时重开；原资金费单位/Bybit native失败继续保留。下一实验未启动，不虚报后台任务；本版完成文档、blob检查、正常模块提交推送后继续。


### D041 GitHub模块闭合

正常提交session19416/chunke8dcf2/exit0，HEAD f1fafeaefac1703016a1d1876289b7865a93729b；推送session93769/chunk56ea3a/exit0；远程精确核验chunk48c712/exit0，local/remote同fullSHA。373既有/新冻结blob全部匹配、private_RUNTIME变更0、源字节index mismatch0、敏感匹配0；原2k源码仓库37355613B，无大行情/模型入库，无force/新auth/settings。reports/GITHUB_PERPETUAL_PUBLIC_BENCHMARK_SYNC_VERIFIED_20261003_V1.json SHAb26110e3575fb71e120944cebe19bf2fbd514234bbae446c4b7640f8cd19c5a9为实际push后的新小凭证，随下一正常模块入库，不为状态另造提交。新科研未启动，具体交接是核上涨/震荡合法USD-M金融输入再固定共同窗口方向检验。
