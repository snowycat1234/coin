# Saved SMA2025 v2r1 full-year economics

Status: AUDITED SAVED RECORDS ONLY. The separate independent audit passed exact native40 bookkeeping and saved minute-value preservation for this completed DEV output. These reports are read-only saved-data calculations, not a new historical run or venue/out-of-sample certification.

## Result and target

- Calendar: Jan 1 through Dec 31, 2025 UTC, exactly 365 days and 525,600 contiguous minute closes; all 12 months complete, with 365 daily decisions.
- Fresh wallet: 10,000 USDT. Final paid-flat cash/NAV: 9,829.62804020 USDT. Net P&L: -170.37195980 USDT; full-year return: -1.70371960%.
- Chosen 20% net-return target: not met. Shortfall: 21.70371960 percentage points, or 2,170.37195980 USDT versus a 12,000 USDT endpoint.
- For this exact one-year interval, simple arithmetic annualization and CAGR both equal the realized wallet return. This does not estimate a repeatable long-term APR.
- 365 times the mean daily percentage return is -1.01369269%, a different statistic. Compounding all 365 daily returns reproduces the wallet return.

## Whole-year risk and actual exposure

- Minute maximum drawdown: 12.26397695%. Peak 10,876.08166039 at 2025-08-14T04:27:00Z; trough 9,542.24151212 at 2025-10-10T21:21:00Z. The peak was not recovered by year-end.
- Daily simple-return sample SD (365 observations, ddof=1): 0.62181753%; annualized by sqrt(365): 11.87980714%.
- Held-position forecast sigma from causal rolling daily covariance reached 24.20954729% at 2025-08-27T14:36:00Z. The independent audit evaluated all 525,600 held minute-weight vectors plus 10,988 before/after funding and fill observations; the latter separately peaked at 24.18682194%.
- The 10% covariance forecast is an admission-time target, not a continuously enforced held-position hard ceiling or an identity with realized daily volatility. Held forecast sigma of 24.2095% and realized daily-based annualized volatility of 11.8798% are different risk measures. Nominal tier/target does not establish equal realized risk.
- Actual gross marked exposure/NAV: minute mean 15.46653468%, median 14.24947615%, 95th percentile 28.49060623%, peak 32.30021518%.
- Actual signed net exposure/NAV: mean 5.51826492%; range -18.24984247% to 29.85872947%. Mean absolute net exposure: 13.61189254%.
- Mean long component: 10.49239980%; mean short component: 4.97413488%.
- Risk observations are minute-close marks and saved fills/funding, not unobserved intraminute extrema or certified native exchange liquidation/risk tiers.

## Exact cost accounting, without double-counting

Gross same-quantity mid-price P&L -90.08650000
− spread plus slippage 17.52804392
− fees 12.05056983
+ signed funding -50.70684605
= net P&L -170.37195980 USDT.

Equivalent bridge: realized fill-price P&L -107.61454392 − fees + signed funding = net P&L. Fill-price realized P&L already embeds execution cost; subtracting spread/slippage from that figure again would be wrong.

- Fixed modeled half-spread and slippage are 4 bps each per side. Their combined execution cost can be allocated equally: 8.76402196 USDT each. These are modeled charges, not separately observed venue components.
- Execution plus fees: 29.57861375 USDT, 0.29578614% of the initial wallet.
- Funding: paid 79.89960353, received 29.19275748, net -50.70684605 USDT. Of 5,475 source events, five initial-flat/no-past-mark events had no account application; 5,470 account receipts include 3,059 owned-position funding events and 2,411 zero-position receipts.
- Funding uses the saved RAW_AS_FRACTION scenario. Raw funding units and event-time publication assumptions remain uncertified.
- Nominal 27 bps roundtrip = 2 × (5.5 bps fee + 4 bps half-spread + 4 bps slippage). Exact fees use fill-price turnover; spread/slippage uses mid-price turnover.

## Turnover and all-period attribution

- Paid legs: 48, comprising 24 opens and 24 closes. Complete flat-to-flat campaigns: 24, with 13 long and 11 short; 5 net-profitable and 19 net-losing after fees, execution and funding.
- One-way paid fill turnover: 21,910.12696920 USDT, 2.19101270× initial wallet. Mid-price turnover: 21,910.05490000 USDT. Each entry and exit is counted once.

All five assets, using the full calendar:

