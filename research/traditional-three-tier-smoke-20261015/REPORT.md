# V3 traditional grid: minimal recovery report

## Result and scope

All nine saved V3 cases passed independent saved-output review: PASS_ALL_NINE_SAVED_EVIDENCE. Each separate fresh 10,000-USDT, isolated one-way 1x account completed 4,320 real-source native minutes over [2023-01-01, 2023-01-04) UTC and ended paid flat. Every case has zero residual notional, unpaid liability, liquidation-required halt, bankruptcy halt, and actual simulated liquidation fills. A liquidation-required halt would not constitute a modeled liquidation fill.

This is an actual-source three-day technical smoke in seen DEVELOPMENT. It is not an annual return test, untouched OOS, stable risk estimate, independent alpha result, or venue/live-use certification. No new actual-source historical account or run was created during packaging. Generated tests use synthetic account fixtures. Frozen core/spec and saved results are unchanged. Annual source-only entry work is separate and is not included or authorized.

## Fixed comparisons and economic qualification

The fixed labels are canonical later risk-retargeted STATIC50, exactly-once H090 amplification followed by its original clip/gross/vol shrink order, and constant-long equal CORE5 VOL_MANAGED_HOLD with its original past-30 covariance downscale. LOW/MID/HIGH nominal annual covariance budgets are 5%/10%/15%, with gross admission/target ceilings 30%/60%/90% and a common absolute asset ceiling 30%. All use the existing common capital floors/ceilings and the same charged discrete partial ladder. There was no fit, adaptive search, per-year switching, or outcome-selected parameter change.

Costs are conditional BASE27: 5.5 bp taker fee plus 4 bp half-spread and 4 bp slippage per side. STRESS43 exists as unchanged code sensitivity but no STRESS43 actual-source smoke is reported here. Signed funding uses the original RAW_AS_FRACTION scenario; archive rate units, publication/arrival, charge-price timing, and logical source-close availability remain conditional. Execution uses Binance proxies and Bybit fee assumptions. Native historical filters, margin/risk tiers and liquidation fills are uncertified.

Nominal budgets and caps constrain sizing/admission and do not promise equal achieved or realized risk. Held inventory can drift above a forecast-risk budget after covariance/mark refresh and coarse lot effects. LOW HOLD reached past-30 forecast sigma 0.05319508653784451 against 0.05, with 1,949 minute observations above the target. Three-day daily-return sample volatility is descriptive and must not be interpreted as stable annual risk. Same-tier nominal-budget excess below is qualified by different observed risk and exposure; these are not realized-risk-matched comparisons.

## All nine saved conditional outcomes

Percentages are the unannualized three-day return and all-observation maximum drawdown. CASH has zero modeled return. Each row is an independent account; do not sum returns as one portfolio.

| Configuration | Paid/marked return % | MDD % | Excess vs same-tier HOLD pp | Fees USDT | Execution cost USDT | Signed funding USDT | Maximum gross | Max forecast sigma | Minutes sigma above target |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| STATIC50_LOW | -1.061787319 | 1.147786907 | -1.792327409 | 2.88556714182000 | 4.197129040 | -6.08053570745617067640 | 0.271605608 | 0.040553319 | 0 |
| STATIC50_MID | -0.837370201 | 0.919037591 | -1.947687656 | 3.19559595704800 | 4.648094400 | -5.30912976869249618400 | 0.297025175 | 0.045607706 | 0 |
| STATIC50_HIGH | -0.624339672 | 0.687886415 | -1.835463604 | 2.40998418804000 | 3.505397920 | -3.97758513918571963800 | 0.223503732 | 0.033768342 | 0 |
| H090_LOW | -1.061787319 | 1.147786907 | -1.792327409 | 2.88556714182000 | 4.197129040 | -6.08053570745617067640 | 0.271605608 | 0.040553319 | 0 |
| H090_MID | -0.837370201 | 0.919037591 | -1.947687656 | 3.19559595704800 | 4.648094400 | -5.30912976869249618400 | 0.297025175 | 0.045607706 | 0 |
| H090_HIGH | -0.624339672 | 0.687886415 | -1.835463604 | 2.40998418804000 | 3.505397920 | -3.97758513918571963800 | 0.223503732 | 0.033768342 | 0 |
| VOL_MANAGED_HOLD_LOW | 0.730540090 | 0.223663209 | 0.000000000 | 1.16821199462000 | 1.699263760 | 3.55698472150404852880 | 0.107134160 | 0.053195087 | 1949 |
| VOL_MANAGED_HOLD_MID | 1.110317454 | 0.358440278 | 0.000000000 | 2.16157366119200 | 3.144177760 | 5.99929685029654122560 | 0.200311854 | 0.098367869 | 0 |
| VOL_MANAGED_HOLD_HIGH | 1.211123932 | 0.389068289 | 0.000000000 | 2.32925954918800 | 3.388090800 | 6.65744353154498269160 | 0.215659555 | 0.105926328 | 0 |

STATIC50 and H090 had matching executed economics within every tier in this smoke: paid return, MDD, fees, execution cost, funding, turnover, and minute NAV/exposure all matched. Their target identities are nevertheless distinct. Common normalization can erase H090 amplification when its clip does not bind; exact arithmetic/identity differences do not establish independent alpha. No execution wallet was reused merely because targets or economics matched.

