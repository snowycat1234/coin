# 固定 7 日原生候选标签：接口与合成验收

状态：实现与合成验证完成；真实行情标签、训练、模型搜参、冻结 A/B 修改均为 **NOT_RUN**。工程通过不构成 selector 收益改善证据。

假设只有一个：单日贪心奖励可能忽略后续持仓、ramp 和成本，固定多日净收益是否更适合 selector。委托提供的 E5 H1 日贪心 +377 美元、固定组合 +467 美元只用于提出假设，本任务未重算这些经济结果，不能将单日贪心称作整段上界。

## 唯一标签定义

`HOLD_INITIAL_REQUEST_7D_DAILY_CAUSAL_REMAP`：在决策 d 的**同一实际钱包状态**分叉每个可用 one-hot 请求。在 d 到 d+7 日之间保持该请求，每个 UTC 日重新取得当日因果 context，以分支前一日预算调用传入的原 mapper，再由原 `NativeDailySimulator.advance_day()` 执行。保持请求不等于固定目标持仓；也不表示第一天请求之后延续基准。

Y 为 `NAV(d+7日) - NAV(d)`，保留原账户手续费、execution cost、资金费、保证金与 signed 头寸、风险减仓、逐日 ramp、pending orders、现金退出重试和订单优先级。中间标签边界保留 marked NAV 和残仓，没有免费平仓；恰好到原全局 end 才执行原收费终端规则。最后一天是否 target zero 由原 simulator 的显式配置决定，绑定到标签身份。不足完整 7 日返回不可评价状态，Y 和成熟时间为 null，不缩短期限。

这只是有限候选在明确延续规则下的条件价值，不是全局最优，不是 soft mixture 上界。`best_evaluable_action` 只是诊断，不能将其 7 日终态作为次日钱包或把不同赢家终态相加。

## 接口与因果边界

实现：[multiday.py](../../modules/native_action/multiday.py)。返回 `SevenDayEvaluation(row, diagnostic_end_states)`；无训练入口或历史生成 CLI。

```python
from modules.native_action.multiday import evaluate_candidates_7d
from modules.native_action.teacher import E6

evaluation = evaluate_candidates_7d(
    simulator, context_at, original_mapper,
    action_order=E6[:5],     # E5；E6 对应六个候选输出
    time_limit_seconds=900,
)
row = evaluation.row
```

E5/E6 输出复用现有六预算槽钱包/DayContext 契约，RANK 不可用时用 availability 分支已有 mask 和 checkpoint schedule；未把缺失 RANK 预测或奖励补零。原 mapper 作为依赖传入，没有改成新财务内核。合成测试使用已有 reference mapper；真实 E6 mapper 与保存预算/targets 的值级复核仍由实际输入拥有者完成，本任务不宣称真实适配已验收。

所有首日候选 X 在读取任何未来 context/行情前保存：当前因果 market/expert/wallet/budget 白名单，加首日 request、预算变化、可执行目标和相对当前仓位变化。d+1 至 d+6 的 context、目标、实际成交、reward、终态、未来可用性仅用于 Y/诊断，不进入 X。每日检查可得时钟；mapper、市场、非 RANK 身份、特征 schema、原生账户配置和延续规则绑定到 SHA256。RANK 仅可按照同一冻结 schedule 因果换 checkpoint。

`action_available` 只来自首日信息；`valid_mask` 表示后续评价完整性。首日不可用候选不映射、不分叉，features/Y 均 null。若后续请求不可用，或残余预算指向无定义的不可用专家，该路径 reward=null，不虚构 fallback/退出。发生后续缺失或账户/终端失败的整行 `optimization_allowed=False`，防止将未来可用性变成事后的训练赢家掩码。接口保留部分诊断。

标签 `evaluation_end_us` 为实际完整 7 日评价终点，`label_available_us` 至少为该终点，并包含观察到的资金费出版延迟/账户时钟；不是首日结束时间，也不是执行代码的墙钟时刻。

`purged_chronological_split()` 只分组，不拟合。整个状态及所有候选在同一数据角色；训练的完整 7 日 outcome end 和 label maturity 必须严格早于验证开始，保守排除共享边界 mark。验证样本必须有完整 outcome 落在验证窗口内且在 asof 成熟。新 schema、continuation binding 和 SHA、horizon、action order、可用/有效掩码及 null 奖励均检查。它是单个时间顺序切分，不承诺 shuffled CV；如以后做滚动 folds，必须逐个使用其实际边界，不混用未来重叠 folds。

## 原生流式缓存

[MarketTape.retain_days](../../scripts/investment/resumable_perpetual.py) 仅新增 reader cache。候选按日共同推进，同一流式市场块只读取一次；最多保留 7 个 immutable 日，真实钱包仍可随后推进一天。下一实际日的标签窗口滚动释放上一日，不复制财务引擎，也不改账户类、`simulate()` 或原单日训练器。

一个 tape 是顺序 reader；新的窗口不能倒退到已释放日，也不承诺旧诊断分支无限回读。调用者应顺序推进一条预先声明的实际政策；不同研究路径需要独立恢复/reader。本任务连续 14 日分段验收为第二段使用 portable snapshot 独立恢复 reader，首段原钱包仍可正常推进。

