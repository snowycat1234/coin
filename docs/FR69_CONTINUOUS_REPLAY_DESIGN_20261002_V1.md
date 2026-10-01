# FR69 连续回放薄编排方案与接口复核

创建UTC `2026-10-01T17:17:36Z`，北京时间2026-10-02。
已验收提交 `1251dd5b8f5aa9cb4cd89a6b0fd550b0e383753f` 的source保持原字节；
独立复核登记的23项源码/旧文档SHA复查0差异。没有启动真实训练或下载。

原v6 `OPEN_SOURCE_REUSE_OVERRIDE_v6_2026-10-01.md:732` 要求predict→等完整label成熟→
learn，`:1324` 的FR69明确 `static linear / River online linear / weekly XGB refit`
使用同chronological replay。本方案符合这一方向。现有6个隔离7日fold比较仍保留；
每fold重置的结果不能代替连续适应比较。

## 固定policy与执行范围

|项目|30日独立诊断|180日FR69方案，执行未启用|
|---|---|---|
|共同官方来源prefix|2025-07-01 ≤ day < 2025-07-31|2025-07-01 ≤ day < 2025-12-28|
|初始fitting/validation|07-01起12d fitting、随后2d validation|相同|
|共同连续OOS|07-15 ≤ decision < 07-29|07-15 ≤ decision < 12-28|
|dataset模式|smoke，SMOKE_ONLY|formal来源要求180共同完整UTC日|
|Ridge|只初始fit一次，整个OOS固定|相同|
|River|初始train warm-up、initial validation不learn、OOS持续成熟更新|相同|
|XGB|07-15初始fit，07-22再fit，共2版本|每7d真实历史窗口refit，最后不足7d保留|
|经济评价|连续14d每个方向一次，NAV/持仓不换周重置|连续166d每个方向一次|

保持RIDGE-1、XGB-S、RIVER-1原参数及seed20261001。XGB各版本在周开始前使用
过去14d中的首12d fitting与末2d validation保留段；其真实train cutoff继续复用
原Fold的embargo和310s成熟规则。现有XGB-S没有验证集选超参数/early stopping，
2d validation仅保留，不改成新训练实现。

所有模型外部feature/target normalizer在初始fit cutoff各拟合一次，后续冻结。
River现有官方内部StandardScaler仅在成熟例子上更新；原ADWIN只记录、不调参。
此policy是独立连续比较登记，不能把其新Fold冒充原6个预登记rolling fold；
`evaluate_fold`会记录`formal_fold=false`，不输出FR70六fold排行榜或晋级资格。

## 现有接口限制与最小接线

1. `fit_tabular`与`fit_river`内部调用`fit_fold_scaler`/`fit_target_scaler`，没有传入
   frozen scaler参数。局部`FrozenReplayDataset`只是同一CachedSequenceDataset的
   视图，两个方法返回初始scaler原对象。原trainer、scaler、特征、labels都复用；
   不全局patch，不改已验收source。结果逐项断言原scaler receipt完整相同。
2. `normalized`要求normalizer.fold_name与Fold.name相同。初始与所有weekly Fold
   共用明确的单一合同名`FR69_CONTINUOUS_INITIAL_SCALERS_V1`；该名表示本次replay
   的共同归一化合同。每周真实训练起止/cutoff和预测归属另记在weekly_versions中。
   没有改normalizer的name、时间、rows、mean/scale/variance或复制新fit收据。
3. 原`Fold.test`按test_end移除末310秒；若每周设置局部test_end，会把边界前仍应
   预测的端点丢掉。因此每个weekly Fold.test_end都保留连续终点，视图仅按
   `decision < week_end`限制该版本预测归属，不按`label_mature <= week_end`裁剪。
   各周indices并集必须等于完整共同连续test indices，且每个indices只赋值一次。
4. River使用原`fit_river`在完整连续Fold上运行一次，其待成熟队列和模型不换周
   重建。训练warm-up仍用原共同train endpoints；validation不学习。周末最后310s
   发出的旧预测保存到连续数组，旧标签只在后面的实际tick成熟后学习。
5. `EvaluationBatch.from_dataset`要求完整test indices。只为连续Fold建立一次batch，
   三个方向原单位预测均对齐它；`evaluate_fold`各执行一次。周切换只改变未来
   预测的XGB版本，不改变已有signal、持仓、cash、NAV、成本或观察价格。

三个方向共用同一个native CachedSequenceDataset基础、合同/index/ID及初始两套scaler。
局部视图共享该实例的bounded日缓存，不另建pipeline；只物化原tabular 204维汇总，
不物化`[N,256,68]`。原官方manifest/resume_day仍负责CHECKSUM、原SHA、schema、
raw临时删除和跨日边界。范围先显式检查缺档；没有glob locked。

## 已落本地wrapper与实际轻量验证

忽略文件 `.cache/fr69_continuous_replay_v6.py`，15,254字节、369行，SHA256：
`fcccc1207438a14e9cfae33b2730e4d00e72fce93b57657eca698ff0169edac0`。
写入前确认不存在；`git check-ignore`确认不入库。设计文档可入库，但不能假设
其他checkout已有该忽略文件。当前仅本地方案，不声称正式模块验收。

