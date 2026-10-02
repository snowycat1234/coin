# 条件双腿账户：固定 90 日时间外推（2026-10-03）

## 本轮六项科研结论

1. **当前长期 APR 候选：NONE。** 全平与配对减仓均只保留为条件研究能力，本模块接受完整账本与独立数学核验。
2. **净收益证据：** 2025-12-01 至 2026-03-01 前，两个独立初始化的 10,000 USDT 账户各净赚 **3.988973 USDT（90 日 +0.0398897%）**。描述性复利年化为 +0.1618736%，长期净 APR 仍为 `NOT_EVALUABLE`；与旧 122 日账户分别报告，不拼接为在线曲线。
3. **最大阻碍：** 收入相对成本的余量很薄；资金费 fraction 单位、事件可见性与归属、charge mark、真实买卖价差和原生平台结算仍未认证。采用 Bybit 普通费率假设，价格与率来自 Binance 官方档案，不能称为 Bybit 原生收益。
4. **最重要发现：** 本期没有触发减仓或风险全平，两政策分钟及日 NAV 文件字节 SHA 相同，净差为零；因此本期没有新增的减仓效果证据。2 月带正负号的资金费与扣费前结果均负，收入机制本身会随时间变化。
5. **下一高价值问题：** [D032](RESEARCH_DECISION_LOG.md) 已事前登记唯一过去 7 个完整 UTC 日的非正持有资金费永久退出假设；8 天持有门槛、观察窗口、每日决策时刻与一天发布延迟假设以 D032 为准。在完整旧 122 日与新 90 日分别检验，资本、成本和原风险规则保留。仍须先冻结执行协议，再运行新数学；不选 2 月、不调参或重跑旧控制。一天发布延迟仍未认证，不能把 `calc_time` 当成已认证实时可见信号。
6. **暂停及重开：** 暂停该固定配方的投资资格与继续参数搜索；来源与账户能力保留。重新考虑投资资格需闭合原生输入、单位/归属、执行成本与独立时间证据；减仓机制可在事前固定且实际触发风险上限的区间重开。资金费退出机制仅在新协议冻结后开展，不因本期两政策相同而删除整个 carry 方向。

## 共同账户与实际结果

固定全期 90 日，BTC/ETH；24 个已接受输入文件，每币 129,600 分钟，540 个实际来源资金费事件（每币 270）。不假定 8 小时事件数；源计数来自已完成来源 QA。该日期段曾用于既有 Spot 研究，仅是开发时间外推，不能称为真正未见的 OOS。首个闭合分钟发信号，下一闭合分钟加 1μs 成交；最后允许闭合分钟加 1μs 强制退出。最后价格属于 2 月，不读取 3 月行情或锁定历史。

两账户资本均为 10,000 USDT，每币每腿初始名义 1,250、隔离余额 1,250；总毛敞口触发线 0.6、每币两腿 0.3、隔离权益 625 触发全平，非正隔离权益直接拒绝。PAIR_TRIM 仅在敞口触发后减至信号 NAV 的 0.25 配对名义，其他规则保留。上限是延后成交的退出触发器，不保证成交时绝不越线；共同上限也不能普遍称为相同实际风险。

| 指标 | ALL_FLAT | PAIR_TRIM |
|---|---:|---:|
| 净 PnL / 90 日净收益 | +3.988973 / +0.0398897% | 相同 |
| 按同一实际成本数量加回费用的 gross PnL | +17.351509 | 相同 |
| 手续费 / 假定价差 / 假定滑点（USDT） | 6.574776 / 3.393880 / 3.393880 | 相同 |
| 总成本 / 签名条件资金费（USDT） | 13.362536 / +17.573984 | 相同 |
| Turnover / 成交笔数 | 0.848470 / 8 | 相同 |
| 来源事件 / 持有资格事件 / 排除事件 | 540 / 538 / 2 | 相同 |
| 配对减仓次数 | 不适用 | 0 |
| 分钟及全部观察点最大回撤 | 0.1982046% | 相同 |
| 日频最大回撤 / 描述性年化波动 | 0.0941904% / 0.2203314% | 相同 |
| 最大总毛敞口 / BTC / ETH 两腿毛敞口 | 0.552721 / 0.270340 / 0.287428 | 相同 |
| 最低 BTC / ETH 隔离权益（USDT） | 1,144.442897 / 1,060.588020 | 相同 |
| 终端 Spot、short 数量与条件 dust | 均为 0 | 相同 |

假定成本固定为 Spot 每边 10bp、perp 每边 5.5bp、每腿往返价差 8bp、每边滑点 4bp。Gross 是原成本数量和成交时刻的成本加回，不能解释为免费重定尺寸的账户。资金费按严格持有区间、严格过去的闭合 mark 代理记账，包含所有正负原始事件；入场前两事件未计收入。±5 秒边界见证为 0，但不认证真实归属。没有账户密钥、订单、模型拟合或 GPU。

## 连续月度归因

| 月份 | Gross PnL | 净 PnL | 带正负号的资金费 | 费用+价差+滑点（USDT） |
|---|---:|---:|---:|---:|
| 2025-12 | +9.916928 | +2.050373 | +9.653125 | 7.866554 |
| 2026-01 | +11.311882 | +11.311882 | +11.110057 | 0 |
| 2026-02 | −3.877301 | −9.373282 | −3.189198 | 5.495982 |

