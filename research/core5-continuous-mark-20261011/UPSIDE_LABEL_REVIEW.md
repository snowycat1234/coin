只读核对已发表 short-upside-quantile-20261011 源码和冻结协议，0结果数组读取/模型重跑/文件修改；必要独立review由paper_mechanism_review完成。

冻结标签为mark的end5mclose下一UTC日最大上行幅度：y_t=max(0,max_{k=1..288}log(P_mark(t+5kmin)/P_mark(t)))。prepare.py:67–77从实际markPriceKlines1m CSV只取close[4::5]；2022:116–117也明确mark通道。tail.py:19–24构造excursion，训练tail.py:76和诊断diagnose.py:105取excursion[i+1]。下一日00UTC成熟（diagnose.py:103/123），不是实际历史arrival证书。PROTOCOL.json:6已经明确5mclose不能认证minutepeak/liquidation/legacyentryheadroom。

刚完成的trade1mOHLC-vs5mclose差值属于不同价格域，不能当成上述mark标签误差，也不能移植20.42等数值。对同一mark锚点，分钟close／OHLC high最大值不会小于采样5mclose最大值，但差多少要另核mark来源。这是已明确的采样覆盖限制，旧标签按其冻结定义成立；如改mark分钟high，必须另冻结标签与评估，不能偷偷替换旧结果或复活其STOP。

没有因此判定原PnL算错：diagnose.py:129–142的价格代理使用trade端点close回报，没有把path-max标签充当收益；:150明确其非walletprofit/清算结果。本次mark恢复用于之后原生回放数据完整性，不重跑该失败预测器，也不声称补数据自动建立其价值。
