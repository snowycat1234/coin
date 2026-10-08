# 连续 E5 预算两臂原型：待父任务启动

本轮 **0 fit、0 新策略原生账户、GPU0、付费0、发单0**。代码、合成检查、既有固定路径校准已完成；`training.fit_pair` 已实现但未调用。仅此一个固定方案，不做参数/结构/种子搜索。Library 停用，未访问 Binance、locked 正文或 2025H2。

## 两臂契约

- 冻结 E5 顺序：CASH、VOL_MANAGED_HOLD、PUBLIC_SMA50_200_SIGNED、DONCHIAN_EXIT10、CSMOM21。CORE5 顺序：BTC、ETH、SOL、XRP、DOGE USDT；RANK 排除。
- 共用同一个 **43→tanh8→softmax5、397 参数**头；seed=20261009，完全相同初始参数。输入严格相同：已有 causal market13、25 个冻结有符号专家目标、5 个可用性位。两臂都不喂 teacher 钱包/预算状态，不新增持仓记忆。前处理在训练片段合计数据上计算一次 mean/std，constant std≤1e-8 用1，验证不参与。
- 输出为连续 E5 **request**，不直接输出 CORE5 仓位。softmax 支持 simplex 内部 soft 预算，边界 one-hot 由固定教师/控制提供；最后一天由共用原生规则强制零仓位。不得宣称头能在有限 logits 下精确输出 one-hot CASH。
- 共用既有 mapper：不可用专家预算先释放给 CASH；对释放后 prior/request 做 L1≤0.1 ramp；按冻结专家有符号 targets 分配腿；**netting 前**检查单标的 allocated gross≤0.3、全组合≤0.6；执行一个净钱包；按过去30完整日 simple returns、sample covariance ddof=1、×365 检查 annual vol≤10%。冻结专家已缩放，本原型不再次缩放，也不静默裁剪超限目标。
- A=`IMITATE_REQUEST`：逐日 CE 拟合原 native greedy 实际获胜候选的 **one-hot request**。不拟合 ramped budget，否则会重复 ramp。共用片段最后现金日排除监督标签。教师是自路径状态的一日局部贪心，A 在自己预算路径使用这些离策略标签；该分布偏移明确保留。
- B=`DIRECT_PATH_UTILITY`：在自身连续预算/数量/NAV 路径最大化 `mean(log(V_next/V) - 5*min(V_next/V-1,0)^2)`。包含最终现金日 paid close。解析梯度穿过 eligibility release、原 L1 ramp 的当前分支、数量延续、wallet compounding、全部 BASE27 成本和 funding。L1 kink 采用 sign(0)=0 子梯度；没有平滑掉约束。
- 连续 soft 预算的动作集比教师的五个 one-hot 请求更大；greedy teacher 既非全路径上界，也非连续动作集上界。创新仅检验直接路径效用目标，未迁移 DeePM 架构。

## 固定时间与资金协议

| 角色 | UTC 起止，右端不含 | 钱包/预算初值 | 最后一天 |
|---|---|---|---|
| TRAIN BEAR2022NOV | 2022-11-01 → 2022-12-01 | 独立10,000 USDT、100% CASH | Nov30 强制零目标并付费清仓 |
| TRAIN RECOVERY2023JAN | 2023-01-01 → 2023-02-01 | 独立10,000 USDT、100% CASH | Jan31 同上 |
| TRAIN H1_TRAIN | 2024-01-01 → 2024-05-01 | 独立10,000 USDT、100% CASH | Apr30 同上 |
| VALIDATE H1_VALIDATE | 2024-05-01 → 2024-07-01 | 独立10,000 USDT、100% CASH | Jun30 同上 |

三个不连续训练片段分别闭合，不能跨 Nov→Jan→H1 日期缺口拼收益。H1 按固定时间再分训练/验证；May1 的验证是另一个独立钱包，不继承训练末仓，不合加独立钱包 NAV。训练182个日区间，A179个可优化标签；B182个含付费边界的区间。验证61日。各一日学习标签 `label_available_us >= decision_us + DAY_US` 且严格早于对应 split cutoff；最后强制现金日不学习。

