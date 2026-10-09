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
