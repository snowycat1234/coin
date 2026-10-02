# V8 因果入口适配模块验收

候选 **NONE / NO_QUALIFIED_CANDIDATE**，P1 **NOT_READY**。本模块只验收正确性；没有
行情模型拟合、交易收益或长期净 CAGR 证据。

## 接受范围

| 入口 | 当前实现 | 独立验收 | 实际运行 |
| --- | --- | --- | --- |
| 非重叠标签 | `labels_v5.py` | V5 R2：PASS_CONTRACT_IMPLEMENTATION | 合成验收 session 58695，exit 0；独立复审 81570，exit 0 |
| 固定共同特征 | `features_v4.py`，原 478 定义不变 | 审计 V3：PASS_FEATURE_CONTRACT_IMPLEMENTATION | 合成验收 68984，exit 0；独立审计 73372，exit 0 |
| 固定基准目标意图 | `benchmark_targets_v2.py` | PASS_INDEPENDENT_TARGET_ADAPTER_ONLY | 合成验收 63630，exit 0；独立审计 46205，exit 0 |

标签修复时戳／成熟期、严格 cutoff、OOF 来源守卫、锁定日期导出／split、缺失未来窗口
逐行保留及列序一致性。特征只增加 past-only primitive 与真实空条守卫，避免缺失价格／
成交大小静默补零以及整数 mask 绕过。基准目标只增加时戳整数守卫；持仓意图不等于成交。

旧绿色验收、独立失败及修复版本均保留。包括标签 V4 首轮列序失败、审计 probe 的
两项夹具修正、特征登记器 KeyError 和基准审计第一次在 pytest 捕获阶段退出。
没有重写这些报告；小型 probe、原输出、RUN_BINDING 和 JUnit 已精确归档。

## 根侧凭证

`reports/fast_research/V8_CAUSAL_ADAPTER_ROOT_MODULE_ACCEPTANCE_20261002_V1.json`
SHA256 `e032548588fc239547081af6a7e3f8f150b968186f5a6e8b55e45a1ba49d912a`。
根侧核对 42 份源码绑定、59 份工件绑定、4 项实际 task completed/exit 0。
复用已有实际输出，没有再跑一遍相同检查。完整 CPU 锁不变，全部在 bounded WSL 内。

固定特征 API 的合成十端点吞吐实测平均 0.02001 秒／端点；110k 端点约 37 分钟仅为
外推，不能保证行情缓存耗时。未拟合模型，GPU 0。

## 尚未接受

共同行情 scaler／模型调用链、完整经济回放、实际 ask/bid／size／latency 成交、费用与
不可能成交 mutation、资金费 carry、maker queue、最强风险基准增量及校正统计均未验收。
这次通过不能开启深度模型竞赛或交易。非重叠历史机制输出及日历补齐另行验收。
