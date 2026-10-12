本模块冻结现有 Closing v2 账户为三臂统一期初合约。只豁免退出腿的最小名义额；开仓门槛、数量步长与真实容量、费用/执行成本、资金费、逐仓保证金、风险限制、原终端付款平仓均沿用。1e-8 是未认证数量代理，不能据此宣称历史或当前交易所原生可交易。

一个固定尝试，P1 `[2021-04-01,2022-07-01)` 456日及 P2 完整2023 365日，各 CS_MATCHED、VOL_MATCHED、STATIC50 三个独立共享10k账户，至多6新账户/0拟合/0下载。目标023ebb…及旧STATIC50 fe694d…/252d34…逐字节复用，50:50 不放大抵消后的风险。所有窗口是已见开发验证，不能称全新样本外、论文原样复现或跨窗口拼接收益。

只读去重：旧四单臂和两STATIC50账户从期初使用默认不豁免合约，D048八账户为不同303日BTCETH Turtle/HOLD；均不等价，不冒充本模块新控制。既有默认停止/残仓/亏损、排名与选择器负结果完整保留。c5f46a9 的锚定退出只证实一个真实付款平仓请求对规则敏感，不是新年度收益。

5个相关测试通过（4.35秒）：现有默认golden、小额付费平仓、开仓门槛、容量/步长/不翻仓、逐仓共享风险、版本混用拒绝，以及本适配器精确目标和原生调度器零推进恢复。28个源码/配置/目标SHA通过。源码及协议先发布再运行。每窗口三账户原始状态/日账/全部37分钟字段公开、逐臂新目录零推进冷恢复后，才执行下一窗口。

资源：旧15GiB磁盘保留、1线程、4GB AS、2GB sampledRSS停止、8GB主机、无swap/GPU及1200秒单进程守卫保持；单账户600秒、单窗口STATE1.1GB、公开有效载荷总计500MB在结果前冻结。只回收六个已公开恢复PASS的重建缓存，并用标准sparse-checkout排除五个旧公开分片目录的工作区重复文件；Git及远端对象、真实观测账户未删除。回收后可用18,291,564,544B。状态服务8765未运行；无实盘/账户访问。

实际结果与公开恢复证明将在有限窗口完成后追加。官方403/451不再请求；2024缺失mark、不开放2026锁、丢失2026账本不捏造；不修改另一收益分布研究。

最小运行命令（先在精确发布版本检出；STATE新目录，目标已在Git）：

```bash
COIN_CPD_STATE=/workspace/unified-exit-economics-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/unified-exit-economics-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/unified-closing-exempt-economics-20261012/driver.py --window P1 --state /workspace/unified-exit-economics-state/OBSERVED_P1 --prepared /workspace/cs-continuous-state/SOURCE_RECOVERED --source-commit "$(git rev-parse HEAD)"
```

完整冻结身份和预算见 PROTOCOL.json/SOURCE_SHA256.txt。归档 `archive.py pack --window P1 --arm CS_MATCHED --state <armSTATE> --destination <result/P1/CS_MATCHED>`；公开版本恢复 `archive.py restore --window P1 --arm CS_MATCHED --state <emptySTATE> --artifact-commit <packetSHA>`。P2沿用同命令替换窗口和缓存 `/workspace/cs-2023-state/SOURCE_OBSERVED`。

P1 实际运行631.341437秒（科学来源9c578028），三臂均完整456日/656640分钟、付款清仓、零残仓/债务/清算、独立Decimal NAV误差最大3e-35。CS净+2637.824583（vol9.835080%/DD7.975715%）全部窗口门槛通过；HOLD净+342.136528（vol10.858409%/风险门槛失败/现金CI跨零）；STATIC50净+1466.383920（vol6.865349%/风险门槛通过），现金14日区块CI[-.000044404541,.000691541682]跨零，STOP。STATIC50对CS少1171.440664、对HOLD多1124.247392USDT，联合风险不同的同合约描述性比较。旧默认42日停止记录未覆盖；不同合约从期初重跑不能解释成旧账户中途收益补救。

独立只读审阅发现归档未核CLI臂身份，发布前补齐BINDING/RESULT/INDEX窗口、臂、Closing版本和期初标记断言；新增错标签/错版本反例通过。最终相关6测试PASS3.88秒。仅归档验收增强，P1账户零重跑，科学来源及冻结金融参数不变。
