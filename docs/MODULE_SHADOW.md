# 前向纸面账户：工程基础

2026-09-30。状态：**工程基础验收通过，17项故障/记账测试与静态检查通过**；不等同于P05真实72小时验收或P06真实180天验收。当前研究候选已停止，B2也没有通过收益资格；此模块只记录B0现金和B2趋势参考，不接入champion、不升级模型、不发真钱订单。

当前资源授权为D盘项目与WSL合计40GB、32GB预警、36GB停止新增、4GB缓冲；所有运行/训练合计RAM不超过5GB，禁用GPU。此前P03约6.215GB磁盘、20GB旧上限的验收属于2026-09-30较早阶段历史记录，保留原记录。SQLite默认位于D盘WSL虚拟磁盘内的原生 `STATE/shadow.sqlite3`，避免DrvFs锁问题。

## 接口与运行桥接

文件为 `src/quant/shadow.py`，故障演练为 `tests/test_shadow.py`。引擎只读collector数据库，不执行网络请求；由root运行器桥接正在接收的公开WS报价与collector健康状态。

```python
from quant.shadow import Quote, ShadowEngine

engine = ShadowEngine(
    collector_db=STATE / "live.sqlite3",
    db_path=STATE / "shadow.sqlite3",
    initial_disk=prechecked_disk_ledger,  # 全盘检查在WS循环以外执行，至少预留100MB
    initial_health=current_health,
)
quotes = [Quote(symbol, bid, ask, received_ms, update_id, source="websocket")]
report = engine.process_tick(now_ms, current_health, quotes)
engine.refresh_disk_budget(fresh_full_ledger)  # root约15分钟后台更新一次
engine.close()
```

时间全部使用毫秒，账本接收时刻转存为微秒。`Quote`字段为 `symbol,bid,ask,received_ms,update_id,source`。`quotes_from_buffers()`可适配collector当前内存quote_buffers；root已有实时报价回调时直接构造Quote。**不能从历史quote_minutes回放报价来补成交**：该表通常下一分钟才落盘，它可以提供覆盖率证据，但不替代当时实际收到的可用报价。

健康字典必须包含 `state="RUNNING"`、`healthy=True`、`qualified_72h=True`、`heartbeat_ms`、`clock_offset_ms`、`unresolved_gaps=0`、`disk.status="OK"/"WARNING"`。root负责确保资格缓存asof不早于45秒，并桥接真实运行状态和磁盘结果。引擎再验证两币报价不超过5秒、WS闭合bar不超过90秒、heartbeat不超过45秒、时钟偏差不超过5秒。live模式还比较自身墙钟和单调时钟的增量；跳时、回拨、断流、未解决缺口或磁盘异常均冻结新信号。后台必须捕获磁盘/SQLite异常并保留上游事故记录。

建议root每秒至多处理一次，闭合bar事件及时调用；fill时刻是实际处理tick时刻，不伪装为市场首个quote的时刻。记录quote接收时间和update_id，因此1秒采样带来的模拟延迟可审计。

## 冻结账户与下单规则

冻结版本由配置和本模块源码SHA-256共同生成；既有账本版本不匹配时拒绝继续写入。同一数据库只有一个Linux文件锁持有者。改变规则必须另立版本/账本，不能改写旧成绩。

| 项目 | 实现 |
|---|---|
| B0 | 初始10,000USDT，始终现金，独立日NAV。 |
| B2 | 完整1h、EMA20/EMA100；连续100根完整小时后才允许趋势多头；缺小时或非真实WS来源重置热身。 |
| 真实数据来源 | 只使用 `closed_bars.source="websocket"` 且真实接收时刻不晚于决策的闭合分钟。REST修复及REST先入库后仅附加WS标志均不当作实收价格。 |
| 决策 | 只对当前刚结束且收到完整两币数据的小时生成，15秒后不补发陈旧信号；启动前小时只用于已知热身，不制造历史决策/成交。 |
| 共同风险 | 无做空/借贷；单币最多30%、合计最多60%；过去30完整UTC日的因果组合协方差，至少20个有效日收益，预计年化波动目标10%。不足时 `RISK_WARMUP`、持现金。 |
| 下一分钟执行 | 决策生成后，下一分钟实际收到的新quote才可模拟成交；不得复用决策前报价、重复update_id或分钟末之后的历史报价。 |
| 成本 | 每边手续费10bp，实际半点差至少1bp，额外滑点4bp；实际点差扩大只提高成本。成交价格已含点差/滑点，不重复扣费。 |
| 容量 | 该报价收到前已实际闭合的上一1m金额×0.1%，同一分钟累计成交不能重复使用容量；REST容量不接受。 |
| 交易规格 | BTC数量步长0.00001、ETH0.0001；向下取整；最低10USDT。余数不虚构成交，不算闭合周期。当前规格近似不代表历史规则。 |
| 预算/现金 | 卖先买后，现金以及计费后单币/总仓限制逐单检查，其他币因费用降低NAV产生的占比也受约束。 |
| 未完成目标 | 最长5分钟；健康事故立即追加取消记录，恢复后等新小时决策；进程重启也取消未完成目标，保留已成交数量和现金。 |

