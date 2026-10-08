# 连续 E5 预算两臂原型：待父任务启动

原型交付与入口准备阶段0 fit；父任务随后核准输入并明确启动，现已 **恰好2 fit、各64epochs、0重拟合、0 新策略原生账户、GPU0、付费0、发单0**。仅此一个固定方案，不做参数/结构/种子搜索。Library 停用，未访问 Binance、locked 正文或 2025H2。

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

训练输入须保持 E5/CORE5 顺序、每专家目标可用时钟、完整过去协方差和真实日期。`pack.load_pack` 验证父任务核准的 manifest 与四个小 NPZ 的实际字节；teacher/source/mapper/market SHA 是原生 producer 绑定的来源，入口不假装重读小包中没有的完整原始文件。`validate_fragment` 继续检查时间范围、标签成熟与来源格式，不代替字节检查。不得使用包含已见尾段诊断的行拟合 scaler。

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

## 父任务可启动的有限预算与硬限额入口

冻结建议：**恰好两次 CPU fit**，共同 Adam lr=.001、betas(.9,.999)、eps1e-8、global gradient norm≤1、weight decay0、每臂64 full-fragment epochs；只保留 epoch64，不 early stopping、不 seed ensemble、不挑 checkpoint。每臂≤120秒、串行、≤2线程、process RSS≤1GB，服从已有8GB共享上限与零swap/GPU。任一 NaN、mapper违规、代理敞口 STOP 或超时，整对记 INCOMPLETE，不变更配方救结果。

`entry.py` 默认只检查输入，不训练；显式 `--mode run-pair` 才串行创建两个独立 worker。每臂硬墙钟120秒包括 import、加载、64epochs 和导出；独立进程组超时 SIGKILL，内核 RLIMIT_AS≤900,000,000B 从 exec 前生效，比 RSS≤1GB 更严格，额外每25ms查 RSS/线程；CPU affinity≤2、BLAS/OMP 等实际设1线程，线程总数≤2。只读核 active swap 必须为空，CUDA 可见设备置空、仅 NumPy。已有更严格上级限额保留。检查 worker≤30秒，无 GPU/付费。`fit_pair` 本身仍只有 epoch 边界软时钟，真实拟合必须走 supervisor。共享云机器总RAM限制由上级负责，本入口仅保证本次串行 worker 子预算。

原生 producer 从完整本地历史导出四片小包、获胜 candidate.request/成熟时钟、全部真实 funding events 与 strict-past marks、mapper/expert 来源。本入口现支持 producer 的 `BYTE_BOUND_DIRECT_PATH_FRAGMENTS_V1`，直接调用 `data_adapter.load_training_and_validation`，仅返回的3片进入fit。保留原字段/时钟/来源inputSHA，并另记delivered fragment SHA。对照核准原adapter，四片全部数组、时钟、43feature及训练mean/std完全一致，误差0；只增加受限字节快照与receipt一致性检查，没有改数据。没有新增行情下载。原生执行器将冻结 request 送入原 **E5 mapper→NativeDailySimulator→BybitIsolatedAccount**；不要重复拟合，勿把旧校准面板当训练集。

producer包commit `d69e9ac94478c5be54cb46c622afec7aaf3c61f7`，ZIP 214,624B、SHA `5c693dbae6a8702d5304d92e5890697a11ffa1f5579b69f05dd16322f248aef5`；INDEX SHA `e4fecc49cd1bb05f72dc0f8d24e793a5d7e4d2436c89a18bd9d7c625a7849be8`。ZIP15成员与全部memberSHA已核。receipt资金费525/465/1815/915条，各5条start事件明确fresh-cash跳过，globalend排除与代理末日q=0一致；末日午夜事件仍归前一interval。该producer schema不转换成下方通用V1，源字节保持原样。

### 冻结导出接口

两臂仅保留epoch64，不因训练代理数字改变配方。61日验证只作冻结request推理，不计算代理验证PnL、不挑参数/epoch。`freeze_evidence`只读已冻结头并复核输出，生成模型+scaler、397参数向量、每臂64条日志与逐训练片段代理路径，不调用优化器。冻结结果按用户既有公开GitHub保存授权发布至 `research_artifacts/direct_path_frozen_pair_20261008`；INDEX绑定同一118,740B原包及全部模型/request/scaler SHA，FEATURE_SCHEMA给出43列完整顺序与SHA。原生侧仅加载，不重复拟合。

### 小输入包 V1

manifest UTF-8 JSON，≤128KiB：`schema="DIRECT_PATH_TRAINING_PACK_V1"`、producer `source_commit`（40位SHA）、`symbol_order`/`expert_order` 为上述固定顺序，`fragments` 按表中四角色排列。每项包含 `window_id`、平面相对 `file`（NPZ）、`bytes`、`sha256`、`funding_events_complete=true` 与 `binding`（`teacher_jsonl_sha256`、`expert_identity_sha256`、`mapper_sha256`、`market_binding_sha256`）。实际 NPZ SHA 由入口填 `input_npz_sha256`。每个NPZ≤4MB、展开≤8MB、allow_pickle=False；不接受路径逃逸或重复文件。字段名不同可用该项 `field_map={canonical_name: producer_name}` 显式一一映射，不推断/放宽语义。

