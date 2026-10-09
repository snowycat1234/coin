# Exact matched512 weighting pair: two native61 plans

Two new fresh 10,000 USDT wallets use the same cached 2024 May 1–July 1 exclusive
61-day native tapes: `EXP_GRU64_WEIGHT_DATE` first, then
`EXP_GRU64_WEIGHT_MIXED`. Actual frozen exports are pinned at
`d3d57332ca45b7a4443108db21f46abad0e1ac99`, under
`research/temporal-episode-weighting-v2-20261009/native61-requests`.

The producer records **exactly 512 additional updates each**, identical full
model/Adam/RNG initialization SHA256
`0f51bd3316f6e1100de518e8283ef3afb1c1148007bbb4d5fa7e3d1375acaddb`,
the same 13,699-parameter architecture, causal expert inputs and expanded action
pool. Completed base Adam steps are 1292 and new-parameter steps are 512 in both.
All training specification fields match after removing only `algorithm.arm`
and `algorithm.mixing`; their normalized common specification SHA256 is
`bc4a3daac16e5933eda04b2763aaa2ede7e5626be7fbab55f345fba5e7fd44ca`.
Training success means fixed update completion, not demonstrated convergence.

Five original chronological training-wallet lengths are 54/88/62/144/430.
Date coefficients are `n/778`: 6.94/11.31/7.97/18.51/55.27%.
Mixed coefficients are `.5*n/778+.5/5`: 13.47/15.66/13.98/19.25/37.63%.
No days are resampled or dropped. These are loss coefficients, not gradient
shares, capital allocations or native returns. No training is performed here.

[READINESS.json](READINESS.json) checks every hashed bundle member, all original
retained input bytes, exact current expert inputs/eligibility/clocks, and the
corrected E6 contract SHA256
`9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`.
For each actual request path, producer and canonical native E6 mapping produce
bit-identical budgets and targets. Original E5 slots and appended MOM30-short
slot 5 are preserved. No model tensors are loaded and no predictions are rerun.

The unchanged guard-OFF financial engine remains SHA256
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
Costs, actual signed funding, isolated 1x/MMR .005 account, covariance/risk caps,
daily L1 ramp, quantities, lot/capacity/delayed-order execution, reductions and
paid terminal-flat closure are unchanged. Each wallet has one CPU, 6 GB address
space, 600 CPU/wall seconds and a 15 GiB disk reserve. Fresh output directories
and unique request-manifest ledgers prevent duplicate wallets.

Publish the first audited result promptly, then the matched May/June, minute
exposure/drawdown, request/budget and financial comparison. Reuse Cash50,
Static50 and relevant completed accounts as references; never rerun or stitch
them. May–June remains seen development. Daily proxy PnLs are not native results
or acceptance/tuning targets; no OOS/alpha or convergence claim follows.

Readiness uses `prepare_short_expansion61.py --profile weighting512`; execution
uses unchanged `evaluate_requests61.py`, these published plans and the retained
dependency recipe. Exactly two new wallets, zero fits/model inference, market
downloads, old-wallet reruns, trading, deployment or new recipes. Historical
publication and venue/account rules remain uncertified conditional assumptions.