两政策月表完全相同。持仓和 NAV 连续传递，月末不重置现金或重开仓；月净值严格加总至全期净收益，reconciliation error 为 0。1 月贡献大部分正净收益，2 月扣费前已负，费用进一步压低终值；事后排除该月会改变本实验。

## 验收、失败与资源

唯一新合成用例只验证新日期/来源/端点和两政策 context，`1/0/0/0`，没有重放旧金融测试。两实际任务真实 exit0 后，独立 V3 重构两账户：每账户 24 输入、129,600 分钟、540 原事件、90 日、3 月、8 成交；最大现金误差 1.0477379e−11 USDT，比例误差 1.2798651e−12。验收范围是条件数学，单位、原生账户、unseen 和长期 APR 均未放行。

| 实际任务 | Host / task ID | 退出 |
|---|---|---:|
| 唯一 tiny | session50927 / `8aa58c7b8b7a46099ab1704222ccd5d4` | 0 |
| ALL_FLAT | session73766 / `1e3ca61feca046b58bdf2e373b30c882` | 0 |
| PAIR_TRIM | session33399 / `c826e624cd7a42f586ff60cae275beff` | 0 |
| 独立 V3 | session12463 / chunk17c029 / `289b34e535f043f395b75c6dfd04267d` | 0 |
| 根验收 | chunkc5523e / `98198248313245c0bec42013553492c9` | 0 |

独立 V1 因金融区段 anchor 定位失败（0 个账户完成，task `87b37512cedb45039b04258398c35e55`、exit1）；V2 在一个账户完成后因 PAIRCOUNT literal guard 失败（task `66e7de4ddf7a46fcad59a89c219510cb`、exit1）。两份原失败报告与源码保留；V3 只修正独立核验的区段/周期绑定，没有修改已完成生产账本或收益。实际任务不是预先宣布的 PASS。

ALL_FLAT / PAIR_TRIM 主进程分别 53.13 / 52.50 秒、RSS 449,466,368 / 447,397,888B；两份输出合计 12,431,046B。独立 V3 35.94 秒、RSS 117,313,536B。共用 RAM 硬限 4,999,999,488B、swap0、GPU0；源行情留 D 盘、输出保留 STATE，均不入 Git。根验收只检查小凭证与新输出字节 SHA，没有重新计算金融或来源 QA。

## 精确证据与复现入口

以下 SHA256 均指原字节；实际命令、冻结来源与四个输出绑定见各报告。

| 凭证 | SHA256 |
|---|---|
| [共同协议](../protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json) | `84e14795c2622067b42c978225525773a06ecda3b8661f37f62cbc369609c3a3` |
| [24 输入来源视图](../reports/fast_research/CARRY_90D_SOURCE_VIEW_20261003_V1.json) | `d167109731945e06aea2134f1eb495ab5647f68b70fc288ab2d23a03c7a1ee29` |
| [Tiny](../reports/fast_research/CARRY_90D_PERIOD_TINY_20261003_V1.json) | `85c55fc47d04e18324af8fc141ed229f15d9aaf4340d217a2c62ef691cd38984` |
| [ALL_FLAT actual](../reports/fast_research/CARRY_90D_ALL_FLAT_ACTUAL_20261003_V1.json) | `5f2f117ce7d8c2230ddb1981762a8262fe9699c865cc83ace524125e98c3e1dc` |
| [PAIR_TRIM actual](../reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json) | `dd42d50cff88f1d04a952cbe92f01af2bcb3413c6ad30b0371f625972f9f3a71` |
| [独立 V1 FAIL](../reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json) | `3881af3d02f6870b17d4c06a75f5d5db4b1f3067aa6a787482db396ebab3c2d5` |
| [独立 V2 FAIL](../reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json) | `13df62fdfeebd67fad6ee8448a4fa7b7cfa1a00cb0babdcb2886c6a44556922f` |
| [独立 V3 PASS](../reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json) | `fb020128a4c2e0c7be22bb5b54e5a47a651a40a91bd77c69a57d8b79294ba504` |
| [根验收](../reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json) | `95dbe4da78b7c0114321756ae9e289f094fc2b1a5066f14c54f6c65b995feed4` |
| [闭合来源绑定（109 项冻结 ROOT 来源）](../reports/GITHUB_CARRY_90D_SOURCE_BINDING_20261003_V1.json) | `ec6055d9a3ac9b1650857dad74bd41e02bc681b94d987cfa8741e32000d7d95f` |

[薄周期 adapter](../scripts/investment/conditional_carry_90d_period_adapter.py) SHA `a88b3d5d551216c34ab66abad07ecc4502c065de4c0eb6e9fdd0aa4a0c919574`；[唯一新用例](../tests/test_conditional_carry_90d_period_binding.py) SHA `eddf89063c7d58a7a50d1ff92cf5f6887546e79bbf82a9ee13ec717c06fdaf65`。复现使用原 `--research --policy ALL_FLAT|PAIR_TRIM` 命令、同协议与新的独立 STATE/output，经进度包装与 bounded clean environment；本次文档编写没有执行该命令、读取行情数组或重复绿测。
