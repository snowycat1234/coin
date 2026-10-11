# Continuous CORE5 development risk data

Completed: **698 continuous valid joint trade risk dates**, 2021-01-02–2022-11-30, measured from5,032,800 actual minute rows. The699th source-calendar day retains its unknown prior close asNaN. All115monthly originals plus10already-published daily repairs are bound; only45missing2022monthly ZIPs were downloaded (76,794,401B). Daily repairs add14,400 actual minutes with **zero common rows**, so there is no numerical-overlap evidence. Existing large sources and2021price panel were referenced rather than duplicated.

Three causal/budget tests pass, five raw-minute public cold phases pass, and the347,153B combined dataset recovers byte/vector-exact from publicGit in freshSTATE. Public training-information covariance/statistics also reproduce exactly without newfits/labels/wallets/originalSTATE access. Two source-interface failures and their fixes are preserved; seven preparation attempts yielded five completed phases. All module resources and environment versions are in `COMPLETION.json`.

`continuous/DAILY_CONTINUOUS.npz` is the usable dataset; `continuous/COVERAGE.json` binds the chain. `information/TRAINING_SOURCE_COVARIANCE.npz` and `information/INFORMATION.json` hold the frozen637day descriptive diagnosis, excludingOctober/November. Five assets have median participation breadth1.60, and fixedBartlett30 stationary-mean information equivalents41–61, rather than3490independent samples. These are not forecast-testESS or profitability evidence. `NEXT_DECISION.md` gives the genuinely different joint-correlation candidate and the precise remaining native gaps. No forecasting plan or target gate has been executed in this data module.

Minimal published verification (from this source checkout and existing environment; freshSTATE paths):

```bash
COIN_CPD_STATE=/workspace/repro698-guard \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/repro698-guard \
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
research/core5-continuous-risk600-20261011/cold_join.py \
--commit c78d60386ac3f81c8014879d0d5197a32cf4f939 --state /workspace/repro698-cold

COIN_CPD_STATE=/workspace/reproinfo-guard \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/reproinfo-guard \
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
research/core5-continuous-risk600-20261011/verify_information.py \
--commit 0d3f9784fc53ae5b7add0c3870e4f8b2dadaa9bf --state /workspace/reproinfo-cold
```

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

For an old phase's raw cold replay, check out that exact phase artifact SHA first: its frozen parser/adapter/verifier bytes are intentionally checked. Final `join.py` can recover and certify all five published phase feature/source references without reparsing raw history; this separate scope is reported explicitly.

`run_phase.py` is the normal acquisition entry: it reserves the previous published byte total plus a whole35MB quarter and bounded8MiB in-flight archive before any HTTP. The lower-level `prepare.py` alone enforces per-phase bytes; the completed first three quarters were also cumulatively bounded by actual Q1/Q2 bytes51,063,650 plus the final35MB phase (<100MB). Independent review identified and corrected this generic orchestration gap before any further acquisition. Cold verification additionally binds its own bytes, all shared validator/date-guard dependencies and both symbol-order fields. Daily repair comparisons with common_rows=0 mean genuine gap filling, with no numerical-overlap evidence implied.

The two meaningful synthetic tests check the missing first boundary and future-suffix invariance, and reject a missing minute. Original official-source validators handle CRC, schema, OHLC, units, duplicates and UTC grid. No economics or model results are implied by source completion. Old HAR/upside-quantile STOP decisions remain frozen; a genuinely different next research protocol can be considered only after coverage and information/sample-size assessment.
