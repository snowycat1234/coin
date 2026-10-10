# Frozen forecast economic relevance diagnostic

One read-only comparison of the existing fixed 21-day CORE5 market-return
forecasts against subsequent VOL-minus-SHORT and VOL-minus-CS outcomes in all
four original folds. Positive forecast favors VOL; zero is the fixed sign
threshold. No fit, retuning, threshold search, data download, model inference,
new economic rollout, or selector change.

Outcomes are NAV[k+21]/NAV[k]−1 on each frozen continuous standalone control
wallet, with its inherited holdings, ramp, all saved costs/funding, eligibility
and endogenous risk reductions. They are daily surrogate marked subperiod
returns, not fresh 21-day accounts, switching profits or native execution.

The original wallet has 62 active intervals and a paid terminal close. Starts
0…41 support 42 full21 active interval windows. Start42 has 20 active intervals
plus paid close; report it separately, retaining all 43 original starts and the
original disjoint starts 0/21/42. The full-active disjoint subset is 0/21 only.
Forecast labels use completed daily closes; saved wallets use 00:01 execution
marks. No outcome-selected exclusions. Statistical effectiveN remains unknown.

Pearson, Spearman with average tie ranks, and sign agreement are reported per
fold. Exact contrast ties are counted and excluded from sign denominators.
Comparisons are the frozen causal prefix-mean forecast, constant VOL, constant
other, and uninformed fair-sign expected50%. Constant correlation is undefined.
No pooled inference or p-values; two or three disjoint spans are extremely few.

Executable: `READ_ECONOMIC_RELEVANCE.py --root CHECKOUT --output NEW_OUTPUT`
through the existing bounded resource guard. Python 3.12, installed NumPy 2.5.3;
pytest 9.1.1/Ruff 0.16.9 for the focused tests. No dependency installation.
Source and input hashes, maturity/fidelity audit and fixed choices are recorded
in [PROTOCOL.json](PROTOCOL.json) before any association calculation.

The fixed calculation is complete: [344 paired rows](PAIRED_ASSOCIATIONS.csv),
[all metrics and input hashes](RESULT.json), [independent verification](VERIFICATION.json).
The source/protocol/input audit was public at 77e8326cb69a6ebe5c77bb2dda41519405e51270
before associations; all eight changed files were remotely read back.
Three focused tests pass. NumPy read/calculation completed in 0.252 seconds
under the one-CPU/1 GB/120 second guard; the 0.25 second sampling interval is too
coarse to establish peak physical memory. No new fit/inference/rollout/download.

## Full21 active interval windows:42 per fold

| Fold | Contrast | Pearson | Spearman | Sign agreement | Prefix mean | Always VOL | Always other |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023-07-03 | VOL−SHORT | -0.028 | -0.030 | 61.9% | 71.4% | 28.6% | 71.4% |
| 2023-07-03 | VOL−CS | +0.063 | -0.006 | 40.5% | 50.0% | 50.0% | 50.0% |
| 2023-10-02 | VOL−SHORT | +0.893 | +0.876 | 54.8% | 0.0% | 100.0% | 0.0% |
| 2023-10-02 | VOL−CS | +0.091 | +0.103 | 54.8% | 4.8% | 95.2% | 4.8% |
| 2024-01-01 | VOL−SHORT | +0.218 | +0.171 | 61.9% | 61.9% | 61.9% | 38.1% |
| 2024-01-01 | VOL−CS | +0.403 | +0.161 | 92.9% | 92.9% | 92.9% | 7.1% |
| 2024-04-01 | VOL−SHORT | +0.651 | +0.599 | 50.0% | 61.9% | 61.9% | 38.1% |
| 2024-04-01 | VOL−CS | +0.635 | +0.633 | 66.7% | 78.6% | 78.6% | 21.4% |

Uninformed fair-sign expectation is 50% in every row; constant correlations
are undefined. No exact contrast ties or zero forecasts occurred.

## Fixed full-active disjoint starts 0/21: 2 per fold

