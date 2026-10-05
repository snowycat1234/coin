# COIN：量化研究与共享资本模拟

当前投资资格为 **NONE/CASH**，项目仍在历史研究和前向证据建设阶段。支持现货库存约束、USDT线性永续多空/空仓、可配置N资产与共享资本；支持能力不等于采用某个配方或授权真钱。

- [当前研究、结果与下一决策](docs/RESEARCH_STATUS.md)
- [长期目标与阶段位置](docs/GOALS.md)
- [实验记录](reports/experiment_registry.jsonl) / [决策日志](docs/RESEARCH_DECISION_LOG.md)
- [开源来源与适配](docs/OPEN_SOURCE_REGISTRY.md)
- [有效执行规则](AGENTS.md)

运行在D盘hpc_linux WSL，共享RAM≤5GB、swap0/GPU0，项目加整个D盘WSL VHD≤40GB。通过scripts/with_task_progress.sh包装科学任务，已有进度窗口http://localhost:8765/。具体受SHA配置/复现命令见各结果文档；旧实验按其Git提交复现。

Binance行情配Bybit用户费用时明确为代理；完整资本、真实成本、因果与封存数据隔离继续。测试通过和历史正收益不认证长期APR、交易所真实成交或真钱资格。
