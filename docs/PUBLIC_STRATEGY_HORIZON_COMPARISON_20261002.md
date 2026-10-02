# 公开策略1h / 2h比较 · 2026-10-02

## 当前判断

固定2h成为下一阶段**研究主力**，不是真钱或合格Candidate。2025-08-01..<12-01连续122日、30/32/36bp下净收益均正；主要改善来自成本减少，成本前gross下降，分钟回撤反而增大。+1.9815%只是30bp期间收益的描述性几何年化，**长期净APR仍未证明**。

下一项按D014固定90日时间外推，检验成本优势与regime敏感性是否持续，优先于再试4h选赢家。无新HPO、降费、杠杆或新模型。

## 共同账户与三成本

2h只新增3账户，原Cash/BH/VM/1h的12账户直接按SHA复用，未重复回放。每账户10,000 USDT、连续122日、31日July预热、同分钟源/风险/执行。成本为单边费10bp、滑点4bp、全价差2/4/8bp。表为期间净收益%，不拼接旧7日独立账户。

| 策略 | 30bp | 32bp | 36bp |
| --- | ---: | ---: | ---: |
| Cash | 0 | 0 | 0 |
| Spot持有 | −5.6438 | −5.6480 | −5.6570 |
| VM持有 | −4.0601 | −4.0820 | −4.1267 |
| Donchian 1h | −0.2673 | −0.4142 | −0.7053 |
| Donchian 2h | +0.6580 | +0.5958 | +0.4692 |

30bp费用均为USDT；换手为全期未年化值，fills / RT为实际成交/已完成往返数。

| 周期 | gross | 费 | 价差 | 滑点 | 换手 | fills / RT | 盈亏平衡往返bp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1h | 193.55 | 146.85 | 14.69 | 58.74 | 14.5928 | 158 / 38 | 26.36 |
| 2h | 160.62 | 63.21 | 6.32 | 25.29 | 6.2421 | 69 / 17 | 50.82 |

总成本220.28→94.82（减约57%），gross保留约83%；净利润−26.73→+65.80。账本分解为成本减少125.46、gross减少32.94，净改善92.53。这不是纯成本因果实验：gross使用各自**costed实际成交数量**，不是共同数量或零成本重执行的反事实。

## 月度归因与风险

月末持仓连续标记，不重置/清仓；单元格为gross / 全成本 / net，USDT。

| 月份 | 1h | 2h |
| --- | ---: | ---: |
| Aug | 91.78 / 51.19 / 40.59 | 132.58 / 23.27 / 109.31 |
| Sep | 24.17 / 83.32 / −59.15 | −40.57 / 37.53 / −78.10 |
| Oct | 123.87 / 57.41 / 66.46 | 190.47 / 20.09 / 170.38 |
| Nov | −46.27 / 28.36 / −74.62 | −121.86 / 13.93 / −135.79 |

1h September是成本压制正gross，November则gross本已负；2h这两月gross/net都更差。收益强化来自Aug/Oct，Oct占正gross月总和59.0%（1h为51.7%）；两个周期均仅2/4月净正，不能称所有regime或信号都改善。2h September末仍有约2,999.49 USDT持仓，月分解已含标记价值。

| 30bp风险 | 1h | 2h |
| --- | ---: | ---: |
| 日收益年化实际波动% | 6.4952 | 6.2029 |
| 分钟MDD% | 3.6911 | 4.7087 |
| 峰值gross权重% | 32.0632 | 31.1750 |
| 峰值BTC / ETH权重% | 30.1671 / 19.6183 | 30.3472 / 19.3867 |

共用10%波动目标、30%单币/60%gross目标，不等于实际风险相同；压缩意图变动时再平衡，价格漂移可超单币目标。2h终端三档flat，约1e−12 USDT为浮点残余；末期退出仍计原延迟/容量/成本。较低波动没有消除更大回撤。

## 固定复用与边界

