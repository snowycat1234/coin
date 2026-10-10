# Fixed July2024 CORE5 economic and native-minute data

**Daily economic inputs are ready; full native minute coverage has two unresolved
mark bars per asset.** This completes the 63 observed 00:01 execution prices and
62 held funding intervals for every CORE5 asset in the frozen
[July2024 protocol](https://github.com/snowycat1234/coin/tree/6cdddbe57485066e2a98a0042da398494f55b709/research/temporal-july-frozen-transfer-20261010).
It does not establish a minute-native performance result or complete the
model task's remaining serialized feature rows.

The interval is [2024-07-01, 2024-09-02), UTC. CORE5 order is BTCUSDT, ETHUSDT,
SOLUSDT, XRPUSDT, DOGEUSDT. The unchanged 63-decision convention has 62 active
intervals, with paid flattening on **2024-09-01 00:01:00.000001 UTC**. No
September2 economic outcome or synthetic terminal row is supplied.

The subsequent user authorization permits missing official minute/funding
archives with a 180 MiB cap. It supersedes only the earlier protocol's
acquisition restriction; the protocol bytes, period, model/scaler, primitive
features and economic contract are unchanged. No new interval, fit, inference,
wallet, price substitution, credentials or CFTC request was made.

60 original official ZIPs total **28,332,709 bytes (27.02 MiB)**: monthly
July/August trade/mark minutes; daily June30 boundary-context and September1
minutes; small monthly July/August/September funding reports; and five
targeted August12 daily mark files to check the actual source gaps. The first
55 bodies were reused during the supplemental pass rather than downloaded
again. Earlier tasks supplied no matching raw2024 archive; cumulative new
official archive bodies are 28,332,709 bytes. Listing/HEAD sizes and official
CHECKSUM SHA256s were verified before each acquisition, then size/SHA/ZIP CRC
were checked. June30 supplies genuine prior boundary marks/quote context.
Raw September funding reports contain the remainder of that month, because
the monthly report is the original archive unit; only events before September2
enter the normalized requested-domain table.

| Input per CORE5 asset | Verified coverage |
|---|---:|
| Trade minute rows in requested interval | 90,720 / 90,720 |
| Mark minute rows in requested interval | 90,718 / 90,720 |
| Actual 00:01 trade OPEN execution prices | 63 / 63 |
| Actual held event-funding intervals | 62 / 62 |
| Requested-domain funding events with strictly prior source marks | 189 / 189 |
| Funding events held until paid close | 186 |

The missing mark bars have original open timestamps **2024-08-12 10:02:00 UTC**
and **10:03:00 UTC** (`1723456920000`, `1723456980000` milliseconds), for all
five assets. Both monthly and daily official files omit them. Each daily file
has 1,438 observed rows; all 1,438 overlapping values exactly equal the monthly
source, and it supplies zero additional rows. No fill-forward, interpolation,
trade-as-mark or synthetic zero was used. Native consumers must preserve this
gap and apply the original missing-mark stop/diagnostic rules; this pack must
not be labeled a complete native minute tape.

A bounded official recovery probe on 2026-10-10 is **NO_GO**. The documented
`GET https://fapi.binance.com/fapi/v1/markPriceKlines` request for BTCUSDT,
`interval=1m`, `startTime=1723456800000`, `endTime=1723457159999`, `limit=6`
spanned 10:00 through 10:05 UTC. At 02:36:15 UTC it returned HTTP 451 with an
explicit restricted-location denial. That route stopped after its first
request, without retries, other symbols, alternate hosts or location bypass.
No API bars were returned, so API neighbor comparison was not run and record
existence remains unknown. No repair or source precedence was applied.

Only the ten small official CHECKSUM sidecars were reread; all were
byte-identical to the first acquisition and matched the cached archive hashes.
No archive ZIP was downloaded again. The four observed neighboring bars in
the requested window match exactly between the cached daily and monthly
archives for every asset, including all twelve numeric columns. The official
correction log at `binance/binance-public-data` commit
`f446ce3812bd4e5521f21faecd4ae3c6460e49fc` lists only 2022 updates and no
applicable correction. See `receipts/mark-gap-api-NO_GO.json`, the preserved
response and bounded audit receipt. All ten missing native marks remain
unfilled; existing economic array and original-pack hashes are unchanged.

The frozen normalizer's `numeric_csv`, price/funding validators, `canonical`,
`aggregate_price`, `mark_funding` and `funding_windows` are imported directly.
Their four source/dependency hashes match the original68 source manifest at
`b8299bc22321b9dadf707f14da83ac40a39b5491`. Original event milliseconds and raw
signed rates are retained, with unchanged source/charge-clock and rate-unit
proxy assumptions. The strict-prior clock was independently checked as
`((event_us - 1) // 60000000) * 60000000`, including exact-boundary events.
Every mark matches that actual source minute's close. Independent event sums
agree with the signed quantity-denominated funding coefficients to at most
3.553e-15. Source quote-USDT volume is unchanged; canonical Parquet round trips
preserve values and types. There are zero observed zero-volume trade minutes
inside this interval.

`JULY2024/INDEX.json` uses the existing `CORE5_NATIVE_MINUTE_ORIGINALS_PARTS_V1`
format, part names and SHA256/size bindings; parts are at most 768 KiB.
The ZIP_STORED wrapper contains unchanged originals and CHECKSUM sidecars,
raw/validation manifests, compact economic Parquets, and `ECONOMICS.npz`.
Native minute Parquets are derived locally to avoid storing the same large
minute data twice. `recover.py` adapts only the existing recovery prefix/fold,
verifies each remote part/wrapper/member, then each recovered official ZIP.

The original pack was recovered from immutable public commit
`58e333b03adc72ddd8bd8503340fb5998aa892fd`: all 37 remote parts, all 60 official
archives and their original SHA/ZIP CRC checks passed. Local canonical
restoration from those recovered bytes completed successfully. Every one of
the 56 derived artifact sizes and SHA256s exactly equals the first validation,
including native minute Parquets and the economic array. The restored coverage
and supplementary source checks also agree, including the two genuine mark
gaps. See `receipts/REMOTE_RECOVERY.json` and `receipts/RESTORATION_CHECK.json`.
`verify_restoration.py` reproduces the comparison of two restored roots; it
does not acquire data.

```bash
# Use the existing project bounded launcher and an unoccupied output path.
python research/core5-july2024-native-data/recover.py \
  --commit <immutable-data-commit> --fold JULY2024 --output /own/state/recovered-july2024
python research/core5-july2024-native-data/validate.py \
  --root /own/state/recovered-july2024 --source-root /own/coin
```

For local minute restoration, copy this module's `protocol/` directory beside
the restored `JULY2024/` directory before the second command. The source-root
normalizer hashes must match the manifest. Restoration does not acquire market
data or invoke a model/wallet. `CONSUMER_INDEX.json` supplies the compact source
and readiness contract.

The same 7,293-byte economic array is also published directly as
`JULY2024/ECONOMICS.npz`, with SHA256
`9c503a8dd01be93dd1b7e0ddeb267a4f6bf38daec20db5ac026b0ea20af774a9`,
so the model task can fetch it without the original-archive pack.
`ECONOMICS.npz` contains `decision_us[63]`, `execution_us[63]`,
`prices[63,5]`, `funding_interval_start_us[62]`,
`funding_interval_end_us[62]`, `funding_coeff[62,5]` and `symbol_order[5]`.
It has only observed execution rows and actual held intervals, with no
terminal padding. The model task must apply its unchanged terminal convention
and bind these new economic-data hashes explicitly. It must retain/rebuild
features from its original ten-asset primitive tables; these economic daily
tables are not replacements for those feature tables. The prior retained
July1 economic value was not independently compared here because those
original20 table bodies are not in this cloud cache; new values are fully
bound to official originals. Frozen code identity does not imply identical
historical market-source bytes.

All Python stages used the existing unchanged one-CPU, 2 GB address/RSS monitor,
swap=0/GPU=0. Receipts include the initial validation stop on the real mark
gap and the successful final execution/funding validation. Only this isolated
research data module changes; no active implementation or branch was edited.
