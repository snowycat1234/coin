# Two authorized frozen short-expansion native61 evaluations

These plans bind the real exports at
`7059e955306a5285316b58f7d38a26f917cdb116`, under
`research/temporal-short-expansion-20261009/native61-requests`.
The primary comparison is **EXP_GRU64_CASH_MOM30_SHORT versus its continued
EXP_GRU64_CASH_CONTROL**, each with fresh 10,000 USDT on the same 61-day
May 1–July 1 exclusive 2024 tapes. Existing baseline wallets are reused.

[READINESS.json](READINESS.json) verifies every hashed bundle member, the
corrected contract `9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`,
and all original retained input bytes. Both raw request exports independently
produce **bit-identical budgets and targets** through the source-bound producer
private five-coordinate mapper and the canonical native E6 mapper. The original
E5 target/mask/clock slots are unchanged. Slot 5 is exactly the retained
`MOMENTUM30_SHORT_ONLY` payload, development SHA256
`89183eb92bd45b65a1209aa139f80964cc013c62015a803336db7a7bbd90840d`;
training SHA256
`64accfc82f78034af0da48561ef7e2fabfc8712760066860194e3d2bce9e382d`.
No model is loaded for this check.

Control completed 395 expansion updates; short completed 374. Both are capped,
not converged, and share the parent checkpoint, scaler, training plan and
dataset. Their update counts and future realized risk are unequal. May–June
is already seen development, not OOS. The previously reported daily proxy
outcomes are not native results or acceptance targets.

The source-exact guard-OFF engine remains SHA256
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
The plans retain actual signed funding, original costs, risk caps, covariance,
lot/capacity/delayed-order execution and paid terminal flattening. Each wallet
has one CPU, 6 GB address-space limit, 600 CPU/wall seconds and a 15 GiB disk
reserve. Run the control once, report and preserve its completed audited result,
then run the short once. Duplicate request ledger identities and existing output
directories stop execution.

Use [prepare_short_expansion61.py](../prepare_short_expansion61.py) with the
retained state and hash-verified bundles to reproduce readiness into a fresh
directory. Execute the published request-specific plans with the existing
[evaluate_requests61.py](../evaluate_requests61.py) and
[dependency recipe](../requirements-native61.txt). No training, model inference,
provider download, existing wallet rerun, live deployment or account action is
authorized by these plans. Historical publication and venue/account rules remain
uncertified conditional research assumptions.
