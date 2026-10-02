# Spot / USD-M 经济映射：审阅草稿（2026-10-02）

**APR候选与证据**：尚无长期净APR候选。已查看的7日开发段中，15m DIRECT仅3笔往返，净收益为+0.0335%（2bp点差假设）、+0.0155%（4bp）和−0.0205%（8bp）。共同样本还依赖未来有效性筛选，不能据此年化或声称可执行收益。

**阻碍、发现、下一步**：主要阻碍是可交易收益幅度、换手成本及独立永续价格/成交/保证金证据。7月资金费以正值为主，但规模远小于往返手续费；较低的费用假设不能代替永续实验。优先在已预登记的三个真正unseen folds比较固定成本/风险下的15m DIRECT及校准/残差，约20% frontier保留给独立永续/short target。以下只读分析未拟合模型、读取新标签或使用账户密钥。

## 1. 费用事实与情景分开

当前[官方现货普通用户费表](https://www.binance.com/en/fee/trading)可读，maker/taker均为单边10bp；不假设BNB、推荐、VIP或活动折扣。原现货协议保持往返20bp手续费＋8bp滑点＋2/4/8bp点差（总30/32/36bp），预测门槛35bp、单币新分配30%NAV、合计60%，不增加杠杆。

[当前USD-M费表](https://www.binance.com/en/fee/futureFee)抽取结果无记录；[官方费用FAQ](https://www.binance.com/en/support/faq/detail/360033544231)的单边maker 2bp/taker 5bp明确为示例。因此往返taker 10bp/maker 4bp仅作**官方示例情景**。本账户当前适用费率、2025—2026历史费率/活动/档次均未知。maker情景还缺排队、实际成交与逆向选择证据。

| 预测horizon | DIRECT粗平衡往返成本bp | OOF两阶段粗平衡bp | DIRECT往返数 |
|---|---:|---:|---:|
| 5m | 无成交、不可估计 | 无成交、不可估计 | 0 |
| 15m | 33.72 | 1.79 | 3 |
| 30m | 5.34 | 1.65 | 22 |
| 60m | 8.31 | 5.43 | 109 |

这里是原现货账本的 `2×同实际数量gross PnL / 双边reference notional×10000`，不是每笔交易保证边际。30/60m DIRECT与OOF粗边际均低于示例USD-M 10bp往返taker费**本身**；这提示cost/target需改进，但未评价永续/short价格收益，不能推出永续无机会。15m的三笔交易和压力点差负结果不足以产生长期资格。

## 2. 已核验的资金费事件及持有边界

复用登记的[官方数据来源及CHECKSUM约定](https://github.com/binance/binance-public-data/blob/f446ce3812bd4e5521f21faecd4ae3c6460e49fc/README.md)，[BTC 2025-07 funding包](https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2025-07.zip)及[ETH包](https://data.binance.vision/data/futures/um/monthly/fundingRate/ETHUSDT/ETHUSDT-fundingRate-2025-07.zip)再次按相邻`.CHECKSUM`核验。两币各93次、声明8小时；发布的`calc_time`偏离整点0—11毫秒，不能当成账户实际扣费时刻。

| 币种 | 正/负事件 | 每次费率范围bp | 均值bp/次 |
|---|---:|---:|---:|
| BTC | 93 / 0 | 0.1028～1.0000 | 0.7831 |
| ETH | 90 / 3 | −0.3011～1.0000 | 0.7560 |

[官方资金费规则](https://www.binance.com/en/support/faq/detail/360033525031)：正费率long付short；负费率short付long；以结算时mark notional计整次费用。只持有5分钟也可能支付完整一期，不按分钟摊费用。实际交易扣费存在15秒偏差，边界应保守处理；当前间隔可调整，7月8小时不能外推所有时期。

若**持仓固定为5/15/30/60分钟，入场相位均匀且独立于费率，采用7月8小时事件间隔**，跨一次结算的示例概率分别为1.0417% / 3.125% / 6.25% / 12.5%，不跨则为0。跨一次时BTC long现金流为−1～−0.1028bp、ETH long为−1～+0.3011bp，short符号相反，均以事件mark notional为分母。它们不是策略实测、权益收益或APR。**预测horizon不等于实际持仓时间**；真实账本必须逐次检查入/出场，长持仓可跨多次事件。

## 3. 永续评价缺口及reopen条件

USD-M需要独立现金流：`direction×quantity×(perp实际出场价−入场价)`，加每次`−direction×abs(quantity)×event mark×funding rate`，减实际两侧手续费/点差/滑点。Spot与perp basis变化会改变收益；mark/index蜡烛不是BBO或保证成交价。[官方清算说明](https://www.binance.com/en/support/faq/detail/360033525271)以mark计算未实现PNL/清算，维护保证金随敞口分档；足额抵押的short仍可能因价格上涨与资金费损耗触发约束。历史档位、清算费用和确切保证金边界当前未知。

**实际可用性**：两funding月包完整，但不含mark。BTC/ETH的7月1m mark/index月档四个确切CHECKSUM路径、7月1日日档四路径均404；这些是按目录约定推导的探针，不代表官方承诺提供、或整个归档不存在。公开USD-M REST原请求451，未绕过。官方网页正文由浏览工具读取，WSL直接网页请求202空响应，不能混称本地正文验证。当前没有真实历史BBO。

**暂停与reopen**：永续/short经济回放保留能力方向，待独立perp成交价格、事件mark/funding、预登记历史费用情景或可验证费表、因果点差/滑点及历史保证金/清算约束齐备后重开；风险上限沿用现货，不增加杠杆。maker路线需真实排队/成交/逆向选择证据及原门槛后重开。当前先完成unseen信号与经济验证，再决定该frontier是否优于继续现货校准。

**独立凭证**：`V7_VENUE_METADATA_AVAILABILITY_20261002_V1.json`；`V7_SPOT_USDM_ECONOMIC_MAPPING_20261002_V1.json`。此分支累计网络响应11,088字节，原ZIP及失败响应保存在D盘WSL STATE，原研究/采集证据未覆盖。
