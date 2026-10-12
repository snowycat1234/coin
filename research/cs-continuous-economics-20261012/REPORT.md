# 固定 CS21 连续经济验证：结果与复现

固定 CS21 在这段已见历史上的账面增量为正，熊市对冲值得保留为研究对照；稳定增量和完整清仓门槛未通过，最终状态为 `STOP_FIXED_CS_CONTINUOUS_GATES`。没有修改账户、dust 门槛、时间范围或参数来挽救结果。

这是一项原有加密货币 CS21 路线的经济适配验证，不是《Slow Momentum with Fast Reversion》的原样复现、Transformer 新训练或全新样本外结果。先前论文机制、selector、FOMC、HRP 和 2024 CS 负面结果均保留。

## 范围与冻结实现

- 各臂独立初始资金 **10,000 USDT**；每臂内部所有资产共用一个钱包。
- 精确连续范围 **[2021-04-01 00:00:00 UTC, 2022-07-01 00:00:00 UTC)**，456 日、每臂 656,640 分钟。期间无重置、资金注入或中途独立清仓后重启。
- CORE5 顺序：BTCUSDT、ETHUSDT、SOLUSDT、XRPUSDT、DOGEUSDT。
- CS：原有 21 日收益排序，前二做多、后二做空，固定七日锚点；基于过去 30 日协方差控制风险。HOLD：原有 `VOL_MANAGED_HOLD` 等权常多方向，不是逆波动率组合。
- 在当前五币都可用的日期，两个原始组合只向下缩放到共同的事前协方差风险，保留原方向、30% 单币 / 60% gross 目标。4 月 1 日两臂因当时资格不足持现金，4 月 2 日开始就绪。实际敞口和事后风险分别报告。
- 原默认 `NativeDailySimulator` / `USDTLinearPerpetualAccount`，**1×逐仓、不自动补款**；前一报价量的 0.001 容量、10 USDT 最小名义金额、数量步长 1e-8、五次尝试、原最后六分钟付费终端平仓均未改变。
- 时间范围在首个历史结果前由数据完整性、成熟期和自然季度边界冻结；不以盈利月份选择范围。完整 [2021-01-01, 2024-01-01) 的 1,095 日开发参考另行保留，其中 60 个季度/臂条件参考 32 完成、28 因来源缺口 STOP，未拼成三年钱包。

## 两个真实连续钱包

以下成本均已进入 NAV。CS 因仍有残仓，其收益是**账面净收益**。

| 指标 | CS_MATCHED | VOL_MATCHED（HOLD） |
|---|---:|---:|
| 终值 NAV / USDT | 12,488.398901 | 10,355.707171 |
| 净收益 / USDT | +2,488.398901，账面 | +355.707171，已付费清仓 |
| 分钟平均 gross / NAV | 31.513199% | 11.810372% |
| 分钟最大 gross / NAV | 60.792560% | 19.642128% |
| 实际日收益年化波动 | 9.945793% | 10.893474% |
| 全观测最大回撤 | 7.975151% | 18.579978% |
| 最差滚动 30 日收益 | −4.933178% | −7.030468% |
| 手续费 / USDT | 131.746704 | 14.450979 |
| 半价差成本 / USDT | 95.816690 | 10.510019 |
| 滑点成本 / USDT | 95.816690 | 10.510019 |
| 资金费现金流 / USDT | −15.550204 | −284.445177 |
| 强平事件数 | 0 | 0 |
| 付费终端清仓 | **FAIL** | PASS |

费用为原 `BASE27`：每边 5.5bp 手续费 + 4bp 半价差 + 4bp 滑点，名义往返 27bp。实际资金费沿用原 `RAW_AS_FRACTION`、scale=1，按恢复的实际事件时间戳和费率处理；表中负号表示现金流出。6,840 条实际费率事件及来源绑定在 [SOURCE_INDEX.json](source-result/SOURCE_INDEX.json)。历史费率单位、准确扣费价、维护保证金和到达时间的交易所权威性仍未认证，因此这是条件账户实现的真实历史运行。

gross = 所有持仓绝对名义金额之和 / NAV；该数也是组合总名义杠杆，与逐仓配置 1×不同。CS 的 60.792560% 实际峰值包含价格漂移超过 60% 目标的事实，未声称目标是每刻硬保证。最大回撤包含因果可用分钟收盘标记及成交/资金费观测，不覆盖未观测的分钟内标记极值。

