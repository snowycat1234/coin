# 固定 CS21 与同风险 HOLD：完整 2023 连续经济验证

全年结果为 **`STOP_FIXED_CS2023_CONTINUOUS_GATES`**，八项继续门槛全部失败。CS 已付费清仓净收益 −15.030256 USDT；HOLD 账面净收益 +2,411.867442 USDT，但仍有残仓。四个自然季度相对增量全部为负，实际波动、回撤及最差 30 日均更差。这段真实历史未支持固定 CS21 的稳定增量。

此前 456 日的正面熊市对冲点证据与负面分期均保留。本轮没有调参、加门控、重训或改变时间窗口；这是已见历史的经济适配验证，不是论文原样复现、全新样本外结果或对所有信息型空头的否定。

## 冻结范围与两臂

精确范围 **[2023-01-01 00:00:00 UTC，2024-01-01 00:00:00 UTC)**，365 日，每臂 525,600 分钟。两个独立新 10,000 USDT 钱包，各自内部 CORE5 资产共享资金；期间无重置、注资、跳段或按盈利月份选窗口。

旧状态确实止于 2022-07-01，已经终端处理，且未识别到可核验的同账户年末状态或完整 2022H2 桥接。因此本轮没有接续或拼接长期净值。

CS21 和 HOLD 的全年目标逐字绑定既有公开 `TARGETS.npz`：原 21 日横截面前二多、后二空，固定七日锚点；HOLD 原等权常多方向。使用同一过去 30 日协方差、当前五币可用性和共同事前风险，只向下缩放原方向。没有读取未来结果来删除目标日期，零新拟合。

| 指标 | CS_MATCHED | VOL_MATCHED（HOLD） |
|---|---:|---:|
| 终值 NAV / USDT | 9,984.969744 | 12,411.867442 |
| 净收益 / USDT | **−15.030256，已付费清仓** | **+2,411.867442，账面** |
| 分钟平均 gross / NAV | 42.916924% | 18.565276% |
| 分钟最大 gross / NAV | 61.948219% | 37.187545% |
| 实际日收益年化波动 | 12.593819% | 11.228829% |
| 全观测最大回撤 | 14.915381% | 9.250515% |
| 最差滚动 30 日 | −8.430467% | −6.280101% |
| 手续费 / USDT | 118.655925 | 20.307638 |
| 半价差成本 / USDT | 86.295316 | 14.770026 |
| 滑点成本 / USDT | 86.295316 | 14.770026 |
| 资金费现金流 / USDT | −28.947631 | −151.273316 |
| 强平数 / 独立仓位与 NAV 审计 | 0 / PASS | 0 / PASS |
| 付费终端清仓 | PASS | **FAIL** |

采用未改的默认 USDT 账户及 `318a0ae6…` 分钟内核，1×逐仓、不自动补款。Binance 行情与 Bybit 费用代理显式区分；原 `BASE27` 每边 5.5bp 手续费、4bp 半价差、4bp 滑点，名义往返 27bp。资金费使用实际恢复时间戳与费率，沿用 `RAW_AS_FRACTION`、scale=1；负号表示现金流出。历史单位、准确扣费价、交易所风控层级和到达时间仍为条件假设。

原 30% 单币 / 60% gross 目标、前一报价量×0.001 容量、10 USDT 最小名义金额、1e-8 数量步长、五次尝试和最后六分钟付费终端均保持。gross 指绝对名义敞口之和÷NAV；与逐仓 1×配置不同，也没有强行等同两臂的实际敞口或风险。CS 实际峰值 61.948219% 超过 60% 目标的漂移原样保留，未声称每刻硬保证。最大回撤覆盖可用分钟收盘标记及成交、资金费观测，未覆盖未知分钟内标记极值。

HOLD 保留 **DOGE 65.01673761**，终端标记价 0.08958，价值 **5.8241993551038 USDT**。这是未清仓持仓，`unpaid_liability=0`，不是债务；没有免费删除、延长重试或更换账户。HOLD 收益及配对点差因此为账面量。

独立 Decimal 桥：CS 价格毛收益 305.163931 − 手续费 118.655925 − 执行成本 172.590632 − 资金费 28.947631 = −15.030256；HOLD 2,612.988447 − 20.307638 − 29.540051 − 151.273316 = 账面 2,411.867442。最大桥误差 4e-36 USDT。

