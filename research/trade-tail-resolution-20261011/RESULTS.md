结论：**SOURCE_SAMPLING_UNDERCOVERAGE_QUANTIFIED，0新预测拟合**。在698个已见历史共同日期，end5minuteclose尾部采样系统性小于同日官方1minuteOHLC极值。此结果量化标签覆盖限制，不能建立alpha、预测增量、净收益、清算防护或可成交极值。所有旧模型STOP保持。

远端冻结d19859e67f40e3ccc4e856a9ecd90f5e162bd169先于一次真实来源诊断；源码/source306b58c4/协议/SHA均绑定。699来源日2021Jan1–2022Nov30，首日真实前边界未知保留NaN，余698共同日＝2021的364日＋2022的334日。两种测量都使用真实前UTC日收盘锚点，up/down包含起点zero。OHLC测量逐元素完全等于原全分钟source primitives。原分钟CRC/checksum/完整格点/边界证据复用五个已公开phase冷核验，不宣称本次重新扫描5032800分钟。

以下是每币698日的遗漏中位数与实际OHLC尾部的相对遗漏中位数。相对量仅在实际OHLC尾部>0时定义；真实zero保留NaN，不补零。单位**log-pricebp＝10000×logpricechange，不是PnL/costbp**。

|资产|上尾遗漏中位bp|下尾遗漏中位bp|上尾相对遗漏中位|下尾相对遗漏中位|
|---|---:|---:|---:|---:|
|BTC|20.42|26.02|10.95%|11.91%|
|ETH|21.79|31.65|8.51%|11.24%|
|SOL|27.15|34.57|7.05%|9.46%|
|XRP|24.03|37.22|8.88%|11.92%|
|DOGE|29.36|37.56|9.38%|11.91%|

冻结的共同日期统计每天取五币最大遗漏，不是池化3490个独立样本：上／下侧的median59.66／66.28bp，p90为155.31／210.19bp。遗漏>10bp的日数692／695，>50bp的日数425／464。阈值仅是预先固定的来源描述分箱，没有收益门限或事后调参。完整年度/每币/侧别、相对量有效数量、真实zero及sampledzero但OHLCpositive数量在result/SUMMARY.json，全部699行向量/共同mask/时钟在SOURCE_RESOLUTION.npz。

实际来源算术0.271342秒，guard1.509995秒，最大采样RSS101396480B，1CPU/4GBAS、GPU0/swap0、15GiB保留。一次原始来源诊断，0fit/收益标签/预测评分/targets/钱包/下载/CSVrescan/原STATE访问。五个有意义合成反例通过；最初一个仅因四天fixture未跨年度失败，调整日期后通过，失败及guard均保留，真实源之前0拟合或诊断。

信息缺口已具体化：旧5mclose尾部不能代替分钟OHLC尾部，更不能代替markprice尾部或legacyentry逐仓剩余空间。若今后设计风险标签，必须先明确所预测的价格域、采样极值和可用时钟，并冻结新独立机制；这些事实不允许复活旧HAR/quantile/JOIN/flow模型。本模块没有minute内峰值顺序、BBO、成交/费用/资金费或账户证据。连续fullmark2021Dec–2022Sep及funding/arrival/venue/MMR证书仍缺，native经济结果NOT_RUN。不可把这些已见历史称全新样本外。

完整结果公开后再做零拟合公共冷恢复；原来源SHA、原代码SHA、guard与字节hash均随结果保存。
