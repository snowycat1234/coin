# 单个结算资金费通道：训练期条件增量

本模块已完成来源与可运行预检，科学拟合尚未执行。独立分支 `research/short-nonprice-diagnostic-20261011`，先发布并逐字节核验实现，再运行唯一两拟合。

经济假设是过去正资金费代表多头拥挤，能在固定价格/波动率/资产控制之外改善下一周空头机会预测。资金费并非新特征：旧联合模型、七日符号分箱和分布研究已有先例。此次只隔离一个每资产连续资金费通道，范围不同于旧联合配方；[去重依据](NON_DUPLICATION.md) 和 [全部30远端head/551源码blob目录](BRANCH_INVENTORY.json) 已保存。

固定CORE5，2021年拟合、2022两个半年度作训练内诊断；Monday七日非重叠区间，跨年/跨半年度标签严格成熟及purge。共同因果输入掩码保留全部可用市场周：拟合255资产周/51市场周，诊断125+123资产周/25+25市场周；两个SOL资产周因过去资金费完整性未通过而共同排除。2020仅预热，不读2023/2024开发值、Q3 2026或保留集。

价格ridge对照与价格+资金费ridge，alpha1、无随机初始化或搜参。训练期归一化、资产指示和未来收益只用于2021拟合；资金费事件窗固定 `[D−8日,D−1日)`，同刻上界排除。官方历史结算时钟有毫秒抖动，预检曾误用精确整点间隔并退出；修复只给名义间隔QA留60秒抖动容差，真实事件时钟完全保留，缺事件仍不可用，不读取未来事件证明完整。初始失败及完整性诊断收据保留。

BASE27单腿每边fee5.5bp、spread4bp、slip4bp，费用作用于执行后价格，逐周独立入场/退出收费。单位short价格代理为 `(1−.0008)(1−.00055)−(Pexit/Pentry)(1+.0008)(1+.00055)`；除以过去30日波动率×sqrt7供模型评分。它是价格预测目标，并非native账户或包含真实资金费的净收益。初始每币.12参考名义的周机会描述保留现金周，不强制空头比例或挑选月份。实际资金费/执行/风险/逐仓/终端账户保持NOT_BOUND。

[冻结协议](PROTOCOL.json) 的七门槛全部通过才允许另行冻结开发验证；否则立即STOP。共同日期四周block bootstrap，1000次、seed811031，资产不是独立样本。正资金费系数只检查2021固定拟合，失败不反向选择另一因子。历史发布时钟、单位认证及原生经济资格不由本诊断建立。

数据是已有公开Git `e0d3400b` 三个2.25MB历史档案parts及既有十个真实缺失价格修补；不重新下载官方大行情。只投影2023前的close/完整性和结算时钟/原率/名义间隔，未来收费mark、execution价格和24输入NPZ均不读作模型输入。修补值及官方CHECKSUM来源按原已接受记录保留，未重拟合任何CPD模型。

在本研究分支，通过既有已公开保守云资源守卫运行：

```bash
task_state=/workspace/short-funding-residual-reproduction
COIN_CPD_STATE="$task_state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python research/short-funding-residual-20261011/experiment.py \
  --mode preflight --state "$task_state"
```

真实拟合要求干净的发布源码checkout、确切40位提交及对应 `SOURCE_PUBLIC_READBACK.json`；原目录存在STARTED时拒绝重复运行。复现可重放公开保存模型，无须重训。1CPU/1线程、4GB地址、2GB采样RSS/8GBhost、1200秒、10MiB输出/15GiB磁盘预留、GPU/swap0；云守卫是已声明重构版，不声称WSL旧cgroup逐字节恢复。7项边界/因果/Decimal费用/缺结算/单位缩放/闭式拟合测试通过；最终结果与模型将在本目录公开保存并独立读回。
