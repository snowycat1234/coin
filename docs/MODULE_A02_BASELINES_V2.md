# A02：固定强基线与统一 V2 报告

## 范围与当前状态

遵循 `CODEX_AUDIT_AND_NEXT_PLAN_2026-09-30.md` v3 override。
实现独立 `quant.baselines_v2`，不覆盖 P03/P04/历史回放报告、不训练模型、不消费
2026-03-01 至 2026-09-01 的 `LOCKED_HISTORICAL_TEST`。
正式绩效执行必须等 A01 的统一执行合同与跨引擎 parity 验收通过。

资源仍为 D 盘项目与 D 盘 WSL 合计 40GB，共享 RAM ≤5GB、swap=0、不用 GPU。
审计文件的 8GB/VRAM 建议不视为用户新的明确资源授权。

## 固定定义

两项都只接受 BTCUSDT/ETHUSDT 完整 1h K 线，信号在该 bar 实际 available 时刻产生。
原始目标是每币 0 或 30%；公共回测器只缩放一次，统一总仓 60%、年化波动目标 10%、
前一完整分钟成交额 0.1% 容量、5 分钟等待、10 USDT 最低金额和冻结 lot step。

|基线|入场|退出|连续热身|
|---|---|---|---|
|B3 Donchian55/20|当前收盘价严格大于**之前**55根完整小时的最高 high|持有后收盘价严格低于**之前**20根完整小时的最低 low|55根前序小时；第56根才可发入场信号|
|B4 Slow Momentum|`close / close[t-168h] - 1 > 0` 且 `close > EMA168`|任一条件不成立即空仓|169根连续小时，满足完整168小时滞后|

B3 当前 bar 的 high/low 不计入自身比较通道。等于通道不触发，持有状态直到退出，
不把小时内触价当成免费成交。B4 EMA 使用 `adjust=False`、alpha=2/169，自当前连续段
首根收盘价初始化，当前 bar 收盘价可更新 EMA，因为决策发生在收盘资料可得之后。
缺一完整小时则重置窗口、EMA和持有信号，重新热身；不向前填充行情或交易信号。
OHLC 无效、非完整小时、重复主键和可得时刻非递增均拒绝。

参数固定，无优化或候选参数搜索。两币独立生成信号，不借用另一币未来资料。

## API

`strong_baseline_signals(bars, name)` 返回 B3/B4 诊断表，含可得时刻、仓位信号、热身、
前序通道或 EMA/168h 收益。`baseline_targets_v2(bars,name)` 覆盖 B0..B4，返回
`available_us/symbol/target_weight` 公共回测合同；B0/B1/B2 沿用原固定定义。

`run_baseline_suite(bars,minute_bars,config,parity_receipt=...,output_dir=...,dataset_id=...)`
是受门槛保护的统一报告入口，不自行加载数据。缺 A01 PASS 或 `ExecutionContractV2`
时在信号和回测之前拒绝。必须显式相同首尾时刻，历史 latency=1；风险和成本参数不得改动。
输入出现锁定区间 bar/minute 直接拒绝，终点最多 2026-03-01 不含。
A01 receipt 必须同时含 `status=PASS/execution_contract_version=execution_v2`、当前
`ExecutionContractV2.digest()`、`cross_engine_parity.pass=true`、canonical baseline PASS。
`source_hashes` 每条必须安全位于 ROOT/src/quant、匹配当前源码，至少绑定 backtest 与统一合同；
canonical baseline 的 path（若是目录则 summary.json）须为真实项目文件且字节 SHA 与
`artifact_sha256` 一致。缺证、自称通过或实现改变均拒绝；门槛尚未就绪时不得执行绩效。

报告包含 B0 Cash、B1 BuyHold、B2 EMA20/100、B3、B4，各自基础、手续费2倍、额外滑点2倍。
公共风险、费用、成交和估值缺口统计保留。主动中位数仅 B2/B3/B4，Cash/BuyHold 单列；
净收益和 Sharpe 中位数分别给出，不把赢一个负收益基线解释为 alpha 通过。
所有结果只称 `DEVELOPMENT_HISTORY`，`alpha_candidate=false/true_forward_days=0`。
每份底层报告仍保留观察日度 MDD 与未观察路径限制。

