# 共同策略收益比较 · 2026-10-02

后续连续122日已完成并推翻将1h策略晋级盈利主力的假设；本页为最初四段筛选的历史结果。
当前结论见 [连续122日比较](STRATEGY_CONTINUOUS_122D_20261002.md)，旧参数/输出/决策不追溯修改。

## 研究选择与证据范围

下一阶段研究主力选择 **Donchian 1h Spot 移植**：30bp平均7日净收益 +0.4734%，最差 −0.0305%；收益集中，无长期净APR证据。原预选primary仍是VM；Donchian属下一阶段选择，非追认primary或Candidate。

6策略×4独立7日账户×3成本，共72账本。A=2025-08-20..<27，B=09-25..<10-02，C=10-24..<31，D=11-18..<25（UTC）；初始10,000 USDT/账户、31日预热、同BTC/ETH分钟日历。窗口此前已看，属 **SCREENING，非unseen**；独立账户不能拼连续复利，7日年化不是长期APR。

## 30bp 名义往返成本

单边费10bp、滑点4bp、全价差2bp（每边一半），逐成交入账。收益/MDD/波动为%；MDD为最差分钟回撤，换手为7日账户平均（未年化）；费用三项为四账户总USDT；残余为终端平均标记金额/未平账户数。

| 策略 | 净均值 | 最差 | 分钟MDD | 换手 | 费 | 价差 | 滑点 | 实际波动范围¹ | 残余USDT/# |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cash | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| Spot持有 | 0.4212 | −0.6879 | 3.0502 | 0.4038 | 16.15 | 1.62 | 6.46 | 7.39–21.08 | 524.38/2 |
| VM持有 | 0.1875 | −0.6446 | 2.9804 | 0.4670 | 18.66 | 1.87 | 7.46 | 7.49–16.85 | 402.65/2 |
| 固定分钟趋势 | −2.9074 | −3.9177 | 4.6966 | 20.9204 | 824.44 | 82.44 | 329.77 | 7.06–14.69 | 433.53/2 |
| 固定分钟均值回归 | −9.1007 | −9.4942 | 9.5753 | 63.2811 | 2436.32 | 243.63 | 974.53 | 8.11–13.15 | 241.85/1 |
| Donchian移植 | 0.4734 | −0.0305 | 0.7418 | 0.5582 | 22.35 | 2.23 | 8.94 | 0.15–10.22 | 283.75/1 |

¹ 7个UTC日净值收益估算的年化波动，仅描述。共用10%波动目标、30%单币/60%gross目标上限，**实际风险不相同**；仅意图变动时再平衡，价格漂移可超目标。终端清仓受延迟/容量/最小量限制，残余按末价标记。

## 成本压力与失败机制

32/36bp 分别把全价差增至4/8bp，费和滑点保持原值。单元格为平均净7日收益（最差），单位%。

| 策略 | 32bp | 36bp |
| --- | ---: | ---: |
| Cash | 0（0） | 0（0） |
| Spot持有 | 0.4172（−0.6901） | 0.4089（−0.6953） |
| VM持有 | 0.1829（−0.6470） | 0.1734（−0.6529） |
| 固定分钟趋势 | −3.1106（−4.1134） | −3.5166（−4.5067） |
| 固定分钟均值回归 | −9.6796（−10.1751） | −10.8266（−11.5306） |
| Donchian移植 | 0.4677（−0.0377） | 0.4564（−0.0519） |

30bp趋势/均值回归四账户gross仅73.68/14.20 USDT，成本1236.65/3654.48，高换手吞掉边际。gross用**受成本影响的实际成交数量**，同数量gross−fee−spread−slippage=net；不是无成本重执行的反事实。

Donchian四折30bp净收益 −0.0305%、+1.5049%、+0.3986%、+0.0205%；B占合计净利润79.5%、正净利润约78.2%。各折最大正gross日占正gross日总和69.9%–100%。下一步使用现有完整Aug1..<Dec1连续122日，检验集中和四段账户重置影响；该连续范围仍SCREENING，不是unseen。

分钟趋势/均值回归仅暂停固定配方。重开须预登记低换手周期/因果过滤，或新信息支持更高成本前优势；不能降低成本、事后调阈值或改名unseen。VM、Cash、Spot持有保留参照。

## 复用、运行和限制

复用MIT Jesse示例 commit `7c91e0a37bf62165790120d730442e4f6eb00364` 的原hooks、前20根排除当前Donchian及SMA200过滤。COIN指定闭合1h、仅多、0/30%，原策略未定周期；共同风险/成本/执行替代原全余额sizing，未复现完整Jesse/Rust或公开收益。

复用原分钟ExecutionContractV2：完整分钟后+1分钟+1微秒执行，前完整分钟quote-volume的0.1%容量、最多等5分钟。OHLC/容量是代理，非真实BBO/队列；费率/lot为研究假设。carry、CURRENT_XGB、完整等风险ensemble缺合格输入，未评价。

真实session59353 exit0，63.039s、主进程peakRSS407,851,008B、新增STATE40,376,039B；5GB共享RAM、swap0、GPU0小时、无拟合/真钱/locked。实际盘量19,360,045,166B，扫描结束2026-10-02 11:45:06.442813 UTC；共享历史RAM peak不是本任务独占峰值。

## 凭证与验收

独立72账本现金/数量/费用/净值/时序/过去容量核验已通过，
[独立结果](../reports/fast_research/SIMPLE_STRATEGY_COMPARISON_INDEPENDENT_ACTUAL_AUDIT_20261002_V3_R4.json)。
checker此前Arrow chunk序列化、float比值精确比较及最后NumPy计数JSON导出失败均保留；
最后计算任务exit1仅发生在72结果完成后的导出，恢复为短bounded命令exit0，只重导出、不重算行情。
[根侧验收](../reports/fast_research/INVESTMENT_COMPARISON_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)
SHA `63aec2086f6f196a53b94553e04f844114a30ff961cf18830148f5ca0a2607d5`，
接受共同分钟proxy筛选经济账范围，不是长期APR或真钱资格。下述曾待验收的记录已由此凭证闭合。

结果来自 [ACTUAL V3](D:/codex/coin/reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_20261002_V3.json)（SHA `b9825db24c880064af68f3e9280f60d6593e3667742cf053fa8b7b2b13a0177d`）、[EXIT V3](D:/codex/coin/reports/fast_research/SIMPLE_STRATEGY_COMPARISON_ACTUAL_EXIT_20261002_V3.json)、[冻结协议V3](D:/codex/coin/protocols/SIMPLE_STRATEGY_COMPARISON_V3.json)。复用 runner SHA `ec42803504b83997f595b5fd2366b56295c5c9cf494c389ab6aed6177a4dd9cd`，精确绑定及工件SHA见EXIT。

[原9账本中断](D:/codex/coin/reports/fast_research/SIMPLE_STRATEGY_COMPARISON_PARTIAL_TERMINATED_20261002_V1.json)：117s目标生成瓶颈；[V2失败](D:/codex/coin/reports/fast_research/SIMPLE_STRATEGY_COMPARISON_TINY_20261002_V2.json)：NumPy整数索引错误；[V3修复/equivalence](D:/codex/coin/reports/fast_research/SIMPLE_STRATEGY_COMPARISON_TINY_20261002_V3.json)+EXIT：原9账本全部值一致、分钟源同字节，参数/成本/期间不改。仅只读整理，独立经济验收待根追加；无Candidate/长期APR资格。