## 固定配对检验

全年账面增量 **−2,426.897699 USDT**，配对实际日收益差均值 **−0.000591268206**。循环 14 日块 bootstrap，seed **811720**、1,000 次，95% CI **[−0.001457369585，+0.000122004926]** 跨零；未声称显著负效应、独立市场周期或选模修正后的置信度。

| 连续分期 [含首，不含末) | CS NAV 变化 | HOLD NAV 变化 | 相对增量 / USDT |
|---|---:|---:|---:|
| Jan1 → Apr1 | +209.722808 | +1,057.082657 | **−847.359849** |
| Apr1 → Jul1 | −616.179287 | −92.911148 | **−523.268139** |
| Jul1 → Oct1 | −744.403712 | −43.041643 | **−701.362069** |
| Oct1 → Jan1,2024 | +1,135.829936 | +1,490.737577 | **−354.907641** |

这是同一持续钱包的分期 NAV 变化，不是四个满资金独立账户。全部八项继续门槛失败，包括净收益、点增量、CI 下界、所有季度增量、实际波动比例、回撤、最差 30 日和两臂完整清仓。CS / HOLD 实际波动比例 **1.121561** 超过冻结 1.10 上限；最差 30 日分别发生于 Jun14–Jul14、Aug13–Sep12。

同一 CS 钱包内 LONG / SHORT 贡献为 **+2,621.147105 / −2,636.177362 USDT**，合计 −15.030256；不是两个独立 10k 策略、可学 alpha 证明或 oracle 路由收益。过去信息描述 UP/PULLBACK/REBOUND/DOWN/SIDEWAYS 日数 175/74/30/47/39，仅用于描述。

## 实际来源、计算与公开证据

已复用公开 `b6f71c9f208a0c4a3dbfc3aac45fe8f4bb472c3e` 的 Jul–Dec 60 个完整 trade/mark 月档，没有重复下载。缺失 Jan–Jun 的 60 个官方月档分两个固定季度补齐；五币 Feb mark 月档均漏 Feb24 的 1,440 分钟，取得五个对应官方日档并精确补齐真实行，未插值。

新增原始压缩档案 **77,488,290 字节、65 个**，低于预固定 100MB / 10 日档预算；Q1 39,210,299 字节，Q2 38,277,991 字节。HTTP_RETRIES=0，沿用官方 `Job/fetch/checksum/CRC/numeric_csv/validate_price`，未发生地区或权限绕过。两个季度均发布、验证远端并做新空目录 Git 冷恢复后才进入下一阶段。

完整来源覆盖每币 525,600 分钟及 5,475 个实际资金费事件（每币 1,095），12 月份完整网格、全部 365 日收盘与旧真价格 cube 一致，每币 364 个实际前分钟边界核对。Jan1 首日决策复用已 SHA 绑定日线边界，不声称恢复 Dec31 分钟；fresh-flat 首个资金费无仓，第一实际分钟为首成交提供已完成 quote/mark，原内核语义未改。

