# 单个结算资金费通道：训练期条件增量

已完成唯一训练期成对检验：**1次科学尝试、2次确定性ridge拟合，七门槛5通过、2失败，STOP**。没有反向改因子、追加特征搜索或读取2023/2024开发值。结果与两模型已保存在本模块；远端恢复认证另见 `results/PUBLIC_RESTORE.json`（结果首次发布后生成）。

| 固定区间 | 价格对照MSE | 加资金费MSE | 相对MSE改善 | 成对价格成本代理增量/市场周 |
|---|---:|---:|---:|---:|
| 2022全年训练诊断 | 2.435649 | 2.401268 | 1.411591% | −4.163982bp |
| 2022H1训练诊断 | 1.600143 | 1.568760 | 1.961261% | +0.750126bp |
| 2022H2训练诊断 | 3.284741 | 3.247313 | 1.139469% | −9.078089bp |

条件性联合日期bootstrap95%相对MSE改善区间为 **[0.397996%,3.522169%]**；两个半年度均改善。2021资金费标准化系数 **−0.09823997**，与冻结的“正资金费、多头拥挤、随后更利于做空”方向相反，且价格成本代理的成对增量为负。这只建立小幅条件预测增量，未建立指定经济机制或可交易空头收益。不能事后反号继续配方。

资金费不是新特征：旧联合模型、七日符号分箱和另一分布研究已有先例。此模块隔离一个每资产连续结算资金费通道，对照相同价格/波动率/资产输入；不同于旧联合Transformer/selector/CPD配方。[去重依据](NON_DUPLICATION.md) 与 [全部30远端head/551相关源码blob目录](BRANCH_INVENTORY.json) 保存来源，不声称重跑所有旧研究。

固定CORE5：2020只预热，2021拟合255资产周/51市场周；2022H1/H2分别125/123资产周、25/25市场周作**训练内诊断**。Monday七日非重叠标签，标签终点严格早于区间终点，跨年/半年度purge。共同因果输入掩码排除两个SOL资产周；缺未来价格硬停，不能按未来结果删样本。归一化和两模型参数只拟合2021；alpha1为sum squared residuals+1×slopes²，截距不罚，无HPO。

资金费窗固定 `[D−8日,D−1日)`：真实结算时钟严格早于D−24小时，未来事件不用于证明过去完整性。官方事件有毫秒抖动：初始精确整点QA导致预检失败、科学拟合0；冻结前改为名义间隔60秒容差，实际时钟不取整、不挪边界，缺事件仍不可用。过去168名义小时、价量时点和标签成熟均已核验。24小时滞后只是条件可用性代理，官方档案缺历史publication/receive时钟，**不声称真实as-of已认证**。

BASE27每边fee5.5bp、spread4bp、slip4bp，费用作用于执行后价格。单位short目标为 `(1−.0008)(1−.00055)−(Pexit/Pentry)(1+.0008)(1+.00055)`，除以过去30日波动率×sqrt7。固定每资产.12参考名义的独立周探针，在prediction>0时入场、否则现金；全部50市场周保留，各次支付入场和退出成本。代理不是共享钱包、复利账户或净收益；实际资金费、分钟执行、资金/风险路径和终端账户未绑定。未来资金费仅描述原率求和（名义小时160–176），未认证单位/charge mark/持仓数量，不入输入或现金。

数据复用已有公开Git `e0d3400b23842f11f167a63e7d80856d76501de8` 的2,246,454B三片档案，及既有十个真实SOL/XRP价格修补，官方行情新下载0。Arrow只投影2023前close/完整性及结算时钟/原率/名义间隔；24输入联合NPZ及未来执行/收费mark不作模型输入。2026锁、失落账本、旧CPD证据和另一研究文件均保留。

科学源码先在 `e347fa4f8dc5d65c9a419b45eb330476d8c734ed` 发布且逐字节远端读回，才执行两拟合。完整配置、seed811031、来源SHA和两模型scaler/coefficients见 [协议](PROTOCOL.json)、[来源绑定](SOURCE_BINDING.json)、[完整结果](results/RESULT.json) 和 [模型](results/MODELS.json)。不是原论文复现，也不是全新样本外。7项相关测试通过；全仓测试NOT_RUN。

## 最小保存模型复现

在该研究分支的已发布checkout运行（既有环境为Python3.12.14、NumPy2.5.3、PyArrow23.0.1）：

```bash
task_state=/workspace/short-funding-public-reproduction
revision="$(git rev-parse HEAD)"
COIN_CPD_STATE="$task_state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python research/short-funding-residual-20261011/public_replay.py \
  --revision "$revision" --state "$task_state"
```

使用全新STATE，从不可变远端提交逐字节下载清单、源码、两模型、结果与小历史档案；原预测/源读取算法不变，只有 `git show` 的INDEX读取改为同SHA公开INDEX字节。禁止fit/subprocess及旧workspace/STATE/cache读取；重放2模型、496个预测值与统计量。已有解释器/依赖复用，不声称新机器安装验证。训练原命令及守卫收据见 [完成记录](COMPLETION.json)。

守卫：1CPU/线程、4GB地址、2GB采样RSS、8GBhost、1200秒、10MiB任务输出、15GiB磁盘预留、GPU/swap0；为已声明的重构云版，不声称旧WSL cgroup原样恢复。真实两拟合+bootstrap+导出1.332秒，完整命令1.713秒，采样RSS99.82MB，未触发守卫。门槛失败后development/wallet/新模型均0。