| NPZ canonical 字段 | shape / 单位 |
|---|---|
| decision_us、available_us、label_available_us | int64[T]，UTC微秒 |
| target_available_us | int64[T,5]，UTC微秒，每专家≤decision |
| expert_targets、eligible | float64[T,5,5] 有符号NAV比例；bool[T,5] |
| past_returns30、market13 | float64[T,30,5] 过去完整日simple returns；float64[T,13] 原causal特征 |
| prices、funding_coeff | float64[T+1,5] 正USDT/unit，completed daily close；float64[T,5] signed USDT/unit |
| greedy_request | float64[T,5] 原获胜one-hot REQUEST，末日排除标签 |
| funding_event_us、funding_symbol_index、funding_mark_close_us | int64[N]，事件UTC微秒、CORE5索引0…4、严格过去mark close UTC微秒 |
| funding_mark_price、funding_rate_fraction | float64[N] 正USDT/unit；raw signed fraction，scale1 |

T分别30/31/121/61，prices多一行表示右端日close。事件范围 `[start,end]`，初始同刻事件看到已声明现金；其余按 `(decision,next]` 汇总，下一决策同刻事件归前一持仓。入口重算 `sum(mark*rate)`，容差 rtol=atol=1e-12；拒绝重复事件/缺数据/非严格过去mark。真实事件覆盖由已核准 producer manifest 明确背书，不能从空事件列表推断没有funding。可选 `features43[T,43]` 必须与13+25+5构造逐值完全一致。非末日标签时钟≥decision+DAY且<split end，不因临界标签不足而放宽；末日仍付费平仓。

```sh
# 默认模式：仅校验。目录必须尚不存在；不能覆盖已有证据。
PYTHONPATH=src:. python3 -m modules.direct_path.entry \
  --manifest /path/to/manifest.json --approved-pack-sha256 PARENT_VERIFIED_SHA \
  --output /path/to/new-check-directory
# 仅在父任务明确启动后：恰好两臂，任一STOP整对INCOMPLETE，不改配方。
PYTHONPATH=src:. python3 -m modules.direct_path.entry --mode run-pair \
  --manifest /path/to/manifest.json --approved-pack-sha256 PARENT_VERIFIED_SHA \
  --output /path/to/new-pair-directory
```

输出 `pair.json` 包含实际 fits_started/completed、源码/包SHA、每worker资源测量和状态；共享一次训练集 standardizer。各臂只导出 epoch64 的397参数+mean/scale NPZ、模型SHA、三个独立训练钱包的代理报告。最终参数也再检查自身路径，避免把末次更新前收益冒称epoch64收益。H1_VALIDATE仅生成61个冻结head request与公共末日force_cash mask，绑定模型/输入SHA；不算验证代理收益、不挑epoch、不更新scaler。原生验证结果由执行器提供。本轮新增测试仅使用合成包/未拟合头与可终止sleep子进程，优化器调用0。

入口交付校验：32项 unittest 通过，实测1.20秒、35,799,040B主测试进程峰值RSS；包含默认check的真实受限子进程、120秒机制的缩短时限反例（SIGKILL）、RSS/线程STOP、unlimited AS拒绝、hash后磁盘突变仍解析原已核bytes、资金费符号/同刻边界及成熟时钟。测试未启动任何fit；这些测量不是未来完整包训练耗时。独立审阅发现的无限AS哨兵与字节重开竞态已修，配方不变。

训练后共同一次原生H1验证：2个独立10k钱包、同 cost/mapper/funding/risk/paid terminal，各≤600秒。总推荐硬墙钟≤1440秒；本轮没有消费该训练/验证预算。保持真实未决单、容量、margin及强平机制，报告原生净收益、全部成本/funding、分钟DD、gross/单资产、拒单/未决/强平与终端flat。若不能原生闭合，收益不可验收。父任务决定后续冻结评估，不因代理盈利或任何已见尾段结果放宽要求。

复现工程检查（当前明确指定云端 `/workspace` 环境；原AGENTS的WSL硬路径包装器不可用于此环境，未修改它）：

```sh
PYTHONPATH=src:. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  timeout 45 prlimit --as=4000000000 --cpu=40 python3 -m unittest \
  tests.test_direct_path_utility tests.test_direct_path_entry -v
PYTHONPATH=src:. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  timeout 45 prlimit --as=4000000000 --cpu=40 python3 -m modules.direct_path.calibrate \
  --panel-root /workspace/coin-state/direct-path-source --output /tmp/new-panel-calibration.json
```

校准目录把优先索引存为 `PANEL_INDEX.json`；脚本核固定索引SHA `5b6edb92…`。所有结果仅本轮代码/短协议入分支；模型、市场输入、JSON日志与包留任务STATE。仓库 `main` 不改、无forcepush、无PR。

## 思路来源登记

只读研究 [DeePM固定commit base.py](https://github.com/kieranjwood/deepm/blob/94aa148295d9147f6533f877256b663b918ed2e6/deepm/models/base.py) 与[论文v1](https://arxiv.org/html/2601.05975v1)。MIT[LICENSE](https://github.com/kieranjwood/deepm/blob/94aa148295d9147f6533f877256b663b918ed2e6/LICENSE)已读取。仅采用“连续预算/敞口→净换手成本→组合效用”的数学思路；全部新数学和梯度独立实现，复制代码0行、执行第三方项目代码0次、迁移模型框架0。论文为传统多品种期货研究，**不构成币圈盈利证据**。依本任务“仅源码/测试/简短协议”范围，来源登记置于本协议，未改全局registry/status。
