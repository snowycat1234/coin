# Source registry and nonduplication review

- Paper: [Generalized Distribution Prediction](https://arxiv.org/abs/2410.23296),
  v2 dated2025-01-28. Definition/equations3.1–3.2.4: one marginal of daily log
  returns in a future window. Quantile evaluation uses22 days; distribution
  metrics use30. Loss sums raw and standardized pinball over future observations.
- [Official code](https://github.com/izzak98/dist-pred/tree/bf0a6554054735448ea02910e0ced335c7481969),
  commit`bf0a6554054735448ea02910e0ced335c7481969`. README declares MIT via link;
  no LICENSE file was found. Code is read as a method reference, not vendored.
  Own minimal architecture uses unmodified installed PyTorch2.6.0+cpu, BSD-style.
- `ta_utils.calculate_log_return(period=2)` changes period to1, so `return_2d`
  really is one-day log return. `DistDataset` uses separate past/future chunks.
  Labels are multiplied by100; standardized labels divide by past scale.
  Cross-sectional code computes EWMA of squared returns (no square root) from
  contemporaneous observations and multiplies by sqrt252, unlike the written
  sigma formula. We use explicit causal daily EWMA standard deviation.
- The paper says validation2018 through2019 and test2019–2024. Current config
  instead says validation[2018-01-01,2019-01-01], test[2019-01-01,2024-01-01],
  with inclusive Pandas slices. Fixed22-day synthetic replay has zero overlap
  in actual labels: last validation labelJan1, first test labelJan23. This is
  a fixture result, not a certification of all original Yahoo assets or
  random15–29 sequences. We enforce disjoint labels and exclusive maturity.
- `result_utils.calculate_crps` compares a CDF with an observation step function
  on linspace(0,1) and averages squared error, although its density routine
  produces a different return grid. It omits the actual return axis/integral.
  Table8's crypto Gaussian0.3544, qLSTM0.4320 and qHybrid0.4179 are the authors'
  reported scores, not independently validated standard CRPS or profit evidence.
- Official `train` assigns best_weights=model.state_dict() without deep copy;
  the adaptation deep copies the selected checkpoint. Original unconstrained
  market scale may be negative; adaptation enforces a positive multiplier.
  The optional auxiliary cheat_quantile_loss is not used. No upstream training,
  Optuna DB or pretrained pickle is executed/loaded.
- Public daily evidence archive at`e0d3400b23842f11f167a63e7d80856d76501de8`,
  SHA`bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30`.
  Reuse exact Git bytes and existing provider receipts. Whitelist daily OHLCV;
  compare close and log1p archived mom1. No fresh raw exchange certification.
- NumPy2.5.3/SciPy1.18.1 BSD-3-Clause, Polars1.44.2 MIT, PyArrow23.0.1 Apache2.0,
  pandas2.3.3 BSD-3-Clause and pytest9.1.1 MIT are existing installed dependencies,
  unmodified. No installs, GPU, fees, credentials, deployment or Library access.

`BRANCH_INVENTORY.json` records all27 remote heads and relevant changed-file
paths. No distribution-prediction/quantile/CRPS experiment was found in branch
paths or matching commit subjects. This is a scoped repository search, not a
claim to recover private/missing historical files. Existing TCN/GRU/Transformer,
E5/selector, path-utility and expert-aggregation experiments solve other targets.

Read saved native baselines from recovery commit546cb9bd: momentum short fixed30
(MAYJUN−64.63, NOV2022+92.26, JAN2023−210.35, OKX86−588.87USDT), Donchian20/10
short (NOV+41.45, JAN0 inactive, OKX−397.51), and SMA50/200/Donchian long pool61
(−10.50/−128.40). These independent10k wallets are cited, never rerun or added.
Expert aggregation's28-wallet report at5346a5c7 concludes STATIC_EDGE_ONLY;
direct path eef4be71 has two frozen fits and does not prove distribution alpha.
The main branch's fixed50% short collateral protection is paused after losses
in2025H1. These results motivate tail/utility checks, not another trend trial.

2021/2023/July2024/Q42024 published native packets were inspected by README/index.
They are reusable if a native economic phase is justified. July2024 omits two
mark minutes per asset; Q4 minute tapes are complete. No raw packs were
redownloaded. Recovery546cb9bd preserves financial sources; original unpublished
Q1/Q2 ledgers remain MISSING and are not claimed recovered here.
