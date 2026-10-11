# 2022 CORE5贸易价／标记价RV：真实恢复通过，热身缺口明确

这是独立的**数据价值模块**，不是失败HAR的参数、窗口或资产补救。源包在HAR拟合前的历史inventory中已识别；使用完整2022November、原CORE5顺序、两种价格流，不依据行情结果挑选。冻结协议0f7f5c2a，解析源码445720c4da101d40b990ac4ba79eeb1958094d97。无拟合、钱包或provider下载。

复用 [Git d69e9ac 的来源INDEX](https://github.com/snowycat1234/coin/blob/d69e9ac94478c5be54cb46c622afec7aaf3c61f7/research_artifacts/e5_bear_recovery_20261008/INDEX.json) 四个bytepart，重组28,983,173B、SHA98e38bc3f0e6a16fd51a63be880371882d4e2b52df1d8ec5a39963721d2d2bb8。只解析2022November十个原始分钟ZIP及CHECKSUM；未解析包内旧模型/账户/结果或2023January行情。163个包成员目录只用于身份检查。独立只读审阅核CHECKSUM、member与官方下载manifest；主模块核实际CSV，避免两agent重复行情解析。见 [INDEPENDENT_DATA_CHECK.json](INDEPENDENT_DATA_CHECK.json)。

所有10条实际流各43,200分钟，合计432,000行，exactgrid、原始OHLC、CRC、CHECKSUM全部通过，无缺失填充/去掉冲突行。贸易价zero_quote=0；标记价的volume是占位0，**不能把标记价volume当成交可用掩码**。下采样保留每第五根分钟的实际close及其保守完成时钟，8640个五分钟端点/流。首日缺前一日端点，RV保持NaN，其后29日完整；两种价格域共290个资产域日RV。

| 资产 | 全月mark/trade RV总量比 | 五分钟端点最大绝对价差/bp |
|---|---:|---:|
| BTC | .987779 | 32.27 |
| ETH | .979318 | 197.79 |
| SOL | .823597 | 542.99 |
| XRP | .981789 | 67.52 |
| DOGE | 1.014816 | 116.40 |

价域差异说明贸易RV不能直接替代标记价格风险。表中价差只覆盖五分钟close，不是逐分钟极值或隔离清算阈值验证；没有交易收益或账户保护结论。完整SHA/时钟/零量/各域指标见 [RECOVERY.json](RECOVERY.json)。

固定30个完整日RV加下一日成熟标签的可用样本数：**0（两个域均为0）**。2022-11-01 00:00的预测必须使用10月2–31日30个完整UTC日RV；第一个日内return还需10月1日23:59开时的1m bar实际close（10月2日00:00完成）。数学最小分钟数据为该前值和10月2–31日全量；完整October月档案足够，无需September。先前33heads、本次34heads路径核验未识别完整October分钟档案，这不证明其它未展开历史包内永远不存在。该缺口不以日OHLC、缺失补零或假造2026账本代替。

独立审阅核实五份资金费表footer及member身份，字段calc_time_ms/funding_interval_hours/last_funding_rate/past_mark_price/past_mark_available_us；manifest保留UNCONFIRMED_RAW_PRESERVED。这里只检查metadata，未消费资金费值；历史发布/扣款时刻与单位仍未认证。正式钱包仍需来源合适的逐分钟实际mark/trade、实际资金费及原生账户规则，不能把本RV面板当成完整执行账本。

实际解析2.83秒，守卫4.33秒、采样RSS159.9MB，1CPU/2GBRSSstop/4GB地址空间/15GiB预留，无GPU/swap。既有2021HAR科学尝试/两项旧STOP/永久unpaidHALT修复、distribution分支和collector2026锁保持。源包中的账本只作运输字节SHA，不作研究输入。

公共 [DATA_BUNDLE.zip](DATA_BUNDLE.zip) 392,857B，9个成员，保存实际5mincloses、日RV、来源receipt及主/独立审阅守卫；[PUBLIC_BUNDLE.json](PUBLIC_BUNDLE.json)逐成员绑定。下面冷恢复命令从公开Git读取到新目录，复核来源SHA及290个日RV，无原STATE读取、重拟合或新钱包。ARTIFACT_COMMIT取发布此数据包的提交：

```bash
COIN_CPD_STATE=/workspace/rv2022-cold-guard QUANT_ROOT=/workspace/coin-har-risk \
QUANT_STATE=/workspace/rv2022-cold-guard bash research/slow-momentum-cpd-20261011/launch.sh \
 /workspace/coin/.venv/bin/python research/core5-2022-rv-source-20261011/cold_verify.py \
 --commit ARTIFACT_COMMIT --directory /workspace/rv2022-cold-restored
```

需重做分钟解析时，checkout445720c4，将INDEX四byteparts按index顺序拼接为originals.zip并核上述完整SHA，再经同一守卫运行 `recover.py --archive originals.zip --output fresh-prepared --source-commit 445720c4da101d40b990ac4ba79eeb1958094d97`。既有Git原件是可恢复输入，未经新网络下载。公共冷验收只重算已测RV，不重复43万行分钟解析。
