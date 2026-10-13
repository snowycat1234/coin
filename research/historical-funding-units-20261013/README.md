# Historical funding numeric-chain and fixed-tape audit

2026-10-13 UTC. **原始数值链已证；历史经济单位仍未认证。** This is new evidence, not a zero-progress reclassification of the earlier funding charge-source blocker.

## What is proven

- Read **90 already-retained official funding CSV ZIP bodies**: CORE5 July–December 2024 (30 archives, 2,760 events) and full 2025 (60 archives, 5,475 events). Every one of the **8,235 rows** exactly matches the backtest's prepared event on symbol, original millisecond timestamp converted to microseconds, raw numeric rate and reported 8-hour interval. Both float-value and original decimal-string equality passed. All 2025 rows also exactly match the saved consumer funding Parquet. Individual ZIP/CSV/checksum-or-receipt SHA-256 and example rows are in [SOURCE_IDENTITIES.json](SOURCE_IDENTITIES.json). No provider URL was requested.
- Original e0 Parquet member bytes exactly match all 5,475 prepared 2021 events, all 5,475 prepared 2023 events, and 2,745 prepared 2024-prefix events. The latter includes the July 1 overlap. H1.zip contains the **same member hashes** as e0; this is replicated storage evidence, not an independent original source. H1 has no raw funding bodies. The 2024 prefix plus H2 raw stream has 15 overlapping CORE5 events; the prepared full-year stream contains 5,490 unique events, with no duplicate charging.
- All four complete source streams retain 8-hour nominal intervals and original millisecond jitter. Maximum within-8h timestamp jitter is 47ms (2021), 29ms (2023), 15ms (2024) and 16ms (2025). The code's only event-clock conversion is milliseconds ×1,000. Rates are neither percent-scaled nor hourly-normalized. Interval hours validate spacing; they are not a factor in the charge formula.
- Independently checked eight existing recorded account tapes, totaling 43,830 funding receipts. Event IDs are unique, source rates are exact, unowned events have zero cash, and every owned charge equals **−recorded quantity × recorded strictly-prior mark × raw numeric rate**, within 1e-30 USDT. The recorded signed funding sum agrees with the separate Decimal NAV bridge. This rejects a hidden ×100/÷100, interval multiplier, or double charge in these named tapes. The simulator and kernel also have explicit event deduplication. [FIXED_TAPE_FUNDING_AUDIT.json](FIXED_TAPE_FUNDING_AUDIT.json) records exact arithmetic and input hashes.

## What remains unproven

The retained CSV has only calc_time, funding_interval_hours and last_funding_rate. Its header does not declare whether a numeric 0.0001 represents 0.01% or 0.0001%. A source checksum proves bytes, not that semantic conversion. The 2021/2023/2024-prefix original funding CSV bodies are absent from the inspected packages; producer receipts remain prior-producer evidence.

The inspected, dated official Binance public-data trees and official Postman collections do not supply a numeric funding-unit certificate or archived settled-event response. [OFFICIAL_DOCS_CHECKS.json](OFFICIAL_DOCS_CHECKS.json) lists exact commits, blob hashes, URLs and limited-coverage negative findings. This does **not** establish that no original evidence exists anywhere. Current API examples and current fee descriptions are context only. No current documentation is promoted into historical event-specific authority.

This audit therefore keeps **RAW_AS_FRACTION and RAW_AS_PERCENT as conditional economic interpretations**. It does not certify historical publication/charge time, associated exact charge mark, native venue fidelity, symbol filters, MMR, or the ten separately disclosed 2024 derived mark cells. Source numeric-chain evidence must not be conflated with these other gates.

## Strongest recorded CSH result: fixed-tape funding sensitivity

The strongest currently paid-flat STATIC50 result among the compared seen years is full 2021: 10,000 USDT initial capital, **2,499.48957079 USDT profit, 24.99489571%**, under the original RAW_AS_FRACTION assumptions. Recorded net signed funding cash is **−168.94119181 USDT**, a 1.68941192 percentage-point drag, rather than the source of its positive profit.

For a **fixed recorded quantity/mark/fill tape only**, uniform scale s has the exact arithmetic identity:

fixed_tape_net(s) = recorded_net + (s−1) × recorded_signed_funding_cash.

Changing only that fee arithmetic from s=1 to s=0.01 improves this fixed tape by **167.25177989 USDT = 1.67251780 percentage points**. For uniform s in [0.01,1], the frozen-tape final cash difference is bounded by [0,167.25177989] USDT. Its absolute recorded event funding is 461.40769172 USDT; even allowing different events independently to take either scale gives a conservative **456.79361481 USDT** absolute difference bound on the same tape. These bounds concern recorded fees only.

Selected same-tape s=0.01 minus s=1 cash differences:

- 2021 STATIC50: +167.25177989 USDT; paid-flat recorded return 24.99489571%
- 2021 EXACTHALF: +262.81304634 USDT; paid-flat recorded return 20.47333835%
- 2023 STATIC50_FINE_ORIGINAL: +132.45688096 USDT; paid-flat recorded return 11.59692494%
- 2023 COMBINED_FINE_ORIGINAL: +127.78879829 USDT; paid-flat recorded return 2.54982870%
- 2024 EXACTHALF_FINE_ORIGINAL: +170.95614509 USDT; paid-flat recorded return 13.86553321%
- 2024 STATIC50_FINE_GUARD50: +150.78883895 USDT; paid-flat recorded return 19.81826252%; this is a distinct protective-policy case, not the original unmodified STATIC50
- 2025 STATIC50_FINE_ORIGINAL: +71.33213675 USDT; recorded marked return 16.12841014%, with unpaid terminal residue
- 2025 COMBINED_FINE_ORIGINAL: +39.87204595 USDT; recorded marked return 5.97573186%, with unpaid terminal residue

