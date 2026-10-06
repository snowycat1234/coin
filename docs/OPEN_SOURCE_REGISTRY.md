# FR61 开源复用登记表

### D054实际复用

固定November官方URL/CHECKSUM增量和原已接受两层暖源桥已完成；只新增24分钟价格/mark/资金费档，6旧档与90暖源元数据复用。既有Polars/NumPy、官方`binance/binance-public-data`与原许可证/commit不变；无依赖安装/自行Transformer/下载框架。normal calendar/QA路径薄适配及共享pool比较修正不复制第三方代码。三固定HOLD配置真实同资金账户，第三方原SMA/许可不变且本轮未重跑SMA。结果为跨场所条件开发证据，不能由开源许可证推断服务数据/native资格。

## 2026-10-03 Bybit原生公开资金费小窗口（D026）

复用已锁定Python标准JSON／Decimal及项目来源凭证、progress／registry；不增加依赖。
HTTP传输复用既有Windows系统`System.Net.Http.HttpClient`，只取原始字节，WSL负责解析；
不复制SDK、建立下载框架或改变系统HTTPS配置。已有httpx0.28.1／BSD-3登记保持，不新增安装。
`bybit-exchange/pybit`仅查官方接口参考，**NOT_INSTALLED / NOT_ADOPTED**，不借其MIT标签
描述服务或Windows运行库。官方服务协议版本为V5，无源码commit／开源license；
接口及数据条款仍属服务方，不把公开API资料当MIT代码。

