# Frozen training-only identifiability and margin diagnosis

This diagnoses the old 40-date, 60-feature training design and saved 5 × 61 linear coefficient anchor. No optimizer, parameter tuning, feature selection, evaluation arrays, 2024 outcomes, noise simulations, network access or publication were used. The standalone fixture contains only training dates, features, eligibility and utilities, the saved scaler/coefficients, feature/expert names, and existing source commit a3d9128a41e70142293e5ac236cdf309ce6e4af5. This is a baseline diagnosis; it does not constrain future training to 40 dates or prohibit overlapping training windows or additional years.

## Results

- Ten features are constant: all ten CASH feature columns.
- The standardized 40 × 60 matrix has numerical rank 39 using max(shape) × machine epsilon × largest singular value. Its full coefficient problem is rank deficient. The ratio of largest to smallest retained singular value is 237.75; this is a nonzero-subspace condition number, not a finite condition number for the entire feature problem.
- Effective participation rank is 7.026. Three, eight and sixteen components explain 50%, 80% and 95% of squared singular-value energy. All singular values and the tolerance are in results.json.
- Eighteen nonconstant feature pairs have absolute correlation at least .95. These are descriptive redundancy measurements, not a feature-removal prescription.
- Centered row leverage is .975 on every date, to floating-point precision. Rank 39 spans the entire centered 40-observation space: this saturation makes leverage unhelpful for distinguishing individual dates. It does not establish that all dates are equally influential on fitted decisions.
- Across all 40 dates, the top-versus-runner-up score margin has minimum/median/maximum .001122/.07099/.37193. There are no exact top-score ties. CASH is the top choice on one date.
- The analytical standardized L2 distance to the frozen top/runner boundary has minimum/median/maximum .008852/.63413/4.08391. The three smallest distances occur on 2023-06-16, 2023-11-15 and 2023-11-23; each compares VOL_MANAGED_HOLD with PUBLIC_SMA50_200_SIGNED.
- Thirty dates offer an eligible positive utility above CASH. On 22 of these, the selected choice leaves some positive utility uncaptured. Fifteen selected choices have utility below CASH. Mean selected utility is .00109071 versus mean best eligible utility .00985022; mean uncaptured positive utility above CASH is .00612759. These are training-label utility units, not a portfolio return, annualized result or validation estimate.

## Interpretation and boundaries

The old design has few independent directions carrying most feature variation, exact non-identifiability and some very small decision margins. With an intercept, the augmented design has rank 40 across 61 coefficients per noncash expert, leaving at least 21 coefficient directions per expert unidentifiable from predictions on these rows alone. Regularization can choose among such solutions; it does not add identifying observations.

These facts do not prove underfitting, establish that a smaller penalty would generalize better, or identify optimal features. Training misses are compatible with regularization, a ranking objective that does not directly maximize selected utility, noisy labels, limited signal and other explanations. A causal diagnosis needs a separately authorized and controlled training comparison, followed by evaluation under an appropriate design.

Boundary distance equals the observed score margin divided by the norm of the difference of frozen coefficient vectors, excluding the intercept and holding constant coordinates fixed. It is the exact unrestricted standardized-feature distance for this pair. It is not a market-feasible perturbation, a probability, an uncertainty interval or a guarantee about robustness. Feature dependencies can make this perturbation infeasible; another rival can have a closer decision boundary. Ordinal score margins are not utility differences.

Overlapping training windows can legitimately add training examples; this report does not exclude them. Their dependence should not be mistaken for the same number of independent validation observations. More years may add regime coverage; no claim about their benefit is measured here.

## Reproduction

Run `timeout 120 python diagnose.py` in this directory. Run `timeout 120 python -m unittest discover -s . -p 'test_*.py'` for tests. Five tests pass, including retention of all dates, rank/leverage checks, exact-tie averaging, analytical boundary verification and CASH regret decomposition. No model code is imported. All outputs are generated from the training-only fixture.
