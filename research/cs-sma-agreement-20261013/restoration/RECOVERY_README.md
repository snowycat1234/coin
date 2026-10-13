# Compact public restoration for the CS + SMA gate

Source repository: snowycat1234/coin, pinned commit 53357f33f4e6ccb536af762fbff39b269c24d837.

The existing bare repository is retained untouched. It has no origin and does not contain this newer commit. Instead of fetching the repository's large history, this restoration uses the authorized public GitHub connector to read only the compact INPUTS_FINAL packet and minimal code.

## Inputs

INPUTS_FINAL/PACKET.zip has 389,393 bytes and SHA256 0d2cf51769f2c9444c83b1715c5a6fd730d282e96cc4e84d1feaecf482ffdcd2. Packet identity, every member's SHA256 and size, and the exact member list were verified before extraction into inputs/.

For each of the 365 decisions in 2023 and 365 decisions in 2025, all CORE5 members have 200 consecutive, finite, positive completed daily closes available no later than the decision. Execution-start/end prices and signed financing coefficients are finite for all 1,825 owned asset intervals per year. Every saved owned-interval validity flag is true. Adjacent execution boundaries are exactly equal. INPUT_QA.json records these checks; they do not certify historical publication or packet-arrival times.

These are previously seen development calendars. The 2025 execution calendar includes its previously admitted next-January-1 terminal boundary. No protected March–September 2026 or unknown reserved data was read. No provider GETs, credentials, paid data or live orders were used.

Overlap check found ten old SOL/XRP close-cell differences between the two source histories in February–April 2022. All precede the earliest 200-close experiment context in June 2022, so they do not affect the fixed 2023/2025 signal windows. Exact old differences are preserved in INPUT_QA.json; full overlapping-history equality is not claimed.

## Code and compatibility

repo/ preserves original upstream paths for the numpy quantity proxy, shared covariance risk controller, canonical weekly cross-sectional strategy and original source manifests. RESTORATION_SOURCE.json contains exact Git blob identities, SHA256, size and upstream links. No downloaded preparation or scoring script was executed.

Canonical public_targets has an unused top-level dependency on Polars through its original risk-helper module. scripts/research/public_cross_section_momentum_compat.py is a transparent import-only compatibility copy: its complete algorithm body is unchanged, while the risk-helper import refers to cs_numpy_risk_compat.py. The latter copies the exact inspected numpy helper function bodies and omits the unrelated Polars-based target API. Originals remain untouched; no AST-based runtime extraction, import stubs or dependency installation is used.

Six original synthetic target tests, with only their module import adapted, and two exact tie tests pass. CS_COMPAT_QA.json records source hashes and checks. These tests create no economic accounts.

The unchanged raw CS rule is top two +0.15 and bottom two -0.15, based on exactly 21 simple-return days; a fully tied score range at or below 1e-12 is cash. Stable score sorting uses explicit symbol order. Ranking occurs on the fixed Monday anchor 1704067200000000 plus integer multiples of seven UTC days. Raw rank is sticky between scheduled ranks; unavailable members clear and cannot reenter before another scheduled rank. Its usual returned weights include daily signed covariance scale-down. The diagnostics' rank_events.raw_weights expose the unchanged unscaled vectors.

## Scope

Restoration and target/input QA only. Candidate protocol, causal joint gate, economic scoring and publication belong to the parent task. No candidate economic experiment was started by this restoration.
