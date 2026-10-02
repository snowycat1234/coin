# 公开策略90日时间外推 · 2026-10-02

## 当前判断

**盈利研究主力：NONE；NO_QUALIFIED_CANDIDATE。** 固定2h在新90日三成本下均亏损，按D014预先条件降为防御参照。Cash的0收益优于全部四个风险方向。比较与账本能力可接受，盈利假设不能延续；没有长期净APR或真正unseen证明。

原2025Aug–Nov的122日2h净收益+0.6580%，新Dec–Feb为−1.8175%（30bp）。它们是分别初始化的账户，不拼接成在线策略曲线，也不事后挑1h作为盈利赢家。

## 固定共同范围与净收益

2025-12-01..<2026-03-01连续90日，每方向/成本独立10,000 USDT，5×3共15账户；月间现金、持仓和NAV连续传递。预热Oct31..<Dec1为31日。费率单边10bp、滑点4bp、全价差2/4/8bp，对应往返30/32/36bp；实际费用按成交量计。表为期间净收益%，没有年化资格。

| 方向 | 30bp | 32bp | 36bp |
| --- | ---: | ---: | ---: |
| Cash | 0 | 0 | 0 |
| Spot持有 BH | −5.5734 | −5.5723 | −5.5758 |
| 波动管理持有 VM | −5.5815 | −5.5975 | −5.6335 |
| Jesse Donchian 1h port | −0.7497 | −0.8335 | −1.0024 |
| Jesse Donchian 2h port | −1.8175 | −1.8684 | −1.9709 |

三成本账户受费用后可买数量、lot舍入与后续持仓影响，不能假定完全同qty；BH的32bp微小改善不代表成本有益。

## 30bp：收益、成本与实际风险

金额单位USDT；成本依次fee / spread / slippage。gross用同一costedqty归因，非重优化零费策略。turnover沿原引擎口径，波动率为日收益实际年化波动，MDD取完整分钟NAV。

| 方向 | gross | net | 成本三项 | turnover | fills / RT | 实际波动% | 分钟MDD% |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Cash | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 | 0 | 0 |
| BH | −553.96 | −557.34 | 2.26 / 0.23 / 0.90 | 0.2282 | 4 / 0 | 10.2553 | 8.6740 |
| VM | −533.23 | −558.15 | 16.62 / 1.66 / 6.65 | 1.6726 | 145 / 0 | 11.0005 | 9.3794 |
| 1h | +52.62 | −74.97 | 85.06 / 8.51 / 34.02 | 8.4998 | 120 / 27 | 6.1875 | 3.2524 |
| 2h | −104.26 | −181.75 | 51.66 / 5.17 / 20.66 | 5.2092 | 65 / 15 | 6.6013 | 3.7207 |

2h成本77.49低于1h的127.59，节省50.11；gross却少156.88，净结果差106.78。低换手保留，gross优势反转：2h问题已经涉及signal/regime，不能仅归咎费用或机械延长到4h。

| 方向 | 实际峰值总暴露% | BTC / ETH峰值% | 末尾持仓notional USDT |
| --- | ---: | --- | ---: |
| Cash | 0 | 0 / 0 | 0 |
| BH | 19.9192 | 9.7433 / 10.3643 | 860.86 |
| VM | 34.0189 | 16.8120 / 17.2282 | 613.47 |
| 1h | 33.9430 | 24.9043 / 24.3577 | 660.26 |
| 2h | 34.1480 | 30.0163 / 24.2896 | 浮点dust≈0 |

共享10%波动目标、30%单币/60%总目标不等于相同实际风险。只在intent变化时再平衡，2h BTC被动漂移至30.0163%。BH/VM/1h末持仓真实计MTM，尚未全清仓；不能补虚假的免费平仓。RT为已闭合roundtrip，不等于所有交易已结束。

## 月度机制归因

下表gross / cost / net为USDT，cost含三项。全部15账户按31/31/28日完整MTM与90日金额加总相符，无月边界重置。

| 月 | 1h gross / cost / net | 2h gross / cost / net |
| --- | --- | --- |
| Dec | −57.55 / 59.59 / −117.14 | −184.79 / 38.90 / −223.69 |
| Jan | +159.64 / 41.87 / +117.76 | +180.08 / 30.22 / +149.86 |
| Feb | −49.47 / 26.12 / −75.59 | −99.55 / 8.37 / −107.92 |

两public方向仅Jan gross为正，正gross月贡献集中度均100%；BH/VM三个自然月gross全负。Dec末1h/2h约1631/1634 USDT持仓传入Jan。2h在Dec与Feb的gross损失更大；现有月度证据不能直接证明退出慢是原因，entry选择和物理回看长度也改变了。

## 来源、失败和独立核验

复用Oct2025..Feb2026 BTC/ETH十份封存Spot分钟文件，151日/币、434,880来源行；预热+交易衍生视图348,480行。指定hash/Parquet metadata/旧日历凭证直接复用。[A05预检](../reports/A05_RESEARCH_PREFLIGHT_ACCEPTANCE.json)fold7/8与[A06实际fit](../reports/A06_NONLINEAR_RESEARCH_ACCEPTANCE.json)已消费Dec–Feb，本轮是已见开发历史chronology screening。2026Mar1..<Sep1锁定行情未启封。