主文档：[funding/history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)、
[官方主机与访问范围](https://bybit-exchange.github.io/docs/v5/guide)、
[收费公式与符号](https://www.bybit.com/en/help-center/article/Funding-fee-calculation)。
本地修改仅新薄固定历史请求与格式校验；单位仅Bybit文档ratio惯例，真实覆盖／限制以本轮结果为准。

## 2026-10-02 具体公开策略比较增量

| repo | 固定commit／许可 | 用途与本地修改 |
|---|---|---|
| https://github.com/jesse-ai/example-strategies | `7c91e0a37bf62165790120d730442e4f6eb00364`／MIT | PINNED：Donchian官方49行策略原字节及LICENSE置于`third_party/jesse_example_donchian`；复用信号hook，预先固定1h、common风险／账本。与原全仓配置不同，名称为`COIN_JESSE_DONCHIAN_1H_SPOT_ADAPTER`，不称原回测复现。 |
| https://github.com/jesse-ai/jesse | `417f8765225e3bfc12043d4b712f19fe15a3c078`／MIT | PINNED：仅原Donchian指标及MIT原字节；复用其nonsequential NumPy分支。未安装Jesse／Rust框架，最小context port提供已观察candle及SMA200 NumPy reduction；所有改动与逐字节摘要见上述目录`UPSTREAM.md`。 |

本轮参数在收益运行前固定，不根据上游展示收益或本轮结果选择。

### 固定公开RSI2与官方Rust依赖登记（D021，结果前登记，D022已验收）

| repo／发行源 | 固定commit／version／许可 | 用途与本地修改 |
|---|---|---|
| https://github.com/jesse-ai/example-strategies | `7c91e0a37bf62165790120d730442e4f6eb00364`／MIT | RSI2原hook保持字节，long-only1h、2/5/200/10固定；原wholebalance/short不移植，common资金风险与费用。已完成六实际账户及独立审计，固定配方净负暂停，研究能力保留。 |
| https://github.com/jesse-ai/jesse | `417f8765225e3bfc12043d4b712f19fe15a3c078`／MIT | 复用原RSI wrapper与官方helpers截尾语义；默认nonsequential240bar是上下文配置，与SMA200参数不同。原文件不改，不安装完整框架。 |
| https://github.com/jesse-ai/jesse-rust / https://pypi.org/project/jesse-rust/1.3.0/ | `1.3.0`／MIT，配套上述requirements | ADOPTED_OFFICIAL_KERNEL：cp312 Linux wheel独立置D承载STATE，wheel SHA `65c0e9edd3af5397642ca417da2ef7c23f311d6fa2bf6a2d46c729f656528cee`；原wrapper/helpers/Rust源保留字节。不改旧env或手写RSI；Python3.12/NumPy2.5.3 ABI、scalar240/seed/flat实际验收通过，安装约2.54MB。 |

版本/许可在下载执行前登记于`third_party/jesse_example_rsi2/DOWNLOAD_PREBIND_20261002_V1.json`。
首次raw官方LICENSE握手超时退出1，未安装wheel或调用kernel；沿用同pin已有许可证后仅恢复失败项。
本轮登记前原表完整字节保存在`docs/archive/OPEN_SOURCE_REGISTRY_PRE_RSI2_20261002.md`。
第二次安装因假设`rsi.rs`路径而失败，官方sdist实际为`src/oscillators.rs`；复用既有wheel/sdist恢复，失败报告与helper原字节保留。
最终依赖与synthetic语义实际退出0，唯一新增集成1case及六新proxy账本独立审计完成。
COIN只增加薄指标／目标adapter与common策略ID／三行路由；MIT rawhooks/wrapper/helper/kernel零修改。
状态为**ADOPTED_RESEARCH_CAPABILITY_ONLY / PAUSED_FIXED_RSI2_RECIPE**，不是原Jesse全仓复刻或盈利资格。
见[实际经济比较](PUBLIC_RSI2_NATIVE_FEE_ECONOMICS_20261002.md)、`RSI2_OFFICIAL_KERNEL_ACTUAL_EXIT_20261002_V1.json`与新根验收。

共同策略72个实际账本与独立资金/风险复核已通过，状态为 **ADOPTED_PROXY_SCREENING_ONLY**。
根验收 `INVESTMENT_COMPARISON_ROOT_MODULE_ACCEPTANCE_20261002_V1.json`；
随后连续122日已完成，原30/32/36bp情景均净负；1h保留为防御研究参照，
不再作为盈利主力。下一仅预登记一个2h换手诊断。原Jesse字节无本地改动，COIN adapter显式移植；
不表示长期盈利、真实BBO可成交或可用真钱。

### 2026-10-02 固定2h挑战者（D013，结果前登记）

来源/commit/MIT许可证继续复用上列两个Jesse项目，原策略/指标/许可证字节不改。
本地变动只在COIN adapter增加闭合120分钟聚合和明确2H标识，默认1h合法值保持；
20根通道和SMA200保持，所以物理回看长度也翻倍。风险、费用、执行及资金仍共用原引擎。
不称Jesse原生回测复现，不使用上游展示收益；仅一个固定配置，0模型拟合。
第一版1h移植的`third_party/jesse_example_donchian/UPSTREAM.md`保留原冻结字节；
2h的新增源码/协议/实际结果另绑定。当前2h为PLANNED，未产生经济或候选资格。

本段保留结果前登记；实际122日3成本账户和3账本独立复核均exit0后，2h升级为
**ADOPTED_PROXY_RESEARCH_MAIN_ONLY**（D014）。30/32/36bp净+0.6580/+0.5958/+0.4692%，
分钟MDD高于1h且仅2/4正月；不是长期盈利或真钱候选。来源、MIT字节、本地修改范围不变。
具体证据见 `PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json` 与独立审计；
原1h阴性和旧全部账本保留，不用新版本覆盖它们。

90日固定外推已完成，原30/32/36bp净2h−1.8175/−1.8684/−1.9709%，且同数量gross为负；
按结果前D014缩小为 **RETAINED_DEFENSIVE_PROXY_REFERENCE_ONLY**（D015），盈利主力NONE。
根验收 `PUBLIC_STRATEGY_90D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json`；
独立15账本限定精确Parquet/逻辑绑定，原内存IPC指纹未重现，初次FAIL保留。
Jesse原策略、指标及MIT许可无新改动；用户新增Bybit费用基准不改写上述Binance代理结果。

### Bybit费用资产与固定hybrid增量（D017–D020）

第三方仍为上列两个固定Jesse commit/MIT，原上游文件与许可证零修改，无新增依赖。
新本地`public_donchian_hybrid.py`（SHA `80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68`）
只复用原hook/闭合K线及共同目标格式，固定2h入场/1h退出；7项旧信号验收凭证直接复用，
新增一个native费用联合用例通过，六新实际账户及独立数学/因果核验完成。122日恶化、90日改善，
暂停此固定配方，未采用为盈利主力。[规则](PUBLIC_DONCHIAN_HYBRID_FIXED_TARGET_20261002.md)与
[实际经济比较](PUBLIC_DONCHIAN_HYBRID_NATIVE_FEE_ECONOMICS_20261002.md)。common/core/fee/hybrid源无新改动。
Bybit费用资产adapter来自本项目冻结backtest与execution.py commissionAsset语句，
属于本地复用，无新增第三方模型框架；六个2h费用控制账本通过限定金融核验，原盈利结论不变。
本次增量前登记表精确字节保存在`docs/archive/OPEN_SOURCE_REGISTRY_PRE_BYBIT_HYBRID_20261002.md`，
SHA `67b1d5e77a7ba0b2d595bac50429522848c0e89053966b1585f344d5770174e0`。
本轮经济登记前原表精确字节保存在`docs/archive/OPEN_SOURCE_REGISTRY_PRE_HYBRID_ECONOMICS_20261002.md`，
SHA `f77aec85bf0ddf442fe7f1b23c8911c43b5f2784e7fbc5f41b1638086defdb4e`。
D020时下一公开RSI2仅浏览同pin原文；该结果前状态现由上方D021–D022实际安装／六账户证据更新。

## 当前集成增量（FR66/FR67/FR68）

FR66/FR67验收时的登记表原字节已保存在
`docs/archive/OPEN_SOURCE_REGISTRY_AFTER_TLOB_20261001.md`，SHA256
`bf48b66b7637eb3336f84292689e4ba475d590d57f283ba89c1d3c184f94a49c`。
其原验收凭证不修改；历史绑定按此精确字节副本核对，当前集成另行绑定本表。

以下原FR61核验是11:49 UTC的历史快照，字节副本保存在
`docs/archive/OPEN_SOURCE_REGISTRY_FR61_20261001.md`，SHA256
`54b3995408556c7b2960aba1defc0731222ae825b7bf17b1c90b1a49580ec134`。
原凭证与Git提交`7fd5d936`保留；本登记表按实际集成继续更新。

| 项目 | 实际集成状态 | 本地修改与验收范围 |
|---|---|---|
| pytorch-tcn 1.2.3 / MIT | ADOPTED_ENGINEERING | 原包零修改；仅末态encoder＋共同8输出head；TCN-S/M各四项smoke通过 |
| TLOB `f1c0af4d81067978914361766db0457a7d8b6a46` / MIT | ADOPTED_ENGINEERING | `third_party/tlob`最小三核心、LICENSE/原字节/SOURCE_INDEX/UPSTREAM；仅相对导入、显式CPU、移除无用绘图导入、BiN负权重原地修复与零std保护；adapter替换末层3类head |
| River 0.26.1 / BSD-3-Clause | ADOPTED_ENGINEERING | 原包零修改；462个RECORD摘要逐字节核验；官方scaler/LinearRegression/ADWIN加完整标签成熟队列、共同replay六项通过。正式六fold待运行 |
| TS2Vec `b0088e14a99706c05451316dc6db8d3da9351163` / MIT | ADOPTED_ENGINEERING_AND_SHORT_MARKET_SMOKE | `third_party/ts2vec`官方七文件＋完整LICENSE和原字节；仅三个相对导入及包导出；官方合成smoke三项通过。共同两日实际train-only预训练600迭代及两个冻结probe完成；正式六fold待运行 |
| Torch 2.7.1+cpu / BSD-3-Clause | CPU_RUNTIME | 官方CPU发行版，未编译CUDA；独立D盘WSL研究环境，不改旧依赖锁 |
| NumPy 2.5.3 / BSD-3-Clause，einops 0.8.2 / MIT | COMPATIBILITY_DEPENDENCIES | 原包零修改；固定实际版本；NumPy/Torch/sklearn接口已运行核对 |

TCN-S/M、MLPLOB、TLOB、TS2Vec两probe以及Ridge和两档XGBoost均完成共同四路两日工程段。
River工程接入通过、真实短段回放另行验收。
共同180天、六个OOS fold、统一经济评价及预测稳定性结论尚未通过。
完整本地修改逐项见`third_party/tlob/UPSTREAM.md`，独立模块文档/验收凭证另列。
不安装tsai、不复制LOBFrame或未确认许可的LOBench代码。

### 共同数据与评价的既有依赖

以下实际import/安装元数据核验保存在
`reports/fast_research/FR65_SHARED_LIBRARY_METADATA_20261001_V2.json`。
沿用既有环境，零本地库修改；包发行版与repo HEAD不混称。

| 项目repo | 实际包版本 | 主项目许可证 | 用途 | 本地修改 |
|---|---|---|---|---|
| https://github.com/scikit-learn/scikit-learn | 1.9.1 | BSD-3-Clause | 共同StandardScaler、Ridge、多输出probe | 无 |
| https://github.com/dmlc/xgboost | xgboost-cpu 3.4.1 | Apache-2.0 | 两档固定树模型 | 无 |
| https://github.com/lightgbm-org/LightGBM | 4.7.0 | MIT | TS2Vec固定树probe | 无 |
| https://github.com/apache/arrow | pyarrow 23.0.1 | Apache-2.0 | Parquet row-group读取 | 无 |
| https://github.com/pola-rs/polars | 1.44.2 | MIT | 原有共享聚合、labels、daily metrics | 无 |
| https://github.com/scipy/scipy | 1.18.1 | BSD-3-Clause | Pearson/Spearman共同指标 | 无 |
| https://github.com/encode/httpx | 0.28.1 | BSD-3-Clause | 原有薄官方归档HTTP调用 | 无 |
| https://github.com/numpy/numpy | 2.5.3 | BSD-3-Clause | 共同数组/数值接口 | 无 |
| https://github.com/pytorch/pytorch | 2.7.1+cpu | BSD-3-Clause | 官方DataLoader/optimizer及模型运行 | 无 |
| https://github.com/arogozhnikov/einops | 0.8.2 | MIT | 官方TLOB张量变换依赖 | 无 |
| https://github.com/narwhals-dev/narwhals | 2.26.0 | MIT | River发行版依赖 | 无 |

主项目许可证不能覆盖wheel内全部第三方运行库；实际发行版完整license保留于安装环境。
XGBoost的发行包名为`xgboost-cpu`，Python import名为`xgboost`；首次按import名查询
包元数据失败，独立V2模块快照保留，随后按真实发行名补核，不是依赖损坏或重新安装。
FR68核心登记时的原表也保存于`docs/archive/OPEN_SOURCE_REGISTRY_FR68_CORE_20261001.md`。
FR68完整依赖登记时原表保存在`docs/archive/OPEN_SOURCE_REGISTRY_AFTER_FR68_20261001.md`。
TS2Vec的UPSTREAM日期补记仅文档增量；其原文保存在同目录`UPSTREAM_FR68_CORE_20261001.md`。

## 原FR61来源核验快照（以下安装状态以当时为准）

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


### 固定公开 SMA50/200 日线来源（D038，收益运行前登记）

| repo | commit／license | 用途与本地修改 |
|---|---|---|
| https://github.com/jesse-ai/example-strategies | `7c91e0a37bf62165790120d730442e4f6eb00364`／MIT | 原 `SMACrossover/__init__.py` 置 `third_party/jesse_example_smacrossover/smacrossover_original.py`，SHA `453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae`；原策略及同commit MIT许可字节零修改。COIN将仅移植长仓/退出hook，固定50/200闭合UTC日线，原short及whole-balance不移植；风险、10k资本、36bp费用与既有proxy账本复用。不安装新环境，不称原策略回测复现或投资资格。 |

追加前原登记字节保存 `docs/archive/OPEN_SOURCE_REGISTRY_PRE_SMACROSSOVER_20261003_V1.md`，SHA `b3143326fd24f534c501a5f2a5ed81ae2ad5bba19d3106af261fe9e62acad3bb`；旧记录及原冻结来源不改写。

### USDT线性永续双向研究增量（D040）

| repo | 固定commit／license | 用途及本地修改 |
|---|---|---|
| https://github.com/jesse-ai/example-strategies | `7c91e0a37bf62165790120d730442e4f6eb00364`／MIT | 原SMA50/200源码与许可零修改；新增COIN永续adapter接入原short entry/exit及long hook。固定daily、闭合200日、过去30日有符号协方差、绝对.3/.6和统一.99 sizing buffer。四方向分别只许可指定方向，空仓独立；原全仓、Jesse执行不复现，退出后下个daily决定才可新入场。旧D038 Spot long-only结果不改名完整复现。 |
| https://github.com/binance/binance-public-data | `f446ce3812bd4e5521f21faecd4ae3c6460e49fc`／README软件MIT声明；数据另受原登记条款 | 复用原`download_file`及已有薄包装，官方USD-M monthly klines URL、CHECKSUM和ZIP CRC。新增28个1d、14个1m档；仅资源兼容扩展单ZIP16MB/解压CSV128MB边界，真实最大ZIP约2.02MB，原2MB限制不足。保持成交OHLCV、quote/taker量与count，不用mark/index冒充成交，不重写下载框架。 |
| https://github.com/pola-rs/polars / https://github.com/numpy/numpy | 既有锁定`1.44.2`／MIT、`2.5.3`／BSD-3-Clause | 共用来源接线、目标、过去协方差及评价；库零修改/零新安装。标准库Decimal独立参考会计；原ExecutionContractV2只复用时钟与成本算术，不将其Spot费用/风险身份赋予永续。 |

新账户为最小逐仓单向线性合约研究适配，无交易所连接。旧carry固定hedge不能承担一般方向及反手；不安装新平台或复制第三方交易引擎。原Spot库存保护保持，资金费单位/Bybit原生成交/历史MMR与filters尚未认证，只能明确假设下筛选。新增前登记表原字节保存在`docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_20261003_V1.md`，旧凭证按该字节核对；不覆盖历史登记。

### 同产品公开2小时永续参照（D041）

| repo | commit/version及license | 本地用途与修改 |
|---|---|---|
| https://github.com/jesse-ai/example-strategies | 7c91e0a37bf62165790120d730442e4f6eb00364／MIT；Jesse指标417f8765225e3bfc12043d4b712f19fe15a3c078／MIT | 原Donchian strategy/indicator零修改，复用原prior20通道/SMA200 entry filter及held lowerbreak exit；原should_short=False保持。仅COIN产品适配、UTC2h闭合时钟、past30日风险和原逐仓账户，whole-balance/Jesse执行不复现。该策略是具体公开参照，不代表完整开源市场。 |
| https://github.com/binance/binance-public-data | f446ce3812bd4e5521f21faecd4ae3c6460e49fc；原软件MIT声明/数据条款继续 | 两个July2025 USD-M官方2h monthly ZIP，复用download_file/CHECKSUM/CRC和原薄格式转换，仅私有AST改interval/duration与12bar/UTCday，无新downloader；20MB/512MB预算。其余已验收USD-M分钟用原closed_hours与Polars first-open/sum-volume合成2h，不混Spot预热、不截短评分。 |
| https://github.com/pola-rs/polars / https://github.com/numpy/numpy | 既有1.44.2 MIT/2.5.3 BSD-3-Clause | 原库零修改/无新安装；统一账户、过去30UTC日风险、同两窗口/10k/成本/完整资金费事件/日月评价。私有原controller仅四signal接点，金融语义与旧Spot保护保持。 |
追加前当前登记原字节保存 docs/archive/OPEN_SOURCE_REGISTRY_PRE_DONCHIAN_PERPETUAL_20261003_V1.md，SHA b9965d36cd017e7c0df9d3550ffa1a5903e7551af2d14e209a766c3f8f9d8293；实际source/金融经济尚待本轮运行验收，不提前宣称PASS。

### 固定547日永续研究输入（D042）

复用 https://github.com/binance/binance-public-data 固定 f446ce3812bd4e5521f21faecd4ae3c6460e49fc；README软件MIT声明和原数据条款边界沿用。没有修改官方download_file、换下载host或安装依赖。新增perpetual_history_source薄编排仅固定148个URL、两个阶段、资源预留与receipt；原trade/mark/funding转换和CHECKSUM/CRC复用。资源兼容只在私有原函数namespace调整ZIP16MB、file32MB和CSV128MB；2h原日历适配沿用。独立QA复用原audit_one，trade仅私有2h duration分支，全部原CSV值和UTC月历/跨月实际funding间隔核对。Polars1.44.2 MIT、NumPy2.5.3 BSD-3-Clause及锁定环境保持。

固定研究日历2024-01-01..<2025-07-01；新trade1m36、mark1m36、funding36、daily38、2h2，旧12个USD-M日档仅凭证复用。已见开发筛选输入，不是Bybit原生数据/成交或未来证据；funding单位/charge/publication未认证。本条登记源编排用途，实际source接受与经济另见模块凭证，不提前宣称通过。追加前完整字节保存在OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_HISTORY_20261003_V1.md，SHA1c33a5a19063cd4a4331892c1f2490d80a4fa30ad2ee138d39a20090b92b503d。
### D043：完整213日同产品对照复用

| repo | commit/version / license | 用途和本地修改 |
|---|---|---|
| https://github.com/binance/binance-public-data | f446ce3812bd4e5521f21faecd4ae3c6460e49fc / 原README软件MIT声明，行情另沿原条款 | 同官方URL/CHECKSUM/CRC，51逐文件完整旧工件＋21新mark/funding档；原download_file/CSV转换不改，薄编排只固定72选择和显式两owner。全72第一次独立日历验收；原547 failed/source及8月缺口不改，不称恢复547或原生Bybit。 |
| https://github.com/jesse-ai/example-strategies | 7c91e0a37bf62165790120d730442e4f6eb00364 / MIT；原Donchian indicator版本沿D041 | 原SMA50/200双向及Donchian2h prior20/current200 hook零修改，沿用D040/D041产品/风险/账户适配；只私有日期/metadata接线213，原金融体和容差不改。SMA four方向/cash和原Donchian仅多，非原Jesse执行复现、非整个公开市场水平。 |
| https://github.com/pola-rs/polars / https://github.com/numpy/numpy | 1.44.2 MIT / 2.5.3 BSD-3-Clause，原uv.lock | 原库零修改/无新安装，同输入/账户/指标；标准库Decimal原独立参考会计，17实际金融调用＋3恒定现金严格等价。显示unit冲突/独立路径用新V3修复，只metadata不改经济。 |

追加前当前登记原字节见OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_213_20261003_V1.md；旧引用继续按历史SHA与对应archive校验。实际21新源、72 QA、20市场选择器/17实体工件、独立/保存比较/根均有真实exit0，详见D043模块；资金费单位/原生风险/发布/长期APR仍未认证。

### D044：同产品受控持有强基准

| repo | commit/version / license | 用途、本地修改 |
|---|---|---|
| https://github.com/binance/binance-public-data | f446ce3812bd4e5521f21faecd4ae3c6460e49fc / 软件MIT声明，行情沿原条款 | 原官方URL/CSV/CHECKSUM和已接受156档，只读合并原元数据；无下载/旧QA重跑，不扩数据资格；原547失败和缺口保留。 |
| https://github.com/jesse-ai/example-strategies | 7c91e0a37bf62165790120d730442e4f6eb00364 / MIT；原Donchian版本沿D041 | 原SMA/Donchian hook零改，引用60已接受same-product摘要。新HOLD只复用原fixed_targets AST与signed风险函数，私有方向hook固定多头；非Jesse完整engine或原Spot EWMA复现。 |
| https://github.com/pola-rs/polars / https://github.com/numpy/numpy | 1.44.2 MIT / 2.5.3 BSD-3-Clause，原uv.lock | 库零修改/无新安装；原金融simulate AST、Decimal独立账本/audit_case体与指标不改，只一个新目标及元数据adapter。三窗口12新真实账户、独立12金融调用；单位/原生/长期APR不认证。 |

追加前精确当前登记见OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_HOLD_20261003_V1.md（b43b2464…），旧所有SHA继续按原archive/凭证核验。原v1/v2失败metadata和新修复版本均保存，不通过放宽金融容差/成本/风险制造通过。采用研究基准/比较能力，投资现金/NONE。

### D045：固定303日来源增量（运行前登记）

沿用 binance/binance-public-data 固定 f446ce3812bd4e5521f21faecd4ae3c6460e49fc、原README软件MIT声明/行情条款；原 download_file、CSV/parser、CHECKSUM/CRC 和94固定官方URL无重写，无新依赖或host。薄编排仅原D042 main私有选择94：54旧完整工件原owner与receipt不变，40新mark/funding；原148与42 HEAD/CHECKSUM任务仅投影，不伪称新元数据任务。70首次独立QA、24原验收日档只流式哈希和凭证复用，不重复旧行/CRC。Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause及原锁定环境零修改。303已见筛选输入，不升级原547失败或Bybit原生/资金费单位/投资资格。本条实际source验收尚未执行，完成凭证另存。
D045实际复用闭合：SMA原jesse-ai/example-strategies commit7c91e0a37bf62165790120d730442e4f6eb00364/MIT hook零改；D044固定多头风险适配、原simulate/Decimal账本/指标直接调用，只有303日期、五选择器和metadata接线。Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause及原环境无新安装/库修改。source/70首次+24QA复用/一个新增病例/20选择器/独立17调用/保存比较/最终ROOT均真实closed0，四LS停止前缀保持NE；无旧QA/旧账户重复。当前登记追加前原字节见OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_303_20261003_V1.md，所有旧来源SHA/许可证继续。协议继承字段reused_daily_archives=12仅原D040日档子集，实际producer复用daily34（另外22为原H42）；完整实际94=54旧/40新、QA70/24为本版权威数量，不覆盖冻结协议。采用对照和复用能力，不认证投资/单位/Bybit原生成交。

### D046：仅风险减仓正确性薄适配（已实际完成）

同原Jesse例程7c91e0a37bf62165790120d730442e4f6eb00364/MIT、SMA日线hook、Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause和原环境；第三方实现无修改/新安装。原controller/account冻结不变，仅私有simulate两个唯一AST锚：risk request向合法step/min10取整和risk完成向零谓词；DAILY_TARGET/TERMINAL/fill-capacity/费用/mark/caps/时序/资金费均不动。初freeze anchor0真exit1/0arrays保存，V2表达式锚只元数据修正；唯一新手算/容量/未来扰动case真PASS。四303日LS新账户全部完整、原HandLedger/independent audit_case直接调用4次，其他16已接受摘要引用不重算，旧4停止前缀保留。最终ROOT053f42ed…真0；正确性能力采用，固定SMA投资/HPO暂停，候选NONE/APRNE。原登记精确字节在OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_RISK_REDUCTION_20261003_V1.md，不能误称原生Bybit或单位认证。

### D047：TurtleRules固定4h双向研究（使用前登记）

jesse-ai/example-strategies commit7c91e0a37bf62165790120d730442e4f6eb00364/MIT，原TurtleRules源码零修改、4h为本地事前选择，保留20/10含当前bar/ATR20×2/最多4层0.5ATR/原S1与成交hook。成熟Jesse417f官方ATR/Donchian wrapper、已接受jesse-rust1.3.0原扩展与原许可证直接复用，无新安装/手写indicator；新增薄context/order/callback桥仅共享caps/过去cov sizing、持久延迟stop、partial/恢复执行适配，非完整native Jesse intrabar或经典Turtle认证。源码获取V1 TLS失败已保留，V2恢复及兼容性未验收，不写成功。Binance binance-public-data f446ce... 原官方URL/download_file/CSV/CHECKSUM薄适配，拟仅新增USD-M4h2024-07/08两币预热，不补旧547失败；score复用原303官方1m/mark/funding与每日risk。旧精确registry在OPEN_SOURCE_REGISTRY_PRE_TURTLE_20261003_V1.md；所有source/version/license/实际本地差异以新proof具体哈希绑定，投资NONE/资金费单位条件/seen/no orders/资源边界保持。
D047实际闭合：Turtle原类SHA35e4c3cd.../ATR原wrapper398a1225.../MIT80d87314...、原Jesse417f与jesse-rust1.3.0直接复用；无新安装/第三方修改/自写ATR。源码V2 actual0、4×186新官方4h预热独立0、唯一新入口caseV2 PASS、四新账户actual0/独立金融4调用/保存摘要比较V2 actual0。新薄bridge6056ead6...含真实逻辑ENTRY/ADD/STOP/EXIT/RISK/TERMINAL与首次正fill原callback/片段保护/恢复；V2 controller dff1fc4f...只修V1五条/两条相邻AST锚。原S1 last_was_profitable仅原takeprofit置位未补造完整经典Turtle。4h score仅原完整303分钟聚合；744预热行不评分、不插值、不补旧547缺口。1完整净−5.55%、3合法停止前缀NE；规则/失败/原账户不覆写。记录金融认证仅已记录wallet/NAV，不认证完整策略意图、盘中native stop或历史Bybit过滤。Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause、原uv.lock97335...保持。采用接线能力，投资CASH/NONE；下一主任务公开Bybit产品过滤语义，非模型HPO。明细及实际proof见TURTLE_PERPETUAL_20261003.md；新增repo/source/LICENSE/UPSTREAM位于third_party/jesse_example_turtle_rules。
### D050：正常多币组合与官方历史来源复用

无新第三方库安装或修改。沿用binance/binance-public-data固定f446ce.../MIT的官方历史URL、CSV格式与.CHECKSUM定义及已登记格式解析；当前WSL无路由Errno101，网络环节的明确兼容例外为正常Windows System.Net.Http默认HTTPS访问同一官方主机，固定范围、字节/耗时上限、无重试/新代理/限制绕行。薄包装为scripts/investment/multi_asset_data.py与multi_asset_official_transport.ps1；本轮过去July流动性/200日资格选池先于September读取，UNKNOWN完整保留。

目标/协方差与账户正常参数化N，复用Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause、Python标准Decimal和原ExecutionContractV2，原环境uv.lock97335...不改。HOLD是本项目过去风险控制常量多头基准，不冒称原创alpha或完整公开bot；SMA原MIT hook仍可通过同一N目标接口使用。第三方无本地改动，本地改动为有序身份、逐币profile、共享账本、按日分钟读取和正常关闭规则。历史旧实现以其Git复现，不要求保持旧金融源码为当前依赖。

### D051：固定池跨月份与残仓标记净值

同一binance/binance-public-data f446ce3812bd4e5521f21faecd4ae3c6460e49fc/软件MIT声明、官方URL/CSV/.CHECKSUM及原行情条款。仅正常薄编排扩至已授权完整2024年10月；24新档首次独立QA，6旧October与80已接受暖源只metadata/hash复用。Windows System.Net.Http仍默认同一官方HTTPS/原限制，无新代理/重试/规避；初环境入口失败发生在网络与行情前，原记录保持。

Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause、标准库Decimal/原环境无安装或第三方代码修改。正常日期/closed-September日线聚合及source catalog集合guard、完成分类和保存marked末未实现归因为本地适配；金融、费用、0.1%容量/5次退出政策不改。旧D050通过Git b00183d复现；本版旧7c0/45fa/5d21实际入口归档，非继续堆版本运行包装。十币marked独立核算通过但清仓收益NE，无原生或投资认证。

### D053：固定公开SMA50/200与同池HOLD的方向机制对照（运行前登记）

直接复用 jesse-ai/example-strategies commit7c91e0a37bf62165790120d730442e4f6eb00364/MIT 原SMACrossover hooks与已登记Polars1.44.2/MIT日线均值实现，原第三方源码及LICENSE零修改，无安装或新依赖。新public_sma_pool_target.py仅调用现有配置化目标接口，接入同July十币池、固定50/200多头/空仓状态、原过去协方差风险与共享10k账户；未active等权预算不重分配。原公开教学信号作为机制对照，不称完整Jesse执行或市场强bot。两个完整已见开发月复用既有来源、资金费条件与成本，不下载/训练/搜参。当前登记追加前精确字节见archive/OPEN_SOURCE_REGISTRY_PRE_PUBLIC_SMA_POOL_20261004_V1.md，SHA12563be0047e2b09a43c44eeb0a957cdbeaa15d3ec27bc63b5f72f933d492283；旧登记和负结果保留。
D053实际闭合：同原Jesse7c91e0.../MIT与原SMA/Polars均值，第三方零修改；薄adapter0d8eca...、正常组合d6678c...、独立scalar参考82f461...、保存对照e3fec4...。两月8新实际/8独立账户与两对照真实exit0，固定方向gross明显弱于同池HOLD，配方暂停/能力保留，投资NONE。无新库/模型/数据/搜参；进度正常sampler c90仅修双writer临时路径与明确阶段新鲜度，不改研究Progress/金融源码。原registry snapshot12563be...及原负结果/残仓/单位UNKNOWN继续保留。
### D054：固定November来源增量（运行前登记）

沿用binance/binance-public-data固定f446ce3812bd4e5521f21faecd4ae3c6460e49fc/原软件MIT与行情条款、官方USD-M URL/.CHECKSUM/CSV格式与已登记成熟parser，正常薄wrapper只有限添加已授权2024Nov和完整Sep/Oct暖源。24首次新QA、6BTCETH303旧meta与90暖源复用，不新增aggTrades/LOB/daily下载或库安装。WSL无route仍原Windows System.Net.Http默认同一official HTTPS、字节/耗时限制，无重试/新代理。Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause/Decimal原环境不改；账户/执行/费用保持，不认证Bybit原生/资金费单位或长期APR。正常日历/metadata接线是本地修改，原代码由Git3549675复现，失败/旧证据不覆盖。

### D055：连续91日既有来源/账户复用（运行前登记）

仍使用上述已登记Binance来源、Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause和标准库Decimal，0新依赖/第三方修改/下载/训练。正常适配只将原Sep/Oct/Nov接受manifest做小metadata组合、日块遍历和独立必要金融列连续读取，原三HOLD目标/共享账户/资金费/费用/风险/原五次退出数学不变。原D054与此前结果由Git90c6020及其父提交复现，不复制整套版本或框架；既有源格式QA证据按原byte/SHA复用，不自授新认证。

D055实际闭合：同原Binance f446ce.../Polars1.44.2/NumPy2.5.3/Decimal，0新增依赖或第三方修改。Normal continuous接口与三accepted160身份metadata复用，12新实际/12独立与两保存对照已真实0；唯一金融input候选筛选修正不改数学/容差，原失败source/report/plan保持。Core账户/目标/执行仍原字节，不把条件历史净利当原生或APR资格。

### D056：下一固定季度（运行前登记）

复用原binance/binance-public-data固定f446ce3812bd4e5521f21faecd4ae3c6460e49fc/官方URL+CHECKSUM+格式，现有thin默认Windows传输与trade/formats parser；不新造下载框架。Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause、Decimal原环境零安装/第三方修改。正常本地适配只增Dec2024–Feb2025有限日期/profile、单quarter源与按日块读取；72首次新QA、18旧score与100旧warm接受metadata复用，0重旧CSV/CRC/行情账户/模型。原账户/风险/目标/费用/资金费体保持；旧D055/失败由Git1f40239及父提交复现，历史证据不篡改。Bybit原生与单位/发布时钟不自授认证。

### D057：固定30日方向/现金薄适配（调用前登记）

本配方是COIN自己的简单研究规则，不冒称公开momentum策略完整复现，无新第三方repo/安装/模型库。固定30个完成日close比较与一个state hook，直接复用已登记NumPy/Polars、正常public_sma_perpetual.fixed_targets(direction_factory=...)的有序成员/过去协方差/风险及共享账户；原第三方版本/license/本地修改继续见上表。官方public-data/CHECKSUM只复用两已接受manifest，不下载/重QA；不加载原Jesse SMA alpha，不新增训练、资源框架或金融loop。

### D058：日线RSI2固定多头/现金薄适配（已运行）

复用MIT `jesse-ai/example-strategies` commit `7c91e0a37bf62165790120d730442e4f6eb00364` RSI2原类，原SHA `fd463da53b6ac78138a0886268f654973daa569dd2094c6aa96796a8a5015f70`/license `80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d`。官方indicator源commit `417f8765225e3bfc12043d4b712f19fe15a3c078`、原已装jesse-rust1.3.0及bindingSHA `4035a57485f63bc7e4470f91b7fdea950e3b99a07638e959d32013b705f23b2a`沿旧登记；0新依赖/第三方修改/自写RSI。正常本地adapter仅日线完整close上下文、明确240完成日、原long入/出hooks与COIN共享目标/风险，日线是新显式假设，原类未声明周期，原short/go/资金配置/原生执行未复现，旧1h负结果不覆盖。8新账户/8独立参考实际完成，不称完整双向公开策略复现。

Binance public-data原repo/固定commit `f446ce3812bd4e5521f21faecd4ae3c6460e49fc`/MIT软件和行情条款继续；仅January1d8新档/首次QA与2旧meta复用，官方URL/CHECKSUM/CSV薄编排，不重新造下载framework。正常Polars/NumPy/Decimal已登记版本不变，独立参考使用原官方compiled顺序RSI（共享内核限制明确）。第三方源码无修改；本地source-verification只精确允许原已pin两源码文本，旧金融函数体和容差不变。Bybit VIP0配Binance行情仍代理，单位/native不认证；本配方投资暂停，能力保留。
### D059：原RSI2选择性short共用N资产账户（已实际运行）

仍复用MIT jesse-ai/example-strategies commit7c91e0a37bf62165790120d730442e4f6eb00364/原RSI2 fd463da53b6ac78138a0886268f654973daa569dd2094c6aa96796a8a5015f70、license80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d，官方indicator commit417f8765225e3bfc12043d4b712f19fe15a3c078/jesse-rust1.3.0与上述binding不变。0新依赖/第三方修改/自写RSI。正常adapter仅增加原明确选择性short入/出、LONG_ONLY/SHORT_ONLY/LONG_SHORT/CASH模式与本地N共享目标；runner与独立reference传同mode、保存comparer加入direction对照。240完成日、原5/200/2/10/90与日线假设不改，原go/全余额/原生执行仍不复现；不能称完整Jesse engine复现。默认long与Git61316ff原目标/状态一致，历史源/证据由Git保留，未复制版本框架。

所有行情直接复用两已接受Binance public-data f446ce3812bd4e5521f21faecd4ae3c6460e49fc官方URL/CHECKSUM/CSV与January暖源；0下载/新源QA/库安装。Polars1.44.2/MIT、NumPy2.5.3/BSD-3-Clause与Decimal/原账户不变。8真实共享多空账户、8独立金融与8保存方向pair已完成；核账共用官方compiled RSI内核限制明确，不冒认第二独立递推。Bybit费用与Binance数据仍代理、单位/native不认证；投资NONE/CASH，固定配方暂停，方向能力保留。

D060本地Turtle适配更新：jesse-ai/example-strategies原登记commit/MIT不变，未重写原ATR/Donchian/Turtle hooks；直接共享N账户事件接口、ordered symbols/snapshot、allow_pyramiding薄适配。真实回放揭示未缩放权重→数量映射误差导致伪risk reduction，旧投资解释待新正确性版本替代，非开源原策略缺陷认定。

D061（2026-10-04）：沿用既有jesse-ai/example-strategies已登记commit与MIT原文件，未改第三方源码。正常本地Turtle bridge V3_EXACT_CANDIDATE只修未缩放Decimal候选身份（8行），数量/STOP/EXIT必要反例和同成本303日True/False实际回放见TURTLE_EXACT_QUANTITY_*；无新模型或框架。

D062：继续原binance/binance-public-data f446ce3812bd4e5521f21faecd4ae3c6460e49fc/MIT软件及行情条款、官方URL/CHECKSUM；仅本地四月编排/已保存字节恢复。Polars1.44.2/MIT、NumPy2.5.3/BSD和Decimal不变，无新依赖/模型/第三方修改。正常parse_csv明确Float64价格/量、Int64时间/count，避免整数前缀推断丢小数，账户Decimal不变。十二122日账户/十二独立账本已运行。用户Bybit snapshot是输入证据非开源代码/历史费用证书，未启用新产品或Maker成交。

D063：未增加第三方库或框架。继续复用原ExecutionContractV2 clock/费用算术、Decimal/NumPy/Polars/pytest；仅薄用户费率快照适配和正常账户接口。Bybit费用/公开盘口官方说明是来源参考；用户JSON SHA a406d4bd..为当前账户场景输入，不是开源项目或原图/历史费区认证。禁自造downloader/online/model框架保持。

D064运行前登记：沿用MIT jesse-ai/example-strategies commit7c91e0a37bf62165790120d730442e4f6eb00364及jesse indicator417f8765225e3bfc12043d4b712f19fe15a3c078；复用既有third_party/jesse_example_donchian原类fc635b25..和原Donchian指标b7e96ebe..，license80d87314..，0新库/第三方修改。正常薄adapter只close上下文、原filters接线和显式日线共享N风险sizing，非whole-balance/native Jesse复制。标量SMA200使用NumPy均值，上游SMA实现内核未复现，独立直接窗口核数值；原previous20高低和严格entry/exit保持。Binance已接受官方source/CHECKSUM370身份只组合，无下载/新QA；费用/资源依赖沿D063正常接口，不添加策略框架。

D064实际复用闭合：3条连续研究配方在303日正常共享账户已产生12完整保存轨迹，日线source/目标直接参考与12金融核验完成；原未确认资金units/Bybit原生限制保持。十币HOLD输出预算失败保留，单次saved-financial orchestration仅调用现有normal财务函数和直接目标参考，无市场重放/新账户引擎/库。诊断复用normal saved measures与perasset Decimal桥；无自写downloader/模型/online/资源平台。相关性30样本只是描述，旧source/caps/成本未因收益调整。


D065沿用D064 pinned MIT Jesse Donchian原代码、license与commit，不修改vendor；仅COIN共享raw分配增加ACTIVE_EQUAL。原日线入场/过滤/退出未变，仍不是Jesse原生整个平台或Bybit成交复现。

D067运行前登记：继续原MIT Jesse Donchian类/指标的既有commit与四vendor/license SHA，第三方原字节不改；仅正常adapter新增COIN_EXIT10薄退出hook，调用原donchian(candles[:-1],period=10)。原prior20 entry/SMA200/共享风险接线沿用，不声称10日退出是原公开配方。无新模型/库/下载/框架；独立参考直接10日最低价与原20日入场窗口，不调用生产目标。

D070：沿用已登记同commit/MIT Jesse Donchian策略/指标/SMA200过滤；vendor字节与LICENSE保持，正常薄direction适配新增退出10后armed恢复prior10上沿，首次prior20与旧默认保持。共享targets可选reset_signal_state回调清资格/CASH的arm；无新库/Transformer/账户/下载框架。新变体为COIN适配，不称上游原始策略或Bybit原生成交。

D070真实结束：Jesse原commit/MIT与vendor字节保持，单一COIN快reentry变体完整四账户净与risk更差而暂停；原研究/多空能力保留。金融only无损报告schema/row编码，无新依赖/自写model/framework；独立decoder仅standard json/Decimal，完整3030记录/全源除报告块等价，范围非独立市场。失败、两币误启动2+前缀和真实8核账calls保留。


D071无新增第三方依赖/模型/下载框架；正常既有共享过去协方差风险函数只接线可选有限budget，旧默认10%保持。4新HOLD_TWO实际账户复用原共享引擎/Decimal核账，8%为COIN风险预算配置；旧公开策略vendor/commit/license未改。独立资金复核standard JSON/Decimal，不重放市场。


D072沿用已登记MIT Jesse Donchian原commit/策略/指标与license SHA，vendor未改；COIN既有EXIT10适配/共享账户/过去协方差规则未变。只修正常独立金融入口旧十币限定，并运行同两币配置对照；无新库/模型/账户/下载框架。保存诊断复用原measures/Decimal，独立standardJSON/Decimal金额桥不重放市场。


D073无新增第三方或vendor修改，继续已登记MIT Jesse Donchian固定来源；COIN薄adapter正常复用原HOLD10和EXIT10 ACTIVE_EQUAL目标接口，在过去风险缩减后固定各半，共享原账户。它是COIN目标组合，不原生Jesse组合或Bybit可执行复现。独立参考复用已有scalar/window/cov逻辑与标准JSON/Decimal；无新模型/下载或账户框架。

D081运行前登记：继续MIT jesse-ai/example-strategies commit `7c91e0a37bf62165790120d730442e4f6eb00364` 与 Jesse指标 `417f8765225e3bfc12043d4b712f19fe15a3c078`，原策略/指标/许可四SHA和vendor原字节不变。D080正常COIN4h信号/日风险接口保留；本轮仅薄 `ma_trend` property上下文从200个4h替换为200个已完成日，仍复用原 `filter_trend`/入场/Donchian通道以及既有COIN exit10。原SMA property上下文不再称全原样；并非将两个SMA作AND，也不改持仓退出。日协方差/HOLD日target/共享账户/费用/caps沿用。NumPy/Polars/Decimal原版本和许可证不变，零新库/模型/下载/账户框架；配方独立命名 `DAILY_TREND`，不声称原生Jesse或Bybit复现。


D085：复用 https://github.com/dmlc/xgboost ，本机 `xgboost-cpu 3.4.1`（import xgboost），Apache-2.0；仅共同日特征/5d成本带分类labels/one-hot symbol/既有账户的薄adapter，未改库源。一个固定CPU hist multi:softprob fit，非自写树/在线学习框架。参数定义参考 https://xgboost.readthedocs.io/en/stable/parameter.html 。NumPy/Polars/scikit-learn沿用已有环境uv.lock，不新增依赖或模型内核；Donchian/HOLD的既有vendor/commit/许可不变。未确认funding/basis/OI不补造；模型与行情只留D/STATE。

D086运行前登记：复用 https://github.com/scikit-learn/scikit-learn 已装1.9.1/BSD-3-Clause 的 StandardScaler 与 GaussianMixture，库零修改、零新安装。仅薄过去市场特征/训练中心状态映射/现有共享方向目标adapter；1个固定3-component diag GMM，random_from_data/n_init1，1个训练期scaler，0个内部KMeans或方向重训。HIGH_VOL_CRASH是预先固定过去行情风险覆盖条件，不造不存在的崩盘训练类。实际版本随运行receipt核对。方向复用D085已冻结XGBoost，过去/未来共同期间概率及三种旧默认目标逐字golden；不自写HMM/聚类框架。官方定义 https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html 与 https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html 。相关测试另有2次GMM/2次scaler拟合，仅未来扰动验证，不作alpha配置搜索；生产预算仍单一配置。

D087：既有XGBoost模型只加载，既有GMM仅作不可变对照；零新模型/标准化拟合，零新依赖与库修改。固定过去BTC SMA200/20d状态沿用D085/D086原描述性定义，薄规则adapter；4新共享账户与16原SHA对照。仅2项状态边界/未来可得性/缺口回归，零拟合；不重新实现模型内核。

D088：沿用D085已装XGBoost固定模型、D087薄过去趋势规则和原signed目标/账户，仅SHORT_ONLY mask反事实；零库修改/新依赖/新拟合。4新完整资本账户，对照20个已验收旧账户按SHA引用。已有SHORT_ONLY默认golden与独立目标会计复算复用，不重跑无关GMM模型。

D089 (2026-10-05): reuse existing XGBoost3.4.1 model, fixed BTC regime and owned perpetual account/data/cost cores; no new dependency/fit/search. Local change only optional daily zero-target persistent reduce-only retry, bounded by existing capacity, risk and terminal supersession; prechange Git-bound default golden + four related regressions. External strategy/model provenance unchanged.

D090 preregistration (2026-10-05): reuse pinned MIT Jesse SMACrossover hooks and Polars SMA adapter, original source/license bytes unchanged; public_sma_perpetual shared signed target intents, owned account/risk and D089 optional cash closing. One binary XGBoost3.4.1 Apache-2.0 fit, same fixed small CPU parameters, thin execute/reject adapter. Deterministic external primary intent, no in-sample primary probabilities/OOF requirement; no new library/framework/Transformer/online core. New recipe explicitly COIN prepared intent filter, not native Jesse balance/position execution or Bybit history.

D091 运行前登记：零训练冻结经典CTA四family，Moskowitz/Ooi/Pedersen 2012（https://doi.org/10.1016/j.jfineco.2011.11.003）12m sign与vol scaling方法参考；SMA200 sign为COIN双向日线规则，Faber原作者10月long/cash说明（https://mebfaber.com/2016/09/14/episode-20-listener-qa/）不是完整signed策略复现；Original Turtle Rules（https://www.followingthetrend.com/?mdocs-file=2551）20/10与55/20通道规则参考，未复制文献全文/添加ATR stop、加仓、完整系统1过滤。直接复用已登记MIT Jesse indicator commit417f8765225e3bfc12043d4b712f19fe15a3c078、原Donchian nonsequential内核及4vendor/license SHA；成熟NumPy mean/cov/std reduction，不重写指标/账户/框架，无新库安装或第三方修改。仅规则与时钟/方向/等权三forecast薄adapter，12m按真日历年/月初更新，未知保留；量额仍原owned Decimal账户。各家价格序列是永续trade-price proxy，12m不冒充原论文含roll/excess futures return。源字节/参数/两项真实回归已冻结在protocol，56成本/unit/方向实际账户上限；已见122日非完整周期，不能把crypto实验等同传统期货文献证据。

### D092 initial ATR protection reuse

Existing Jesse/Turtle MIT pinned source and jesse-rust1.3.0 unchanged; existing `turtle_perpetual_bridge.official_context` loads original ATR/go_long/go_short. Adapter: actual-first-fill anchor, initial-only symmetric2ATR, minute range observation, shared scheduler paid exits and next-month cooldown. No new indicator/account core; not full Turtle. Pins/installed receipt in `protection_journal.json` and frozen protocol source hashes.


D094运行前：继续复用D091已登记Jesse MIT commit417f8765225e3bfc12043d4b712f19fe15a3c078原Donchian内核及Turtle20/10、55/20公开周期；vendor/license零修改、无新依赖。仅显式输出原已计算55/20状态，固定两forecast等权平均（COIN adapter，非完整Turtle）。共同原vol sizing/Decimal账户/价格/资金费/用户费率保持；旧默认signal全窗口golden和CASH/HOLD全303日ordered targets核对后复用8控制，12新方向账户实际重跑。零训练/搜索/下载；V1新样本未触发半仓导致失败保留，V2实际突破样本通过3项相关回归。


D095：复用D091已登记NumPy reduction和既有SMA200 signed适配、既有共享永续账户及Jesse对照。repo/version/license/vendor修改均沿用既有登记，无新依赖或策略内核。SMA200 signed不是Faber原10月long/cash策略完整复现；本轮仅扩同窗观察并使现有只读汇总接受SMA200 family，不改财务或信号。

- D096 selective short: reuse existing MIT Jesse pinned20/10 and55/20 kernels; Goulding/Harvey/Mazzoleni2023 DOI10.1016/j.jfineco.2023.05.007 and Daniel/Moskowitz Momentum Crashes as research design references, no paper/code copied and no claimed crypto profit replication. Owned DC_CONFIRMED_SHORT adapter only; zero training/search, positive forecast unchanged, simultaneous negative confirmation and veto.

- D097 pandas-ta-classic https://github.com/xgboosted/pandas-ta-classic version0.8.32 (PyPI wheel SHA e8e1ede0c13d5927d28c91dce3d5ab2c71a1fb7f2e62fb61fe95178d4ab768e0), MIT, native CE22/3/rma default applicability and causal probe, local modifications NONE; only thin closed-daily adapter. Independent supplementary STATE runtime and all installed hashes in reports/SHORT_CHANDELIER_PROBE_20261006_V1.json; pandas2.3.3 BSD-3-Clause/dateutil2.9.0.post0 Apache-2.0 and BSD-3-Clause/pytz2025.2 MIT/tzdata2025.2 Apache-2.0/six1.17 MIT dependencies unchanged. TradingView https://www.tradingview.com/support/solutions/43000773013-chandelier-exit/ methodology reference only. Complete economic strategy is NOT_RUN, not copied/sold as profit replication.

- D098: existing Jesse MIT repo https://github.com/jesse-ai/jesse commit417f8765225e3bfc12043d4b712f19fe15a3c078 Donchian scalar kernel, same pinned bytes/license, modifications NONE. Thin4h20/10 state adapter and short gating only; Original Turtle Rules https://tradingblox.com/originalturtles/originalturtlerules.htm and Goulding/Harvey/Mazzoleni2023 DOI10.1016/j.jfineco.2023.05.007 are method references, no code or paper copied, no new dependencies, no claim full strategy replication.

- D099: reuse binance/binance-public-data MIT declared repo, commitf446ce3812bd4e5521f21faecd4ae3c6460e49fc, same original utility files and CHECKSUM scheme, local upstream modifications NONE. New Jan2022 scope only thin orchestration of existing source conversion and independent raw-reference APIs; no new transport/parser or downloader framework. Older source publication/unit/MMR assumptions remain unconfirmed; pilot is not economics.

- D099完成扩展：同pinned官方Binance utility/CHECKSUM，完整BTC2022–2023，三个月明确raw union派生输入有官方逐日父源、CHECKSUM和独立逐行核对；不是把本地派生ZIP标为官方整月原件。现有Jesse Donchian/past-cov及账户内核无改动，0新依赖/模型训练。ETH官方日源仍缺失，负结果保留。

- D100：复用D091/D095既有NumPy reduction与COIN SMA200 signed日线适配，保持现有版本/license/财务内核，无新依赖/第三方修改。只是公开均线方法family对照，不声称完整Faber10月long/cash或Man50/200策略复现。仅新增已有完整控制的身份绑定复用。

- D101：沿用NumPy既有版本/license、经典SMA200目标和账户；仅SHORT增加完成50日均价确认，OWN_MODIFICATION，不声称完整Man/Faber策略复现。无新库、训练、下载或周期搜索；旧默认逐日golden与独立标量参考验收。

- D101来源复查：Man Group https://www.man.com/insights/in-crypto-we-trend （其50/200均线交叉并非本地price-vs50过滤）；https://www.man.com/insights/need-for-speed-trend-following 仅方法/速度参考，未复制代码或收益。无代码version/commit/license改动，网页核查2026-10-06；本地SHORT50明确OWN_MODIFICATION。

- D102：继续复用 https://github.com/xgboosted/pandas-ta-classic 0.8.32／MIT，原已登记wheel与全部安装文件SHA相同，local modifications NONE。公开说明 https://www.tradingview.com/support/solutions/43000773013-chandelier-exit/ 仅方法参考；COIN ratchet/原持仓影子时点是OWN adapter，不是完整公开策略或新账户收益。

- D103/D104：复用jesse-ai/example-strategies MIT commit7c91e0a37bf62165790120d730442e4f6eb00364，third_party/jesse_example_smacrossover/smacrossover_original.py SHA453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae，原should_long/short/update_position不修改。现有public_sma_perpetual仅替换整余额sizing为共享10k/caps/past-vol，并使用COIN分钟成交；不是Jesse/Bybit原生复现。DC20/10、DC55/20、D096与SMA200参数不变；oracle DP/归一化分析是薄OWN_DIAGNOSTIC，不是新公开交易内核。NumPy/Polars沿登记版本，无新库、训练或行情下载。
