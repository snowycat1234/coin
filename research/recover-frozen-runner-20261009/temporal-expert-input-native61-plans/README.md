# Frozen expert-target/eligibility input ablation: native61 plans

Run exactly two new fresh 10,000 USDT May 1–July 1 exclusive 2024 wallets:
`EXP_GRU64_EXPERT_INPUT_CONTROL` first, then `EXP_GRU64_EXPERT_INPUT_ACTIVE`.
Both actual frozen request bundles are pinned at public commit
`bd0d1d4b9b50fb8547f75f28c166bc445a09e073`, under
`research/temporal-expert-input-20261009/native61-requests`.
No completed wallet is rerun and no model is loaded or fitted here.

[READINESS.json](READINESS.json) verifies all bundle members, original retained
market bytes and the corrected E6 contract SHA256
`9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`.
The common 61×18 expert input packet is byte-bound and exactly reconstructs
current VOL/CS/MOM30-short signed targets divided by fixed .3, followed by
their three eligibility values. Unavailable targets are masked before scaling;
flat remains distinct from unavailable. Its saved availability clocks match
the canonical sources, do not exceed the decision or reported feature clock,
and are not backdated. Control disables this block; active enables it. Producer
source declares identical 13,699-parameter GRUs. Parameter tensors are not loaded.

Original E5 slots and the appended slot-5 short context remain exact.
For **each actual request path**, the source-bound producer private mapper and
canonical native E6 mapper give bit-identical budgets and target fractions.
The guard-OFF financial engine remains SHA256
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
Original costs, actual signed funding, isolated account, covariance/risk caps,
daily ramp, lot/capacity/delayed-order execution and paid terminal-flat closure
are unchanged. Each wallet has one CPU, 6 GB address space, 600 CPU/wall seconds
and a 15 GiB disk reserve.

Control completed 403 additional updates; active completed 350. Both are
`CAPPED_NOT_CONVERGED`, share parent/scaler/training plan/datasets, and retain
their actual 2026 fit timestamps separately from training cutoff clocks.
Unequal update counts and eventual realized exposure prevent an isolated
causal input benefit/failure claim. May–June is already seen development;
daily proxy outcomes are not native results or tuning targets.

Publish and report the first completed audited account before the second, then
preserve their matched monthly/exposure/drawdown/request-weight comparison and
original journals. Readiness is reproducible with
`prepare_short_expansion61.py --profile expert-input`; wallets use the unchanged
`evaluate_requests61.py` with their published request-specific plans and
`requirements-native61.txt`. Unique request ledgers and fresh output-directory
checks prevent duplicate accounts. No provider downloads, fits, model inference,
real trading, deployment or new recipes. Historical publication and venue/account
rules remain uncertified conditional research assumptions.
