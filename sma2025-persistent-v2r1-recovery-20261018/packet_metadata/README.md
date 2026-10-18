# SMA2025 persistent v2r1: complete-output recovery packet

Local preparation only. This packet has not been pushed, uploaded, published or used to create a remote branch. Suggested future branch, if separately approved: `research/sma2025-persistent-v2r1-recovery-20261018`.

## Result and evidentiary status

The single fresh 2025 DEV execution completed with EXIT 0: 365 days, all twelve months, 525,600 contiguous minute closes, and an actual paid-flat terminal wallet. The independent saved-record audit passed exact chronological native40 arithmetic, source/causal clocks, full saved float64 minute reconciliation, frozen identities and zero residual positions/debt/pending requests. The 10,000-USDT wallet ended at 9,829.62804019943618961520 USDT: net -1.70371959800563810384800%. The 20% return target was not met.

Minute-close maximum drawdown was 12.2639769534%. Daily-return annualized realized volatility was 11.87980714%. The causal rolling daily-covariance forecast sigma of actual held positions reached 24.2095%, materially above the 10% admission target; that target is not a continuously enforced held-position risk ceiling. These are different risk measurements.

This one-year observed return is not evidence of a reliable repeatable long-term APR. All inputs are seen DEV. Funding units/publication/actual source-arrival timing, historical venue filters/risk tiers, and native liquidation/no-liquidation are uncertified; no OOS, live-readiness or original-code-equivalence claim follows. No bound pre-existing causal bull/bear/rebound/range labels were supplied, so regime performance is not certified. No 2022 joint/same-engine claim is made. An old different-engine 2022 result cannot be stitched to this new-version 2025 result.

Start with the final `coin_recovery_20261018/audit_sma2025_v2r1/AUDIT_REPORT.md` and `AUDIT_RECEIPT.json`, then the final `economics_sma2025_v2r1/FULL_YEAR_ECONOMICS.md` and `.json`.

## Exact identity anchors

- Scope: `SMA200_PERSISTENT_V2R1_MID_BASE27_CORE5_2025_DEV`
- Terminal proof SHA256: `6793008b479ca39e5520a1390b6f7f80aa65e7cd660f803e03f7cd23c5d89815`
- Final run spec SHA256: `6a3e9e4cf180a11215458afe0c485c43d6116e63d85e16280951b34d6580027c`
- Final preparation review SHA256: `40f5eb066d0b5fa8d06899076d75a8f3ba92458a2f73f7f132fcbf30bdac2665`
- Consumed GO SHA256: `8d4e45e2b888070396ac2df854232644fc962f3e262e6456a85f4c98c52b4571`
- Final saved-record audit SHA256: `98eb900afed1647972e4034cf34279a455ca38382df3f1d62199ed99cfb9d778`
- Full minute NPZ SHA256: `12d43683d52d045062a11361fe40bd3cc815a0343d722c75ab0637ce3efd0447`

The complete `native_minutes.npz` is 43,274,761 bytes, with 525,600 × 36 float64 values and the exact int64 clocks. It is included intact. All eleven actual annual outputs total 44,883,678 bytes; none is replaced by a summary, sample, prefix, CSV projection or compact reconstruction promise. Funding-source records, account/funding journals, policy/adapter evidence and progress/terminal records are included losslessly.

## What was recovered, and what is newly implemented

The original fixed SMA200 source/signal bytes, exact canonical 2025 source-cache identities and published 96-member financial-kernel source/metadata closure were source-restored. Their public-Git commit/path/blob/member pins are preserved.

The persistent-position policy v2r1, adapter and reviewed causal-daily-observation caller are a new, separately identified implementation. This does not recover or prove equivalence to the lost unpublished standalone persistent-lot engine. The daily caller deliberately observes every causal daily frame before open funding, including inactive hard-risk states. Unchanged published financial methods and source pins do not turn that new caller into old-code equivalence.

Source, contracts, frozen final specs, generated test code/results, independent policy/adapter/preparation reviews, complete annual outputs, final saved audit and final arithmetic economics analysis are included. Historical preparation READMEs/receipts are preserved at their original exact bytes: their preparation-only statements describe their creation stage. This top-level README and the final execution/audit records establish the later completed status.

## Safest starting point: offline verification

After extracting the ZIP into a new ordinary directory, run from its root:

    python recovery_tools/verify_packet.py --root .

This checks every listed file length and SHA256, the manifest seal, and symlink-free listed paths. It imports no research engine and makes no network request. To verify the ZIP by streaming every member without extraction:

    python recovery_tools/verify_packet.py --zip /path/to/SMA2025_PERSISTENT_V2R1_RECOVERY_20261018.zip

The ZIP verifier refuses duplicate/unsafe/encrypted/nonregular members and has explicit member-count, single-member and total-uncompressed-size bounds. The packaging QA performed this complete streaming verification. `MANIFEST.json` lists all packet members except itself and its seal; `MANIFEST.sha256` seals the manifest. The separately supplied package receipt and ZIP SHA256 sidecar identify the whole ZIP.

