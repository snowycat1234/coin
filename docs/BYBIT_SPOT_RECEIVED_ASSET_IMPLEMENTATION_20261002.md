# Bybit 现货收到资产扣费：实现与合成验收

记录日期：2026-10-02。状态：**费用资产合成验收覆盖通过，未在本文授予经济或候选资格**。
当前仍为 `NO_QUALIFIED_CANDIDATE`。共同研究入口的集成验收和市场回放由独立凭证记录。

## 研究口径

本适配把已固定的 Bybit 普通用户常规现货费用规则应用于 Binance 分钟价格代理，
用于比较费用资产改变后的现金、净库存与收益。它是当前费用规则的反事实研究，
不是 Bybit 原生历史行情、历史账户费率或可执行成交证据。Bybit 历史价格、BBO、
lot／过滤条件、实际容量与延迟均未由本模块验证。

费用参照为 [Bybit Non-VIP profile](../protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json)，
SHA256 `d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f`。
该参照核实于 2026-10-02 13:50:20 UTC，采用公开全球常规现货每边 **10bp**；
地区／账户实际费率未核实。永续／期货 taker 5.5bp 不适用于本现货适配。
费用从收到资产扣除的来源与核实边界见 [费用标准](BYBIT_NONVIP_COST_STANDARD_20261002.md)。

## 薄适配与冻结来源

入口为 [bybit_spot_adapter.py](../scripts/investment/bybit_spot_adapter.py)：
`run_backtest(bars, minutes, targets, config=None)` 返回原 `BacktestResult` 类型；
`derivation_receipt()` 返回变换身份；`export_derivation(directory)` 保存可审查的派生源码。

没有覆盖原引擎源码。每次调用硬核对以下依赖 SHA256；哈希不符或原引擎导入路径不符即拒绝：

| 原始来源 | SHA256 |
|---|---|
| `src/quant/backtest.py` | `ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a` |
| `src/quant/execution_contract.py` | `b7fc110d84240233611e2f7e7360c1b7cc5c92308f842a796560964db33f97d1` |
| `src/quant/execution.py` | `8d886164668f3ae4b0be47f9cc04c99a78ce85e8f96fe10d6a04d6bd89addd3b` |

适配复制原 `run_backtest` 的 AST，只接受 12 个精确唯一语句锚点和 4 个精确唯一字典锚点，
再为派生函数赋独立名称、编译至复制的 globals 字典。原模块 namespace 不被修改。
变更清单记录每处旧／新 AST 哈希与源码；不满足精确匹配不尝试宽松补丁。

| 允许的变更 | 数量 | 内容 |
|---|---:|---|
| 语句 | 12 | 买入单位净值与成本、目标分母、单资产／总仓位分母、现金买入上限、卖出净库存上限、费用资产计算、现金更新、净库存更新、保留正 dust、买入 cycle 成本、订单 gross 成交数量 |
| 字典 | 4 | 订单初值数量、成交新增结算字段、成交 schema、订单数量 schema |

`execution.py` 中原有的三条 `commissionAsset` 余额更新语句也按唯一 AST 锚点提取，
编译为纯余额函数。没有创建 `ExecutionEngine`，没有引入数据库、网络或账户执行。
原费用合同哈希仅绑定原时序与风险来源；新费用资产行为具有独立 adapter、协议、
profile 和派生 AST 身份，不能把全部费用行为称为旧合同不变。

## 现金、数量与风险定义

令 gross 成交数量为 `g`，成交价 `F`，当时 mid 代理价 `M`，费率 `r=0.001`。

| 方向 | 现金变化 | 实际基础币变化 | 费用资产／数量 | 费用 USDT 估值 |
|---|---|---|---|---|
| 买入 | `−gF` | `g(1−r)` | BTC 或 ETH／`gr` | `grM` |
| 卖出 | `gF(1−r)` | `−g` | USDT／`gFr` | `gFr` |

买入费从基础币扣除，不能再从现金扣一次等额 quote fee。卖出数量不得超过实际收到的净持仓。
订单／成交 `quantity` 和新增 `gross_quantity` 都表示 gross 数量；lot、成交容量按 gross 订单计算。
`position_delta` 才是净持仓变化；`cash_delta` 是真实现金变化。

新增成交字段为 `gross_quantity`、`position_delta`、`cash_delta`、`fee_asset`、`fee_amount`、
`fee_USDT_mid`。旧数值字段 `fee` 保留，等于 `fee_USDT_mid`；旧 summary 数值键保留。
基础币费用按该笔成交时的 `M` 换算，不能将 `fee_amount` 的 BTC／ETH 数量直接加到 USDT 费用中。

买入每 gross 单位的净估值为 `m_net=M(1−r)`，NAV 成本为 `c=F−m_net`。
目标权重 `w` 的数量分母为 `m_net+w*c`；单资产上限／总仓位上限的分母为
`m_net+cap*c`。分子沿用原目标美元差额或上限净值差额。
现金可买上限为 `cash/F`；其他币因本次 NAV 下降受到的上限约束仍为
`max(0, (NAV−other_position_value/max_weight)/c)`。
卖出沿用原 quote 扣费成本和目标解法，但 gross 数量严格受实际净库存限制。

原时序、风险窗口、容量、holding、pending／到期／重试和标记估值逻辑继续复用。
手续费资产改变不产生新的成交能力。被动价格变化带来的权重漂移也未通过本适配加入新再平衡策略。

## Cycle、dust 与 gross shadow

买入 cycle 的成本只增加已支付 `gF`；卖出 proceeds 增加 `gF−gFr`。
cycle 的 informational fee 仍记录成交时 USDT 费用估值，不再作为买入现金支出重复扣除。

