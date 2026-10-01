# A03 通用候选纸面引擎接线

## 范围与准入

本模块把现有 `CandidatePaperEngine` 接到 `FrozenCandidateStrategy`，引擎不再直接执行 Logistic scaler/coefficients。生产工厂仍走原开发报告与单次发布凭证；实际 `STOP_v2` 未解除。传入通用模型的构造仅允许 `engineering_simulation`，拒绝发生在 source/journal 文件、锁及网络写入前。没有新增 CLI、生产启用入口、训练、参数搜索、真实订单或锁定价格读取。

旧源码 SHA `e01f836c9640a9fafd648600024237c7cd26e32e048d0a7ff8632e5cb7d5de2a` 保存在 `legacy/a03_candidate_original/<SHA>/candidate_paper.py`，索引为 `legacy/a03_candidate_original/INDEX.json`。原 G45 文档/验收引用与初次失败记录保留，不以本模块覆盖既有凭证。根代理独立审查与最终凭证另行生成；以下工程测量不宣称独立审计已通过。

## 接口

- 旧接口：`CandidatePaperEngine(source, journal, model=legacy_json, config=...)`。十项原增量特征、15m/1h、原顺序 `sum` 聚合、非零系数 scaler/logit/probability/target 保持精确兼容。旧 fixture 没有正式训练元数据；`LegacyPredictorAdapter` 显式声明未认证训练来源，不补造 cutoff/data SHA。持有参数仍为 0。
- 新离线接口：`CandidatePaperEngine(source, journal, predictor=already_loaded_frozen_predictor, feature_provider=Hourly40FeatureProvider(), decision_policy='A'|'B'|'C', config=ShadowConfig(mode='engineering_simulation'))`。
- `ingest_bar(bar, received_ms)` 只消费原闭合 WS 分钟 Kline 所携带的 OHLC、成交量、主动买入量。禁止 REST 补信号、未来/迟到超过 15s、重复变更、倒序分钟。`ingest_tick` 及实际 `CandidateCollector.handle_message` 路径已接线。
- `feature_ready(end_ms, now_ms)` 验证共同逻辑可得时点与两币实际收到时间；collector 通过 `notification_ready` 唤醒。旧简化通知提示可唤醒额外 tick，实际推理仍严格要求 receipt。

新增 `candidate_strategy.py` 的通用输出只有 expected_return/confidence/target_weight/semantics/release；正式预测输入只取模型精确 feature_names 加 symbol/interval/available_us/received_us 四个上下文字段。OHLC、emitted_asof、其他 A04 辅助列不会传入模型。缺回归结果明确风险归零；字符串、bool、非有限值、错误 release/semantics、范围错误被拒绝，`target_weight=None` 不会自动变成长仓。

## 因果特征与决策

Hourly40 provider 组合已验收的 `HourlyFeatureState`，保留两币共同小时 pending、100 根连续历史和 EMA。小时由完整 60 个分钟组成，逻辑 availability 为共同 close_us，实际 receipt 独立保存为两币最大接收时间。时点乱序但在 15s 内合法配齐不会被先到 quote 消耗；未配齐先等待，确证缺口或超时才风险归零。迟到/缺信号的风险判断采用实际 now 排队，不能回填旧信号时点的可成交资格。

ABC enter/exit 值和原策略源 SHA 同时绑定；数值策略与已冻结 `hysteresis_targets_v2` 逐序列一致。意图持有两小时；订单同时携带 `minimum_hold_minutes=120` 与 risk override。实际约束复用冻结 ShadowV2，按首次真实模拟成交计算两小时。风险缩仓/清仓可越过普通持有约束。

candidate/fee_x2/slippage_x2 分别持久化 policy 与 holding。`_account` 上下文向父金融方法提供每个场景独立 alias，并在 finally 恢复 config/现金账户/capacity/consumed_quotes/holding。B2 无 alpha hold。首次部分成交锚不会被后续加仓覆盖；币尘保留金融 cycle，重入单独建立新 holding 锚。风险清仓后原意图仍 long 时，下一次从零买入也复用已修复父执行规则重建锚。

