# D038：固定公开 SMA50/200 日线筛选（2026-10-03）

**当前 `NO_QUALIFIED_CANDIDATE`，长期净 APR 不可评价。** 新 SMA50/200 日线账户在已见 547 日窗净赚 940.611246 USDT，122 日窗净亏 531.707290 USDT；90 日窗没有交易、全程现金。三个生成器、独立核验、保存结果比较和根验收均已真实完成，验收范围是历史代理核算与因果筛选，不是投资采用资格。547 日 VM 在净收益、实际波动和分钟回撤三项均优于 SMA；122 日 VM、2h 和 hybrid 均如此。没有原生 Bybit 成交证明；三个独立评分窗不拼接 NAV，不把描述性 CAGR 称为长期净 APR。

## 瓶颈、发现与科研选择

前两窗的费用已经较低：547 日 gross 979.538133、总成本 38.926887 USDT；122 日 gross −521.729329、总成本 9.977961 USDT。后来窗口的损失主要发生在成本之前，不能再把高换手费解释为主要失败机制。不同入场确实降低交易次数，但尚未提供跨状态稳定净优势。

风险与执行也有实质缺口：547/122 日实现年波动分别 13.174393%/14.749935%，并不等于原 10% 目标；547 日期末仍有 **1662.260412 USDT 实际持仓市值**，这是实质残余库存，不能称为 dust、免费清仓或已经变现的利润。原 .3 是订单/目标权重约束，**不是每个分钟标记持仓的硬上限**；547 日 BTC 被动漂移最大权重 34.491194%，独立核验有 **35,016 个分钟**单币标记权重超过 .3，gross 未超过 .6。同一风险规则不能替代统一实际风险验证，也不能据前窗正收益宣称风险收益赢家。

保留原开源 hook、日线薄适配、官方数据与共同核算能力；暂停本固定 SMA50/200 配方的投资采用。重开须有新的事前固定因果信息/机制，或真正未来、同原生成本与合理风险下的稳定净证据。不同窗口的原负结果、原参数和失败证据继续保留，不扫描均线周期、挑月份、降低成本或增加杠杆。

Research lead 选择的下一普通研究是**固定三窗、已保存 SMA/VM/2h 的分币 gross 与实际持有暴露归因**：先区分集中 BTC beta/被动漂移与 signal，再决定风险控制实验。只复用已有账本，不新增账户、调均线/HPO、重做旧 QA、挑赢家月份或拼接期间。这项选择不预先假定日频再平衡会盈利；归因尚未执行。

## 固定配方与数据角色

- 原 `jesse-ai/example-strategies` commit `7c91e0a37bf62165790120d730442e4f6eb00364` / MIT；原 `SMACrossover` class hooks 字节不改。`fast>slow` 允许空仓入场，`held long & fast<slow` 退出，相等保持原状态；不是必须当天发生交叉。原 class 只有 `@property`，SMA 每已完成日重算，COIN port 用成熟 Polars rolling mean 的 scalar last50/200。[原来源](../third_party/jesse_example_smacrossover/UPSTREAM.md)、[真实来源证明](../reports/fast_research/SMACROSSOVER_OFFICIAL_SOURCE_PROVENANCE_20261003_V1.json)
- 原策略支持 short 与 whole-balance sizing；本轮只移植原比较/退出 hooks，固定 daily long-only、每币 0/.3 目标，原 sizing/short/Jesse engine 不移植。
- 三评分窗固定 2024-01-01..<2025-07-01、2025-08-01..<2025-12-01、2025-12-01..<2026-03-01；每窗独立 10,000 USDT、fresh flat。200 连续已完成 UTC 日只预热指标，不建立 warmup 仓位。来源直接复用 D037 官方日线 66 档/每币 1004 日，不再下载或 QA。[已接受日线来源](../reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ACTUAL_20261003_V2.json)
- 日线只生成信号；执行、30 日/最少 20 日风险、前一分钟容量和终端估值继续使用已接受分钟来源与原 native 金融循环。day close==decision 可用，原下一分钟 close+1µs 执行，end 收盘不进入 end−1minute 最后决策。
- Bybit 普通用户/VIP0 **Spot 10bp/side 按收到资产扣费**，买入扣 base、卖出扣 USDT；spread 8bp round trip、slippage 4bp/side，总名义 **36bp round trip**。此规则应用在 Binance 历史代理数据上，非 Bybit 原生行情/BBO/过滤器/历史账户费认证，不挪用永续 5.5bp。[费用标准](../protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json)
- 模型拟合/HPO 为 0；locked、真实资金、账户密钥、GPU 未使用。旧来源、日线算法、账户核心和旧负结果保留；新 runner 只作私有 namespace/strategy dispatch。

## 独立账户结果

