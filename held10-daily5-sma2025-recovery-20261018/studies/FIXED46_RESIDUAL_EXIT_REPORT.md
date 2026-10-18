# Fixed46 residual-exit-only diagnostic, 2025

## Result

All **five original residuals close at the next minute OPEN, +1 minute**, under the frozen historical-volume/adverse-price proxy. All 46 original events and entry assumptions remain. No inventory remains open at the next-event boundary, and no later frozen event collides with retained inventory. The single partial entry E022 stays 4000 DOGE versus its 5000 coarse request; no missing entry quantity is restored. Final complete entered-quantity roundtrips are 46/46; full-coarse-request roundtrips are 45/46.

Across all 46, aftercost arithmetic on **each event's actual entered quantity × original observed entry OPEN** has mean **149.865178bp**, median **−21.557642bp**, and **21/46 positive**. Funding is excluded because its historical units/charge-mark/real ownership are uncertified. This is descriptive seen-DEV event economics, not shared-wallet PnL, capital feasibility, APR, execution certification or a deployable edge.

The prior full-coarse fixedexit counterfactual mean 149.826694 bp changes by only +0.038484 bp under this paid-exit policy. The median moves from −21.321174 bp to −21.557642 bp. Comparing only the prior 41 fully closed events (mean 168.089558 bp) would change the sample and is not the appropriate all 46 comparison.

The full-intended coarse-size fixed-exit counterfactual sums to 796.386113248356 USDT across independent events; using the actual entered size gives 794.705731740756 USDT. Final paid exits give 794.795610280356 USDT. Only E022's 4000/5000 DOGE partial entry causes the intended-versus-entered size difference. Its bp result is unchanged by that size scaling because each version uses its own entry-notional denominator. These event sums are not account PnL.

## Frozen policy and chronology

The executable, full protocol and24 synthetic checks were hash-bound before any later exit OPEN/volume/funding outcome inspection. The local freeze receipt is 2026-10-18T09:44:21.974105Z; protocol and executable hashes were also sent to the parent before the scan. These are locally recorded chronology, not trusted external timestamp attestation or proof of absence of prior access. The 46 original event outcomes were already seen development data.

- Original entries, signs, quantity floors, paid entry fees and original entry +60-minute exit attempts are unchanged.
- Only unclosed quantity gets greedy exit attempts at every subsequent exact minute OPEN, starting fixed exit +1 minute. No price-based waiting, new signal scan, parameter sweep or event deletion.
- The last permitted attempt is strictly before that asset's next frozen entry, or 2025 dataset end when no next entry exists. The bound preserves the original study's per-asset non-overlap purpose and is determined only by the frozen schedule. An unresolved remainder at that boundary would remain open/unpriced and be reported as a collision; it would not cancel or replace the next event. No bound was chosen to achieve flatness.
- At an attemptOPEN u, capacity uses only the minute opened u−2 minutes, with completion u−1 minute and availability u−1 minute+1us. The adjacent prior minute is still unavailable at exact u. Capacity is quote_volume×.001/observedOPEN, floored to original coarse lots. Close minimum is exempt.
- Exit fill=observedOPEN×(1−direction×.0008); fee=closed quantity×actual adverse exit fill×.00055. Retried closes pay no new entry fee. There is no additional27bp subtraction.
- Literal funding timestamps are preserved, and funding precedes fills at ties. Additional attribution is weighted by the residual quantity owned immediately before funding divided by original actual entered quantity. No cash or basispoint conversion is made.
- Missing exact source rows/hash/grid mismatch fail closed. Unavailable or invalid price/volume causes a zero-fill retry with explicit mask. Any residual is carried to the next allowed attempt; still-open final economics are null, never marked into completion.

## The five paid exits

All quantities are base units; all final economics exclude uncertified funding. Paired delta is versus a hypothetical full exit at the original fixed endpoint for exactly the same actually entered quantity and same entry-notional denominator.

|Event|Asset|Original residual|Paid retry UTC|Retry observed OPEN|Causal quote_volume|Delay min|Final event aftercost bp|Paired delta bp|
|---|---|---:|---|---:|---:|---:|---:|---:|
|E013|DOGEUSDT|3000|2025-02-25T08:32:00Z|0.20636|798660.11302|1|173.362395|+10.670187|
|E017|XRPUSDT|100|2025-04-02T12:14:00Z|2.1121|732978.94735|1|-22.743581|-0.472935|
|E024|DOGEUSDT|2000|2025-05-15T21:13:00Z|0.21972|526380.05854|1|-50.050317|+4.174467|
|E027|DOGEUSDT|5000|2025-06-21T22:30:00Z|0.15415|860781.52466|1|-46.207835|-6.925902|
|E033|DOGEUSDT|1000|2025-09-13T18:19:00Z|0.28472|1074947.55617|1|-52.234321|-5.675539|

All five are long positions. Each residual closes in one paid retry. First/final/quantity-weighted residual delay is 1 minute for each. No volume is reused across attempts for any event; no cross-event shared liquidity allocation is claimed. Original entry fill quantities remain 5000, 500, 5000, 7000, 4000 respectively. The 21/46 positive count is unchanged.

## Costs: paid leg versus incremental comparison

