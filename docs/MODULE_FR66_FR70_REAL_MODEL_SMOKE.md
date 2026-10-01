# 十配置共同真实数据工程模拟

2025-07-01/02 BTC/ETH × Spot/Perp八档数据，共2,355个有效端点。
与已验收三基线完全相同的短段fold：1,113个train、982个test；一个seed20261001。
10个不同配置全部产出有限`[982,2,4]`预测，使用同一dataset、split、scalers、
八个label、价格观测与费用政策。所有982×8个评价truth与dataset.y_raw精确相同。

## 实际完成

- Ridge/XGB-S/XGB-M沿用已保存结果，没有重训。
- TS2Vec官方fit仅共同fitting段17,158唯一行，600迭代；一个冻结encoder共享两个probe。
  预训练约223.56秒；两个probe约0.01/5.24秒，不把共享训练时间算作两个不同预训练。
- TCN-S/M、MLPLOB/TLOB各一epoch，仅验证市场接线，分别约7.72/12.74/5.88/49.00秒。
  正式协议仍为最多10 epochs、patience3；未据短段结果修改配置或搜索。
- River官方组件按顺序完成2,095次predict/成熟learn，train1,113/test982，末端pending0。
  实际replay约3.25秒；ADWIN成熟误差记录62次诊断事件，没有自动重置或调参。
- 统一评价复用SciPy及原daily_metrics；固定双边20bp fee、8bp滑点、2bp假设spread，
  并共同评价4/8bp spread敏感性。交易、日NAV明细留D盘WSL，不推送行情或模型。

小型结果见`reports/fast_research/FR70_ALL_TEN_REAL_SMOKE_20261002_V1.json`，
可读对比见`reports/fast_research/MODEL_SMOKE_COMPARISON_20261002_V1.md`。
主情景Ridge约−0.5308%、TS2Vec-linear约−0.4374%、River约−14.3271%；其余未触发35bp门槛。
零交易不等同于预测有效或风险资格通过。只有982个工程端点，不能判稳定IC或经济效果。

## 中断和失败原样保留

WSL重启导致原训练及历史下载进程消失；四个已完成部件保留，剩余MLPLOB/TLOB另行完成。
`V6_WSL_RESTART_PRESERVATION_20261001_V2.json`记录闭合SQLite备份、日志、原历史进度和SHA。
旧健康时间不拼接，没有新A11/resource-observer。原历史批次报告快照为22共同日/88文件，
原worker校验既有manifest/Parquet并续跑独立V3报告。
现有两路采集恢复快照证明确实有PID和CONNECTED/RUNNING状态，不授连续健康资格。

River训练已完成后，根侧报告器误把numpy对比数组写JSON，导致序列化失败。
预测/checkpoint已经保存；完整evidence字典和checkpoints计数独立核对，V2报告恢复，未重fit。
原不完整JSON字节以`legacy/failed_reports/FR69_REPORT_SERIALIZATION_PARTIAL_20261002_V1.txt`
保存；实际行情预测仍只留STATE。River独立RSS未记录成功，明确为缺失，不填造峰值。

资源报告有两个scope生命周期，不能合并为持续运行证明。
最新恢复快照全项目＋整个D盘VHD约11.894GB、共享RAM当前0.792GB/该scope峰1.936GB、swap0、OOM0。
报告中的native环境bind命令曾返回0，但当前读者mountinfo未见挂载，**不认证它已生效**；
资源仍由未修改的完整磁盘守卫实测。byte-verified per-fold输入副本实际生效且合同不变。

## 正式研究仍待完成

尚未有180共同历史日、完整10配置×6个事前固定OOS fold、首轮MODEL_LEADERBOARD、top-3选择。
条件性future-valid endpoint价格proxy不能解释为实际BBO可成交或可实施策略；不产生候选。
无GPU、locked消费、真钱或新主网工程。
Fine-tune仅在TS2Vec第一轮晋级后允许一个配置；第一轮仍只两个冻结probe。
六个孤立OOS周内没有第二次weekly XGB refit，不声称完成连续weekly adaptive benchmark；
正式在线比较复用共同Ridge/XGB-S与River结果，未覆盖的连续周另行如实登记。
