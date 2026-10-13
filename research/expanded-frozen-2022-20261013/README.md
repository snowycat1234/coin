# Full-2022 frozen five-arm source and target preflight

This is a pre-target, pre-wallet development-year packet. No 2022 target
matrix or 2022 economic score has been generated. The full calendar is
2022-01-01 through 2023-01-01 exclusive, 365 UTC decisions and 525,600 native
minutes per future independent wallet.

The daily target source is the **whole original Y2023.npz**, SHA256
`1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f`.
All 365 days have full-five contiguous finite positive 200-close warmup;
2022-01-01 begins with 2021-06-16. The canonical weekly rank backstarts at
2021-12-27, so it must not be reset on Jan 1. The alternative original
Y2025 cube has ten SOL/XRP finite-to-NaN differences during Feb–Apr 2022;
no splice or replacement is valid. True trade-minute daily-close parity
remains a source gate.

`targets_2022.py` copies the exact frozen 2024 five-arm formulas, changing
only calendar/input/output and requiring a separate `--parent-go` to create
the 2022 target packet. It SHA-pins four original target/risk modules and
bit-exact reproduces both original 2023 and 2025 saved four-arm matrices
and annual covariance. `preflight_2022.py`, `PROTOCOL.json`, and
`test_frozen.py` contain no 2022 target generation or financial scoring.

`GIT_ARCHIVE_MATRIX.json` inventories 110/120 SHA-bound original CORE5
monthly 1m trade/mark ZIP receipts for Jan–Nov 2022 on the project's public
Git branches. This task has not reassembled those originals locally. The
remaining five Dec trade and five Dec mark monthly originals were not
identified in the reviewed public Git manifests. A direct official archive
HEAD timed out in this environment, and the cloud browser could list an
official December object but was blocked from opening its checksum; this
route was stopped. There is no provider-download ETA here.

The locally present original public `features.zip` funding archive has five
2022 event tables and 5,550 actual recorded rate/event rows. SOL's 1,170
events include 2h and 4h intervals; it cannot be forced into 2024's fixed
8h event slots. Eighteen saved prior-mark fields are null on BTC July31–Aug1
or all five assets Oct2–3, where genuine daily mark repairs have been
published. Any used prior mark must be revalidated from actual bars. Raw
unit/arrival and exact charge-mark authority remain conditional.

Official monthly/daily source unions still leave **27 actual missing mark
minutes** on July 12–13, 2022. Exact runs are ETH July12 12:57 (1), 13:07
(1), 13:15–13:21 (7), 13:52 (1), and July13 06:59 (1); SOL July12
13:16–13:21 (6); XRP and DOGE July12 13:17–13:21 (5 each). They are
recorded in the project's public Q3 mark cold recovery. No 2022 mark gap
interpolation has been authorized or applied. The original-source full-year
native gate remains closed even after recovering the December ZIPs unless
genuine mark observations resolve these gaps or a separately approved,
clearly labeled sensitivity is frozen.

To rerun this non-economic preflight with the companion restored sources:

    python coin_2022_frozen_coverage_20261013/preflight_2022.py
    python coin_2022_frozen_coverage_20261013/targets_2022.py \
      --repo coin_cs_sma_recovery_20261013/repo \
      --inputs coin_cs_sma_recovery_20261013/inputs \
      --saved coin_strong_candidates_20261013 --verify-history
    python -m unittest discover -s coin_2022_frozen_coverage_20261013 \
      -p test_frozen.py -v

No protected 2026 March–September data, credentials, live accounts, paid
resources, Library, target outputs or economic wallets were used.
