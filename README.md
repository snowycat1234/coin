# Coin Quant

当前原则为用户2026-10-04的“从功能验收到投资改进”：解释实际损益与成本，选择一项有依据的改进，完成共同经济对照。历史实验由Git提交、配置、环境、数据清单和结果保留；当前源码可以正常维护。REUSE FIRST继续，旧固定模型顺序和永久代码冻结不再是当前路线。

- **投资候选：NONE，投资选择：CASH。** 研究强基准为过去风险估计控制的HOLD；代理历史正收益不代表长期APR或真钱资格。
- 已实现现货库存保护，以及单向逐仓USDT线性永续多头、空头、空仓、部分成交、资金费、保证金与恢复。D049八账户/303天、独立核账及12保存账本原因诊断均真实完成；仅多毛收益被成本抵消，仅空毛收益本身为负。
- 可配置多币组合已接入正常活动入口：有序标的映射、N维协方差、共享钱包与逐币规则、成交/净值输出和按日读取。相同规则和完整10k资本的两币/十币各四条件30日已完成：净收益两币1.36..1.46%、十币2.82..2.91%，分钟回撤约2.02%→1.43%，实际波动略升；仅为有限币池的开发筛选，不能年化为长期优势。完整结果见[多币组合](docs/MULTI_ASSET_PORTFOLIO_20261004.md)，投资仍CASH/NONE，风险与资源权限保持。
- 同一July池的10月31日对照已实际完成并独立核账：两币净0.95..1.18%，十币marked净0.006..0.138%、回撤更大，9月改善未延续。十币末真实8.65..8.79USDT持仓/浮亏完整计入，清仓收益NE；当前完成分类与分币归因已正常修正，旧失败保持。保留多币能力，暂停固定等权十币晋级；下一过去波动定权对照未启动，不能拼独立月份净值。
- 目标费用为Bybit VIP0。当前历史输入仍是Binance代理；数量过滤/历史清算和资金费单位尚有限条件，不叫Bybit原生回测。固定Turtle仅多仍亏0.83%–4.25%，仅空亏4.70%–7.34%，不采用为投资主力。
- 当前权威经济状态：[RESEARCH_STATUS](docs/RESEARCH_STATUS.md)，进度：[GOALS](docs/GOALS.md) / [PROGRESS](docs/PROGRESS.md)，实验记录：[registry](reports/experiment_registry.jsonl)。普通研究自主，不按固定旧清单重复验收。
- 长任务进度窗口：[localhost:8765](http://localhost:8765/)。只展示实际状态，未知总量不造百分比，磁盘值保留扫描时刻。
- D盘项目＋整个WSL VHD≤40GB（32GB预警/36GB停止新增），共享RAM≤5GB、swap0、GPU0。无锁定集、密钥、真钱、测试网或主网发单；单币绝对名义30%/共享gross60%、1倍逐仓、不追加保证金。

## 历史阶段说明

当前组合入口为 `scripts/investment/multi_asset_portfolio.py`，直接调用正常账户与目标接口；多空能力不要求每个规则策略都开空。D049及更早绑定旧源码的实验按其Git提交复现，旧报告不改写，旧AST/动态复制入口不作为当前组合路径。进度与限定证据见 [本轮记录](docs/MULTI_ASSET_PORTFOLIO_20261004.md)。

此前v3/v4/v6等结果保留，仅为历史证据；当前选择见上述状态页。以下旧阶段数值和门槛不代表当前运行任务或最近资源测量。
以下保留v3纠偏阶段结果：`CODEX_AUDIT_AND_NEXT_PLAN_2026-09-30.md`。
已验收工单A01–A08见`docs/GOALS.md`，当前优先级由v4增量覆盖。
G47/G50执行层扩张停止，旧Logistic STOP和原始报告保留。资源仍40GB/5GB，不用GPU。

当前A05/A06已完成：六配置×九fold共54次拟合、23个账户的790日开发期评估，
独立训练/推理/逐笔财务审计通过，结果**STOP_v2**。基础收益最高XGB_C为2.4724%，
Sharpe0.361，手续费2倍−0.4639%；主动基线中位数净收益5.2035%。
没有冻结候选或启封锁定历史测试。结果见`docs/MODULE_A05_RESEARCH_V2.md`和
`reports/A06_NONLINEAR_RESEARCH_ACCEPTANCE.json`。

在 D 盘的 `hpc_linux` WSL 中执行；工作目录 `/mnt/d/codex/coin`。

```bash
bash scripts/bootstrap.sh
bash scripts/check.sh
bash scripts/run.sh --help
```

Windows 调用方式：`wsl -d hpc_linux --exec bash /mnt/d/codex/coin/scripts/run.sh ...`。

全部运行数据、环境、缓存、临时文件和日志均在 D 盘。最新授权资源：40 GB 磁盘，
包含整个现有 D 盘 WSL 虚拟磁盘；32 GB 预警、36 GB 停止新增。
全部运行和训练共用 `coin-quant.slice` 的 5,000,000,000 字节 RAM 硬限，禁用项目 swap。
实时进程子限 2 GiB；所有重计算须通过 `scripts/bounded.sh`，GPU 暂不使用。

研究协议见 `PROJECT_PLAN_v2.md`；模块状态和验收记录见 `docs/PROGRESS.md`。仅提供公开行情与研究功能，账户密钥不属于首版配置。

完整目标清单和当前步骤见 `docs/GOALS.md`；编码、历史模拟与真实实测分别见
`docs/DELIVERY_STATUS.md`。历史182天端到端模拟、订单/对账核心和测试接口已工程验收，
执行合同、强基线、40因果特征、原生冻结推理与受控研究已验收；只读质量诊断已验收，当前积累交易流数据与真实时间证据，
全部模块尚未编码完成，盈利候选180天实测没有启动。
已完成的 Logistic v1 两项候选均 STOP，不部署盈利模型；最后六个月仍封存，
现称LOCKED_HISTORICAL_TEST，启封需要v2候选冻结及用户另行明确授权。
实际结果见 `reports/generated/P04/REPORT.md`。

历史完整系统模拟：`reports/replay_2024-01-01_2024-07-01/README.md`，
182日、四次同期间回放及三类故障通过，真实证据0天。
订单接口离线串联：`bash scripts/run.sh execution-check`，正式报告输出到
`reports/generated/P07/REPORT.md`，不使用账户凭证或发送交易所订单。

当前公开交易流采集使用 Windows 的 `scripts/microstructure.ps1 start/status/stop`，
运行于D盘`hpc_linux`，恢复后的真实断档保留。24h容量和14/30天数据质量门槛尚未满足。
旧`scripts/live.ps1`参考账户已停止，因冻结依赖变化拒绝复用；原账本和合同保留。
独立公开Kline v3已通过20项离线及真实90秒短测验收，长期启动后已核实跨调用存活与两币新增闭合WS线；
使用`scripts/collector_public_v3.ps1 start/status/stop`，见`docs/MODULE_COLLECTOR_PUBLIC_V3.md`。
新原生库不拼接旧版本的健康时间；72h资格尚未认证。
只读质量诊断通过26项工程检查，验收凭证`reports/A07_QUALITY_DIAGNOSTIC_ACCEPTANCE.json`。
2026-10-01 03:02:48 UTC实际报告核验184个分片、68,398行，完整性PASS，
实际24h容量/质量状态仍为INSUFFICIENT_EVIDENCE/QA_ONLY；完整共同UTC日为0。
新特征分布/数值范围诊断通过9项工程验收，见`docs/MODULE_A07_FEATURE_STABILITY.md`。
08:07:43 UTC真实快照308分片、114,938行，共同可用45,447秒，17特征无范围报警；
该有限描述诊断仍为QA_ONLY，不授予14/30天研究资格。
真实10月1日后原始接收凭证见`reports/A08_REAL_RECEIPT_START_20261001.json`，
仅证明实际接收开始，尚无候选TRUE_FORWARD_V2账户。
08:15:49 UTC新诊断验收全项目加整个WSL虚拟磁盘8.939 GB/40 GB，共享RAM峰2.083 GB/5 GB、swap0、OOM0、无GPU。
64项纠偏清单57项已有对应证据，7项待真实时间或候选资格，见`docs/V3_TASK_CHECKLIST.md`。
通用推理和40特征接线的分钟独立锚版本99项完整回归通过（561.60秒），原76项保留。
四账户实际成交后的压力短测2,380次尝试，闭合DB净增2,142,208字节；联合180天有限
投影37.904GB的旧容量失败保留。新正常/持仓压力完整重测及最终工程验收通过，
联合有限投影27.832GB/35.752GB，凭证`reports/A03_GENERIC_INTEGRATION_ACCEPTANCE_20261001.json`。
这项工程不等待盈利候选，生产运行仍须完整准入。
既有金融/执行状态机复用，修缮前来源及失败测量均归档保留。
本轮测试工件触发A07磁盘守卫退出，已取证、隔离测试、备份停机库并恢复新会话；
断档和旧会话保留。真实资源观察器已通过11项测试及60.005秒/7点实测，
2026-10-01 09:35:48 UTC开始新24h资源采样；须到真实窗口结束后另行复核，尚未认证24h。
整个项目尚未形成合格alpha或竞争性未来记录，盈利候选180天没有启动。

闭合资源窗口复核63项、原始环年龄诊断21项已完成工程验收；实际raw快照909分片、
139.99MB、最早命名15.42h，仍无24h保留/质量资格。正常连接轮转与strict clean日
判据的冲突见`docs/A07_DIAGNOSTIC_REVIEW_20261001.md`；不改冻结结果来授予资格。
异常凭证模块修缮后26项及真实60.004448秒验收通过，当前24h资源窗口继续运行。
原14/30研究门槛已按实际共同可用秒数累计；新报告解释范围见
`docs/A07_DATA_REVIEW_SCOPE_20261001.md`，不凭模糊断开原因增加有效/健康秒。

GitHub仓库为 `https://github.com/snowycat1234/coin.git`；按用户选择，仅每完成一个
模块并验收、更新文档后提交与推送。同步范围和推送记录见 `docs/GITHUB_SYNC.md`。
