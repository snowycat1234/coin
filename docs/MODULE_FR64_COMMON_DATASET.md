# FR64 共同历史数据、标签和 splits

状态：`IMPLEMENTED_PENDING_ROOT_ACCEPTANCE`；不足 180 个共同完整日只返回
`SMOKE_ONLY`。依据 `OPEN_SOURCE_REUSE_OVERRIDE_v6_2026-10-01.md`，SHA
`bc650cda80b6f6478a3bd81f28d0971dfe8183a72e330a443e8b1c741290b86a`。
已验收 A10 与 execution/STOP_v2/live collector 字节保留。

复用成熟实现：Arrow Parquet row-group 解码、Polars 同步/向量标签、sklearn
`StandardScaler.partial_fit`、PyTorch `Dataset/DataLoader`。本模块只适配交易流合同，
不重写 loader、scaler、网络结构、训练框架、下载器或交易引擎。
参考 [Arrow](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html)、
[sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html)、
[PyTorch](https://docs.pytorch.org/docs/stable/data.html)。

## 来源与窗口

固定协议：`protocols/fast_research_v6.json`；实现
`src/quant/research_fast/dataset.py`、`labels.py`。历史仅
`2025-07-01<=t<2026-03-01`。先验证全部声明的日期再打开任何行情文件；显式
manifest 列表，不扫描 locked 目录。manifest 需 FR62 官方 ZIP checksum PASS、
输出 Parquet SHA 和转换收据相互绑定；日内 quality 0 不证明跨日原始成交 ID 连续。
共同来源为`trade_flow_5s_v2`，原V1来源/失败/现货凭证保留。
正式模式要求从 2025-07-01 起首 180 日四流各 17,280 桶；Spot跨日原始范围相邻，
Perp跨日聚合ID相邻、原始范围不重叠且增加，原始范围跳号显式审计而不假定原始总成交数。
manifest必须绑定原V1复用来源与V2adapter来源、无fixture、durable发布及owned raw删除；
少日/少流/坏 SHA/未知质量/断档不能取得正式资格。

输入固定四流顺序：Spot BTC、Spot ETH、Perp BTC、Perp ETH。使用唯一时间戳精确
inner join，同时核对完整 5 秒网格；不 asof、不插值、不补档。每 60 秒固定一个
decision，所有流当前 5 秒桶已闭合且 available_us≤decision 才能进入过去 256 桶。
Parquet 只解码时间范围相交的 row groups，endpoint index 为 native STATE 内
int64 timestamps 的只读 memory map。每个 `__getitem__` 读窗口与成熟标签所需区域，
不保存 `[N,256,F]`；纯 tabular 使用同 tensor 的 concat[last,mean,std]，204 项。

每流 17 项（四流总 68）在协议逐项冻结：backward return、flow imbalance、
VWAP/close offset、log high/low range、large-trade share、signed-price impact、
八个 log1p 活动/数量字段与 has_trade/has_return/has_interarrival 三个 mask。
count 在全部市场统一为真实观察的聚合成交行数，agg-count为同值兼容别名；不推断
永续原始总成交数。首轮保留事前同形状68输入，两个计数列同值，不因模型结果选特征。
size 使用聚合成交的 quote notional。
无成交及未建立前桶基线时的未定义数值在模型矩阵为 0，同时保留显式 mask；
原价格和标签不补零、不 forward fill。未知/NaN 源值不能转换为零或正常 mask。

## 八个标签和代理限制

只预测两币 Spot；Perp 提供共同输入。每币任务顺序固定为
`flow_5m, return_5m_proxy, flow_30s, logrv_5m`，`y` 为 `[2,4]`，八项共用同一
endpoint。Future flow 在 `[decision,decision+horizon)` 的 60/6 个桶累计 buy-sell
quote notional，再除累计 buy+sell+1e-12；原净 USDT 流量留 QA。
RV 为未来 60 个有效 backward return² 之和，标签为 `log(RV+1e-12)`。
缺 future bar、未知 return 或任一币无效标签会排除整个共同 endpoint。

历史 aggTrades 没有真实 quote。价格标签采用事前固定 **trade-price proxy**：
entry anchor=decision+5s、exit anchor=decision+305s，使用各 anchor 所在 5 秒桶
的第一笔 trade-open；每侧 first_trade_us 必须在 anchor 后 2 秒内。实际持有约
300±2 秒，真实 entry/exit trade timestamps 与价格始终保留 QA。
标签 `exit_trade_open/entry_trade_open-1` 为 gross reference-price return；
成熟时点为 decision+310s，不冒称 v4 decision+1s 的可成交 BBO 或 alpha。

共同经济代理单独扣成本，避免 spread 双计：roundtrip fee20bp、extra slippage8bp、
assumed spread2bp，总30bp；唯一预测 gross threshold35bp 包含5bp buffer。
spread sensitivity 固定4/8bp；Spot long/flat、约5m hold、每币 NAV30%、gross60%、
同币不重叠。不因结果降成本。本模块未实现模型或经济执行引擎。

## Folds、归一化、训练接口

首轮固定 6 个完整 rolling fold，索引 `[0,4,9,13,18,22]`，从首 180 日 23 个
候选 fold 中事前近似均匀选择，不按结果选择。每个 14d train 包含首12d fitting 与
末2d validation，7d test、7d stride。fitting cutoff=validation_start-5m embargo-
310s maturity；train/validation labels 须在下一 split 开始前5m已完全成熟；
test labels 须在 test_end 内成熟。少于6个完整 OOS 不能冒称正式研究。

每 fold 使用同一 sklearn 输入 scaler：仅独特 synchronized fitting rows，不把
重叠 windows 反复当作拟合行；mask 保持原样。validation/test 使用冻结状态，
scaler fit_last_us 必须早于其 decision。另用同一 sklearn target scaler 对八项
train labels 做标准化，只有在 fitting cutoff 前完全成熟的共同 train endpoints
可拟合；所有模型共享。训练矩阵使用完整 fitting 段统计；推理使用此前已冻结统计。
Target prediction 必须 inverse_transform 回原单位再算 metrics/经济代理。
sequence standardized MSE 每币任务权重 `[1,1,0.1,0.1]`，tabular 同 standardized y。
同一来源、sample IDs、labels、split、scalers、metrics/economics 用于全部10配置。

```python
specs = [ShardSpec.from_manifest(p) for p in explicit_manifest_paths]
ds = FastSequenceDataset(specs, mode="smoke")  # >=180d 满足正式门槛才用 formal
receipt = ds.prepare_index(STATE / "new-endpoints.i64")
fold = make_folds()[0]
feature_scaler = ds.fit_fold_scaler(fold)
target_scaler = ds.fit_target_scaler(fold)
view = ds.normalized(feature_scaler, fold, "train", targets=target_scaler)
indices = ds.split_indices(fold, "train")
loader = DataLoader(Subset(view.as_torch_dataset(), indices.tolist()),
                    batch_size=64, num_workers=0, shuffle=False)
```

Sample 返回 `sample_id, decision_us, x, y, y_raw, target_units, label_available_us,
qa, status`。`qa` 中未来价格/时点和 raw net-flow 只用于标签与经济评价，不能拼进 x。
`TargetNormalizer.inverse_transform` 支持 `[B,2,4]`；`tabular_view` 支持同一批 x。
保存 scaler 的 receipt 可绑定实际拟合时点、行数、mean/scale/variance 与 dataset SHA。

首轮固定10 directions/configs、seed20261001；Ridge alpha1，XGB depth3/100trees 和
depth5/200trees、lr.05/subsample.8/colsample.8/lambda10/hist/jobs2；TCN两组、
MLPLOB/TLOB各1、TS2Vec-linear/LGB各1、River1。无首次 fine-tune、额外树、PatchTST
或大搜索。具体 upstream/pinning 和共同 trainer/evaluator 由根侧独立登记。

## 验证与资源

专项测试最多8个关键 case，fixture、negative source 与 index/basetemp 均在 native
STATE；实际 XML、失败/Ruff 与修复复测分开保存。Python 在 D-host hpc_linux 经
`scripts/bounded.sh` 共用5GB RAM/swap0；CPU Torch smoke，不启 GPU，不拟合模型。
实际来源与输出收据由根侧独立验收，不把小数据 smoke 改名为 OOS。
