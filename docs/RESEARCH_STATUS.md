# COIN 当前研究状态

投资资格 **NONE/CASH**；长期净APR **NOT_EVALUABLE**。

## 最新实际经济结果

D105把冻结expert目标放入真实单10k钱包。两资金费条件oracle相对最佳单expert增量3335.69/3386.30，比shadow诊断低27.93/28.69，机会门槛保留，但oracle未来知情始终不算候选。八expert等权弱于原仅多；固定SMA200/HOLD/CASH=.5/.25/.25降低实际波动/回撤、提高Sharpe，但净收益低于原仅多，两条件均未达替换门槛。投资NONE/CASH，原SMA200仅多风险效率参照及多空正SHORT挑战者保留。

PCT实际oracle净5799.64（比最佳单expert2413.34增3386.30），DD6.62%、vol10.37%；未来知情、绝不作为可行策略或投资证据。真实账户净收益比shadow诊断低28.69。固定三expert净1377.58、SHORT189.50、Sharpe1.217、DD5.11%、vol5.42%；原LO净1563.48、Sharpe1.121、DD6.23%、vol6.68%。静态分散改善风险，但不是净收益全面优势；相同caps未等风险。

## 当前研究问题与下一项

D106单一slow×fast×vol固定软映射未通过事前排名门槛：RAW/PCT平均加权排名0.67049/0.69400，静态三expert0.63839/0.66518，最佳单expert与只用成熟过去排名均0.64286/0.69643；虽胜同频随机和滞后60日特征，未超过打乱状态95%对照0.67637/0.70124，两年相对优势也不一致。仅8个评价标签，不声称regime alpha；暂停这个映射，保留SHORT与专家库。

用户现已授权有限ML selector，覆盖此前未开放classifier的暂缓。本轮D108只保留冻结SMA200_SIGNED/HOLD/CASH，26past-only特征、H30/60/90、正则线性与单套小XGBoost；MLP样本不足跳过。DATA_SPLIT_AUDIT读取2157个历史metadata/manifest与选择记录，2022–23明确已见，季度purged walk-forward加H日额外embargo是内部chronological validation，非独立OOS；locked正文不读。

训练前协议已commit/push `0dc2f2f` 并核远端；两日真实共享钱包接线QA通过（2880分钟、paid flat、独立资金/NAV核验，0fit）。首个后台启动因systemd缺WSL标识被bounded守卫阻止（0fit），启动修复已commit/push `6e41645`；原协议保留，runtime_fix只改launcherSHA/新目录，其余科学协议完全相同。2026-10-06 14:06后实际核对后台coin-selector-v1存活，runner PID13164、原生阶段DATA、state/selector_progress.json持续更新；完整自动DAG现 **RUNNING**，断点/恢复与日志在既有D-hosted STATE。最终模型净收益 **NOT_YET_READ**，不需要LLM/API逐折参与。预算2worker各2线程、8小时、12GB新增空间预留，原采集不动。入口/恢复/只读状态见[SELECTOR_RUNNER](SELECTOR_RUNNER.md)，配置见[selector_v1](../configs/selector_v1_runtime_fix.yaml)。60主CV组和320shuffleCV组，最多1080底层fit；故障最多一次额外重试，保留attempt。成功需两资金费条件均胜static、各placebo95%、两年评价段改善、capture至少15%及既定风险门槛；仍只是已见开发筛选，不晋真钱。

原SMA200仅多风险效率参照及正SHORT多空挑战者保持；静态三expert保留控制。暂停已测D106人工映射、D101硬过滤、D102无重入CE、八expert等权主力与旧ML/4h网格，能力和负结果保留；新ML仅上述有限预注册对照，无密扫。2022 shortcapture仅验证Q4的92日，不冒称全年；资金费单位/原生数量与MMR的不确定仍限制投资结论。
[实际榜单](CTA_LEADERBOARD.md)；[完整经济与排名证据](SHORT_SELECTION.md)。

## 数据、账户与资源边界

实际BTC730日、2021预热、官方分钟成交/mark及实际资金费不变；ETH官方2022年7月mark仍缺11分钟，相关账户暂停，只接受合法完整真实输入reopen，不填零/删日期。N资产能力保持，BTC对照不是历史10币池完成。已看历史继续开发角色，不启封locked。

完整资本10k、abs单币30%/组合gross60%、单向逐仓1x、无自动加保证金保持；实际波动/DD、gross/net/保证金及瞬时cap漂移与减仓延迟分别记录。Binance价格配Bybit用户费是跨场所代理，资金费单位两条件解释、MMR/数量及历史费用未原生认证。金额/数量精度保持。

共享RAM8,000,000,000B、swap0/GPU0、D项目+整个WSL VHD150GB（120预警/135停新增/15预留）。上一经济模块D105：6新730日组合账户+4完整控制复用，最多2并行各2线程/1.2GB守卫，实际任务304.6,565.5秒、RSS峰值746.0MB、共享采样峰值3.15GB，新增目录392.4MB。本轮D106只读排名探测0新账户/行情/训练，核心计算0.65秒、RSS峰值244.5MB；核心时间不等于全部原生任务时间。实际区间并集/最新磁盘扫描时刻见D106 close，不把D105采样或旧扫描当本轮。

## 运维与证据

8765沿用；原public/micro公开采集存活核对另报，断档不拼72h资格。完整目标/权重/费用及Decimal资金NAV通过，真实平仓，不删残仓。未来知情oracle不进入候选；D106状态可预测性及排名placebo已测并未通过；可行adaptive账户净收益仍NOT_RUN。无真钱/密钥/发单/付费/GPU/封存正文。
