# Why the symmetric CS/SMA200 agreement gate failed

Saved-holdings diagnostic only. All 365 dates in each of 2023 and 2025; no replay, new targets, fitting, random draws or parameter search. Original quantity rows, p0/p1/funding, target masks and proofs were hash-verified.

## Net shortfall: mostly lost price PnL

| Full year | CS net | AGREEMENT net | Difference | Price PnL difference | Funding difference | Rebalance expense difference | Terminal expense difference |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | -89.72 | -522.08 | -432.36 | -352.00 | -70.94 | -12.94 | +3.51 |
| 2025 | +2,195.97 | -398.49 | -2,594.46 | -2,688.24 | -10.36 | +96.67 | +7.47 |

All amounts are USDT. Expense differences are signed contributions: positive means lower expense. These sum to the published separate-wallet net difference, within 1e-8 USDT.

## What the gate removed versus what resizing changed

| Full year | Removed CS long price PnL | Removed CS short price PnL | Total removed price PnL | Kept sizing effect at CS NAV | Kept NAV-path effect |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | +995.03 | -893.38 | +101.65 | -200.69 | -49.66 |
| 2025 | +669.98 | +1,343.16 | +2,013.14 | -644.13 | -30.97 |

2025 is the clearest failure: the gate removed profitable relative losers as well as profitable longs. Requiring a cross-sectional short to be in an absolute SMA downtrend discards shorts that can profit even while their own long-term trend is up. That mechanism is consistent with the observed attribution; it is not proof of a causal marginal effect. The remaining inventory was also resized differently: 548 of 819 kept leg-dates had smaller AGREEMENT weights than CS, and 131 had larger weights.

2023 is mixed: rejected CS short legs carry −893.38 of price PnL, while rejected longs carry +995.03. Rejected shorts also carried 109.09 of funding receipts, versus 19.18 funding expense on rejected longs. Different sizing on the surviving legs further reduced price PnL; the more one-sided inventory carried greater net funding expense.

### Asset contributions to AGREEMENT minus CS

| Full year | Asset | Price | Funding | Rebalance expense | Terminal expense | Net |
|---|---|---:|---:|---:|---:|---:|
| 2023 | BTCUSDT | -245.67 | -15.04 | -8.17 | +0.41 | -268.48 |
| 2023 | ETHUSDT | +297.16 | -34.02 | +1.42 | +1.35 | +265.91 |
| 2023 | SOLUSDT | -1,020.42 | +21.09 | -0.76 | +0.41 | -999.69 |
| 2023 | XRPUSDT | +303.13 | -33.09 | -6.21 | +1.35 | +265.18 |
| 2023 | DOGEUSDT | +313.80 | -9.87 | +0.78 | +0.00 | +304.72 |
| 2025 | BTCUSDT | -147.08 | -4.22 | -7.73 | +2.43 | -156.60 |
| 2025 | ETHUSDT | -1,005.58 | +3.55 | +15.85 | +2.45 | -983.73 |
| 2025 | SOLUSDT | -737.28 | +6.17 | +36.40 | +0.00 | -694.71 |
| 2025 | XRPUSDT | -95.26 | -9.80 | +32.04 | +1.31 | -71.71 |
| 2025 | DOGEUSDT | -703.05 | -6.05 | +20.11 | +1.28 | -687.72 |

2023 lost most incremental price PnL in SOL. In 2025 ETH, SOL and DOGE account for most of the price shortfall. DOGE retained holdings still produced −998.99 of AGREEMENT price PnL; this is descriptive, not permission to drop DOGE or select assets after seeing results.

## Hedging and exposure changed

| Full year | CS / AGREEMENT mean gross | AGREEMENT mean net-long | CS / AGREEMENT realized annual vol | CS / AGREEMENT drawdown |
|---|---:|---:|---:|---:|
| 2023 | 44.15% / 31.04% | 5.14% | 13.32% / 9.99% | 14.97% / 17.30% |
| 2025 | 48.89% / 22.68% | 1.85% | 9.70% / 11.30% | 3.56% / 12.17% |

The ungated CS wallet remains net-neutral; the gate removes that hedge structure. In 2025 it more than halves mean gross yet raises realized volatility and markedly worsens drawdown. A common nominal 10% risk policy did not create matched realized risk.

The predefined NO_REALLOCATION diagnostic nets −249.45 in 2023 and +113.87 in 2025; AGREEMENT nets 272.63 and 512.36 less, respectively. This supports inspecting survivor sizing, but does not isolate a causal sizing return because the wallet NAV paths differ. Removing hedges pushes its estimated risk above 10% on 154 and 254 dates; its 2025 realized vol is 15.49% and drawdown 14.12%. It is not a qualified replacement winner.

## Most useful next research direction

Preserve the relative CS signal and long/short hedge structure. Prioritize one predeclared transaction-cost-aware inventory/risk-rebalancing experiment instead of another absolute-sign gate. CS 2023 earns +233.27 price PnL but pays 295.34 total costs and 27.65 funding; CS 2025 earns +2,560.22 price PnL and stays strongly net-positive. This targets a measured weakness without discarding the profitable 2025 relative shorts.

CS same-sign resizing costs are 91.49 / 104.76 in 2023 / 2025; non-weekly-rank-date expenses are 81.63 / 84.80. These are overlapping classifications, not additive savings, and not certified avoidable. Even a perfect rebate of every non-rank-date 2023 fee would still leave CS negative by 8.09. A new design must explicitly trade reduced costs against changed inventory, achieved risk, net neutrality and missed price/funding PnL. Freeze one causal recipe and its full-calendar gates before any run; no tuning, shortened windows or protected holdout access follows from this report.

Keep the prior failed own-21-day-return short gate, failed SMA hard-gate evidence and failed additive SMA/CS mixture intact. The symmetric gate also remains failed. The JSON contains complete additive asset × side × gate attribution, all expense conventions, turnover diagnostics and arithmetic reconciliations.

## Attribution conventions and limits

- Price PnL = q × (p1 − p0); funding cash = −q × original funding per unit; rebalance cost = −|q − prior q| × p0 × 0.00135; terminal cost = −|last q| × last p1 × 0.00135. q is exactly the saved binary-float quantity, without regenerated holdings.
- Holding price/funding use the saved ownership-date gate and inventory direction. Opening/increasing cost follows current inventory; closing/decreasing cost follows prior inventory and prior gate. A reversal splits old close and new open. This convention makes every expense additive; alternative attribution conventions can move costs between buckets.
- The kept-leg identity is qA − qC = (qA × NAVC/NAVA − qC) + qA × (1 − NAVC/NAVA). The first term is sizing at CS contemporaneous NAV; the second is the NAV-path effect at AGREEMENT sizing. The order determines allocation of their interaction. These are algebraic PnL/funding terms, not new quantities replayed in an account, independently tradable strategies or separately evaluated returns.
- CS kept/removed components used the full CS wallet NAV and risk sizing. Their sum is an account attribution, not an equal-capital substitute portfolio or proof that removing a component causes the measured return difference.
- Known historical development years, hypothetical filled daily proxy and paid hypothetical terminal only. No capacity, margin, liquidation, minQty, live-fill or pristine out-of-sample evidence.

Reproduce: python attribution.py --self-test; python attribution.py. Existing scoring, protocol, targets and result artifacts are not modified.
