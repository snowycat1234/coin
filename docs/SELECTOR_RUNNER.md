# Selector v1：一次启动、本地独立运行

配置：[selector_v1_runtime_fix.yaml](../configs/selector_v1_runtime_fix.yaml)。日期审计：[DATA_SPLIT_AUDIT](DATA_SPLIT_AUDIT.md)。三个冻结expert为SMA200_SIGNED/HOLD/CASH，原交易参数不改。

所有命令在D盘 `hpc_linux` WSL、项目 `/mnt/d/codex/coin` 执行。训练复用既有CPU环境；配置、进度和绘图依赖安装在D盘WSL的独立selector-support-v1目录，逐文件SHA冻结，原训练环境不改。运行DAG不请求LLM/API、读取密钥或发单。

## 推荐：独立服务启动与恢复

```bash
bash scripts/research/selector.sh start
```

这一个命令启动完整DAG。用户服务经既有progress→bounded链路，归入coin-research.slice；SSH断开不会结束训练。重复start发现存活服务时保留它，不再启动第二个runner。

```bash
bash scripts/research/selector.sh status
bash scripts/research/selector.sh logs
bash scripts/research/selector.sh resume
```

status只读 `state/selector_progress.json`。resume使用同一配置与完整匹配checkpoint；改变配置、源码、数据或已有模型字节会拒绝复用。未完成任务最多允许一次故障重试，旧attempt保留；不能把停止/残仓账户包装成完整收益。

## tmux / nohup替代方式

仅在上述服务没有运行时使用，runner文件锁会拒绝重复进程。

```bash
tmux new -s coin-selector
scripts/with_task_progress.sh --title 'Selector v1 independent DAG' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/research/run_selector_research.py --config configs/selector_v1_runtime_fix.yaml
# Ctrl-b d 脱离；tmux attach -t coin-selector 回看。
```

```bash
nohup scripts/with_task_progress.sh --title 'Selector v1 independent DAG' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/research/run_selector_research.py --config configs/selector_v1_runtime_fix.yaml > /home/xflops/coin-state/selector-v1.nohup.log 2>&1 < /dev/null &
```

主入口为 `python scripts/research/run_selector_research.py --config configs/selector_v1_runtime_fix.yaml`，必须通过上述既有WSL守卫调用。

## 冻结预算与验证语义

- 26个过去特征，固定H=30/60/90。ATR/RSI/Donchian复用pandas-ta-classic；rolling统计复用Polars；不实现新的indicator/model kernel。
- Ridge+StandardScaler和一套CPU XGBoost参数。5个expanding chronological folds、60主CV组。XGBoost每组3个utility head，实际底层fit计数保留。
- 16训练label shuffle、16训练feature shuffle、32同频随机路径，共64placebo路径×2资金费条件；同频随机条件化时序是诊断对照，不是可部署策略。
- 320shuffle CV组，最多1080成功底层fit；每任务最多2attempt，总fit尝试上界2160，未完成fit计数记UNKNOWN，不假装0。没有Optuna或结果后搜参。
- 158个真实共享完整10k钱包对照、最多2worker各2线程/1.5GB；8小时、最多12GB新增工件预算。共享RAM8GB、swap0/GPU0、D项目+整个VHD150GB沿用。预算耗尽保留checkpoint，不能无限自动重试。
- 每fold先purge所有未成熟/重叠train标签，再额外H日embargo；scaler/model只fit train。每日overlap标签不按独立样本计数，MLP因有效样本不足跳过。
- **全部2022–2023历史已见**。验证是开发内部时间顺序回测，不是独立OOS。2022 short capture只覆盖Q4的92日，不宣称全年捕获；FINAL LOCKED TEST不读、不跑。
- Champion按两资金费条件中较弱的共同成熟日期utility-rank选，不能按最终钱包净收益选。最强static、各placebo95%、两个年份方向、风险与15%oracle-gap捕获门槛在配置中事先冻结。
- 真实backtest先合成三个expert目标，再进入同一个共享账户；不加独立钱包收益。手续费/执行/资金费记一次，必要风险减仓不关闭。

## 进度与工件

已有8765窗口显示实际阶段；终端输出DATA/FEATURES/LABELS/CV/PLACEBO_FIT/BACKTEST/REPORT。每5秒写machine-readable状态：stage、elapsed、当前阶段ETA、fold、model、全DAG completed_jobs/total_jobs、当前阶段计数、best_validation_score_so_far、共享组RAM和runner进程树CPU。

ETA初始UNKNOWN；只在有任务完成后估当前阶段，不能把训练阶段耗时推作回测阶段保证。原始账户分钟进度位于各job的progress.json；源数据、模型、账本和日志在D-hosted STATE。

自动最终输出：

- `reports/SELECTOR_ML_REPORT.md`
- `reports/SELECTOR_ML_RESULTS.json`
- `reports/SELECTOR_ML_PLOTS/`
- `state/selector_progress.json`

SOURCE/CONFIG/审计必须先commit，runner在任何fit前逐字核Git HEAD。不符合就拒绝训练。完成后再由Codex读取最终工件做一次决策，运行过程中不需要Codex逐折参与。

所有收益是Binance USD-M价格配Bybit用户费用代理；资金费单位两种条件解释、历史数量和MMR未原生认证。即使开发筛查通过，投资资格仍为NONE/CASH，年化只是描述外推。

后台启动修复：原systemd用户manager没有WSL_DISTRO_NAME，既有bounded守卫在训练前以1退出；实际日志保留在STATE/selector-v1-startup.log。启动器现显式传入经外层核对的hpc_linux标识并将日志持久写入D-hosted STATE。原selector_v1.yaml保留；runtime_fix仅修改launcher源码SHA与新运行目录，数据/feature/H/models/cost/budget/gates/placebo完全相同。旧准备目录/两日QA保留，正式新目录在commit后开始。
