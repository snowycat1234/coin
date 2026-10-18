# SMA2025 persistent v2r1 recovery publication

This publication preserves a completed 2025 DEV run and complete saved outputs.
The immutable ZIP is represented by raw-byte parts listed in ARCHIVE_PARTS.json.
All 308 members and 96 financial-kernel closure members are preserved, including
all 11 actual annual outputs and the intact 43,274,761-byte minute NPZ.
The inner preparation-stage README/receipt statements describe local packaging;
this outer publication is a later transport step. No new financial run occurred.

## Result

The 10,000-USDT wallet ended paid-flat at 9,829.62804019943618961520 USDT.
Net 2025 DEV return: -1.70371959800563810384800%; the 20% target was missed.
Minute-close maximum drawdown: 12.2639769534%.
Daily-return annualized realized volatility: 11.87980714%.
Forecast sigma of actual held positions reached 24.2095%; the 10% admission
target was not a continuous held-position hard risk cap.
The saved-record arithmetic audit passed. See results/AUDIT_REPORT.md and
results/FULL_YEAR_ECONOMICS.md for exact assumptions and limitations.

This is a newly implemented persistent policy/adapter/daily caller bound to
restored published kernel and signal source. It does not establish equivalence
to the lost unpublished engine. An old different-engine 2022 result cannot be
stitched to this new-version 2025 result. All inputs are seen DEV. No OOS,
live-ready, certified regime-performance or reliable long-term APR claim follows.
Funding units/arrival, historical venue filters/risk tiers and native liquidation
status remain uncertified. This record does not authorize trading or a rerun.

## Restore and verify without network or financial execution

Download this directory, preserving raw part bytes, then run:

    python reassemble_archive.py --verify-only
    python reassemble_archive.py --output /new/path/SMA2025_PERSISTENT_V2R1_RECOVERY_20261018.zip
    python verify_packet.py --zip /new/path/SMA2025_PERSISTENT_V2R1_RECOVERY_20261018.zip

The helper requires a new absent output, checks part names, offsets, lengths,
SHA256 and Git blob SHA1, and verifies the whole length/SHA256 before success.
No market data is downloaded or duplicated by either helper. Follow
packet_metadata/README.md for separately authorized public-Git source-cache
restoration only if required. Raw market ZIP and canonical monthly cache bodies
are deliberately omitted; their immutable existing public-Git inventories remain.
Source-cache reconstruction was not rerun for this publication.

## Attribution and licensing scope

Binance Vision source-data extracts and data-derived numerical material are
CC BY-NC-SA 4.0. Read DATA_ATTRIBUTION_AND_LICENSE.md and
DATA_DERIVATIVE_SCOPE.json, which accompany the immutable archive and apply to
its identified data-derived contents. Keep these sidecars when redistributing.
Existing source/code licensing remains unchanged; no repository-wide code
license is introduced. No provider endorsement is implied.

## Exact archive identity

Archive: SMA2025_PERSISTENT_V2R1_RECOVERY_20261018.zip
Bytes: 46,161,099
SHA256: bcf7382a8fce51ae83d18ef1a8ca70c70635126a553e89b3ca51a9e94ab98d17
Manifest SHA256: aab82302a10bf006915f3791913df67f7d35b455b0bfd9337676812d5980f46e
Terminal proof SHA256: 6793008b479ca39e5520a1390b6f7f80aa65e7cd660f803e03f7cd23c5d89815

PACKAGE_RECEIPT_LOCAL_PREPARATION.json is the immutable local preparation
receipt, not evidence of remote publication. Remote verification is recorded
separately by the publisher after the branch exists.

## Separate completed-study addendum

See studies/README.md and the separate addendum ZIP for the frozen mark/trade
event and exact-cost/capacity screens with independent reviews. These are
post-SMA descriptive studies; their event mean is not APR. The October 10
contribution is 121.63%; five fixed exits leave explicit unpriced residuals.
The original SMA ZIP remains unchanged. The attribution sidecar also covers
these studies’ source extracts and data-derived numerical portions only.
