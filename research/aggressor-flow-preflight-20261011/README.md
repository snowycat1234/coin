这是相关性STOP后的下一项来源预检，独立research/aggressor-flow-preflight-20261011分支。只恢复固定BTC2022January原月，0下载/新收益标签/训练/targets/账户。主动买卖成交量是不同输入；旧selector已有unsigned volume momentum/zscore，因此不得以泛volume改名声称全新。

[Bouchaud等原文](https://arxiv.org/pdf/cond-mat/0307332)研究股票tradeevent-time方向持续与做市反转的平衡，强调成交方向自相关不等于价格可预测性；K线聚合比例不能复制原propagator、L2/中间价或limit-order机制。官方[USD-M kline字段](https://github.com/binance/binance-public-data)含totalquote/takerbuyquote，做原source/CHECKSUM/CRC/稠密格/买量不超过总量/零量NaN核验。

先冻PROTOCOL与synthetictest，再实际读一月。通过也只是完整CORE5flow来源准备的依据，不立即拟合。旧相关性/HAR/quantile/CPD/residualSTOP、mark/funding缺口与locked边界保持。

```bash
COIN_CPD_STATE=/workspace/flow-preflight-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/flow-preflight-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/aggressor-flow-preflight-20261011/test_preflight.py --basetemp=/workspace/flow-preflight-state/pytest
COIN_CPD_STATE=/workspace/flow-preflight-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/flow-preflight-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/aggressor-flow-preflight-20261011/preflight.py --output /workspace/flow-preflight-state/result
```
