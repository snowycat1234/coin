# Next economical evidence module: STATIC versus HOLD

Status: analysis/reporting recommendation only. No financial code, target, account, history, or holdout change is authorized by this document.

## Recommended first step

Use the completed saved records to compare the two distinct realized families, STATIC and VOL_MANAGED_HOLD. Preserve H090 rows for the frozen-cohort record, but group any byte-proven duplicate paths with STATIC rather than count them as independent confirmation. Keep all nominal tiers and both years; do not select a winner or a subset after seeing outcomes.

There are 18 separate annual accounts in the original matrix: 17 new cells and one exact reused 2024 STATIC50 MID D case. Every account starts with 10,000 and ends at its own calendar boundary. Annual returns cannot be multiplied into a continuous two-year account result or live CAGR.

## Saved-only calculations

1. Bind exact case receipts, code/policy, calendar, source/quality, output hashes and independent terminal/risk approvals. A conditional model return, paid full-calendar return, and halted prefix are separate fields. Never subtract a partial baseline prefix from a full-year result and call the difference uplift.
2. Read only the saved MINUTE output for each approved case. Its 37 columns include NAV, signed per-symbol weights, gross/net weights, quantities, marked notionals, cash/margin and cumulative fees/execution costs/funding/turnover. Hash columns and canonical array bytes. A saved float64 observation is not a native-40-digit monetary ledger; preserve this distinction.
3. Derive observed minute returns as NAV[t]/NAV[t-1]-1, with the first denominator equal to 10,000; collapse to daily endpoint returns on the exact calendar. Do not interpolate missing observations or manufacture flat tails. Retain the frozen daily-volatility definition for comparability and native all-observation MDD separately from minute-close exposure telemetry.
4. For matched year and nominal tier, report STATIC/HOLD return differences alongside actual gross/net/asset exposure distributions, time flat, realized daily volatility, forecast-volatility budget overshoots, cash/margin extrema, paid turnover and warning exits. Keep all-minute overshoot counts and maxima. Nominal tier equality does not establish equal realized risk.
5. Report fees, execution-price costs and signed funding distinctly. Reuse the proven native same-quantity PnL bridge for cost description; it is not a counterfactual no-cost strategy. Native-40 chronological financial reconciliation remains authoritative, with raw higher-precision captured-delta residuals retained separately.
6. Prove duplicates from exact native trade/funding and full-column minute projections, not merely equal ending NAV. Preserve IDs unless the existing independent proof explicitly defines a non-financial field exclusion.

The main deliverable can be a small 18-row table, six matched-year/tier STATIC/HOLD pair summaries, exact duplicate groups, a return-versus-realized-risk plot, and an actual-exposure/forecast-overshoot table. Publish compact aggregates/proofs and original array hash/size only. Original large minute arrays stay local; public all-minute recomputation requires those originals or a separately admitted identical run.

## Ex-post descriptive normalization

A simple diagnostic is annual net return divided by full-sample realized annual volatility, alongside net return divided by average actual gross exposure. Label these as descriptive return-per-risk/exposure ratios, not alpha, an executable account return, or an out-of-sample test. State the exact denominators and show unnormalized returns too.

The full-sample volatility denominator uses future observations relative to early trades. Do not turn it into an allegedly implementable scaled-trade backtest. Scaling an existing return series does not rerun paid costs, fixed cash/margin limits, lot steps, latency, shared pending orders, or insolvency handling. A rescaled curve would therefore be only a mathematical diagnostic; it is unnecessary for this first module.

No further threshold search, model fit, family selection or historical financial run is needed to produce this evidence.

## Separately frozen prospective causal alternative

Only after the descriptive module, consider one common past-only risk-budget policy for STATIC and HOLD. Root must freeze the budget, original covariance estimator/availability convention, observation schedule, action routing and evaluation window before opening new outcomes. The existing MID 10% budget is a possible fixed candidate, not an admitted or tuned choice.

Use actual post-phase weights and the original strictly-past covariance to estimate forecast risk. Signal-time target projection alone does not control held-state drift, as the current overshoots demonstrate. A stronger candidate would issue genuine paid reductions when known/fresh post-mark-and-complete-funding observations exceed the frozen forecast budget. It must retain D Guard50, native costs, clocks, capacity/latency, lots, common wallet/caps and quality semantics. Unknown quality must not manufacture a new exit. Existing legitimate reductions continue under their native execution rules.

The precise paid reduction/hedge sequencing is a new policy contract that needs review: quantization or partial fills can unbalance hedges and temporarily increase portfolio risk even while gross quantity falls. Budget shortfall, infeasible lots and remaining overshoots must be reported rather than repaired hypothetically. No collateral transfer, external capital or synthetic settlement can be introduced to make matching look feasible.

Even this policy matches a causal forecast conditionally; it cannot guarantee equal future realized volatility, drawdown or turnover across families. Those are observed outcomes, not admission promises.

## Minimal admission evidence for any later implementation

- Freeze one rule and evaluation window, with no performance grid or outcome-based cell selection.
- Generated tests: past-only covariance availability, mark/risk/full-funding ordering, unknown-quality intent preservation, nonzero paid partial reductions, hedge/lot boundary failures, shared-wallet pending corners, finite resources and restart/replay honesty.
- Detached previews and financial journals must leave the live state unchanged. No hypothetical forced settlement may fund a new increase.
- Independent source/generated review and a fresh exact root GO precede any financial run. Preserve all current records and failures.
- Determine genuinely untested time coverage from outer metadata only. A current lock label does not prove a year was never used. If historical non-use cannot be certified, explicitly use a new prospective post-freeze window rather than describe an already-used year as untouched.

Current frozen reporting source: traditional_three_tier_freeze_20261015/annual_reporting.py, SHA256 3ffee703c1fabd4e18d9673220a850fff5e5663aed697e2dead7627017ff8636.
