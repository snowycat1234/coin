# One prefix-selected static expert benchmark

Choose the largest mature-prefix arithmetic mean of cost-after 21-active-day
standalone returns among VOL, CS and MOM30 short/cash. Use exactly the common
371/462/553/644 labels from the closed direct-contrast study. Original gaps,
full label maturity and paid-terminal exclusions remain intact; no alternative
weighting, lookback, threshold or choice rule. CASH is excluded as a candidate,
including when all means are negative. Expert inactivity and mapper cash remain.

Choices are SHORT/VOL/VOL/VOL for July/October/January/April. They are frozen
before forward evaluation; no forward data enters the choice function. The
constant one-hot request persists for all63 decisions. The unchanged mapper
starts in CASH, takes20 decisions to reach full expert budget (L1<=.1/day),
respects current eligibility and .6 gross/.3 asset caps, and pays final closure.
Each fold is one continuous10k shared CORE5 wallet. Same funding, costs and
charged risk reductions. Existing Static50 and Cash50 are independent controls.

Reuses cached standalone histories and the existing surrogate engine; no
training, new data, downloads or native replay. Four selected paths will be
checked bitwise against their cached controls. The benchmark is not a learned
selector. These repeatedly examined blocks are historical development, not
novel OOS or statistical-strength evidence. Prefix means use overlapping,
state-conditioned standalone labels; they are not realizable switching returns.

[Choices/means/maturity](FROZEN_SELECTIONS.json), [rule/source hashes](PROTOCOL.json),
[duplicate check](DUPLICATE_CHECK.json). Three causal/negative-mean/tie/identity
checks pass. Python3.12/NumPy2.5.3; installed Torch2.6 CPU for surrogate replay,
pytest9.1.1/Ruff0.16.9 for tests. No installation. Through the existing bounded
guards, with checkout/src in PYTHONPATH:

```bash
python -m modules.temporal_prefix_static_baseline.baseline --root CHECKOUT --destination NEW_SELECTIONS.json
python -m modules.temporal_prefix_static_baseline.evaluate --root CHECKOUT --state STATE --selections NEW_SELECTIONS.json --producer-commit FROZEN_COMMIT --destination NEW_OUTPUT
```

The selection file must exist in FROZEN_COMMIT at its public canonical path
before evaluation. Export canonical seven-field E6 native63 requests with
selection/source/context identities, current masks/clocks, fresh cash startup
and paid terminal contract. Native rollout remains NOT_RUN pending a decision.
Stop after this specification.

The four choices and sources were public at `49c0ff4b88286ccb7131af99e88838b4015dc5be` before forward evaluation; all eleven files remotely read back.
Three focused tests pass. All four selected control requests/NAV/targets/
budgets reproduce bitwise, including the exact20-decision ramp and paid close.
Independent checks verify prefix means/argmax/maturity, 252 native request rows,
source identities, masks/clocks/caps, final cash and account PnL/drawdown.
Zero training or downloads; four surrogate replays, zero native rollouts.

## Mature-prefix mean21-day standalone return

All three means use identical windows and own-path cost/funding treatment.
Averages are fractional returns, shown as percentages; overlapping labels
do not establish independent evidence. CASH is never considered.

| Fold | Labels | VOL | CS | SHORT | Frozen choice |
|---|---:|---:|---:|---:|---|
| 2023-07-03 | 371 | +0.0289% | -0.4596% | +0.1055% | SHORT |
| 2023-10-02 | 462 | +0.0595% | -0.7855% | -0.1921% | VOL |
| 2024-01-01 | 553 | +0.6179% | -0.2799% | -0.3065% | VOL |
| 2024-04-01 | 644 | +0.8878% | -0.2116% | -0.4015% | VOL |

## Own-path charged daily surrogate results

Each cell gives net PnL in USDT / maximum drawdown. Capital10,000 USDT
per independent wallet; do not sum equity across folds or control wallets.

| Fold | Choice | Prefix static | Static50 | Cash50 |
|---|---|---:|---:|---:|
| 2023-07-03 | SHORT | -30.89 / 5.21% | -405.67 / 4.62% | -218.47 / 2.67% |
| 2023-10-02 | VOL | +1,168.18 / 1.96% | +950.33 / 1.80% | +472.43 / 0.90% |
| 2024-01-01 | VOL | +877.40 / 1.99% | +394.72 / 1.77% | +189.03 / 1.08% |
| 2024-04-01 | VOL | +110.53 / 2.20% | -198.56 / 2.36% | -116.18 / 1.40% |

Prefix static improves PnL versus both controls in all four development
folds. It does not dominate risk: drawdown exceeds Static50 in three folds
and Cash50 in all four; July remains a loss with5.21% drawdown. No threshold,
weight, lookback or choice-rule alternative was tried. No statistical strength,
novel OOS, stable APR, or native execution claim follows from this screen.

[Full result/accounting](RESULT.json), [independent checks](VERIFICATION.json),
[preservation receipt](PRESERVATION.json). Source-bound native63 request bundles:

- [2023-07-03: SHORT requests/manifest](FOLD_20230703/MANIFEST.json)
- [2023-10-02: VOL requests/manifest](FOLD_20231002/MANIFEST.json)
- [2024-01-01: VOL requests/manifest](FOLD_20240101/MANIFEST.json)
- [2024-04-01: VOL requests/manifest](FOLD_20240401/MANIFEST.json)

Each bundle has REQUESTS.npz, SURROGATE_PATH.npz and RESULT.json, with hashes
and pointers to the unchanged canonical expert context. Public E6 slots/masks/
clocks are preserved; input code/prototype/risk accounting identities are bound.
Native startup is fresh cash10k, previous_quote=None, initial_capacity0; final
paid close uses the existing native63 contract reference from the April handoff.
All requests remain one-hot in the selected non-CASH expert, including the
terminal day; common terminal target forcing closes the actual wallet and pays
costs. Residual mapper CASH during ramp and inactive SHORT targets remain.
No neural checkpoint is required or invented for this zero-parameter policy.

STOP: native replay is NOT_RUN_AWAIT_NATIVE_DECISION. The direct-contrast
experiment remains closed and unchanged. This benchmark has executable own-path
surrogate results; it does not turn standalone spread labels into switching
profits or certify intraday/native fills, margin, reductions, or liquidation.
