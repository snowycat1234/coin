# Matched payoff-sensitive four-way control

One fresh 20-epoch, 240-update fit substitutes a payoff-weighted pairwise logistic loss for the existing CE20 loss. The same 13,699-parameter model, seed, causal 64-day inputs, expert-state block, prefix-only scaler, 744 mature TRAIN rows, batch order, Adam, dropout and gradient clipping remain. No additional regularizer, architecture, threshold, calibration fit, class balancing or SHORT quota is introduced. This is a development experiment on already-seen history, not pristine OOS.

## Exact objective and interpretation

For all six unordered pairs of CASH/VOL/CS/SHORT, let delta = u_i - u_j and z = log(q_i / q_j). The loss is the mean over rows and pairs of:

    ([delta]+ * softplus(-z) + [-delta]+ * softplus(z)) / scale

Here [x]+ = max(x, 0). The single common scale is the median nonzero absolute pair gap across mature TRAIN labels only. It does not clip economic tails or change relative costs. Log preferences use the float64 tiny floor only for numerical safety; there is no economic threshold.

Thus each SHORT/VOL, SHORT/CS and SHORT/CASH confusion receives its corresponding utility gap. Three additional nonSHORT pairs preserve meaningful CASH/CS choices. A winner-versus-runner-up CE weight would not distinguish all these costs. A binary SHORT/VOL collapse discards the other two choices; PLAN contains a TRAIN-only oracle opportunity diagnostic quantifying that sacrifice.

The derivative for each pair logit, before averaging, is abs(delta)/scale * (sigmoid(z) - 1[delta > 0]). Exactly equal utilities contribute zero loss and gradient. A confidently wrong preference keeps a substantial gradient. In contrast, linear expected fixed-policy regret through a softmax multiplies its logit gradient by the action probability and can stall after saturation. Logistic loss also has limits: untrimmed extreme gaps can dominate updates, the unchanged global clip caps the resulting parameter gradient, and the model's shared-score/hierarchical parameterization may not realize every optimal pair ratio simultaneously. There is no guarantee of generalization or better wallet outcomes.

For an unconstrained individual pair, its population-optimal preference odds are E[(delta)+] / E[(-delta)+]; the preferred side matches the sign of E[delta]. These are payoff preferences, not probabilities of the four-way winner. Do not apply the CE inverse-class-weight correction. Proper logloss/Brier are therefore omitted. Decisions use argmax raw q with the original first-coordinate tie rule.

## Data semantics and bounded decision

Labels are frozen sums of 21 daily log1p(netreturn) - 5*min(netreturn, 0)^2 from separately continuous fixed-policy diagnostic wallets. Costs, funding, caps and charged reductions are inherited. A label's horizon start inherits that fixed policy's holdings; these utilities are not reset-at-decision or tradable switching returns. Daily-boundary full-fill assumptions are not minute-native execution. The objective learns preferences for these labels only. Labels mature strictly before their assigned cutoff; 42 crossing labels remain purged. Normalization uses 850 unique valid TRAIN-window dates only.

The reused matched CE20 baseline was selected in the previous experiment; fixing epoch20 now is a development choice inherited from that result. No new epoch search occurs. The objective and its associated decision-score contract are the changed variables, so this is not a test of CE versus utility probability calibration.

Only 2023 controls adoption: mean overlapping opportunity regret must be strictly smaller than both CE20 and constant VOL, and regret on the fixed phase-0 disjoint 21-day grid must be no worse than either. Exact overlap ties fail. This gate is an internal stopping decision, not statistical proof; overlapping horizons and residual dependence remain. All 21 grids are reported without pooling or phase selection. There is no minimum SHORT rate. Failure stops without opening the previous audit predictions or performing new 2024 inference/scoring. A passing selection must be publicly frozen before a single selected-only 2024 development audit. No replacement, further fit or threshold optimization follows that audit. No 2025 IO is allowed.

## Run and recovery

Use the existing coin_runtime Python from the repository, wrapped by coin_single_state/bounded_cloud.py with a unique resource report for every invocation. Limits: one CPU/thread; no GPU/swap; RSS 2 GB, address space 4 GB, host-used 8 GB; 1200 seconds wall/CPU. The following are the inner commands:

1. python -m pytest -q modules/temporal_payoff_pairwise/test_control.py modules/temporal_purged_supervised/test_control.py --basetemp UNIQUE_STATE_TEST_DIR
2. python -m modules.temporal_payoff_pairwise.experiment ready --state STATE --out NEW_OUT --baseline STATE/purged-supervised-prefix
3. Persist PLAN and source. Supply a verified receipt with status=PAYOFF_PAIRWISE_PREFIT_PUBLIC_VERIFIED and exact plan_SHA256.
4. python -m modules.temporal_payoff_pairwise.experiment train --state STATE --out OUT --publication PREFIT_RECEIPT
5. python -m modules.temporal_payoff_pairwise.experiment select --state STATE --out OUT
6. Only if the gate passes, persist SELECTION and provide a receipt with status=PAYOFF_PAIRWISE_SELECTION_PUBLIC_VERIFIED and exact selection_SHA256.
7. python -m modules.temporal_payoff_pairwise.experiment audit --state STATE --out OUT --selection-frozen SELECTION_RECEIPT

Model/Adam/RNG/permutation checkpoints are atomic after every minibatch, cannot overwrite, and resume exactly. Source/data/baseline identities are checked on continuation. Completed evidence cannot be overwritten. Focused tests cover analytic and finite-difference gradients, zero/equal gaps, costly false-positive and false-negative directions, untrimmed tail weights, numerical stability, four-way CASH/CS choices, adoption without forced SHORT, failed-gate audit rejection, and exact atomic-checkpoint/dropout/Adam/RNG resume. The reused original tests cover maturity purges and prefix-scaler causality. Full trading wallet validation is NOT_RUN because this module changes only offline label training/scoring.
