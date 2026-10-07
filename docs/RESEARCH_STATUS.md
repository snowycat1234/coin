# COIN 当前研究状态

投资资格 **NONE/CASH**；长期稳定净APR **NOT_EVALUABLE**。

## 2026-10-07：Transformer v2 开发完成，封存数据不可评价

当前决定 **B. CONTINUE RESEARCH, NOT YET PROMOTED**，投资 **NONE/CASH**。120个CUDA开发fit、24个past-only最终fit、720个开发任务、36个暴露对照和修正oracle诊断已完成；逐SHA核验764个唯一新账户，653个完整，111个保留真实风险停机前缀，不将前缀算为完整收益。固定跨资产utility/方向候选六窗口收益中位数 -1.7914% / -0.3479%，对旧Transformer配对中位差 -1.4509 / -3.9976 pct，开发gate失败。

封存正式数据门禁检查一次，**预测0、经济账户0**：WIF、1000SATS、ORDI 的2026-06-24 04:00资金费事件无法核实，最新月档未修正、日档404、官方历史接口451。2026-06-29十币mark/premium缺口已找到20份完整官方日档，但资金费仍阻止固定十币连续184日评价；不补零、不删日、不挑子窗口。完整封存经济实验尚未完成，不声称最终实证闭环或晋级。详见 [报告](../reports/transformer_v2/TRANSFORMER_V2_FINAL_REPORT.md)、FINAL_REVIEW_EVIDENCE.json、CURRENT_EVIDENCE_AUDIT.json。旧数据、模型、账本、D108及原正式N/E记录保留。

## 2026-10-07：归档采集与完整数据窗口验证模块

新增 [collector_research 模块](../modules/collector_research/README.md)。服务器上的四类模型研究已完成，验证复用40个模型折与372项产物；新原生账户验证先按输入完整性分段，788天排除UTC2024-08-12一个缺口日，6段787天，共96/96独立10k账户完整且真实平仓，独立NAV/钱包最大误差5.46e-12 USDT。最后24小时采用原持续、容量受限的收费平仓规则；缺口不补造，段间收益不相加或拼成一个钱包。

这不是D108原数据复现，也不是未见OOS。四类模型在两资金费条件下的共同窗口收益中位数均为负；原日频筛查的基线门槛均未通过，最终模型未拟合，不晋级、不部署，投资资格仍NONE/CASH。后验完整数据窗口不能解释为当时能够预知并避开未来缺口。详见 [实际结果](../reports/COLLECTOR_COMPLETE_WINDOWS_20261007.md) 与 [小型验收摘要](../reports/COLLECTOR_COMPLETE_WINDOWS_20261007.json)。旧D108判断与证据保留。

用户2026-10-07明确区分资源：服务器按实际配置，无项目CPU/RAM/swap/墙钟限制；本机限制继续。模块默认local，必须hpc_linux及8GB/swap0/GPU0；server需显式选择且拒绝WSL。当前服务器10CPU/33.65GB，性能切换复用76例、只继续20例。行情、模型、环境和大账本留在外部STATE。

## 最新实际经济结果与采用判断

D108自动ML selector实验已完成：SMA200_SIGNED/HOLD/CASH三冻结expert，26past-only特征，固定30/60/90d，正则线性与单套小XGBoost，5个purged chronological folds加H日额外embargo。实际440底层fit、350训练期scaler fit、158完整共享10k钱包；MLP按样本门槛跳过。后台Python独立完成，没有LLM/API参与实验流程。

事前utility-rank选出LINEAR_H60，未按最高回测PnL换成H30。BTC评价窗口2022-10-01至2024-01-01，实际457日；2022仅Q4。全部已见开发/内部时间验证，不是独立OOS；FINAL LOCKED TEST未读未跑。

|方案|RAW净USDT|PCT净USDT|RAW/PCT实际年化波动|RAW/PCT分钟MDD|RAW/PCT Sharpe|
|---|---:|---:|---:|---:|---:|
|LINEAR_H60|1446.38|1614.65|10.42%/10.43%|6.41%/6.20%|1.088/1.198|
|SMA200_SIGNED|827.62|971.38|10.64%/10.64%|9.69%/9.54%|0.650/0.749|
|HOLD|1842.31|2080.75|10.64%/10.63%|7.32%/7.31%|1.323/1.473|
|固定SMA/HOLD/CASH=.5/.25/.25|896.98|1023.79|6.54%/6.54%|5.26%/5.11%|1.082/1.223|

RAW/PCT是资金费未确认单位的两条件解释，不选择更盈利者当事实。selector胜SMA、旧人工map和各类placebo的经验95分位，但没有胜最强static HOLD：净差−395.93/−466.09，oracle-gap capture为−31.29%/−38.47%，2022Q4改善、2023未改善，未达事前门槛。相对HOLD有小幅DD改善，但Sharpe及净收益更低；实际vol接近，不能把相同caps当严格风险匹配。

## 钱赚在哪里、亏在哪里

