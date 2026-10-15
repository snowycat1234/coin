# Two legacy CORE5 signals: finite 2023 extension

Status: source targets prepared; no extension financial run, launch authorization or publication is included.

This first extension contains exactly two existing signal versions × LOW/MID/HIGH = six 2023 cases. It is a bounded addition to the 37-configuration, 333-status-row traditional catalogue, not a claim to have finished that larger campaign.

## Frozen signal definitions

- STATIC50_OLD_NO_REEXPANSION: exactly 0.5 × the pinned match_core.match CS_MATCHED leg + 0.5 × its VOL_MATCHED leg. No final risk_budget.scale call.
- HOLD_CORE5_VOL_MATCHED_NOREEXP: exactly the original VOL_MATCHED leg. It is not the unmatched original HOLD or the later risk-retargeted HOLD.
- Apply only LOWER_ONLY to these intrinsic weights: min(1, tier gross/gross, 0.30/largest asset, tier volatility/sigma). LOW uses 0.30/0.05, MID 0.60/0.10, HIGH 0.90/0.15; all use asset 0.30.
- Volatility is a ceiling. Released budget is never redistributed or reexpanded. Original zero-common-risk semantics remain cash.

The exact AST loader plus six original references are pinned by source file length, SHA256 and Git blob. The adapter calls original signed_intents and match functions. HOLD's finite-SMA gate is explicitly projected from 200 completed positive finite closes, with full-five admission and optional explicit finite-mask support. The SMA direction is not used by HOLD. Original CS weekly ownership, current masks, 31-close risk context and match's 64-clock gate remain intact.

This is a new common-execution comparison variant. It does not claim literal replication of the legacy feature pipeline or account.

## Execution and research limits

- Execution uses unchanged current V3 native finance, scheduler, partial ladder, quantity profile, costs, funding convention, paid terminal60 and capital guards.
- 2023 only: 365 decisions, 525600 native minutes per financial case, fixed CORE5 order, BASE27, initial USDT 10000, 1× isolated leverage, USDT 1000 free-cash increase floor and USDT 8500 isolated-margin ceiling.
- The source-only preparation binds the existing reviewed original200 proof covering all 365 windows. Existing source-clock and raw-funding-unit qualifications remain conditional and uncertified.
- 2023 is seen development. No untouched OOS, new alpha family, actual exchange/filter certification or equal realized-risk claim is made.
- No 2024 source is loaded. No denied 2025 source is accessed, retried or bypassed. No holdout, new source, download or publication occurs.
- Nominal target ceilings and fill guards do not guarantee continuous held-inventory risk limits. Coarse quantity and capital effects remain part of the unchanged common execution.

## Exact cohorts and completed-current reuse

source_2023_attempt003 is the final entry/driver-bound source-only preparation. source_2023_attempt001 is preserved solely for the independently reviewed pure-adapter snapshot.

All six extension targets differ bytewise from the corresponding completed current-2023 same-tier targets. No completed current financial execution is reusable for an extension case. The completed current comparison remains [the existing full matrix](https://github.com/snowycat1234/coin/blob/884c22c55d5911f3f3ee956b73297a411e7a519a/research/traditional-nine-cell-2023-20261015/REPORT.md); no current case is rerun.

Old STATIC MID/HIGH target arrays are byte-identical, but the tier/account execution contexts differ, so execution cannot be shared across them. Matched HOLD MID/HIGH differ in five cells on one day by at most 3.469446951953614e-18 from a downward rounding adjustment. This is not independent alpha and does not permit approximate deduplication.

Current same-tier difference-date counts, before any extension return:
- old STATIC LOW/MID/HIGH: 197 / 365 / 365
- matched HOLD LOW/MID/HIGH: 85 / 211 / 365

## Gates before any account

extension_entry_2023.py uses explicit new signal/version IDs and passes a reviewed tier and exact target path into the unchanged V3 constructor. It does not monkeypatch current-core strategies or pretend these targets are STATIC50.

A financial launch needs independently reviewed final code/source/target identities plus externally supplied exact root-GO bytes and their expected hash. The GO binds preparation, review, six-version namespace, source, common execution, controller/reporting, costs, calendar and resource limits. It may approve one pilot before the remaining five. Tests manufacture fictional validation fixtures only; they do not supply authorization.

The constructor revalidates original sources and rebuilds all six target/covariance paths before the sole account seam. Preparation and executable identities are rechecked immediately before construction. No prior completed or economic-terminal case can enter this extension's scope.

The controller is serial and bounded: one CPU thread, 600-second wall/CPU limit, 2 GB RSS stop, 4 GB address space, 250 MB output per case, at most six explicitly approved cases. Parent-level concurrency approval is separate.

Recognized native liquidation-required/bankruptcy HALTs preserve witnesses, positions, debt, fees and partial observations. They remain partial/unpaid, with no annual paid return or APR. Continuing to another explicitly approved case additionally requires the exact GO's economic-terminal-continuation permission. Unknown, resource, hash, source or engineering failures stop the queue without automatic retry. Saved terminal validation binds the primary minute and guard/rejection/funding evidence; paid completion requires ACTIVE, flat, zero-debt/residual, exact full-year clocks and NAV-consistent payment math.

## Verification and reproduction

Python 3.12, NumPy 2.3.5 and Polars 1.44.2 were used. No dependency installation or network request is performed by these files.

Generated-only signal checks:

    python -m unittest -v test_legacy_core_adapter

Full generated plus source-gate suite (original restored 2023 source must exist in the expected sibling directory):

    python -m unittest -v test_legacy_core_adapter test_extension_entry test_terminal_policy

Source-only regeneration against existing local original inputs:

    python prepare_2023.py --source-root /path/to/original/restored2023 --output /path/to/new/source_preparation

The output directory must be new. Regeneration creates targets/proofs/manifests only, never an account. Original input tapes are deliberately not redistributed in this packet; their exact hashes and proof identities are in PREPARATION.json. There is no source-download fallback.

The pure-adapter interface is deliberately small: CONFIGS, build_target_grid and target_identities. The finite manifest and separate source-bound entry carry the explicit scope. Future catalogue adapters require separate source preparation/review/GO; the common financial loop need not be rewritten and no additional versions or years are admitted here.
