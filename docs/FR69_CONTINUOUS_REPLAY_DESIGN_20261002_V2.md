# FR69 连续回放 V2：30d native 与180d原路径入口

创建UTC `2026-10-01T17:38:58Z`，北京时间2026-10-02。本次只改独立薄wrapper，
已验收core、协议、模型参数、六个固定fold及旧报告保持原字节。
独立复核登记的23项源码/旧文档SHA复查0差异；未运行模型fit、真实来源QA或下载。

## 来源保留与最小变更

V1 wrapper与V1设计先逐字节保留到独立archive，原V1文件亦保留：

|档案|字节|SHA256|
|---|---:|---|
|`docs/archive/FR69_CONTINUOUS_REPLAY_WRAPPER_20261002_V1.py`|15,254|`fcccc1207438a14e9cfae33b2730e4d00e72fce93b57657eca698ff0169edac0`|
|`docs/archive/FR69_CONTINUOUS_REPLAY_DESIGN_20261002_V1.md`|10,166|`71587b5a8fb5d196da46484f3f139f6e7efce3bae283e9f69fe54e2623dc14c4`|

两个archive的SHA分别与原V1文件一致。V2新文件在创建前确认不存在：
`.cache/fr69_continuous_replay_v6_v2.py`，15,603字节、376行，SHA256
`2f2d2a25b8dbb80bba82b93e2d9190ae788b5322f4d22c083fe2e150ef3ee469`。
该本地文件被`.cache/`规则忽略，未将未验收新入口冒充accepted core。
以后实际验收并登记时可将同字节脚本纳入Git，V1/V2凭证保持独立。

V2仅解除180d模型入口拒绝，选择30d/180d输入方式，并按
`Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix()`登记真实wrapper
来源key。当前key是`.cache/fr69_continuous_replay_v6_v2.py`；以后同字节移到另一
ROOT内路径时，收据绑定实际执行路径，不再错误写成V1文件。
模型/scaler/evaluator主体与V1一致，没有新模型、normalizer、loader、cache实现、
observer、framework或超参数搜索。V1中根发现的`.manifest.parquet`误判修复仍保留。

## 同一连续policy

原v6§15和§FR69指定Static / River online linear / weekly XGB在同chronological
replay比较。本policy保持RIDGE-1、XGB-S、RIVER-1原参数与seed20261001：

|规则|固定行为|
|---|---|
|初始训练|07-01起12d fitting + 2d validation保留段，原embargo/maturity规则|
|公共外部scalers|初始feature/target各拟合一次，原对象和真实receipt冻结|
|Static Ridge|只初始fit一次，整个连续OOS固定|
|River|原warm-up，初始validation不learn；整个OOS持续predict→成熟→learn，无周重置|
|Weekly XGB|每7d对过去14d首12d fitting再fit，末2d validation保留，参数不变|
|预测归属|weekly Fold.test_end始终是连续终点，只按decision决定当周模型版本|
|共同评价|全部连续test indices/IDs、truth、QA、观察价格完全一致，每方向evaluate一次|
|经济状态|每方向初始10,000 NAV；整个OOS不按周重置持仓/NAV/成本|

局部FrozenReplayDataset视图继续复用原CachedSequenceDataset、原fit_tabular与
fit_river。所有weekly Fold共用一个显式初始归一化合同名；scaler原name/时点/
rows/mean/scale/variance没有改写。真实weekly训练时间窗口独立记录。
周边界前最后310s预测保留、标签在后续真实tick成熟后更新，indices并集必须
完整且只归属一次。最终全局终点仍执行共同label成熟规则。

这是独立FR69连续比较。原6个预登记rolling fold不变；新连续Fold的evaluator
`formal_fold=false`按实际记录，不写FR70排行榜，不选top-3，不产生候选/未来资格。
Conditional future-valid trade-price proxy及无真实历史BBO的限制全部沿用原评价器。

## 两种有界输入路径

