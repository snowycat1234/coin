### D032：固定过去资金费永久退出假设（新状态控制／数组数学前，2026-10-03）

- 不继续调减仓target或挑2月退出；新增一个无拟合假设，完整原122日与90日各一个新账户，对照已保存pair-trim。C0=10k、初始q／1250reserve／625guard、gross0.6／单币0.3、BybitVIP0 fee／spread／slip、延迟／ownership规则完全保持；不新下载、改旧源码证据或重跑控制。
- 原开仓不变，持有满8×24h后，在每日00:00 UTC用决策前完整7UTC日、结束于决策前1UTC日的已归属signed funding合计；窗口首时刻须晚于entry。合计≤0则下一严格较晚closed分钟全平、永久CASH。原margin全平优先，已经排定的cap partial照固定事件优先级处理；无重入／增仓／补保证金／按币赢家选择。
- 一日滞后是显式未认证publication假设；raw archive event time／fraction／真实平台到账仍未证明，不能把历史已实现coupon视为即时可交易信号。新协议／费用钱包／退出ownership因果边界先冻结验收，再一次完整运行，7日窗／1日滞后不因结果更改。
- 预期信息：过去负coupon是否持续、提前永久退出损失多少后续正收入及两腿退出成本；从两完整窗口净值／事件DD／费用／放弃coupon判断，不以单月或Sharpe采用。两窗改善不一致或主要正收入被截断，则暂停这一固定gate；不接着扫3／14／30日，重开需新过去可得状态信息或真正时间外证据。原静态carry能力及负结果保留。
- 新模型拟合0／HPO0；预算共享5GB、swap0、GPU0、D40GB，新STATE两账户合计≤50MB／每任务≤600s。Bybit native重开仍须合规可达原生输入／filters／MMR；locked／真钱／密钥／付费／冻结覆盖须另获授权，普通研究继续。

### D032实施时序澄清（新gate数学前，2026-10-03）

- 日界锚点D=00:00 UTC，观察窗口精确为[D−8day,D−1day)，排除最近完整日，window_start>entry；合计为实际OWNED的两币signed funding现金，不用raw rate之和、不按币选择，真≤0且不加数值零带。复用原closed+1μs观察阶段判定，记decision_price_close_us=D及decision_observation_us=D+1；新退出在(D+60s)+1μs，原事件／fill循环不拆写。来源整数ms×1000不能在D+1μs发生事件，日界coupon输入仍严格滞后；原margin/full与已due partial优先规则保持。该时序明确实现口径，没有依据新结果改窗口／阈值；publication单位资格仍未认证。

### D032比较口径冻结（新gate正确性／行情数学前，2026-10-03）

- 两完整窗口分别对照已保存PAIR_TRIM；研究机制采用需每窗netΔ>1e−7USDT、all-observation MDD≤各自control+1e−10且原成本／risk／wallet检查闭合。阈值只是沿用会计误差判可分辨增量，不称为经济显著性、长期APR或完整风险等价。
- “主要正收入被截断”明确为退出后放弃的saved-control实际OWNED正coupon超过其全期OWNED正coupon总额50%；任一窗出现即暂停这个永久退出配方。负coupon避免额、净放弃额、暴露／费用／月度净值完整并列；这些均为结果后条件归因，不进入交易signal／NAV或倒选月份。0触发／两窗无一致净改善同样无新增采用依据。
- 门槛不会因本轮结果改变；Candidate仍NONE、长期APR仍NE。失败只否定固定7日／1日滞后永久退出，不永久删除adaptive learning或资金费能力，重开须新过去可得状态信息或真正时间外证据。
- 数值谓词事前明确为math.fsum已实际credited且逐事件独立核验的Float64 ledger cash≤0，无零带。Decimal钱包只核金额，不替换该决策符号；另报告Decimal.from_float精确和／独立钱包Decimal和及符号分歧。触发若对舍入敏感，保留ROUNDING_SENSITIVE_TRIGGER_WITNESS并暂停本固定gate采用，不把数值边界当稳定经济信号。
