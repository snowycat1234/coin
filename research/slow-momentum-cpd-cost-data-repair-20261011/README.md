# 修复训练数据后的趋势 / CPD 成本目标实验

已完成，结论为 **STOP_NO_FURTHER_RECIPE**。此次固定预算适配未建立稳定增量或正的绝对价格/成本代理收益，不继续搜索配方或启动钱包。全部种子和区间保存在 [完整结果](results/RESULT.json)、[预测仓位](results/POSITIONS.csv)、[每日成本路径](results/DAILY.csv) 和 [独立审计](results/INDEPENDENT_AUDIT.json)。

|已见历史开发验证|趋势费用后 Sharpe|趋势 + CPD|增量|
|---|---:|---:|---:|
|2023 上半年，180 成熟日|0.416868|0.308910|−0.107958|
|2023 下半年，183 成熟日|−1.799019|−1.670213|+0.128806|
|2024 年 1–4 月，120 成熟日|−0.706772|−1.021415|−0.314643|
|全部 483 日|−0.814851|−0.831824|−0.016973|

1,000 次联合 14 日 bootstrap 的条件性 95% 区间为 [−0.223299,+0.236027]，无退化抽样。三个种子的增量为 [−0.774542,+0.442275,+0.102089]。五项冻结门槛仅“两种子改善”通过；区间未调整此前研究选择或训练不确定性，不能排除小增量，也不能称全新样本外。

趋势/CPD 的累计价格/成本代理分别为 −0.0104483975 / −0.0096021925，占静态参考资本的比例。CPD 少负约 +0.000846205，但 Sharpe 更差，两者都没有正绝对代理收益。毛价格代理为 −0.0080280405 / −0.0077674881，已支付成本为 0.0024203570 / 0.0018347044。平均 gross 目标为 1.67816% / 1.56883%，平均有效 |p| 为 0.067338 / 0.061880；CPD 的 |p|<.001 比例仅 0.6211%，near_cash_flag=false。很多小交易低于参考 10USDT，未获原生可成交认证。

六个全新模型各 64 次完整日历更新，共 384 次；六个终端检查点保存后才做一次最终导出，包含全部 18 个模型/区间预测集。拟合与最终导出用时 49.146 秒，完整守卫命令 55.221 秒，采样 RSS 435,445,760B、host used 1,193,697,280B，无守卫停止，GPU/swap=0。全部 384 步被梯度裁剪且末段训练损失继续改善，固定预算未证明收敛。

40 项相关测试通过；独立审计的 18 组同策略模型读回误差为零，3,936 项 Decimal 每日/摘要核验最大误差约 1.735e−18；直接成本后净序列的 bootstrap 和全部门槛一致。234 份旧清单工件和 12 个旧模型保持原字节。累计研究为 4 次科学尝试、18 次 fresh 拟合、14,208 次更新；本次新增 1 个 GP 组/2 次优化器调用/1 次 scaler 拟合、6 个模型/384 次更新，另有 18 组审计读回。无行情提供方下载或 native 钱包。完整仓库测试为 NOT_RUN，隔离模块的全部 40 项相关检查已运行。

首个可运行恢复里程碑是 `fb08e7024c177597f475979e106cbb22084c0e26`。十个原始 SOL/XRP 日分钟 ZIP 及官方 CHECKSUM 响应文本来自已公开 Git `49017d88b75498a53f90857fe0d01a622e812a2f`，不重复下载行情。14,400 分钟的校验和、CRC、字段和完整网格均验证，仅修复十个原本缺失的训练收盘价。已有 359 个观测日/资产及缺口两侧八个相邻日与此前公开修复源精确一致，其余训练价格全部不变。

旧 `slow-momentum-cpd-cost-objective-20261011` 仍 BLOCKED/NOT_RUN。本独立数据版本保持同一因果掩码规则和严格标签成熟/purge；恢复真实观测后训练端点自然从 2,526 增至 3,142，日历仍为 729 天。训练期 GP/scaler 重新冻结一次，两个原定最多 60 步优化器在 24/47 步收敛。修复和重新冻结没有返回验证行。这些数据变化使与旧实验的差异不能单独归因于成本目标。

GP 重新冻结实际执行的是已公开并逐字节核验的 `fb08e702` 源码；STARTED 中 optimizer_calls=2 是计划数，两个终端结果确认实际完成。其后独立审阅建议增加拟合前修复哈希断言并明确 planned 字段，改动用于未来复现，未重复拟合，也未将后补检查伪称已执行。实际执行源码 SHA 记录在 CONFIG。

成对假设：同一小型趋势 LSTM 加入训练冻结的变点 age/evidence，能提高旧历史开发区间的成本后序列表现。两臂保持相同 10 输入/hidden16/tanh 模型、63 日序列、三个种子 2001/2002/2003、相同 fresh 初始化、Adam .001、clip1、64 次完整路径更新；baseline 在共享新 scaler 之后将 CPD 通道置零。原 BASE27 费用、入口/漂移/掩码退出/终端成本、1e−9 训练 epsilon、无 epsilon 的计分、五门槛及近现金限制均未改。无 HPO、种子/检查点选择、延期或自动重试。

[论文](https://arxiv.org/abs/2105.13727v3)及 [MIT 官方项目](https://github.com/kieranjwood/trading-momentum-transformer/tree/e0352cb0bdbf8045accb1bf1a5705ae0cb9ea624) 的表现来自传统期货，未提供加密货币收益证据。历史收益/MACD 是趋势信息；Matérn 变点 age/evidence 是状态信息；短期反转由 signed LSTM 仓位隐式学习，没有单独反转 head 或 selector。这里是适配实现，未使用后来 Transformer 配方或 oracle 收益，不是论文原样复现。

最小复现使用同一冻结数据、GP/scaler 和 CONFIG，无需在训练时重新拟合 GP。方便入口会核验真实分钟 Git 对象与修复收盘价，必要时从三个固定 Git parts 恢复原始价格档案，并对公开源码/配置/派生物逐字节读回。它在结果完成后新增，默认只检查；下面的 --run 显式启动一个单独的完整复现实验，必须使用新 STATE。单分支克隆若没有来源对象，先正常 fetch `research/temporal-feature-data-20261009` 和 `research/cloud-single-stream-20261010`；已有对象不重复获取。

```bash
cd /workspace/coin-slow-momentum
state=/workspace/slow-momentum-cost-reproduction
COIN_CPD_STATE="$state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python \
  research/slow-momentum-cpd-cost-data-repair-20261011/reproduce.py \
  --state "$state" --run
```

去掉 --run 即为只读来源/身份检查，不初始化模型、不重新拟合 GP、不读取历史验证结果。已完成复现的审计命令使用同一 bounded launch，运行 `python -m modules.slow_momentum_cpd.audit_repaired_cost --state "$state" --config-sha d54f4b20133bd281c04d1ae3eeb4f9f51a7de14d0d0cf54d439ff9f520aef891 --output "$state/INDEPENDENT_AUDIT.json"`。CONFIG SHA 即该值；实际训练发布源码为 `14939d25ad8f0b88a58181273fc736304c683799`，训练前公开核验 26 个文件。

真实 signed 资金费、分钟可用性与成交、lot/minimum/capacity、共享钱包风险及实际终端账本尚未绑定；在门槛失败后它们为 NOT_RUN，不能补零或近似。没有真实钱包净收益/APR或上线资格结论。2026-03-01 至 2026-09-01 的 collector 锁、失落的 2026 Q1/Q2 账本及另一收益分布研究均未改变，未使用 Library、账户密钥、创建凭证、付费、实盘或部署。
