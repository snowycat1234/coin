# Transformer v3 Oracle policy：强平修复与冻结回放

从远端 v2 `0350589199d4566ac519b0e581ff86eb065ba934` 建立独立分支。旧 v2 STATE、formal locked N/E、模型和账本不改写；16,025 个保护文件（33,182,604,674 bytes）已有完整 SHA 清单，原件留在服务器。

当前阶段成果已发布：[2026-10-07阶段报告](../../reports/transformer_v3/progress_snapshot_20261007/CURRENT_STAGE_REPORT.md)。快照UTC10:02:40（北京时间18:02:40）：864旧回放、348HALF对照、60开发fit及12固定过去数据最终fit全部完成；新开发账户190/576继续后台执行，locked敏感性与最终研究报告尚未运行。原111停机账户恢复108个，3个风险减仓受限保留N/E；753个原完整且未强平账户经济一致性核对通过。旧neutral稳定性门槛未通过，投资资格仍NONE/CASH。阶段证据包含完整旧回放分析、半仓位结果、预测诊断、新旧regret对照、训练记录及已完成新账户子集；全部发布账户summary/audit与72次fit的weights/scaler SHA已核对。阶段发布不是最终模型选择。47项已提交后续源码测试通过；大行情、权重、分钟账本留外部STATE。

资金费 exact source 均未恢复；授权失败和空网页不是无结算事件证据。ZERO、LINEAR_INTERPOLATION、PREVIOUS、NEXT、FORMULA_RECONSTRUCTED 全部已登记，公式使用分钟 premium 近似，绝不标 exact。用户同意采用相邻事件均值估算，五种敏感性仍全部保留。

十个 Bybit risk-limit 公开请求均 HTTP403；当前声明原研究 MMR=.005、MMD=0 的条件假设。实现 Mark-trigger / cancel intents / isolated bankruptcy takeover / 不返还保险基金剩余 / wallet 和其他仓位继续 / 下一正常 rebalance 可重新开仓。通用 laddered IOC 已验证，但不虚构未观测容量，未证明真实最低风险档位；分钟 mark 也不是交易所逐笔强平认证。

两个真实窗口probe及FULL全批864行（720原模型任务、72旧控制、36暴露、36corrected oracle）实际执行完成，保存后仅byte-identical文件引用保护旧工件。864中861完整，原720模型账户717完整；旧完整且新无强平账户经济一致≤1e-7 USDT。已保存“Mark强平与funding同clock”反例，并在独立后续执行checkout修复独立校验的排序；默认普通账户经济一致，旧批次源码绑定不改写。实际先完成旧回放及neutral/combined分析、提交协议bdfe816，之后才执行新fit。

有限预算为348个固定HALF旧对照；2类小policy模型、3seed、5fold×2fund，共60开发fit及12过去数据final fit；576个新开发钱包；模型、profile、weights完全冻结后10个独立输入源（5bridge×2fund），400个184日封存比较。只用FULL .60/HALF .30、K2，不Optuna、不温度搜索、不winner seed。实际协议已在完整864回放及neutral分析后生成并commit，训练前绑定凭据随阶段证据发布。

teacher复用严格成熟的cost-aware日频SMA/HOLD/CASH utility，60日purge/embargo；不是minute native-wallet等价oracle。新增3-action直接policy head为主要决策；保留7/30/60相对rank，30日为portfolio主分数。所有teacher只作训练target，推断Dataset仅过去features/masks。每fold的IC/Spearman/hit/spread/regret与真实钱包费用、funding、强平和net独立报告。

新钱包保存使用无损gzip原JSON字节与Float64 XOR/Parquet。XOR的每个原始位与残差保留，公共Mark参考SHA绑定；读取金融列必须经storage.hydrated_account还原原schema后再核验，物理压缩文件不是直接可读的Float64账本。实际182日36.52MB分钟文件压至2.25MB，所有浮点位完全一致。旧文件不压缩、不改写。

pipeline.py为持久有限编排器，失败保存且最多一次原生任务/fit重试；完成产物按SHA复用，不重跑前面的训练。它等待当前864服务，再分析、核已commit的同clock校验修复与测试，生成并仅commit授权的协议元数据文件，然后按规定顺序推进。不自改源文件。若修复后的旧neutral已通过稳定门槛，优先固定HALF旧对照；否则GPU训练与CPU HALF对照并行。GPU fit并行度取实际GPU显存和CPU配置，本次4090为2个独立任务，优化器/batch/seed/模型数不变。最终past-only拟合与576开发钱包并行，全部完成并冻结后才运行封存敏感性。最终逐项回答用户11个问题，五bridgeheadline全部min/median/max和经济判断一致性；原formal v2 N/E不变。

运行入口：`python -m modules.transformer_v3.replay --state <NEW_STATE> --v2-state <READ_ONLY_V2_STATE> --workers 10`。`--probe-only --workers 2` 为两个真实窗口。服务采用服务器实际配置，未添加 CPU/RAM/墙钟限制；本机仅源码与小证据，不运行科学计算。持久进度 replay-progress.json，逐账户 progress.json 提供实际分钟数。

实时查看：`python -m modules.transformer_v3.progress --state <NEW_STATE> --watch`，显示实际模块计数、epoch/batch和最近账户分钟计数；缺总数不会伪造百分比。完整编排入口：`python -u -m modules.transformer_v3.pipeline --state <NEW_STATE> --v2-state <READ_ONLY_V2_STATE> --collector-root <COLLECTOR> --work <DEVELOPMENT_WORK> --source-run <SOURCE_RUN>`。只在独立云Linux服务器执行，worker默认实际CPU affinity；本机资源限制继续有效。

阶段证据导出使用`publish_snapshot.py --state <STATE> --repo <EXECUTION_REPO> --output <NEW_PUBLICATION_DIRECTORY>`，仅在独立云Linux运行，不重跑训练或账户，不修改运行中的源码及保护工件。读取一次当前已完成账户集合，保留N/E和部分状态，验证summary/audit、weights/scaler SHA；生成报告、阶段计数与逐文件manifest。发布目录独立于科学STATE和执行仓库，再同步小证据到Git。本阶段结束不等于整条研究完成。

公开规则来源：[Bybit liquidation process](https://www.bybit.com/en/help-center/article/UTA-Trading-Rules-Liquidation-Process)、[Bybit risk-limit schema](https://bybit-exchange.github.io/docs/v5/market/risk-limit)、[Binance funding](https://www.binance.com/en/support/faq/detail/360033525031)。依赖沿用既有 Decimal、NumPy、Polars、Torch，无新付费或私有账户接口。
