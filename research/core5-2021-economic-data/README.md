# CORE5 2021 economic packet

Fixed January 1–December 31, 2021 calendar: **365 real decisions, 364 distinct eligible active intervals, one separate episode**. It starts from fresh CASH and requires a charged final CASH decision at December 31 00:01:00.000001 UTC. No economic dates or held intervals are excluded after source validation. No 2020 decisions, January 2022 held outcome, training, inference, backtest or wallet was added.

[Y2021/INDEX.json](Y2021/INDEX.json) is the consumer entry point. Concatenate its ordered parts and verify every part, wrapper and member hash. All parts are at most 768 KiB. The wrapper contains 130 unchanged official ZIPs/checksums, compact execution/funding Parquets, original context targets and masks, explicit episodes/exclusions, and an unpadded economic array. Existing feature history, original ten-asset aggregates, signed funding and December event marks are referenced at immutable feature commit `e0d3400b23842f11f167a63e7d80856d76501de8`.

Acquisition used **164,656,739 bytes (157.0289 MiB)** of new official archive bodies, below the 180 MiB cap. The initial 115 monthly files used 164,149,016 bytes. BTC, SOL and XRP monthly marks omitted July 1 and July 24–27, totaling 21,600 source minutes. Fifteen targeted official daily mark files added exactly those real missing minutes for 507,723 bytes. Original holes and source provenance remain recorded; no interpolation or synthetic observations were used. All trade minutes and January–November mark minutes are complete after this repair. December's full native mark tape was not reacquired or published.

Independent raw-CSV checks verify all 1,825 actual 00:01 OPEN execution prices, all 1,825 preceding completed-minute quote-USDT observations, and 5,010 freshly sourced owned funding marks. Another 450 owned December marks match immutable cached actual event values and latest strictly-prior completed-minute clocks. All 5,470 retained signed event records, including both bracketing events per asset, preserve original timestamp, rate and nominal hours. The first unowned January 1 midnight mark remains UNKNOWN; it is not needed by fresh CASH. Actual zero-volume source minutes remain present, and all execution-point preceding quote volumes are positive.

Original E5 slots remain CASH=0, VOL=1, CS=4; the published target axis explicitly names these slots. Original fixed-five `(30,5)` finite past returns are ready for every decision. The original target functions reverify DOGE VOL eligibility from January 26 and SOL from April 2, retaining 25 and 91 earlier per-asset VOL exclusions respectively. CS membership is available throughout. Existing per-feature/time masks, including missing premium observations, remain unchanged. There is no all-64-complete or ready256 admission gate, scaler fit, pool change, or selection by returns. Historical completed-day publication proxies and the existing conditional funding-unit/cross-venue cost contract remain as before; this packet is not a native December minute-tape certification or a performance claim.

Run these commands through the project's approved bounded Python launcher, with the full immutable package commit from the publication receipt:

```sh
python research/core5-2021-economic-data/recover.py --commit <40-character-commit> --output <new-directory> --cached-feature-archive <verified-FEATURE_ARCHIVE.zip>
python research/core5-2021-economic-data/validate.py --root <new-directory> --source-root <checkout-of-0090a7182c75a655197afd85f4db2c66db6456f6> --feature-archive <new-directory>/FEATURE_ARCHIVE.zip --core-source <new-directory>/protocol/conditional_selector_core.py
python research/core5-2021-economic-data/audit_packet.py --root <new-directory> --feature-archive <new-directory>/FEATURE_ARCHIVE.zip
```

Omit `--cached-feature-archive` to recover its three immutable public parts. The unchanged normalizer and expert dependencies match the branch's `0090a718...` base and are checked by exact source hashes. The archived original expert recipe and causal helper are included unchanged under `protocol/`. Recovery fetches public GitHub parts, verifies SHA-256 and inner/outer ZIP CRCs, and performs no provider redownload.

`ECONOMICS.npz` has prices `(365,5)` and funding coefficients `(364,5)`, explicit execution/interval/maturity clocks, quote-USDT observations and readiness masks. Funding charge is `-signed_quantity * funding_coeff` over `(start_execution,end_execution]`. `EPISODES.json` requires the last decision to be paid CASH. Consumers with the older N+1 loader contract must adapt explicitly; do not manufacture an extra price or funding row. The original context targets at the terminal date are inputs, and do not waive the forced CASH closure. Feature-window references select the unchanged cached feature NPZ; economic completeness is not an input feature.

The independently published expansion adapter at `556fc9d157747a76f28a15d03dd953e6ca44529a` requires a strict seven-field NPZ and fixed economic table paths. [consumer/CONSUMER_INDEX.json](consumer/CONSUMER_INDEX.json) binds that layout. Its 365 real prices, 364 real signed funding coefficients and exact table bytes are copied from the recovered source packet. The richer quote/readiness fields remain in the original packet; no price, funding, date, closure or mask semantics change. `export_consumer.py` verifies this equality, and `check_adapter.py` invokes the actual pinned `load_packet` without a model or scaler fit.

The reviewed wire consumer is immutable commit `1009a6cf6d7c79e3cd914861dc2aeafc3d23709e`, index SHA-256 `3ba1e64d7c91150a73c28642bed46d1dd2325fcf8fa8aade9425164f526d66ba`. All 17 files passed remote readback; the actual adapter accepted prices `(365,5)` and funding `(364,5)` with all entries known. The original source packet at `29030f34a5a2f4b8c83569a42063fef9b2b99545` passed all 212 part hashes and 130 original inner ZIP CRCs, and regenerated 81 identical canonical artifacts. [PUBLICATION.json](PUBLICATION.json) binds this handoff and all exclusions. A harmless adapter warning casts the unowned January 1 UNKNOWN mark clock; every owned interval passes without altering that source value.

For just the small model consumer, use the current helper through the approved bounded launcher:

```sh
python research/core5-2021-economic-data/recover_consumer.py --commit 1009a6cf6d7c79e3cd914861dc2aeafc3d23709e --consumer-sha256 3ba1e64d7c91150a73c28642bed46d1dd2325fcf8fa8aade9425164f526d66ba --output <new-packet-directory>
```

This fetches only 558,517 bytes from public GitHub, verifies every supplied economic table and array by SHA-256, and supplies the directory expected by the expansion adapter. It performs no official provider download.

Validation, independent raw checks, remote readback and canonical restoration receipts are in `evidence/`. All acquisition and verification Python ran with one CPU, a 2,000,000,000-byte address/RSS cap, no GPU/swap, and a 15 GiB disk reserve. After a transient GitHub 503, recovery resumed exact verified parts; `--resume` preserves this behavior for consumers without any provider redownload.
