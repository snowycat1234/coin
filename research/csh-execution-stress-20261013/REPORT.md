# 原 fine STATIC50：固定执行成本与容量敏感性

经济冻结 SHA256：`244109743b2c153bcd7b3dcbf8b3e277509ea9f03f321d6c949900d3284379e0`。6 个新历史钱包各仅一次，3,153,600 个完成分钟；0 base 重放、0 fit、0 调参、0 交易、0 provider 下载。全部2021/2023/2025完整已见开发年，各自独立10,000 USDT，不拼资本曲线。

摩擦臂：每侧fee5.5bp不变，spread/slippage各4→8bp；容量臂：保持base每侧5.5/4/4bp，但prior-minute quote参与率.001→.0005。**cost/cap与base不同，是单因素敏感性，不是同成本、同风险alpha比较。** 原目标、共享钱包、isolated1x/no-topup、fine1e-8、原始资金费事件、严格过去mark和原五次收费终端尝试均保持。

| 年/冲击 | marked净USDT | paid净USDT | Δmarked对base | 分钟DD | 残仓gross USDT |
|---|---:|---:|---:|---:|---:|
| Y2021_FRICTION_DOUBLE | 2406.729488 | 2406.729488 | -92.760083 | 5.178316% | 0.000000 |
| Y2021_CAPACITY_HALF | 2443.440821 | NOT_EVALUABLE | -56.048750 | 5.078372% | 137.274392 |
| Y2023_FRICTION_DOUBLE | 979.582473 | 979.582473 | -180.110021 | 12.827266% | 0.000000 |
| Y2023_CAPACITY_HALF | 1177.110206 | 1177.110206 | +17.417711 | 12.260649% | 0.000000 |
| Y2025_FRICTION_DOUBLE | 1403.035700 | NOT_EVALUABLE | -209.805314 | 8.840752% | 1258.088684 |
| Y2025_CAPACITY_HALF | 1642.144107 | NOT_EVALUABLE | +29.303093 | 8.495813% | 1966.190605 |

base复用：2021 paid/marked2499.489571、DD5.112714%；2023 paid/marked1159.692494、DD11.993969%；2025 marked1612.841014、DD8.497864%、残仓1304.437581，paid不可评价。2023/2025 fine base只读公开结果摘要/原result SHA绑定；未宣称恢复了其未公开完整账本，缺失的base峰值/净敞口/终端成交细项为未知，不补造。

摩擦翻倍使三个年marked收益均降低约92.76/180.11/209.81 USDT；2023两冲击DD均跨过12%。容量减半改变持仓路径，2023/2025 marked点估计略升不能救出现金收益资格：2021从paid-flat转为DOGE残仓，2025残仓增至1966.19 USDT。固定结果保留，不选赢家、延长退出或改费用容量救结果。6/6完整、0 halt、3 paid-flat/3 marked-only；所有失败尝试保留，不继续新增模型或钱包。

| case | 实际作业start UTC | 结果写完end UTC | 状态 | 秒 |
|---|---|---|---|---:|
| Y2021_FRICTION_DOUBLE | 2026-10-13T18:02:44.029513+00:00 | 2026-10-13T18:05:47.886989+00:00 | FULL_PAID_FLAT / ACTIVE | 183.582 |
| Y2021_CAPACITY_HALF | 2026-10-13T18:06:30.632492+00:00 | 2026-10-13T18:09:19.541967+00:00 | FULL_MARKED_RESIDUAL / ACTIVE | 168.645 |
| Y2023_FRICTION_DOUBLE | 2026-10-13T18:13:44.514433+00:00 | 2026-10-13T18:17:01.668349+00:00 | FULL_PAID_FLAT / ACTIVE | 196.793 |
| Y2023_CAPACITY_HALF | 2026-10-13T18:17:18.342418+00:00 | 2026-10-13T18:20:47.566957+00:00 | FULL_PAID_FLAT / ACTIVE | 208.770 |
| Y2025_FRICTION_DOUBLE | 2026-10-13T18:22:00.498896+00:00 | 2026-10-13T18:25:24.754682+00:00 | FULL_MARKED_RESIDUAL / ACTIVE | 203.828 |
| Y2025_CAPACITY_HALF | 2026-10-13T18:27:12.628388+00:00 | 2026-10-13T18:31:14.368391+00:00 | FULL_MARKED_RESIDUAL / ACTIVE | 241.279 |

start为实际有界钱包作业启动（含源码校验/载入），不是准备完成时间；end为最终RESULT写完的实际文件系统时间，非事后估算。单独第一分钟执行微秒未打点。首例60现金预热日ETA仅早期估计；240日实际吞吐3136分钟/秒、余57秒；实际首例183.582秒。六例主体累计1202.897秒，不冒称会话端到端耗时。

