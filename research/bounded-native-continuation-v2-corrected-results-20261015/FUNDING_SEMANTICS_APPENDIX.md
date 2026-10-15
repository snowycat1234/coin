# Corrected V2 funding appendix: saved-data-only check

Review date: 2026-10-15 UTC. Both corrected B/C terminal files were saved before this check. This appendix is separate from the preserved diagnostic V1 report. No account replay, new financial run, source download, code edit, or upload was performed.

## Conclusion

The corrected paths retain zero same-symbol fills within 15 seconds of funding. The original V1 finding is now independently established for corrected V2; it is not inferred from the diagnostic paths. Funding archive units, historical publication/arrival, and actual charge-mark authority remain conditional.

## Corrected saved results

- B, CONTINUE_ONLY: FULL_CALENDAR_CONDITIONAL_SETTLED_FLAT; 527,040 completed minutes, 323 fill legs, 5,490 funding rows, 4,990 owned rows.
- C, TOPUP_THEN_CONTINUE: FULL_CALENDAR_ACTUAL_PAID_MARKET_FLAT; 527,040 completed minutes, 320 fill legs, 5,490 funding rows, 5,018 owned rows.
- Both saved funding projections exactly equal admitted 2024 EVENTS.json, in order and in all four raw fields: symbol, event_us, raw_rate, reported_interval_hours.
- Both have zero exact timestamp overlaps, zero same-symbol fill legs within five seconds, and zero within fifteen seconds (inclusive bounds).
- Closest pair in both: BTCUSDT CLOSE fill at 2024-11-12T00:01:00.000001Z (1731369660000001) versus funding at 2024-11-12T00:00:00.002000Z (1731369600002000). Exact positive separation: 59,998,001 microseconds = 59.998001 seconds.
- B owned mark ages: 4,230 at exactly 60 seconds; 760 at 1–15 ms.
- C owned mark ages: 4,254 at exactly 60 seconds; 764 at 1–15 ms.
- Each case has 5,485 mark-bearing rows: 4,635 at 60 seconds and 850 at 1–15 ms; five fresh-flat rows have no mark.

All four final terminal checkpoint hash bindings pass in each case: native result, case receipt, financial audit and primary reconciliation. Every mark-bearing funding row has mark_close_us strictly before event_us, while stored rate_available_us equals event_us. All rate scales remain 1, raw units remain UNCONFIRMED, and publication labels remain EVENT_TIME_CONDITIONAL_NOT_CERTIFIED.

## Interpretation and comparison

V1 B/C fill counts were 353/359 and owned funding counts 4,844/4,846. Corrected V2 counts are 323/320 and 4,990/5,018. The nearest fill separation changes from 59.993001 to 59.998001 seconds. Therefore corrected paths changed exposure histories but did not introduce a recorded near-funding fill in the tested window.

The 60-second versus millisecond mark-age discontinuity persists. These ages describe the chosen strictly-prior closed-minute proxy; no actual funding-charge mark is present to measure its true error. Zero near-event fills does not certify provider clock semantics or arrival.

The [current Binance funding FAQ](https://www.binance.com/en/support/faq/detail/360033525031) motivates the fifteen-second diagnostic. Today's stated rule is not treated as proof of 2024 rules. The [current history API](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data#get-funding-rate-history) uses fundingRate/fundingTime and an associated charge mark; the exact archive field mapping remains unverified. See the preserved V1 report for the full provenance and missing-evidence discussion.

## Immutable identities

- Admitted 2024 EVENTS.json SHA256: 44c91c0310974527e850c280ab073c07668160b9ee947471cd64a03269d93dbb
- Corrected B NATIVE_RESULT.json SHA256: d08b714a923c0019e6245db6f583068fd529982b611e26f9efc860d4fff84aea
- Corrected C NATIVE_RESULT.json SHA256: 888587d430fea9648f37b2b0b84eb3647f9efc76ace0089f77cceecd6c250197
- Preserved V1 REPORT.md SHA256: 86527d62dfee89c897d4f4f9d20a77ff9839e07d305fca92de2418f91e78e5c1
- Preserved V1 EVIDENCE.json SHA256: 5d00cfd09a80262256b6a03aab67651ae74901847ac2ca76239783c6a7165dcc

V2_EVIDENCE.json contains exact hashes/sizes of all fifteen inspected input files, checkpoint checks, full mark-age histograms and the closest pairs. All input identities were rechecked after analysis. The original V1 files remain byte-identical.
