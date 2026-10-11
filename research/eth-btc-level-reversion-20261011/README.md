# Fixed ETH/BTC level convergence: STOP

One independent frozen mechanism after32-head/575-strategy-blob history review. Protocol published4996fcac; runnable source/test passed and remotely verifiedd58016c32227371c097058f6a6096b62152ccba9 **before first historical fit**. This is a mechanism adaptation, not Slow Momentum with Fast Reversion replication. Fixed ETH/BTC pair comes from major liquid recovered coverage, not exclusion of losing DOGE. No pair, lag, threshold or holding-window search.

2020 calibration uses366 completed price observations; one intercept/elasticity OLS and training-only normalization. β=1.29128850, residual σ=.16419847. Fixed Engle–Granger maxlag1/autolagNone p=.79576060 fails the prespecified .05 gate (conditional I(1) assumptions; cannot prove every relation absent). Evaluation uses50 nonoverlapping seven-day mature Monday labels, Jan11–Dec20 2021, final maturityDec27, first evaluation embargo10days. Historical training/development, already seen; no pristine OOS claim.

|Active development half|n|Reversion seven-day gross proxy|Paired proxy vs spread momentum|After27bp entry roundtrip proxy|
|---|---:|---:|---:|---:|
|H1|17|−8.9536bp|+29.8190bp|−17.1564bp|
|H2|25|−9.3351bp|−25.4594bp|−21.2845bp|

Proxies use beginning target weights and simple seven-day price returns; these are not shared-wallet returns and do not invent funding or spendable oracle收益. Pooled -z/forward-spread correlation+.19253 does not rescue the failed stationarity and half-year gates. Same pair/common activity mask, past30 covariance, abs.3/gross.6/10% risk algorithm; actual future perturbation changes past targets by0. Six gates pass/four fail. **STOP_FIXED_ETH_BTC_LEVEL_REVERSION; economic wallets NOT_RUN by frozen gate.** No forced fee/funding backtest, no rescue experiment. Old BTC residual four-wallet STOP remains unchanged.

Actual scientific attempt1: primary calibration OLS1 + fixed cointegration-test internal OLS2, prefix refits0, neural0, historical new wallets0. SeedNONE (deterministic); unused planned bootstrap811107. Complete guarded diagnostic3.8243seconds, sampled RSS191,844,352B; timing inside model procedure .0991seconds excludes imports and must not replace guard total. Single CPU/thread, GPU0, swap0. Reconstructed cloud guard (no shared cgroup claim), fixed resource limits/receipt retained. Three focused causal/identity/missing/cap fixtures pass; separate financial54 pass. Earlier3 level fixtures were rerun after adding symbol identity rejection; this is verification, not historical scientific retry.

Data/source binding: existing Git e0d3400b public archive bdbcdc48 reused; only BTC/ETH daily dt/close/completeness <=2021 projected; no2023/24 arrays or locked2026 body. Calibration inputs, entire projected726x2 price matrix,350daily two-asset target vectors per arm (1400scalar weights total), parameters, matured labels and all result/source hashes are public in `results/`. No new market-provider download. Dedicated STATE statsmodels0.14.5/patsy1.0.1 installed anonymously via uv; no shared venv change. Initial missing-package check and no-pip install command stopped before fit and are retained; successful uv setup receipt retained.

Full first-run reproduction requires the existing repository environment, Git data object e0d3400b and a fresh STATE:

```bash
git worktree add --detach /workspace/coin-level-repro d58016c32227371c097058f6a6096b62152ccba9
cd /workspace/coin-level-repro
COIN_CPD_STATE=/workspace/level-repro-install QUANT_ROOT=$PWD QUANT_STATE=/workspace/level-repro-install bash research/slow-momentum-cpd-20261011/launch.sh uv --no-config --no-cache pip install --python /workspace/coin/.venv/bin/python --target /workspace/level-repro/dependencies --no-deps --index-url https://pypi.org/simple statsmodels==0.14.5 patsy==1.0.1
COIN_CPD_STATE=/workspace/level-repro-guard QUANT_ROOT=$PWD QUANT_STATE=/workspace/level-repro-guard bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/eth-btc-level-reversion-20261011/diagnose.py --dependencies /workspace/level-repro/dependencies --output /workspace/level-repro/diagnostic --source-commit d58016c32227371c097058f6a6096b62152ccba9
```

Minimal saved-result recovery (zero new fits/wallets), using the current branch launcher:

```bash
COIN_CPD_STATE=/workspace/level-cold-guard QUANT_ROOT=$PWD QUANT_STATE=/workspace/level-cold-guard bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/eth-btc-level-reversion-20261011/cold_verify.py --commit 100b905fde56290f262c04d6f96e27fa3f67b35c --directory /workspace/level-cold-restored
```

Actual cold check ran a script downloaded from that public commit in a fresh STATE. Seven source bindings and five result artifacts restored from public GitHub URLs; original study workspace/STATE open attempts0. Independently checks saved OLS normal equations without refit, all700arm-day target vectors (1400weights) and50labels; maximum target error7.77e−16/label error1.78e−15. Cointegration statistic is restored, not statistically re-fitted. `PUBLIC_RESTORE.json` is the receipt. No remaining engineering blocker; this fixed scientific mechanism failed. Native2021 margin tiers, fee reserve and funding publication/unit certification remain limitations for any later wallet experiment.