`INPUT_OUTPUT_MANIFEST.json` lists all final-spec bound code/source/review inputs, the complete immutable kernel96 closure and execution identity, and every actual output with SHA256 and bytes. Every supporting file/test/report is in `MANIFEST.json`. `HISTORY_INDEX.json` preserves minimal failed/generated records and an exact identity index of omitted repeated historical fixtures. It does not claim full-byte recovery of those omitted generated fixtures. No actual annual-output record is omitted.

## Recovering the public 2025 source cache, only when needed

To avoid duplicate caches, this packet omits raw market ZIP bodies and the twelve canonical monthly NPZ cache bodies. The exact small DAILY/EVENTS/SOURCE_INDEX and inherited 200-close-only warmup are included. The complete actual financial minute output remains included.

Existing public repository: `https://github.com/snowycat1234/coin`. `remote_map/RAW2025_RESTORE_INVENTORY.json` and `RAW2025_STREAM_PLAN.json` list all 229 exact immutable public-Git objects: commit/ref, path, raw URL, bytes, SHA256, Git blob SHA1 and assembly offsets/whole-archive hashes. Total raw-cache transfer: 253,383,984 bytes. Principal commits are:

- H1 and January tail wrappers: `d69e9ac94478c5be54cb46c622afec7aaf3c61f7`
- July–December raw sources/checksums: `d046cc66c2323a5dd692d01b809ce9ac93102358`
- Funding wrapper: `88a77396c7f1e6e0fd5b6249fe0f79dd923fda3b`
- Original signal/protocol: `52bd252fe7d26499ea571d77e4ec3de81aecebb3`
- Small source packet reference: `bae934ffdfc6f90984c57dda2b586e2d98923e65` (kernel recovery also pins the identical archive at `e9153a75c95a2a1096f0f6df15f71f2459d9bfae`)

First inspect/verify the restoration plan with no downloads or writes:

    python recovery_tools/restore_source_cache.py

Only with separate authorization and an absent destination, fetch from the exact public-Git URLs and optionally reconstruct the canonical months:

    python recovery_tools/restore_source_cache.py --destination /new/empty-parent/source-cache-restoration --fetch-public-git-cache --rebuild-canonical

The parent directory must already exist. The destination itself must not exist. Partial failures remain on disk, with no silent overwrite, deletion or resume. The helper refuses alternate hosts, redirects, wrong lengths/digests/blobs, changed offsets and insufficient disk; it does not contact providers or Library. Raw restore plus canonical reconstruction is bounded by 512 MiB additional disk and preserves a 15-GiB free reserve. The network fetch and the relocated canonical-rebuild path were not re-executed during packaging; only syntax and the offline plan path were checked. Previously completed original source reconstruction/readback receipts are included. Future network availability and retention by GitHub are not guaranteed.

Canonical reconstruction uses only the pinned original source-only rebind program, with its BASE path relocated in memory. It requires the recorded numpy/pandas versions, decodes only the allowlisted CORE5 2025 raw trade/mark and funding members, and checks all twelve exact original monthly NPZ hashes. It imports no financial repository modules. The inherited pre-2025 200-close warmup is an exact selected source export; no fresh 2024 raw-source reconstruction is claimed.

The twelve rebuilt months are under `source-cache-restoration/coin_recovery_20261018/restored2025/prepared_2025/months/`. For a future saved-audit rerun, place only those verified monthly files into the matching `coin_recovery_20261018/restored2025/prepared_2025/months/` directory of a disposable extracted packet copy. Keep all originally supplied receipts and metadata unchanged. Do not replace the exact original restoration receipt with a new timing/resource receipt. The original source scripts are retained verbatim as provenance and contain their old absolute workspace path; use the portable helper above.

## Runtime and execution boundaries

Recorded numerical runtime: Python 3.12.14, numpy 2.3.5, pandas 2.2.3, polars 1.44.2 and polars-runtime-32 1.44.2. Requirements and official wheel identity metadata are preserved. No venv, wheelhouse or binary environment is bundled. Recreate dependencies only in a separately authorized environment; packet integrity does not certify equivalence of another platform/runtime.

The consumed one-shot GO and claim are audit evidence only. This packet grants no new run, restart, resume, reentry, replacement wallet, 2026-source access or financial experiment. Do not delete claims/output directories to bypass the one-shot boundary. Some exact published closure members are historical/inert run/profile entries; preserve them for hash closure and do not import or run them casually. Start with static verification and saved reports, not `run_prepared.py --run-once`.

No Library transfer, public upload, remote branch creation, provider download, new financial run, source alteration or deletion occurred while preparing this packet. The allowlist excludes credentials, unrelated notes, private human conversation quotes, caches and compiled bytecode. `RECOVERABILITY_PRIVACY_CHECKS.json` documents the scope and limitations of the privacy/recoverability checks.
