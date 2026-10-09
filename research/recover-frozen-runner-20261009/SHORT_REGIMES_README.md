# Frozen short20/10 cross-regime challenge

Predeclare exactly three fresh independent10000USDT native accounts: November
2022 (Nov1–Dec1 exclusive), January2023 (Jan1–Feb1 exclusive), and OKX2026
July15–October9 exclusive86days. Keep the published short-only20/10 expert
unchanged: strict prior20-low entry, prior10-high exit, no SMA200 filter,
200 real contiguous completed bars, exit first/no same-day reentry, CORE5
EQUAL raw-0.12 per active asset without inactive redistribution, causal30-day
covariance10% scale-down, fresh CASH20-day deployment, unchanged account/caps,
capacity/fees/slippage/funding, and original paid terminal convention.

All three actual inputs and causal warmups passed before any wallet started.
The bear/recovery bundle at public commitd69e9ac94478c5be54cb46c622afec7aaf3c61f7,
`research_artifacts/e5_bear_recovery_20261008/INDEX.json`, reconstructs archive
SHA256`98e38bc3f0e6a16fd51a63be880371882d4e2b52df1d8ec5a39963721d2d2bb8`.
Its included offline normalizer recreated all20 minute Parquets with exact
registered hashes. Original daily/funding bytes and evidence are retained.
November has525 actual funding events, including165 SOL events; preserve its
actual intervals and millisecond timestamps. January has465 actual events.
OKX retains all430 resolved asset-day shards and1290 actual funding events,
including the published SOL archive precedence and preserved API evidence.
No exchange downloads, synthetic fills or substituted warmup are permitted.

The plan binds separate immutable account directories, one CPU,6GB maximum,
600seconds per wallet and15GiB free disk reserve. Source/plan/preflight must be
committed and publicly read back before the first account. Serial wallets
prevent competing resource allocations. Report zero activity truthfully:
January preflight has no short signals; an inactive cash account is not alpha.

These periods are known research history. The2026 account is a conditional OKX
robustness challenge on a previously seen period, not pristine OOS or certified
native OKX settlement. The account remains the unchanged conditional Bybit
isolated1x/MMR0.005 contract. No parameters, risk limits, asset pool, models or
existing VOL/CS contexts change after these outcomes. Both hold diagnostics
remain unstarted. Selector promotion and new training remain out of scope.

Generate a separate short-expert target/eligibility payload on the exact frozen
778 training dates and61 development dates. Training signals start fresh flat
at the first frozen training date and advance on every intervening calendar
day, including days without mature financial outcomes; economic episode
boundaries do not reset virtual signals. The frozen strategy resets at missing
history and exits. Development starts fresh flat at May1, matching short61.
Only causal unramped expert targets, raw signs, eligibility, source hashes and
completed-bar availability are emitted. Native ramp and paid terminal closure
remain execution policies. Original three-slot context bytes remain immutable;
no labels, fitting or pool expansion is performed.

Reproduce using retained/public recovery bundles and the dependency recipe:

```bash
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/recover_short_bear.py --state "$STATE"
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/short_regimes.py check --case NOV2022 --state "$STATE" --output "$STATE/NOV_RECHECK.json"
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/short_regimes.py run --case NOV2022 --state "$STATE" --output "$STATE/short-regimes/NOV2022" --plan-commit "$PUBLISHED_PLAN_COMMIT"
PYTHONPATH="$STATE/deps" python3 research/recover-frozen-runner-20261009/verify_short_regimes.py --directory "$STATE/short-regimes/NOV2022" --state "$STATE" --write
```

Run JAN2023 and OKX86 with their explicit plan identities in separate fresh
directories. Never repeat an account with a retained STARTED receipt.
`short_training_context.py --state "$STATE" --output NEW_CONTEXT_DIRECTORY`
creates the separate target/eligibility contexts without a wallet or model.
Full per-asset targets, minute inventory, fills, order rejections and independent
signal witnesses are preserved for every account.
