# 固定 HAR-RV 风险缩放：STOP，真实数据与可恢复结果已完成

本模块改变既有 CORE5 CSMOM21 的共同仓位缩放，不预测方向。原论文提供多期限已实现波动结构；这里是加密五分钟**方差**、日历1/7/30、训练 smearing 的适配。作者2004原文已阅读，2009发表版本仅核元数据；不声称原论文复现或原 FX 结果可迁移为加密收益。原始依据与差别见 [PROTOCOL.json](PROTOCOL.json)。先去重33个实际远端头、1014个策略/协议源码对象，再冻结本方案。此前两项 STOP 和 unpaidHALT-v2 修复保留、不重跑。

运行身份：协议59578cb9；原 CORE5 控制身份于首个拟合前独立修正20b97061；最终拟合源码 **265afb71f5a4300cb71305448d9809d54c127727**。修订仅替换此前声明的 beta 对冲控制，预测参数、时间切分、门槛和预算不变。源包94fe13c4的原始60个月度分钟ZIP/CHECKSUM/CRC，2,628,000个实际分钟行；稀疏 execution_minutes 不用于 RV。首日缺前一五分钟收盘，保留缺失；五资产均有364个完整日 RV。30日实际日收益与保存 covariance 输入在331个日期上误差0。

一次科学尝试，五个独立 intercept OLS；训练决策2021-02-02至06-30，每资产149行，标签最迟07-01成熟。07-01决策purge；诊断07-02至12-30、182个次日成熟标签。所有历史属于已见开发/训练域，**不是全新样本外**。无标准化或测试期重拟合；随机种子811130只用于固定1000次、7日共同日期区块 bootstrap。三个合成测试通过（10个合成 OLS，不混计科学拟合）。

| 固定诊断段 | HAR相对昨日RV的QLIKE改善 | 相对30日平均RV改善 |
|---|---:|---:|
| Jul2–Sep30 | 35.67%，5/5币改善 | 5.06%，3/5币改善 |
| Oct1–Dec30 | 25.25%，4/5币改善 | 4.04%，3/5币改善 |

两项成对损失差95%区间为 **[-.445681,.002327]** 与 **[-.069876,.027446]**，均跨0，违反发布前门槛。结论 **STOP_FIXED_HAR_RV_SIZING**；0真实钱包、8个条件经济账户 **NOT_RUN_FAILED_STATISTICAL_GATE**。不改门槛/参数/窗口挽救，也不据此永久否定HAR模型族。

| 全182日影子目标诊断 | BASE30 | HAR | 固定训练平均减仓 |
|---|---:|---:|---:|
| 平均gross | 31.97% | 23.15% | 29.47% |
| 固定目标的日内年化RV波动 | 13.50% | 9.29% | 12.44% |
| 毛价格proxy/10k | 780.74 | 446.37 | 719.61 |
| 13.5bp换手成本proxy/10k | 115.21 | 155.84 | 106.19 |

未来分类从不用于信号或筛选。空头急涨尾部4个资产日：BASE/HAR价格proxy -557.18/-367.76；反弹100日 -2651.29/-1886.39；正常下跌112日 +2954.44/+2268.30。减仓同时减轻损失和削弱趋势收益；4个尾部观察不足以认证尾部保护。预测总体偏高，逐币实际/预测方差均值 .67–.88，降风险还包含过度预测造成的暴露下降。恒定减仓对照不是实际风险匹配，影子RV不是完整NAV收益波动；这里没有成交、实际资金费、隔离清算或付费终端的净收益结论。所有标的/分段完整结果在 [RESULT.json](RESULT.json)。

准备23.20秒；历史诊断1.97秒（守卫3.72秒、采样RSS153.2MB）；1CPU、无GPU/swap、2GB采样RSSstop、4GB地址空间、15GiB磁盘预留。首次准备因输出父目录缺失而停止，未解析行情/拟合，修复源码后再准备；失败receipt保留。无provider下载、凭证、实盘、Library或2026锁正文访问。

公共恢复包 [RESULT_BUNDLE.zip](RESULT_BUNDLE.zip) 1,759,325B，保存实际5m closes、日RV、模型、全部预测/目标、原始控制、来源与运行/失败receipts；[PUBLIC_BUNDLE.json](PUBLIC_BUNDLE.json)绑定15成员和SHA。源码绑定 [SOURCE_SHA256.txt](SOURCE_SHA256.txt) 包括纠正后的 unpaidHALT-v2 及原共享内核；本模块未实例化钱包。公共冷恢复已通过 [PUBLIC_RESTORE.json](PUBLIC_RESTORE.json)，目标误差1.80e−16，原STATE访问0、额外拟合0；可直接执行：

```bash
COIN_CPD_STATE=/workspace/har-cold-guard QUANT_ROOT=/workspace/coin-har-risk \
QUANT_STATE=/workspace/har-cold-guard bash research/slow-momentum-cpd-20261011/launch.sh \
 /workspace/coin/.venv/bin/python research/har-rv-risk-20261011/cold_verify.py \
 --commit b4756ec8fb59457cfd8db74a79ca6a859f07f331 --directory /workspace/har-cold-restored
```

上述命令从真实公开Git读回，拒绝打开原研究STATE；检查原训练OLS normal equations及smearing、全部182日预测/四组目标、QLIKE和bootstrap，**0额外拟合/0钱包**。从原分钟包重新准备则checkout265afb71，运行 `prepare.py --archive existing-originals.zip --output fresh-prepared --source-commit 265afb71...`，继而 `diagnose.py --archive existing-originals.zip --prepared fresh-prepared --dependencies task-local-statsmodels0.14.5 --output fresh-diagnostic --source-commit 265afb71...`；两者同样经上述守卫。三个测试：守卫运行 `python -m pytest -q research/har-rv-risk-20261011/test_har.py --basetemp STATE/pytest`。历史重拟合命令只用于明确复现，不曾二次执行。

首次公共读回因命令误抄SHA返回404，保存 [FAILED_PUBLIC_FETCH_GUARD.json](FAILED_PUBLIC_FETCH_GUARD.json)；改为真实远端SHA后成功，工件/模型未修改。独立数据价值模块已恢复2022November全月trade/mark档案，检查真实连续覆盖和30日热身缺口，见 [恢复说明](../core5-2022-rv-source-20261011/README.md)；不复用失败配方产生新收益结果。历史2021原生MMR、资金费单位/时点、跨场所成本认证仍是未来钱包边界。
