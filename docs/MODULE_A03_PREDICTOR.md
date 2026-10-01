# A03：通用冻结模型推理接口

日期：2026-10-01。依据用户指定 v3 审计第 10、13 节。此模块只完成推理工程与合成验收，不训练、不搜索、不评估历史收益，不赋予任何候选部署资格。

## 范围与接口

新增 `src/quant/predictor.py`，未修改 `candidate_paper.py`、`research.py`、`backtest.py` 或旧研究证据。

`FrozenPredictor` 是算法无关 Protocol，公开 `model_type`、`schema_version`、`feature_names`、`decision_interval`、`prediction_horizon`、`release_sha256` 和 `predict(features)`。

| 实现 | 文件 | 输出语义 | 目标仓位 |
|---|---|---|---|
| `LogisticJsonPredictor` | 旧 scaler/coefficient JSON，原字节可保持不变 | 未来 4h 净收益为正的概率；`expected_return=None` | 按原阈值输出 0 或 0.30 |
| `LightGBMPredictor` | 原生文本 | 未来 4h 可执行毛收益，小数单位 | `None` |
| `XGBoostPredictor` | 原生 JSON | 未来 4h 可执行毛收益，小数单位 | `None` |

统一输出字段为 `expected_return`、`confidence`、`target_weight`、`prediction_semantics`、`release_sha256`。0.006 表示 60bp 预测收益；分类概率不能冒充收益。树回归不提供统计置信度。无状态 predictor 无法证明滞回状态及两小时持仓，树模型仓位须由后续独立决策规则产生；`None` 不能被下游解释为自动获准交易。

```python
from quant.execution_contract import ExecutionContractV2
from quant.predictor import (
    contracts_from_execution, legacy_feature_schema,
    make_predictor_manifest, load_frozen_predictor,
)

execution = ExecutionContractV2()
cost, risk = contracts_from_execution(execution)

# model_bytes 来自已获准研究导出的文件；本函数没有 fit 或市场读取。
manifest = make_predictor_manifest(
    model_bytes,
    model_type="logistic_json",  # 或 lightgbm / xgboost
    feature_schema=legacy_feature_schema(),
    execution_contract=execution,
    cost_contract=cost,
    risk_contract=risk,
    training_cutoff="2026-03-01T00:00:00Z",
    training_last_available_us=last_training_feature_us,
    training_last_label_end_us=last_training_label_us,
    training_data_sha256=training_subset_digest,
)

# 调用方按自己的不可改写 release 流程保存 manifest 后载入。
predictor = load_frozen_predictor(
    model_path, manifest_path,
    execution_contract=execution, cost_contract=cost, risk_contract=risk,
)
prediction = predictor.predict(feature_vector)
```

另有 `load_frozen_predictor_bytes()` 用于导出推理和工程测试。直接实例化三个具体实现也必须提供同样合同并通过完整校验。原生树导出应只含冻结的选定迭代；加载器使用文件中全部迭代，不根据未绑定的训练对象临时选择 best iteration。

## 冻结与拒绝规则

`frozen_predictor_v1` 的 SHA256 release 绑定：

- 模型确切字节 SHA 与长度、模型类型与原生格式。
- predictor 当前源代码 SHA。
- 有序特征名称、float64 类型、公式定义与 schema 版本；缺值规则固定拒绝。
- `ExecutionContractV2.version == execution_v2` 及其 `digest()`，包括 A01 源码/固定参数绑定。
- 费用与风险文档的版本、完整定义和 SHA；必须与 V2 规范参数相符。
- 训练数据子集 SHA、明确 UTC 训练截止、最后特征可得时刻、最后标签结束时刻。
- 决策周期、4h 预测期、输出任务/单位、CPU 单线程运行合同。

训练截止不得晚于 `2026-03-01T00:00:00Z`，最后标签不得跨越该截止。没有时区或非 UTC、重复 JSON 字段、NaN/Infinity、文件变化、schema/合同变化均拒绝。旧 Logistic 本身训练时的旧执行成绩仍属 `legacy_execution_v1`；新增推理绑定不重写旧标签、旧训练证据或 STOP 结果。

特征按冻结名称取值，dict 插入顺序不会改变向量。缺特征、未知特征、非有限数、字符串、布尔、复数、超出 float64 的数均拒绝。可附 `symbol/interval/available_us/received_us` 上下文但不作为模型输入；特征因果性仍需上游 A04 与数据可得时刻守卫证明，模型加载不能证明特征源没有未来数据。

SHA 是完整性绑定，不是外部签名，也不能证明不诚实的导出者没有伪报训练边界。后续研究 exporter 和 release receipt 仍须独立核验。模型可加载不等于 alpha 合格或可部署；A01 完整验收、R2/M1、锁定测试及真实前向资格由对应模块负责。

