# P06：真实前向竞争性记录验收基础

本模块是纯只读证据评估，不启动采集、影子、测试环境或真钱交易。没有符合完整门槛的真实记录时，产出 `INSUFFICIENT_EVIDENCE`，不能把工程完成解释为策略认证。P04 Logistic 首轮已拒绝，B0/B2 后续记录只作参考，不授予盈利 champion。

最新资源约束：D 盘项目和 WSL 总预算 40 GB；运行与训练共享 RAM 上限 5,000,000,000 字节，禁止 GPU，后续重任务统一由 `scripts/bounded.sh` 进入共享 cgroup。已封存的旧 20 GB 数据审计报告保留原始记录，不改写历史结果。

## 合同与资料完整性

`evaluate_forward_records(records, head_hash, triggers_verified, expected_version=None)` 先核验整个追加式 SHA-256 日志，再筛选一个冻结候选版本。每条记录字段为 `seq/received_us/version/kind/payload/prev_hash/hash`；序号从 1 开始，首个前序哈希为 64 个 0，使用排序和固定分隔符的 canonical JSON。SQLite 只读快照适配器须核验拒绝 UPDATE／DELETE 的触发器，提供完整记录和尾哈希。

`read_forward_report(db_path, expected_version=None)` 使用 `quant.shadow.read_forward_evidence(db_path)` 的只读连接读取整条链，再筛选候选版本。账本未存在时直接证据不足；不能用 collector 的行情 SQLite 替代。`evaluate_forward_snapshot` 可供 CLI 对接已关闭的只读快照。

完整性范围是本机正常应用路径的 append-only 与哈希链审计，当前不含外部签名或不可篡改外部锚，不能宣称可抵抗同时恶意改写数据库和所有本地审计资料。链断裂、日 NAV 改写或重复记录直接 FAIL。正常版本更新须新版本重新起算，不能拼接收益或日期。

记录种类为 `start/nav/round_trip/incident/heartbeat`。候选起始记录须 `role=candidate`、`mode=live_paper`、`source=live`，并记录初始资金和开始前真实 72 小时资格。日 NAV 分别为 `candidate/B2/fee_x2/slippage_x2`，包含 UTC 日期、NAV、当日费用、点差滑点、换手、`stale_exposure/daily_risk_observable` 与来源。只有在该 UTC 日结束后 5 分钟内真实写入的日度观察可作为前向证据；shadow 自身标为 `timely_recorded=false/MISSED_WHILE_STOPPED` 的记录，即使只迟到数分钟也不计资格。迟到历史重构不能凑天数。

工程合成资料须 `mode=engineering_simulation/source=synthetic`。可诊断链和日期合同，真实观察天数固定为 0；190 个合成日也无法获得 180 天资格。纯行情采集会话没有候选版本和日NAV，不能作为策略竞争性成绩。

## 固定认证门槛

同一冻结候选真实首尾至少 180 天，且至少 180 条连续完整 UTC 日 NAV 可观察，候选、B2 和两种成本压力记录须为完全相同日期区间。首个部分 UTC 日 `complete_utc_day=false` 不计完整日，其及时可观察日终NAV作为随后完整日窗口的起始资金，不把部分日损益错误归到次日。任何其他不完整日不能补造，起始NAV缺失也不能默认补初始现金。缺少压力数据时明确报告缺失，不能填 0、采用历史回放或假定压力非亏。存在事故直接 FAIL；其他阶段、时长、日期或资料不全为 INSUFFICIENT_EVIDENCE。

完整证据后才检查：净收益正、UTC 日度 365 日年化 Sharpe ≥1、观察日度最大回撤 ≤12%、至少 4 个完整正收益日历月、两种成本压力净收益非负、相同期间净收益超过 B2、至少 30 个有唯一标识的已闭合独立持仓周期、事故数 0。配对日收益差采用 7 日循环区块自助法、2,000 次、种子 20260930；日均超额 95% 区间下界须严格 >0。通过以上门槛才 `PASS/champion=true`，否则完整实验记 `FAIL`。

P06 PASS 仍不授权真钱，也不能替代真实至少 30 天 Binance 测试环境、订单状态与对账凭证、框架版本复核和用户资金授权。本模块只读取现有证据；`write_forward_report` 在 D 盘生成中文 REPORT.md 和 JSON。

## 本轮状态

P05 当前是公共行情采集前置；新 paper 基础仅计划 B0/B2 参考账本，没有冻结盈利候选和成本压力前向日NAV。因此当前结论必为证据不足。工程测试仅验证日期、缺证、事故、篡改、版本隔离及相同期比较，不能替代180天实测。

2026-09-30 验收：9 项工程测试通过（13.13 秒），Ruff 全部通过。包括 190 个合成日仍不能获得真实天数、缺成本压力不填 0、事故拒绝、哈希篡改检测、版本不拼接、B2 日期严格匹配、SQLite 只读检查后文件 SHA-256 不变，以及部分首日不计完整观察日。当前默认 native shadow 库尚不存在，只读报告正确返回 `INSUFFICIENT_EVIDENCE`；中文与 JSON 初始报告已保存至 `reports/generated/P06/`，没有建立策略库或启动影子进程。