| Fold | Contrast | Pearson | Spearman | Sign agreement | Prefix mean | Always VOL | Always other |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023-07-03 | VOL−SHORT | +1.000 | +1.000 | 50.0% | 50.0% | 50.0% | 50.0% |
| 2023-07-03 | VOL−CS | +1.000 | +1.000 | 50.0% | 50.0% | 50.0% | 50.0% |
| 2023-10-02 | VOL−SHORT | -1.000 | -1.000 | 100.0% | 0.0% | 100.0% | 0.0% |
| 2023-10-02 | VOL−CS | -1.000 | -1.000 | 50.0% | 50.0% | 50.0% | 50.0% |
| 2024-01-01 | VOL−SHORT | -1.000 | -1.000 | 50.0% | 50.0% | 50.0% | 50.0% |
| 2024-01-01 | VOL−CS | +1.000 | +1.000 | 100.0% | 100.0% | 100.0% | 0.0% |
| 2024-04-01 | VOL−SHORT | +1.000 | +1.000 | 0.0% | 0.0% | 0.0% | 100.0% |
| 2024-04-01 | VOL−CS | -1.000 | -1.000 | 100.0% | 100.0% | 100.0% | 0.0% |

Uninformed fair-sign expectation is 50% in every row; constant correlations
are undefined. No exact contrast ties or zero forecasts occurred.

## Original disjoint starts 0/21/42: 3 per fold, third span partial

| Fold | Contrast | Pearson | Spearman | Sign agreement | Prefix mean | Always VOL | Always other |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023-07-03 | VOL−SHORT | -0.715 | -0.500 | 33.3% | 66.7% | 33.3% | 66.7% |
| 2023-07-03 | VOL−CS | -0.671 | -0.500 | 33.3% | 66.7% | 33.3% | 66.7% |
| 2023-10-02 | VOL−SHORT | +0.776 | +0.500 | 66.7% | 0.0% | 100.0% | 0.0% |
| 2023-10-02 | VOL−CS | +0.210 | -0.500 | 33.3% | 33.3% | 66.7% | 33.3% |
| 2024-01-01 | VOL−SHORT | +0.569 | +0.500 | 66.7% | 66.7% | 66.7% | 33.3% |
| 2024-01-01 | VOL−CS | +0.769 | +1.000 | 100.0% | 100.0% | 100.0% | 0.0% |
| 2024-04-01 | VOL−SHORT | +0.977 | +1.000 | 33.3% | 33.3% | 33.3% | 66.7% |
| 2024-04-01 | VOL−CS | +0.898 | +0.500 | 100.0% | 100.0% | 100.0% | 0.0% |

Uninformed fair-sign expectation is 50% in every row; constant correlations
are undefined. No exact contrast ties or zero forecasts occurred.

Two-point nonconstant correlations are necessarily ±1 and carry almost no
information; three spans are also far too few for inference. The third span
is conditional on the original paid-close boundary and has 20 active intervals.
All 43 saved-path-window metrics are retained in RESULT.json.

The cached controls all remain eligible 63/63 days. SHORT targets are entirely
flat on 8/42/17/14 days in July/October/January/April; flat SHORT remains an
outcome, never a discarded observation. CS has 1/1/7/3 endogenous risk events
and charged reduction costs 0.321982/0.659110/1.721870/1.401540 USDT. Reading
saved NAV retains these costs and reductions; a target-only price formula
would omit them. VOL and SHORT have zero such risk events. All original
full-wallet fees, spread, slippage, funding and risk costs are recorded in
PROTOCOL.json/RESULT.json; terminal flattening is paid, never free.

VOL-minus-SHORT rank association is strong in October and April, weak in
January and absent in July. VOL-minus-CS is near zero in July/October and
clearest in April. Sign agreement improves on the frozen prefix mean only
in October, where constant VOL already agrees 95.2% (CS) and 100% (SHORT);
January agreement simply matches the positive constant, and July/April lose
to the prefix mean. Positive correlation alone does not imply successful
expert choice at the fixed zero threshold. Forecast calibration and unequal
standalone path state can affect this comparison; no adjustment was fitted.

This provides conditional ordering evidence in some periods, but no stable
incremental choice evidence across folds, switching profits, native result,
pristine OOS, or statistical strength. Prior negative selector/next-day
findings remain byte-identical. One bounded implication: retain the selector;
any later chronological validation should preregister relative-expert outcomes
and constant controls alongside market-forecast error/calibration. No further
validation, thresholds, training or policy changes were run here.
