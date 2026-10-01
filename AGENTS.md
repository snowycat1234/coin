# 项目执行约束

**当前最高优先级**：用户直接要求立即执行
`OPEN_SOURCE_REUSE_OVERRIDE_v6_2026-10-01.md`，登记
`docs/OPEN_SOURCE_REUSE_OVERRIDE_v6.md`，当前长清单`docs/FAST_RESEARCH_TASK_CHECKLIST.md`。
REUSE FIRST → ADAPTER SECOND → CUSTOM MODEL LAST。冻结除实际correctness blocker外的
execution/Testnet/mainnet/resource-observer工程，不启动新的A11观察器或版本切换。
官方Binance历史URL/格式/CHECKSUM薄包装；pytorch-tcn/TLOB/TS2Vec/River优先成熟实现。
一套dataset/split/labels/normalization/metrics/economics；第一轮固定10配置1seed，两个primary。
不消费locked、不用真钱、不做RL/MARL/world model/dashboard。历史范围2025-07-01至
2026-03-01前；历史研究不受旧live14/30/60天等待约束，也不产生未来资格。
第三方先登记repo/commit/version/license/修改。已有全部冻结证据保留，下述旧v4冲突部分让位v6。

用户于2026-10-01明确采纳新方案，当前增量覆盖为根目录
`CODEX_AUDIT_AND_NEXT_PLAN_2026-10-01.md`，登记见 `docs/V4_OVERRIDE.md`；
旧 `CODEX_AUDIT_AND_NEXT_PLAN_2026-09-30.md` 的未冲突部分与既有证据继续保留。
实际进度、冻结来源和验收凭证见 `docs/GOALS.md`、`docs/PROGRESS.md`、
`docs/V4_TASK_CHECKLIST.md`；旧 `docs/V3_TASK_CHECKLIST.md` 保留。用户的后续指示优先。

- 所有 Python、测试、运行和训练在 `hpc_linux` WSL 中，通过
  `scripts/bounded.sh` 共用最多 5,000,000,000 字节 RAM，项目 swap 为 0。
  项目数据/缓存/临时文件位于 D 盘；完整项目＋整个 D 盘 WSL VHD 合计最多
  40,000,000,000 字节，32GB 预警、36GB 停止新增。当前不使用 GPU。
- 既有冻结研究/采集/质量来源、协议和证据按凭证哈希保护。先核对来源绑定；
  新实验、代码版本、失败、修复和复测使用独立新报告，不覆盖旧证据。
- 两路公开采集可能在后台运行。测试不得在真实 ROOT 中放置预期被守卫拒绝的
  外部符号链接、污染实际来源/数据库或临时删除目录。负面工件、短寿命目录和
  pytest `--basetemp` 放在 `/home/xflops/coin-state/` 的新独立测试目录。
  需要模拟 ROOT 的单元测试仅替换该独立测试模块的 ROOT 常量，全部工件在 STATE。
  不改冻结磁盘守卫来迁就测试；清理只针对可证明属于本测试的工件。
- 当前并行A09/A10，A09验收后才A11切换独立microstructure_l1_v2采集；不改v1来源/
  store/库，不拼接v1资格。v2实际14天仅诊断、30天仅固定Pilot、>=60真实UTC日且
  至少6完整OOS fold才正式预登记研究/M2；Pilot不能产生候选。Candidate冻结后才
  开始它的真正未来记录。启动前联合容量expected≤32GB/stress≤36GB/hard≤40GB，
  含1GB工作临时预算。L5/maker/GPU/复杂模型须满足新审计条件，当前不实现。
- 在线进程异常时先保存日志、检查点、audit head 和必要的闭合数据库备份；
  核对实际退出原因、资源及来源后恢复已授权的公开采集。新会话与断档如实记录，
  不拼接健康时间、不将缺失窗口补记为有效数据。
- A05/A06 当前为 STOP_v2；无新增结果驱动调参、最终拟合、模型冻结或锁定历史
  测试消费。微观结构 <14天只做数据QA/描述性特征诊断，14天仅预测诊断，
  30天固定三模型Pilot，>=60真实UTC日且>=6完整OOS fold才正式研究；须依据实际有效数据与验收门槛。
- 工程/历史回放、实际数据质量/资源窗口、alpha 候选和竞争性未来记录分别验收。
  当前无合格候选或交易所发单。真钱和锁定历史测试分别需要用户明确授权。
- 每完成模块，保存实际验收凭证、更新对应文档和长清单并报告进度。
- 用户指定 GitHub 仓库 `https://github.com/snowycat1234/coin.git`，仅在每完成
  一个模块并验收、修缮文档后提交和推送；不按小时定时推送。提交前核对源码字节与
  冻结哈希、敏感信息及新增文件大小。代码、协议、文档、小型验收报告和人工合成
  工程模型夹具入库；行情原始数据、真实模型文件、数据库、环境/缓存、日志、VHD
  和用户压缩包留在 D 盘。保留既有 Git 历史，不强推；推送需核验远程提交一致。