**None is a new strategy return or a bound on a counterfactual strategy return.** Funding changes cash and NAV, which affect subsequent sizing, risk thresholds, reductions, available margin, capacity-limited fills, costs, potential halts and terminal residue. A fresh authorized end-to-end replay would be needed to establish changed strategy outcomes. No wallet, target or fit was created here. No annual stitching, alpha/OOS claim, or native venue certification follows from this arithmetic.

## Most effective next confirmation path

1. Recover a **pre-existing original official settled-funding response or export** containing a named historical event's symbol, exact timestamp, raw rate and an explicit decimal-versus-percent unit certificate. Pair by exact identity and rate, not nearest minute or a familiar-looking 0.0001. A conceptual fee formula alone does not bind archive numeric units.
2. Reuse the original source producer's raw funding archive/receipt cache for 2021, 2023 and the 2024 prefix, and match its bytes to the existing saved source hashes. This closes raw-body provenance but still needs the official numeric-unit mapping. Its cache/location needs to be established first; none was newly downloaded here.
3. If an official unit certificate establishes a homogeneous format across the relevant archive history, bind it to exact source versions and event pairs before changing metadata. If the necessary original certificate cannot be retrieved within authorized access, retain the explicit conditional scale rather than quietly certifying it. Do not retry previously denied provider/API routes.
4. Only after unit evidence is settled should an authorized fresh cash-feedback-preserving sensitivity run be considered. The exact charge-price/publication and other venue gates remain separate.

## Sources and byte identities

- Existing public [funding-charge evidence](https://github.com/snowycat1234/coin/blob/de14c492e8efbbbab1f039507f4905e1fee7c892/research/funding-charge-evidence-20261011/result/RESULT.json): original blocker UNKNOWN, no historical REST body; this audit adds the numeric-chain evidence above.
- [e0 feature transfer index](https://github.com/snowycat1234/coin/blob/e0d3400b23842f11f167a63e7d80856d76501de8/research/temporal-feature-data-20261009/INDEX.json): wrapper SHA-256 bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30; five exact member hashes in SOURCE_IDENTITIES.json.
- [Original normalizer](https://github.com/snowycat1234/coin/blob/e0d3400b23842f11f167a63e7d80856d76501de8/modules/collector_research/pipeline/normalize.py): SHA-256 ee394086066c96bc23e83b45bf0bc2777264ab4eb57128886394fee47fecd4ff. It preserves raw rates and explicitly labels units UNCONFIRMED_RAW_PRESERVED.
- [Retained 2024 H2 source wrapper](https://github.com/snowycat1234/coin/blob/d69e9ac94478c5be54cb46c622afec7aaf3c61f7/research_artifacts/native_20261008/coin_public_tail_archives_20261008_part01.zip): SHA-256 10de51c5daed8bcc63e9d2cecbd17146ca2e7c0ab488dea221eab44b920a9bbc. Individual original official URLs are saved as provenance only; they were not accessed by this audit.
- [Original 2025 primitives manifest](https://github.com/snowycat1234/coin/blob/88a77396c7f1e6e0fd5b6249fe0f79dd923fda3b/research/core10-2025-primitives-20261010/MANIFEST.json); saved PRIMITIVES.zip SHA-256 a42785c91a7645ce3df1335a261758b896d0992858738bed5a18d6d237d0321a. Original member names and exact archive/CSV hashes are listed in SOURCE_IDENTITIES.json.
- [Funding simulator](https://github.com/snowycat1234/coin/blob/b9c0020ec0ae9c7be991e58544bb5227657ef640/scripts/investment/resumable_perpetual.py): SHA-256 318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585. [Kernel charge/dedup code](https://github.com/snowycat1234/coin/blob/b9c0020ec0ae9c7be991e58544bb5227657ef640/src/quant/perpetual_account.py): SHA-256 ffa57a4c3c3b031945fcbc5db429d8b5e6ef06e880a8a577265836602ad55110.
- [Reviewed 2021 results](https://github.com/snowycat1234/coin/tree/edfaea80a89b0f9610f98216f67757b615924870/research/core5-2021-strategy-20261013/results) provide the strongest recorded case's public compact result. Full synthetic research account journals were read locally for the fee audit but are not duplicated here.
- [BRANCH_HEADS_20261013_1610.txt](BRANCH_HEADS_20261013_1610.txt) is the supplied exact **91-line historical branch snapshot before this new audit branch**, not a claim that the repository still has exactly 91 branches.

## Verification and publication scope

Final local read-only audit, with supplementary consumer archive/member manifest checks: 3.139 seconds; peak RSS recorded in [RUN_RECEIPT.json](RUN_RECEIPT.json); 2 GiB address limit, one CPU/thread. The earlier 3.025-second pass was retained locally when the input inventory was expanded. Zero provider requests, Library calls, 2026 holdout reads, new wallets, fits or edits to original source/account files. The final receipt binds outputs.

Run `python verify_published_evidence.py` in this published folder for stdlib-only byte-hash and receipt/arithmetic verification. This is intentionally **not** a public replay of every original CSV or full account: raw sources and complete journals are not duplicated in this minimal publication. `audit_saved_units.py` is the full read-only source/journal audit code; re-running it requires the named SHA-bound pre-existing workspace sources and synthetic research journals in their original relative layout. Invoke it with `--workspace-root PATH_TO_ORIGINAL_LAYOUT --output ABSENT_OUTPUT_FOLDER_INSIDE_THAT_WORKSPACE` using Python with NumPy and PyArrow. Output records use workspace-relative paths, so the fresh output folder must be inside that workspace. It does not import execution kernels. No historical performance experiment runs.