## Independent evidence and portability

- Original V3 builder generated suite: 56 passed. Original independent suite: 39 passed, consisting of 32 generated checks plus seven read-only restored-source/GO checks. Independent code/source hashes were unchanged. Seven additional constructor-negative tests and five source-helper schema tests are included.
- The saved-output reviewer independently reconstructed cashflow NAV, signed funding and execution formulas, fee/friction charges, quantities, 1x margins, opening capital constraints, fill/capacity clocks, source-open prices, paid terminal exits, target/preparation/core/root-GO bindings, minute calendar/MDD/exposure, and forecast risk. It created or reran no account. All nine passed with no binding errors or missing cases.
- Complete compact saved output is included for attempt002: per-case RESULT, CASE_RECEIPT, audit snapshot, MINUTE.npz, guard receipts, funding journal, and native rejections. MINUTE.npz contains saved simulation observations, not a replacement raw market payload.
- Full portable test instructions and the recoverable omitted-source layout are in README.md. validation/ records the actual packaging checks; their generated-account fixtures do not grant historical authorization.

The original read-only saved-output reviewer can be rerun after exact source recovery, from the package root:

    python traditional_three_tier_independent_review_20261015/review_saved_smoke.py --matrix traditional_three_tier_freeze_20261015/actual_smoke_matrix_attempt002 --preparation traditional_three_tier_freeze_20261015/actual_2023_smoke_preparation_attempt004 --output saved_review_recheck.json

Use a new output filename. It reads and audits saved evidence only; it never imports, constructs, or advances a financial account. No re-audit is required to inspect the included original passing review.

## Attempt001 failure addendum

Attempt001 used the separately archived exact V2 runtime/spec. STATIC50_LOW completed 4,320 minutes and paid flat. STATIC50_MID logged 1,440 minutes and then failed when a flat same-clock trade-close observation attempted to overwrite an existing native mark (ValueError: old or conflicting mark). Seven configurations were NOT_RUN. The original controller stopped, with no automatic retry.

The failed MID partial financial snapshot was not saved. No snapshot, PnL, account bridge, or restart state has been fabricated or reconstructed. Attempt001 is incomplete and remains separate from the fresh attempt002. Raw failure tracebacks contained private absolute execution paths and are omitted; ATTEMPT001_SAVED_REVIEW_SANITIZED.json removes only the raw traceback field and records the original review hash. ATTEMPT_STATUS.json and this addendum retain the failure and missing-state facts.

The V3 correction seeds only absent marks in a detached genuinely fresh-flat probe. Every existing native mark remains authoritative, including after the account later becomes flat. It changed no target, cost, tier, capital, partial ladder, or finance method. The V3 generated regression and independent saved smoke both pass.

## Exact frozen identities

- frozen_grid.py: a64abec4b396b17ff1e93bbc95ad77c6a76a26e54ecdf36bb5c9ddaedac6b8f1
- native_runtime.py: e716eace323b82954cd13755d0af80e046cd4daf5b37147300c417e7ac7d4b1a
- historical_entry.py: f8be19239bef56d7db514a327e09dfacf153bc1bdf54bbbc2b87616254df66b7
- FROZEN_SPEC.json: 53392714aea7f1ec545cc4476291044e0640b8c63c7aa822af2808c40dae36e7
- SOURCE_PROVENANCE.json: ef36bee5b7c6d8dbef5ebd10f604b00a2f46aeceab88d848b958b4212416df56
- NATIVE_SOURCE_PROVENANCE.json: a8a59ba72e61cab35f4bd84da1f09f5a3d0052fcaa3effba819d93f4b102f1fb

Old archival runtime SHA256: 20b4f8f764e3c7a26ddc24f29f75e20e9ab610fbec287b829381adaa319702ad. Old archival spec SHA256: 30d9b3bfd47ada0357dcadedc529ef860f29ab3cc5d9220323320691cade6568. These exact bytes were recovered by narrow reversal and matched their recorded pre-fix hashes; they are not invented substitute versions.

## Recovery and remaining limits

Public source dependencies remain exact bytes with original SHA256, Git blob, commit, and repository-path provenance. Public source recovery pins/helper cover already-public raw parts, checksums, normalized source identities, warmup and original200 quality proof. The twelve-month market values and large raw archives are omitted to keep this package small. No provider or GitHub object was fetched during packaging.

The independent readiness recommendation says the smoke execution passed, while a separate exact annual entry review and root GO remain pending. Its timing/output extrapolations are feasibility estimates only, not annual completion guarantees. Restart/fork certification is explicitly unavailable; saved audit snapshots are financial evidence, not a certified recovery engine. No locked or holdout outcomes were opened. No annual, OOS, edge, investment, or native-venue conclusion follows.

## Public-safety scan

Every package text, JSON, Python, log and decompressed proof was scanned for newly captured private execution paths, raw traceback frames, credential/token patterns, signed credential URLs, and common key material. The only retained absolute machine-path strings are three already-public references in the unchanged hash-pinned joint_expert_information.py dependency. Their exact source identity and public provenance are retained and their occurrences are listed in PUBLIC_SAFE_SCAN.json. Raw attempt001 failure logs/tracebacks, bytecode, virtual environments, large market data, SOURCE_BINDING/private-path artifacts, and unrelated publication packages are excluded.