独立 Decimal 核算桥：CS 价格毛收益 2,827.329188 − 手续费 131.746704 − 执行成本 191.633379 − 资金费 15.550204 = 账面净收益 2,488.398901；HOLD 675.623366 − 14.450979 − 21.020039 − 284.445177 = 355.707171。逐币仓位审计和 NAV 桥均 PASS，最大误差 1e-35 USDT。

CS 终端剩余 **DOGE 6.07978772**，实际终端标记价 0.06638419，名义价值 **0.4036017831641468 USDT**。未免费清除、改变最小名义金额或换账户。该余额使清仓门槛独立失败。

## 配对增量与失败门槛

整段账面相对增量 **+2,132.691730 USDT**。实际配对日收益差均值为 **0.000408041335**，预固定循环 14 日块 bootstrap（seed 811720，1,000 次）95% CI **[−0.000359784715, +0.001153031870]**，跨零。该 CI 描述已见联合路径，未做选模修正，也不代表独立市场周期。

| 预固定连续分期 [含首、不含末) | CS NAV 变化 | HOLD NAV 变化 | 相对增量 / USDT |
|---|---:|---:|---:|
| 2021-04-01 → 2021-07-01 | +744.089156 | +1,024.645622 | **−280.556466** |
| 2021-07-01 → 2022-01-01 | +661.149142 | +777.287455 | **−116.138313** |
| 2022-01-01 → 2022-07-01 | +1,083.160603 | −1,446.225905 | **+2,529.386509** |

这些是同一持续钱包的分期 NAV 变化，没有分别重置资金或拼接独立钱包收益。优势集中在 2022H1，前两个固定分期相对表现为负。稳定增量 CI、所有分期正增量和完整付费清仓三项门槛失败；正净收益、正相对点增量、相对波动/回撤/尾部门槛通过。

同一 CS 共享钱包内 LONG / SHORT 的账面贡献为 +211.232793 / +2,277.166108 USDT；这不是两个独立资金策略或可学空头 alpha 证明。过去信息描述的 UP/PULLBACK/REBOUND/DOWN/SIDEWAYS/UNKNOWN 日数为 117/57/42/199/40/1，仅用于描述，不作为交易筛选或独立状态样本数。

## 来源、尝试和测试

