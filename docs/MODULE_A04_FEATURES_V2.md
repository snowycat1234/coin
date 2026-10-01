# A04：固定40项小时级因果特征

## 当前范围

独立 `features_v2.py`，不改旧 research/candidate/backtest、模型或历史结果。
本模块只定义和计算特征，无标签、预测、下单、收益评估、数据下载或学习式归一化。
实际资源保持 D盘40GB、共享RAM5GB、swap=0、不用GPU；测试通过bounded.sh。

## Schema 与定义绑定

`FEATURE_NAMES_V2` 为固定40项，前10项与 Logistic v1 的名字/定义兼容。
`feature_schema_v2()`返回 `version/missing_policy='reject'/features`，每项含
`name/dtype='float64'/definition`，供 FrozenPredictor manifest 直接绑定。
`feature_contract_v2()`另外返回 schema、全部滚动/时间政策的 definition 以及实际实现SHA。
这三者随状态一起封存；定义或实现改变不能恢复旧状态。状态摘要仅为本地内容完整性，
不宣称外部签名或真实前向审计资格。

|类别|固定特征|
|---|---|
|旧10项|log_return_1/4/16, volatility_24/96, volume_z96, range_fraction, body_fraction, ema_gap, taker_fraction|
|扩展收益/趋势|log_return_2/8/24, ema_gap_8_32, high_distance_24/96, low_distance_24/96|
|波动/区间|volatility_6, atr_fraction_14/48, close_location|
|量/主动成交|volume_z24, quote_volume_z24/96, taker_imbalance, taker_imbalance_mean_4/16|
|跨币6项|other_asset_return_1/4/16, relative_return_1/4, rolling_corr_24|
|标识与UTC时间|is_BTC/is_ETH, hour_sin/hour_cos, weekday_sin/weekday_cos|

收益为对数收益；rolling窗口含当前**完整可得**bar，std为ddof=1。
EMA adjust=False，从连续段首收盘价初始化；20/100旧定义至少100根，8/32至少32根。
body_fraction保持 `(close-open)/open`，不改写旧定义。high/low距离为当前close除以
窗口内high最大/low最小减1。ATR-like采用完整窗口简单均值TR除当前close，TR为
high-low及对前收盘价两种缺口的最大值；非Wilder平滑。close_location在零range时为0.5。
零volume的taker_fraction为0.5，imbalance为0；量Z分母加固定1e-12。
跨币相关使用24个同步小时对数收益；任一population std≤1e-12则为0，表示无信息。
无 global fit/scaler，所有标准化只按已知的 trailing 数据公式。

## 一套状态转移供历史与实时复用

`HourlyFeatureState.ingest(bar,asof_us=None)`接受完整BTC/ETH 1h OHLC、volume、quote_volume、
taker V/Q和 UTC微秒时间。显式asof不能早于逻辑available或实际received，拒绝未来、
错位/未完整小时、NaN、非法OHLC/VQ、乱序/回补和已观测资料改写。
重复相同原bar可以有新的received delivery，但不重算或修改状态。

每币独立EMA与最多100根trailing历史。缺小时重置该币全部窗口和EMA，重新100根热身。
只有同close_us的两币均已出现才生成跨币向量；不以另一币上一小时进行stale asof join。
若BTC已经走到下一小时，之前小时的snapshot仍固定，不把新的BTC价格混入旧配对。
最多等待4个未配对闭合小时，更旧未配对时间明确丢弃，不补成当时可得特征。

输出逻辑 `available_us=max(两币available_us)`，实际 `received_us=max(两币received_us)`，
另有 emitted_asof及两币各自的available/received，逻辑与实际时刻不混写。
logical availability源本来延迟时可max；实际packet迟到不提前造可用资料。
下游真实引擎仍须独立判断receipt延迟/交易合同，特征库不授健康或前向天数。

`build_features_v2(bars,include_warmup=False)`只把同一ingest按availability/receipt顺序调用，
默认仅返回两币均有100连续小时的完整finite向量；可显式返回warmup行用于诊断，
其feature_ready=false和缺字段不能进入 missing_policy=reject 的推理器。
首96/100窗口不补值；两币任一未热身则不产生完整模型输入。

`export_state()`与 `from_snapshot()`支持JSON无损恢复，包括单币先到的pending snapshot；
恢复不调用交易、补计健康时长或产生新观测。schema/definition/source和状态正文均核摘要。

## 合成验收

10项检查已通过（104.22秒）：固定40schema、旧10项对独立Polars公式100h后完全兼容、
批量/增量逐位一致和单币pending时JSON重启、另一币迟到且自己未来价已变化仍不泄漏、
单币缺小时不stale join并100小时重新热身、未来改动不能影响任何历史向量、
直接TR/Z/高低距/时间公式、常价零range零volume全部finite、重复/未来/改写拒绝、
状态内容和definition改写拒绝以及历史/pending状态上界。没有真实数据训练或alpha评估。

固定状态容量上界测试只证明特征状态不随运行无限增长；它**不替代**G45账本24h/180d
存储投影验收。G45紧凑checkpoint仍为WIP，按v3优先级后续单独处理。

准确写明相关系数低方差政策后，当前schema绑定与JSON恢复的2项集中复核通过（53.82秒），
Ruff通过。最终摘要与实现绑定见 `reports/A04_FEATURE_ACCEPTANCE.json`；此文件只认证
特征工程，不授予模型或前向资格。schema SHA为373cfb9c…，definition为b89e2896…，
实现SHA为797c5b15…。父任务可绑定固定schema用于预登记与FrozenPredictor。
