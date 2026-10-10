# Fixed100-epoch training-adequacy diagnosis

Exactly 80 additional epochs from the frozen20-epoch model; Adam/RNG/permutations retained. Same architecture, training rows, class-balanced objective and predeclared prior correction. Total 2,000 minibatch updates. No early-best selection or hyperparameter grid. Frozen terminal7110f3c69430b98d3b3e192e10f3a5ebc023e64e before evaluation.

Corrected training accuracy increased47.97% to88.86%, training SHORT recall8.49% to88.99%. Thus20 epochs had not exhausted this model's capacity to fit training labels; longer training can learn to select SHORT.

On the already-seen2025 development-forward period, corrected SHORT choices152/344,23correct: recall27.38%,precision15.13%. Overall accuracy23.26% versus20.06% for the constant train-prior action, but logloss worsened from1.41085 at20epochs to2.40725 (prior1.35007), Brier1.18957 versusprior0.76606. On17fixed disjoint windows accuracy17.65% versusprior29.41%, logloss2.75021 versusprior1.30405. Four true short winners, one recalled. Overlapping opportunity regret improves0.02322 to0.01888, but disjoint0.02148 is slightly worse thanprior0.02140. These mixed metrics do not establish incremental forward skill, calibrated probabilities, or profitable switching.

This is evidence of training fit improving without reliable forward generalization, consistent with overfitting/distribution shift. It does not prove the features are intrinsically unpredictable or the selector route impossible. The next useful control must choose training duration/regularization using purged chronological validation inside pre-May2024, and assess payoff margins and feature stability there. Do not repeatedly tune against2025.

No new trading wallets or financial return/APR produced. Previous portfolio results/cost/risk assumptions remain those linked from the parentRESULTS.md. All2025results are seen-development forward diagnostics, not pristineOOS or live.
