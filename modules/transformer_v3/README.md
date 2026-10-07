# Transformer v3 Oracle policy：强平修复与冻结回放

从远端 v2 `0350589199d4566ac519b0e581ff86eb065ba934` 建立独立分支。旧 v2 STATE、formal locked N/E、模型和账本不改写；16,025 个保护文件（33,182,604,674 bytes）已有完整 SHA 清单，原件留在服务器。

当前完成的是数据恢复尝试、五种 funding bridge 事前登记、逐仓 bankruptcy takeover 实现及相关反例验证。新 v3 训练、完整冻结回放及 locked bridge 经济结果尚未运行，不能称研究完成或晋级。27 项相关测试已在服务器通过；日志在 reports/transformer_v3/PHASE2_FINAL_TESTS.log。

资金费 exact source 均未恢复；授权失败和空网页不是无结算事件证据。ZERO、LINEAR_INTERPOLATION、PREVIOUS、NEXT、FORMULA_RECONSTRUCTED 全部已登记，公式使用分钟 premium 近似，绝不标 exact。用户同意采用相邻事件均值估算，五种敏感性仍全部保留。

十个 Bybit risk-limit 公开请求均 HTTP403；当前声明原研究 MMR=.005、MMD=0 的条件假设。实现 Mark-trigger / cancel intents / isolated bankruptcy takeover / 不返还保险基金剩余 / wallet 和其他仓位继续 / 下一正常 rebalance 可重新开仓。通用 laddered IOC 已验证，但不虚构未观测容量，未证明真实最低风险档位；分钟 mark 也不是交易所逐笔强平认证。

接下来先运行两个真实窗口 probe，再运行 864 行冻结任务（720 原模型任务、72 旧控制、36 暴露、36 corrected oracle）。每个任务实际执行新钱包；保存后仅 byte-identical 文件引用保护的旧工件以节省空间。所有原完整且新无强平账户必须保持经济结果误差 ≤1e-7 USDT。先分析 neutral/combined 及原 111 个不完整原因，再冻结 v3 teacher/policy 模型协议。

运行入口：`python -m modules.transformer_v3.replay --state <NEW_STATE> --v2-state <READ_ONLY_V2_STATE> --workers 10`。`--probe-only --workers 2` 为两个真实窗口。服务采用服务器实际配置，未添加 CPU/RAM/墙钟限制；本机仅源码与小证据，不运行科学计算。持久进度 replay-progress.json，逐账户 progress.json 提供实际分钟数。

公开规则来源：[Bybit liquidation process](https://www.bybit.com/en/help-center/article/UTA-Trading-Rules-Liquidation-Process)、[Bybit risk-limit schema](https://bybit-exchange.github.io/docs/v5/market/risk-limit)、[Binance funding](https://www.binance.com/en/support/faq/detail/360033525031)。依赖沿用既有 Decimal、NumPy、Polars、Torch，无新付费或私有账户接口。
