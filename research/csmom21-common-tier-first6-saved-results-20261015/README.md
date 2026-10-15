# CSMOM21 common-tier FIRST6: exact saved-evidence publication

This additive research publication preserves the sealed packet unchanged. Five newly verified DEV cases are 2022 MID/HIGH and 2023 LOW/MID/HIGH. A separate recovered 2022 LOW supplies the sixth comparison row. The exact-five controller has actual EXIT0; its root-exit receipt SHA256 is 4afa42f5c7c0a805b4a265a00d9fd728475c6930a7d08166360ca3f233aa15c3. This is not one successful six-run attempt. The original controller EXIT1, frozen codec failure, old interrupted MID's unverified economics, and wasted computation remain recorded.

## Required trust boundary and disclosed verifier limitation

Authenticate the original outer ZIP against this externally trusted SHA256 before extracting or running anything:

4d16bf162a94ca28ebd3007a897b1a4328f13f5e285bce3bd1c13e59ec13d525

Expected size: 9,379,700 bytes; exact inventory: 129 files. The two transport files are the original ZIP's consecutive raw byte slices (8,388,608 and 991,092 bytes). Concatenate them in manifest order. Do not repack, recompress, or substitute a regenerated archive. transport/REASSEMBLY_MANIFEST.json has SHA256 f77acc2c990d1b95c14fd35f0b6bf0ff6a4b3f3e5a75d472b6c649bc1a8b306a.

The independent review passed this exact sealed artifact with an explicit coverage limitation. Its ATTEMPT_SCOPE_AND_STATUS.json GO and financial-code declarations are correct, and the case reviews hard-pin the real GO and financial-code identities. However, verify_packet.py accepts a copied packet if either ancillary GO_SHA256 or financial_code_manifest_SHA256 declaration is changed and the attacker regenerates that copy's file manifest. The embedded verifier therefore does not authenticate a self-modified, self-rehashed copy and does not provide complete semantic validation of all metadata. Require the trusted original outer ZIP SHA above. See review/FINAL_INDEPENDENT_REVIEW_HANDOFF.json and review/ADDITIVE_STRICT_REVIEW.json for the exact result. No old review, verifier, or sealed packet byte was changed for this publication.

## Read and recover

- Start with summary/COMBINED_FIRST6_ECONOMIC_REPORT.md and its exact JSON. RESULTS.csv, COSTS.csv and RISK.csv project exact stored report values without recalculation or rounding; fractional returns/risks remain fractions and costs/funding remain separate signed USDT values.
- Root MANIFEST.json and READMAP.json are exact copies of the sealed packet's metadata. Their internal paths resolve after ZIP extraction. PACKET_README_EXACT.md is the unchanged historical packaging README, so its then-unpublished/review-pending wording describes that original sealing stage.
- Download transport/*.part001 and transport/*.part002, concatenate in listed order, check size and trusted SHA, and safely extract all 129 files. In the extracted cs_exact_five_compact_saved_results_public_recovery_20261015_v1 directory, Python 3 standard-library-only saved checks are: python -S -B verify_packet.py and python -S -B test_packet.py. The five saved native40 proofs reconstruct from public stored financial event bytes. These are saved-only checks, not account/provider/controller execution or financial backtests.
- All six annual wallets start fresh at 10,000 USDT. Full 2022 and 2023 are seen DEV. No annual-wallet compounding, CAGR, OOS, matched-realized-risk, optimized-tier, or superiority claim is made. Nominal budgets are not continuous risk caps; descriptive forecast overshoots and coarse-lot/admission differences remain visible. July 2022 source valuation and venue/funding assumptions retain their stated uncertainties.

## Sources, omissions, and historical limits

Source code public ancestor: https://github.com/snowycat1234/coin/tree/3246e85474581a25dd090aff1ae11be5e6b853af/research/csmom21_common_tier_source_evidence_20261015

Separately recovered 2022 LOW, sole publication parent: https://github.com/snowycat1234/coin/tree/4f9b7babdebe810b076f50d99dfe4b3c16f9ccc2/research/csmom21-common-tier-low2022-recovered-partial-results-20261015

LOW ZIP SHA256: 5901e267046d6e6adf44a9ff97f0d94fca7289c9fe143608d7dc34a9afac0c71. Its financial payload is not duplicated. The new five use their separate GO and code identity.

Private GO/claim/reservation/recovery bodies, source/target/minute arrays and private absolute prefixes are omitted; retained hashes cannot reconstruct omitted bytes. Historical execution/restart, source/target generation, minute-risk/covariance regeneration and a portable financial rerun are not self-contained. The public saved-only native40 recovery is self-contained for the five included cases. Actual account/provider execution tests are provenance-only. The private 296,808,751-byte full archive is never uploaded. See OMITTED_ARRAYS_AND_RECOVERY_LIMITS.json and the sealed dependency/provenance maps.

Only the two raw transport parts and a small readable index/report/review wrapper are added. Financial event payloads remain once inside the sealed ZIP. Existing parent leaves and main are preserved; no merge or force-push is involved.
