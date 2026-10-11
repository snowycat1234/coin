一次共同风险相关性实验，独立分支 research/joint-correlation-risk-20261011。

新增信息是同一个30日窗口的同步5分钟跨币协方差，预测次日相关性；保留原native简单日收益方差对角，只拟合一个全矩阵theta。旧HAR只预测方差，旧native已有30日跨币相关性。本实验不是HAR重命名，也不是论文原样复现。

方法依据：[Andersen等2003作者原文](https://econ.duke.edu/~boller/Published_Papers/ecta_03.pdf)，其外汇高频协方差结果并非加密货币净收益证据。PROTOCOL.json在拟合/未来标签评分前冻结；SOURCE_CONTROL_REVIEW.json是必要独立只读审阅。已见历史、时序成熟/purge、强基线、统计和经济门槛、预算均见协议。

数据引用已公开306b58c4，698连续真实trade风险日；不重复下载，不读locked及2023/24结果。全mark/资金费认证不齐，native钱包NOT_RUN。先预测质量，过门槛后才做保存targets的条件trade风险/尾部/换手诊断；实际风险及等比例减仓单列。旧STOP不变。

最小合成验证：
```bash
COIN_CPD_STATE=/workspace/jointcorr-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/jointcorr-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/joint-correlation-risk-20261011/test_joint.py --basetemp=/workspace/jointcorr-state/pytest
```

真实输入/拟合/恢复命令及结果将在各完成模块追加。合成测试不冒充真实历史。
