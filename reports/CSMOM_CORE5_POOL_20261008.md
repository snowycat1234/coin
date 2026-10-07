# 固定五币池：单因素完整钱包对照

决定 RETAIN_CORE_POOL_DEVELOPMENT_CLUE；投资NONE/CASH。仅改变币池，两个新账户/零拟合，原配方仍暂停。

|资金费解释|五币净PnL|原六币净PnL|差额|LONG净|SHORT净|波动|分钟MDD|费/执行/资金费|换手|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|0.01|838.90|1192.46|-353.57|523.69|315.21|9.70%|4.16%|73.97/107.60/0.04|13.45|
|1|842.85|1193.48|-350.64|493.53|349.32|9.68%|4.11%|73.99/107.62/3.88|13.45|

同一2025已见181日、10k共享资本、相同双侧参数/成本/资金单位；池改变会改变排序、协方差和后续钱包，不是从六币结果减去PEPE利润。
旧六币HOLD/SMA不能充作五币同池强控制。仅筛查原2025正收益能否在既有核心池保留，不提供独立/全年或长期APR。真实gross漂移与风险延迟仍按原引擎报告。

复现：python -B scripts/research/check_momentum_pool.py --protocol protocols/CSMOM_CORE5_POOL_20261008.json --state /home/ubuntu/coin/execution-state/csmom-core5-20261008-NEW，须已有8GB/swap0/GPU0受限scope。
