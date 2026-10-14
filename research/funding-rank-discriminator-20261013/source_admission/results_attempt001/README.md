# One attempted funding-adjusted CS21 basket pass

The sole historical pass started 2026-10-14 00:36:15.647837 UTC and stopped
00:36:16.801290 UTC, exit 1. All 212 rank records and independent checks were
completed and saved. The final readable summary failed to serialize a NumPy
int64 count. The failed attempt, exact records and original frozen runner are
preserved; there was no historical rerun.

`RECONSTRUCTED_SUMMARY.json` is an authorized reporting-only reconstruction
from those exact saved records. Its helper validates all year/rank/date roles,
ownership context, conditional source readiness, event-ID intervals and
independent proof values. It imports no scoring engine and recomputes no
signals, ranks, baskets or future returns. The original frozen code remains
byte-exact in the source module and commit ef3ff4060aee888568ef8490aef749d6fa0f8634.
An additive serialization-fixed code copy and tiny synthetic regression are
included for future reproducibility; that copy has not run on history.

## Complete full-calendar result

| Year | Scheduled ranks | Paired ready | Original cash | Rank-order changes | Signed basket changes |
|---|---:|---:|---:|---:|---:|
|2021|52|39|13|1|0|
|2023|52|52|0|4|1|
|2024|53|53|0|5|2|
|2025|52|52|0|2|1|

There are no missing required original-active ranks or ownership contexts.
Three preceding ownership records are separate context, never extra scheduled
observations. All 212 saved records report independent PASS. There are no
fully tied scores on paired-ready ranks. Twelve rank-order changes result in
four signed basket changes across 196 admitted weekly ranks, about 2.04%.

All four changed episodes remain included, in fixed original CORE5 order
BTC/ETH/SOL/XRP/DOGE:

|Date|Same-lag price-only basket|Funding-adjusted basket|
|---|---|---|
|2023-10-02|+.15/−.15/+.15/0/−.15|+.15/0/+.15/−.15/−.15|
|2024-03-11|−.15/+.15/0/−.15/+.15|0/+.15/−.15/−.15/+.15|
|2024-09-16|0/−.15/−.15/+.15/+.15|+.15/−.15/−.15/+.15/0|
|2025-06-02|+.15/+.15/−.15/0/−.15|+.15/+.15/0/−.15/−.15|

2021 is an exact raw-basket no-op relative to the identical-lag price control
on its admitted original support. This does not establish identity with the
original unlagged strategy or native wallet. The other years establish sparse
feature-selection changes only, with no evidence of economic advantage.

## Authority and limits

The fixed score is simple21day price return minus actual observed raw rate
sums over the same lagged interval. It is an approximation, conditional on
raw-fraction scale one. Completeness is relative to the SHA-pinned retrieved
project/archive event set only. Provider completeness, historical publication,
actual charge clock and funding units are uncertified. Unknown raw intervals
remain unknown. Original weekly clock, all-five masks and stable ties remain
fixed. No wallets, fits, provider requests, financial backtests, future outcome
inspection, adaptive subsets or retuning occurred.

`RANK_RECORDS.jsonl.gz` is a deterministic lossless compression of the original
1,947,533-byte record body, SHA256
cc0536ff885071ccc6793c0f6ce639a826b493fb5767d24efb500c5c031c9e06.
Decompress it and verify that exact identity before inspecting results. The
public launch receipt retains the serialization failure while the original
traceback containing absolute runtime paths stays private. This publication
does not authorize another historical pass, financial simulation or model.

For a saved-output-only cold check, run from this package directory:
`python -c 'from reconstruct_saved_summary import reconstruct; print(reconstruct())'`.
The helper reads the compact records and failure/start receipts here when no
original local attempt exists. It needs no market-source input or NumPy.
