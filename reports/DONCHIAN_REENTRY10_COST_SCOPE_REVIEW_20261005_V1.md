# D070 Reentry10：成本与产品边界独立复核

日期：2026-10-05。复核者：`active_allocation_test` 子 agent。结论：**在已声明的开发筛选、跨场所价格代理和固定成本/资金费情景内，未发现需要重复 D063 修复或阻止本次固定 D070 对照的新成本 blocker。原生 Bybit 成交、历史费区、实际资金费单位与长期投资资格仍未获认证。**

## 复核范围

静态读取用户两份附件、仓库逐字节副本、当前成本适配器/账户/活动 runner、D063 已闭合验收与失败记录、D070 V2 事前协议。父任务提供接手 HEAD `1b3987e`；本复核未调用 Git 重新认证当前 HEAD。D063 推送凭证中的 `local_HEAD` 与 `remote_main` 同为 `29393019aed0e1a3b643877eaf97947f38c25b0c`，这是既有凭证，非本次重新查询远端。

本复核未运行 Python、测试、市场回放、QA、API 或采集；未查看尚在运行的 D070 新账户载荷；未改源码、协议、registry 或旧证据。仅新增本报告。复核者编写了 D070 新机制反例测试，故不是该测试的独立作者；以下成本复核依据是另一条 D063 账户证据和当前账户代码，而非重复自证该测试。

输入附件与 `docs/input_evidence/` 副本的 SHA256 相等：

| 输入 | SHA256 |
|---|---|
| COIN_COST_AND_STRATEGY_CORRECTION_20261004.md | `0e9d51841b40f136b1ab9785fc2f80e6558ce95d9de5da6d212cb313660e04cb` |
| BYBIT_USER_FEE_SNAPSHOT_20261004.json | `a406d4bd0e47ff4ae4895fda0a2f2698b5763667d82b22b7f264d6220e27e8bd` |

当前 `bybit_cost_inputs.py`、`perpetual_directional.py`、`perpetual_account.py`、`multi_asset_portfolio.py` 的实际源码 SHA 均与 `protocols/DONCHIAN_REENTRY10_20261005_V2.json` 绑定相等。协议本次读取 SHA：`926d86978101436fdeb591070e4eee51527fae6b0a64193ee6861e1ebdb349ce`。

父任务随后报告实际启动纠正：V2 市场命令漏掉 `--pool-id LIQUIDITY_TEN`，启动了默认两池；父任务只对自有 PID 发出 SIGINT，task `31b55392..` 实际退出 -2/host1，留下 2 个完整 TWO_ASSET 账户及第三前缀，耗时 198.99s、42.949MB。该尝试必须保留，不能计为十币四账户完成。V3 将显式绑定十币并更正 CLI，既有新测试 V2 已通过且不重跑，生产代码未改。本报告未读取尚未完成的 V3 冻结/新结果；下面的固定十币结论属于研究口径，最终采用必须核对实际 V3 完整运行，不能用 V2 协议替代启动证据。此启动错误不改变 D063 成本复核。

## D063 已完成的必要成本纠偏

1. **5.5bp/side 并不是待修费用错误。** 当前标准 crypto perpetual taker 为 `.00055`。BASE27 为每腿 `5.5+4+4`；STRESS43 为 `5.5+8+8`。27/43bp 包含双边手续费及摩擦假设，不能称为官方手续费。
2. 通用配置允许有限、非负摩擦与合法费率；低于旧 4bp 摩擦或改变费率时必须显式给成本来源 context。旧 BASE27/STRESS43 数值保留供历史复现。新适配器核对百分数、fraction、bp 同一性和 roundtrip 算术。
3. `snapshot_cost` 要求明确 exchange、USDT linear perpetual、TAKER、各 symbol 的显式且同质 fee zone、来源 SHA 与时间范围。不会由 `BTCUSDT` 名称推断现货/合约、费区或 maker。MNT 折扣保持关闭。8 类费率保存在附件里，不代表活动账户支持 8 类产品。
4. 逐腿手续费基于**实际成交数量与成交价**；当前账户数量为 base、合约乘数为 1。反手拆平仓/开仓，两腿各计费；部分成交/reduce-only 仍走实际账本。成交价已包含方向正确的执行损失，报告拆为 half-spread/slippage 时不再扣一次。非等额摩擦按配置比例拆分，零摩擦要求零执行损失。
5. 当前交易入口、首次 CASH 与缓存 CASH 都使用正常 cost 入口；缓存只接受 NAV10000、无交易/无资金费/无持仓的已知现金账户，并重建成本摘要。快照恢复核对配置、每腿费用及实际执行身份；旧已知 RT27 元数据迁移不能改变旧 journal。
6. D063 验收明确是账户身份与人工合成验证，**不是市场校准**。主测试 V1 实际失败被保留，V2 实际 7 项通过；closing 新测试实际 1 项通过。低摩擦 `2+1` 与 `0+0` 的真实运行仅属人工合成，不是可采用的历史成交成本。

相关证据：

