# Result: SHORT signal survives, error costs defeat it

The single purged prefix control supports some SHORT-specific timing association into 2023 and early 2024. It does not establish actionable calibrated/payoff skill. More epochs clearly overfit, so simply training longer is not the fix.

One fresh unchanged 13,699-parameter model trained on 744 mature prefix labels, with a prefix-only normalizer, causal 64-day windows and expert state. Forty-two crossing labels were purged. The fixed 20/100 snapshots were chosen by corrected 2023 logloss, then epoch20 was publicly frozen before the selected-only 2024 audit. No2025 inputs or trading replay were used. These dates are previously seen internal chronological development history, not pristine OOS.

- 2023: epoch20 SHORT precision 48.62% versus prevalence 29.94%; recall 85.44%. Logloss 1.32405 versus prior 1.30705; regret .017649 versus constant VOL .015272.
- 100 epochs: train logloss improves from 1.02681 to .28673, but 2023 logloss deteriorates to 2.54620. SHORT picks expand from181 to272, mostly adding mistakes.
- Selected-only 2024: SHORT precision 17/32=53.13% versus prevalence27%; recall17/27=62.96%. Logloss1.54579 versus prior1.39691; Brier.71844 versus.70508; regret.010992 versus VOL.008594.

The payoff decomposition explains the mismatch. In2024, correct SHORT picks average +.02735 SHORT−VOL utility, while incorrect picks average −.04698. Contributions per all100 rows are +.004649 and−.007047, exactly explaining the net disadvantage. In2023 the corresponding average margins are +.04354 and−.05000. These are hindsight fixed-policy utility units, not tradable returns or profits.

The selected model never picks CASH/CS in either later block. NonSHORT accuracy is52.05% versus VOL71.23% in2024, and CASH per-class logloss5.0796 further hurts calibration.

Uncertainty is large: the fixed disjoint21 grid has17 observations in2023 and only5 in2024. The latter has SHORT precision1/2 with approximate95% interval9.45–90.55%; paired logloss/regret intervals cross zero. All21 phase grids are reported without pooling/selection. Residual dependence remains.

Next useful hypothesis: costly false-positive tails and weak four-way calibration prevent useful allocation despite a SHORT association. A future payoff-sensitive SHORT gate would need its own bounded prefix-only plan; no further fit was run here. Four focused tests, exact checkpoint validators, final Ruff and resource/IO checks passed. Source, complete scores, diagnostics and verified recovery archives are preserved; full wallet tests are NOT_RUN.
