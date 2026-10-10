# Q4 2024 CORE5 economic and native-minute inputs

The fixed **[2024-10-01, 2025-01-01)** UTC input block is ready. Each CORE5
asset has 132,480 trade minutes, 132,480 mark minutes, 92 actual 00:01 execution
prices and 91 held funding intervals. There are no missing minute timestamps.
CORE5 order is BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT.

This block is reserved for current tuning only. Earlier project research has
already examined this history; it is not pristine out-of-sample data. This
module supplies data and validation evidence. It performs no model fitting,
policy inference, strategy evaluation or wallet simulation.

| Input per asset | Verified coverage |
|---|---:|
| Trade minute rows | 132,480 / 132,480 |
| Mark minute rows | 132,480 / 132,480 |
| Actual 00:01 trade OPEN execution prices | 92 / 92 |
| Held funding intervals | 91 / 91 |
| Requested-domain funding events with strictly prior marks | 276 / 276 |
| Funding events held through paid close | 273 |
| Genuine zero quote-volume minutes, preserved | 89 |

`protocol/PROTOCOL.json` is a **new data-calendar recipe**. Its inherited
clock and normalization source contract comes from
`b8299bc22321b9dadf707f14da83ac40a39b5491`; that old commit did not predeclare
this Q4 block. Decisions run from October1 through December31. Execution
clocks are 00:01:00.000001 UTC, priced at the original 00:01 trade minute OPEN.
The artifact has 92 observed prices and 91 actual funding coefficients, with
no terminal padding or January1 economic outcome. Its terminal clock is
**2024-12-31 00:01:00.000001 UTC**. An evaluation must explicitly bind this
paid-close convention before consuming it.

Funding retains original signed `last_funding_rate` and actual `calc_time_ms`.
The mark is the actual close of the latest source minute whose completed
availability is strictly before the event. The independent timestamp check is
`((event_us - 1) // 60000000) * 60000000`; mark ages range from 1,000 to
60,000,000 microseconds. Each coefficient is the signed sum of rate times mark
per held unit in `(start_execution_us, end_execution_us]`. A signed wallet
charges `-quantity * coefficient`. Independent event sums agree to within
1.422e-14. These checks preserve the frozen rate-unit and funding-charge-clock
proxy assumptions; they do not establish an exchange-native settlement rule.

Quote capacity uses the original `klines.quote_volume` in USDT, preserved
exactly. Complete timestamp grids contain 89 genuine zero-volume minutes per
asset. Consumers must retain those zeros and apply their existing capacity
rules. The source daily economic tables here contain forward execution/day
information and must not replace the causal model primitive tables.

The 55 original official ZIPs total **41,770,327 bytes**. Forty-five monthly
October–December trade, mark and funding archives were recovered selectively
from immutable public source commit
`d69e9ac94478c5be54cb46c622afec7aaf3c61f7`, using exact byte ranges for only
the required stored members. All match fresh official CHECKSUM SHA256s and
accepted project source manifests. Selected outer member CRCs and original
inner ZIP CRCs passed. Whole old source packs and byteparts were not fetched,
so their full-file SHA256 verification is not claimed.

Only ten September30 daily 1m trade/mark context ZIPs were newly downloaded
from the permitted official archive: **452,166 bytes (0.43 MiB)** against the
180 MiB provider-body cap. This genuine prior-day context supports the first
funding prior mark and prior-minute capacity. It adds no supervised decisions.
Listing, HEAD, checksum, length and inner ZIP CRC checks passed. No futures API
route or CFTC route was used for this block.

`Q42024/INDEX.json` uses `CORE5_NATIVE_MINUTE_REFERENCE_AND_DELTA_PARTS_V1`.
The new ZIP_STORED delta includes the ten boundary archives and sidecars,
manifests, 15 compact economic Parquets and `ECONOMICS.npz`. Ordered parts are
at most **768 KiB**. The other 45 originals are referenced immutably in the
packed `PUBLIC_REFERENCES.json`, avoiding another public copy of their bodies.
Native minute Parquets are restored locally. September Parquets contain only
September30 context, while October–December Parquets have complete months.

`recover.py` verifies each new remote part, combined wrapper and member. It
copies referenced originals from an optional SHA-verified cache; cache misses
fetch only the exact stored source member ranges. All 55 recovered official
ZIPs must pass original size, SHA256, sidecar and inner CRC checks. The
unchanged four frozen normalizer dependencies are checked against the original
source manifest before import. Current canonical Parquet SHA256s bind this
producer's encoding; accepted older normalized SHA256s are provenance only.

```bash
# Run through the existing project bounded launcher with a fresh output path.
python research/core5-q4-2024-native-data/recover.py \
  --commit <immutable-data-commit> --fold Q42024 --output /own/state/recovered-q4 \
  --cache-root /optional/existing/Q42024
cp -r research/core5-q4-2024-native-data/protocol /own/state/recovered-q4/
python research/core5-q4-2024-native-data/validate.py \
  --root /own/state/recovered-q4 --source-root /own/coin
```

Omit `--cache-root` to recover all 45 existing originals from their public
references. The source-root dependency hashes must match the supplied manifest.
`verify_restoration.py` compares the 56 derived artifacts and their coverage
between two restored roots without acquiring data. Immutable readback passed at commit
`c2b88a1bf77b59bc21a6591718ca12867020222a`: both new parts and all 55
original SHA256/inner CRC checks passed. Forty-four referenced originals were
reused from a verified cache and one small original was fetched by exact public
ranges; all 45 had already been selectively recovered and verified from the
public source during production. All 56 canonical artifacts regenerated from
these recovered originals have byte-identical sizes and SHA256s, including
native minute Parquets and the unpadded economic array. Coverage evidence also
agrees. See `receipts/REMOTE_RECOVERY.json` and `receipts/RESTORATION_CHECK.json`.

`CONSUMER_INDEX.json` binds the direct economic array, tables, original source
commit, recipe and normalization hashes. `protocol/CACHED_PRIMITIVE_BINDINGS.json`
identifies the already cached original ten-asset daily primitives and the
155 required bars from July29 through December30. All 155 bars per asset have
the original source hashes, complete flags and finite positive closes. These
primitive bodies are reused without republishing or recomputing them. Q4
serialized model features, signal masks and causal contexts remain the model
task's responsibility.
