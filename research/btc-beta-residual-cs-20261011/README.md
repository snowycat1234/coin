# BTC beta残差排名：相同对冲的成对实验

最终：`STOP_THIS_84_21_RECIPE`，仅停止本轮84/21配方。固定2021Apr5–Jun7四个真实历史条件账户全部完成、付费终端CASH，独立Decimal逐分钟现金/持仓/资金费/清算顺序核验PASS；每钱包两次DOGE逐仓清算，所有清算现金保留。完整经济源码fd7083ce先公开，17关键文件实际字节读回后运行；4钱包100.708秒/完整命令106.612秒，采样RSS317.95MB、GPU/swap0、无资源停止。额外fit/开发/新窗口0。

|资金费原率尺度|raw净USDT|residual净USDT|成对净增量USDT|alt毛价增量|BTC对冲毛价增量|raw/residual实际年vol|
|---|---:|---:|---:|---:|---:|---:|
|1|−211.0803|−324.8188|−113.7385|−65.3912|−49.1419|11.438% / 12.757%|
|.01|−194.1430|−311.5880|−117.4450|−65.3790|−49.2168|11.426% / 12.749%|

成对14日联合bootstrap1000次/seed811084，净增量条件95%区间分别[−874.68,+555.11]和[−880.29,+549.71]USDT。8经济门槛仅完整收费清仓/独立审计通过，其余7失败。残差/对照实际vol比1.1153/1.1159；minuteMDD分别7.183%/8.461%和7.096%/8.359%，不能把共同目标下缩称风险匹配alpha。全部资本10k，四独立钱包不相加。Binance行情/Bybit费用、单位/严格过去分钟mark/MMR仍条件化，不是原生市场、全新样本外或长期APR。

已实际完成后续无拟合账本取证：两组清算数相同，残差组清算损失反而略少（457.76/458.24 vs460.11/460.56USDT），故成对较差不是多一次清算。负增量主要来自alt和BTC毛价，额外费用+执行仅约2.887USDT，资金费抵销+.0369…+3.6817USDT；不把清算损失再加一次或制造无清算反事实。目标beta误差近0，但实际持仓的模型beta绝对均值约.0034、最大约.0557。详细结果`economic-results/RESULT.json`、四`CASE_*.json`及`SAVED_WALLET_FORENSICS.json`。

25相关因果/适配/当前内核测试PASS，加3无损存储测试PASS。完整测试失败也保存：旧V2 AST适配器要求前代controllerSHA，与当前冻结内核不兼容；新12分钟合成例最初缺UTC日终，修测试起点后通过，没有改金融语义或真实窗口。13.383MB公开账本包保存全部实际journal、summary、daily、targets及17个原始逐分钟审计列的逐位无损字节。其余20个冗余风险/equity列仍在原STATE，绑定原full37列ParquetSHA；不声称原完整Parquet字节冷恢复。公开预算20MB保持，不重复发布166.7MB行情包。

最小完整复现（原经济执行在fd7083ce；原目标科学执行在3f62a0f1，导出修复10268d29）：

```bash
export COIN_CPD_STATE=/workspace/btc-beta-reproduction
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  research/btc-beta-residual-cs-20261011/restore_minutes.py \
  --state "$COIN_CPD_STATE" --features /workspace/short-funding-residual-state/source/features.zip
# 在干净fd7083ce源码工作区；原协议禁止在研究中重复账户。
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  research/btc-beta-residual-cs-20261011/economics.py --state "$COIN_CPD_STATE" \
  --features /workspace/short-funding-residual-state/source/features.zip \
  --source-commit fd7083ce17c566dcf1e79a84a1df4da25962bbfc
# 无模型/账户重跑的公开恢复，使用公开结果提交SHA：
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  research/btc-beta-residual-cs-20261011/cold_verify.py \
  --commit RESULT_COMMIT --state /workspace/btc-beta-cold-fresh
```

2021是已有开发/训练历史；2023/2024和2026保留集未读取。恢复绑定完整来源/字段/校验/单位、科学attempt1、1476+740OLS、神经0、额外拟合0、wallet4和种子均在小JSON中。旧资金费/CPD STOP保持，原失落2026账本未捏造；本模块不是Slow Momentum论文原样复现，也不重复旧“移除alt short换BTC short”规则。

首个真实里程碑：2021因果配置门槛PASS，51个成熟周中27个改变alt配置（52.94%）；最大模型beta误差3.3331e−17、共同目标协方差波动上限10%，未来后缀扰动过去目标误差0。9项数学/因果/身份/周期测试PASS。原始执行源码3f62a0f1，primary过去OLS1476次，前缀反事实过去OLS740次，共2216次；1科学尝试、神经fit/未来结果查询/钱包/开发读取0。

最终JSON遇到NumPy布尔序列化故障；保存目标、回归系数、排名与风险工件完整。10268d29只修导出类型，用保存工件恢复门槛，额外fit0。原失败导出保留为`diagnostic/ORIGINAL_FAILED_EXPORT.partial.json.txt`。完整结果与必要模型见`diagnostic/DIAGNOSTIC_RESULT.json`和`SAVED_TARGETS.npz`。这些是因果配置差异，尚无经济收益结论；下一阶段严格按原协议固定63日/4钱包运行。

独立分支 `research/btc-beta-residual-cs-20261011`，此前启动取消未运行新实验；本模块是一次固定84日回归/21日形成/周排名检验，不调整旧资金费和CPD STOP。

先对2021做因果性、共同掩码和选择差异检查，通过冻结分配门槛才运行固定2021Apr5–Jun7的4个独立共享钱包：raw/residual×两种资金费单位解释。候选都是ETH/SOL/XRP/DOGE，BTC只作回归市场与对冲；两边都保留alt空头，同算法对冲和统一风险下缩，所有对冲换手付费。不是共同减BTC收益，也不同于父本地旧“移除alt空头、替换BTC空头”配方。

31远端head和工作区状态核实，无该已运行实验。父本地三条旧对冲SHA在当前Git不存在，记录为未恢复，不能宣称读回其30钱包。原21日累计收益、top/bottom2、周Monday锚和10%/30%/60%约束来自已公开CS源码。

回归带截距，残差信号按最近21个 `r_i−alpha_i−beta_i*r_BTC` 求和；只用截至当天的84个已完成日收益。原始排名保留原21日累计价格收益。共同风险控制使用同30日简单收益协方差；拟合beta以log收益定义，不能当作完美实现的实际风险中性。

概念可参照作者的股票[Residual Momentum](https://www.sciencedirect.com/science/article/pii/S0927539811000041)；全文访问403，未绕过，未声称复现原三因子股票论文。当前仅为明确冻结的一因子BTC加密适配。见[完整冻结协议](PROTOCOL.json)。

输入优先复用公开Git对象。2021Jan-Nov分钟trade/mark已公开完整，December全mark tape缺失，所以先固定一个63日训练经济窗口；不依盈亏挑月份，不读取开发验证或2026保留集。金融内核保持原字节，资金费单位、精确收费mark、历史publication与native风险阶梯仍条件化；不得称原生钱包实绩、风险匹配alpha或全新OOS。