- 初始冻结协议：`f6a0231372e19f7e9e99a8a1802ed8a7a69c89df`。
- Q1 原档：`c5a59cc3cc81b017197c21f507351e70d55107b8`；Q2 原档：`90748ff2551e5f03bfa6fa6726d8da9b73a2d5e5`，各自冷恢复凭据在 `source-phases/`。
- 完整来源运行代码：`f2db682ff77eba85de3b811529f313b739dba2be`；来源证明及真实钱包启动 HEAD：`f38617c5a0917490c8b90fba355ecf0d5f1b87f4`。源码、原档、向量、日线/资金费正文 SHA 见三个源码清单与 [SOURCE_INDEX.json](source-result/SOURCE_INDEX.json)。
- 机器结果：[`96d3e0e86ed5ea7f8bd4ad8579c93143b5a92a51`](https://github.com/snowycat1234/coin/commit/96d3e0e86ed5ea7f8bd4ad8579c93143b5a92a51)，[RESULT.json](native-summary/RESULT.json)。
- 完整真实账户包：[`b8373a0167482f28a900e430b94a03433f947588`](https://github.com/snowycat1234/coin/commit/b8373a0167482f28a900e430b94a03433f947588)，120,875,200 字节 / 154 分片 / 765 成员，SHA256 `d8fff06a23affd8821e4c0e63f81898446524aa7830ba4b8bf9c894b8068a675`。两个原账户/调度器快照、730 个真实分钟块、全部 37 个分钟数值列及完整 journal 保留，原 Parquet 容器编码未声称逐字重新发布。
- **一个固定经济假设，两个新钱包，零拟合、零旧钱包重跑**。新来源 / 年度目标适配器四项测试 PASS，4.34 秒；此前八项因果/金融/状态测试明确 REUSED。只读审阅核实默认账户、费用、资金费、残仓、增量/CI/实际风险；未替代实际冷恢复。
- 来源组装 100.331954 秒；两个钱包 301.888207 秒（guard 306.519148 秒），采样 RSS 峰值 728,997,888 字节。沿用 1 CPU/thread、4GB AS、2GB 采样 RSS 停止线、8GB host、无 GPU/swap、15GiB 磁盘保留的重建云 guard，未声称原 WSL / 共享 cgroup 认证。

## 最小公开复现

实际公开零 STATE 恢复已 **PASS**，131.836567 秒（guard 136.205638 秒，采样 RSS 峰值 795,705,344 字节）。新目录从 Git 重建完整来源，恢复两个原调度器，状态 hash、账户、journal/summary、全部 37 个分钟数值列与坐标以及独立仓位/NAV 桥精确一致。**账户推进 0、新钱包 0、拟合 0、交易所下载 0、原观察 STATE 打开尝试 0**。证据：[PUBLIC_RESTORE.json](evidence/PUBLIC_RESTORE.json)、[PUBLIC_SOURCE_RESTORE.json](evidence/PUBLIC_SOURCE_RESTORE.json)、[PUBLIC_COLD_GUARD.json](evidence/PUBLIC_COLD_GUARD.json)。这是零 STATE 恢复，不是新机器依赖安装或重新回测。

恢复后本模块 STATE 总量 1,466,038,048 字节，磁盘剩余 17,485,561,856 字节，满足 2GB STATE 和 15GiB 保留边界；不将采样 RSS 写作内核精确峰值。

在干净本研究分支 checkout，已有项目依赖及上述公开 Git 对象；`--state` 必须是尚不存在的目录。此命令核验公开来源和原调度器，**不重跑钱包或拟合**：

```bash
COIN_CPD_STATE=/workspace/cs-2023-state \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/cs-2023-state \
bash research/slow-momentum-cpd-20261011/launch.sh \
/workspace/coin/.venv/bin/python research/cs-2023-continuous-economics-20261012/persist.py restore \
  --state /workspace/cs-2023-state/PUBLIC_COLD \
  --artifact-commit b8373a0167482f28a900e430b94a03433f947588 \
  --source-science-commit f2db682ff77eba85de3b811529f313b739dba2be \
  --source-artifact-commit f38617c5a0917490c8b90fba355ecf0d5f1b87f4
```

再次运行时换一个不存在的目录。实际账户命令仅作来源记录：在 HEAD 精确 `f38617c5…`、已恢复完整来源时执行 `native_run.py --state /workspace/cs-2023-state/NATIVE_OBSERVED --prepared /workspace/cs-2023-state/SOURCE_OBSERVED --source-commit f38617c5a0917490c8b90fba355ecf0d5f1b87f4`，同样通过上述 guard；无需重跑即可核验已发布结果。

新适配器测试命令：

```bash
COIN_CPD_STATE=/workspace/cs-2023-state \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/cs-2023-state \
bash research/slow-momentum-cpd-20261011/launch.sh \
/workspace/coin/.venv/bin/python -m pytest -q -p no:cacheprovider \
  --basetemp=/workspace/cs-2023-state/recheck-tmp \
  research/cs-2023-continuous-economics-20261012/test_source.py \
  research/cs-2023-continuous-economics-20261012/test_native.py
```

本模块补足了完整 2023 的条件分钟经济覆盖。剩余限制是历史交易所费用/资金费单位、准确扣费标记、原生风险规则和到达时间权威性，以及不存在已验证的 2022H2 同账户接续。保留既有正负证据，不救援调参。锁定 2026 collector 数据、丢失账本、另一研究、账户密钥、付费、部署和 Library 均未使用。