New retry exit legs have **1.277836912 USDT paid fees** and **1.860160000 USDT adverse-price cost**, total 3.137996912 USDT. The adverse-price cost is the modeled difference between observedOPEN and adverse fill; it is already inside gross fill PnL. These amounts must not be subtracted again from the final aftercost column.

The corresponding hypothetical original unfilled exits would already have required 1.2777874516 USDT fees and 1.860088000 USDT adverse-price cost, total 3.1378754516 USDT. Those fees were never actually paid by the original incomplete screen.

The paired incremental change is therefore:

- Gross price drift on residual quantity:+0.0900000000 USDT
- Incremental exit adverse-price cost:+0.0000720000 USDT
- Incremental exit fee:+0.0000494604 USDT
- Paired aftercost difference:+0.0898785396 USDT across the46 independent event calculations

All original entry fees total 27.864847276992 USDT; original paid partial/full fixedexit fees 27.380486730652 USDT; new retry fees 1.277836912 USDT. Final total fees 56.523170919644 USDT. Each original entry fee is charged once, with no fresh entry charge on retries. Monetary sums across independent events are bookkeeping diagnostics, not account PnL or simultaneous capital.

## Funding and concentration

There are **zero additional literal funding events** between any original exit and its +1-minute final close. The existing native signed raw-rate coefficient sum stays +0.00033534. No assumption that raw funding is zero cash, no conversion, and no netting of funding into final aftercost is made. For a hypothetical tie, residual ownership is measured before that minute's close.

October 10's five events are untouched: mean 1953.334656 bp, all five positive. The other 41 retained events have descriptive mean −70.070124 bp, median −30.207272 bp and 16 positive. Those date partitions explain concentration; they do not define a revised strategy or justify deleting events.

The largest DOGE winner remains 6051.091758 bp aftercost. Earlier independent raw review found its entry-time mark/trade gap already opposite its frozen feature. This residual policy does not repair the stale signal or establish mark convergence. Closing these small non-crash residuals leaves that concentration and mechanism problem intact.

## Source and execution uncertainty

Data attribution: Binance Vision public historical USD-M trade minute archives, from previously restored local 2025 data. No new provider request or download was made. SOURCE_INDEX.json SHA256 is8a0235e428902f7a0ea4ec1893343abae6ccc23715080771796b54fb58f1f3c4; source commit3c94a713de56d6c1244353e8a8c5c90f10c9cbd8, receipt commitbe48f5519c23f0e64eb4d75f8b8358915c254f7b. SAVED_RECONCILIATION.json preserves original provider archive URLs, byte counts and SHA256 for each used trade source, together with canonical month hashes and every retry OPEN/volume locator.

All 12 canonical month byte identities and the funding identity were checked before new numeric-array access. Only five month files were decoded for the ten selected retry scalars. No annual SMA or original event study was rerun. No credentials, live orders, account engine,2026 source bodies, Library/GitHub writes or provider downloads were used. Resource counters are self-reported, not a system-call audit.

Most importantly, a minuteOPEN is a historical first trade, not a tradable quote, guaranteed arrival or fill. A prior minute's traded quote volume is not current depth or executable liquidity. A real retry could miss thatOPEN or require more than 8 bp adverse movement even when this volume test passes. Coarse lots are research floors, not certified historical venue filters. This study fixes the inventory accounting under its assumptions; it does not validate the assumptions. No slippage/cost sensitivity grid was run, so the result is not robust execution evidence.

## Reproduce and interpret

Run from the workspace root, writing to a new output directory:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python coin_recovery_20261018/event_residual_exit2025/resolve.py --output NEW_OUTPUT_DIRECTORY

The normal run and python−O replay match all six substantive outputs byte-for-byte, and RESULT.json apart from variable resource counters. See REPRODUCIBILITY.json. Frozen files are not edited after outcomes.

- PROTOCOL.json: deterministic policy, source bindings, boundaries, caveats
- FREEZE_RECEIPT.json / SYNTHETIC_TESTS.json: executable+protocol freeze and 24 pre-scan checks
- run/EVENT_RESIDUAL_ROWS.json/.csv: unchanged original46 rows plus final economics/status
- run/RETRY_ATTEMPTS.json: five paid attempts, scalar sources, clock masks and fees
- run/EXTRA_FUNDING_ATTRIBUTION.json: empty because no additional events
- run/SOURCE_READ_RECEIPT.json / PRE_SCAN_PINS.json: exact source reads and identities
- SAVED_RECONCILIATION.json: paired cost decomposition, first delay, source lineage and concentration
- review/: independent saved-record verification

Original baseline columns intentionally retain their one-shot meanings: status, open_unpriced_residual_quantity and completed_roundtrip_after_cost_USDT are historical. Final state is residual_status, remaining_open_unpriced_quantity and final_completed_roundtrip_aftercost_USDT. For a final 46-event read, use final_completed_aftercost_bp_on_actual_entry_observed_notional. The separate full-coarse intended-size counterfactual columns are preserved for reconciliation and are not actual entry quantities.

Frozen protocol SHA256:0f8c1813f06539cff58d9285b41bc865e75ec6934d76e85c80f0abfc788bfdba

Frozen executable SHA256:f76e78259d9f781424eca2e9cb1f1686af08459752198ab21289f3681f862350