| 工件 | 本次读取 SHA256 / 口径 |
|---|---|
| reports/fast_research/COST_PROVENANCE_ACCOUNT_ACCEPTANCE_20261004_V1.json | `25496eec756a7fe3dd61b1e127c43c9c6428b7a0b8615f8056a9812bfcd5baed`；账户身份/CASH/合成通过，非市场校准 |
| reports/fast_research/COST_PROVENANCE_CLOSING_SYNTHETIC_20261004_V1.json | `e46849288e9ad9d710f424b8698e894f8a787d7008ffb9101a0b4ed4b6b583fe`；task `0da14db906614d62bef821e4f62681e3`，exit0，1 项合成通过 |
| reports/COST_PROVENANCE_INDEPENDENT_REVIEW_20261004_V1.md | 原静态复核包含最初成本下限、RT 标记、比例拆分、恢复及 CASH 问题，最终正常入口已修正 |

附件还包含策略节奏、机会预算与连续账户研究要求；不能把这些全部称为 D063 已完成。随后 D064/D065/D067 的固定日线、连续账户及单因素对照属于独立研究版本。本次只核这些既有成本修复仍在 D070 活动链路中。

## 仍 UNKNOWN 或未接入的能力

| 项目 | 当前事实 | 对 D070 的限制 |
|---|---|---|
| 历史账号费率/费区 | 用户快照没有截图时刻或生效起止；当前账号情景不能证明 2024–2025 历史账号费率；十币历史费区未认证 | D070 沿用统一标准费率情景，不得声称每币历史 native Bybit fee 正确 |
| 历史可成交价与摩擦 | Binance 来源与 Bybit 成本组合；分钟 open 作成交 mid 代理，4+4/8+8 非历史 BBO/冲击校准；参与率/尝试次数仍是执行模型假设 | 不得把净收益解释为真实 Bybit 可执行结果；现价 BBO 不能追认历史盘口 |
| 产品/数量/保证金规则 | 账户明确 linear USDT/base/乘数1/逐仓1x；native filter、适用历史最低单量、数量精度、MMR/清算与盘中跳空边界未完整认证 | caps 与会计正确性不等于真实历史未清算保证；不得声称原生规则齐全 |
| 资金费单位与可得性 | `RAW_AS_FRACTION=1` 与 `RAW_AS_PERCENT=.01` 都是未确认情景；报告 `unit_certified=False`、publication 未认证；官方 parity 单次请求 HTTP451 已停止 | 四个情景都须保留；不能按收益择单位，也不能给出一个确定净资金费/净 APR |
| Bybit 官方合约输入 | 既有 instruments 单次探测 HTTP403 已停止，未重试/绕过 | 只阻止依赖 native 产品认证的结论；不授权本次再请求 |
| Maker/其他产品 | maker 费率仅记录；活动成交角色 TAKER。Spot/TradFi/options 被新适配器拒绝；创新/盘前费区仅显式假设且账户仍 linear perpetual | 无 maker execution/盈利证据，不能自动扩产品或交易权限 |
| 将来认证接口 | 当前 cost context 明确要求 `native_fee_zone_certified=False`、`historical_execution_certified=False`；不是已有自动升级到认证数据的入口 | 未来有合法新证据时可正常修改活动接口并另建协议；现在不能把 false 改 true 后自称已认证 |

资金费失败工件 `FUNDING_SEMANTICS_PROBE_20261003_V2.json` SHA `54febc06b7815e521715c8d70c3e930929a489c7e2a84d1ddae9507a03e4da4d`；Bybit 失败工件 `BYBIT_PUBLIC_SPEC_PROBE_20261003_V2.json` SHA `e9af503294fd147d31ca936042bd1a9c5ceca2aeba1c3b830cef08947b99084f`。失败与访问限制均保留，不从量级或盈利猜单位。

## 本固定研究是否被阻塞

**不阻塞有限的 D070 开发机制比较。** 协议使用同一 accepted 数据、同一 303 日连续共享 10000USDT 钱包、同一十币顺序、ACTIVE_EQUAL、past30 协方差与 abs.3/gross.6/逐仓1x；相对已存 D067 控制只改变退出后 armed reentry 的 prior20→prior10，首次入场 prior20/SMA200、exit10、成本、资金费两解释及末平仓尝试不变。应分别核对 BASE27/STRESS43 × 两个资金费解释的四个新账户完整回放、末持仓、独立账本与经济桥，不从旧 NAV 后验缩放。

同成本配对**不会使不确定成本完全抵消**：reentry 改变数量、时点和换手，因此手续费、摩擦与资金费差额需要真实新账本；压力情景稳定性只能支持该假设下的机制判断，不能认证实际交易成本。

**阻塞的声明**：native Bybit 回测/成交、精确历史手续费归属、已确认资金费净收益、真实安全清算、长期可执行 APR、独立投资优势与真钱采用。本报告没有读取或给出正在运行的 D070 收益结果。候选保持 `NONE`，资金选择保持 `CASH`；所有已看历史继续为开发筛选。

本轮判断：保留 D063 成本接口与当前四情景，不重复修复、不为了盈利降低摩擦；等待已启动 D070 的完整市场、独立资金核对及诊断闭合，再依据实际价格损益、交易成本、资金费和实际风险作研究取舍。
