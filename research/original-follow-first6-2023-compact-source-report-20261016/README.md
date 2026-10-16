# FOLLOW 2023 first6: compact report and source bindings

This additive research publication preserves the exact independently reviewed packet. It covers six 2023 adaptive DEV simulations: the FOLLOW pool and dependent control, each at LOW, MID and HIGH nominal tiers. Every account started separately with 10,000 USDT, completed 525,600 simulated minutes and ended actual paid market-flat. These are historical simulated outcomes, not future APR or deployability evidence.

**Compact report and source bindings only; omitted full event history means the public packet alone CANNOT reconstruct all native40 checks.** Qualified 2023 HLC/full-prefix/target bodies and parts of inherited financial runtime are omitted and hash-pinned. Hashes cannot restore missing bytes. The cold reader verifies included bytes and cross-bindings; it does not rerun financial simulation or native40 event-state checks. Native40 PASS labels in exact historical matrices are preserved prior-audit results.

## Same nominal tiers, not risk-matched

Intrinsic samegross precedes separate lower-only tier adaptation, so post-tier samegross is not guaranteed. Control LOW forecast-held annual volatility reached **27.11395% against the nominal 5% budget, with 74,631 breach minutes**. Its realized daily-return annual volatility was 6.8841%, versus pool LOW 4.6361%. Return differences do not establish risk-matched superiority.

| Case | Paid net return | All-observation MDD | Paid fees, USDT | Adverse execution cost, USDT | Signed funding, USDT |
|---|---:|---:|---:|---:|---:|
| Pool LOW | 6.8324% | 5.8187% | 35.493067 | 51.626810 | -58.118360 |
| Pool MID | 9.0240% | 5.1309% | 58.242291 | 84.716781 | -81.672414 |
| Pool HIGH | 10.0519% | 5.3966% | 66.000572 | 96.001630 | -79.083531 |
| Dependent control LOW | 13.0157% | 3.9718% | 23.167333 | 33.698842 | -53.049765 |
| Dependent control MID | 10.4816% | 5.1520% | 50.798113 | 73.888959 | -69.628090 |
| Dependent control HIGH | 10.3036% | 5.7880% | 53.824774 | 78.291366 | -65.206358 |

Execution costs are already embedded and must not be deducted twice. Funding uses literal saved rates/clocks; raw units and historical arrival/publication are unconfirmed. Actual-held risk is measured post-transition at minute close; MDD covers all saved observations with independently checked extrema witnesses, not an independent replay of the full observation stream. Admission limits are not continuous marked-state guarantees. Venue filters, native liquidation and risk tiers remain uncertified. All 2023 quality-interval/block rows are zero. No untouched OOS or future-performance claim is established.

## Contents and prior failures

- Exact archive: `original_follow_pair_first6_compact_source_report_20261016_v1.zip` (785,511 bytes, 198 members, 3,872,485 expanded bytes).
- Exact saved six-case JSON/CSV are also exposed under `results/` for reading.
- Exact independent final PASS, review manifest, verification report, narrative and review-iteration history are under `review/`. The review manifest binds additional retained evidence; not every external review file is repeated here. It is not a claim of a self-contained external review tree.
- The archive preserves both V1 cp437 pre-account failures, explicit V2 recovery, earlier pending-exit metadata, later final audit and root EXIT0 receipt. Earlier failed/unsealed publication and reviewer attempts remain historical, hash-bound evidence. No original is rewritten.
- The frozen packet's local-preparation/no-upload-authority statements describe its historical preparation stage. This additive publication is separately authorized; the review itself does not confer publication authority.
- Historical project executor path literals inside frozen source/receipts are inert provenance and are never followed by the cold reader. No raw market bodies, private authority bodies or credentials are included in this publication selection.

## Independent trust pins and cold verification

Authenticate both the archive and launcher against independently trusted receipts before execution:

- ZIP SHA256: `73901dc04248d1ce3e31e88b0fab8e9b06332232a5cd70aea4ae5537b1a186f0`
- Launcher SHA256: `2f47a308af0727d2654cad26bf7c0decdca07b2cccd867c5196198b023688963`
- Packet manifest SHA256: `104fa9dea4eb8bbf4c2f9fec379e1290f2b0106df0423645b0e53fcfea12c173`
- Independent final PASS SHA256: `f5dc493bdaaf225707fbc22d19c59e915b47e79363b3a65d143ef5adcc8c3a4f`
- Independent review manifest SHA256: `16bd55c68fe4b2dacce0b03876d2afbac593af8c1a911efc032a244d79b19ddf`
- Independent verification report SHA256: `749e886f596a4fa1329cd15efef26b3dc56c84dc6f927b593c56ad668cececbb`

Use Python 3.12, stdlib only, from a clean working directory:

```sh
python -I -S -B run_isolated_cold.py original_follow_pair_first6_compact_source_report_20261016_v1.zip --trusted-zip-sha256 73901dc04248d1ce3e31e88b0fab8e9b06332232a5cd70aea4ae5537b1a186f0 --receipt NEW_NORMAL_RECEIPT.json
python -O -I -S -B run_isolated_cold.py original_follow_pair_first6_compact_source_report_20261016_v1.zip --trusted-zip-sha256 73901dc04248d1ce3e31e88b0fab8e9b06332232a5cd70aea4ae5537b1a186f0 --receipt NEW_OPTIMIZED_RECEIPT.json
```

The unchanged launcher retains a tiny temporary extraction and enforces a 1.5 GiB free-disk floor plus extraction allowance. It denies external reads, directory access, network, process execution, unauthorized writes/mutations, historical code execution and non-stdlib imports. Never execute historical financial/source CLIs.

The independent review reports 318 CSV/JSON field checks, six explicit source/code/proof chains, 294 dependency classifications (49 bundled and 245 omitted), 213 omitted-evidence pins, 19 generated tests in each Python mode and 57 mutation negatives. Those are the independently reported review results, not additional tests newly performed by publication. This publication makes no GitHub CI-pass claim.

The research commit is additive to sole parent `fd1500c5b5b661d9e05594ef03f78e0ea364a8f7`; main remains separate.