V1退出1、保留3个Cash部分工件：Feb末合法分钟的exclusive close=Mar1触发旧signal时间守卫。V2只截取signal close≤最后decision；完整执行分钟、末尾估值、规则/成本不变，新增边界反例实际退出0。V2真实session4852退出0，15/15完整；此修复失败不算经济阴性。

首次独立审计V2在账本前因`Fold input bytes`失败（0/15），旧失败保留。R2 session88702退出0、15账本资金/成本/时间/capacity/NAV/月度/终端核验通过，限定`PASS_ACTUAL_PROXY_LEDGER_ACCOUNTING_AND_SCOPE_WITH_NONPORTABLE_IPC_LIMIT`。准确Parquet SHA、完整UTC/schema及其自身IPC roundtrip值核验通过；原运行内存fingerprint仍 **NOT_REPRODUCED_NONPORTABLE_IPC_BYTES_NO_PASS_CLAIM**，不宣称原内存字节或值重现。

成交使用分钟OHLC/quote-volume代理，不是真BBO/深度或真实fill证明；复用原MIT Jesse hook，COIN账户/风险/执行port不代表原平台收益。长期APR、交易资格、真钱均未接受。

## 复现凭证与资源

入口为`compare_simple_strategies.py --research --protocol PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json`；完整冻结命令在[实际报告](../reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json)的`binding.exact_command`。复现必须用新的STATE/output，不能覆盖旧报告。绑定HEAD `1519a61`；原session/task及失败均留存。

- [协议V2](../protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json)：`82996c12…`；[来源](../reports/fast_research/PUBLIC_STRATEGY_CHRONOLOGY_SOURCE_REUSE_20261002_V1.json)：`388d3be0…`。
- ACTUAL SHA `7e47d20fb71a8c6f87cc5b1adc26a2e031bb9bdbd8cf1a64d61ab6b4ac25642c`；[退出/月度](../reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_EXIT_MONTHS_20261002_V2.json) SHA `86dbe235e2f3cdb96a0e89ab653506aa9f13d14681d6e2905e1be23af20179cc`。
- [独立R2](../reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2_R2.json)：`32c2d897…`；[首次独立失败](../reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2.json)：`d9a5ec7d…`。
- [R2实际退出/归档](../reports/fast_research/PUBLIC_STRATEGY_90D_AUDIT_ACTUAL_EXIT_AND_CODE_BINDING_20261002_V2_R2.json)：`a45fcefa…`，原失败与修复checker均按字节保留。
- 原工件目录：`/home/xflops/coin-state/public-strategy-continuous-90d-actual-20261002-v2`，真实耗时80.30s、producer RSS632,123,392B，报告时工件73,832,601B。共享cgroup峰值3,236,868,096B是累计峰值；cap4,999,999,488B、swap/OOM/GPU=0。
- D项目+VHD实际19,382,577,169B，扫描结束**2026-10-02 13:30:46.612451 UTC**；这是该时刻值，不冒充实时磁盘。

## 下一项高信息价值问题

建议只做固定2h entry + 原1h exit机制challenger：保留2h prior20bar/SMA200入口，持仓按原1h prior20bar下轨退出，共同风险/成本/来源。它同时改变exit检查频率和回看40h→20h，应称联合exit时间尺度诊断。先看gross恢复、月度负尾、分钟MDD与额外成本，不能仅看turnover下降。当前未启动；不做4h/HPO、降费或加杠杆。

固定1h/2h盈利假设暂停，保留防御参照；reopen需预登记的小机制实验给出扣费后改善并获得更多时间外推支持。比较能力保留，禁止因一个窗失败删除整个突破能力。

## 根验收与用户新增平台标准

[根验收](../reports/fast_research/PUBLIC_STRATEGY_90D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json)
SHA `865eea7de746b3c21e09dca197c88ff5b7e1bcbf07c5c8ae25df30d278020740`，限定已见90日代理资金账本与逻辑来源；不接受原内存IPC指纹、长期APR或交易资格。
V1部分失败和初次checker失败均保留，实际/独立宿主exit0与wrapper task退出绑定。

用户随后指定Bybit普通用户标准，[费用登记](BYBIT_NONVIP_COST_STANDARD_20261002.md)按官方表核实。
crypto Spot仍10bp/side，因此上述旧费用数值不变且不重复运行；费用资产规则尚不同。
D016先补最薄Bybit费用资产兼容，再继续上述固定hybrid诊断；永续5.5bp不能替换Spot费率。

精确入口、环境与源哈希在实际报告中。需新STATE/output复现时，在hpc_linux下运行：

```bash
scripts/with_task_progress.sh --title '固定90日策略比较复现' -- \
 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python \
 scripts/investment/compare_simple_strategies.py --research \
 --protocol protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json \
 --experiment-id USER-REPRODUCE-90D-NEW-ID \
 --run-dir /home/xflops/coin-state/user-reproduce-90d-new-id \
 --output reports/fast_research/USER_REPRODUCE_90D_NEW_ID.json
```

以上新目录/ID必须尚不存在，当前代码和协议冻结绑定一致；不触碰原报告或封存集。
