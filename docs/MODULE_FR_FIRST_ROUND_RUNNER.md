# 固定第一轮运行入口

`scripts/fr_run_first_round.py`仅编排已有数据、模型与共同评价接口。
没有新模型、下载器、特征管线、搜索框架、执行客户端或资源观察器。
第一轮固定10配置×6个事前指定OOS窗口、一个seed20261001；全部CPU串行。

## 实际预检与边界

入口只显式访问2025-07-01至2025-12-28前的720份manifest/Parquet，不枚举locked历史。
完整文件后才调用原官方`resume_day`核来源、CHECKSUM、SHA/schema/原raw删除和跨日编号范围。
随后同一个`CachedSequenceDataset(mode=formal)`构建唯一index。未齐时立即拒绝，不拟合。
根已实测`--preflight-only`返回`INSUFFICIENT_180D: 613/720 missing; model_fits=0`，
该时刻只有107档已发表；这份拒绝不是数据损坏或模块完成证据。

第一次运行指定新的D盘WSL STATE目录，绑定源码、原manifest、protocol、data合同、
index SHA、发行包version/METADATA/RECORD。既有run只能在这些绑定完全一致时继续。
每fold仅复制其输入时间范围所需原Parquet到native工作目录，副本≤1GB；
仍用全部720个ShardSpec，仅替换路径，canonical合同和样本ID不变。
fold结束先核原byte绑定及目录归属才移除该独占副本；失败目录保留。

## 模型与恢复

每个模型任务是一个新Python进程，共享原5GB cgroup、swap0。
Ridge/XGB调用原`fit_tabular`，TCN/MLPLOB/TLOB调用原`fit_sequence`，
River调用原`fit_river`。TS2Vec两个probe共用一个worker和一次600迭代encoder。
过程峰值RSS单独归worker；共同cgroup峰另注明累计，不将两probe重复加总。
正式序列训练仍用最多10epochs/patience3；本模块没有缩短正式研究范围。

正式run持有stdlib文件锁，并把锁句柄传给worker；parent退出时worker仍阻止另一正式任务并发。
完成预测、index、日NAV、交易proxy、训练checkpoint、evaluation、来源副本清单均SHA绑定。
恢复核预测形状/原单位字节、共同完整测试IDs与评价、不能只有一个绿色状态标记。
JSON以临时文件fsync＋exclusive hard-link原子发表，不能覆盖旧完成凭证。
TS2Vec先持久保存两probe完整group凭证，若只发表一个COMPLETE后中断，
在核两份原预测/标签/评价/encoder绑定后发表缺失的凭证，不重新预训练。

根复核了agent草稿，并修正两probe原来共用最后一次destination的问题。
两项最终测试实际通过：中断在两个probe发表之间后的恢复、关联checkpoint修改拒绝；
720份数据缺失必须在任何source读取/fit之前拒绝。人工模型夹具不是真实模型训练。
Ruff通过。此前测试XML保留；没有额外正式模型拟合。

## 首轮输出

仅60个配置×fold完成且共享数据/评价绑定一致时写
`reports/fast_research/MODEL_LEADERBOARD.md`。
列flow IC/sign、return Pearson/Spearman、RV rank、gross、fee/spread/slippage、
cost/net/turnover/Sharpe/MDD、worker时间、进程peak RAM、GPU hours及sprint gate。
跨foldIC/费用/收益/Sharpe为等权平均、MDD取最差fold；孤立测试周不冒充连续收益。
换手为相同初始10,000 USDT账户的reference成交额；费用三列是初始NAV占比。
两probe共享representation时间/RSS会明确注明。4/8bp点差敏感性和逐fold明细留STATE。
top-3按不同方向归组，同TCN/XGB/TS2Vec相关配置不能占多个方向名额。
仅sprint筛选、条件性完整未来标签价格proxy，无实际BBO/可实施交易/候选资格。

本模块验收仅为编排正确性、拒绝与恢复路径。180日数据、真正60次formal结果、
连续weekly adaptive对比、首轮榜和top-3尚未完成；不制造这些结果。

运行（已有共享限制内）：

```text
scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 /home/xflops/coin-state/research-env-v6/bin/python scripts/fr_run_first_round.py --preflight-only
scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 /home/xflops/coin-state/research-env-v6/bin/python scripts/fr_run_first_round.py --run-dir /home/xflops/coin-state/fr-first-round-20261002-v1
```

第二条命令须在720档已齐并独立接受历史数据之后由根启动；当前不启动。
