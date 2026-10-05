# COIN：当前有效执行规则

用户2026-10-05已采纳快速研究工作流，精确原文 `docs/archive/COIN_FAST_RESEARCH_WORKFLOW_USER_20261005.md`。它覆盖重复文档、逐小任务发布和固定多agent要求。投资质量与资金/数据/资源边界保持；旧指令与结果按Git和既有archive复现，当前状态只看 `docs/RESEARCH_STATUS.md`。

## 权限与资源

- 普通研究自主：先核HEAD/diff、实际任务和必要经济结果，再选有限高价值问题；不重做已完成修复、不覆盖他人WIP、不无限搜参。
- 所有Python/测试/训练在hpc_linux WSL，经 `scripts/with_task_progress.sh` → `scripts/bounded.sh`；D盘ROOT `/mnt/d/codex/coin` 与STATE `/home/xflops/coin-state`，数据/缓存/临时不占C盘。
- 共享RAM最多5,000,000,000B（当前守卫4,999,999,488B），swap0、GPU0。项目+整个D盘WSL VHD合计40GB；32GB预警、36GB停止新增，保留守卫预留空间。不改硬规则、不拿旧扫描伪作当前值。
- 完整共享资本10k，单币abs名义30%/组合gross60%，累计各资产/产品/策略腿；永续单向逐仓1x、无自动加保证金。不得自行增资本/caps/杠杆。
- 不读取账户密钥、真钱、Testnet/mainnet发单、付费、规避交易所限制、启封locked或扩预算。`state/dataset_lock.json`仅核SHA，不解析正文。
- 现货库存保护保留；永续signed多空/现金、N资产能力保持。保证金非PnL、空头名义卖款非现金；价格/mark/index/资金费单位和时钟必须明确，不确认则UNKNOWN，不补零掩盖。

## 当前正常入口

- `scripts/investment/spot_perpetual_product_comparison.py`：Spot规则/HOLD组合与保存控制对照；`src/quant/backtest.py`：owned Spot、received-asset手续费、订单和NAV。
- `scripts/investment/multi_asset_portfolio.py`：N资产共享永续组合；正常targets为public_sma_perpetual、donchian_daily_pool_target、hold_donchian_blend_target等。
- Binance行情配Bybit用户费用是跨场所代理，费用profile/SHA/产品/费用资产显式绑定；未经核对不得称Bybit原生成交。
- `accept_spot_research.py`复用本族历史账户/参考验收，`checkpoint_spot_research.py`做薄归档/状态/manifest，`run_research_steps.py`顺序批处理和单调计时；采用规则在新实验前明确，不把工程验收绑定盈亏方向。

## 研究与验证

- REUSE FIRST → ADAPTER SECOND → CUSTOM MODEL LAST。第三方来源/commit/version/license/本地修改登记OPEN_SOURCE_REGISTRY；不重写成熟内核。
- 运行前短记假设、对照、数据角色、指标、预算与停止条件。新经济语义完整重跑受影响账户；只读诊断读旧账本，不删成本保留旧毛收益。
- 因果时间、标签成熟、共同时间切分/适用OOF与独立数据角色保持；已见历史不重命名unseen，不拼接独立满资金账户/事后赢家，不放松成本造APR。
- 按风险验证：只读检查输入/计算/引用；新配方用目标因果/身份顺序、真实账户及现有独立资金/风险核验；金融/可得性修改加相关反例与旧默认golden。REUSED需范围与身份绑定，未运行写NOT_RUN。
- 标的顺序必须贯通targets/cov/账户/成交。缺失与退出保留原因，缺成交/mark或不能清仓按规则停止或有限诊断；marked NAV与liquidated return分别验收，正残仓不能删除/免费平仓。
- 真实风险减仓不得因低换手关闭，净抵消不是gross消失。报告完整资本、gross/net、资金费/费用/执行、实际vol/DD与集中度。
- frozen数据/协议/证据不覆盖；活动代码可正常维护，旧实现依Git复现，不日常复制V1/V2/V3或AST绕过旧源码绑定。已有FrozenPredictor/ExecutionContractV2/STOP_v2/A07/holdout工程和负结果保留。

## 运维、进度与交付

- 先核 `http://localhost:8765/api/status`，沿用服务；未运行再按现有授权bounded启动。长任务显示真实阶段/完成数，未知总量不造百分比，磁盘注明实际扫描时刻。
- 合法采集不停止/注入；异常先保存日志/checkpoint/audit head/必要闭合备份、查实际退出与断档再有限恢复。不拼健康时间。独立历史输入有效时collector存活单独报告，不阻塞离线账本；若影响数据/资源/安全则阻塞相关任务。
- 默认主agent做短任务，必要独立只读审阅才委派；避免重复读写/重复账户。子agent失败只接管未完成部分，不扩大权限。
- 负面测试/pytest basetemp在STATE独立目录，不能污染实际ROOT/source/store或为迁就测试改守卫。只清自己可证明的工件。
- 只维护一份RESEARCH_STATUS，registry/decision log只追加；详细工件路径/SHA引用。README/GOALS/PROGRESS是入口，不继续八份摘要。记录实际阶段计时；并行取区间并集、父子不双计，未知间隔/模型配置写UNKNOWN。
- 一个有限相关模块完成并验收后正常commit/push `https://github.com/snowycat1234/coin.git`，核远端，不按小时、不force push。代码/协议/小证据入库，行情/模型/db/env/cache/log/VHD留D。检查源码字节/敏感信息/文件大小，保留无关WIP。