资金、成交、日度 NAV、尝试/费用/换手/现金/数量算法仍由冻结父实现承担。`_append/_fill/_seal_days/_cancel_pending` 资金方法的原算法保留；独立根审计会比较归档与现版本 AST。

## 恢复与绑定

绑定涵盖原生模型 bytes SHA、manifest/release SHA、精确特征定义、固定阈值数值、策略/adapter/predictor/执行/金融源 SHA、成本/风险、来源与版本。constructor 与恢复拒绝任何变化；运行 guard 检查 strategy/provider/predictor/interval/model_sha/binding 重绑定和实际源变化。执行合同缓存仅使用默认冻结规范实例，并以执行源实际 SHA 为 key，返回副本；源变更仍拒绝。

共同 provider 完整 snapshot 及分钟增量写入同一追加不可改写链。恢复选最新已认证 joint 锚并只重放其后的 feature_minute；财务/健康不重放、不补 credit。金融 checkpoint 保存账户、pending、各场景 policy/holding 等全部可变状态，以 SHA 引用 start:candidate 的完整不可变 binding。恢复先校验该锚及引用，再恢复特征。错误引用/损坏快照拒绝且不新增记录。金融 tick 暂存只读特征引用，父交易事务只复制/回滚金融状态；finally 恢复特征，异常中的现金/仓位/链头/alias 保持一致。

CandidateCollector 只在自己隔离的 source 库增加 `(symbol,source,received_ms)` 覆盖索引，查询语义不变，索引字节计入容量。任何受保护实时库名字、public/microstructure/未知来源表，即使改名也先只读拒绝，禁止创建锁/索引/元数据。专用候选 source 合同绑定来源和候选实现。

## 工程证据与资源

最终测试 XML：`reports/A03_CANDIDATE_FINAL_TESTS.xml`。两种原生 40 特征接线路径固定使用已有开发历史首 fold `LGB_A/fold0` 与 `XGB_A/fold0` 模型原文件及 manifest，不修改、不重签、不按收益选模型、不 fit。实际闭合 WS handler →完整小时→40 特征→原生推理→统一输出→四账户，另以直接 CPU Booster 同向量核对。固定模型可能全部现金；实际持仓/partial/费用/风险/故障分支以明确 stub 工程 oracle 验证，不能称 stub 原生模型盈利证据。P06 对工程来源仍 `INSUFFICIENT_EVIDENCE`、真实资格天数 0。

`scripts/measure_candidate_adapter.py` 顺序测量独立 native 库的 24h 合成完整结构：两币每秒 quote、每币 closed minute、原小时特征/决策/四账户/heartbeat/checkpoint/NAV/审计及重启。独立 5min 低容量探针真实产生每秒尝试与金融 checkpoint。测量包含 source/journal DB、WAL/SHM、索引、类别最大 payload、采样峰值、32d synthetic risk seed、100h synthetic feature seed、进程 RSS 和全盘/VHD。源 SHA 在开始和结束核对，报告 exclusive 创建。

180d 安静/持续低容量投影独立列示，联合预算从最新 project+整个 VHD 占用出发，仅增加未来增长、A07 剩余 8GB feature/4GB raw 限额、公开 source 与微观审计预留，避免再次相加已经位于 VHD 中的 fixture 文件。36GB intake 保留 4GB emergency，40GB hard。部分市场/健康持续抖动的粗上界另列，不承诺任意故障可持续 180d；硬磁盘 guard 继续停止 intake。投影不是实际 24h 容量证书，也不能替代 180d 同版真实记录。

所有执行在 D-hosted hpc_linux，通过共享 `coin-quant.slice`（总 RAM≤5GB、swap0），CPU 单线程推理，无 GPU。正式模块状态需结合根独立审查与实际容量报告，不授 alpha/future/真钱资格。
