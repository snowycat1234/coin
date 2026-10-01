# 当前长目标：开源复用科研 v6

当前步骤：FR61已验收推送；FR62真实现货日已验收，FR63四路首日发现永续编号语义问题，正在另建v2修正。
下面仅凭实际工件勾选；旧v3/v4清单保留，当前优先级为用户直接指定的v6。

## 约束与保留

- [x] 01 原v6附件字节、SHA及用户最高优先级授权登记
- [x] 02 保留ExecutionContractV2/FrozenPredictor/STOP_v2/A07/holdout工程证据
- [x] 03 冻结新execution/Testnet/mainnet/resource-observer工程
- [x] 04 磁盘40GB、共享RAM5GB、swap0、GPU需要时再落实
- [ ] 05 完成模块普通GitHub推送并核验远程（持续）

## FR61/62/63 官方来源与数据

- [x] 06 官方repo、commit/version与许可证登记
- [x] 07 LOBFrame仅方法参考；LOBench未确认许可前不vendor
- [x] 08 官方aggTrades Spot/Perp URL、字段和时间单位
- [x] 09 ZIP/.CHECKSUM实际SHA256核验
- [x] 10 薄转换器产生固定5s schema；V1现货已验收，永续修正另建v2
- [x] 11 真实一天download→checksum→convert→raw删除→manifest验收
- [ ] 12 BTC/ETH×Spot/Perp四路完整UTC日对齐
- [ ] 13 >=180实际历史完整日，无缺日期静默忽略
- [ ] 14 历史长期特征≤8GB，整个项目/VHD与新增增长复核

## FR64 唯一科研数据与评价合同

- [ ] 15 Parquet streaming/row-group dataset，无巨大窗口materialization
- [ ] 16 所有adapter共用sample IDs/tensor/labels
- [ ] 17 过去256×5s输入，严格可得时间与缺口排除
- [ ] 18 两primary/two auxiliary因果标签与成熟时间
- [ ] 19 固定chronological folds、5m embargo、train-only normalization
- [ ] 20 trade-based return proxy来源、spread假设和费用滑点明确
- [ ] 21 所有模型共用预测与经济评价
- [ ] 22 固定10configs/1seed，无新搜索或locked消费

## FR65/66/67/68/69 模型复用与运行

- [ ] 23 Ridge1/XGB2真实历史初轮结果
- [x] 24 pytorch-tcn依赖及shape/causal/deterministic/no future norm smoke
- [ ] 25 TCN-S/M同一数据实际运行
- [x] 26 MIT TLOB上游固定commit/LICENSE/UPSTREAM与薄adapter
- [ ] 27 MLPLOB1/TLOB1同一数据实际运行
- [ ] 28 MIT TS2Vec最小核心/兼容性修改与来源登记
- [ ] 29 train-period预训练后linear/LGB两个probe
- [ ] 30 River依赖，predict→label mature→learn_one复测
- [ ] 31 Static/River/weekly refit同一chronological replay
- [ ] 32 GPU确需使用时资源落实；GPU-hours与peak RAM实测

## FR70 统一结论与后续门槛

- [ ] 33 统一MODEL_LEADERBOARD：flow IC/sign、return Pearson/Spearman、RV rank
- [ ] 34 gross edge/fee/spread/slippage/net/turnover/Sharpe/MDD完整列出
- [ ] 35 实际OOS fold同号≥60%，positive signal集中度≤60%独立判定
- [ ] 36 可预测但成本受限明确记录，不当生产通过
- [ ] 37 第一轮结束只保留最多top-3；其余停止
- [ ] 38 仅top-3允许后续3seeds/ablation/regime
- [ ] 39 无预测结构则记录有效否定结果，不扩复杂模型
- [ ] 40 最终研究结论、模块凭证、文档与远程一致性汇总

资金授权、锁定历史启封、候选未来资格仍为另外的用户授权与实测门槛。

FR61已登记8个官方项目、固定commit及许可证；凭证
`reports/fast_research/FR61_OPEN_SOURCE_REGISTRY_ACCEPTANCE.json`。
FR62已闭合真实BTC现货2025-07-01一天，CHECKSUM通过、17,280桶/2.72MB，raw已删除。
当前12/40项有阶段证据；第10项仅记录已验收V1现货工程，不代表四路共同合同通过。
FR62根侧凭证：`reports/fast_research/FR62_OFFICIAL_PIPELINE_ACCEPTANCE_20261001.json`。
FR63首日实际失败已保存，完整共同日=0；不会用原始编号跳号直接冒充永续档案缺失，
也不会将这些跳号静默删除。公共数据合同待新的聚合成交计数版本及四路实测。
FR66/FR67根侧工程验收已闭合，共同最终16项通过；尚无市场训练或预测结论。
