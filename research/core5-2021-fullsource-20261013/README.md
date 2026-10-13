# CORE5 full-2021 source gate

Source only. No new targets, models, wallets, provider downloads, Library actions or retained-2026 reads.

2021-01-01 00:00 UTC through 2022-01-01 00:00 UTC: five assets, two real minute domains, 525,600 minutes per asset/domain. All 120 monthly streams close exactly. Fifteen actual daily mark repairs add 21,600 absent original-month minutes. No forward fill or trade/mark substitution.

Actual funding: 5,475 events with original millisecond timestamps and reported eight-hour intervals. Strict-prior marks are rebuilt from real minute closes for 5,470 events. The five initial events precede the declared fresh-CASH first execution; their missing pre-2021 minute boundary stays UNKNOWN. Authoritative funding-rate units and historical publication/arrival times remain unconfirmed.

Daily OHLC: 1,825 complete cells; all close bits match the existing saved cube. The saved 21-/31-close windows are available on all 365 decisions. The 200-close asset masks preserve DOGE readiness from January 26 and SOL from April 2. Fullfive-200close January 1 is not admitted. Pre-2021 warmup is saved-daily provenance, not newly reacquired minute tape.

## Minimal reconstruction

Use Python 3.12, NumPy 2.3.5, pandas 2.2.3 and PyArrow 23.0.1. Preserve one CPU, a 2GiB per-process address-space ceiling and 15GiB free disk.

1. Materialize the existing public parts listed in evidence/Y2021_INDEX.json at commit 94fe13c494c82bb6e6868e6614eb7298fb15b3c3 into source/Y2021_parts; materialize the ten December mark parts listed in evidence/DEC2021_RECOVERY.json at a23f8cc36bdaddce832b2305a16fda493d1cf764 into source/DEC2021_parts/<symbol>. Reuse SHA-valid cached parts. restore_public_sources.py is a pinned public-Git-only transport option when its network route is permitted.
2. Set COIN_CUBE_PATH to the existing Y2023.npz (SHA256 1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f) and COIN_FEATURES_PATH to the existing features.zip (SHA256 bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30). Their original public locators are in REPRO_MANIFEST.json. Do not replace missing source data.
3. Run, in order: test_source_parser.py, audit_warmup.py, audit_funding.py, assemble_offline.py, prepare_full_2021.py, verify_few_boundaries.py. The scripts are standalone Python entrypoints. A fresh output directory is required; COIN_2021_SOURCE_OUT can select it for preparation.
4. Match reconstructed month/file hashes to SOURCE_INDEX.json. Runtime timing, memory and disk fields can vary. Preparation also enforces the exact raw input hashes, complete clocks, official CHECKSUMs, CRCs, original daily close bits and strict-prior causal marks.

Only compact code, receipts, masks and reconstruction indexes are saved here. No original market ZIPs or rebuilt price NPZs are uploaded again. Fixed-target and wallet admission remain separate gates, including causal masks and declared terminal quote semantics.
