独立research/core5-continuous-mark-20261011补独立mark回放输入。复用已有65mark月档和21日修补档，真正缺失50币月：2021Dec、2022Jan–Sep。公开来源哈希仅存证不等于原body恢复；先绑定旧Git来源目录清单和当前sourcemetadata差异，后单worker按月补官方markPriceKlines。403/451等拒绝即停来源，不查询既拒funding/riskAPI。

固定6阶段：复用2021Jan–Nov→Dec2021→Q12022→Q22022→Q32022→复用OctNov2022。每阶段核实际分钟、dailyunion逐字段共同重叠、真实月前23:59markclose/币序/UTC，保存、push核远端、新STATE公共原分钟冷恢复后继续。只新原档上传一次；已有wrapper/sourceparts不重复上传。不用trade high/low或close替mark high/low，不把分钟markclose说成精确资金费charge mark。

mark_source.py薄适配复用既有SourceReader/collector Job+fetch/CRC/checksum/numeric_csv/validate_price及已公开measure，financialkernel不改。DAILY/FIVE_MIN为来源诊断工件；真实1minuteOHLC原source公开引用支持后续lazy原生回放，不重复上传大derivedminute tape。首日Jan1未知过去边界保留NaN，699来源日对齐698valid trade边界日。clock是网格closure，不是历史实际arrival证书。预算PROTOCOL.json，代码绑定SOURCE_SHA256.txt。

```bash
COIN_CPD_STATE=/workspace/mark-continuous-state QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/mark-continuous-state bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/core5-continuous-mark-20261011/test_mark.py --basetemp=/workspace/mark-continuous-state/pytest
```

阶段命令在远端协议发布后填入确切sourceSHA并执行，不使用猜测SHA。全程0模型fit/收益label/wallet，数据完成后独立审核下一钱包机制所需fundingunit/精确收费mark/历史风险阶梯/venue等；mark分钟齐全不等于全native认证。已发表upside标签定义只读结论在UPSIDE_LABEL_REVIEW.md，旧STOP保持。

Official-source holes are explicit: Q3's original strict grid attempt failed and its receipts remain in `failures/Q3_INITIAL`. The gapped source amendment does not relax wallet certification. Its raw cold restore ran from source `8323f8feabc88d419bf0bf376824b24629d8a571`, artifact `075e50d9c9cf7b210b848113962ade220693ca4f`. Check out that source before repeating `cold_gapped.py`; the immutable original and gapped binding manifests are retained.

October reuse exposed the inherited trade-only October source selector. `mark_reader.py` now selects the independently bound family/symbol/URL record from the existing public index. No archive redownload, financial-kernel changes, or trade/mark substitution. Active `mark_source.py` and `cold_mark.py` use an explicit `SOURCE_CURRENT_SHA256.txt` for new phases; old phase source code and manifests reproduce from their recorded Git source SHA. `COMBINE_GAPPED_SHA256.txt` separately freezes the actual-missing-mask join, leaving the original unused combine manifest unchanged.

Final source outcome: `result/COVERAGE.json` records 699 calendar dates, **696 common valid risk dates**, 5,032,773 observed mark minutes, and 27 unfilled source minutes on 2022-07-12/13. Complete minute continuity remains failed. New raw ZIPs total 47,963,120 bytes: 50 monthly originals and 5 daily companions. Six published source phase cold restores passed, including explicit gapped Q3 semantics. The joined daily panel and masks are byte-identical on public restore; zero fits, new forecast labels or wallets ran.

Minimal source-certificate reproduction from this recorded code branch, using a fresh task STATE (all Python stays under `launch.sh`):

```bash
export COIN_CPD_STATE=/workspace/mark-reproduce
export QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE="$COIN_CPD_STATE"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/core5-continuous-mark-20261011/test_mark.py research/core5-continuous-mark-20261011/test_gapped.py research/core5-continuous-mark-20261011/test_combine.py research/core5-continuous-mark-20261011/test_reader.py --basetemp="$COIN_CPD_STATE/tests"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/core5-continuous-mark-20261011/combine_mark.py --commit c4f44417a665ded2c43e6767221efea004d90dd1 --output "$COIN_CPD_STATE/combined" --expected research/core5-continuous-mark-20261011/result/MARK_DAILY_CONTINUOUS.npz
```

Each `phases/*/RECOVERY.json` records its actual scientific source SHA; check out that SHA to reparse its originals with the corresponding `cold_mark.py` or `cold_gapped.py`, using the artifact SHA from its `PUBLIC_RESTORE.json`. Frozen old bindings remain unchanged. Seven original full-grid source invocations include two blocked attempts (Q3 holes and October reader); six completed phases comprise five original full-grid successes and one explicit partial-source resume. Two finite gap checks and the original unit import collision are preserved. Source-only random seed is not applicable. No model STOP, old ledger, or upside label was modified; trade-tail diagnostics neither invalidate the frozen mark-five-minute label nor establish original PnL error.
