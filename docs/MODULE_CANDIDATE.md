# G45：一次性留出、冻结候选与四路径前向接入

## v3 覆盖：容量修缮 WIP，执行扩展暂停

2026-10-01 按根目录审计指令 v3，G50 与新的执行功能暂停，优先 A01 执行一致性和 A02 强基线。
已有紧凑持久化修缮暂标 **WIP，未完成资源验收**：金融 checkpoint 保留金融/健康状态与
feature snapshot 锚；完整 trailing 特征只在决策 bar 边界保存，原始 feature minute 增量保留。
恢复从已认证锚后增量只重建特征，不重放财务或补健康时长。原始 quote 回调按每秒一次采样，
完整 closed bar 仍逐根处理；两币同毫秒收齐后的首个后续 quote 可额外触发一次决策检查。
新增 15m/1h 恢复、重复和 burst 采样检查通过，candidate 测试合计 15 项、80.13 秒。
**24h 账本实际字节和 180d 保守容量投影尚未完成，不能据此认证长期容量。**

曾拟增加每分钟账户下单尝试限制，已按 v3 指令撤回；填单机制保持父 Shadow 原有行为。
本次新实现 SHA 不得拼接旧 forward 版本。当前没有实际候选账本，也未触碰锁定历史测试。
后续资源 correctness 可在 A03 一并完成，但不能挤占 A01 的最高优先级。

## 当前状态与范围

`holdout.py`、`candidate_paper.py` 已实现未来候选的完整工程接入分支。当前正式 `logistic_v1` 研究仍为 STOP，没有合格冻结模型，没有真实 release，没有启动候选或揭晓最终留出。G45 不改 P04/P06 协议、结果或门槛，也不授权 Testnet 或真钱下单。实际仍须满足留出通过、开始前真实 72 小时采集、同版本真实至少 180 天竞争性记录和独立 Testnet 30 天等阶段。

资源：D 盘项目加 D 盘 WSL 总预算 40 GB；运行和训练共用 RAM 硬上限 5,000,000,000 字节，swap=0，不用 GPU。运行均经 `hpc_linux` 的 `scripts/bounded.sh`，SQLite 使用 native `STATE`；工程临时库与当前参考库、182 天历史回放分开。

## 一次性留出与 release 真源

`evaluate_holdout_once(development_report_path, model_path, protocol_path, grant=HoldoutGrant(...), state_db=None, engineering=False)` 的第一步只读开发结果并检查 `_development_gate`。STOP、没有唯一冻结模型、开发门槛未通过或已经揭晓时，在模型、协议、数据、SQLite 初始化前拒绝。已封存 v1 协议 SHA 对应 STOP 时，换一个自称通过的 summary 仍然拒绝。

通过者核对模型、协议、数据集摘要，训练和标签不跨留出、验证结束等于留出起点，并要求明确的 prior root/用户单次授权 `HoldoutGrant`。grant 记录 model/protocol/dataset、授权人、理由和 `one_frozen_candidate_once`；它记录既有授权，函数不能自行产生人类授权。

真实消费真源固定为 `STATE/holdout.sqlite3`。`attempts.dataset_id` 唯一，先在事务中消费票，再允许 loader 读取价格；并发第二消费被唯一约束拒绝。原始票和 receipts 表均有 UPDATE/DELETE 阻断触发器与 canonical SHA。评估失败或技术异常后不再次读取；异常记 `INVALID_RUN_CONSUMED`，进程在消费后崩溃也不能借重启重看留出。

默认评估器使用冻结 Logistic JSON 和现有 P03 回测。仅概率推断，不重新训练或调整阈值；候选/B2 同一首尾区间，共同起点和终点前一小时平仓目标，尾部停止新预测并保留 4 小时 horizon 与 embargo。比较基础、费用两倍、额外滑点两倍，沿用登记门槛并输出配对超额 CI。只有完整通过才 `PAPER_ELIGIBLE`，失败 STOP；此状态只表示允许申请真实 paper 前向。

`verify_paper_release(receipt, model)` 是后续准入真源接口。它只读固定消费库，核对原始 attempts ticket 与 receipt 的 model/protocol/dataset/development 摘要、原 grant、原始 `engineering=False`、唯一 dataset 票、receipt 正文和摘要、不可改写触发器，以及原始 `result.gates` 非空且全部通过。单独 JSON、随意 SHA、工程子库自称 PAPER 均不足以准入。当地账本可审计，不宣称具有外部不可篡改签名。

工程模式必须显式注入 synthetic 数据、评估器、校验器和独立 native 消费库，synthetic/engineering 数据集标识不得与真实集混用。即使合成门槛通过也只产 `ENGINEERING_ONLY`，永不授予 live release。真实模式不允许替代 evaluator 或 loader。

## 模型与因果特征

`CandidatePaperEngine(source_db, candidate_db, model=JSON, config=ShadowConfig(...), release=None)` 读取已冻结 Logistic JSON。合同包括 10 个固定特征、classes `[0,1]`、scaler mean/scale、系数/intercept、15m/1h interval 和阈值；工程模型必须明确 `provenance=engineering_simulation`。live 模式须经 release 真源且真实 72h 到达后才创建 start。

