The user fixed July1–September2 exclusive, 2024, for one frozen-policy transfer
comparison: unchanged April-prefix GRU512, unchanged prefix-static VOL choice,
Static50 and Cash50. [PROTOCOL.json](PROTOCOL.json) fixes their checkpoint,
scaler, original68 source identities, requests and accounting before any policy
inference or economic evaluation. The requested checkpoint commit is
`b8299bc22321b9dadf707f14da83ac40a39b5491`; its checkpoint/scaler bytes match
the retained local files. No fits, scaler updates, alternative intervals or
threshold changes. All four wallets are **NOT_RUN**.

This retains the existing63-decision convention: July1–September1 inclusive,
62 active intervals and paid flattening on September1 at00:01:00.000001 UTC.
Each proposed wallet starts separately with10k CASH and persists throughout.
The final padded price repeats the close; no September2 outcome is consumed.
Daily results would remain an approximate charged-boundary surrogate, not a
minute-native result. The original source bodies, mapper, masks, fees/funding,
L1.1, gross.6/asset.3, risk limit and charged reductions are unchanged.

The [actual coverage audit](COVERAGE.json) finds:

| Required input | Actual retained coverage |
|---|---|
|126 completed daily primitive rows, clocks Apr29–Sep1, raw bars Apr28–Aug31 |126/126 trade closes, premium and funding completeness flags for every original10 context asset |
|Serialized24-feature/mask rows for these clocks |63/126; missing July1–Sep1 rows can be rebuilt from original primitive tables, but were not built or certified |
|63 actual00:01 execution prices per CORE5 asset |1/63: July1 only; July2–Sep1 missing |
|62 actual event/strictly-prior-mark funding intervals per CORE5 asset |0/62 complete; retained event streams stop July1 at16:00:00.001 |

All20 primitive/economic source tables match their original member hashes.
All68 original versioned sources and five model/scaler/manifest/terminal files
plus the frozen static-selection file pass byte-identity checks. The audit
calls only existing read-only funding-window arithmetic; no model or wallet
runner is imported. Valid feature masks do not establish economic completeness.
Original completed-day boundary availability remains a historical proxy;
actual publication times remain uncertified.

Faithful reconstruction is blocked. The unchanged normalizer uses the observed
trade candle open at00:01 and the most recent strictly-past completed minute
mark at each actual funding event. A daily trade/mark candle cannot identify
those values. Daily feature funding values cannot replace quantity-denominated
event funding. No future daily close, synthetic observation or free liquidation
was substituted. New official archive bodies downloaded: **0/30MiB**. Minute
archive acquisition is excluded by this task, so this attempt stops here.

This is project-seen historical transfer, not pristine OOS. The earlier native
tail manifest covers Aug13,2024–Jan2,2025 and overlaps20 decision dates here;
the frozen HGB/teacher/student results already examined that span. Source:
[native storage index at d69e9ac](https://github.com/snowycat1234/coin/blob/d69e9ac94478c5be54cb46c622afec7aaf3c61f7/research_artifacts/native_20261008/INDEX.json),
member `original_inputs/TAIL_MANIFEST.json` in its result ZIP. Only that small
manifest was range-retrieved and CRC-checked; no market archive was fetched.
The published2023 native-data branch supplies July/October2023, not this2024
gap. Previously captured daily source tables also span this requested block.
The April model itself remains trained strictly before April1.

Reproduce the coverage audit using the retained STATE and installed
NumPy/pandas/PyArrow environment pinned in
[requirements-coverage.txt](requirements-coverage.txt), under the existing
one-CPU recovery guard. A fresh environment can install those pins from the
official PyPI index; no installation was needed for this audit.

```bash
PYTHONPATH="$PWD:$PWD/src" taskset -c 3 /workspace/coin/.venv/bin/python \
  research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py \
  --seconds 60 --report NEW_RESOURCE_RECEIPT.json \
  /workspace/coin/.venv/bin/python \
  research/temporal-july-frozen-transfer-20261010/audit_coverage.py \
  --state /workspace/coin-state/work/temporal-two-expert-20261009 \
  --output NEW_COVERAGE.json
```

Receipt records exact repeat, immutable identities, resource use and zero
optimizer/inference/wallet calls. No transfer PnL, model quality, native-replay
value or improvement claim is available. This fixed block is stopped pending
faithful cached derived execution/funding data; no replacement period is proposed.