## 原生依赖与资源

Logistic 路径不导入 sklearn/research 或树库。LightGBM/XGBoost 在请求该类型时才惰性导入；缺库或无法加载 CPU 库时抛 `PredictorDependencyUnavailable`，不替换成 Logistic 或零预测。拒绝 pickle/torch 格式，不安装或使用 GPU。

首批 40 项验收时两树库未安装，该批只证明 API 适配合同和缺依赖拒绝，mock 不计真实原生加载。随后父任务安装并核对官方 wheel SHA 的 CPU 依赖：LightGBM 4.7.0、xgboost-cpu 3.4.1。A01 已通过后，获准追加纯合成工程拟合和真实原生加载验收，结果见下节；没有正式 alpha 训练或封存测试读取。

模型读取上限 64MB，manifest 128KB，文件增长也受有界读取检查；只允许 D 盘项目或 D 盘 WSL STATE，C 盘路径拒绝。本模块无文件写入、网络、订单或市场数据加载。工程命令统一由 `scripts/bounded.sh` 在 `hpc_linux` 执行，共享 RAM 硬上限 5GB、swap0、磁盘总上限 40GB、GPU 不用。

官方接口依据：[LightGBM Booster](https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.Booster.html)、[XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)。

## 合成验收

首批 **40 项独立测试通过（54.23 秒）**，代码检查通过。首轮 36 项耗时 104.60 秒，首次导入旧 research 推理依赖较慢。该批仅手工声明合成系数与随机合成向量，没有 `fit`、参数搜索或收益评估。

- 25 个同向量：原 research 导出推理、直接 scaler/logit 公式与新 predictor 的概率及阈值仓位一致。
- 固定容差 `abs=1e-12, rel=1e-10`；输入 dict 顺序改变结果不变。
- 模型、公式、执行、费用、风险、任务、源码 SHA 防篡改；训练特征与标签边界拒绝。
- 冻结数组/属性、manifest 副本隔离；直接构造不能绕过校验。
- 缺失、无效输入和重复 JSON 拒绝；D 盘文件加载通过、C 路径拒绝。
- 树 CPU1线程/native API 调用与标量语义的合成适配测试；分类目标不得伪装收益回归。
- LightGBM 与 XGBoost 缺依赖明确拒绝。

独立报告：`reports/A03_PREDICTOR_ACCEPTANCE.json`。内核实测共享 `memory.max=4,999,999,488` 字节，swap 硬限为 0。当前 A01 receipt 已存在，本模块绑定真实 V2 digest；这不代表新 alpha 研究已启动或获准。账户接线未在本工单修改；状态只能记为推理工程验收，不得记为 `ALPHA_CANDIDATE`。

## 追加真实原生 CPU 验收

追加后 **43 项全模块测试通过（53.64 秒）**，包含两库真实原生推理及新增 GPU artifact 提前拒绝。每库固定 32 行人工数据、2 特征、2 棵深度 2 树，没有市场输入、参数搜索、CV 或收益评估。合成训练数据 SHA 直接绑定 matrix+target 的实际字节。

| 库 | 原生文件 | 同向量最大绝对误差 | 结果 |
|---|---|---:|---|
| LightGBM 4.7.0 | 原生文本 | 0.0 | research Booster → exported native Booster → predictor 完全一致 |
| xgboost-cpu 3.4.1 | 原生 JSON | 0.0 | research Booster → exported native Booster → predictor 完全一致 |

两个真实原生模型均验证特征换序拒绝，以及分类 objective 不能伪装为收益回归。LightGBM 实测发现 `model_str` 忽略构造器 params；修为解析原生设备声明、构造前拒绝非 CPU、构造后核验实际 params，每次预测显式单线程，不再声称被忽略的参数生效。XGBoost 实际配置核验 CPU、单目标回归、原生特征名。

首次 native 运行 1 通过/1 失败保留在 `reports/A03_NATIVE_INFERENCE_TESTS.xml`：失败是派生二分类测试文本缺 sigmoid 参数，回归推理等价当时已通过。补齐测试副本的 sigmoid 元数据并修正上述实际 API 差异后，完整 43 项回归通过，证据为 `reports/A03_NATIVE_INFERENCE_TESTS_REPAIR1.xml`。未改写首次失败和首批 40 项报告。

最新独立报告 `reports/A03_NATIVE_INFERENCE_ACCEPTANCE.json` 绑定当前 predictor/test 源码、A01 receipt、库版本、模型/特征/release SHA、容差和资源限额。两个合成原生 artifact 与 manifest 留在 `reports/a03_native_engineering_models/`，只可用于工程复核，不能视作 alpha 候选。账户接线、R2 研究与任何部署仍是后续独立任务。
