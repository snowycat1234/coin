# Collector research and complete-window validation

独立模块：官方归档并行采集、规范化、四类模型时间顺序研究，以及复用已有预测的原生共享账户验证。账户、成本、风险减仓和独立账本核验直接调用仓库已有实现；没有另写金融内核。

四类模型为逐资产 XGBoost，以及共享 TCN、GRU、Transformer。四种基线为 HOLD、SMA200_SIGNED、固定三方向混合、CASH。默认两个资金费条件 `1.0` 与 `0.01` 分开保存，不选择更盈利的条件作为已认证单位。

## 已有训练的用法

从仓库根目录运行，下列路径是用户自己的外部 STATE 路径。`collector-root` 指向包含 `config.env`、`pipeline/` 的生产者目录；`collector-work` 包含原来的规范化数据、标签和研究产物；`source-run` 包含原生产者 `BINDING.json` 和两种条件的 `RESEARCH.json`。

```bash
python -m modules.collector_research.validation audit \
  --collector-root /path/to/collector \
  --collector-work /path/to/external-state/work \
  --source-run /path/to/external-state/source-run \
  --run-dir /path/to/external-state/complete-validation \
  --resource-policy server

python -m modules.collector_research.validation run \
  --collector-root /path/to/collector \
  --collector-work /path/to/external-state/work \
  --source-run /path/to/external-state/source-run \
  --run-dir /path/to/external-state/complete-validation \
  --resource-policy server
```

第二条命令重复执行会验证并复用已完成账户工件。被中断的单个账户从新尝试重跑，最多两次；已完成案例不重算。`status` 使用相同参数查看进度；运行目录中 `status.json`、每例 `progress.json` 显示模块、完成数量和真实分钟进度。需要关闭SSH后继续时，使用已有服务管理器或 `nohup`；模块本身不依赖LLM/API调度。

`run` 默认不修改原报告；显式加 `--publish-source-report` 才会先备份再更新生产者的 `FINAL_REPORT.md`。新运行目录必须与原证据目录分开，数据、模型、环境和账本目录必须在Git checkout之外。

## 完整性和研究边界

先核对源文件SHA、模型/预测SHA、成熟标签、时间隔离、训练期标准化和加载权重预测复现。标签仍是日频数量账户代理，不冒充原生分钟标签。没有训练异常不等于具有投资资格；原先未通过基线门槛的结论保持。

再按各折过去训练确定的资产集合，要求交易K线、mark、premium、资金费及执行资金费区间完整。共同日历在真实缺口处分成连续段；事先固定最短30天，只按数据完整性选段，不按盈亏挑日期。原始数据和训练权重不改写，缺价格不补零、不前填。

每段最后24小时统一给现金目标，复用原仓库 `persist_cash_close=True`，按真实分钟成交容量逐步平仓并计费。该日仍计入时间、价格、资金费和成本。完整日历且真实平仓才填完整收益；真实风险停止和库存残余会保留。每段每例独立10,000 USDT，名义单币30%/gross60%、逐仓1x；各段盈亏不相加或拼接成一条长期账户曲线。实际风险漂移及减仓延迟保留在原账本。

这是已见开发历史的后验完整数据筛查，不是未见OOS。缺口边界不是当时可预测的交易信号；不能把区间间平仓当作策略能够预知未来缺口。历史特征缺失仍按原模型的显式mask处理。Binance行情与Bybit费用/账户假设是跨场所代理，不认证Bybit实际成交、原生过滤器、MMR或资金费发布时间。2026-03-01至2026-08-31封存区间保持禁止读取。

## 新采集或训练

没有旧自动运行目录时，训练两个条件后可用 `snapshot` 登记显式指定的研究目录。使用上面相同的路径参数，将动作为 `snapshot`，并增加 `--fraction-study /external-state/work/research/FRACTION_ID` 与 `--percent-study /external-state/work/research/PERCENT_ID`。它不会按回测盈利选模型或重训；已有快照不同则拒绝覆盖。原训练日志未保存时，审计明确记录 `LOG_NOT_AVAILABLE`，不编造训练日志；模型哈希、预测复现和因果检查仍必须通过。

本模块保留已经验证的 `pipeline/` 源字节，因此兼容旧数据代码哈希。只需要复核已有数据/模型时，使用上面的验证入口，避免重新采集或训练。

