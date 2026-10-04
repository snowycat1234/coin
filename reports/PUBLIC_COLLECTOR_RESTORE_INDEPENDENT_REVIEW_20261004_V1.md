# D066 原两路公开采集恢复：独立只读复核

## 结论与范围

在本版两个实际采样时刻，原公开分钟采集与原L1 v1采集均有真实Python进程、新会话和继续推进的市场记录/检查点。未发现阻塞此次有限恢复验收的问题。验收是恢复能力与短时运行证据，不是数据有效日、72h、14/30/60日、alpha或投资资格。

复核只读取ROOT五份保存报告、恢复辅助源码V1/V2、已有归档任务元数据及其SHA绑定，用PowerShell核对哈希和时间/计数差；仅新增本报告。没有运行Python、采集、API、数据库查询、QA、磁盘扫描、源码执行、registry或Git，没有再启动进程或经济回测。进程存活结论限于sample1/sample2实际采样，不宣称未来持续运行。

## 报告身份与来源

五份ROOT报告SHA256：

|报告|SHA256|
|---|---|
|PRESERVATION|09719320c32d72f4c2e5f52b4dc1e444681173562562460aa434a31273aee9be|
|MANIFEST_IDENTITIES|6155d4dc8b96dbb9c9c4fb1c166a4eacaf268392ef8035344b16195d48e4eff3|
|RESTORE_LAUNCH|7bd945bae16b233fdb8f8bad3b29b2f0ae7eed9a7c85989eefac7bdcde4130b6|
|RESTORE_SAMPLE1|642602a3aee114776aa45af10a11720776728376863975f5a9959166d1d278ec|
|RESTORE_SAMPLE2|6f6f964581ae1d96602fbfb208ba6c3a60b7275a35c07c5e056a03db421d8468|

ROOT字节与恢复报告所绑定的STATE preservation、manifest及sample1身份一致。13项公开采集来源SHA逐项匹配当前字节；当前 `src/quant/microstructure.py` SHA仍为 `649a69c924cdcfc4e85dca37a2a6c4958993f3f3365e04b3f10372f8875ddbb4`，与旧binding及新session一致。

preservation实际先确认进程缺失，保存原DB/WAL/SHM、旧日志、任务、启动命令和audit/checkpoint来源。两份闭合衍生数据库分别记录quick_check=ok；原数据库没有被preservation SQL打开，衍生查询后原文件仍稳定。退出码与退出原因明确UNKNOWN，没有将“进程缺失”编造成OOM或正常退出。

preservation本身的payload SHA检验标为NOT_PERFORMED；之后独立manifest任务才实际完成2008/2008原清单成员的字节/SHA身份，96,171,882字节全部exact、errors为空。两个阶段范围被区分，不能把文件身份视为来源数据质量或有效天数验收。复核没有重复读取2008个payload。

## 单次恢复及V1/V2范围

launch报告记录两条已有命令：同一D盘 `.venv/bin/python -u -m quant.collector_public_v3 --run` 与 `quant.microstructure --run`，均通过现有progress/bounded入口、新独立日志和detached session运行。没有切换microstructure_v2、数据库、store、schema、采集端点或账户权限。

恢复辅助V1 SHA为 `120f1c551e2c2d73475e6c5b1e4f9f5c052d7145857d061a5637b93d6ab32980`，V2 SHA为 `5e14a6506e6f89e82207db6fc1e3d40c0c12708f787d97c84fdff5d5ecf6b956`。逐行比较仅新增：

```python
if not args or args[0] != str(ROOT / '.venv/bin/python'): continue
```

这是将含有Python参数的bash/progress wrapper与真实Python进程区分；没有修改采集源码或参数，也没有执行第二次launch。launch阶段的wrapper_pid不是应报告为实际采集Python的PID。

两个样本均保存准确的两条Python记录：

|模块|PID|start_ticks|任务|
|---|---:|---:|---|
|quant.microstructure|890567|20387105|497aaa6d5bcb4661b4a4a02a5b4b6cb6|
|quant.collector_public_v3|890568|20387105|c1242fb3275342deaddd658c4d14d0e1|

