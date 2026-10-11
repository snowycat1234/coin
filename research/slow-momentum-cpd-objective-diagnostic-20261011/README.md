# CPD目标一致性：诊断完成，唯一提案等待核对

旧毛Sharpe配方和 `NO_FIXED_COST_PROXY_MARGIN` STOP 保留。本轮只读既有源码和
保存2048策略，训练/模型推断/钱包/新策略验证/行情下载均0。
唯一新方案见 [冻结提案](COST_OBJECTIVE_PROPOSAL.json)，**NOT_RUN_PENDING_PARENT_REVIEW**。

| 保存483日 equal-target ensemble | 趋势 | CPD |
|---|---:|---:|
| 同方向幅度调整占实际换手 | 69.01% | 66.18% |
| 翻号占实际换手 | 28.54% | 30.54% |
| signal 投影占实际换手 | 100.43% | 98.72% |
| vol scaling 投影占实际换手 | −0.90% | −0.86% |
| eligible 平均 \|p\| / 中位数 | .03991 / .02933 | .03329 / .02393 |
| \|p\|<.001 / <.01 | 2.08% / 18.33% | 1.58% / 22.32% |
| 平均目标 gross | .90368% | .72737% |
| 固定BASE27成本后价格代理 | −.743893% | −.179366% |

signal、vol、前日价格漂移和边界是有符号精确分解，各分量可抵消；
投影不是独立交易腿或成本份额。按实际交易量分组逐项回到旧成本结果；
全3区块/2臂/3seed及ensemble见 [完整结果](results/RESULT.json)。
这是会计分解，不证明某类交易无用、删除可盈利或oracle收益。
近零阈值仅描述，没有新dead-zone策略。

小仓位解释金额/暴露小，不能解释负成本效率。固定参考资本全量成交代理具有
一次齐次性：统一缩小/放大不改变毛收益减成本的符号或盈亏平衡费率。
CPD原盈亏平衡单边3.85bp仍低于13.5bp。最低单/舍入/风险会破坏齐次性，
尚未原生测量；没有放大仓位的策略验证查询。

检索覆盖27个现有本地分支tip SHA、152种匹配源码版本，见
[目录](prefit/SOURCE_CATALOG.json) 和 [来源/实绩](results/SOURCE_PRECEDENTS.json)。
direct_path两fit、temporal四fit已训练自身BASE27/资金费/付费终端路径目标；
v2/v3已有扣成本expert teacher，不能称“加入成本”是新方法。
所检索证据未找到等同的直接资产仓位 trend/CPD 冻结成对净价格成本Sharpe实验；
不是全部历史archive正文或不可访问分支的完整证明。

唯一提案：复用原公开档案、训练期GP/scaler、同10通道hidden16/tanh LSTM；
趋势最后两通道在共享scaler转换后置零。原种子2001/2002/2003，六fresh拟合、
配对初始权重相同，每fit固定64次完整训练日历组合更新，共384，不恢复旧模型。
729训练决策日是严格cutoff下的预期日历，2526端点身份必须预检，保留现金/mask
退出，标签成熟严格早于2023-01-01。完整费用、价格漂移、入口和付费终端先计入
组合价格代理，然后优化成本后Sharpe；固定BASE27系数1，不搜费用/惩罚/持有期。
复用已有完整路径输出VJP，以128特征chunk重算梯度；chunk不重置经济路径。

六terminal冻结后一次导出全部483已见开发日。必要门槛：CPD绝对成本后代理>0、
组合净价格成本Sharpe增量>0、全3区块及至少2seed增量>0、14日/1000次/seed9901
联合bootstrap下界>0。先原日期算费用，再重采样同日两臂net series；不重组价格
路径重算换仓。现金/零方差INVALID。CI未修正之前尝试和提案选择，不是新OOS。
完整日历/组合聚合也改变，故旧sampled gross结果不能单独识别成本项的作用。

待审预算：六fit串行、总1200秒、1CPU/4GBAS/2GB采样RSS停止/共享8GB停止、
GPU0/swap0、state≤10MiB、磁盘保留15GiB；固定64上限不称收敛。
项目abs.3/gross.6限额在本提案新增proxy STOP检查；旧gross runner只报告未约束
敞口，没有这些STOP。不静默clip/放大。来源/因果轴/梯度/数据/caps/数值/资源或
门槛失败即停，不单臂延长/重试。**完整日历训练adapter及其预检尚未实现，
等待核对；此文件不授权训练。** 资金费不是已知零，native钱包/风险/终端未绑定，
净Profit/APR UNKNOWN。论文传统期货机制的CPD适配，不是原样复现或反转因果证据。
collector2026Mar–Sep锁、不可恢复2026Q1/Q2账本和另一研究未触动。

7合成数学测试PASS，包括费用成交价交叉项、漂移、mask/现金NaN、终端平仓、
全部6个非kink坐标有限差分及abs(0)子梯度0；[测试](prefit/TESTS_FINAL.xml)。
实际诊断执行公开并字节核验源码 `0f33e1ab`，guard .503秒/RSS采样41,136,128B；
不是内核峰值。原185manifest文件/4拟合源码/12外部旧模型字节保持。
[独立只读提案审阅](results/REVIEW.json) 已采纳两处文字澄清，未改实验数字。
完整仓库测试NOT_RUN；native可微性未认证。本轮训练累计仍3尝试/12freshfit/
13824updates；若以后批准启动六cost fit才记尝试4。

最小复现使用已有bounded入口。仅需numpy和公开保存CSV即可运行第二条，
不依赖旧模型二进制；数学测试还需原环境torch/pytest：

```bash
COIN_CPD_STATE=/workspace/cpd-objective-check bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python -m pytest modules/slow_momentum_cpd/test_objective_diagnostic.py \
  --basetemp=/workspace/cpd-objective-check/pytest -q
COIN_CPD_STATE=/workspace/cpd-objective-check bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python research/slow-momentum-cpd-objective-diagnostic-20261011/reproduce.py \
  --output /workspace/cpd-objective-check/REPLAY.json
```

原诊断CLI另外核对state中12旧模型完整性；这些二进制未假称公开可恢复。