| case | gross均值/峰值 | signed net均值/abs峰值 | 成交额USDT | feeUSDT | executionUSDT | fundingUSDT |
|---|---:|---:|---:|---:|---:|---:|
| Y2021_FRICTION_DOUBLE | 16.576833%/53.891963% | 6.349778%/17.688287% | 112783.111900 | 62.030712 | 180.460192 | -168.509722 |
| Y2021_CAPACITY_HALF | 16.523438%/53.890577% | 6.322155%/19.874811% | 112364.121392 | 61.800267 | 89.892977 | -167.279581 |
| Y2023_FRICTION_DOUBLE | 38.424942%/62.332462% | 14.610651%/38.438781% | 204202.925400 | 112.311609 | 326.728652 | -132.863643 |
| Y2023_CAPACITY_HALF | 37.906247%/62.329957% | 14.592966%/38.933124% | 205097.829717 | 112.803806 | 164.079280 | -134.109206 |
| Y2025_FRICTION_DOUBLE | 44.673174%/60.642499% | 12.300324%/29.234726% | 246970.060136 | 135.833533 | 395.160450 | -71.250383 |
| Y2025_CAPACITY_HALF | 44.530907%/60.642184% | 12.326157%/33.864683% | 247722.275827 | 136.247252 | 198.180390 | -72.249858 |

gross/net是实际已完成分钟暴露，原caps是目标/必要减仓约束，不保证瞬时实际gross≤60%；真实62%漂移未隐藏。成交额为Σabs(quantity)*不利fill price；execution已嵌入fill，财务桥不重复扣款。

| case | 终端收费close腿 | 终端成交额USDT | 终端feeUSDT | 精确残余quantity |
|---|---:|---:|---:|---|
| Y2021_FRICTION_DOUBLE | 12 | 2681.379783 | 1.474759 | {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"} |
| Y2021_CAPACITY_HALF | 16 | 2551.697158 | 1.403433 | {"BTCUSDT": "0E-8", "DOGEUSDT": "806.50996905", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"} |
| Y2023_FRICTION_DOUBLE | 10 | 2763.046239 | 1.519675 | {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"} |
| Y2023_CAPACITY_HALF | 14 | 2813.939120 | 1.547667 | {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"} |
| Y2025_FRICTION_DOUBLE | 15 | 5361.952906 | 2.949074 | {"BTCUSDT": "0E-8", "DOGEUSDT": "-4971.23594018", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "-366.33837610"} |
| Y2025_CAPACITY_HALF | 20 | 4790.969042 | 2.635033 | {"BTCUSDT": "0E-8", "DOGEUSDT": "-8103.84123152", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "-551.19202869"} |

## 公开可复现范围

公开包是**指标和财务只读重建，不是完整checkpoint字节冷恢复**。完整无损37字段分钟checkpoint/全部原始NPZ、完整状态及失败私有日志仍保留当前实例，未删除。公开包含原执行源码/薄适配、冻结目标原NPZ、真实source index及重建定位、全部fills/funding/account状态、逐日37字段、分钟核心11字段+int64时钟、37字段原数值指纹、结果/失败原因。最终状态是原snapshot的精确字节，指针引用的全部原日NPZ未随包上传，故不能称完整checkpoint恢复。

独立核验实际从远端已推SHA读取最小包，核每文件/part/member SHA和CRC，在新解释器只读重建全部指标/财务，不导入金融实现、不构造/推进钱包、不fit、不重放base或新历史。源码与target/source绑定明确；本地额外对所有真实month NPZ、fund raw event、每笔mid/prior quote共享容量、严格过去fund mark及finally恢复的raw quote核验PASS。远端包只恢复公开11分钟字段，不声称恢复其余25逐资产分钟字段。

本轮原始FREEZE.json保持实际执行字节与SHA不变。其DEDUP.json是含实例隔离标记的**非经济私有运行记录**，不上传，仅保留原哈希；去重公开结果为DEDUP_PUBLIC.json。原run.py作为实际执行源码归档，默认验冻结时会因私有DEDUP缺失而拒绝新的历史启动。公开默认流程是下面只读核验；新的历史重放须source restore、明确新运行授权/公开运行绑定，不能暗中跳过这个封存检查或混同为本轮的cold证据。

## 只读核验与来源恢复

Python3.12 + NumPy；无需账户、API key、Library、付费或新环境设置。
```bash
python research/csh-execution-stress-20261013/cold_remote.py --commit EXACT_PUSHED_SHA --output NEW_EMPTY_DIRECTORY
```

历史重放需要恢复原真实source，不能直接拿公开指标当行情：recover.py恢复字节绑定的金融源码和原目标；restore_source_code.py + prepare2021.py复用公开2021解析/资金费/边界代码；prepare2023.py/prepare2025.py仅恢复旧公开Git行情与真实事件，并逐月逐文件匹配原hash，不生成新策略目标。原预先发布SOURCE_BINDINGS/PINNED_CODE_AND_TARGETS提供全部定位/哈希。当前已验证36/36月份、各年5475真实事件、完成日价格。2021source index只含运行统计的字段会变，实际12月NPZ与EVENTS/DAILY字节完全相同。

Binance观测+条件Bybit费用/过滤器/MMR/到达时间仍是跨场所代理；funding使用原RAW_AS_FRACTION，单位/历史到达/真实venue清算仍未认证。全部已见开发集，不称真实实盘、严格OOS或可靠实盘APR。封存2026-03-01至2026-09-01正文未访问；锁文件本实例不存在，未解析。API403未重试/换API域；未碰dot SMA或60分钟终端窗口、旧源代码、main或环境设置。