`ingest_bar` 只接受完整、原始收到的 closed websocket 1m bar，关闭时刻到收到时刻最多 15 秒；拒绝未来、未收盘、REST 回补、缺主动买入量、乱序和已入账数据改写。重复 delivery 不重复入账。形成完整 15m/1h 后，`update_features` 用持久化 EMA、末尾 close/volume 窗口计算与 `research.build_features` 同式的因果特征。缺分钟或决策 bar 时重置连续窗口，至少 100 根完整决策 bar 热身；不把回补变成当时可得信号。

每个特征保留关闭边界与实际收到时间，决策仅在该时刻所有币种资料都已收到且边界延迟不超过 15 秒时产生。模型、配置、source、release SHA、G45 和 collector/shadow/research/concurrent-budget 实现 SHA 都绑定同一新版本；运行中模型/参数变化或恢复时任何绑定不同均拒绝旧账本。

## 四个独立成本账户与单审计链

四条评价路径为 `candidate/B2/fee_x2/slippage_x2`，各自维护现金、现货数量、未完成目标、容量、已消费 quote ID 与闭合周期。压力路径使用相同候选原始预测和风险目标，各自按成本执行、正常 lot/min-notional/capacity 约束，不借用另一账户的现金或成交。它们是互斥假设路径，不代表实际同时四倍下单。父类保留的 B0 初始参考记录不参与四路径成绩。

复用现有 Shadow 的风险估计、卖出优先、单币 30%/总仓 60%、年化波动目标 10%、小额规则、报价时点和已收到的上一分钟容量。缺可得容量时等待，不按未来分钟成交量补估。单个 quote 在每个账户只消费一次；费用两倍和额外滑点两倍确实分别进入现金和成本账本，不填写为 0。

同一 SQLite `records` 链写 start、feature minute、feature、decision、order、fill、position、round_trip、heartbeat、UTC 日 NAV 与 checkpoint。四条日 NAV 使用同一日期区间和同一版本，并写 `complete_utc_day/timely_recorded/stale_exposure/daily_risk_observable/source`。缺持仓估值或停机后重构不认证风险；首个部分 UTC 日不算完整日。`read_forward_evidence` 和 P06 可直接读取整个链。

恢复验证整链与配置，不重复 candidate start，不重放历史填单，不把停机间隔补成 healthy。Engineering 即使模拟多年，其 `actual_qualification_days=0`；P06仍为资料不足或明确事故失败。工程 seed、模拟报价与模型始终合成来源，不能用历史 replay 凑真实 180 天。

## 独立采集桥接与可调用入口

`CandidateCollector` 继承新并发预算采集类，覆盖 `_notify`，从原始 kline 保留 `V/Q` 与 raw payload 后传入 `CandidatePaperEngine.ingest_tick`。缺 `V/Q` 时记录并永久冻结候选特征合同，不补默认值。原 collector/runtime 文件保持冻结。

`create_candidate_pipeline(...)` 先检查真实开发 STOP，再读模型/release，在全部准入检查后返回一个**尚未运行**的 CandidateCollector。`.stage` 初始 `WAITING_FOR_REAL_72H`，`.candidate=None`。未来显式运行时，只有同一源库产生的 qualification snapshot ≤45秒、有效 disk snapshot ≤45秒、两个币种原始 websocket/fresh 报价均 ≤config 的 5 秒上限、healthy/connected/live_session 全部满足，才延迟创建 candidate start。factory 传真实 snapshot，使用缓存磁盘账本避免回调全盘扫描。

构造和运行要求 D 盘 `hpc_linux`、native STATE，持有与原 collect() 同名 source fcntl 单写者锁。source 与 candidate DB 必须分开，禁止复用 live、shadow、budget-v2 等既有参考库。工程 runner 明确禁止调用真实网络 run。已有健康 collector 条件较宽，因此不能直接把其 30 秒报价健康标志当 5 秒可成交资格。

`await runner.run(...)` 返回原 collector status 加 `candidate_stage/candidate/candidate_qualification`，不会自行关闭数据库。调用方在 `finally: runner.close()`；该 close 幂等，关闭 source、candidate 和两者锁。CLI 若先 close candidate 再 close runner 也可。停止/恢复不会补造真实天数。

磁盘保护分别检查该 writer 自己的数据库增长配额和整个 VHD 的全局上限；其他研究 job 的 VHD 增长不算候选自己的 100MB 写入量。周期刷新预算也更新 candidate ledger。状态仅在审计链按真实输入写入，不修改当前参考账本。

## 验收记录

首轮 13 项核心检查已通过，包括 15m/1h 增量特征与独立 Polars 研究公式一致、未来数据不影响已生成特征、完整原始 mock WS 到四账户成交和实际成本差、四账户现金对账与同日 NAV、P06 合成来源不累计真实天数、缺 V/Q 冻结、时间/重复/数据改写、版本/参数改变恢复拒绝、重启 healthy 不补时、真实 v1 STOP 在模型/留出前拒绝及一次票失败不重读。

2026-09-30 最终扩展验收：19 项通过，57.76 秒，Ruff 通过。新增覆盖工程子库伪造 PAPER 状态拒绝、换 summary 不能改写已封存 STOP、真实启动前 quote/qualification 新鲜度、运行中参数改变阻断、source 单写者锁与幂等释放、错误发行版和既有参考库拒绝。测试只用 native 临时工程库和 mock WS；真实 holdout、实际候选、用户凭证和当前实测进程未触碰。
