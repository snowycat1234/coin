# Fixed minimum minute-conditional joint selector

Completed: **STOP_FIXED_PAIRED_INFORMATION_GATE**. [Full result](result/RESULT.json), [attempt count](result/ATTEMPT.json), saved models/vectors and [exact public restoration](PUBLIC_RESTORE.json) are published. One historical attempt completed exactly3 fits on181 disjoint mature intervals (361 complete candidate dates). No rescue fit or parameter search followed.

|Seen2022 diagnostic|Common statistical dates / original calendar|C MSE increase vs A|C MSE increase vs B|
|---|---:|---:|---:|
|Jan2–Jun29, maturity beforeJul1|171 /179|0.8107%|0.4787%|
|Jul2–Nov29, maturity beforeDec1|147 /151|1.9508%|1.6782%|

All4 registered comparisons fail. H1 paired95% differences cross zero; H2 both intervals are strictly negative for baseline-minus-C loss, supporting worse C prediction on this fixed diagnostic. These are common-label information scores, not complete account returns. Separate one-day reference controls have negative mean utility for VOL and CS in both blocks; the training-only best family is CASH. No per-date oracle payoff or combined independent full-capital profits is reported.

This is a historical crypto adaptation and information diagnostic, not an original paper replication or pristine out-of-sample evaluation. The original Slow Momentum/CPD experiment and previous standalone correlation/flow STOPs remain unchanged. Frozen design: [PROTOCOL.json](PROTOCOL.json).

Source parity passed before labels or fits: original market13 retains its broader aggregate semantics; original CASH/VOL/CS targets, expert masks and asset masks equal all30 saved November2022 producer rows exactly. Actual2020 warmup is retained. Source arrays stream only the prefix through2022Dec1; no2023/24 feature or outcome values are parsed. Source preparation uses published Git objects, no provider download.

One attempt, three original UtilitySelector Ridge(alpha30) fits, seed811134, train-only scaler/utility scale and identical disjoint mature2021 intervals. A=market13+pool intents/masks (46columns); B=A+minute RV excess/adverse signed semivariance (48); C=B+CS-signed five-minute crosscovariance share (49). No search, neural network, alternative horizon, feedback feature, or ex-post expert-winner label. Train maturity strictly before2021Dec31; logical fit availability2022Jan1. Fixed2022H1/H2 diagnostics use calendar blocks with labels mature beforeJul1/Dec1. Paired non-CASH utility MSE must improve2% against both controls in both blocks, with7-calendar-day1000-replicate bootstrap lower95% difference above zero.

One-day labels reuse `modules.collector_research.pipeline.economics.replay` and the original `reference_utility`. They pay entry and terminal costs0.00135 per side, retain original funding coefficients under **conditional raw-as-fraction**, and use the conservative original two-minute maturity delay. This daily quantity proxy does not certify funding units, exact charge marks, venue, arrival, maintenance margin, intraminute liquidation, execution capacity, or terminal paid-flat native behavior. Its daily MDD is not an intraday risk measure. No native research wallet is run here.

2021 price source has365 rows; independent original funding interval source has364. Dec31 funding remains NaN with false completeness, never zero. Actual27 missing mark minutes from the independent mark source are outcome UNKNOWN when owned. Training can exclude matured unknown labels; evaluation keeps every calendar prediction and target. Future quality masks never route to cash or erase previously owned intervals. Native financial acceptance remains blocked by missing marks, historical contract certification, and the existing compatibility terminal residual660.0772133978703USDT.

Public inputs are small source-derived projections with independent original member SHA bindings in `input/PREPARATION.json` and `INPUT_SHA256.txt`. Large original ZIPs remain referenced by their published Git SHAs. Source preparation attempts: first source-only preflight passed, three cost/schema checks stopped before labels/fits, final preparation passed. All failed receipts and protocol/source manifests are retained; failures did not select model settings. Prefix fixture had one initial NumPy API failure before correction. Nine current tests passed (two prefix and seven mechanism/financial/causality tests); the scaler counterexample runs two synthetic Ridge fits, separate from the three historical scientific fits.

Run all Python through the published reconstructed cloud guard (1CPU/thread,4GB address space,2GB sampled aggregate RSS stop,8GB host stop,GPU0/swap0,15GiB free-disk reserve). This guard is not the original WSL shared cgroup. Source600s/1GB STATE; diagnostic120s. No lock body, account secrets, credentials, Library, live trading, deployment, payment, main changes, force push or other distribution-research file changes.

Minimal test command:
```bash
COIN_CPD_STATE=/workspace/selector-tests QUANT_ROOT=$PWD QUANT_STATE=/workspace/selector-tests \
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q \
research/minute-conditional-selector-20261011/test_prefix.py \
research/minute-conditional-selector-20261011/test_experiment.py \
--basetemp=/workspace/selector-tests/pytest
```

Minimal zero-fit reproduction from this branch and a fresh STATE:
```bash
COIN_CPD_STATE=/workspace/selector-cold QUANT_ROOT=$PWD QUANT_STATE=/workspace/selector-cold \
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
research/minute-conditional-selector-20261011/experiment.py \
--state /workspace/selector-cold/VERIFIED \
--source-commit 4c5c727bf8dc50a6538a474a0c6bc3690f481b3f \
--artifact-commit 71c892964d769cc16458a74652370134a2a98039
```

To reproduce the three fits, use an isolated clean checkout of `4c5c727bf8dc50a6538a474a0c6bc3690f481b3f`, the same command with a different fresh STATE and without `--artifact-commit`. That code SHA was pushed and remote-verified before any historical label/fit. Result artifact71c892964d769cc16458a74652370134a2a98039 was pushed and verified before cold restoration. Code/checkpoint/input identities are in `FIT_SOURCE_SHA256.txt`, `RESULT_SHA256.txt`, `INPUT_SHA256.txt`; installed versions are in `RUNTIME.json`.

Original run3.696359s (guard8.198516s; maximum sampled descendant RSS201715712B). Exact cold restore3.170874s, zero new fits/attempts/provider downloads/native wallets/private input paths. The first cold command contained an incorrectly transcribed SHA and Git refused before loading input/result values; that failed guard is preserved in `COLD_COMMAND_FAILED_GUARD.json`. The successful cold used the remote-verified SHA. This command failure did not change science or models.

All3342022 calendar target rows remain. Each arm's **prospective** target interval reaches the genuine ETH missing mark at2022Jul12 12:58UTC completion; `STOP_UNKNOWN_OWNED_MARK` describes the uncertifiable path if that target is held, not an observed native fill. No native candidate account is run. Target gross/risk and target changes in RESULT are intent diagnostics, not actual exposure/turnover/alpha. Native paid-flat compatibility STOP remains a separate real unchanged-kernel result in [the composite module](../composite-mark-replay-20261011/README.md).

Original raw source reconstruction uses code checkout3efa8d734b0ce04c38860b8af26aa5d75285f548 and `prepare_selector.py --state /workspace/<fresh-path> --source-commit 3efa8d734b0ce04c38860b8af26aa5d75285f548` under the same guard. That old checkout is required for immutable source bindings. The raw reconstruction only reads published source Git objects, while the minimal cold above restores small verified projections.