## 实际验证

- 新模块 **16 passed / 100.37 秒**；旧 scheduler 与输入相关测试 **8 passed / 29.22 秒**。均使用 `scripts/cloud_research.sh`，单 CPU、swap0、GPU0、6 GB address-space limit，分别 300/120 秒上限；不同测试目录位于 STATE。测试只用合成行情，不拟合模型。
- 固定请求两段 7 日与原 14 日连续 `simulate()` 的完整钱包 snapshot、pending、预算、funding cursor、minute ledger、trades/funding/rejections/breaches/extrema/liquidations 一致；中间持仓保留，真实全局终端收费且现金实现。
- 首日特征和候选 X 对未来价格、费率、market features、expert targets 修改不变；非 CASH 的 Y 和后续映射确实改变。另测分支 journal/预算/pending 隔离、stream 一次读取和滑动回读、E5/E6、不足 7 日、后续缺失、残余不可用预算、未实现终端、出版延迟、每日未来时钟、延续身份/请求绑定和完整 7 日 purge。
- 两个初轮失败为测试假设：不存在的交易字段，以及过低但仍可关闭小仓位的容量；修正为原字段/收费总量验收和零容量 pending 反例后完整重跑通过。未修改财务引擎以迁就测试。
- Ruff 新文件检查和 `git diff --check` 通过。汇总与复现命令见 [evidence](../../reports/MULTIDAY_NATIVE_LABELS_20261009.json)。

独立只读审阅并行完成，建议增加真实 future expert target 反例及 purge binding 验证；两项已加入。未启动第二份重复历史研究。

## 成本估计与唯一后续实证建议

每个完整状态最多 E5：`5×7×1440=50,400`；E6：`6×7×1440=60,480` 个钱包分钟。单日标签约 7 倍执行量；市场 reader 仅保留 `7×1440=10,080` 分钟，不随动作数增加。保留的诊断分钟账本和 mutable journals 仍随分支数增长；晚期 wallet fork 成本尚未测量。

初始合成 E6 七日全部评价的 fixture setup **11.96 秒**，包含输入建造、6 次 fork 和 42 个钱包日；不能据此估计真实后期 journal 大小。父线程提供的完整 182 日单政策 native episode **80–95 秒**，按约 176 个完整状态线性估算全段 E5 七日标签约 **45–54 分钟**，E6 约 **54–64 分钟**，尚未加入 fork/验证开销，超过 900 秒。预算不允许本轮生成完整 H1 标签。

唯一建议，待另行授权：在已有 seen H1、同一冻结基准实际钱包路径上，**预先固定 12 个稀疏日期**，各评价 E5 的单日与本七日标签；不搜索日期/模型。8 个训练角色日期为 2024-01-15、01-29、02-12、02-26、03-11、03-25、04-08、04-22；4 个验证角色日期为 05-06、05-20、06-03、06-17。标签完整结束/成熟后按实际边界 purge，05-06 前有超过 7 日的训练决策间隔。所有动作从同一状态分叉，实际基准按原冻结日路径推进，不能在验证部分生成赢家钱包。

先用其中首个与最后一个状态作预算探针并复用探针标签，不重复评价；设置总墙钟 **900 秒硬停止**，不提高内存/CPU预算，不扩容。核心 replay 粗估约 3–4 分钟，加基准推进和单日配对约 5–6 分钟，但晚期 fork 未知；若探针预估剩余工作无法在预算内完成则停止。只比较 1d/7d 的候选排序变化、负成本后 reward gaps、换仓/资金费占比、有效候选覆盖和不同时间段稳定性，保留全部负结果。此试验仍无 fit/搜参，不能证明 selector 学得会或连续收益提升；若没有稳定而有经济意义的标签差异，暂停此假设。

## 源码身份与资源记录

- handoff：`cc1829b3c8b5aa0bcf18ec70c1c669975b5343a5`；availability/本分支 parent：`94286155072ead9705c448b087cc8677a9a7fd35`。
- 最新索引：storage 分支 `b82412e9a34fcdaf7e44f2f9f2664e5b503b90a1` 的 `research_artifacts/native_20261008/INDEX.json`，记录本地源码 commit `987300aaf4e2bedaf1ca1a83dbfcedbaaef69f48`。仅解包所需源码，未恢复 NPZ、真实 teacher labels 或 market archive。
- 所取最小结果 ZIP 为 12,283,650 字节，SHA256 `9fed06d21231ea81419396e5a786511ad59286540ce3741349f480ae5e7340c0`。原 scheduler SHA256 `36c74d0bca4a3d556cf87aae223a8df06340f322652edcca192b363788875f6d`，与 handoff/availability 的原文件字节相同。
- 资源读取消耗另记：初次 Git shallow fetch 三个研究引用也传输了仓库内已有归档对象，`.git/objects` 从约 26 MiB 增为 328 MiB；这不是只取源码的最小传输，已停止进一步归档/行情获取。没有解包或使用行情对象。后续应先按 index/blob 精确取源码，避免全分支 fetch 带入归档。
- 没有 Library、新凭证/密钥、付费、训练、真实标签生成、交易、部署、main 修改、force push 或 PR。没有剩余实现阻塞；真实输入适配/经济价值验证属于未运行范围。
