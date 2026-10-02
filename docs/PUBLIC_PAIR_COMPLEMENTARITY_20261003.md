# D036：两个固定公开策略的保存账本互补性

## 本轮结论

1. **当前长期净 APR 候选：NONE。** 原 2h Donchian 与 2h 入场／1h 退出混合策略仍是研究参照，没有投资采用资格。
2. **长期净 APR 证据：未建立。** 本轮只诊断已接受账户的保存日损益和实际标记持仓，不产生新账户、组合净值或年化收益。
3. **最大阻碍：亏损和暴露高度共同。** 两个策略共用 2h 入场，退出差异及历史净收益排名翻转，没有在固定尾部日期形成净损失保护。
4. **主要发现：** 三个独立窗口的日 USDT 净损益 Pearson 为 0.9031／0.8464／0.8376；所有六组“自身最差 10% 日期上另一策略的净损益”都为负。
5. **本轮采用／暂停：** 接受保存账本统计、来源绑定及独立核验能力；事前预算筛选为 false，暂停这个同入口的固定 50/50 组合，不执行新的组合账户回放。此结果不能证明所有组合必然无效。
6. **下一步／重开条件：** D037 优先固定更慢的开源 Donchian 日线同规则单配置，研究不同入场时间尺度及低换手能否改善成本后的收益；具体来源、暖启动和协议尚未冻结，尚未运行。当前组合只有不同的因果入场信息，或真正后来、同成本风险条件下的净损失分散证据出现时才重开；不放宽本轮阈值。

## 固定范围与结果

P 为原 Jesse Donchian 2h，H 为固定 2h-entry／1h-exit。每个窗口的两个原账户分别从 10,000 USDT 开始，复用相同输入和风险参数、36bp 保守成本档。价格来自 Binance；Bybit 非 VIP 收到资产扣费为费用反事实，未认证原生 Bybit 行情、成交、过滤器或完整实际风险等价。三窗都是已见开发历史，分别计算，不合并账户或按月份选择赢家。

| 窗口（UTC，右端不含） | P 原账户净 USDT | H 原账户净 USDT | 日净损益 Pearson | 最差 10% 日期重合 | 实际持仓权重重合 |
|---|---:|---:|---:|---:|---:|
| 2024-01-01～2025-07-01，547日 | +760.18 | +584.00 | 0.903087 | 38/55 = 0.690909 | 0.628243 |
| 2025-08-01～2025-12-01，122日 | +46.71 | −145.40 | 0.846441 | 7/13 = 0.538462 | 0.685285 |
| 2025-12-01～2026-03-01，90日 | −197.05 | +71.36 | 0.837604 | 4/9 = 0.444444 | 0.848681 |

这些净值差额为原完整账户的保存结果，包括终端标记持仓；不能解释成新增组合收益或全部已变现现金。日净收益率 Pearson 分别为 0.904875／0.846178／0.839888，也没有改变共同亏损结论。

| 窗口 | P 最差日期上 H 的净 USDT | H 最差日期上 P 的净 USDT | 同负日／全日 | P／H 真实负日数 |
|---|---:|---:|---:|---:|
| 547日 | −2,886.83 | −3,804.86 | 282/547 = 51.55% | 298／311 |
| 122日 | −466.46 | −515.78 | 65/122 = 53.28% | 65／69 |
| 90日 | −233.69 | −301.24 | 53/90 = 58.89% | 54／55 |

所有尾部集合都有足够的真实负日，六个另一策略尾部金额均不接近零；没有舍入敏感保护结论。严格正标记持仓（包含 dust）的活跃时段 Jaccard 三窗均为 1.0，不能将其解释为目标完全相同。实际总权重 Pearson 为 0.8180／0.8365／0.9109。

事前规则要求两个后来窗口日净损益 Pearson 都小于 0.8、后来尾部重合均小于 0.7、至少两窗且包含后来窗存在另一策略尾部净损益非负、每窗权重重合小于 0.8。只有尾部重合这一项通过；后来相关性、尾部保护及 90 日暴露条件失败。因此不继续花预算回放该固定组合，不据结果修改筛选阈值，也不将此预算规则称为统计显著性或投资门槛。

## 计算、验收与留证

