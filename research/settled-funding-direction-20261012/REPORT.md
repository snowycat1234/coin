已完成固定融资方向实验；STOP_FIXED_PERP_FINANCING_DIRECTION_SCREEN。2023相对恒定SHORT改善但自身亏损，2025无增量且风险失败。没有分钟原生钱包、参数调整或费用放松。

| 已见开发历史 | SHORT净值变化USDT | 资金费方向净值变化 | 增量 | 日均增量95%区间 |
|---|---:|---:|---:|---|
| 完整2023 | −2209.870784 | −386.025346 | +1823.845438 | [.00012190218,.00116177571] |
| 完整2025 | −3.027713 | −170.811789 | −167.784076 | [−.00025143677,.00020358006] |

每个独立参考初始10k，这是实际历史价格与资金费的日频数量全填代理，每侧BASE27成本.00135及收费终端；不是原生可执行净收益。方向2023价格损益−518.298783、成本109.038959、资金费现金+241.312396；2025分别−145.514060、112.672614、+87.374885。正资金费不能抵消全部价格和交易损失。

规则：原始已结算rate按完整UTC日求和，仅用[decision−22日,decision−1日)21日均值的反向符号；日结束后再延迟完整一天。未知或零输入为该资产CASH，原始.12分配不重分槽位，之后沿用原risk.scale共同缩放。没有价格trend/rank/selector、账户paid coupon输入、拟合或oracle收益。固定BTC/ETH/SOL/XRP/DOGE顺序和过去30日协方差/10%风险预算/30%单币/60%gross。去重未识别等价实跑；旧carry现金占位NOT_EVALUABLE、两腿carry和永久退出不同。这是有界去重，不是全历史不存在证明。

同一风险政策不是匹配实际风险。方向2023/2025实际年化日频vol11.904977%/10.551821%，DD10.638905%/12.854226%，worst30−7.158266%/−8.806227%；SHORT分别12.035108%/10.658360%、23.093327%/12.127734%。方向cap限制44/18日、平均预测风险9.827806%/9.967084%，SHORT10%。2023绝对净收益失败；2025净收益、增量、CI下界和12%回撤失败。两年必跑，未根据首年赢家截断。仅停止这一规则，不推广为全部融资或SHORT机制失败。

来源与首次评分前修正：2023 MPS commit53056adaa3b54f93ef6859269106ac288331dd9c/input SHA e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4；2022Dec热身/e0原事件与f38617c5全年5475实际事件时间/rate/hours一致。旧MPS Feb24五个UNKNOWN持有资产区间，仅从已公开官方日档补缺后的Feb NPZ SHA653e967a983b7536cf1a2660e00c13e0f538beac1077d5dd1d36fa70cb76e861恢复实际strictly-past mark；容差独立验证后保留原1820有限系数位完全不变，只填5缺失。旧输入和准备检查点保留。

2025消费者be48f551/事件534a18fb；2024Dec五个93事件原ZIP及CHECKSUM从d69e9ac9分片恢复，41,525,346B wrapper SHA10de51c5daed8bcc63e9d2cecbd17146ca2e7c0ab488dea221eab44b920a9bbc，0下载。旧消费者仅364区间，末区间用真实年末事件和已准许Jan1来源。全区间实际00:01分钟OPEN、decision+60s+1us全填报价，Jan1终端为INPUTS OPEN[1]；收费mark available严格早于原事件且最多过去60s。每个mark/时钟及原2025前364系数parity记录在最终packet PREPARATION。

一科学配方、4次来源准备、4次真正日频参考共.094978s，0fit/原生钱包/旧金融回放/provider GET。来源工程修正均在0评分时：逻辑ZIP需分片、OPEN/strictpast/旧源缺口、原系数位保留；失败日志/旧准备文件保留。最终准备计时见ADMITTED_PREPARATION_SUMMARY，随机数只用于14日圆形块bootstrap1000次/种子811742_811743，无训练种子或参数搜索。两个publication JS SyntaxError发生在0工具执行时，没有额外来源/金融运行。

5相关测试PASS2.84s。真实两年各365×5有效持有源、输入UNKNOWN0、CASH0；目标变化109/168日、long资产日133/214。源SHA/实际事件/旧资金费系数/成熟时钟/未来rate与NaN及price与NaN前缀验证通过。必要只读审阅的wrapper/OPEN/strictpast/位保留意见均在评分前落实，21原真实金融快照SHA不变。

两个最终packet INPUTS_FINAL/SCORES共610491B公开于5fc36717dbb3357a7989c4f93a123b1a089079b8；adc6前置输入389331B保留，全部999822B。新public cold .087427s PASS：10字节/SHA/CRC成员、1460保存日记录、独立Decimal现金/价格/fund/cost最大误差3.395069039399e−12USDT；0参考计算/fit/网络/原STATE打开。这是数学代理保存结果可恢复，不替代原生执行/历史合约资格证明。

从干净研究分支最小恢复：

```bash
bash research/settled-funding-direction-20261012/reproduce.sh restore /workspace/funding-public-new
```

同一公开输入重算（新目录，明确产生4次新参考计算）：

```bash
bash research/settled-funding-direction-20261012/reproduce.sh score /workspace/funding-score-new
```

这是适配融资机制，不是Slow Momentum原样复现，也不是新样本外/PIT/未来盈利证明。原生费用/minQty/capacity/MMR和历史发布字节未认证；不从账户、锁集或丢失2026账本补缺。守卫仍1CPU/4GB地址空间/2GB采样RSS/8GBhost/swap0/GPU0/15GiB预留，云保守重建不等于旧共享cgroup认证。资源实际峰值/时刻见COMPLETION。dashboard未运行不阻塞独立历史；锁缺失不授权、Mar–Sep保留体未开、丢失Q1/Q2账本未声称恢复。另分布研究/Library/密钥/付费/实盘/部署/main/强推均未触及；项目ACTIVE。
