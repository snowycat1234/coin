独立research/core5-continuous-mark-20261011补独立mark回放输入。复用已有65mark月档和21日修补档，真正缺失50币月：2021Dec、2022Jan–Sep。公开来源哈希仅存证不等于原body恢复；先绑定旧Git来源目录清单和当前sourcemetadata差异，后单worker按月补官方markPriceKlines。403/451等拒绝即停来源，不查询既拒funding/riskAPI。

固定6阶段：复用2021Jan–Nov→Dec2021→Q12022→Q22022→Q32022→复用OctNov2022。每阶段核实际分钟、dailyunion逐字段共同重叠、真实月前23:59markclose/币序/UTC，保存、push核远端、新STATE公共原分钟冷恢复后继续。只新原档上传一次；已有wrapper/sourceparts不重复上传。不用trade high/low或close替mark high/low，不把分钟markclose说成精确资金费charge mark。

mark_source.py薄适配复用既有SourceReader/collector Job+fetch/CRC/checksum/numeric_csv/validate_price及已公开measure，financialkernel不改。DAILY/FIVE_MIN为来源诊断工件；真实1minuteOHLC原source公开引用支持后续lazy原生回放，不重复上传大derivedminute tape。首日Jan1未知过去边界保留NaN，699来源日对齐698valid trade边界日。clock是网格closure，不是历史实际arrival证书。预算PROTOCOL.json，代码绑定SOURCE_SHA256.txt。

```bash
COIN_CPD_STATE=/workspace/mark-continuous-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/mark-continuous-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/core5-continuous-mark-20261011/test_mark.py --basetemp=/workspace/mark-continuous-state/pytest
```

阶段命令在远端协议发布后填入确切sourceSHA并执行，不使用猜测SHA。全程0模型fit/收益label/wallet，数据完成后独立审核下一钱包机制所需fundingunit/精确收费mark/历史风险阶梯/venue等；mark分钟齐全不等于全native认证。已发表upside标签定义只读结论在UPSIDE_LABEL_REVIEW.md，旧STOP保持。
