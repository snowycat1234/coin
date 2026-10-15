# Corrected financial V2: saved full-2024 B/C results

This is the public saved-results publication of the exact independently reviewed corrected financial V2 packet. The original ZIP and its 64 frozen files are unchanged. [Independent packaging review](INDEPENDENT_PACKAGING_REVIEW.json) status is **PASS**, bound to archive SHA256 **f438cad63cf0843c0980a57a38709de1d62da18ae9ca88d6b1bba0fcb903ba2e**. The packaging version V1 in the archive name is distinct from corrected financial policy V2.

## Results and interpretation

- **B, continuation only:** terminal NAV 10814.0378314267891803966 USDT, conditional-model return **+8.1403783143%**, all-observation MDD 6.1361587755%. Two conditional collateral-forfeiture settlements; paid net return is null. Positive marked equity forfeited 2.5688912 USDT, own remaining isolated collateral forfeited 328.3426156 USDT, insurance support zero.
- **C, bounded margin-management package:** terminal NAV 10587.7740661483466886176 USDT, paid-market-flat offline return **+5.8777406615%**, all-observation MDD 6.4438124795%. Eight internal transfers totaling 1639.37122176 USDT, zero conditional settlements, external cash added, or terminal debt.
- Both cases completed 527040 of 527040 minutes. C minus B is **−2.2626376528 percentage points** for the whole fixed package under the declared model. It is not a pure internal-transfer causal effect.

Read the exact [results report](RESULTS_REPORT.json), [A/B/C comparison](A_B_C_COMPARISON.json), [saved halted A baseline](A_SAVED_HALTED_BASELINE.json), and [descriptive asset attribution](DESCRIPTIVE_ASSET_PNL_ATTRIBUTION.json). Attribution is saved trade-log realized PnL minus fees plus applied funding. B includes conditional clearing; friction is already embedded in fill PnL. DOGE contributes −306.6221378039 USDT to C−B; this is descriptive whole-path attribution.

## Controller failure and arithmetic proof

The original serial controller failed with **SAVED_PRIMARY_CASH_ISOLATED_DEBT_LEDGER_MISMATCH** after B completed and before C started. It did not succeed. B was not rerun. A separate recorded root decision allowed the previously approved, never-started C to execute once through the unchanged single-case entry under the same GO. The original error, decisions, case receipts and logs remain in the ZIP; [paired independent review](CORRECTED_V2_PAIRED_RESULTS_INDEPENDENT_REVIEW.json) preserves this history.

One XRPUSDT native40 margin-delta subtraction rounds a stored delta by **+3E−38 USDT** at ledger sequence 4814. Exact100 summation retains the raw 3E−38 residual. The independent every-event frozen-native40 proof verifies actual cash, debt, quantity, basis, margin and totals exactly, without tolerance or financial changes. Direct proof receipts: [B native40 proof](SAVED_B_NATIVE40_EVENT_ARITHMETIC_PROOF.json) and [C native40 proof](SAVED_C_NATIVE40_EVENT_ARITHMETIC_PROOF.json). C's native secondary PnL-bridge residual is 1E−37; descriptive asset-attribution exact100 residuals are B −6.0E−37 and C −5.1E−37 USDT. All remain explicit.

The packaging reviewer inspected proof code, logs and source/audit pins; it did not reexecute the full every-event proof or any historical account. Saved-data packet arithmetic is narrower than the independently retained full-native proof. The reviewed A/B prefix finding covers 269 exact trades, 4650 funding rows and 446576 byte-identical minute rows. Omitted full paths mean the packet alone cannot re-establish that equality.

## Exact publication and historical metadata

- [Original packet README](PACKET_README.md), [63-payload manifest](PACKET_MANIFEST.json), and [original archive metadata](ARCHIVE_RECEIPT.json)
- [Independent packaging PASS](INDEPENDENT_PACKAGING_REVIEW.json), SHA256 **0aa92d0bbec116392b2801e2b1e4c03c30265648abbddc2885609f91119a0e92**
- [Transport manifest](TRANSPORT_MANIFEST.json) and [publication recovery manifest](RECOVERY_MANIFEST.json)
- [Corrected source publication reference](SOURCE_PUBLICATION_REFERENCE.json), source commit **c00c14b25b30a339195fe089acb6bd4d24a29f5f**

Frozen files retain their original unpublished/candidate/PENDING fields. Those are pre-publication history, preserved verbatim. This separate wrapper records the later independent PASS and publication binding without rewriting the reviewed archive. The commit containing this wrapper binds the publication to parent **7edb58b0bab448b8617aad7e55f028604de97273** and parent tree **a2a90eb46089dd075c944fc8dd25d2f60a3f68a2**. That parent preserves the explicitly superseded financial V1 diagnostic publication; it does not turn V1 into corrected results. Source publication alone does not certify controller success or results. Remote-byte, parent-tree and branch/main checks are recorded in the publisher's final verification receipt.

## Reassemble the exact ZIP

The ZIP is **1,159,806 bytes**. Download all three consecutive raw parts from this same commit, verify each size/SHA256 in TRANSPORT_MANIFEST.json, then concatenate:

    cat bounded_native_continuation_v2_corrected_saved_results_public_recovery_20261015_v1.zip.part001 bounded_native_continuation_v2_corrected_saved_results_public_recovery_20261015_v1.zip.part002 bounded_native_continuation_v2_corrected_saved_results_public_recovery_20261015_v1.zip.part003 > bounded_native_continuation_v2_corrected_saved_results_public_recovery_20261015_v1.zip
    sha256sum bounded_native_continuation_v2_corrected_saved_results_public_recovery_20261015_v1.zip

The complete archive SHA256 must be **f438cad63cf0843c0980a57a38709de1d62da18ae9ca88d6b1bba0fcb903ba2e** before extraction into an empty directory. Parts are 400000, 400000 and 359806 bytes, each below 500000 bytes, with no recompression. The ZIP contains 64 exact files under one packet directory; MANIFEST.json pins 63 payloads. Included verify_saved_packet.py and the 25-test saved-data suite perform saved-data-only checks. The previously completed author final/cold suites and independent saved-data verifier are documented in the packaging review.

## Recovery and model limits

Exact retained ledgers, trades, funding, transfers and conditional settlements survive alongside daily/monthly float64 summaries and saved all-observation statistics. Full minute/source/market arrays, full raw audit/native state, complete request/no-op/target/guard/rejection histories and restart state are omitted. Hashes do not recover missing bytes. Full minute-path reconstruction, restart recovery and cold historical reproduction are uncertified.

The model has coarse uncertified filters, fixed 0.005 maintenance and conditional forfeiture semantics. Exchange risk tiers, partial liquidation, insurance/ADL, intraminute/live fills, robustness and long-term APR remain uncertified. [Funding appendix](FUNDING_SEMANTICS_APPENDIX.md) and [evidence](FUNDING_SEMANTICS_EVIDENCE.json) preserve zero same-symbol retained fills within ±15 seconds of funding on both paths; RAW_AS_FRACTION scale=1, historical rate arrival and charge-mark authority remain unconfirmed. The packaging reviewer checked integrity, source correspondence, qualifications and privacy; PASS is not venue or investment certification.