输出须使用新 D 盘目录，不能覆盖已有证据。先统一预留 752MB（15份单报告50MB上限
加摘要），逐份计算/保存后释放大型结果，避免同时保留15份成交表。

## 验收

只使用合成小时路径，验证之前通道而非当前极值、严格阈值、持有/退出、完整168h滞后、
独立 Polars EMA 公式、缺小时重置、未来修改不影响历史、两币隔离、无效时间合同拒绝。
统一 wrapper 用明确测试 stub 验证15条固定成本路径和主动中位数，不产生历史绩效。
缺 A01 时先拒绝的测试不得调用信号或回测。

正式 B0-B4 canonical V2 报告当前未运行；待 A01 通过后另写独立验收与结果。

2026-10-01 准备阶段验收：10 项通过、11.45 秒，Ruff 通过；源码/测试摘要与范围记录在
`reports/A02_SIGNAL_ACCEPTANCE.json`。这份文件只认证因果信号与 mock wrapper，
不是 A01 PASS，也不是 alpha 或历史绩效验收。

随后按父代理 A01 receipt 合同补齐 fail closed 验收：23 项通过、26.92 秒，Ruff 通过；
新增自称 PASS、旧合同、缺 parity、缺基线、恶意路径、摘要不符、改变成本/风险/延迟及
触及锁定区间的拒绝检查。当前实现和测试摘要另存 `reports/A02_PREFLIGHT_ACCEPTANCE.json`，
保留最初准备阶段文件。尚未收到 A01 正式通过信号，绩效仍未运行。

## A01 通过后的正式执行与验收

父代理已明确授权 A01 PASS 后运行。共同区间为 2022-02-01 至 2026-03-01 不含，
数据锁 `dcfd7fdb5824325da2e9acbc4426570e5a26b31260891f5569ae5651f1b11336`。
分钟数据先按文件名 `<2026-03` 枚举100个开发月文件，再打开，只读4,374,720根分钟；
小时数据以 available<cutoff 的 predicate 读取，共72,910根。没有先读锁定分钟再过滤。

15份报告写入新目录 `reports/generated/P03_STRONG_BASELINES_V2`，1489个UTC日，
97.66秒，报告实际约16.27MB。共享RAM峰值1,894,678,528字节，swap=0，无OOM、GPU不用。
已核验 B0/B1/B2 的基础、手续费2倍和滑点2倍**全部指标**与 A01 重新生成报告一致。
`reports/A02_CANONICAL_ACCEPTANCE.json`记录PASS，表示实现和统一报告验收完成，
不表示基线合格或 alpha 通过。

|基线|基础净收益|基础Sharpe|手续费2倍净收益|额外滑点2倍净收益|
|---|---:|---:|---:|---:|
|B0|0.00%|0.0000|0.00%|0.00%|
|B1|24.50%|0.5275|24.07%|24.32%|
|B2|1.61%|0.0886|-15.04%|-5.42%|
|B3|-2.12%|-0.0388|-16.96%|-8.36%|
|B4|-30.59%|-1.0951|-55.80%|-42.08%|

主动 B2/B3/B4 的基础中位数净收益为 -2.1184%、Sharpe -0.0388；不能因中位数为负
而放松 v2 候选的正净收益、Sharpe、成本压力和风险门槛。B3基础手续费1606.78 USDT、
执行成本803.39、单边换手164.923、461闭合周期；B4分别3774.89、1887.45、444.250和1202。
这次结果不触发参数修改或重新选择基线。

**风险限制：** B1/B2/B3/B4 各有1天持仓陈旧估值，来自2023-03-24隔离日。
它们的 `daily_risk_observable=false`，观察日度MDD不能认证完整风险路径；现金B0不受该影响。
缺口内数量与全部跨期损益仍保留。没有已获准盈利候选，也没有真实前向资格。

实际计算使用 backtest 原SHA `18b6defffbf6248c156695102aab80302ec146b0d1d8fb338b272588b319f89d`、
ExecutionContractV2 digest `74a83007641c5243e6042df089ebabfd48e1dbf81b221795c64027cb96a066a2`。
验收从本次 summary 内嵌的当时A01 receipt取执行源码绑定；随后A05持有期执行补充的源码
不能冒充此次运行版本，原始报告不覆盖。
