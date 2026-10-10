# Repaired multi-year history: natural vs balanced training

PREFIT ONLY. Two sequential fixed256-update fits, same fresh neutral SHORT initialization, 13,699 parameters, Adam learning rate0.0003, dropout0.1 and unchanged fee/funding/shared-wallet risk kernels. No grid, no best-epoch selection.

1290 active training intervals in three independent paid-close wallets:2020Oct15-Dec31(77),2021Jan1-Dec31(364),2022Jan2-2024Apr30(849). The added2020 sources have actual execution/funding marks; old2022 observation gaps are repaired using official archives. Original1137 studies remain unchanged. Rolling features/targets were rebuilt; training-only scaler uses1357unique rows. No2025 feature or outcome rows are loaded by the training consumer.

NATURAL uses unchanged equal-date utility. BALANCED weights utility dates by inverse square-root frequency of the joint category: five causal past-price regimes × four hindsight best21day fixed-policy utilities (cash/VOL/CS/SHORT). Solve a common scale so mean weight1 while clipping to[0.5,2]. Last20active days without mature21day labels and each paid terminal retain weight1. Hindsight labels are training-only attention weights, never input features, tradable oracle claims, portfolio resets or added independent samples. All chronological state, switch costs and gradients through prior decisions remain intact.

Uniform weights match the existing exact financial VJP; three nonuniform finite-difference probes passed. Original prototype/risk sources are pinned. This is targeted verification, not a complete repository test-suite claim. Per-step atomic model/Adam/RNG snapshots support exact continuation, oneCPU, noGPU/swap,2GBprocess/4GBaddress/8GBhost-used bounds.

After freezing both terminal models, evaluate once on continuous2025 at the natural distribution and disclose both results with existing four controls.2025controls have already been inspected, so this is seen-development chronological forward validation, not pristine out-of-sample. Neither model may train on2025, use its scaler rows, tune epochs or select weights based on its outcomes.

All evidence and exact consumed new inputs are in PREFIT.zip. Original2020minute ZIPs remain locally retained; public recovery contains derived financial inputs, official source URLs/checksums and producer scripts, not those raw37.75MB bytes. No live orders, APR promise or claim of beating Bybit's robot population.