|输入|30日诊断|180日完整FR69|
|---|---|---|
|显式来源日期|2025-07-01 ≤ day < 2025-07-31|2025-07-01 ≤ day < 2025-12-28|
|manifest/Parquet数|120|720|
|dataset mode|smoke / SMOKE_ONLY|formal / FORMAL_DATA_READY，仅完整来源才能通过|
|连续OOS|07-15 ≤ decision < 07-29，14d|07-15 ≤ decision < 12-28，166d|
|输入路径|原native_shard_snapshot全120档，实际总量≤1GB|原D盘immutable Parquet路径，零整组副本|
|缓存/解码|原24日bounded cache与row group读取|同一原实现，无自写分块/cache framework|
|成功清理|原cleanup核独占目录和SHA后删native，SOURCE_SNAPSHOT留证据|native未创建，原数据全部保留|

30d副本预计约334MB来自根容量判断，仍由原工具计算实际总量并强制≤1GB。
副本路径替换后断言canonical dataset SHA与SampleIDs不变；失败保留副本。
180d来源preflight复用原resume_day及formal dataset合同，缺档先拒绝，随后核
CHECKSUM、SHA/schema、raw删除和跨日边界；仅访问显式prefix，不枚举locked。
本次没有执行这些真实720档检查。

180d直接用原路径会较慢，但不因native优化尚未实现而永久拒绝。
既有row-group读取和24日cache限制内存，不保存`[N,256,F]`；原tabular trainer
只物化`[N,204]`。166d每分钟最多约239,040端点，float32测试汇总矩阵上界约
195,056,640字节（约195MB，实际共同有效端点更少）。这是尺寸推算，不是实际
全程峰值；共同evaluation、其他数组、缓存与训练库仍计入共享5GB总限额。

开始继续reserve1GB，weekly XGB前调用原disk guard；所有Python经hpc_linux的
bounded.sh，共享5GB、swap0，模型CPU2线程沿用现有env/trainer/config。
与正式首轮/当前诊断共用`.fr-first-round.lock`，仅在当前唯一训练任务结束后运行。
单进程各阶段RSS为累计peak，不能当成各模型独立peak。没有新增资源观察器。

## 本次实际验证与未实跑范围

仅一次轻量AST/接口探针在hpc_linux，经bounded.sh和PYTHONDONTWRITEBYTECODE=1
执行，exit0。结果：31个内存手工分钟端点，首周15、次周16，完整并集不丢端点；
周边界前最后310s的5个端点保留，原scaler对象与receipt不变；真实wrapper来源
key正确；180d Fold的OOS长度为166日。Torch未导入、市场数据未读取、model fits=0；
该探针process峰RSS 168,861,696字节。

这不是30d/180d来源或模型验收。未运行真实120/720档QA、Ridge/River/XGB fit、
完整连续经济工件、整体耗时/物理磁盘增长或全程RAM峰值。180d原路径性能和实际
资源能否完成还需运行收据确认，不能先报PASS。新run输出继续保存原预测、indices、
完整初始scalers、真实weekly窗口、2/4/8bp经济工件、River最终checkpoint与源SHA。
V2完成凭证明确source version=2和input_mode；两个版本的结果独立保存。

原tabular接口不返回持久Ridge/XGB模型，本wrapper不依赖当前训练agent的checkpoint。
当前只接受新的独占STATE run目录，中断保留失败证据，不隐式覆盖/自动恢复旧run。
不把独立重跑记作调参，也不把工程接线校验记作正式市场研究结果。

## 根后续实际命令

下列命令本次未执行。先完成当前完整10配置诊断，再独立运行30d V2；若run目录
已经存在，使用新的明确版本目录并记录原因。所有真实输出留D-host WSL STATE：

```text
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6_v2.py --history-days 30 --preflight-only
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6_v2.py --history-days 30 --run-dir /home/xflops/coin-state/fr69-continuous-30d-diagnostic-20261002-v2
```

180日数据独立QA完成、唯一训练名额空闲后，完整连续166日使用同policy，独立run：

```text
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6_v2.py --history-days 180 --preflight-only
/mnt/d/codex/coin/scripts/bounded.sh env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= /home/xflops/coin-state/research-env-v6/bin/python /mnt/d/codex/coin/.cache/fr69_continuous_replay_v6_v2.py --history-days 180 --run-dir /home/xflops/coin-state/fr69-continuous-180d-20261002-v2
```