### 独立公共行情补充

`pipeline.public_supplement` 是小型 Bybit/OKX 适配器，复用既有原子写入和 SHA 工具；
不会写入原 Binance 数据或认证 frozen selector。以下命令默认只打印固定计划，无网络 IO：

```bash
python -m modules.collector_research.pipeline.public_supplement \
  --provider okx --cache /path/to/external-state/public-supplements
# 显式加 --collect-daily 才采集 2025-07-01..2025-12-31 的五个永续日线标的。
```

缓存必须在 checkout 外。每次最多 20 请求/5 MB，每响应最多 1 MB；正常会话、无重定向、
每请求至少间隔一秒，暂时传输/5xx 最多两次；成功页按原 SHA 复用。403/451/权限或限流
保存 `access-stop.json` 并停止该服务，后续运行保留停止状态，不自动改主机或代理。
空列表、HTTP 失败、明确文档留存限制和日历缺口分别记录，不补零、不前填。

原价、原生合约值/乘数、当前 instrument 元数据、每响应原字节 SHA、请求和收到时间保存。
日线结束不是已知历史发布时间；`historical_available_ms=null`，可得时间仅为本地收到时刻。
Bybit `10000SATSUSDT`、OKX `SATS-USDT-SWAP`/`PEPE-USDT-SWAP` 不等同 Binance 千币产品，
价格不自动换算。当前元数据不能认证 2025 历史合约规则。DOGE 2025-12 的 1m mark 计划和
离线解析已提供，当前入口拒绝 minute 网络采集。没有训练、历史回测或投资资格升级。

```bash
python -m modules.collector_research.run_pipeline \
  --work-dir /path/to/external-state/work --resource-policy server collect
# 之后按需运行 normalize、verify、labels、train；不要无条件重跑已完成步骤。
```

训练前需要明确设置 `FUNDING_RATE_SCALE=1.0` 或 `0.01`；UNKNOWN只允许采集/规范化。模型、参数、源哈希与标签配置进入研究绑定；变更后不得静默复用旧模型。16路归档下载使用线程独立会话、校验官方CHECKSUM和ZIP CRC、保留失败记录与已成功任务。

## 运行环境

Python 3.12。安装 `requirements.txt`；神经模型另装PyTorch。已验收服务器版本为 `torch 2.6.0+cu124`、XGBoost CPU 3.4.1、pandas 2.3.3、NumPy 2.5.3、Polars 1.44.2。CPU本机可使用PyTorch CPU版；CUDA服务器使用与驱动兼容的官方wheel，不自动改用CPU训练。

`server` 是明确的Linux服务器执行选项：按实际CPU核心数并行，不施加项目CPU/RAM/swap/墙钟限额。它不能在WSL中使用。`local` 默认保持 hpc_linux 的共享8GB、swap0、GPU0；必须经仓库 `scripts/with_task_progress.sh` → `scripts/bounded.sh`，默认两个账户工作进程。Windows本机只允许编辑和检查源文件，科学任务拒绝直接执行。所有站点保留15GiB空间检查。

本机示例：

```bash
bash scripts/with_task_progress.sh --title '完整区间验证' -- \
  python -m modules.collector_research.validation run \
  --collector-root /path/to/collector --collector-work /path/to/external-state/work \
  --source-run /path/to/external-state/source-run --run-dir /path/to/external-state/complete-validation
```

## 输出与已验收实例

`TRAINING_AUDIT.json`、冻结的 `VALIDATION_PLAN.json`、`BINDING.json`、`NATIVE_RESULTS.json`、`WINDOW_COMPARISON.csv`、`WINDOW_RETURNS.png`、`FINAL_REPORT.md` 以及逐案例原生账本。摘要只使用所有模型/基线共同完成的窗口；未完成案例仍保留，不能只给失败模型删差窗口。

2026-10-07实例：40个模型折/372项产物复用，原788天排除1个真实缺口日，6段787天，96/96案例完整且平仓，最大独立NAV/钱包误差5.46e-12 USDT。两资金费条件下四类模型的窗口收益中位数均为负；原筛查不晋级结论不改。详情见仓库 `reports/COLLECTOR_COMPLETE_WINDOWS_20261007.md` 与小型验收摘要；行情、权重、环境和大账本仍留在外部STATE。