金额单位 USDT。gross 为同实际净收到持仓数量的 gross shadow，不是另跑的免费账户；成交数是 fills。各窗本金分别 10,000，不平均/拼接账户。

| UTC 评分窗 | 天数 | Gross | Fee | Spread | Slippage | Net | 期间净收益 | 分钟 MDD | 实现年波动 | 原引擎期间 turnover | 成交 fills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024-01-01..<2025-07-01 | 547 | 979.538133 | 21.622326 | 8.652280 | 8.652280 | 940.611246 | +9.406112% | 13.765712% | 13.174393% | 1.963968 | 26 |
| 2025-08-01..<2025-12-01 | 122 | −521.729329 | 5.542419 | 2.217771 | 2.217771 | −531.707290 | −5.317073% | 11.339604% | 14.749935% | 0.569461 | 5 |
| 2025-12-01..<2026-03-01 | 90 | 0 | 0 | 0 | 0 | 0 | 0% | 0% | 0% | 0 | 0 |

547/122 日原 daily MDD 分别 11.355949%/10.563342%，与分钟 MDD 不同；all-event MDD 未建立。期末实际持仓市值分别 1662.260412/0.835507 USDT，保留 marked NAV，不假定免费清仓。turnover 为原引擎期间累计值，不是日均周转。描述性年化、Sharpe 仅为保存字段，不能作为长期资格。

### 保存结果的公平比较

[保存经济比较](../reports/fast_research/PUBLIC_SMA_DAILY_ECONOMIC_COMPARISON_20261003_V1.json) 只读取已接受的小报告，没有重跑参照账户。相同本金、费用和原风险规则下，比较期间 net、实际年波动和分钟 MDD；“支配”仅表示这三个保存指标均不劣且至少一项更好，不表示统一实际风险已实现或长期最优。

| 期间 | 保存比较发现 | 经济解释 |
|---|---|---|
| 547d | VM net +1606.234069、波动 10.163562%、分钟 MDD 9.254981%，三项均优于 SMA | SMA 前窗正收益未优于简单风险管理持有；不能仅按收益选择 SMA |
| 122d | VM net −412.710118、2h +46.710155、hybrid −145.395011；三者各自波动/分钟 MDD 均低于 SMA | 低成本 SMA 仍主要输在 gross 与暴露路径，不是费用未压低 |
| 90d | SMA 与 CASH 均零交易/零净收益；hybrid net +71.363856 且承担实际风险 | SMA 的避损是保持现金，不是正交易 alpha；零风险与有风险账户不能据此称统一赢家 |

| 窗口 | 实际报告 / SHA256 | 实际 task |
|---|---|---|
| 547d | [ACTUAL](../reports/fast_research/PUBLIC_SMA_DAILY_547D_ACTUAL_20261003_V1.json) / `8d8b49578af725b6666b3a98e6468e1bb40323fc7c2675f083109985f6da5970` | `106d385620d44722b664c4d2fca92602` |
| 122d | [ACTUAL](../reports/fast_research/PUBLIC_SMA_DAILY_122D_ACTUAL_20261003_V1.json) / `1e52e713eee4ccb36d807ebfa04c4f26a7537e1c688f1a8cc20d6404b6a96974` | `f22bc93fe02d484c81887cfe1fc02800` |
| 90d | [ACTUAL](../reports/fast_research/PUBLIC_SMA_DAILY_90D_ACTUAL_20261003_V1.json) / `60d4d74dcf70d4a227108ab88525402ce9c333a2bb62bd7d4dd5b54e26a0077d` | `40c78f75d78749bba1b46e6bfbd7bfbb`（session81418/chunk48997d/exit0） |

## 失败、修复与验收边界

[唯一新增 case V1](../reports/fast_research/PUBLIC_SMA_DAILY_BOUNDARY_TINY_20261003_V1.json) 真实失败，报告 SHA `a36a0828878734c2df6eef12460db8e9fbb2e84e64eb564b86d6d1eb1fed1181`、session87286/chunkb4ecaf/exit1、task `4c2db7bfba664a44a2a28a66b25172ef`。scalar/state/equal/未来/缺失检查已通过；错误是测试要求每笔 BUY 都发生在首入场时点。失败保存账本中 ETH 在 day1 入场，共同账户合法补买 BTC gross 0.20765，BTC 此前持仓未平。

新 [case V2](../reports/fast_research/PUBLIC_SMA_DAILY_BOUNDARY_TINY_20261003_V2.json) 只修该假设：每币首 BUY 仍精确入场时点，后续 BUY 须已有净仓位且只在独立固定 held 日，保留 latency/no-warmup/no-flat 约束。所有费用、现金/净数量桥、原金融 AST、容差与生产策略不变。实际唯一 case 1 pass、0 failures/errors/skips，task `168bc7b9a6b74e1b9be98ae54ef5c378`，报告 SHA `a18dd4e3dd99c04f0f3bd5bdcac7aca0e2a448f613c082826ad47d98a9ca1c81`；旧测试/协议/失败报告保留，不把 V1 整体记 PASS。

