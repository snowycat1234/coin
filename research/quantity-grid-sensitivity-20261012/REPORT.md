本轮只改变数量粒度：既有Closing退出名义额豁免、固定目标023ebb及已存STATIC50、费用、实际资金费输入、MMR、逐仓1x、共享10k资本、caps、容量、延迟、重试与终端付款规则都保持。金融方法完全继承原实现；新类只固定逐币InstrumentProfile和快照身份。不是历史原生过滤器认证。

限定去重没有发现完全同样的粗粒度六钱包。旧fca3aafd六钱包仍为1e-8，作为对应精确基准REUSED，不重跑；D048、Turtle EXACT_QUANTITY和合成profile测试不等价。没有恢复官方CORE5历史永续表，旧BTC/ETH API403不重试，现货两币规格不能代替永续。

数量假设采用一个固定推导规则，零收益输入。Bybit公开规则BTC最小数量示例.001，仅为条件单位锚；只读已有价格cube e33cc15b，取严格早于P1的2021-03-31 00:00UTC已可得价格。锚名义额.001×58794.16=58.79416USDT，各币选不超过该锚名义额的最大十进制数量步长，固定两窗口，minQty=step。没有引入文档100USDT名义额或其他规格，开仓最小名义额仍10。

| 币 | 条件step=minQty | 实验前参考价格 | 每手参考USDT |
|---|---:|---:|---:|
| BTC | .001 | 58794.16 | 58.79416 |
| ETH | .01 | 1843.43 | 18.4343 |
| SOL | 1 | 19.0933 | 19.0933 |
| XRP | 100 | .5629 | 56.29 |
| DOGE | 1000 | .054096 | 54.096 |

XRP/DOGE大整数是该可解释压力假设，不能叫交易所真实当前或历史单位。源规则、价源SHA、冻结时钟和完整Decimal推导在QUANTITY_PROFILE.json及evidence/PROFILE_DERIVATION.py/ OFFICIAL_NOTE.json。原InstrumentProfile没有独立minQty；本实验明确令minQty=step，使任何正整数手成交满足最小数量，绝不证明其他minQty组合。

预先冻结一个尝试、至多6新钱包/0ML或归一化拟合、0目标生成、0市场下载，同P1 `[2021-04-01,2022-07-01)` 456日和P2完整2023 365日，每段CS/HOLD/STATIC50三个期初相同规格的独立共享钱包。只验证粒度的拒单、真实量化持仓、残仓、付费退出、风险与净收益变化，不挑收益粒度；部分窗口不能与完整基准作收益差。原现金CI/风险门槛保留作为描述，价格变化后实际风险不重新配平。

冻结前8相关测试PASS4.29秒：默认golden、原费用/容量/风险、源目标身份、版本拒绝、规范发布路径与规格SHA、小于一手容量拒绝且保留库存、部分付款减仓、仍允许低于10的付费退出且新开仓不豁免。首轮新增测试因错读快照fees字段KeyError失败（6通过/1失败），原源码/日志/guard留在evidence；只修测试夹具，0历史钱包/金融代码重跑。50源/规格/对应旧基准SHA通过，复现shell语法通过。

同原guard：1CPU/线程，AS4GB、采样RSS停止2GB、主机8GB、swap/GPU0、15GiB磁盘保留、1200秒进程；每钱包600秒、每窗口STATE1.1GB、公开有效载荷总500MB固定。只清公开验证过的两selector恢复缓存及与FINAL逐字节相同的旧COMPLETE/JOINED来源副本、与SOURCE_RECOVERED相同的旧P1月份副本及相同Y2021 ZIP；FINAL、原观测钱包和所有Git/远端字节保留。标准sparse-checkout仅减少本工作区已公开旧byteparts占用；未改其他研究工作区。新分支独立，每窗口三账户完整保存/公开零推进恢复后再执行下一窗口。

恢复一臂的最小命令（最终公开版本检出后，空STATE）：

```bash
bash research/quantity-grid-sensitivity-20261012/reproduce.sh P1 STATIC50 /workspace/new-grid-recovery "$(git rev-parse HEAD)"
```

2024缺mark/403451、2026保留锁与丢失账本状态不变。无实盘、部署、凭证/钥匙、付费、Library或收益分布研究修改。实际启动和结果将在固定运行后追加；不能以合成测试代替历史结果。
