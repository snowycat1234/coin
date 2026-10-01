# 当前长目标：开源复用科研 v6

当前步骤：官方四路两日、共同dataset和全部10配置工程模拟/统一评价通过；
用户新增本机实时任务窗口已独立验收（15项＋真实扫描＋断线恢复），每2秒显示任务。
这是单独的用户体验模块；下述40项主研究门槛及23/40计数保持。
180历史日下载运行中，正式六fold入口已完成工程拒绝/恢复验收；未开始正式首轮或top-3晋级。
首个原定完整21日窗口10配置诊断和首30日历史来源均已验收；
正式入口独立复核通过，换手口径以新补充文档为准。单窗口诊断不勾选正式六fold结果项。
首30日来源/结构独立QA及根侧240文件SHA/行数/边界已通过；第13/14项仍等待180日验收。
完整单窗口10/10已闭合并根侧接受；9静态checkpoint复现、River终态及30成本账本通过。
FR69 V2的30日来源preflight通过，实际连续14日比较已启动，正式166日仍待180日来源。
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
- [x] 12 BTC/ETH×Spot/Perp四路完整UTC日对齐
- [ ] 13 >=180实际历史完整日，无缺日期静默忽略
- [ ] 14 历史长期特征≤8GB，整个项目/VHD与新增增长复核

## FR64 唯一科研数据与评价合同

- [x] 15 Parquet streaming/row-group dataset，无巨大窗口materialization
- [x] 16 所有adapter共用sample IDs/tensor/labels（工程接口；实际完整模型比较仍待各模型运行）
- [x] 17 过去256×5s输入，严格可得时间与缺口排除
- [x] 18 两primary/two auxiliary因果标签与成熟时间
- [x] 19 固定chronological folds、5m embargo、train-only normalization
- [x] 20 trade-based return proxy来源、spread假设和费用滑点明确
- [x] 21 所有模型共用预测与经济评价（十配置982端点工程模拟；正式六fold待完成）
- [x] 22 固定10configs/1seed，无新搜索或locked消费

## FR65/66/67/68/69 模型复用与运行

- [ ] 23 Ridge1/XGB2真实历史初轮结果
- [x] 24 pytorch-tcn依赖及shape/causal/deterministic/no future norm smoke
- [ ] 25 TCN-S/M同一数据实际运行
- [x] 26 MIT TLOB上游固定commit/LICENSE/UPSTREAM与薄adapter
- [ ] 27 MLPLOB1/TLOB1同一数据实际运行
- [x] 28 MIT TS2Vec最小核心/兼容性修改与来源登记
- [ ] 29 train-period预训练后linear/LGB两个probe
- [x] 30 River依赖，predict→label mature→learn_one复测（六项＋真实短段2095成熟更新）
- [ ] 31 Static/River/weekly refit同一chronological replay
- [ ] 32 GPU确需使用时资源落实；GPU-hours与peak RAM实测

## FR70 统一结论与后续门槛

- [ ] 33 统一MODEL_LEADERBOARD：flow IC/sign、return Pearson/Spearman、RV rank
- [ ] 34 gross edge/fee/spread/slippage/net/turnover/Sharpe/MDD完整列出
- [ ] 35 实际OOS fold同号≥60%，positive signal集中度≤60%独立判定
- [ ] 36 可预测但成本受限明确记录，不当生产通过
- [ ] 37 第一轮结束只保留最多top-3；其余停止
- [ ] 38 仅top-3允许后续3seeds/ablation/regime；TS2Vec若晋级，才允许唯一fine-tune配置
- [ ] 39 无预测结构则记录有效否定结果，不扩复杂模型
- [ ] 40 最终研究结论、模块凭证、文档与远程一致性汇总

资金授权、锁定历史启封、候选未来资格仍为另外的用户授权与实测门槛。

FR61已登记8个官方项目、固定commit及许可证；凭证
`reports/fast_research/FR61_OPEN_SOURCE_REGISTRY_ACCEPTANCE.json`。
FR62已闭合真实BTC现货2025-07-01一天，CHECKSUM通过、17,280桶/2.72MB，raw已删除。
当前23/40项有阶段证据；十配置短段工程模拟通过，不代表180天和正式模型研究完成。
FR62根侧凭证：`reports/fast_research/FR62_OFFICIAL_PIPELINE_ACCEPTANCE_20261001.json`。
FR63 V1首日实际失败已保存，当时完整共同日=0；不会用原始编号跳号直接冒充永续档案缺失，
也不会将这些跳号静默删除。V2四路两日已通过，原失败凭证原样保留。
FR66/FR67根侧工程验收已闭合，共同最终16项通过；尚无市场训练或预测结论。
FR63/FR64真实8档/22,096,957B/2,355共同样本已独立验收；24个标签手工回算通过。
共同缓存复用原源码，3项测试通过；24样本输入/八标签/ID/价格/时间精确相同，
仅原始净USDT流量QA允许1e-6绝对或1e-12相对浮点差。暖访问实测快10.47倍。
180历史日批次已启动；Ridge/XGB-S/XGB-M同一短段工程smoke三项已完成，不授正式研究资格。
TS2Vec上游最小核心及三项smoke已通过；正式六fold两个probe和预训练仍待执行。
后续：TS2Vec已在共同两日fitting段完成600次官方迭代及两个probe；TCN-S/M、MLPLOB、TLOB
均完成一epoch市场接线smoke，同一982测试端点。正式六fold训练仍未通过。
共同native工作副本八文件SHA及24真实完整样本逐项相同，暖访问段实测快340倍。
River六项、共同评价十一项最终测试通过；十配置共同真实评价全部982×8标签一致。
主成本情景三项有交易模型均亏损，七项无交易；不据此改配置或选top-3。
WSL重启已保存/恢复，88已验校历史文件续跑独立V3，不拼接健康时间。
正式入口两项恢复/缺历史提前拒绝通过；不足720档不会拟合，不提前造排行榜。
