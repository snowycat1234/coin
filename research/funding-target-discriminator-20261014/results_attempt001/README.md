# Exact CSH target-only result, single ATTEMPT001

The one authorized frozen pass completed successfully on 2026-10-14 at
01:17:56.807963 UTC, exit 0, following an actual 01:17:51.707117 UTC start.
The target engine took 4.962 seconds; no retries or parameter changes occurred.

Full natural-calendar candidate versus same-lag-control target differences:
- 2021: 0 of 365 days; 0 changed asset-days
- 2023: 7 of 365 days; 35 changed asset-days
- 2024: 14 of 366 days; 70 changed asset-days
- 2025: 7 of 365 days; 35 changed asset-days

The four exact changed intervals, with exclusive end dates, are
2023-10-02 to 2023-10-09, 2024-03-11 to 2024-03-18,
2024-09-16 to 2024-09-23, and 2025-06-02 to 2025-06-09.
All five sized weights differ during each interval under unchanged original
CS/HOLD matching and STATIC50 risk allocation; this is not five new signals.
All 1,461 calendar outputs are preserved, including 1,433 zero-delta days.
No required owning-rank source gaps feed an admitted output.

The 2021 result includes the previously omitted activation context:
March 29 CS31 ownership is funding-source ready and has identical paired raw
baskets; April 2 original daily admission activates an identical nonzero CSH
target from that ownership rank. The initial three source-unready owning days
never feed admitted outputs and remain original mandatory cash. There are
274 admitted days and 91 original mandatory-cash days in the full calendar.
This now establishes conditional full-year target identity versus the
same-lag control, beyond the prior result's narrower 0/39 weekly scope.
The prior completed result and its serialization failure are unchanged.

The primary control delays both rank price endpoints by the same 24 hours as
the candidate's price/funding window. Original unlagged strategy improvement
is not evaluated. Current-31 daily risk remains unchanged in both arms.
Raw funding scale 1, actual observed event sums, the availability assumption
and retrieved-project/archive-only completeness remain conditional; provider
completeness, publication and actual charge times are uncertified.

These are target identities, not returns or wallet results. No future returns,
funding cash, costs, turnover, account/NAV, models, provider requests or closed
holdouts were evaluated. A changed target proves no economic advantage.
No constant-notional funding or |delta weight| turnover proxy is used.

RAW_CS_RANKS.jsonl.gz and DAILY_TARGET_PROOF.jsonl.gz decompress byte-exactly
to the saved 212 ranks and 1,461 daily proof records. LOSSLESS_RECORDS.json
retains both uncompressed and compressed identities. The four NPZ files retain
exact paired daily targets, clocks, ownership, admission, readiness and shared
covariance. NumPy can read them with allow_pickle=False. SUMMARY.json is the
original successful output, not a recomputed summary. Cold checking these
saved values requires no historical runner or source-signal recomputation.

Scientific preparation: manifest ec933f33144bb853cef6cbd877c69f23f6896f6f74cf652cbc7f28be7736b05e,
review 6ebe39e3e9f48f6ab5af3609de848ef2087c2069d6cf1fac55da0070c158b0e8,
remote checkpoint 234cf00ac35fec3a0a8aaa88bbed953f5b9d3c41.