- 只读取 12 个既有 Parquet：六份 daily NAV、六份分钟 inventory 投影；不读 fills 或价格输入，不重放旧账户、旧资金数学、旧数据 QA 或绿色测试。
- 每日净损益为连续 NAV 差额，首日前值为 10,000；收益率除以前日 NAV。最差集合取 `ceil(0.1×N)`，按带符号 USDT 差额升序及 UTC 日期破同序；重合为交集数／k。每窗按分钟／币种的实际 `marked_notional/NAV` 计算 `sum(min)/sum(max)`，不跨窗池化，不生成平均 NAV。
- 主体真实 session **48238／chunk53589f，exit0**，task `e7c70fb450b9440fbacc4fbea3e64237`：3窗／12文件完成，73.0202秒、峰值 RSS 406,355,968 B、自有 STATE 1,062,746 B。
- 独立真实 session **7464／chunkf1f6cf，exit0**，task `207f47a48c4f4ab9a02b5565f62c96aa`：同样核对 3窗／12文件，6.5769秒、RSS 401,903,616 B。最大统计差 USDT 1.13687e−13、ratio 1.74527e−13，分别小于事前 1e−7／1e−12 容差；这只是新统计一致性验收。
- 根元数据 helper **chunk949fc5，exit0**，task `1c1ac714114a4501b3aaa250a67d9e15`；报告按实际判定保存 `budget_screen_pass=false`。根报告不自认证活调用完成，后续 Git 闭合凭证保留该限制。
- 两个新科学目录合计 **1,064,080 B**，事前模块预算 5 MB；共享 cgroup RAM 4,999,999,488 B、swap0、GPU0。主体真实扫描总量 **20,178,767,678 B**，完成时刻原 JSON 为 **2026-10-02T23:18:58.237603+00:00**（同 `Z` UTC）；后续工件没有倒填到该扫描。

失败与修复全部保留：初次 PowerShell freezer 的 `H` 与内置 alias 冲突，chunk16ecf6／exit1，未写协议／未读数组；首次主体 session5870／chunk0181b5／exit1，task `18ecbb86586546348663cf660ab43e3e`，Progress AST 扫及 update 的动态 total 而拒绝，尚未创建 STATE、写 START 或读数组。原 `7cac…` 源码和 V1 协议未改。新 `3084088a…` 薄 V2 只限定 Progress `__init__` 的显示 literal，全部科学函数复用原版本。冻结协议显示文字中的 `P/TaskHash` 已独立 erratum 解释为 P/H；结构化策略 IDs、输入和数值阈值没有变化。

## 精确凭证

| 角色 | 文件 | SHA256 |
|---|---|---|
| 冻结实际协议 | [V2协议](../protocols/PUBLIC_PAIR_COMPLEMENTARITY_20261003_V2.json) | `23815084d9369972b34c44ace5be8f9a68908b7d5d23c543fe712beb456b31a5` |
| 主体实际 | [V2结果](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ACTUAL_20261003_V2.json) | `888f230b1e1437544d3bcd6192380a9c4356853e778bd61cb69dccba38841d08` |
| 独立统计验收 | [独立报告](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_INDEPENDENT_AUDIT_20261003_V1.json) | `4964e6f30b71960a49ac7a2335c66279adc23bca0c08f3f9c70adbbda6fc1a1d` |
| 根验收 | [根报告](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_ACCEPTANCE_20261003_V1.json) | `10fe6b4cf844e7f2b3be79a576c99a29a4bb303dc1659516bf6bf0e66f9ff3fd` |
| 可移植来源绑定 | [来源凭证](../reports/GITHUB_PUBLIC_PAIR_COMPLEMENTARITY_SOURCE_BINDING_20261003_V1.json) | `f94b18be86bc07915e3c3bcf67d0d1204ca64b7f2de00d2d1a69c7c31670b71f` |
| 初次 freezer 失败 | [留证](archive/PUBLIC_PAIR_DIAGNOSTICS_FREEZER_FAILURE_20261003_V1.json) | `4c4924cbd71f35a4ee97c02564d4f4e0e22d858d03b4d254a6970ca029cce423` |
| 初次主体启动失败 | [留证](archive/PUBLIC_PAIR_DIAGNOSTICS_ACTUAL_STARTUP_FAILURE_20261003_V1.json) | `38fe40c06b096c6df44d578b3c35ddba4ebfb202fc714c093b217994610ff1ee` |
| 仅显示文字更正 | [erratum](archive/PUBLIC_PAIR_COMPLEMENTARITY_PROTOCOL_DISPLAY_ERRATUM_20261003_V1.json) | `5a76f9df559709cdf89cff163e0591ea7f209915baacca241af13c409c16deef` |

已有来源、框架与公开策略能力保留。没有新模型拟合、阈值搜索、杠杆、账户指令、locked 读取或未来 OOS／长期 APR 资格。

## 模块保存

本轮科学与独立／根验收完成；Git 冻结字节门槛、模块提交及远程一致核验当前办理。后验同步凭证随下一正常模块入库。实际扫描已[发布至进度窗口](../reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_PROGRESS_SCAN_PUBLISHED_20261003_V1.json)。