训练输入须逐文件验证 NPZ/teacher JSONL/source/mapper/market SHA，保持 E5/CORE5 顺序、每专家目标可用时钟、完整过去协方差和真实日期。`validate_fragment` 检查时间范围、标签成熟和 SHA 格式；**它不是文件内容验签器**，父任务输入 adapter 必须核实原字节。不得使用 `TRAIN_ARRAYS` 内包含已见尾段诊断的行来拟合 scaler。

2024尾段/2025H1仅为已见诊断；本轮尾段只是指定执行失败见证，不参与训练、验证、超参数、架构、checkpoint 或门槛选择。2025H2由父任务冻结评估，本原型完全不读取它。

## 日级代理的精确含义与局限

`q_t = .99 * V_t * mapped_target_t / completed_daily_close_t`。同一资产交易量是 `abs(q_t-q_previous)`，不累计专家腿换手。代理用 midpoint PnL：spread4bp+slippage4bp各记一次，fee5.5bp按不利 fill 名义计算；真实 fill-cashflow bridge 则只另扣 fee。费用全额系数1，不采用论文的成本放松系数。

`funding_coeff[t,i]=sum(strictly_past_event_mark * raw_rate)`，事件归属 `(decision_t,decision_next]`，同时间 funding 先于下一次 fill，符号 `-signed_quantity * coeff`；仅作为未来历史效用，不进入 causal features。初始时点为已知零持仓。缺 price/mark/rate/时钟停止，不补零。终端现金日只对残仓收费一次；end-minus6min 原生备用清仓在已经零仓位时不重复计费。

日级代理合并 sizing close / trade midpoint / mark，并假设全量即时成交。**不能表示**一分钟延迟、前一分钟 quotevolume 的0.1%容量、减仓优先及未决订单、lot 舍入、10USDT opening minimum、partial fill/五次到期、持续 zero-close、free collateral、funding 对逐仓 margin 的消耗、分钟风险减仓/阻塞/再入场、MMR/强平/bankruptcy 接管、不同 mark/trade 与盘中 extrema。代理边界实际敞口>30%/60%直接 STOP，不发明可微的风险减仓。原生 controller 也不能承诺瞬时 caps 从不短暂漂移。

BASE27、1x逐仓、scale1、MMR.005及 Binance 历史行情配 Bybit 费用均为现有研究假设，非认证实盘执行。代理盈利不是真钱，也不能据此晋级投资。

## 既有固定路径校准

先按已指定 H1 FAMILY 路径核 mapper，后用父任务优先小面板核账；两种 H1 输入结果一致。按SHA最小读取7b5b9f7包的000/009/010 parts与所需成员；未重组全部11 parts，**不声称验证完整ZIP SHA a998…**。原源码包SHA `9fed06d2…` 已核；当前本地 `perpetual_account.py`/`bybit_isolated_account.py` 与包内源码字节完全相同。

