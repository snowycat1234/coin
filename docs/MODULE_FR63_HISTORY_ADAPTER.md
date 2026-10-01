# FR63：统一聚合计数与官方历史批次

状态：四路两日工程已独立验收；180个共同历史UTC日正在收集，尚未完成。
凭证`reports/fast_research/FR63_FR64_REAL_TWO_DAY_ACCEPTANCE_20261001.json`。

## 修正与复用

真实V1首日Perp失败报告与脚本快照保留。该档案CHECKSUM通过；788,464聚合编号
相邻、时间有序、原始范围不重叠，但原始范围跳号299处/350编号。官方永续接口排除
保险基金/ADL成交，不能要求其原始范围像现货一样连续；每个跳号的具体成因仍未知。
原始范围跨度也不能证明准确原始执行次数。

`trade_flow_v2.py`复用冻结V1解析器及整套5s聚合数学；独立模块实例只把观察的每个聚合
作为一个计数单位交给原引擎。原始a/f/l在适配层先校验，并在manifest还原真实值。
序数计数ID只存在内部，不作为原始ID、数据质量证据或模型特征。价格/数量/时间/方向不变。
新schema去除误导性的raw_trade_count，全部市场统一trade_count=agg_count=聚合行数，
buy/sell partition为买方/卖方主动的聚合行数。质量0只证明官方观察范围，不含所有原始执行。

Spot仍要求原始范围相邻且a增加；Perp要求a相邻、原始范围增加不重叠，原始范围跳号
显式计数/保存例子，原因UNCONFIRMED。跨日同时传前日真实last_l/last_a并按市场验证。
未知聚合缺口、重叠、倒序仍停止，不静默跳过日期。

`hf_fetch_v2.py`仅将此转换器注入独立V1薄包装实例：官方URL/HEAD/CHECKSUM/字节限制/
完整磁盘守卫/fsync/manifest/raw清理全部直接复用，不重造downloader framework。
V1来源/store/凭证不改；新的store为`trade_flow_5s_v2`。

## 实测与批次

V2适配8项/6.36秒、薄日期循环3项/3.41秒通过，Ruff通过。
真实2025-07-01和07-02：BTC/ETH×Spot/Perp，共8档，8个官方CHECKSUM通过，
各17,280桶，总特征22,096,957字节。原始ZIP在耐久manifest后删除，8个owned temp均不存在。
跨日范围/聚合边界实际通过；实际Parquet SHA/schema、计数分区、5s cadence重新读取核对。

唯一共同dataset生成2,355有效分钟端点；24个实际样本future-flow、return-proxy和RV
另行手工回算通过。该短段只有工程资格，不提供180日、6完整OOS、稳定信号或成本后收益资格。

批次显式2025-07-01至2025-12-28前，720日文件；仅复用官方daily归档，串行、失败停止，
resume重新验证来源/schema/Parquet/manifest/raw清理及边界。所有历史版本特征合计8GB
子预算，完整项目+整个D盘WSL VHD仍受40GB硬限与36GB停止新增约束。
运行状态在`reports/generated/FR63_HISTORY_180D_20261001_V2.json`，不将运行中计数当完成凭证。
研究用途与Binance数据CC BY-NC-SA条款仍登记，无locked、GPU、真钱或新执行工程。
