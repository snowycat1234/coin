# Read-only XRP liquidation explanation

Both events are expected isolated-margin outcomes under the unchanged conditional account, not evidence of a unit, collateral-allocation, missing-bar or event-ordering defect in these events. This does not certify historical native Bybit tiers or liquidation charges. The original engine remains SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`; original account sources and completed accounts are unchanged. No wallet/account instance, fitting, policy change, risk-limit change or download was used.

| Observable state just before takeover | Static50 | Cash50 |
|---|---:|---:|
| Exact UTC event | 2024-11-16 10:49:00 | 2024-11-16 10:48:00 |
| Signed XRP quantity | -204.92235685 | -97.21120817 |
| Weighted entry USDT/XRP | 0.532921547052 | 0.528833517001 |
| Actual current mark USDT/XRP | 1.06181663 | 1.05526648 |
| Isolated collateral USDT | 109.207539438 | 51.408545109 |
| Marked unrealized PnL USDT | -108.382426924 | -51.175184354 |
| Isolated equity USDT | 0.825112514 | 0.233360755 |
| Maintenance USDT | 1.087949832 | 0.512918647 |
| Liquidation threshold USDT/XRP | 1.060540392143 | 1.052405008958 |
| Bankruptcy takeover price USDT/XRP | 1.065843094103 | 1.057667034003 |
| Free cash USDT | 9889.719615517 | 9996.912524330 |
| Portfolio gross before takeover | 13.814913% | 6.891658% |
| XRP absolute weight before takeover | 1.953932% | 0.969008% |

For these shorts, equity is `M + q*(mark-entry)` and maintenance is `abs(q)*mark*.005`. Actual collateral equals the remaining entry notional `abs(q)*entry` at1x within the original40-digit rounding residue. The source's liquidation formula therefore reduces to approximately `2*entry/(1+.005)`. XRP rose about99.24%/99.55% above the remaining weighted entry; the previous completed minute was below threshold and the current actual mark crossed it. All five assets have consecutive actual trade/mark bars around both events. No ordinary fill or funding event occurred in either trigger minute.

Both original short episodes began October7 00:01:00.000001UTC. Forty/35 opening or reduction legs changed quantities, but partial reductions released collateral proportionally and preserved the remaining old entry basis. They did not reset collateral to current marked notional. Ordinary loss and fee debits were covered by free cash; funding never consumed isolated collateral. Funding credits went to free cash, not automatic margin top-ups. The last XRP funding was November16 08:00:00.001UTC: raw signed rate0.00010, strictly prior08:00 mark0.9726, credits+0.019930748/+0.009454762USDT. Abundant shared cash and low portfolio gross therefore did not rescue either isolated position. The .6/.3 portfolio caps and past covariance mapper were not an isolated-solvency rule.

| October7 episode through liquidation, USDT | Static50 | Cash50 |
|---|---:|---:|
| Ordinary realized PnL at actual fill prices | -72.520012891 | -36.088495520 |
| Ordinary fees | 0.665437502 | 0.361906385 |
| Execution friction, already in fill-price PnL | 0.967972975 | 0.526459211 |
| Signed funding,121 actual events | +4.941698952 | +2.632155265 |
| Takeover realized PnL | -109.207539438 | -51.408545109 |
| Episode net through takeover | -177.451290878 | -85.226791749 |

The original policy closes at bankruptcy price and forfeits all remaining isolated collateral. It records zero extra liquidation fee/execution charge and no insurance-surplus refund. `margin_released` in the takeover receipt names the removed collateral; actual `free_cash_delta` is zero, so no margin is returned to the wallet. The full109.207539/51.408545 losses enter realized PnL once. Most of those losses were already in marked NAV: the additional takeover debit at the current mark is the remaining positive XRP equity,0.825112514/0.233360755USDT. Across the trigger minute, all-asset mark moves were-2.178043493/-0.700610770, producing total NAV changes-3.003156007/-0.933971525. Previous/current minute NAV, saved cash/collateral changes and final flat cash all reconcile. Final NAV is `10000 + realized_PnL_at_actual_fills - fees + signed_funding`; execution friction must not be subtracted again from actual-fill realized PnL. Final reported net remains+1461.046199/+742.742940USDT, including the full losses.

After takeover, XRP quantity, basis and isolated collateral become zero and free cash stays unchanged. The engine cancels the affected pending intent and blocks old-signal reopening. The saved minute ledger remains XRP-flat until the next normal rebalance, November17 00:01:00.000001UTC. The new shorts-100.52400972/-47.83810219 allocate fresh112.948817531/53.750910756USDT at1.12360040 and pay0.062121850/0.029563001 fees. Old collateral is neither refunded nor resurrected.

At the same10:48/10:49 observations, the selected model held-30.71759067XRP from a later November13 episode, weighted entry0.694809585772 and collateral21.342876449. Its equity was10.270509118/10.069304292 against maintenance0.162076219/0.163082243; threshold1.382705643327 stayed above the actual mark. XRP signed weight was about-0.29750%/-0.29936% of NAV. The higher remaining entry basis supplied the liquidation headroom; smaller size reduced wallet impact but alone would not change a1x isolated price threshold. This is the saved policy's observable path, not a hindsight change or proof of general learned protection.

The concrete engineering implication is to inspect per-position isolated equity/maintenance and liquidation distance separately from portfolio gross/covariance caps. The takeover's residual-equity penalty also needs a separate event/NAV bridge so collateral removal is not mistaken for a second full loss or a cash refund. No risk-rule adjustment or new strategy is implemented or justified by this explanation; the fixed tuning study remains closed.

`EVIDENCE.json` preserves exact Decimal values, original takeover/reentry receipts, source/account hashes, event clocks, model comparisons and the public recovery identities. `../../explain_q4_xrp_liquidations.py` reproduces this read-only journal fold. Receipt arithmetic uses50 digits and1e-24USDT identity tolerance; original account uses40 digits, and stored float minute NAV compares within1e-8USDT. Every read input's hash was unchanged after analysis. Existing full independent financial/actual-input audits are reused with their original identities.
