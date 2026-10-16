# Six fixed continuous wallets: saved comparison

All six predeclared accounts completed the same [2021-04-02, 2026-01-01) interval: 1,735 actual days, each beginning with 10,000 USDT. These are seen-DEV historical simulations, not OOS evidence or future APRs. Rows remain in their original order; no profitable years or tiers were selected.

| Frozen recipe | Nominal tier | End NAV (USDT) | Cumulative | Historical CAGR | Realized vol | Max drawdown | Mean gross |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original intrinsic STATIC50 | 5.00% | 11799.70 | 18.00% | 3.54% | 4.65% | 11.05% | 10.63% |
| Original intrinsic STATIC50 | 10.00% | 14151.37 | 41.51% | 7.58% | 7.13% | 15.92% | 18.50% |
| Original intrinsic STATIC50 | 15.00% | 14107.39 | 41.07% | 7.51% | 7.81% | 13.50% | 19.21% |
| CORE VOL_MANAGED_HOLD | 5.00% | 12352.05 | 23.52% | 4.54% | 6.31% | 10.13% | 8.30% |
| CORE VOL_MANAGED_HOLD | 10.00% | 15424.36 | 54.24% | 9.55% | 11.32% | 18.87% | 15.64% |
| CORE VOL_MANAGED_HOLD | 15.00% | 18522.33 | 85.22% | 13.85% | 16.47% | 27.20% | 23.05% |

Terminal outcomes: 6 actual paid-market flat; 0 conditional-settled flat. Each outcome remains explicit in the CSV/JSON.

Cumulative = final NAV / 10,000 − 1. Historical CAGR = (final NAV / 10,000)^(365 / 1,735) − 1, using the full actual elapsed interval and a stated 365-day year. Neither is a product of freshly seeded annual wallets or a forward return forecast. Volatility is std(ddof=1) of all 1,735 complete daily NAV ratios minus one, including the initial 10,000, multiplied by sqrt(365). Max drawdown is the saved native all-observation statistic; independently reconstructed minute-close and daily-close drawdowns are retained separately in COMPARISON.json.

## Risk and continuity

- Nominal 5%/10%/15% tiers do not produce matched realized risk. No return rescaling or risk-matched superiority claim is made.
- Every account carried positions, pending orders, margins, cash, basis, open clocks and lifetime peak/risk state through all four Jan1 seams. There were no annual terminal closes, resets or cash reseeds. The global terminal used its single signal 61 minutes before the end and 60 later real minute opens.
- GUARD50_EXIT_ONLY stayed installed, with no automatic cash transfers or topups. Dynamic warning states and paid exits are described below; the contract name alone does not mean that an account remained frozen in exit-only mode.
- Saved covariance forecasts are code-bound diagnostics, not independently recomputed source covariance here. Actual gross/asset risk and saved forecast breaches are retained; no instantaneous capital, volatility or liquidation-safety guarantee follows.

| Recipe / tier | Max gross | Forecast-breach minutes | Max saved forecast vol | Guard50 episodes | Paid legs | Fees | Execution friction | Net funding cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| STATIC50_OLD_NO_REEXPANSION_LOW | 30.08% | 362211 | 10.60% | 8 | 1351 | 73.51 | 106.92 | 279.84 |
| STATIC50_OLD_NO_REEXPANSION_MID | 34.90% | 133521 | 29.53% | 12 | 2149 | 167.89 | 244.21 | 482.41 |
| STATIC50_OLD_NO_REEXPANSION_HIGH | 35.05% | 23808 | 29.42% | 12 | 2227 | 183.83 | 267.39 | 481.24 |
| VOL_MANAGED_HOLD_LOW | 17.71% | 1468691 | 30.07% | 3 | 457 | 11.13 | 16.19 | 440.56 |
| VOL_MANAGED_HOLD_MID | 33.27% | 1222926 | 29.05% | 5 | 1010 | 32.86 | 47.80 | 858.99 |
| VOL_MANAGED_HOLD_HIGH | 49.25% | 979898 | 38.62% | 6 | 1490 | 59.63 | 86.74 | 1413.76 |

All cost amounts are USDT. Signed funding cashflow is also retained in JSON: negative means a cash debit; the table shows its sign-reversed net expense. Costs are already reflected in executed NAV. Execution friction is embedded in actual fills and must not be deducted from realized fill PnL a second time.

Paid trading was active in every calendar component for every account. Annual activity/exposure/cost observations are retained in JSON solely as carried-wallet descriptions, without multiplying annual fresh-wallet returns or attributing exposure changes to the guard alone.
Dynamic Guard50 warning counts, active years, maximum duration, unresolved episodes and cross-Jan1 episodes are retained separately from the persistent policy name.

Every recorded Guard50 episode resumed normal mode within 120 seconds; none crossed Jan1.

Warning-active years mean actual temporary REDUCE_ONLY_MONITOR episodes. A retained cash-watch reason can outlast a warning while the actual mode is CONTINUE_CONDITIONAL; the reason string is not a persistent exit-only state. UTC warning timelines and annual dynamic modes are retained in JSON. Annual activity/cost rows use UTC event year, while Jan1 marked NAV includes same-clock funding before the next daily decision. These rows are chronology, not exact cost attribution to marked subperiod returns.

## Evidence and limits

- Two root-observed controller exits, all six child exits, terminal checkpoints, exact code/source identities and independent saved reconstructions are bound by SOURCE_PINS.json and the consolidated saved proof. Every account has 2,498,400 minute rows; native40 accounting and four carried annual seams passed.
- Literal signed funding rates, event clocks, ordering and reported interval labels were preserved without interval rescaling. Each journal observed 26,100 events; 26,095 entered the account ledger because five genesis observations had no ownership/no past mark and zero cashflow. Funding units/publication timing remain uncertified.
- Both quality sources were OR-composed (reject when either is unrecovered): 27 typed 2022 cells/eight genuine recovery endpoints and the separate 2024 interval. Typed cells with carried positions, in fixed account order: 27/27, 27/27, 27/27, 27/27, 27/27, 27/27; rejected-increase receipts: 0, 0, 0, 0, 0, 0. Valuation exposure remains; zero rejections is not safety evidence.
- Venue/arrival/current-mark certification, liquidation or no-liquidation safety, OOS validity and instantaneous-risk guarantees remain false/unknown. Tiny native40 secondary bridge residuals are retained unchanged, not treated as cashflows or silently forgiven.
- Each case stayed under the frozen 2,400 combined CPU-second, 2,700 wall-second, 4.5GB observed RSS, 7GB hard AS and 700MB output limits. The 4.2GB logical cohort includes the first pilot, remaining outputs and permanent claims. Admission required 5.5GB available memory; writes retained a 1.5GB disk floor. Cgroup visibility and unsampled transient/AS peaks remain qualified, not invented.
- This closes the annual-reset evidence gap for this exact predeclared six-account simulation. It does not establish a deployable winner, live safety or an unseen-period result. No other account, strategy, parameter or half-SMA variant was added.

Local research only. External publication remains blocked. Full minute chunks remain in their original locations; this compact comparison duplicates none.
