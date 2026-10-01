# FR61 开源复用登记表

登记依据：用户已采纳 `OPEN_SOURCE_REUSE_OVERRIDE_v6_2026-10-01.md`，SHA256 `bc650cda80b6f6478a3bd81f28d0971dfe8183a72e330a443e8b1c741290b86a`。核验于 2026-10-01 UTC；GitHub 默认分支实际 HEAD 查询时间 11:32:05，许可证/PyPI 查询时间 11:36:31。完整来源、响应摘要与文件摘要见 `reports/fast_research/FR61_OPEN_SOURCE_REGISTRY_ACCEPTANCE.json`。

本模块只登记来源和接口。没有安装依赖、vendor 代码、训练或改变已冻结工程；下列“PINNED”是后续集成的固定来源，不等于已经安装或通过模型 smoke。

## 1. 状态定义

- **PLANNED**：用途已选择，尚未确定可用上游/版本；不能计作已集成。
- **PINNED**：已核真实 commit 或发行版、许可证和用途；实现/安装另行验收。
- **ADOPTED**：已经实际集成且有独立安装、适配修改与 smoke 凭证。本次没有此状态的模型。
- **REFERENCE**：仅引用论文/实验设计；不复制、vendor 或运行其框架。

## 2. 固定来源与使用范围

