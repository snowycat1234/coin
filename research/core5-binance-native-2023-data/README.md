# CORE5 public Binance native minute inputs, 2023

Bounded task: obtain the missing original USD-M 1m trade and mark archives for
July/August/September and October/November/December 2023. The requested native
intervals are [2023-07-03, 2023-09-04) and [2023-10-02, 2023-12-04), UTC, for
BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT in that order. Each interval requires
90,720 minutes per asset per family. Full months preserve source context before
each requested start. Daily and funding contexts are existing separate inputs.

Authorization explicitly permits official public downloads and public GitHub
research-data storage. The initial budget is 150 MiB of original compressed
archives across both folds; `INVENTORY.json` declares 77,522,788 bytes (73.93 MiB),
including 37,862,875 for July and 39,659,913 for October. No H1 or OKX files,
funding downloads, fits, or backtests are requested. Stop for an access denial,
checksum mismatch, invalid source clock/price, or an expected budget excess;
do not bypass restrictions, invent missing minutes, or alter active branches.

`acquire.py` checks the official S3 listing, exact archive HEAD size, and official
CHECKSUM before bounded downloads (four workers). Original ZIP SHA256, size and
CRC are verified. `validate.py` imports the existing normalizer from source
commit `0090a7182c75a655197afd85f4db2c66db6456f6`, checking its SHA256 bindings.
It adds an independent full-minute-grid check, verifies completed-minute
availability and unchanged quote-USDT volume, and checks exact Parquet round
trip equality. It creates the normalizer's standard native minute directory
layout locally; no daily/funding input is synthesized. These are data checks,
not a native strategy performance result.

`pack.py` stores unchanged original exchange ZIPs, CHECKSUM sidecars, and source
and validation receipts in a ZIP_STORED wrapper, split into files of at most
768 KiB. Each fold's `INDEX.json` binds every part, wrapper, and original member
by SHA256 and size. Normalized Parquets are derived locally rather than stored
twice. `recover.py` retrieves only immutable public GitHub commit URLs, checks
all part and wrapper hashes, and verifies every recovered original against its
official CHECKSUM and ZIP CRC. It refuses an existing output directory.

With the project dependency environment and applicable bounded launcher:

```bash
python research/core5-binance-native-2023-data/recover.py \
  --commit <full-data-commit> --fold JULY2023 --output /own/state/recovered-july
python research/core5-binance-native-2023-data/validate.py \
  --root /own/state/recovered-july --source-root /own/coin --fold JULY2023
```

Normalized files are under `<root>/<fold>/normalized/data/normalized/minute/`.
The consumer must bind its existing daily/funding contexts, native execution
recipe, and source identity. A `VERIFIED_COMPLETE_TRADE_MARK_MINUTE_INPUTS`
status describes only this minute-input scope. The official timestamp is epoch
milliseconds; minute availability is the exclusive close in microseconds.
Trade quote volume remains USDT. No mark, funding, or volume is fill-forwarded.

All cloud Python commands used the existing unchanged resource monitor with
one CPU, 2,000,000,000-byte address/RSS limit, swap=0, GPU=0. Resource receipts
are provided separately. This isolated branch leaves active research branches
unchanged and must not be merged as a strategy or economic result.

Both requested intervals passed: 90,720 observed minutes per asset per family,
zero missing minutes, and the immediately previous boundary minute present.
All 60 complete source months passed clock, OHLC, checksum, and exact canonical
Parquet round trip checks. Source quote-USDT volume, including observed zero
volume minutes, is retained. All original exchange ZIPs are published without
recompression; parts and recovery receipts are source-bound in each fold index.
July was published first at `88d6ff788dad5ce68efee1a200605f506c067339` and all
49 parts were independently downloaded from immutable GitHub URLs and checked.
The latest branch adds October and the remote recovery receipts. Use the
immutable data commits in `receipts/*-REMOTE-RECOVERY.json` for recovery.
