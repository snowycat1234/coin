# Fixed short-only Donchian20/10 development diagnostic

This one recipe was selected after observing June2024. It is seen development
evidence, not OOS, and June profit is not promised. Freeze the source, plan and
preflight publicly before running one fresh10000USDT account from2024-05-01
through2024-07-01 exclusive. Keep its positions and NAV continuous through June1.

The established long expert enters above the prior20-bar high with an SMA200
entry filter and exits below the prior10-bar low. Its original public class
does not short. This explicit new variant enters below the prior20-bar low,
exits above the prior10-bar high, and uses no long-term trend filter. Both
channels exclude the current completed daily bar and use strict inequalities.
As in the established entry hook, “breakout” means close outside the prior
channel; there is no additional previous-close crossing predicate. Exit first,
stay cash that decision, and permit reentry only on a later decision. Retain
200 contiguous actual completed bars, fresh flat signal state at May1, missing
history reset, and no warmup positions.

Current CORE5 E5 uses EQUAL: each active signal has raw signed allocation-0.12,
and inactive budgets stay in cash. The recovered conditional-selector recipe
calls the existing target adapter without an allocation override. Original
saved CORE5 raw arrays independently contain0.12 for every active long signal,
even with one or two active assets. The older D067 ten-asset document describes
ACTIVE_EQUAL; that historical allocation is not the current CORE5 baseline.

Reuse the unchanged MIT Donchian scalar kernel, shared ordered200-bar state and
past30 covariance10% annual scale-down mapper, and the20-day CASH deployment
path with daily budget L1 at most0.1. Engine SHA256 remains
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
Use native delayed/partial capacity-limited entries,5-attempt expiry, risk
reductions first, fee5.5bp/side, halfspread4bp, slippage4bp, signed actual
funding scale1, funding before fills using strictly prior completed mark,
isolated1x/MMR0.005, existing caps, original last-day-zero and paid terminal
closure. Original exchange/publication/account rules remain conditional.

Historical CTA Donchian20/10 short tests were found:2025March–June122days and
2024September–2025June303days, ten assets, inverse-volatility allocation and
different virtual direction-state semantics. They supply prior mechanism
evidence but no reusable same-scope CORE5 May–June2024 account was found. Their
wallets are preserved and are not rerun. The two-account hold diagnostic was
paused before any wallet started.

Three targeted tests verify direct prior windows, strict equality, exclusion of
the current bar, exit-first state, future perturbation and real200-bar warmup.
Preflight independently reconstructs all305 actual signal states/raw weights
and sample-covariance expert targets with zero error. No account was run for
these target checks.

From the repository root, with retained recovery state and dependencies:

```bash
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/donchian_short61.py check --state "$STATE" --output "$STATE/SHORT_PREFLIGHT_RECHECK.json"
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/donchian_short61.py run --state "$STATE" --output "$STATE/donchian-short61/DONCHIAN20_EXIT10_SHORT_ONLY" --plan-commit "$PUBLISHED_PLAN_COMMIT"
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/verify_native61.py --directory "$STATE/donchian-short61/DONCHIAN20_EXIT10_SHORT_ONLY" --state "$STATE" --write
```

One wallet only; no sweep, model fitting, provider download, retuning or pool
promotion. The separate model worker retains ownership of its authorized four
fits. If June is net positive, require a separately predeclared comparison
before any proposal to add this expert to the selector pool.

## Completed account

Exactly one account completed all87840 minutes,64 paid fill legs and915
original funding events. Independent signed journal/NAV/wallet reconciliation
and actual fill/capacity/fee/mark/funding checks passed; maximum NAV and wallet
errors were1.8189894035458565e-12USDT. Terminal positions are paid flat, with
zero liquidations. The engine bytes are unchanged. Saved numerical targets
equal frozen preflight exactly; the original last-day-zero engine convention
serializes positive zero in place of signed negative zero.

| Incremental period | Gross price PnL | Fees | Spread+slippage | Signed funding PnL | Net USDT | Mean/peak gross | Daily annual vol | Minute MDD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| May2024 | -69.47 | 1.02 | 1.48 | +1.18 | **-70.79** | 2.29%/9.68% | 2.72% | 0.83% |
| June2024 | +90.97 | 4.02 | 5.85 | +7.65 | **+88.75** | 11.62%/27.50% | 7.38% | 2.63% |
| Full61days | +21.50 | 5.04 | 7.33 | +8.83 | **+17.96** | 6.88%/27.50% | 5.51% | 2.63% |

June begins with the continuing May wallet NAV9929.209656457846USDT; its
incremental net gain88.7483783427142USDT is0.893811% of that opening NAV.
Positions happened to be flat at May end under the fixed signal rules. No
June1 capital or signal reset was introduced. Full terminal NAV is
10017.95803480056USDT, a0.179580% total return. Normalized full-capital turnover
is0.916059. All actual price/cost/funding contributions are short-side;
long-side gross, fees, execution, funding and net are all zero. No hard-bound
risk reduction was required. Monthly MDD uses the month's opening NAV and
minute snapshots; full MDD includes all native observations.

The saved independent long/cash Donchian baseline made+85.58 in May and-213.99
in June, total-128.40USDT. This is a descriptive comparison of separate complete
wallets. Removing the SMA200 entry filter and changing direction also change
exposure, so it is not a matched-risk single-factor result or an executable
long/short switching payoff.

June net is positive after every charged cost, but May loss leaves only a small
full-period gain. Actual signed funding aids the shorts. Preserve the recipe
without tuning or promotion; a separately predeclared independent-period
comparison remains required before selector-pool inclusion. No further wallet
or fitting was launched, and the hold accounts remain unstarted.

`comparison-donchian-short61/DONCHIAN_SHORT61_RESULTS.json` contains exact
monthly economics/exposure and audit limits. The ordered768KiB-or-smaller
transport parts retain the unchanged full account journals, witnesses,
standalone financial verifier and member hashes. Reassemble with
`reassemble_results.py --root comparison-donchian-short61 --destination NEW_DIR`,
then run `NEW_DIR/verify_native61.py --directory
NEW_DIR/accounts/DONCHIAN20_EXIT10_SHORT_ONLY` with the dependency recipe.
The public actual-source audit additionally requires the already recovered
H1 inputs; raw markets are referenced rather than duplicated.
