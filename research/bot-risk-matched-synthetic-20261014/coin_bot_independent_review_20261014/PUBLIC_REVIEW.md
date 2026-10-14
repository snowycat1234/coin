# Independent review of the BTC grid replacement prototype

## Conclusion

PASS_SYNTHETIC_SOURCE_ONLY. The frozen CSH_BTC_GRID_REPLACE10 helper passes the original 40 generated tests, 41 independent adversarial tests, and the generated toy demonstration. This establishes bounded source-level behavior. Native shared-wallet execution, observed risk matching and economic performance remain NOT_CERTIFIED_NEEDS_NATIVE_BINDING. No historical run is authorized by this review.

The candidate is a fixed-range grid mechanism adapted into a long-only BTC target sleeve in the original isolated 1x perpetual account. It is not a reproduction of Bybit Spot Grid, Futures Grid or a proprietary AI algorithm. Its proposed replacement is exactly 10% of the positive original BTC target; the remaining original targets, including other-asset shorts, must be preserved. The untouched original and the same-slice cash replacement are necessary controls.

## Frozen evidence and test results

Review date: 14 October 2026 UTC. The final source freeze is 04:57:18.303266 UTC. The exact FINAL_MANIFEST.json SHA-256 is ddea8797f02722f39c779fc548d0e3471f13907f04d94f9f9c3fe8b4be605bd8. Every manifest entry matched before testing, and all candidate file bytes were unchanged afterward.

The independent receipt is REVIEW_CHECK_RECEIPT_0001.json. It binds the source before and after, the independent suite and runner, the fixed command results, and original financial-source hashes. The original suite passed 40 tests; the independent suite passed 41 tests. The toy demonstration passed. Command wall times were approximately 0.084, 0.087 and 0.045 seconds. Maximum child RSS was 15,104 KiB, about 14.8 MiB. Each child was limited to one CPU, 60 seconds and 512 MiB of address space.

Four original source copies were hashed read-only before and after testing. Each remained equal to its existing pin: perpetual_account.py, execution_contract.py, fine_account.py and terminal_adapter.py. These files were not imported or executed by the review. Market-data reads, downloads, historical wallets, native financial advances and external mutations were all zero.

## Independently checked behavior

- Initialization creates explicit paid buy intents and starts with zero owned inventory. A signal or price touch never creates a filled holding.
- Quantity remains fixed on the assumed 1e-8 lot grid. Four potential inventory slots valued at the upper range plus the declared one-sided BASE27 debit fit the initial replacement budget. Narrow fee-insufficient ranges and inadequate opening notionals are rejected.
- Daily candle end and logical availability are distinct. Future, stale, missing and duplicate daily tapes are rejected. A completed candle genuinely available at the decision is admitted without adding an artificial day of lag.
- Both startup price and later observations require fresh timestamped completed-minute inputs. Future, stale, conflicting and rewound observations are rejected without changing policy state. Fill, confirmed-cancellation and expiry callbacks share a monotone event clock.
- Each session has a distinct UUID instance nonce, and each intent has an immutable session/order identity. Wrong-side, stale-order, cross-instance and duplicate-fill callbacks are rejected before mutation. Partial fills remain owned. A late cancellation or fill from an old order cannot mutate its successor.
- The fixed seven-day session boundary automatically blocks new intents, including an intent whose next eligible open would be outside the session. Outstanding executable orders and inventory remain until actual fills or confirmed cancellations. Out-of-range inventory is retained.
- Unfilled buys reserve risk alongside owned inventory and retained strategy legs. Pending sells do not release owned risk. Opposing legs cannot erase gross exposure. All buy-fill vertices are checked for gross, per-asset, absolute-net and covariance-risk bounds.
- Dropping original legs, supplying unfunded reservations, omitting requested buy notionals, exceeding shared cash or prior-minute capacity, changing leverage/capital/caps, and unknown covariance fail the arithmetic gate. Boolean numeric inputs and malformed report schemas fail closed.
- Favorable caller-supplied arithmetic never grants native execution permission: allowed remains false. Favorable scalar metric reports never certify risk matching. Truthy string flags, noncanonical contracts, missing evidence, worse risk endpoints, actual-cap breaches, halts, ruin, unpaid residuals and unfilled risk cannot produce a pass.

The initial review found slot-only callback ownership, truthy certification flags, unbound lineage/cash inputs, backdated fills, and an unenforced session boundary. The final source contains focused fixes, and the independent suite retains regressions. PRE_FIX_FINDINGS.json records the exploratory reproductions; no immutable pre-fix hash was captured while that source was changing.

## Economic interpretation and integration gates

A closed grid cycle can make money while remaining inventory loses more. The demonstration's +5 closed-cycle gain and -40 floating inventory loss imply -35 total before additional costs. Neither callback counts nor closed-cycle profit establish strategy returns.

The spacing filter is evaluated at configured levels. Actual next-open market execution can gap, incur costs and consume scarce capacity. The upper-range budget is not a guarantee that a pending buy will fill within that range or that native collateral is available. A perpetual adaptation must preserve the original fee, spread, slippage, conditional raw-fraction funding, isolated-margin and paid-terminal conventions; it receives no spot funding exemption.

Target caps do not establish equal realized risk. A later properly bound comparison must include minute drawdown, daily volatility and expected shortfall, worst 30-day loss, actual gross/net/per-asset exposure, halts, ruin, unfilled risk and terminal residuals. Absolute caps still apply when the control overshoots them. Incomplete halted prefixes cannot become full-year cash returns. All predeclared inactive, losing and stopped cases must remain visible, and no parameter sweep or equity-path rescaling may rescue a failed recipe.

The following remain prerequisites, not completed work:

1. A reviewed original-engine adapter and verified native snapshot/ledger loader, with exact source, clock, mask and target lineage binding.
2. Actual paid reductions before replacement initialization; shared collateral and capacity across all sleeves; preservation of original longs and shorts; daily budget/mask reductions and original hard-risk priority.
3. Authentic fill and confirmed-cancel callbacks, exact identity persistence across restarts, no overlapping sessions, and correct treatment of delayed callback availability versus venue execution time. The helper has no production order manager or restart persistence.
4. Original perpetual cost/funding attribution and the exact paid terminal scheduler. Manual expiry preserves holdings but does not implement or pay an exit.
5. Historical source/provenance and real-mark preflight, independent adapter review, and separate explicit authorization. Locked and unknown holdouts remain closed.

Do not unlock a historical or economic stage by merely changing allowed to true or trusting a report's evidence-origin label. The current source deliberately refuses that certification.

## Reproduction

Keep the frozen candidate folder and this review folder adjacent. From the review folder, python -m unittest -v test_adversarial runs the independent generated suite without market data. python run_review_checks.py additionally checks the exact frozen manifest, reruns the designer suite and toy, and verifies the four pinned original source copies when they are present in the reviewed workspace. Each run creates a new exclusive review receipt. There is no market-loader, historical CLI, optimizer, account key or live-order path.
