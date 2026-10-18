# 2025 DEV regime coverage and saved-run attribution

## Main finding

All 365 days are classified and all 88 contiguous episodes are retained. Both saved runs lost money in the bull, bear and rebound buckets. Their gains came from range and correction buckets. HELD10 reduced the bull-bucket loss substantially but earned less in correction episodes. This is descriptive attribution, not evidence of profitability across regimes.

The rebound bucket has only 11 days in 4 episodes. Coverage is unequal and correlated over time. No significance, threshold-stability or long-term robustness claim is established.

## Definition fixed before outcome joins

The BTC proxy uses the latest completed daily trade close declared available at each decision, its inclusive trailing 200-close average, and trailing 20-day simple return.

- RANGE: absolute 20-day return is at most 2%, including the threshold
- BULL: price is above or equal to SMA200 and 20-day return is greater than 2%
- BEAR: price is below SMA200 and 20-day return is below −2%
- REBOUND: price is below SMA200 and 20-day return is greater than 2%
- CORRECTION: price is above or equal to SMA200 and 20-day return is below −2%
- UNKNOWN: required observations are missing, unqualified/generated, nonpositive, nonfinite, stale, future-dated or noncontiguous

RANGE takes precedence. Equality with SMA200 belongs to the above-or-equal side. This is a single new analyst-specified descriptive rule on already seen DEV. It was frozen before regime outcomes were joined, not before 2025 DEV was seen. Related older causal conventions were inspected; none supplied this exact requested partition. The older multiregime future-target array was rejected for decision-time attribution. No interpolation, threshold search, learned gate or financial rerun was performed.

Rule SHA256: 31c90233b335c9ce2d45f2388a844a3e4da6df814af5e88957eeca9ad57997e4
Source-only label SHA256: 610df3ad51d44a964990fee0137d397ded4106eed8b06d15584e3fdea516ecd2

## Complete coverage and additive dollar contribution

| Regime | Days | Share of 365 days | Episodes | Baseline net USDT | HELD10 net USDT | HELD10 minus baseline USDT |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 114 | 31.23% | 15 | -1,039.89221084 | -166.69289158 | 873.19931926 |
| BEAR | 70 | 19.18% | 15 | -328.57779833 | -316.52895182 | 12.04884651 |
| REBOUND | 11 | 3.01% | 4 | -113.37969349 | -49.61506897 | 63.76462452 |
| RANGE | 76 | 20.82% | 34 | 365.29264403 | 425.02250450 | 59.72986047 |
| CORRECTION | 94 | 25.75% | 20 | 946.18509883 | 473.89536888 | -472.28972995 |
| UNKNOWN | 0 | 0.00% | 0 | 0.00000000 | 0.00000000 | 0.00000000 |

These are additive dollar contributions on the actual strategy paths. Dividing dollars by 100 gives percentage-point contribution to the initial 10,000 USDT wallet. Disjoint regime buckets are not compounded or annualized. Differences between saved strategies are path-dependent and do not by themselves isolate a causal treatment effect.

## Costs and exposure by regime

Fees and adverse execution are positive costs; funding is signed cash received or paid. Gross mid-mark PnL is the exact bridge: net NAV change + fees + adverse execution − signed funding. Mean and maximum exposure below are the preserved 1-minute float64 sample summaries, not continuous-time maxima. Exact rational boundary dollar exposures are in the daily JSON files.

### BASELINE

| Regime | Gross mid-mark PnL bridge USDT | Fees USDT | Adverse execution USDT | Signed funding USDT | Mean gross exposure / NAV | Max gross exposure / NAV | Mean gross exposure USDT | Minutes forecast sigma > 10% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULL | -1,000.77210492 | 5.72099402 | 8.31868624 | -25.08042565 | 18.75% | 32.30% | 1,919.82 | 101220 / 164160 |
| BEAR | -320.90522155 | 3.40043446 | 4.94729960 | 0.67515727 | 6.15% | 16.49% | 620.86 | 27212 / 100800 |
| REBOUND | -112.71050818 | 0.00000000 | 0.00000000 | -0.66918531 | 8.17% | 13.99% | 830.27 | 8640 / 15840 |
| RANGE | 380.66180864 | 0.76399254 | 1.11188832 | -13.49328375 | 17.16% | 29.77% | 1,775.35 | 59597 / 109440 |
| CORRECTION | 963.63952601 | 2.16514882 | 3.15016976 | -12.13910861 | 17.91% | 28.74% | 1,826.59 | 68813 / 135360 |
| UNKNOWN | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | n/a | n/a | n/a | 0 / 0 |

### HELD10

