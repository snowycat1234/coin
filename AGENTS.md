# 项目执行约束

**当前长期研发原则为用户2026-10-02明确采纳的《COIN：自主迭代、开源对标、投资质量优先》**，
精确原文 `docs/archive/COIN_AUTONOMOUS_INVESTMENT_PROMPT_USER_20261002.md`。
冲突处覆盖下列V8/v7固定科研路线、模型顺序、478特征强制共用、P1失败后的路线禁令及
固定frontier配额；不改变因果、真实成本、风险／资金、locked、密钥、资源和Git权限边界。
优先最短可靠的实际共同策略收益比较；可以采用具体公开策略为研究主力，再由自研挑战。
主力研究方案不等于真钱候选。允许清楚假设下proxy历史筛选，不必先齐全部BBO或高级统计；
代理成交必须标注。策略可有不同合理周期／特征，共用可比市场、资金风险、成本和评价。
每轮基于当前HEAD/实际任务/真实结果自主选择主任务，运行前短记问题/对照/数据角色/预算；
完成后报告改变、证据、采用或放弃和下步理由，不以合同／测试数量替代经济证据。
已有已验收入口／模型／失败工件保留，依赖不变不重复全套检查；普通方向无需逐项批准。
当前权威状态／只追加决策日志／registry继续沿用；不重新写总计划或扩平台。

用户2026-10-02新增平台费用标准为 **Bybit普通用户（nonVIP/VIP0）**，见
`protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json`与`docs/BYBIT_NONVIP_COST_STANDARD_20261002.md`。
常规crypto Spot maker/taker10bp/side；perp/futures maker2bp/taker5.5bp/side，不能混产品。
当前历史Spot研究输入仍为既有Binance封存来源，不把代理结果改称Bybit成交；旧协议/报告不覆盖。
Bybit Spot费用扣收到的资产，须薄适配并验证base/quote资金守恒；原quote扣费引擎保留。
未来实验显式绑定市场、费用profile SHA及费用资产规则；区域/实际账户费率、Bybit行情/过滤器
未验证。普通公开研究授权继续；不因此使用密钥、真钱、扩资源或重建执行平台。

**此前V8科研指令（冲突处让位上述长期原则）**，原文逐字节留存
`docs/archive/COIN_V8_USER_DIRECTIVE_20261002.md`，登记`docs/V8_OVERRIDE.md`。
冲突处覆盖下列v7：目标为risk-constrained net CAGR，当前必须
`NO_QUALIFIED_CANDIDATE`；≤180天仅SCREENING。旧oracle只叫
`SAME_WINDOW_IMPACT_DIAGNOSTIC`，不能叫可交易预测上限。
P1非重叠/严格OOF/匹配direct基线及四个分散OOS与统计经济gate通过前，暂停正式
深度模型研究、新增模型族、大HPO、maker盈利声明和真钱。P1若失败只能以真实
L1/L5/BBO信息重开，或转carry/basis/慢速组合，不继续同标签堆模型。
当前权威状态仅`docs/RESEARCH_STATUS.md`，决策日志只追加，所有运行登记
`reports/experiment_registry.jsonl`（旧运行缺失元数据明确UNKNOWN，不伪造）。
v7预算/自主权限及旧源码、数据哈希、负结果保留；40GB磁盘、当前5GB共享RAM、
swap0、GPU0和locked/真钱/密钥边界继续。旧AGENTS完整快照保存在
`docs/archive/AGENTS_PRE_V8_20261002.md`。窗口修复仅用户已授权的进度显示。

**此前v7科研指令（冲突处让位V8）**：
`CODEX_AUTONOMOUS_RESEARCH_DIRECTIVE_v7_2026-10-02.md`，登记`docs/V7_OVERRIDE.md`。
最终目标为统一风险下、扣除真实成本的长期净几何APR。自主选择信息增益最高的下一实验；
普通科研无需逐项批准。旧v6冲突的固定roadmap/180日启动等待/纯IC排名让位v7；
REUSE FIRST、冻结证据、holdout/真钱边界和D盘40GB继续。v7授权RAM最多8GB，
当前内核仍保持原5GB，GPU尚未启用。预算约60/20/20，至少20%frontier。
报告先讲APR候选/证据/阻碍/发现/下步/暂停与reopen；不追测试数量或工程百分比。
重大选择只追加短`docs/RESEARCH_DECISION_LOG.md`，不重新编写大规划。

用户于2026-10-02明确新增本机实时任务进度窗口；这是旧“不增加dashboard”的窄例外，
仅显示训练/测试/扫描任务进度，不扩市场、执行或资源观察器。新启动的长任务统一通过
`scripts/with_task_progress.sh --title '任务名称' -- 原命令`（内部仍经bounded.sh）。
先核对 `http://localhost:8765/api/status`；服务未运行时经bounded.sh启动
`scripts/task_progress_window.py`，在Codex浏览器打开并保留 `http://localhost:8765/`。
已有冻结/正在运行任务不注入或改源；实时轮次不可得时明确未知，只显示实际完成数、
进程耗时和工件更新。未知扫描总量不造百分比；最近磁盘值必须显示实际扫描时刻。