[独立审计 V1](../reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json) 另有真实初始化失败：task `f8285234aef34fc7a35dc97484ee944c`、exit1，SHA `958f1168adbd9caeb60cdae4baf3364fe78297bac3a6edf0242c5a79947af419`。严格守卫在价格/金融数组前拒绝本轮新增的 `docs/OPEN_SOURCE_REGISTRY.md` 元数据路径，完成账本数为 0。V2 只桥接该精确路径与已冻结 `8da5b041…` 字节身份；来源、策略、金融数学和容差不变，V1 不改为 PASS。

[独立审计 V2](../reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json) 实际 closed0，3 账户 / 759 日 / 1,092,960 分钟 / 25 月。独立 `math.fsum` last50/last200 严格比较、原 hook 状态与保存目标三窗一致，没有增加 epsilon；Sparse Decimal 逐成交现金/净数量/费用桥最大金额误差 **1.7054845e−11 USDT**。Decimal ratio 断言未执行，全事件 MDD 未认证，不把金额核验扩称比率/全事件风险认证。没有调用生产目标生成器或模拟器重放旧账户。

| 闭合角色 | 实际报告 / SHA256 | 实际任务与退出 |
|---|---|---|
| 独立 V2 | [AUDIT](../reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json) / `dddc9a0514767c3f4e2b8059d82a3da76bd12a81d90e34a3bc46aa1fce77db4f` | `90a7c36a5e0d48e8aaffe190369644f5`，session13246/chunk0a13b4/exit0 |
| 保存比较 | [COMPARISON](../reports/fast_research/PUBLIC_SMA_DAILY_ECONOMIC_COMPARISON_20261003_V1.json) / `2b00a16f4b7ec31c792893fc17aa2105e6f5b4c94bf199a7faf9ef036165b33d` | `e6357597667f4d46af038ac4502e9737`，chunkfc62af/exit0 |
| 根验收 | [ROOT](../reports/fast_research/PUBLIC_SMA_DAILY_ROOT_ACCEPTANCE_20261003_V1.json) / `c3175271dd339f65e339141b8cc36d98472b4cf4acf114ceaacb03caf44f935c` | `fb382c25d5254f5cad1252f49190561a`，session80045/chunk595ad1/exit0 |

根报告生成时如实保留自身 `LIVE_NOT_YET_CLOSED` 字段；随后真实 task 元数据已 completed/exit0，不覆盖报告造闭合。两次失败、小报告和来源快照均保留。[便携来源绑定](../reports/GITHUB_PUBLIC_SMA_DAILY_SOURCE_BINDING_20261003_V1.json) SHA `fb932534a248f167e1e75c948f97798546ce75bbc5c99a05a8126ca1068e5dcc` 将私有数据 lock 单列校核。**Git 提交/推送与远程精确一致尚待完成**；本文件不预填 PUSH 成功。

## 已记录资源与磁盘时刻

| 角色 | 耗时 | 主进程峰值 RSS（B） | 实际 owned bytes |
|---|---:|---:|---:|
| 唯一 case V2 | 112.4017s | 191,770,624 | 2,423,720 |
| 547d | 79.8993s | 2,015,547,392 | 262,836,433 |
| 122d | 72.8323s | 642,916,352 | 69,760,609 |
| 90d | 73.4167s | 542,232,576 | 50,689,753 |
| 独立 V2 | 86.1143s | 1,051,361,280 | 4,618 |

根验收逐八个登记 STATE 目录合计 **388,013,693B ≤ 450,000,000B**，包括 vendor、小测试 V1/V2、三账户和独立 V1/V2失败/成功目录；这是该八目录的实际专属字节范围，不是全盘新增估计。共享 WSL RAM 5GB、swap0/GPU0、D盘项目+VHD40GB边界保持。根验收共享 cgroup 采样 `memory.peak=3,263,008,768B`、swap0、OOM/OOM-kill0；累计 cgroup 峰值不冒充本模块独占或某角色同时峰值。主进程 RSS 也不冒充共享峰值。

- 122 日实际磁盘扫描结束 2026-10-03 08:48:56.860859+08:00，项目+VHD **20,549,753,655B**。
- 547 日实际磁盘扫描结束 2026-10-03 08:49:16.863148+08:00，项目+VHD **20,616,889,535B**。
- 90 日实际磁盘扫描结束 2026-10-03 08:54:32.790511+08:00，项目+VHD **20,886,214,070B**。这是三个账户报告中最后一次实际扫描，旧值不包括之后新工件，不标作实时磁盘量。