| Regime | Gross mid-mark PnL bridge USDT | Fees USDT | Adverse execution USDT | Signed funding USDT | Mean gross exposure / NAV | Max gross exposure / NAV | Mean gross exposure USDT | Minutes forecast sigma > 10% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULL | -122.15090949 | 9.35754099 | 13.60785376 | -21.57658734 | 18.15% | 37.69% | 1,827.67 | 5093 / 164160 |
| BEAR | -300.60424034 | 7.82693240 | 11.38923864 | 3.29145956 | 11.98% | 35.35% | 1,222.86 | 7571 / 100800 |
| REBOUND | -49.36307867 | 0.00000000 | 0.00000000 | -0.25199030 | 12.76% | 17.95% | 1,291.20 | 0 / 15840 |
| RANGE | 441.56641968 | 4.84516296 | 7.04843784 | -4.65031437 | 15.58% | 33.92% | 1,580.50 | 1586 / 109440 |
| CORRECTION | 503.19230882 | 8.75944746 | 12.73889416 | -7.79859832 | 17.67% | 37.95% | 1,795.63 | 860 / 135360 |
| UNKNOWN | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | n/a | n/a | n/a | 0 / 0 |

## Every contiguous episode

ALL_EPISODES_PAIRED.csv lists all 88 episodes in chronological order with both runs, exact net dollars and costs, simple unannualized episode NAV return, and exposure/risk. The two ALL_EPISODES.json files retain full exact rational data. No profitable-month selection or episode exclusion was used.

## Exact conservation and funding boundaries

### BASELINE
- Initial NAV: 10,000 USDT; terminal paid NAV: 9829.6280401994361896152 USDT
- Exact net NAV change: -170.3719598005638103848 USDT
- Exact fees: 12.05056983306; adverse execution: 17.52804392; signed funding: -50.7068460475038103848 USDT
- 48 paid legs; all 5,475 source funding events accounted for: 5,470 account rows and 5 fresh-flat, zero-position source skips
- 366 exact NAV boundaries, 365 daily contributions and 525,600 minute observations
- Daily, regime and episode sums exactly match the independently audited full-year net and costs
- Exact mark/inventory cashflow bridge: maximum absolute daily native40 residual 0 USDT

### HELD10
- Initial NAV: 10,000 USDT; terminal paid NAV: 10366.0809610143028640295 USDT
- Exact net NAV change: 366.0809610143028640295 USDT
- Exact fees: 30.78908381318; adverse execution: 44.7844244; signed funding: -30.9860307725171359705 USDT
- 131 paid legs; all 5,475 source funding events accounted for: 5,470 account rows and 5 fresh-flat, zero-position source skips
- 366 exact NAV boundaries, 365 daily contributions and 525,600 minute observations
- Daily, regime and episode sums exactly match the independently audited full-year net and costs
- Exact mark/inventory cashflow bridge: maximum absolute daily native40 residual 0 USDT

The decision label covers (decision, next decision]. Closing midnight marks and exact-boundary funding belong to the preceding day and regime. A funding event after midnight belongs to the following interval. The five initial flat source skips occur 15 milliseconds after genesis, with their actual clocks preserved, and belong to day 1. This exactly preserves the R2 actual post-already-paid-boundary-funding observation phase. The shared deviation from the intended strictly pre-funding experiment remains disclosed.

Every daily NAV is the audited frozen observation NAV at the interval start and next observation NAV at the end; the final interval uses terminal paid NAV. All 365 end points also match saved progress checkpoints and preserved float64 minute endpoints. Exact rational boundary exposure uses saved paid inventory and the same decimal-rendered canonical source marks as the audit. No account, margin, strategy or financial clock was rerun.

## Scope and limitations

- Already seen 2025 DEV; no OOS or reliable long-term APR claim
- BTC is a proxy for market conditions, not a separate regime measurement for every traded asset
- No significant or robust cross-regime outperformance conclusion; only 11 rebound days
- No source arrival/publication, raw funding-unit, historical venue-filter/tier, liquidation/no-liquidation, or live execution certification
- No 2022 stitching, 2026 data, network market downloads, source modifications, or strategy replay
- Machine-readable calculation snapshots retain their creation-time pending-review status. The current independent review is recorded separately under review; consult the final delivery receipt for its outcome.

## Files

- RULE_FREEZE.json and DAILY_LABELS.json: frozen causal definition and all source-only labels
- REGIME_ATTRIBUTION.json: complete bucket results, source pins, exact conservation and limitations
- BASELINE_DAILY_ATTRIBUTION.json and HELD10_DAILY_ATTRIBUTION.json: all days, exact dollar contributions/costs/boundary exposure, float64 minute summaries
- Daily CSV files: convenient decimal financial rows
- Both ALL_EPISODES.json files and ALL_EPISODES_PAIRED.csv: the entire contiguous episode partition
- review/: independent convention/source and attribution reviews