**此前v6优先级（冲突部分让位v7）**：用户直接要求立即执行
`OPEN_SOURCE_REUSE_OVERRIDE_v6_2026-10-01.md`，登记
`docs/OPEN_SOURCE_REUSE_OVERRIDE_v6.md`，当前长清单`docs/FAST_RESEARCH_TASK_CHECKLIST.md`。
REUSE FIRST → ADAPTER SECOND → CUSTOM MODEL LAST。冻结除实际correctness blocker外的
execution/Testnet/mainnet/resource-observer工程，不启动新的A11观察器或版本切换。
官方Binance历史URL/格式/CHECKSUM薄包装；pytorch-tcn/TLOB/TS2Vec/River优先成熟实现。
一套dataset/split/labels/normalization/metrics/economics；第一轮固定10配置1seed，两个primary。
不消费locked、不用真钱、不做RL/MARL/world model/dashboard。历史范围2025-07-01至
2026-03-01前；历史研究不受旧live14/30/60天等待约束，也不产生未来资格。
第三方先登记repo/commit/version/license/修改。已有全部冻结证据保留，下述旧v4冲突部分让位v6。

用户于2026-10-01明确采纳新方案，当前增量覆盖为根目录
`CODEX_AUDIT_AND_NEXT_PLAN_2026-10-01.md`，登记见 `docs/V4_OVERRIDE.md`；
旧 `CODEX_AUDIT_AND_NEXT_PLAN_2026-09-30.md` 的未冲突部分与既有证据继续保留。
实际进度、冻结来源和验收凭证见 `docs/GOALS.md`、`docs/PROGRESS.md`、
`docs/V4_TASK_CHECKLIST.md`；旧 `docs/V3_TASK_CHECKLIST.md` 保留。用户的后续指示优先。

- 所有 Python、测试、运行和训练在 `hpc_linux` WSL 中，通过
  `scripts/bounded.sh` 共用最多 5,000,000,000 字节 RAM，项目 swap 为 0。
  项目数据/缓存/临时文件位于 D 盘；完整项目＋整个 D 盘 WSL VHD 合计最多
  40,000,000,000 字节，32GB 预警、36GB 停止新增。当前不使用 GPU。
- 既有冻结研究/采集/质量来源、协议和证据按凭证哈希保护。先核对来源绑定；
  新实验、代码版本、失败、修复和复测使用独立新报告，不覆盖旧证据。
- 两路公开采集可能在后台运行。测试不得在真实 ROOT 中放置预期被守卫拒绝的
  外部符号链接、污染实际来源/数据库或临时删除目录。负面工件、短寿命目录和
  pytest `--basetemp` 放在 `/home/xflops/coin-state/` 的新独立测试目录。
  需要模拟 ROOT 的单元测试仅替换该独立测试模块的 ROOT 常量，全部工件在 STATE。
  不改冻结磁盘守卫来迁就测试；清理只针对可证明属于本测试的工件。
- 当前并行A09/A10，A09验收后才A11切换独立microstructure_l1_v2采集；不改v1来源/
  store/库，不拼接v1资格。v2实际14天仅诊断、30天仅固定Pilot、>=60真实UTC日且
  至少6完整OOS fold才正式预登记研究/M2；Pilot不能产生候选。Candidate冻结后才
  开始它的真正未来记录。启动前联合容量expected≤32GB/stress≤36GB/hard≤40GB，
  含1GB工作临时预算。L5/maker/GPU/复杂模型须满足新审计条件，当前不实现。
- 在线进程异常时先保存日志、检查点、audit head 和必要的闭合数据库备份；
  核对实际退出原因、资源及来源后恢复已授权的公开采集。新会话与断档如实记录，
  不拼接健康时间、不将缺失窗口补记为有效数据。
- A05/A06 当前为 STOP_v2；无新增结果驱动调参、最终拟合、模型冻结或锁定历史
  测试消费。微观结构 <14天只做数据QA/描述性特征诊断，14天仅预测诊断，
  30天固定三模型Pilot，>=60真实UTC日且>=6完整OOS fold才正式研究；须依据实际有效数据与验收门槛。
- 工程/历史回放、实际数据质量/资源窗口、alpha 候选和竞争性未来记录分别验收。
  当前无合格候选或交易所发单。真钱和锁定历史测试分别需要用户明确授权。
- 每完成模块，保存实际验收凭证、更新对应文档和长清单并报告进度。
- 用户指定 GitHub 仓库 `https://github.com/snowycat1234/coin.git`，仅在每完成
  一个模块并验收、修缮文档后提交和推送；不按小时定时推送。提交前核对源码字节与
  冻结哈希、敏感信息及新增文件大小。代码、协议、文档、小型验收报告和人工合成
  工程模型夹具入库；行情原始数据、真实模型文件、数据库、环境/缓存、日志、VHD
  和用户压缩包留在 D 盘。保留既有 Git 历史，不强推；推送需核验远程提交一致。
