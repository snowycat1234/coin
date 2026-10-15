# Published saved D GUARD50_EXIT_ONLY results

This research branch publishes the exact independently reviewed saved-results packet for the finished full-2024 STATIC50_MID BASE27 D run. The immutable archive is split into two binary transport parts of at most 500,000 bytes. This publication adds no financial execution, market advancement, source download, strategy change or live order.

## Direct evidence

- [Frozen saved results report](RESULTS_REPORT.json)
- [Frozen B/C/D comparison](B_C_D_COMPARISON.json)
- [Exact independent packaging review](INDEPENDENT_PACKAGING_REVIEW.json)
- [Frozen packet README](SAVED_PACKET_README.md)
- [Frozen archive descriptor](ARCHIVE.json)
- [Transport, part hashes and reconstruction order](TRANSPORT.json)

The original archive descriptor, packet README and report intentionally retain their pre-publication wording, including PENDING, awaiting review and publication_performed=false. Those fields describe the saved packaging event. The separate independent receipt records PASS for this exact immutable content, and this wrapper describes its publication. No frozen file has been edited to relabel that history.

## Result and interpretation

D's paid-flat terminal NAV was 11,625.3968100935644481993 USDT from a 10,000 USDT simulated wallet: 16.253968100935644481993% paid net return, with saved all-observation MDD 5.891240783337448%. It had 298 paid market trade legs, three genuine paid Guard50 warning exits, zero warning renewals, zero internal transfers, zero conditional settlements, zero unpaid liability and zero paid liquidation events. The D controller succeeded with exit 0. The earlier B serial-controller failure is B history and does not apply to D. The secondary native PnL bridge residual remains exactly 1E-36 USDT; it is not cashflow and has not been zeroed.

B returned 8.140378314267891803966% under a conditional-model settled-flat classification with two forfeiture settlements. C returned 5.877740661483466886176% paid-flat. D minus B is 8.113589786667752678027 percentage points; D minus C is 10.376227439452177595817 percentage points. D minus B measures the fixed paid-exit overlay. C versus D compares different warning-response packages and is not a pure transfer increment.

D was selected after seeing corrected B/C 2024 outcomes. This is adaptive development evidence, not independent out-of-sample validation. No 2025 or locked/holdout source was read. Single-year fixed MID BASE27 evidence does not establish robustness, future profitability or long-term APR. Funding units/publication timing, fixed MMR, research filters, execution, insurance sufficiency and venue behavior remain uncertified.

## Independent review and an explicit verifier limitation

The independent packaging receipt's status is PASS_EXACT_IMMUTABLE_GUARD50_EXIT_ONLY_D_SAVED_RESULTS_CONTENT. It reports a cold saved-data-only verifier pass, 36 author mutation tests, 10 additional independently rejected hash-bypass corruptions, every-event native40 arithmetic and strict100 zero terminal stored-delta errors. This does not constitute a new financial run.

The same receipt explicitly discloses a limitation: the standalone source-reference semantic check does not reject hash-bypass mutations of 12 source-reference-only fields. These are source_archive_SHA256, source_archive_bytes, source_archive_members, parent_commit, tree, commit_url, publication_url, independent_source_packaging_review_SHA256, source_publication_CI_status, source_scope, source_cold_test_limit and source_publication_does_not_certify_financial_results. Ordinary byte tampering is still caught by manifest/pin checks. The reviewer separately compared all actual material values against the exact verified source-publication receipt and passed this immutable content. No general claim that every semantic mutation is rejected is made.

Full minute/market arrays and complete account/native exports and general request/target/rejection histories are omitted. Hashes cannot restore missing bytes. Daily/monthly reductions cannot reconstruct full paths or all-observation MDD. Four narrow first-warning rows per B/D cannot re-prove the independently reviewed 108,338-row byte-equal prefix. See the frozen README and review for all limits.

## Recover the original archive

Download both binary part files listed in TRANSPORT.json, concatenate them in the listed order, then confirm the result is 639,236 bytes with SHA256:

    8e0275afa2f7b75983b3949df6e206bcd519c3da279fd11aa6ec16239ab064d2

The unchanged ZIP has 53 members; its MANIFEST.json SHA256 is 8c1b8e3da3ec9b7fb7e53d5e76cd23194e83e364038a00dcfb0bc490c9cc4afc. The exact separate independent receipt is 11,577 bytes with SHA256 c3f7193b97ea806afc637d5a36f806d024a2c68353d84c6b50e4f242d75e36d5.

After extraction, the standard-library-only verify_saved_packet.py and test_saved_packet.py verify saved data; they do not reconstruct a historical account or rerun the financial model. rebuild_from_saved.py needs omitted workspace originals and is not a cold historical reproduction route.

## Provenance

This results publication is based directly on verified D source commit [65ec73d8dfda43802b273e9f3a55b9cd43c2d3a4](https://github.com/snowycat1234/coin/commit/65ec73d8dfda43802b273e9f3a55b9cd43c2d3a4). The source publication is separate and does not certify financial results. The exact saved B/C reference is commit [832aa1fc4d3c2d941060d7b5b0f9080344539637](https://github.com/snowycat1234/coin/commit/832aa1fc4d3c2d941060d7b5b0f9080344539637). Publication grants no permission for future financial executions. No PR, merge, or change to main is part of this publication.