wrapper直接复用原`fit_tabular`、`fit_river`、`EvaluationBatch`、`evaluate_fold`，
以及已验收入口的source/runtime/原子JSON发表辅助；没有新regressor、scaler、
ADWIN、特征/标签实现、通用framework或observer。由于从`.cache`执行，历史辅助
通过明确文件路径导入`hf_fetch_history.py`，不依赖scripts恰好在sys.path。

在hpc_linux、`scripts/bounded.sh`、`PYTHONDONTWRITEBYTECODE=1`下对根复核前草稿
做了一次有结果的
轻量接口校验：AST语法通过；内存中31个手工分钟端点跨周，第一周15、第二周16，
拼接恰好等于完整共同indices；周边界前最后310s的5个端点保留。原normalizer对象
身份、receipt及原normalized检查保持一致。process峰RSS 168,701,952字节，
Torch未导入、市场数据未读取、model fits=0。一次较早相同探针的输出未被捕获，
不计作验收证据；随后有结果的探针正常exit0。没有pytest或镜像实现测试。

根随后复核发现一项真实提前拒绝bug：`2025-07-01.manifest.json`使用
`with_suffix('.parquet')`会生成不存在的`2025-07-01.manifest.parquet`。已在尚未
绑定/真实执行的draft中改为`path.parent / (path.name[:10] + '.parquet')`，因此明确
查找`2025-07-01.parquet`。此前接口探针没有执行common_sources，不能记作此来源
检查已经通过。同步按根要求增加30d原工具native副本和180d执行拒绝。最终draft
再次经同bounded/PYTHONDONTWRITEBYTECODE=1做AST语法校验exit0，未导入模型或fit。

## 输出、资源和未解决范围

wrapper要求新的独占STATE目录，与正式首轮共用`.fr-first-round.lock`，阻止两个
训练编排重叠；运行仍在既有5GB共享cgroup、swap0、CPU内。开始reserve1GB，
每次weekly XGB前再调用原disk guard。当前训练agent占用唯一训练名额，此次没有
运行preflight或真实fit。全部数据/预测/checkpoint/NAV/trades留D-host WSL STATE。

30d执行直接复用`native_shard_snapshot`复制全部120档到该run独占native目录；
根容量估计约334MB，本次未实测，实际工具强制总量≤1GB并先调用磁盘guard。
副本重新构建同一dataset，断言canonical合同不变后才准备index；原SOURCE_SNAPSHOT
完整保留到run并绑定SHA。成功后复用原cleanup核归属和全部SHA才移除native；
失败时保留副本和证据。没有改变原Parquet、manifest或已有采集来源。

输出包括byte-bound RUN_BINDING、唯一endpoints index、各模型原单位预测/indices、
共同EVALUATION、2/4/8bp场景日NAV与trades、River最终checkpoint、weekly真实时间
窗口与保留边界端点数、三个COMPLETE和连续总凭证。总凭证核三者同batch fingerprint，
不写MODEL_LEADERBOARD，不授予候选/未来/生产资格。

限制需保留：

- 真实30d来源preflight与完整三方向fit/evaluation没有运行；轻量几何/身份校验
  不能代替这些验收。180d实际容量、耗时与连续结果仍未实测。
- 180d不能整组native复制；当前仅source preflight开放，真实执行在任何fit前
  明确拒绝。后续应复用已验收fold分块副本方式，同时保持River跨块连续状态与
  同一初始normalizer，单块≤1GB。该接线尚未实现/复核，不能运行180d模型回放。
- 单进程依次执行，记录的RSS是整个连续进程的累计峰，不能称每方向独立峰值；
  worker总时间亦不得按共享过程重复计数。若将来确需独立每方向峰，应沿用既有
  worker进程方式单独验收，当前没有扩建资源工程。
- 原tabular trainer不返回持久Ridge/XGB模型；本wrapper保存原预测/evidence，
  不依赖当前训练agent的任何模型checkpoint，也不宣称冻结候选或可再加载模型。
- 中断时保留失败与已有工件；当前wrapper只接受新目录，不提供半途自动恢复。
  需要继续时使用独立新run并记录重跑原因，固定policy/seed不构成结果驱动调参。
- 最终全局终点仍只评价在终点内完整成熟的共同labels；这是共同terminal规则。
  内部周边界不再额外删除310s。条件性未来标签有效端点与trade-price proxy的
  限制仍由原evaluator明确记录，无法推导真实历史BBO或可实施alpha。

## 根任务下一次实际命令

先待当前唯一训练进程结束或明确退出并保存凭证，再在hpc_linux执行；下列命令
未在本次运行。30d先只核来源，再使用新的、此前不存在的STATE run目录：

```text
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6.py --history-days 30 --preflight-only
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6.py --history-days 30 --run-dir /home/xflops/coin-state/fr69-continuous-30d-diagnostic-20261002-v1
```

180d当前只有source preflight可执行；正式连续入口待分块接线独立复核后再给命令：

```text
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6.py --history-days 180 --preflight-only
```