`strategy_state`说明等待合格小时、小时不完整、风险热身或就绪；collector72小时未合格时持续记录冻结原因与现金日NAV，不冒充已经启动收益合格策略。报价深度和队列位置没有证明真实订单可按纸面价格成交，此模块是可追溯的模拟，不是交易所执行验收。

## 追加账本、恢复与证据读取

`records`统一记录 `seq,received_us,version,kind,payload,prev_hash,hash`，额外有唯一event_key用于幂等。规范JSON（键排序、紧凑分隔、不允许NaN）除hash自身外计算SHA-256，首prev_hash为64个0。SQLite触发器拒绝UPDATE/DELETE；决策、订单创建/状态变化、fill、position、日NAV、闭合周期、事故、heartbeat、checkpoint均追加写入。`decisions/orders/fills/positions/daily_nav`为对应只读查询view。

实际fill、现金/持仓变化和checkpoint在同一SQLite事务中提交；中途故障整体回滚，重复tick/quote不会重复成交。恢复先逐行校验整条hash链与不可改写触发器，再读取最新checkpoint及heartbeat；记录数量增加不要求把完整账本载入内存。重启期间不累计健康观测时间，未完成目标取消。heartbeat约15秒追加，checkpoint约每分钟及关键事件追加；单次健康观测增量超过30秒不记健康秒数。无需逐WS消息落盘，180天规模的账本保持有界增长，并受100MB写入预算及周期全盘更新约束。

```python
from quant.shadow import read_forward_evidence

# 恢复/日常审计：整链验证，O(1)记录内存。
audit = read_forward_evidence(STATE / "shadow.sqlite3", include_records=False)
# 独立离线报告才展开记录；必须预留报告内存，不能在WS事件循环中全量展开。
evidence = read_forward_evidence(STATE / "shadow.sqlite3", include_records=True)
```

可传version确认其存在/选择头信息，返回records仍为整条链，供独立再验证；不截断prev_hash链。头hash是本地审计证据，不等同外部签名或抵抗恶意重写文件的证明。测试使用 `engineering_simulation/source=synthetic` 的独立冻结版本，绝不算live时间。

## 日NAV与缺口

日结束后按截至该UTC日结束的已成交持仓和现金估值，随后收到的成交不会写进前一日。使用当时已经实际收到的日末闭合WS价格；缺失则保留最后已知价格并标记 `stale_exposure`。已封账NAV永久保留，后来修复或新行情不能改写旧值。持仓数量不丢，恢复日后按可得新价完整计入跨缺口损益；不能假装缺口中平仓。

首次不足整UTC日的NAV标记 `complete_utc_day=False`；日末超过120秒才记录的标记 `timely_recorded=False`、`MISSED_WHILE_STOPPED`。`daily_risk_observable`要求没有持仓旧价、及时记录且完整UTC日。缺口路径的真实回撤/波动未知，不能据旧价日NAV认证风险；完整日度记录也不涵盖日内极值。P06还须检查冻结版本、健康/时钟事故和真实时间，不能只读取这个布尔字段。

当前记录仅scenario B0/B2，start角色为cash/baseline，不存在candidate、fee_x2或slippage_x2真实前向账本。因此P06冠军资格应保持证据不足；不得拿历史压力回测或B2参考代替候选前向证据。

## 工程验收与日历门槛

故障演练覆盖当前小时闭合与下一分钟报价、实际点差增大计费、上一分钟累计容量、REST拒绝、风险历史不足、72h资格/断线/缺口/22秒偏时/磁盘故障、重复quote与重启幂等、单写者、配置冻结、不可改写触发器及整链校验、整日NAV不可改写与恢复损益、事故取消旧目标、事务中断回滚、重启取消部分成交余量。合成数据时间和行情保留synthetic标识。

命令由共享5GB、swap=0的 `coin-quant.slice` 限制；无需GPU：

```bash
source /mnt/d/codex/coin/scripts/env.sh
scripts/bounded.sh .venv/bin/python -m pytest tests/test_shadow.py -q
scripts/bounded.sh .venv/bin/python -m ruff check src/quant/shadow.py tests/test_shadow.py
```

最终17项测试在共享受限slice中全部通过，用时22.75秒，静态检查通过。源数据库与账户测试使用D盘WSL原生临时目录；合成记录不进入正式shadow数据库。root的一体主网短测另写入总进度记录。真实72小时与180天只能随实际时间累计；工程测试和接入成功不能替代这些门槛。