selector在2022Q4 SHORT净+367.93/+350.23；2023 SHORT净−553.21/−558.07，LONG净+1631.66/+1822.49。457日SHORT总贡献−185.28/−207.84，SHORT毛价格损益已为负，不是费用吞掉正alpha。全部手续费+执行约49.90/49.94；主瓶颈是反弹期方向/专家选择及多头参与不足。相对SMA200减少反弹空头损失，但还不足以胜HOLD。

独立复核158账户、6.43GB实际工件SHA、4026个成熟标签、训练期scaler均值、purge/embargo、日收益/Sharpe/vol及资金桥接通过；钱包/NAV最大误差1.82e−12 USDT。同一H60成熟日期上，selector加权utility-rank为0.56697/0.56899，低于恒定HOLD的0.63995；预测排名目标也未胜强常量基准。仅16个每类shuffle的经验95分位不是p<.05证据（即使全部胜出，未校正有限尾概率下限仍1/17=0.0588）；六模型方案在同一验证池选择也未做选择偏差校正，不能声称regime alpha。训练R²高而所有H60季度验证R²为负，utility校准迁移弱；近常量标签会放大R²幅度，不把该统计直接当唯一投资结论。

## 当前保留、暂停与下一步

**不晋级ML selector，不追加模型复杂度或调温度/阈值。** 保存线性/树能力、全部试验、模型与失败，SHORT方向保持一级研究方向。冻结SMA200多空作为透明方向参照；既有SMA200仅多作为风险效率参照，风险管理HOLD作强基准，固定三expert作低风险控制。没有合格投资主力，不能把本窗口HOLD事后胜出解释成实时regime选择。

下一主任务：先核已有D043完整2024年1–7月213日输入，在相同冻结三expert/费用/完整资本与风险口径下核对跨窗口条件优势及oracle机会是否仍存在；零新增ML拟合、零搜参。2024同样已见，只称迁移开发核对，不是独立validation。该小闭环区分“机会只在一个周期存在”与“当前过去特征/标签校准未能迁移”，比继续救模型更有信息价值。若没有持续条件优势则保留强单策略/静态控制；只有多个完整市场阶段给出稳定排名信息或可靠新增因果特征，才reopen learned selector。

[自动最终报告](../reports/SELECTOR_ML_REPORT.md)；[最终结果/账本引用](../reports/SELECTOR_ML_RESULTS.json)；[独立复核](../reports/SELECTOR_ML_INDEPENDENT_REVIEW_20261006_V1.json)；[启动/恢复](SELECTOR_RUNNER.md)。旧D105/106及所有负结果按Git和既有报告保留，不覆盖。

## 数据、资本与资源边界

Binance USD-M行情+Bybit用户费用为跨场所代理；27bp往返费用/点差/滑点固定，实际资金费按两个条件解释。原生数量/MMR/资金费单位及历史费用仍未认证。完整10k资本、abs单币30%/gross60%、永续单向逐仓1x/无自动追加保证金；真实risk减仓不关闭，瞬时caps漂移与执行延迟保留报告。N资产和SHORT能力保持，本次BTC实验不代表10币组合已验证。

RAM共享8GB、swap0/GPU0、D项目+整个WSL VHD150GB（120预警、135停止新增、15预留），按用户2026-10-05扩容。实际DAG运行6363秒，账户worker峰值RSS595.23MB；末次共享RAM采样7.79GB，完整共享组运行峰值未保存、重启后不能补称旧值。158账本文件共6.43GB；2026-10-06 16:17保存前实测总磁盘45.45GB；当前实际磁盘扫描见本模块close，不拿旧扫描冒充当前。

## 运维

8765沿用。D108完成后核对到WSL新boot、原采集进程缺失；退出原因UNKNOWN，不能归因用户或OOM。已保存41份原DB/WAL/SHM、日志、checkpoint和闭合SQL副本/audit head，按原只读源/5GB coin-quant子组恢复；两次实际PID/source binding核对一致、public心跳+75117ms、micro新增17610事件且asof推进，连接已实测。具体证据见SELECTOR_COLLECTOR_RESUME_SAMPLE V1/V2；不注入工程升级，不拼接连续健康时间。采集恢复证据单独记录，离线历史结果有效性不依赖此轮采集存活。无密钥/账户/发单/付费/GPU/封存正文。

## 2026-10-07：Transformer v3 强平修复，回放准备验收

用户授权独立分支 research/transformer-v3-oracle-policy。已完整 hash 保留 v2 HEAD0350589及16,025个外部保护文件，旧正式locked N/E保持。五种缺失资金费估算已在任何新经济结果前登记。逐仓接管不会因单币强平停止整钱包；27项服务器测试通过，真实864行冻结回放尚未完成，新模型fit与locked经济结果尚未运行。十个官方risk档位请求403，因此MMR=.005/MMD=0只能作为明确声明的条件研究假设，不能称真实档位认证。投资资格NONE/CASH；先核两个真实窗口，再全量回放和neutral分析。详见 [模块](../modules/transformer_v3/README.md) 与 reports/transformer_v3/V2_REPLAY_PROTOCOL.json。