- 初始冻结实现：`5b60f3b9b8b1d8743ba075e07267b87f3ba14351`。
- 实际完整来源恢复代码：`eefb67af42dcff3eeadaa6dc144483bdcdc7b038`。
- 来源证明及首个钱包运行时精确 HEAD：`fd83183c363c14e8095a6a90c252b42e22cf6493`。
- 账户持久化代码冻结：`04504c4246f71a35f30caec50e150d2fbbcf9535`。
- 完整公开账户 packet：[`714e8f577284449774d3bd4b6089074958e1e7a5`](https://github.com/snowycat1234/coin/commit/714e8f577284449774d3bd4b6089074958e1e7a5)。155,663,037 字节，198 个分片，912 个真实分钟块；完整 journal、原账户/调度器快照和全部 37 个分钟数值列保留。原 Parquet 容器 SHA 已记录，未声称重新发布其编码字节。
- 公共行情 Git：trade `306b58c4a52035ac9f374de7c25d40dff22fb658`，mark `a23f8cc36bdaddce832b2305a16fda493d1cf764`，原 2021 wrapper `94fe13c494c82bb6e6868e6614eb7298fb15b3c3`，实际小资金费档案 `e0d3400b23842f11f167a63e7d80856d76501de8`。完整文件/向量/重叠/归属 SHA 见来源索引及三个源码清单。
- 默认分钟引擎 SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`，未修改。
- **一个固定经济假设尝试、两个新真实钱包、零监督拟合、零旧钱包重跑、零交易所数据下载**。
- 基础设施失败保留：错误启动 SHA 被拒绝；首个来源恢复在所有价格校验后发现每币少一个实际 2021-12-31 16h 资金费事件并 STOP；一个测试 fixture 的 NameError。资金费事件由已有小 Git 档案精确恢复，每币 824 条重叠相等、实际补一条，未猜测费率。原 28 个季度来源 STOP 和其他研究输入未改。
- 最终 **8 个针对性测试 PASS，4.13 秒**（seed 811710）：因果前缀/方向和风险匹配、当前成员/时钟、缺口留仓、资金费符号及付费终端、终端费耗尽、资金费/日历篡改、实际来源精确 union、原默认调度器合成分段恢复等价。合成测试不声称历史来源权威。
- 实际钱包总耗时 419.412006 秒，采样 RSS 峰值 868,982,784 字节。1 CPU/thread、4GB AS、2GB 采样 RSS 停止线、8GB host、无 GPU/swap、15GiB 磁盘保留，详见 [NATIVE_GUARD.json](evidence/NATIVE_GUARD.json)。这是重建的云 guard，未声称原 WSL/共享 cgroup 认证。

## 公开零推进冷恢复与最小命令

从**新空 STATE** 恢复已 PASS，97.936538 秒；guard 101.763345 秒、采样 RSS 峰值 947,740,672 字节。来源从已有公开 Git 对象重新构建，两个真实原调度器恢复后，状态 hash、账户、全部 37 列分钟数值位、journal/summary 和独立仓位/NAV 桥精确相等。**账户推进 0、新钱包 0、拟合 0、交易所下载 0、原观察 STATE 打开尝试 0**。证据：[PUBLIC_RESTORE.json](evidence/PUBLIC_RESTORE.json)、[PUBLIC_COLD.log](evidence/PUBLIC_COLD.log)、[PUBLIC_COLD_GUARD.json](evidence/PUBLIC_COLD_GUARD.json)。这是零 STATE 恢复，不是新机器依赖安装或再训练验证。

在干净的本研究分支 checkout，使用已经准备好的仓库依赖和上述公开 Git 对象；`--state` 必须是尚不存在的路径。当前云工作区实际运行的最小恢复命令如下；再次运行时换一个不存在的目录即可，不需要重新跑钱包：

```bash
COIN_CPD_STATE=/workspace/cs-continuous-state \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/cs-continuous-state \
bash research/slow-momentum-cpd-20261011/launch.sh \
/workspace/coin/.venv/bin/python research/cs-continuous-economics-20261012/persistence.py restore \
  --state /workspace/cs-continuous-state/PUBLIC_COLD \
  --artifact-commit 714e8f577284449774d3bd4b6089074958e1e7a5 \
  --source-science-commit eefb67af42dcff3eeadaa6dc144483bdcdc7b038 \
  --source-artifact-commit fd83183c363c14e8095a6a90c252b42e22cf6493
```

最终测试的命令（所有 Python 通过原 guard）：

```bash
COIN_CPD_STATE=/workspace/cs-continuous-state \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/cs-continuous-state \
bash research/slow-momentum-cpd-20261011/launch.sh \
/workspace/coin/.venv/bin/python -m pytest -q \
  research/cs-continuous-economics-20261012/test_core.py \
  research/cs-continuous-economics-20261012/test_state.py
```

实际钱包命令仅作运行来源记录：运行时 HEAD 必须精确为 `fd83183c363c14e8095a6a90c252b42e22cf6493`，来源已由上述代码恢复，输出目录必须新建。无需执行它即可核验公开结果。

```bash
COIN_CPD_STATE=/workspace/cs-continuous-state \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/cs-continuous-state \
bash research/slow-momentum-cpd-20261011/launch.sh \
/workspace/coin/.venv/bin/python research/cs-continuous-economics-20261012/native_pair.py \
  --state /workspace/cs-continuous-state/NATIVE_OBSERVED \
  --prepared /workspace/cs-continuous-state/SOURCE_RECOVERED \
  --source-commit fd83183c363c14e8095a6a90c252b42e22cf6493
```

后续有价值的证据是扩大独立日历和完整经济来源覆盖。2022 年末 / 2023H1 分钟经济路径与原生交易所权威性仍未认证；2023 条件参考负面季度、原 2024 CS 负面钱包和所有旧 STOP 均保留。本模块不添加特征、重新拟合或改窗口以挽救结果，也未访问锁定 2026 collector 数据、丢失账本或另一项收益分布研究文件。
