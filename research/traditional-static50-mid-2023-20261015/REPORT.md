# Saved full-2023 STATIC50_MID pilot

## Result and scope

Status: PASS_SAVED_FINANCIAL_PILOT_WITH_EXPLICIT_RISK_QUALIFICATIONS.

Exactly one unchanged V3 STATIC50_MID BASE27 simulated account completed [2023-01-01, 2024-01-01) UTC: 525,600 native minutes and 365 days. It began with 10,000 USDT and ended paid flat at 12,405.356292506602 USDT. Marked and paid net return were +24.0535629251%; native all-observation maximum drawdown was 6.4341828488%. There was no liquidation-required halt, bankruptcy halt, residual marked notional or unpaid liability. Liquidation fills are not implemented as a certified native-venue model.

The saved account records contain 296 paid trade legs, including 155 OPEN legs and 141 quantity-reducing CLOSE legs. Fees were 24.842629927412 USDT; spread/slippage execution friction was 36.136371600 USDT; signed funding cashflow was -91.72740596598593916530 USDT; turnover was 45,168.418049840 USDT. The independent saved-cashflow NAV discrepancy was 1E-35 USDT. The original account bridge was 1.1E-35 USDT.

Only this pilot is reported. The other eight finite-year cells are separate work and require their own exact external root GO. No performance selection or tuning occurred during packaging. Exact preparation SHA256 is 43c715123c2be9a1398bd5242bc86da27efaf1cd30927117d9d835a3bcaebb43. Pilot GO SHA256 is 6930d9450279f652db8f6b644ec00043a6cedb166410191859c2f666d62f37ef.

## Risk is conditional sizing/admission, not a continuous invariant

MID nominal forecast-volatility budget is 10%. Actual post-transition minute-close forecast volatility reached 17.6378107253%, averaged 8.1884976445%, and exceeded the nominal budget by more than 1e-10 for 68,425 minutes across 87 calendar days. Realized daily NAV simple-return sample volatility annualized with sqrt(365) was 9.5888445714%. Gross exposure maximum/mean were 55.8299807226%/21.6215496852%; maximum absolute single-asset weight was 18.6658000264%. These do not make the account realized-risk matched to another cell.

The independent risk-causality addendum is included in full, with its exact reader and log. It used saved quantities/NAV and existing source open/mark observations plus an algebraic fee/friction/funding bridge. It imported no account engine and performed no account simulation or financial replay. Across all 155 actually executed OPEN legs, the maximum fresh-open, signal-bound-covariance forecast was 9.9708471455%, below 10%; all 155 had allowed fresh guard witnesses. The NAV algebra reconciled to the next saved minute within 3.64e-12 USDT. This result covers actual executed OPEN legs, not every hypothetical unexecuted guard corner, whose compact receipts omit detail.

The 17.6378% maximum occurred on 2023-01-15 at 00:01 UTC. Quantities were unchanged from the preceding midnight. Forecast on midnight weights changed from 12.7569% with the old covariance to 17.7317% with the refreshed daily covariance. The last prior increase was January 13; there was no OPEN on the maximum-risk day. The maximum minute observation preceded the first paid reductions at 00:01:00.000001 by one microsecond. Five paid CLOSE legs then executed the full native lot-floor reductions. All five remaining target gaps were strictly less than one native lot; the next minute's forecast was 9.9159709316%. Those genuine sub-lot gaps were not the cause of the pre-action 17.6378% peak.

All 141 CLOSE legs strictly reduced their symbol quantities. Thirty-four increased portfolio forecast volatility by removing hedges, and 47 ended above the nominal budget. Pure reductions intentionally bypass new-OPEN admission. Held inventory, covariance refresh and subsequent marked-price changes can exceed the sizing target. The observed peak must not be described simply as dust or generic drift, and no continuous forecast cap is established.

No observed minute close fell below the 1,000-USDT free-cash floor or exceeded 8,500-USDT isolated margin. Minimum observed minute-close free cash was 4,695.077819165723 USDT; the native all-observation minimum was 4,695.044108525723 USDT. Maximum observed isolated balance was 5,280.88921224 USDT. Exact capital-binding counts cannot be recovered from compact combined rejection reasons. Exposure shortfall is not attributed to capital alone.

## Runtime and unchanged identities

The pilot measured 114.4777987000 seconds whole-case wall time, 106.6380170940 seconds native-loop time, 114.615403 CPU seconds and 720,662,528 bytes peak RSS. The case reported 80,968,196 output bytes before its final receipt; final case files totalled 80,970,267 bytes including that 2,071-byte receipt. These are one MID workload's measurements, not a guarantee for other cells. Frozen per-case limits remain 600 seconds, one CPU thread, 2 GB RSS, 4 GB address space and 250 MB output, serial execution, stop-on-first-failure, no automatic retry or certified restart.

Core V3 hashes match the published base and unchanged annual protocol: frozen_grid.py a64abec4b396b17ff1e93bbc95ad77c6a76a26e54ecdf36bb5c9ddaedac6b8f1; native_runtime.py e716eace323b82954cd13755d0af80e046cd4daf5b37147300c417e7ac7d4b1a; historical_entry.py f8be19239bef56d7db514a327e09dfacf153bc1bdf54bbbc2b87616254df66b7. Full identities are in the protocol, preparation and receipts. Strategy formulas, account math, costs, guard policy, target grid and frozen tests were not edited.

Whole-year pre-return target equality found nine byte-distinct target paths and nine canonical execution jobs. Small floating-point STATIC50/H090 differences do not establish independent alpha families. This package reports no HOLD-relative annual excess because the other cells are absent; no post-hoc risk scaling or matched-realized-risk excess was preregistered or claimed.

## What is included and omitted

- Unchanged annual entry/protocol/controller/reporting and builder/independent test sources; existing 27-test passing review and logs
- Exact attempt003 source-only preparation, TARGETS.npz, target proofs, equality and readiness receipts
- Original result, risk report, case/controller receipts, log and historical GO
- Complete synthetic account snapshot, funding journal, guard receipts and native rejections as lossless gzip with exact decompressed parent hashes
- Saved financial review, full risk-causality addendum, reader regression and final engineering recommendation
- 365 daily saved observations and 1,716 rule-selected original minute rows, with transparent reporting-only derivation code and parent hashes
- Pinned public V3 base and 2023 source recovery locators; no private path dependency

The 60,638,969-byte MINUTE.npz is deliberately omitted; its SHA256 is e240c1a3e210efbffd8be0517d9e09a05413747ebe331cc857b0de9c7402f746. Full original local records remain retained. Compact evidence cannot reconstruct all minute rows or independently reproduce the full source-dependent risk audit without the omitted parent and recovered market source. Hashing and compact checks do not claim otherwise.

## Interpretation limits

2023 is previously seen development, not untouched OOS. Funding rates are unchanged raw fractions under an uncertified unit/publication/arrival assumption. Exchange quantity filters and liquidation/risk-tier fidelity remain conditional proxies. Native liquidation fills are not implemented. Generated tests validate synthetic engineering behavior. No other-year/holdout payload or locked data was consumed by packaging. No new historical account, financial rerun, fitting, market download, upload, account execution or publication occurred during packaging. This is engineering and saved-account evidence, not a long-term APR, investable-edge or live-use claim.
