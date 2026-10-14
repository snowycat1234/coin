# Paired GRID incremental-consistency diagnostic

Declared on 2026-10-14 before reading daily values or calculating results.

## Question and fixed scope

Are the already-known GRID minus CASH annual differences (+44.4687 USDT in 2023; -35.3650 USDT in 2025) broadly distributed across months, or fragile marginal contributions? Read only the four pinned public saved DAILY.json outputs and necessary ordinary financial fields of their SUMMARY.json files. Use the prior economic assessment only to establish what is already known. No market downloads, engine execution, training, strategy optimization, additional years or account access.

CASH means the control with the BTC allocation replaced by cash; the rest of the original portfolio remains active. It is neither an all-cash wallet nor the original CSH strategy. Both arms start with 10,000 USDT. These are seen-development results with the same period, base costs and configured risk budget, but different actual exposure. They cannot certify strict same-risk dominance or future/live Bybit performance.

## Fixed calculations

1. Require identical, unique, ordered, complete calendar dates for each pair, 365 days in each specified year. Validate the 10,000 USDT starting balance and terminal equity against retained ordinary summary fields. Reject missing or misaligned days rather than filling them.
2. Let D_t = GRID NAV_t - CASH NAV_t, with D_0 = 0. The paired daily dollar increment is x_t = D_t - D_(t-1). Use Decimal arithmetic for dollar contributions, signs, and drawdowns. These are whole-portfolio marginal differences, not a separately funded grid wallet.
3. Report every calendar month's sum of x_t, both positive/negative/zero month counts, and each yearly total. No ex-post month filtering or gating recipe.
4. Report positive, negative and exact-zero increment-day counts; positive-day fraction uses all 365 days, including zeros. Also report the fraction among nonzero days, distinctly labeled.
5. Report maximum peak-to-trough decline of D_t, including the initial zero in the running high. Units are USDT, not a percentage return on fictitious spread capital. Include peak and trough dates and the final gap.
6. Mechanically subtract each year's largest monthly dollar contribution from its annual total. Show the removed month and contribution. This is a concentration sensitivity, not a rerun, a new wallet, a tradable strategy or a month-selection rule.
7. Calculate lag-zero Pearson correlation between paired calendar daily portfolio simple returns, each derived from its own NAV and prior NAV, using the same initial capital for day one. Do not correlate cumulative NAV levels.
8. Optional resampling is omitted: two observed development paths and daily close summaries do not establish an independent sampling design or learnability. Report inconsistency and magnitude without claiming that 'statistical noise' has been proven, a future expected alpha exists, or the pair is same-risk.

## Deliverables and checks

Provide an offline standard-library reproduction script, nine bounded unit/integration tests, exact daily paired contributions, full monthly results, a machine-readable checked result, a concise report, and a clean packet containing only these new analysis files and allowlisted ordinary public financial inputs. Source references use immutable public URLs and public content hashes. Do not copy internal roots or private source-lineage fingerprints embedded in summaries. No publication is performed by this analysis.

## Schema clarification before calculation

The public DAILY schema contains each calendar day's net_increment_USDT rather than an explicit closing NAV. Reconstruct NAV as 10,000 plus cumulative saved daily increments. Decimal parses the original JSON number text, preserving the published decimal precision, not recovering the engine's unrounded internal numbers. Reconcile reconstructed terminal NAV to the high-precision paid_NAV_decimal in the allowlisted summary with a fixed 0.00000001 USDT tolerance; report the residual explicitly. Confirm inferred starting balance = paid_NAV_decimal minus decimal_strings.net_PnL equals 10,000 within the same tolerance. Report the minimum and maximum cumulative paired difference with first dates, including the initial zero. Calendar timestamps are UTC day boundaries. This clarification is recorded before any sums, signs, monthly aggregation, correlations or sensitivities are computed.