| Asset | Gross mid P&L | Spread/slip | Fees | Signed funding | Net P&L | Mean abs exposure | Peak abs exposure |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | -38.351100 | 0.418599 | 0.287803 | -3.352902 | -42.410404 | 0.5346% | 3.1892% |
| ETHUSDT | 239.944600 | 10.378581 | 7.135169 | -26.052105 | 196.378745 | 7.2346% | 18.2599% |
| SOLUSDT | -65.670000 | 3.451048 | 2.372624 | -0.498086 | -71.991758 | 2.1823% | 9.5555% |
| XRPUSDT | -73.920000 | 2.141200 | 1.472108 | -25.594893 | -103.128201 | 3.5911% | 13.8631% |
| DOGEUSDT | -152.090000 | 1.138616 | 0.782865 | 4.791139 | -149.220342 | 1.9239% | 5.3655% |

Full-period direction attribution:

| Held direction | Campaigns | Gross mid P&L | Spread/slip | Fees | Signed funding | Net P&L |
|---|---:|---:|---:|---:|---:|---:|
| LONG | 13 | -37.913600 | 11.272324 | 7.749740 | -62.883969 | -119.819633 |
| SHORT | 11 | -52.172900 | 6.255719 | 4.300830 | 12.177123 | -50.552327 |

ETH is the only net-profitable asset (+196.37874512 USDT). The other four total -366.75070492 USDT. With aggregate P&L negative, a percentage share of total net profit would be misleading. Both long and short groups lose after all costs/funding.

## Coverage and regime limits

Every month is included. Minute coverage, January through December: 2025-01 44,640/44,640, 2025-02 40,320/40,320, 2025-03 44,640/44,640, 2025-04 43,200/43,200, 2025-05 44,640/44,640, 2025-06 43,200/43,200, 2025-07 44,640/44,640, 2025-08 44,640/44,640, 2025-09 43,200/43,200, 2025-10 44,640/44,640, 2025-11 43,200/43,200, 2025-12 44,640/44,640. These are coverage counts, not selected monthly performance windows.

Bull/bear/rebound/range performance is NOT CERTIFIED. No bound pre-existing causal four-regime label mapping was supplied in the saved output or source recipe. SMA long/short direction is not such a classifier. No hindsight labels were created.

## Interpretation and next step

The fixed same-quantity gross price P&L is already negative (-0.90086500% of the wallet). Fees and funding add drag, but they do not alone explain missing the 20% target. This is an accounting statement on recorded quantities, not a cost-free strategy rerun or forecast.

The exact saved-record audit has passed. Next use the saved source bindings, policy receipts, fills and funding ledger to reconcile source directions/requested targets with actual coarse-quantity exposures and all 24 complete campaigns, including how held forecast risk drifts beyond the admission target. Preserve this entire 2025 result as a fixed negative DEV observation; do not select favorable months, directions, assets, or parameters from it.

The lost different-engine 2022 +7.66% result cannot be paired with this run. Prior FLIP2025 +6.66298% and coarse FOLLOW +9.9415% use different policy/runtime and are not same-cost/same-risk paired superiority evidence. No multi-year CAGR, robust regime claim, long-term APR, live-readiness, or original-code-equivalence claim is established.

The run is DEV-only and uses previously seen 2025 data. Venue filters, coarse quantity profiles, risk tiers, liquidation behavior, funding units/publication and scheduler integration remain uncertified. No real-exchange no-liquidation or live-readiness claim follows from model paid-flat completion.

## Reproducibility

Independent receipt: audit_sma2025_v2r1/AUDIT_RECEIPT.json; status PASS_SAVED_RECORDS_EXACT_NATIVE40; SHA256 98eb900afed1647972e4034cf34279a455ca38382df3f1d62199ed99cfb9d778. It reconciles all 3,107 financial states and 18,921,600 saved minute cells. The native40 maximum-drawdown fraction is 0.1226397695339534353972673986743644580545; the displayed minute risk calculation uses preserved float64 NAVs.

Terminal proof SHA256: 6793008b479ca39e5520a1390b6f7f80aa65e7cd660f803e03f7cd23c5d89815

Re-run only this analysis script to reproduce the reports from existing files. It imports no execution engine, changes no source artifact, and performs no network request. Exact decimal attribution and input hashes are in FULL_YEAR_ECONOMICS.json.
