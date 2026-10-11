独立分支research/trade-tail-resolution-20261011，冻结一个来源质量诊断：同一已完成日、同一真实前日收盘锚点下，比较实际1mOHLC极值与288个end5mclose极值。复用公开来源306b58c4，不下载、不重新解析原minuteCSV，不读取模型/结果数组。699来源日中的首日缺真实过去边界，保留NaN；其余698日均为已见历史，按2021/2022固定描述。

这量化旧5m尾部采样的覆盖限制；不是新alpha或旧quantile/HAR的复活。原流水号/源证书绑定、时钟、币种顺序及极值包含关系严格检查。单位10000*logpricechange为log-pricebp，不是PnL/costbp。真实交易OHLC极值不是markprice、BBO、可成交路径或清算证据；没有峰值分钟内顺序，也没有账户风控效果推断。原mark/funding/arrival/venue/MMR缺口、所有旧STOP保持。

五个合成反例测试后发布协议/代码到远端，再跑一次真实来源算术；另用新STATE做公共冷核验。原source1mCRC/checksum/格点证书复用已有五个公开phase冷核验，本模块本身只读取已公开日特征与真实5mpricepanel。完整协议PROTOCOL.json，来源源码绑定SOURCE_SHA256.txt。

```bash
COIN_CPD_STATE=/workspace/tail-resolution-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/tail-resolution-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/trade-tail-resolution-20261011/test_resolution.py --basetemp=/workspace/tail-resolution-state/pytest
COIN_CPD_STATE=/workspace/tail-resolution-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/tail-resolution-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/trade-tail-resolution-20261011/tail_resolution.py --output /workspace/tail-resolution-state/result
```

预算：1CPU/thread、4GBAS、采样RSS2GB停止、host8GB停止、GPU0/swap0、15GiB保留，120秒算术/公开guard1200秒。0fits/futurelabels/predictionscores/targets/wallets，无搜索或收益门限。重建cloudguard不是原WSL/sharedcgroup证书。
