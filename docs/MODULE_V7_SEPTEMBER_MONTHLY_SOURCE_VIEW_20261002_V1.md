# September 官方四流月档与92日共同来源

## 科研用途

当前无合格长期净APR候选。本模块仅供应三个已预登记unseen folds的来源，
未读取新月份模型结果/标签来选日期，不证明alpha或真实未来健康时间。
July已看窗口的OOF负结果要求检验regime与价格相关的预测组件；September
支持fold B，October按同官方monthly路径供应fold C，不等待180日大批次。

## 实际来源与独立QA

September Spot/Perp×BTC/ETH四个官方monthly ZIP分别通过实际CHECKSUM、
完整EOF/CRC、冻结trade_flow_v2逐日转换。120档、2,073,600条5s行全部独立
逐行QA通过；18个原daily重叠的实际Parquet字节完全相同。原daily来源不修改，
新月档独立store/status，不拼接旧acceptance或真实时间资格。raw ZIP均已删除。

后续只读source_view调用已有ShardSpec.from_conversion，绑定每个月的已完成
receipt＋独立QA SHA、官方CHECKSUM、实际Parquet SHA/schema，原daily优先，
每个stream/day唯一。2025-07-01至2025-10-01前92共同日真实绑定通过：
368个stream/day＝266旧daily＋102新monthly，共6,359,040行；原ID混合跨日
连续性通过。该步骤只读取来源、metadata/SHA，不读取模型/未来标签。

source-view实际73.10秒、RSS272,416,768B；原剩余September批次真实退出0。
最近完整磁盘13,899,993,807B，实际UTC2026-10-02T01:34:55.398544。
运行保持原5GB RAM/swap0，无GPU。磁盘记录不表示当前正在下载时瞬时用量。

## 凭证和边界

四路monthly与独立QA凭证按具体market/symbol命名，源view凭证
`V7_SHARED_SOURCE_VIEW_92D_20261002_V1.json`；数据保留D盘，Git仅入小型代码/报告。
原v6/v4/locked/STOP_v2来源保留。独立月QA不在raw删除后重建全部原始交易行，
不推断缺号真实原因或所有原始交易完整性。

October新V2薄wrapper已串行启动，使用QA过的Sep30月末边界，并复用现有真实
日数进度接口；它尚在运行，**不属于本模块已接受的月档结果**，独立验收后再推送。
源view与模型共用原dataset API，不写第二套标签/聚合/模型pipeline。