优先面板：[INDEX@19e81198](https://github.com/snowycat1234/coin/blob/19e81198380656713cbf8f5ecdebaa0c21e9ebc8/research_artifacts/fixed_path_calibration_20261008/INDEX.json)。gzip delivered 与 decoded SHA 都核实。无新原生 replay、无新行情。

| 固定 H1 FAMILY，182日 | 结果 |
|---|---:|
| 全182日 budget / mapped target 最大误差 | 0 / 0 |
| 最大 mapper past covariance annual vol | 9.5841423% |
| 715成交、2730 funding：逐笔 fee / execution / funding 最大误差 | 0 / 0 / 0 USDT |
| midpoint 与 fill-cashflow 两条净收益 bridge 误差 | 2×10^-35 USDT |
| 原生净利 / 日级代理净利 | 466.536471 / 462.304468 USDT |
| 代理减原生净利 | −4.232003 USDT（−4.232003bp/10k） |
| 日增量 MAE / 最大绝对误差 | 0.258440 / 2.202024 USDT |
| 日末 NAV 最大绝对误差 | 6.223147 USDT |
| fee / execution / funding 总误差 | +0.367201 / +0.534108 / −0.046813 USDT |

指定 E6 Ridge 尾段失败见证：682成交/2130 funding、1次 DOGE takeover；账本桥误差1.2461×10^-35、费用与funding逐笔误差0，原生净亏−1404.788206。本代理在第25号日、Sep8边界 gross60.84686% STOP，**没有该路径代理全程利润**。原2,881分钟 witness 中，Nov10 00:45Z DOGE数量−4544.27422697→0；508.77620053抵押损失已在 takeover close ledger，不能再次扣。H1的小误差不构成别的策略的误差上界，特别不覆盖容量和强平。

21个测试通过：cash、fixed long/short、净换仓/腿netting、单位延续、缺失数据/身份/时钟、资金费正负与strict-past mark、起止付费、真实原生固定 fills、合法flip共用fill_id/重复腿拒绝、takeover不重复扣损失、日期缺口、一日标签提前成熟反例、caps/vol STOP、两个目标及全链解析梯度。独立只读审阅另测 availability 切换全链方向导数，误差3.09×10^-11；已修复其发现的一日标签成熟边界检查与合法flip账本腿身份，未改变目标/参数。

## 父任务可启动的有限预算与剩余入口

冻结建议：**恰好两次 CPU fit**，共同 Adam lr=.001、betas(.9,.999)、eps1e-8、global gradient norm≤1、weight decay0、每臂64 full-fragment epochs；只保留 epoch64，不 early stopping、不 seed ensemble、不挑 checkpoint。每臂≤120秒、串行、≤2线程、process RSS≤1GB，服从已有8GB共享上限与零swap/GPU。任一 NaN、mapper违规、代理敞口 STOP 或超时，整对记 INCOMPLETE，不变更配方救结果。

线程/RSS及可中断的硬超时必须由父任务外部运行包装器施加；`fit_pair` 自身只在 epoch 前后检查120秒，不声称它独立保证上述资源封顶。本轮21项检查实测约0.53秒、31.7MB峰值RSS；这不是未来完整数据训练/原生验证的资源测量。

启动前父任务需完成：3训练片段与独立H1验证片段的只读 byte-bound adapter；从原 teacher 行提取获胜 candidate.request 与成熟时钟；按全部真实 funding events 和 strict-past marks生成代理系数；绑定 mapper/expert SHA；将冻结头 request逐日送入原 **E5 mapper→NativeDailySimulator→BybitIsolatedAccount**。此 adapter/完整数据准备本轮未执行，勿把小面板当训练集。

训练后共同一次原生H1验证：2个独立10k钱包、同 cost/mapper/funding/risk/paid terminal，各≤600秒。总推荐硬墙钟≤1440秒；本轮没有消费该训练/验证预算。保持真实未决单、容量、margin及强平机制，报告原生净收益、全部成本/funding、分钟DD、gross/单资产、拒单/未决/强平与终端flat。若不能原生闭合，收益不可验收。父任务决定后续冻结评估，不因代理盈利或任何已见尾段结果放宽要求。

复现工程检查（当前明确指定云端 `/workspace` 环境；原AGENTS的WSL硬路径包装器不可用于此环境，未修改它）：

```sh
PYTHONPATH=src:. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  timeout 45 prlimit --as=4000000000 --cpu=40 python3 -m unittest tests.test_direct_path_utility -v
PYTHONPATH=src:. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  timeout 45 prlimit --as=4000000000 --cpu=40 python3 -m modules.direct_path.calibrate \
  --panel-root /workspace/coin-state/direct-path-source --output /tmp/new-panel-calibration.json
```

校准目录把优先索引存为 `PANEL_INDEX.json`；脚本核固定索引SHA `5b6edb92…`。所有结果仅本轮代码/短协议入分支；模型、市场输入、JSON日志与包留任务STATE。仓库 `main` 不改、无forcepush、无PR。

## 思路来源登记

只读研究 [DeePM固定commit base.py](https://github.com/kieranjwood/deepm/blob/94aa148295d9147f6533f877256b663b918ed2e6/deepm/models/base.py) 与[论文v1](https://arxiv.org/html/2601.05975v1)。MIT[LICENSE](https://github.com/kieranjwood/deepm/blob/94aa148295d9147f6533f877256b663b918ed2e6/LICENSE)已读取。仅采用“连续预算/敞口→净换手成本→组合效用”的数学思路；全部新数学和梯度独立实现，复制代码0行、执行第三方项目代码0次、迁移模型框架0。论文为传统多品种期货研究，**不构成币圈盈利证据**。依本任务“仅源码/测试/简短协议”范围，来源登记置于本协议，未改全局registry/status。
