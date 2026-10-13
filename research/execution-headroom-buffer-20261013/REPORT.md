# Execution headroom buffer v1: bounded read-only shadow

## Result

The frozen single candidate detects the original 2024 XRP short maintenance failure early enough to have real model-capacity exit opportunities, while producing no triggers on the entire original 2025 path. This supports a next economic test. It does **not** establish net benefit, paid-flat execution or a profitable strategy.

- 2024 XRP first signal: **2024-11-16 09:25 UTC**, 84 minutes before the original 10:49 halt. Original quantity was −236.58004288 XRP, isolated equity 12.09474823 USDT. First eligible execution is 09:26:00.000001, 60,000,001 microseconds after signal. Previous completed minute quote-volume capacity at the actual 1.0188 trade open exceeds that quantity. Its projected BUY fill is 1.01961504, fee 0.1326713134 USDT, spread/slippage cost 0.1928221981 USDT. This is a posterior capacity-and-cost reference, not a newly executed account.
- All 84 XRP trigger minutes have sufficient five-open capacity, but only **83** have capacity completion strictly before the original halt. The final 10:48 signal's first executable event is **10:49:00.000001**, after the original halt; its frozen-inventory price-only reference also crosses maintenance at 10:49. That failure is retained.
- 2025: **zero buffer triggers** across all 525,600 original successful minutes. The mechanical old 50%-collateral condition flags 11 DOGE SHORT minutes and one XRP LONG minute on the original path, all buffer-ready and all untriggered by the new formula. Actual old-guard changed-path exit signals at May 11 00:06 and October 10 21:21 are likewise untriggered when evaluated on the original path at those clocks. This supports avoiding those premature original-path exits; a changed strategy's later economic path is not established here.

## Population and coverage

| Original fine CSH year | Observed successful minutes | Buffer asset-minutes / contiguous trigger intervals | Asset, direction and month |
| --- | ---: | ---: | --- |
| 2021 | 525,600 | 628 / 33 | DOGE SHORT, June |
| 2023 | 525,600 | 35 / 7 | XRP SHORT, July |
| 2024 | 461,448, strictly before halt | 1,474 / 22 | SOL SHORT March: 1,390 / 21; XRP SHORT November: 84 / 1 |
| 2025 | 525,600 | 0 / 0 | None |

These intervals are contiguous flags on the **unchanged original inventory path**, not independent executed trades. All observed LONG trigger counts are zero. That is an observation of these sources and costs, not a general claim that a 1x long cannot trigger or is safe.

Every year/symbol has 43,200 initial unavailable minutes: the source lacks the extra initial endpoint necessary for 43,201 strictly continuous marks. First readiness is January 31 00:01 UTC. Original 2021 exposure is zero during this window; 2023/2024/2025 each have 43,199 invested unavailable minutes per symbol. No window is shortened and no prior-year mark is fabricated.

2024 also has **43,202 unavailable minutes per symbol** from August 12 10:03 through September 11 10:04 inclusive. The two original missing source minutes were overlaid by derived marks for all five symbols in the existing account; the buffer rejects every rolling window containing those ten cells. Total 2024 unavailable coverage is 86,402 minutes per symbol, leaving 375,046 ready original minutes. All unavailable intervals and reasons remain in year results.

## Comparison to 50%-collateral condition

Both formulas below are evaluated mechanically on the same unchanged original q/E/collateral path. Actual old-guard paths diverge after their first executions, so later changed-path events are not treated as identical-path comparisons.

| Year | Old condition asset-minutes | Both | Buffer only | Old only while buffer ready |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 2,249 | 0 | 628 | 2,249 |
| 2023 | 1,751 | 35 | 0 | 1,716 |
| 2024 prefix | 7,982 | 1,474 | 0 | 6,508 |
| 2025 | 12 | 0 | 0 | 12 |

The new formula is not a stricter nested version of the old threshold. In 2021 its DOGE short triggers occur while old 50% is false: at the first June 2 10:42 trigger, past-only maxima include a 0.26652467 log five-minute upward move and a 0.07449936 log adverse trade-open/strict-prior-mark gap. Combining separate historical maxima can be conservative and costly. The 2023 XRP and 2024 SOL flags also require actual economic testing; absence of original halt does not prove these exits improve returns.

## Exact single formula

See `PROTOCOL.json` and `headroom_buffer.py`. There is no parameter search.

At completed close t, require exactly 43,201 positive finite genuine mark endpoints P(u) on the minute grid, u in [t−30 days,t]. Within that same window take the maximum nonnegative upward and minimum nonpositive downward five-minute log changes. For completed trade opens v in [t−30 days,t−1 minute], take analogous adverse extrema of log(TradeOpen(v)/P(v)); P(v) is the preceding minute's mark close, strictly before modeled fill v+1 microsecond.

For LONG use downward extrema, for SHORT use upward extrema. Stressed mark P_s applies the five-minute mark move; stressed execution mid applies the execution gap. Fill adds the unchanged 4bp spread plus 4bp slip per side. Trigger when original E+q(P_s−P(t)) is at or below .005×abs(q)×P_s plus full-quantity mark-to-fill execution cost and 5.5bp fee on actual stressed fill. No free cash or top-up is borrowed.