卖出 gross 数量按订单 lot 向下取整；若浮点取整结果超过净库存，再减少一个 lot。
正的 sublot 库存保留终端 MTM，不使用旧的绝对 `1e−10` 清零阈值。负库存触发错误。
合成验收覆盖了约 `1e−11` 基础币残余，未把它删除或假记为完整 round trip。
未可行成交的终端残余保持实际估值。

净 NAV 为 `cash + Σ(net_position*M)`。独立 gross shadow 使用**同一净收到库存路径**：
每笔令 `shadowcash -= position_delta*M`，并将相同净库存按当时价格标记。
因此 `gross_shadow_NAV − net_NAV` 等于累计成交时 `fee_USDT_mid` 加 gross 数量的
execution cost。`execution_cost = g*abs(F−M)`。

保留的 `gross_pnl_before_costs` 是这一净库存路径的成本加回诊断；
它不是把买入 gross 数量全部持有的无费用反事实利润。
summary 的 `gross_pnl_definition` 与 `fill_time_cost_addback_pnl_diagnostic` 明确该口径。

## 两次真实合成验收与复用范围

所有测试使用 hpc_linux 的已接受 clean 环境，通过 bounded／进度包装器执行。
环境锁 SHA256 为 `97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6`。
共享 RAM 上限 5GB、swap0、GPU0；无行情读取、模型拟合、locked 消费、账户密钥或真钱订单。
运行绑定的 Git HEAD 为 `d7aaeb4b1ec5e04908c341a8ab6a569ff81bfde1`，具体命令、源码、
环境、STATE 和 JUnit 哈希均在各报告中。

| 运行 | 实际任务／退出 | 结果与复用 |
|---|---|---|
| V1 | session `8781`，task `5fa4477239db4695a19cf6c8d6603ec4`，exit **1** | 5 case 中 3 PASS、2 FAIL；保留真实失败与源码快照，V1 整体不是 PASS |
| V2 | session `1802`，task `7a1b64de0f08489eb728f9063c66eef4`，exit **0** | 只复测两个失败 case，2 PASS、3 deselected |
| COMPOSITE | task `18c634c150004a6493bee87a34ae5c98`，工具实际 exit **0** | 只读 JUnit、退出记录、报告和源码，复用 V1 三 PASS 与 V2 两 PASS；不是单次五 case 全新运行 |

V1 两项失败均发生在独立等价汇总接近零的比较：约 `1.18e−12`／`1.83e−12` USDT 的
float64 取消误差超过 pytest 默认绝对 `1e−12`。此前逐笔费用、现金、净库存、净值、风险
与数量断言已通过。修复只把该汇总比较设为初始 10,000 USDT 对应的 16 ULP，
即绝对 `2.9103830456733704e−11` USDT。没有放宽数量、费用、现金、NAV、caps 或 dust 断言。
CLI 增加用例选择以避免重跑已通过部分。

COMPOSITE 实际核对：费用实现 `_smoke_main` 之前全文精确不变、16 处变更记录精确不变、
派生 AST 与导出源码精确不变，测试差异仅上述汇总容差。

| 凭证 | SHA256 |
|---|---|
| [V1 失败报告](../reports/fast_research/BYBIT_SPOT_FEE_ASSET_TINY_20261002_V1.json) | `494994ec5a5ad52216936b0ce4388b7dc0d30ca943a96214c548be98a2941607` |
| [V2 两 case 复验](../reports/fast_research/BYBIT_SPOT_FEE_ASSET_TINY_20261002_V2.json) | `933236cc26141df1f4b6cc9b763114baa45ce7cce4e474e12b7b49d909abd04c` |
| [COMPOSITE 五项覆盖](../reports/fast_research/BYBIT_SPOT_FEE_ASSET_COMPOSITE_ACCEPTANCE_20261002_V1.json) | `850b8a2e984bd00d33c396dca43af6b6a2f0d55c327eff3c29fc2f238f63d2b0` |
| V1 JUnit | `aa2257e030155da3dd8278d865afda7c7c8293d6d651bc80ec877ef3efb40840` |
| V2 JUnit | `2b79b44ca6f94e9a515defedc331afe5bd90dd2baa1734175ddedeaebea480f8` |

## 当前可审查身份与归档

| 工件 | SHA256 |
|---|---|
| [当前 adapter](../scripts/investment/bybit_spot_adapter.py) | `8c8852bf70813ada5720c210f50c9038a5ecaadee1b4f38b77a71aa9e8b038ca` |
| [当前合成测试](../tests/test_bybit_spot_adapter.py) | `a786332e6780a24a12db4fa970261bc3265bd61c565f1d64a6ed6be636fa9998` |
| [适配协议](../protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json) | `c8441169d3b42a651c4ae37e11d5eb53943f9b0e0172e2596644fd7cb2fa4912` |
| 派生引擎 AST | `39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73` |
| 导出派生源码 | `a33c4f392c033d44224be5f64a42456b529e973d9af0925c8a454043f2762a8f` |
| [COMPOSITE 元数据操作源码归档](archive/BYBIT_SPOT_FEE_ASSET_COMPOSITE_RECEIPT_SOURCE_20261002_V1.py) | `733cebd9c609b360fee2dc77dd8550ad49813a103f01a8b75d0ca42ac223ee60` |

V1、V2 各自的源快照、RUN_BINDING、START、JUnit、派生源码保存在对应 D-hosted STATE；
原失败报告和原字节不覆盖。元数据 helper 的纯源码已精确归档，原 STATE helper 保留。
合成会计兼容性不能证明长期净 APR，也不能替代共同入口、真实市场 proxy 账本及独立审计。
