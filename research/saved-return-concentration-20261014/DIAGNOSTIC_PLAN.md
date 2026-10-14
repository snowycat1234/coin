# Fixed saved-result diagnostics

Diagnostics fixed at 2026-10-14 22:10 UTC, before return calculations. This plan was recorded after source restoration and endpoint reconciliation, before concentration calculations.

- Analyze both already-public completed 2023 runs: H090 CONTROL and ordinary CS/HOLD. No strategy, training, price source, risk parameter, or date range is changed.
- Reconstruct daily NAV from the saved net_increment_USDT and initial capital, and reconcile the endpoint to saved paid NAV.
- Include every calendar month: net dollars, additive percentage-point contribution on initial capital, compounded monthly return, and share of full-year log return.
- Identify the best month by highest compounded monthly return, then remove that month's observed daily returns multiplicatively. This is a deletion diagnostic, not a re-simulation of an executable strategy. Also report fixed-dollar contribution subtraction separately.
- Compute the worst of every contiguous 30-day and 90-day calendar window, using full windows only.
- Sort all observed daily log returns descending, report top 5/10 sums as a share of net annual log return and of all positive daily log returns, their exact dates, and returns after deleting those daily returns. Shares of net annual log return can exceed 100% because losing days offset winners.
- Report day-count coverage, zero-return days, first nonzero day and saved first entry, daily-boundary drawdown separately from saved all-event drawdown.
- Preserve exact public source URLs, pinned commits, bytes, Git blob hashes and SHA256. Run stdlib arithmetic only under 120 CPU/wall seconds and 2 GiB address-space cap.

Known limitations: both are seen-development results, not out of sample; different nominal risk settings make fair dominance claims invalid. Both use BASE27 cost assumptions and uncertified fine-grid, funding-unit, publication/arrival and native-margin/liquidation assumptions. Daily results cannot establish intraday extremes, execution realism, margin safety, live returns, or long-term APR. No new historical engine, market download, archives, trades, accounts, or publication is authorized by this analysis.
