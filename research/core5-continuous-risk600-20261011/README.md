# Continuous CORE5 development risk data

Frozen data preparation only: five Binance USD-M **trade** streams from 2021-01-01 through 2022-11-30. The target is 698 continuous, valid completed-day risk observations after retaining the first day's unknown prior close. This is already-seen development history, not new out-of-sample evidence. Trade risk does not substitute for mark or liquidation risk.

`SOURCE_COVERAGE.json` binds 135 monthly and 31 daily recoverable original archives to public Git objects and official checksum receipts. `HASH_ONLY_PRIOR_RECEIPTS.json` preserves 125 older receipts explicitly without pretending the original minute bodies were recovered. The only planned new downloads are the 45 genuinely missing 2022 Jan–Sep trade months. Reuse SOL/XRP Feb26–28/Apr1–2 daily sources and all 2021/October/November originals. Monthly gaps beyond these published daily repairs stop acquisition; no interpolation or automatic expansion.

`PROTOCOL.json` fixes the calendar, primitives, availability clocks, refusal policy and budget before computation or download. `primitives.py` measures actual 1m/5m RV, positive/negative semivariance, OHLC/extrema and observed trade completeness. No future target, normalization, feature selection, fit or wallet is created. All five symbols share chronological UTC dates. The true previous 23:59 close is carried across months and years; each feature is available at the following 00:00. Actual historical publication/arrival is not certified.

Run each phase in order: `Y2021`, `Q12022`, `Q22022`, `Q32022`, `OCTNOV2022_REUSE`. Commit and push each completed phase, verify its remote SHA, then cold recover before advancing. New original bytes are published once in bounded Git parts; large older archives and the identical 2021 5m panel remain references. Cold verification fetches public indices/code and recovers raw original bytes from pinned **local public Git objects**, into a fresh STATE, without reading the original caches or redownloading providers. This is the precise cold-recovery scope.

Minimal commands (replace the pinned SHA and use a new STATE for every run):

```bash
COIN_CPD_STATE=/workspace/continuous600-run-guard \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/continuous600-run-guard \
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
research/core5-continuous-risk600-20261011/run_phase.py \
--phase Y2021 --state /workspace/continuous600-state/Y2021 --source-commit SOURCE_SHA
```

Later phases also need `--previous /absolute/repo/path/phases/PREVIOUS/RECOVERY.json --previous-commit VERIFIED_PREVIOUS_ARTIFACT_SHA`. Publish with `publish.py --state PHASE_STATE`; after push, use `cold_verify.py --phase PHASE --commit VERIFIED_ARTIFACT_SHA --state NEW_COLD_STATE`, under the same guard.

`run_phase.py` is the normal acquisition entry: it reserves the previous published byte total plus a whole35MB quarter and bounded8MiB in-flight archive before any HTTP. The lower-level `prepare.py` alone enforces per-phase bytes; the completed first three quarters were also cumulatively bounded by actual Q1/Q2 bytes51,063,650 plus the final35MB phase (<100MB). Independent review identified and corrected this generic orchestration gap before any further acquisition. Cold verification additionally binds its own bytes, all shared validator/date-guard dependencies and both symbol-order fields. Daily repair comparisons with common_rows=0 mean genuine gap filling, with no numerical-overlap evidence implied.

The two meaningful synthetic tests check the missing first boundary and future-suffix invariance, and reject a missing minute. Original official-source validators handle CRC, schema, OHLC, units, duplicates and UTC grid. No economics or model results are implied by source completion. Old HAR/upside-quantile STOP decisions remain frozen; a genuinely different next research protocol can be considered only after coverage and information/sample-size assessment.