两者位于既有coin-quant.slice下，样本任务元数据为running，PID/start_ticks与proc记录一致。两次样本errors均为空。此结论来自样本中的真实proc和任务对应，不仅凭旧锁文件或日志推测运行。

## 新会话、断档与实际推进

公开采集由旧session5进入session6。旧session最后心跳到UNGRACEFUL_PREVIOUS_SESSION检测之间为7,139.314秒；事件明确 `unobserved_time_not_credited=true`，并保留原audit链head。sample2新session healthy_seconds仅165.5286，未继承旧session的195,683.5528秒。

L1由旧session `6ba28c2935bc4c858f988ac62cd5a6da` 进入 `a1cb5a053be046b193906f3b4a011d91`。新SESSION链接旧audit head，RESTART_GAP起点准确等于旧checkpoint.asof_us；记录断档9,874.619301秒及 `uncommitted_tail_unknown=true`，没有补记连续观察。新accepted_events是新session计数，不能同旧累计数拼成资格。

sample1→sample2采样间隔161.885235秒，独立保存计数差为：

- 公开心跳推进165,528ms；同一session保持RUNNING。
- BTC、ETH分别新增3条websocket闭合分钟记录，REST计数均仍553；last_open_ms均由1791127980000到1791128160000，新websocket接收时钟推进。
- L1保持CONNECTED及同一新session；checkpoint.asof_us推进163,029,166us，accepted_events从2,753到10,114，增加7,361；新接收时钟和audit head推进。

L1保存feature_rows=748,394和feature_bytes=96,293,759在两次样本之间未增加。它们比preservation时多，但sample1→2只能证明实时接收/检查点推进，不能据此证明该时段所有事件已变成持久feature或完整有效日。检查点、分钟闭合记录、文件身份与资格是不同验收范围。

sample报告均明确 healthy_gap_splicing=false、real_time_days_certified=0、alpha_eligible=false；公开qualified_72h为未认证。REST补齐minute数据库后unresolved_gaps=0，也不能抹去上述实时时间断档或认证健康连续性。

## 环境、资源与权限

恢复入口沿用原D盘环境；source_contract与旧保存合同完全一致，版本记录仍为Python3.12.3、httpx0.28.1、numpy2.5.3、sqlite3.45.1、websockets16.1.1；L1 binding仍为live microstructure_l1_v1、原store与polars1.44.2压缩配置。当前uv.lock/pyproject和源码SHA匹配。复核未新运行环境探针，运行版本一致性依赖恢复helper实际source_contract比较及保存样本。

launch实际容量扫描记录项目4,314,849,443字节、整个D盘WSL VHD23,047,700,480字节，总27,362,549,923字节；加1GB预留仍低于32GB预警/36GB停止新增/40GB硬边界。复核没有重复扫描，也不把该时刻值称为当前实时磁盘值。

共享cgroup硬上限4,999,999,488字节；sample1内存241,995,776、sample2为219,688,960字节，swap0/GPU0，max/oom/oom_kill事件均0。3,263,008,768字节是内核组历史峰值，不是恢复任务专属峰值。仅这些采样无法证明整段运行最大内存，既有硬守卫仍承担资源边界。

报告保留公开数据只读范围、credentials=false、financial_accounts=false、orders=0、locked=false、新服务0、source_switch=false。恢复没有新增交易或研究资格；经济账本本轮没有重测。

## 交接与限制

可接受原两路采集的单次恢复和两样本推进。故障根因仍UNKNOWN；不能根据本轮低内存样本解释旧退出。若后续心跳/检查点停滞，应核真实进程与退出证据，不能因观察超时重复启动。

没有本次具体blocker；仍未完成的事项包括持续健康时间、L1有效日/feature落盘完整性、候选未来证据与盈利判断。恢复后研究可依据既有预算推进，资金/发单/keys/holdout权限不扩大。
