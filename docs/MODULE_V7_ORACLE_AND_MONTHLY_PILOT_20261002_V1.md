# v7 四周期 oracle 机制诊断与官方月档试点

## 科研结论与下一实验

当前无合格长期净APR候选。已有连续14日XGB-S研究proxy净 −0.1591%，本次
oracle使用未来flow，不能增加APR证据。优先检验严格OOF预测flow→impact及
同样本direct return，衡量现实预测误差后剩余可支付成本edge。

使用已验收July首30日、120原daily档，5/15/30/60m共享34,311可用端点；
train11,590/validation2,283/development test9,281，Jul15至Jul22前为已查看开发数据。
最大标签成熟时间3610s，统一60m embargo。past-state只来自已经闭合的历史bar，
目标scaler和regime切点仅fit-period拟合。一个固定XGB-S配方、8资产/horizon模型，无HPO。

| ETH诊断 | 5m | 15m | 30m | 60m |
|---|---:|---:|---:|---:|
| 真实未来永续flow与Spot return rank关联 | .706 | .745 | .746 | .756 |
| 固定35bp、非重叠oracle交易数 | 61 | 134 | 136 | 82 |
| 平均毛edge/等名义往返break-even成本，bp | 35.01 | 50.42 | 58.34 | 72.52 |

毛edge不是组合NAV。原往返成本20bp fee＋8bp slippage＋2/4/8bp spread保持。
未来flow与return区间重叠，关系可能内生；全四周期端点先按未来有效性共同筛选，
该过滤无法在线实现。测试regime集中，7日结果不足以认定稳定关联、因果impact、
数学收益上界或可预测净收益。没有BBO、真实冲击、资金费率/借贷或交易所成交证据。

## 实际运行与必要核验

oracle正常退出，87.50秒、RSS535,830,528B、GPU小时0，模型与预测留STATE/D盘。
独立核验128个原始flow窗口、closed past-state、统一split成熟/embargo、保存模型全
9,281端点预测（误差0）及固定阈值edge/成本算术。首个导入命名错误在拟合/市场
读取前失败，失败源与退出码留存；复测另立凭证，不覆盖旧报告。

主凭证 `V7_ORACLE_FLOW_HORIZON_20261002_V1.json`；独立核验
`V7_ORACLE_FLOW_HORIZON_CORRECTNESS_20261002_V1.json`；真实数据/模型为
`/home/xflops/coin-state/v7-oracle-horizon-20261002-v1`。

## 官方monthly来源试点

复用官方Binance URL/格式/CHECKSUM和冻结trade_flow_v2；只增加只读UTC分日
ZIP视图，原CSV解析/聚合计算不改，不生成虚构daily ZIP，不写新downloader框架。
September Spot BTC30日/518,400行通过完整ZIP EOF/CRC、CHECKSUM和独立逐行QA。
Sep1–5与既有daily Parquet字节完全一致。月档新来源使用独立status/store，不伪装旧acceptance。

获取/转换382.33秒、RSS86.69MB；独立QA32.45秒、RSS108.87MB。
新增Parquet79,774,108B，原ZIP301,688,191B已经实际删除。
独立QA不在删除后重建全部原始交易行，不作alpha/真实未来资格。
实测完整磁盘13,244,401,587B，UTC 2026-10-02T01:03:21.999717；仍需1GB工作保留。
四流September/October继续串行，不将运行中receipt当作PASS。

本模块沿用原5GB共享硬限/swap0、无GPU、无locked、无真钱、无新观察器。
第三方仍为OPEN_SOURCE_REGISTRY登记的原Binance repo/commit/MIT软件与单独数据条款。
原v6/v4、STOP_v2、FrozenPredictor及ExecutionContract证据均保留。