| 名称 | 实際固定 commit / 包发行版 | 许可证据 | 状态与用途 | 当前本地修改 |
|---|---|---|---|---|
| [Binance public data](https://github.com/binance/binance-public-data) | `f446ce3812bd4e5521f21faecd4ae3c6460e49fc` | [README 软件声明 MIT](https://github.com/binance/binance-public-data/blob/f446ce3812bd4e5521f21faecd4ae3c6460e49fc/README.md)；没有独立 LICENSE，数据受另列条款 | PINNED：FR62 URL、CHECKSUM 与目录约定，个人非生产历史研究 | 无；未复制 helper 代码 |
| [pytorch-tcn](https://github.com/paul-krug/pytorch-tcn) | repo `3b3deac30c9f6a74b5cffbf614378a928268f9bd`；[包 `pytorch-tcn==1.2.3`](https://pypi.org/project/pytorch-tcn/1.2.3/) | [MIT，Paul Krug](https://github.com/paul-krug/pytorch-tcn/blob/3b3deac30c9f6a74b5cffbf614378a928268f9bd/LICENSE) | PINNED：FR66 依赖和薄 encoder 包装 | 无；未安装 |
| [TLOB](https://github.com/LeonardoBerti00/TLOB) | `f1c0af4d81067978914361766db0457a7d8b6a46` | [MIT，Leonardo Berti](https://github.com/LeonardoBerti00/TLOB/blob/f1c0af4d81067978914361766db0457a7d8b6a46/LICENSE) | PINNED：FR67 仅 MLPLOB/TLOB 核心、换最终 head | 无；未 vendor |
| [TS2Vec](https://github.com/zhihanyue/ts2vec) | `b0088e14a99706c05451316dc6db8d3da9351163` | [MIT，Zhihan Yue](https://github.com/zhihanyue/ts2vec/blob/b0088e14a99706c05451316dc6db8d3da9351163/LICENSE) | PINNED：FR68 最小核心、历史 development-train 预训练 | 无；未 vendor |
| [River](https://github.com/online-ml/river) | repo `8fc69a836badf855ccda9e6db157eb9e3819ebdd`；[包 `river==0.26.1`](https://pypi.org/project/river/0.26.1/) | [BSD-3-Clause，River developers](https://github.com/online-ml/river/blob/8fc69a836badf855ccda9e6db157eb9e3819ebdd/LICENSE) | PINNED：FR69 官方 scaler、线性回归、ADWIN | 无；未安装 |
| [tsai](https://github.com/timeseriesAI/tsai) | `bbb61982741d466bfa81669edc0e17f1971980af`；观察到发行版 [1.0.1](https://pypi.org/project/tsai/1.0.1/) | [Apache-2.0](https://github.com/timeseriesAI/tsai/blob/bbb61982741d466bfa81669edc0e17f1971980af/LICENSE) | REFERENCE：必要时一个 PatchTST，当前不安装 | 无 |
| [LOBFrame](https://github.com/FinancialComputingUCL/LOBFrame) | `c47549dc967a884354152bf2484331e11be03023` | [README 声明 CC BY-NC-ND 4.0](https://github.com/FinancialComputingUCL/LOBFrame/blob/c47549dc967a884354152bf2484331e11be03023/README.md) | REFERENCE：预测评价与交易评价分开 | 无；不复制代码 |
| [LOBench](https://github.com/Financial-Simulation-Lab/LOBench) | `c8fe9e701405d553b278cba063012107bd8ec718` | [README MIT badge](https://github.com/Financial-Simulation-Lab/LOBench/blob/c8fe9e701405d553b278cba063012107bd8ec718/README.md)，但 LICENSE 404、API license=null；**未确认可 vendor** | REFERENCE：未来真实 L1/L5 representation 任务设计 | 无；禁止在确认前 vendor |
| Hawkes | 尚未选择上游，commit/version=null | 未确认 | PLANNED / SKIP_HAWKES：optional，不阻塞主线 | 无；不自写优化器 |

所有列出的 repo 实时 API 均为 fork=false。包发行版与 repo 当前 HEAD 分开记录；不声称发行包字节等于当前 HEAD。安装时使用所选包发行版的实际 wheel/sdist 摘要生成集成凭证，升级不得覆盖本次登记证据。

TS2Vec 论文链接的旧地址 [yuezhihan/ts2vec](https://github.com/yuezhihan/ts2vec) 现在重定向到 zhihanyue/ts2vec；[当前 README](https://github.com/zhihanyue/ts2vec) 明确是论文官方实现。[论文](https://arxiv.org/abs/2106.10466) 的旧地址与当前 repo 为同一上游，用户指定地址有效。

## 3. Binance 数据与软件许可分别记录

当前固定 commit 的 [数据条款](https://github.com/binance/binance-public-data/blob/f446ce3812bd4e5521f21faecd4ae3c6460e49fc/TERMS_AND_CONDITIONS.md) 为 v1.0，2026-08-26 更新，SHA256 `dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1`。

条款第 2.4、3、4 节将数据及派生模型/指标纳入 CC BY-NC-SA 4.0，允许个人非生产历史研究；商业利用需另行书面 enterprise license，并限制 live proprietary execution 等用途。当前科研可继续。README 的软件 MIT 声明不能代替数据许可或未来生产授权。数据 manifest 应记录条款 URL、SHA、下载日期与研究用途；真实数据/模型不入 Git。

官方 [README 归档约定](https://github.com/binance/binance-public-data/blob/f446ce3812bd4e5521f21faecd4ae3c6460e49fc/README.md) 提供以下 URL：

```text
https://data.binance.vision/data/spot/{daily|monthly}/aggTrades/{symbol}/{symbol}-aggTrades-{YYYY-MM-DD|YYYY-MM}.zip
https://data.binance.vision/data/futures/um/{daily|monthly}/aggTrades/{symbol}/{symbol}-aggTrades-{YYYY-MM-DD|YYYY-MM}.zip
```

对应 ZIP 同目录追加 `.CHECKSUM`。核对实际 SHA256 和 CHECKSUM 中的精确 ZIP basename 后才解压。官方归档可能事后更新，应保存下载时摘要，不能只保存 URL。

本次只读取得 2025-07-01 的四个 .CHECKSUM 元数据，不下载 ZIP 或行情内容。其 ZIP 指定 SHA256：

| 市场 / 标的 | ZIP 的官方指定 SHA256 |
|---|---|
| Spot BTCUSDT | `69308ceec2c05dd17739f378327dfe13bd536546e5772d10e1b283b060766501` |
| Spot ETHUSDT | `0a5118e25eca84649dc8f682ea584726ce9d0c6f2e2b51d25d8f69fccca87e24` |
| USD-M BTCUSDT | `72146acd2aa13a1da52c398f560e73f765b7a9d4659bfbae1219801f4b86265f` |
| USD-M ETHUSDT | `e6518af7b58c39545bc998fc884c5ad8869cc35ba7f31b0363a93013b24ef92e` |

Spot 从 2025-01-01 起归档时间戳为微秒；USD-M aggTrades 官方示例为毫秒。转换必须按市场、归档日期和合同明确单位，统一成整数微秒并校验日边界，不能把两路时间戳混用。历史 aggTrades 为成交时间，不是本项目 live 收到时间。Spot 有额外 best-price-match 列，USD-M 没有该列；CSV 是否带 header 应校验实际 archive。首条真实数据转换另由 FR62 验收。

研究范围保持 `2025-01-01 <= t < 2026-03-01`，FR63 优先 `2025-07-01..2026-02-28`、至少 180 完整日。2026-03 起锁定历史不消费。

## 4. 四条模型接口的最小适配

### pytorch-tcn

[官方接口](https://github.com/paul-krug/pytorch-tcn) 为 `from pytorch_tcn import TCN`。PyPI 1.2.3 声明运行依赖仅 torch、numpy；本次已观察 NumPy 2.5.3，Torch 尚未在旧环境安装。采用 `input_shape="NLC"` 对接统一 `[B,T,F]`，输出末时刻/pooling 再接共同 head，固定 `causal=True`、`lookahead=0`、`use_skip_connections=True`。不重写 TemporalBlock 或 causal convolution。

TCN-S/M 配置由 v6 固定；padding/mask 只由共同 dataset 和 adapter 处理，TCN 没有自动等同项目 mask 的合同。实际兼容性、形状、因果输入、deterministic eval、无未来归一化仍须四项 smoke。

### TLOB / MLPLOB

[模型核心](https://github.com/LeonardoBerti00/TLOB/blob/f1c0af4d81067978914361766db0457a7d8b6a46/models/tlob.py) 接收 `[B,T,F]`，当前最终输出 3 类。[MLPLOB](https://github.com/LeonardoBerti00/TLOB/blob/f1c0af4d81067978914361766db0457a7d8b6a46/models/mlplob.py) 使用同一接口。最小核心为 `models/tlob.py`、`models/mlplob.py`、`models/bin.py`，以及 DEVICE 兼容层；外部依赖 torch、numpy、einops。原 tlob 顶层还导入 matplotlib/seaborn，实际最小适配可将未使用绘图依赖延迟/移除并如实记修改。避免导入整个 upstream trainer 和 CUDA/Hydra/Lightning/W&B requirements。

构造器固定 seq_size、num_features、hidden_dim、num_layers；TLOB 另需 num_heads/is_sin_emb。dataset_type 使用非 LOBSTER 路径，避免把我们的 feature 41 当订单类型。仅换最终 head，保留 backbone/attention/BiN 结构，研究名称注明 trade-flow transfer，不能声称论文原 LOB 设置。

[BiN 源码](https://github.com/LeonardoBerti00/TLOB/blob/f1c0af4d81067978914361766db0457a7d8b6a46/models/bin.py) 有实际兼容/正确性风险：负 y 分支使用 CUDA FloatTensor 并重新绑定 Parameter，CPU 会失败且 optimizer 可能失去当前参数；feature-axis std 为零时除零。后续必要修缮须保留参数身份、绑定显式 CPU/input device、处理零 std，并在 UPSTREAM.md 逐项记录。这里只登记计划，**尚未修改代码**。原 constants 导入 upstream preprocessing.dataset，不应因此带入整套数据处理依赖。

双向注意力和 BiN 对整个已观察历史输入窗口计算，因此仅用窗口末端 representation 预测未来；不宣称内部每个 timestamp 都是逐时刻因果。数据窗口不可含 endpoint 之后的观测。

### TS2Vec

[最小源码](https://github.com/zhihanyue/ts2vec/blob/b0088e14a99706c05451316dc6db8d3da9351163/ts2vec.py) 为 `ts2vec.py`、`models/__init__.py`、`models/encoder.py`、`models/dilated_conv.py`、`models/losses.py` 及必要 utils。已读这些文件，运行核心只需 torch、numpy 和 stdlib；不安装原 Python3.8/Torch1.8.1 全 requirements。vendor 时保留 MIT/LICENSE 和 copyright，记录固定 commit、每项 namespace/现代 Torch 兼容修改；本次没有 vendor。

`TS2Vec(input_dims=F, device="cpu", output_dims=D)`；fit 仅 development train 数据，encode 接收 `[N,T,F]`。默认 encode 是非因果；`causal=True` 只有 sliding 分支才改变右侧窗口，逐时刻表示必须 `sliding_length=1`，或仅对完全历史截断窗口取 endpoint。sliding_length>1 会包含同块较晚观测，不能作为每个时刻的无未来保证。不要为了快速 encode 先 materialize 全历史三维窗口数组。

### River

[官方 River](https://github.com/online-ml/river) 使用依赖 `river==0.26.1`，Python>=3.11，默认依赖 NumPy>=2.2.5,<3、SciPy>=1.14.1,<2、narwhals>=2；pandas 为 optional extra。本次旧环境 Python3.12、NumPy2.5.3/SciPy1.18.1 满足已声明约束，River 尚未安装。main 当前 HEAD 不等于包版本；不采用新 main 特有选项作为0.26.1保证。

最小 API 为 `preprocessing.StandardScaler.transform_one/learn_one`、`linear_model.LinearRegression.predict_one/learn_one`、`drift.ADWIN.update/drift_detected`。历史 replay 先预测、保存预测时刻输入/特征与已成熟标签队列，再在标签成熟后 learn；ADWIN 接收已成熟误差。不要自己实现 scaler、ADWIN 或增量优化器。

## 5. 本次验收与后续记录

实际核验：8 个官方 repo 的 40 位 SHA、5 份独立 LICENSE、2 个 README 许可证声明、LOBench 许可缺口、3 个 PyPI 发行版本及 source archive SHA、四个官方 CHECKSUM 元数据、四条模型最小接口。未新增框架或 unit tests。

11:36:11 的旧 `.venv` 包元数据快照：pytorch-tcn/River/tsai/Torch/pandas 未安装；本快照不描述主代理之后新 `.venv-research` 的安装状态。没有 `third_party` 目录。已使用的底层依赖沿用原 pyproject/uv.lock 与旧凭证；本次不改它们。

后续每次实际安装/vendor 按 FR66/67/68/69 独立更新集成凭证，将该项目从 PINNED 升为 ADOPTED，并登记许可证、upstream SHA、实际本地文件 SHA、所有修改和四项 smoke。FR61 不提供模型训练效果、容量、alpha 或未来实盘授权；RAM≤5GB、项目加整个 D 盘 VHD≤40GB、无 GPU 约束继续执行。

