# BTC beta残差排名：相同对冲的成对实验

首个真实里程碑：2021因果配置门槛PASS，51个成熟周中27个改变alt配置（52.94%）；最大模型beta误差3.3331e−17、共同目标协方差波动上限10%，未来后缀扰动过去目标误差0。9项数学/因果/身份/周期测试PASS。原始执行源码3f62a0f1，primary过去OLS1476次，前缀反事实过去OLS740次，共2216次；1科学尝试、神经fit/未来结果查询/钱包/开发读取0。

最终JSON遇到NumPy布尔序列化故障；保存目标、回归系数、排名与风险工件完整。10268d29只修导出类型，用保存工件恢复门槛，额外fit0。原失败导出保留为`diagnostic/ORIGINAL_FAILED_EXPORT.partial.json.txt`。完整结果与必要模型见`diagnostic/DIAGNOSTIC_RESULT.json`和`SAVED_TARGETS.npz`。这些是因果配置差异，尚无经济收益结论；下一阶段严格按原协议固定63日/4钱包运行。

独立分支 `research/btc-beta-residual-cs-20261011`，此前启动取消未运行新实验；本模块是一次固定84日回归/21日形成/周排名检验，不调整旧资金费和CPD STOP。

先对2021做因果性、共同掩码和选择差异检查，通过冻结分配门槛才运行固定2021Apr5–Jun7的4个独立共享钱包：raw/residual×两种资金费单位解释。候选都是ETH/SOL/XRP/DOGE，BTC只作回归市场与对冲；两边都保留alt空头，同算法对冲和统一风险下缩，所有对冲换手付费。不是共同减BTC收益，也不同于父本地旧“移除alt空头、替换BTC空头”配方。

31远端head和工作区状态核实，无该已运行实验。父本地三条旧对冲SHA在当前Git不存在，记录为未恢复，不能宣称读回其30钱包。原21日累计收益、top/bottom2、周Monday锚和10%/30%/60%约束来自已公开CS源码。

回归带截距，残差信号按最近21个 `r_i−alpha_i−beta_i*r_BTC` 求和；只用截至当天的84个已完成日收益。原始排名保留原21日累计价格收益。共同风险控制使用同30日简单收益协方差；拟合beta以log收益定义，不能当作完美实现的实际风险中性。

概念可参照作者的股票[Residual Momentum](https://www.sciencedirect.com/science/article/pii/S0927539811000041)；全文访问403，未绕过，未声称复现原三因子股票论文。当前仅为明确冻结的一因子BTC加密适配。见[完整冻结协议](PROTOCOL.json)。

输入优先复用公开Git对象。2021Jan-Nov分钟trade/mark已公开完整，December全mark tape缺失，所以先固定一个63日训练经济窗口；不依盈亏挑月份，不读取开发验证或2026保留集。金融内核保持原字节，资金费单位、精确收费mark、历史publication与native风险阶梯仍条件化；不得称原生钱包实绩、风险匹配alpha或全新OOS。