复用MIT Jesse示例策略pin `7c91e0a37bf62165790120d730442e4f6eb00364`、指标pin `417f8765225e3bfc12043d4b712f19fe15a3c078`；原代码/两MIT许可SHA匹配[归档说明](D:/codex/coin/third_party/jesse_example_donchian/UPSTREAM.md)。严格close>前20根通道且>SMA200入场、close<前20根下轨退出，仅多；SMA过滤只用于入场。COIN替代原全余额sizing及Jesse原引擎，不能援引公开回测收益。

2h保持20/200根参数，物理lookback变为40h/400h，是联合信号时间尺度诊断，不是仅延迟降频。沿原ExecutionContractV2、完整分钟后+1分钟+1微秒执行、前分钟quote-volume 0.1%容量；OHLC与容量是代理，非真实BBO/队列。已看历史SCREENING，无locked/真钱/拟合；独立核验接受代理账本正确性，不证明长期盈利。

## 下一固定90日与污染史

D014：2025-12-01..<2026-03-01，Cash/BH/VM/1h/2h×3成本=15账户；warmup **2025-10-31..<12-01**，November独自只有30日。明确Oct2025..Feb2026十个月档文件（五个月×两币），固定规则不根据新结果调参。源政策locked为2026-03-01..<09-01，此外推不启封locked。

该段不能叫项目级unseen：[旧A05折元数据](D:/codex/coin/reports/A05_RESEARCH_PREFLIGHT_ACCEPTANCE.json) fold7为Oct1..<Jan1、fold8为Jan1..<Mar1；[A06实际验收](D:/codex/coin/reports/A06_NONLINEAR_RESEARCH_ACCEPTANCE.json)有54正式fits，fold7/8实际test_rows为4416/2832，已覆盖Dec–Feb。诚实定位为本次规则的chronological out-of-window robustness，非新OOS资格。复用封存来源，成本低于扩数据/再选周期。

## 运行与验收证据

实际session96916 exit0，65.777s、主进程peakRSS649,715,712B、STATE29,454,343B；共享5GB、swap0、OOM0、GPU0。实际盘量19,379,178,257B，扫描结束2026-10-02 12:51:32.074285 UTC；共享历史RAM peak非独占峰值。

- [2h实际报告](D:/codex/coin/reports/fast_research/PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json)：SHA `2c3799fc82858a6bda6ac42767cd6d740a9d532553dfb5607a3043006d5bce57`。
- [退出/月度补充](D:/codex/coin/reports/fast_research/PUBLIC_DONCHIAN_2H_122D_ACTUAL_EXIT_MONTHS_20261002_V1.json)：真实exit0，月净/gross调和至全期。
- [独立实际核验](D:/codex/coin/reports/fast_research/PUBLIC_DONCHIAN_2H_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json)：`PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE`，审计实际exit0。
- [根模块验收](D:/codex/coin/reports/fast_research/PUBLIC_DONCHIAN_2H_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)：SHA `c9194642e8e90a18350625456b9d5aea87e4ea286fe2efc2b4584353bc5abf0d`；接受2h研究适配和代理共同比较，拒绝长期收益/真钱资格外推。

本文只读整理真实报告；未改源/配置/日期/协议/状态/registry/Git，未重算市场或启动新任务。

在本模块Git版本、原D盘已绑定来源与已接受环境内，可用新独立输出路径复现：

```bash
scripts/with_task_progress.sh --title '固定2h研究复现' -- \
  /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python \
  scripts/investment/compare_simple_strategies.py --research \
  --protocol protocols/PUBLIC_DONCHIAN_2H_122D_V1.json \
  --experiment-id PUBLIC-DONCHIAN-2H-REPRO-UNIQUE \
  --run-dir /home/xflops/coin-state/public-donchian-2h-repro-unique \
  --output reports/fast_research/PUBLIC_DONCHIAN_2H_REPRO_UNIQUE.json
```

实际运行命令、Python/lock、源码SHA、输入SHA与状态工件位于原report/RUN_BINDING；
原STATE账本和市场来源留D盘。以上为复现入口，未为本文再次运行。
