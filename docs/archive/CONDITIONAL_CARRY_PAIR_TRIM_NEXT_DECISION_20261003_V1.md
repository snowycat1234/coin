# 下一项科研判断：固定新时间的 carry 机制验证

依据：CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json，SHA256 71a910d1da8ae9a5ca68411693f14b6f82b43ed992ac33ee50a6dcf321a6b651。只读现存报告／文档及官方网页；未读行情或运行新数学。主体已完成，独立审计仍待完成。

当前盈利候选 NONE、长期净APR NE。条件式122日10k资本净+24.74485（+0.2474485%），funding39.51210、成本14.39006；730/732事件计入、仅1次ETH减仓。机械年化0.74214%不是长期APR。分钟／事件MDD0.38757%，daily MDD0.07657%，不能只用daily弱化风险。原全平亏11.01135主要来自第11.65天截断持有。

| 方向 | 信息价值与当前选择 |
| --- | --- |
| 官方单位证据 | 会改变整个利润解释，但旧REST451／Bybit403不能重试绕过。官方FAQ／API支持一般支付公式及rate字段；本次读取官方归档README无funding字段说明，仍未得到last_funding_rate→API的直接producer映射。保留UNCONFIRMED，不把文档升级成归档或Bybit认证。 |
| 新时间carry | **首选**。区分“低换手收入可摊薄成本”与“仅该窗口的funding／basis环境有效”，直接检验目前唯一完整的小额正净值机制。 |
| Bybit USD-M下旧flow／公开策略映射 | 潜在上限更高，但同窗impact不是可交易future-flow预测；降低费用不能补信号、perp收益／资金费／保证金映射。待有匹配perp账本及过去可得信号毛优势后再开，不把5.5bp嫁接Spot。 |

下一实验只冻结2025-12-01..<2026-03-01的90日（locked前），当前pair-trim及原ALL_FLAT固定控制，同10k／1250初始单腿与reserve／625margin／.3和.6 caps／Spot10+Perp5.5bp／原8bp单边fill成本；无重新筛月、增仓、杠杆、重入或HPO。Spot来源已有凭证；仅补严格授权的新期mark／funding等必需缺档，复用官方CHECKSUM薄包装，缺源则停止，不造carry结果。该时段已被其他策略消费，诚实称开发期时间外推，不能称真正unseen。报告全期净值、全部月份、funding／basis残差／成本、持有事件与分钟／事件DD。

暂不采用pair-trim盈利，先验收；原ALL_FLAT保留控制。若新期同成本／caps下净负或大部分收入由单月支撑，暂停当前固定carry配方扩展；reopen须新独立信息证明收入／风险／成本余量，或合规可达对应venue输入。Bybit原生投资映射仍暂停，reopen需对应资金费与可成交价／filters／保证金。旧oracle只能叫SAME_WINDOW_IMPACT_DIAGNOSTIC；重开交易研究需past-only信号与匹配经济证据。40GB／5GB／swap0／GPU0、无密钥／真钱／locked不变，不覆盖旧失败或单位状态。

官方参考：[资金费公式](https://www.binance.com/en/support/faq/detail/360033525031)、[USD-M历史rate字段](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)、[归档README／CHECKSUM](https://github.com/binance/binance-public-data)。这些网页不等于本项目归档样本parity或原生Bybit现金认证。