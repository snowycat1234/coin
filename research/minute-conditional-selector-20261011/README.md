# Fixed minimum minute-conditional joint selector

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

Fit/cold commands will bind the exact published code and result SHAs after completion; cold restoration regenerates labels, predictions, budgets, target risk and scores from public inputs/models with zero new fits. Original raw source reconstruction uses code checkout3efa8d734b0ce04c38860b8af26aa5d75285f548 and `prepare_selector.py --state /workspace/<fresh-path> --source-commit 3efa8d734b0ce04c38860b8af26aa5d75285f548` under the same guard. That old checkout is required for immutable source bindings.
