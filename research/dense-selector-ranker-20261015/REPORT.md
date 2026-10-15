# Dense-training mechanism ablation

## Result

The one frozen dense301 fit converged and worsened decision quality against the immutable original40 ranker on this repeatedly seen 2024H1 development period. This result does not establish that more data generally hurts: this changes overlapping training-date coverage and its necessary training-only scaler, with all other model choices fixed. It supplies no fresh out-of-sample or deployment evidence.

| Fixed 22 disjoint diagnostic dates | Dense301 | Original40 | Saved Ridge | Fixed CASH |
|---|---:|---:|---:|---:|
| Mean chosen utility | -0.002518096 | -0.000891149 | -0.002061853 | 0 |
| Mean oracle regret | 0.013726166 | 0.012099219 | 0.013269923 | 0.011208070 |
| Pooled pairwise accuracy | 57.1429% | 63.8095% | 62.5397% | N/A |

Dense301 minus original40 mean chosen utility is -0.001626947. Dense301 wins on 4 dates, loses on 6, ties on 12, and changes the chosen action on 10 of 22 dates. Relative to saved Ridge, the dense mean difference is -0.000456243 (7 wins, 7 losses, 8 ties). Dense301 chooses CASH on none of these dates; original40 chooses CASH once, Ridge five times. Utilities are the unchanged expert-label decision metric, not realized portfolio returns; no annualization or significance claim is made.

| All 176 mature dates (overlapping descriptive diagnostic) | Dense301 | Original40 | Saved Ridge | Fixed CASH |
|---|---:|---:|---:|---:|
| Mean chosen utility | -0.005157068 | 0.000111642 | -0.001872061 | 0 |
| Mean oracle regret | 0.016838306 | 0.011569596 | 0.013553299 | 0.011681238 |
| Pooled pairwise accuracy | 53.7549% | 60.4348% | 56.6798% | N/A |

On all176, dense301 minus original40 mean chosen utility is -0.005268711 (21 wins, 56 losses, 99 ties; 79 different choices). All 182 scoring states, including the six immature rows without outcome scoring, and all mature row-level labels and decision metrics are in RESULTS.json. No rows were selected after seeing this outcome.

## Fixed design and admission

301 unique, ordered training dates run 2023-01-15 through 2023-12-17. All labels are strictly mature before 2023-12-25 00:00 UTC, maintaining the seven-day embargo before simulated 2024-01-01 fit availability. The exact original 40 disjoint training rows are retained as an identical subset and separately checked for disjoint label windows. This supports the original minimum-40 admission, not a minimum-80 disjoint family gate. Neither 301 overlapping dates, six experts nor the pair count creates independent samples. The selected 22 evaluation dates were fixed before this ablation and remain descriptive diagnostics on seen DEV.

Only training density and its necessary training-only scaling changed. The 60 features, six experts, utility labels, 305 free coefficients (5 by 61), CASH-zero anchor, penalized intercepts, equal-date weighted ordinal pairwise logistic loss, lambda 1, zero initialization, and deterministic L-BFGS-B settings are unchanged. Population mean/std uses all301 training rows alone, with zero-variance columns mapped to zero. Exact label ties are excluded; zero-pair dates retain their date weight. CASH remains the original40 fixed baseline and was not reselected on dense labels.

## Fit and verification

Exactly one actual dense-data fit started at 2026-10-15T02:15:10.172799+00:00. It was accepted after 10 iterations and 12 function evaluations; gradient infinity norm 1.3766835154499502e-08. Total objective 0.6764521672495656 = data loss 0.6639571629373973 + penalty 0.01249500431216833. Stage elapsed 0.120954669 seconds within the 120-second cap, CPU affinity one core, both BLAS pools one thread. Full receipt and optimizer output are retained. No failures occurred and there was no restart, second actual fit, post-result tuning, new family, wallet, or execution test.

23 tests passed before the fit and again afterward. These include synthetic semantics/gradient tests plus dense-overlap acceptance, strict maturity rejection, duplicate rejection, unchanged evaluation and original40 row identity, train-only scaling, and evaluation leakage rejection. Synthetic optimizer tests are separate from actual-data fitting. Saved-coefficient exact reproduction passed without optimization. A separate verification script checks both saved-coefficient prediction arrays, training scaler, direct objective/gradient, independent chosen-utility arithmetic and paired metrics. Numeric array checks allow tight cross-platform floating-point tolerance; the runner additionally passed same-environment exact saved-result reproduction. Pre-fit checks matched old40 predictions and Ridge predictions to their immutable earlier outputs exactly.

## Reproduction and publication boundary

This directory contains only the clean new runner, derived data, frozen original40 controls, coefficients, results, tests, protocol and receipts. CODE_DIFF.txt records the narrow changes from the prior runner; the prior experiment was not modified. The frozen original40 coefficients and original40 inputs are controls only and must not be refitted. The original saved Ridge predictions are included in the unchanged evaluation fixture, without fitting Ridge. Private source paths, source fingerprints and archives are excluded. Nothing has been uploaded, published or traded.

The numerical outcome is a negative density-only mechanism result within this protocol. A future evaluation needs explicitly designated source years, past-only rolling-origin development with mature labels and embargo, and a genuinely uninspected later/prospective final evaluation. This run inspected no locked future data or unknown holdout and does not support a claim of 1,000 causal eligible dates.