Current close t is already known; no price or capacity from after t enters the signal. The first eligible actual open is t+1 minute, modeled at +1 microsecond; the fifth is t+5 minutes, also +1 microsecond. Posterior witnesses use unchanged 0.001 participation, strictly previous completed minute quote-volume, actual current trade open, one shared symbol/open capacity bucket and 1e−8 quantity floor. No original future fill is subtracted or combined with a hypothetical exit. Each flagged minute's witness is a separate frozen-q reference; capacities are never accumulated across different hypothetical triggers.

The historical extrema are an empirical buffer, not a bound on future prices. Future jumps, funding, mark rules, cash/equity constraints and capacity can still defeat it. Fixed-inventory mark references ignore hypothetical partial closes, future funding and later original fills. Missing, derived or invalid future marks make only that posterior reference NOT_READY_REFERENCE; they never cancel a historical signal. All 2,137 flagged asset-minutes in this run have ready posterior references; all have five-open capacity coverage. One final 2024 XRP reference crosses before capacity completion. These labels do not certify execution success or paid-flat cash.

## Integrity and resource result

One authorized scan only: **33.06099 seconds**; kernel peak RSS **438,550,528 bytes**, sampled descendant peak **438,726,656 bytes**, sampled shared host peak **3,778,514,944 bytes**. One CPU/thread, AS 4GB, effective inner CPU soft/hard 600 seconds, outer wall 900 seconds, RSS stop 2GB, shared host stop 8GB, swap/GPU zero. The reused outer receipt names its generic 1,200-second default CPU cap; the actual observer is additionally launched through `prlimit --cpu=600:600` and its gate rejects anything above 600. Generic wrapper wording about a wallet does not imply a wallet was constructed.

45 bound existing files, all 48 source month hashes and all original daily numeric chunk hashes were checked. The old RESULT state hash matches its genuine recovery pointer. Original signed marked notional matches q×the exact bound source mark. 2024 pointer cursor is the halt, while its last successful numeric close is 10:48; only the 461,448-row successful prefix is used. No post-halt position is invented. 11 worker synthetic tests and 8 independent tests passed, including prefix invariance, exact boundaries, directions, gaps/derived readiness, shared capacity, full costs, delays and future-reference refusal. No invested ready point lies within 1e−8 USDT of the floating shadow threshold; a future live candidate must nevertheless use its own current account state.

**0 new wallets, fits, financial account imports, transitions, source requests or PnL estimates.** Existing original gross/net/targets/costs/capacity/finance are unchanged.

Frozen code/input manifest SHA256: `e5bc0ccf1839d2f4a10ff68480659aa8b306210f101f2dafb55d30c17cf6a72d`.
Pre-scan independent review SHA256: `c39b02d1b8787c9c66b6a0913227ee288fadfb993328c3df45e428f3f3194055`.

## Next test, not yet authorized to run

Keep original fine CSH targets, full 10k capital, caps, 1x isolated finance, costs, quote capacity, same-direction lock and persistent paid exit. Replace only the old guard trigger with this frozen formula; retain original five-open terminal convention. Do not mix in the separate 60-open terminal modification.

2021/2023/2024 need one independent fresh candidate wallet each, reusing all existing original controls. 2025 may reuse its existing original result only after an independent strict no-op induction verifies that the candidate remains unchanged at every relevant decision. Its minimum ready invested buffered headroom is +3.20924175 USDT and no shadow trigger occurs; that is not by itself the full proof. Its original five-open terminal is full-calendar but **not paid-flat**, with marked PnL 1,612.84101423 USDT and paid-cash PnL null. Any no-op reuse must preserve this failure.

This study provides mechanism evidence only. Economic net returns, paid-flat completion, actual fees/funding and comparison against 2021/2023/2024 controls remain NOT_RUN for the candidate.

## Publication scope and retained trigger evidence

The public package contains frozen feature/scanner/test code, exact source/old-ledger identities, independent review receipts, complete population counts and unavailable coverage, and the 2024 XRP first/last witnesses. An attached commit preserves all 2,137 nonempty trigger rows in four lossless CSV.xz files under their original scan/year paths, referenced by pre-existing content-addressed Git blobs without retransmission. TRIGGER_ARCHIVES identifies their Git SHA, compressed size, original CSV SHA256 and row count. Remote validation is exact tree blob SHA/size; binary full-content restoration through the connector was NOT_RUN because it rejects binary UTF-8 decoding.

The original complete 25-file detailed output set remains unchanged in the research workspace and is SHA-bound by OUTPUT_MANIFEST and independent output review. The sixteen empty CSV headers and the full per-episode result JSONs are not duplicated in this public package; their zero populations, complete coverage counts and 62 interval counts are included in COMPACT_RESULTS, while the XRP first/last detailed witnesses are published. Do not claim that all 25 files can be restored from Git alone.

Reproduction of the complete scan requires the exact existing monthly source NPZs and genuine original account DAY/POINTER files named by INPUTS, including the derived-cell identity CSV. This package does not make those external inputs remotely available. Published trigger archives preserve observed flags and posterior capacity labels, not a changed account path, paid-flat result or counterfactual PnL.
