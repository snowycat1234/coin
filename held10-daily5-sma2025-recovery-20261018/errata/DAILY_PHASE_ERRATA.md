# Completed HELD10 daily-observation phase erratum

## Classification

**Intended phase conformity: FALSE.** The frozen contract and analysis protocol
say the daily observation precedes that open's funding. Actual non-genesis daily
observations follow funding whose event timestamp is exactly the decision clock.
This is a material phase-description deviation. It must stay separate from any
later exact-arithmetic PASS. The frozen financial files and failed audit remain
unchanged; this erratum grants no replay, restart, correction of finance, or new
experiment authority.

The completed baseline uses the identical actual observation order. The bounded
comparison may therefore describe these two actual saved same-source DEV runs,
conditional on exact audit, but cannot certify the advertised strictly
pre-funding observation experiment.

## Exact first divergence

At 2025-01-02 00:00:00 UTC, clock 1735776000000000, saved quantities and mark
prices match. Saved overlay daily NAV, forwarder frozen NAV, and independently
recomputed primitive paid-leg/funding NAV all equal
10041.38233340457373150 USDT. The original audit placed the daily observation
before exact-boundary funding and thus expected 10041.51615499667340150 USDT.
The saved-minus-audit difference is exactly -0.133821592099670 USDT:

- BTC: -0.028379650717020
- DOGE: -0.0325039680000
- ETH: -0.030240443113650
- SOL: -0.0194225132690
- XRP: -0.023275017000

All five rows have event_us = rate_available_us = 1735776000000000 and strictly
past funding mark_close_us = 1735775940000000. The original audit's first failure
is therefore exactly explained by its misplaced daily-observation event.
This diagnosis alone does not establish later full-year reconciliation or cuts.

## Actual ordering and baseline identity

The pinned native scheduler updates the closing mark, applies inclusive
funding_through(close, True), writes the last minute row and sets cursor=day_end
(native_scheduler.py lines 440-466). The next _advance_bound_one_day invokes the
daily observer before the next advance_day (HELD10 runtime.py lines 347-364).
Thus observation precedes funding processed by the next day loop, while funding
at the exact decision timestamp has already been paid by the preceding day.

Baseline and HELD10 DailyObservationForwarder AST hashes are both
b85fcfdb8bcb969be9a136d0acc70cc0bc396de474d35f859b28c7cde3745509;
_advance_bound_one_day AST hashes are both
6c8e61c2bbb2593743be42dbceb0d1900a710f56e8ae5878d1860459261bcb7d.
Their source_identity files are byte-identical, with source identity
1ab1d90a5505486ffdeeadd70ff35e5c895b954a4cb9c1212a925d7e63141b34.
Source-file pins and common kernel-manifest, persistent policy, adapter and
financial-profile pins are identical. Baseline day-2 frozen NAV also matches
10041.38233340457373150 exactly.

The saved-only scan checked all 365 daily quantities against actual paid legs,
all daily prices against causal native marks (or flat-genesis fallback), and all
daily NAVs against forwarder receipts. There are 1,025 exact-decision-timestamp
account funding rows, 833 nonzero, across 205 daily observations. Their exact
signed total is -5.2616639369425408557 USDT. Full row evidence is retained in
PHASE_ERRATA_EVIDENCE.json.

## Causality and limits

No future information is found under the declared conditional availability
model: prepaid exact-timestamp rates have rate_available_us <= decision, and
funding marks are strictly earlier. This is not certification of real exchange
publication or arrival. Raw source records lack an independent publication
timestamp; setting rate_available_us=event_us is a declared model assumption.
The next daily covariance is available at the decision, never from a later day.

Machine-readable DAILY_PHASE_ERRATA.json includes exact rows, before/after NAVs,
code/document SHA256 pins, line references, identical baseline identities, and
FALSE intended-phase conformity. First diagnostic and full phase scan artifacts
are separately hashed there. No frozen or financial artifact was changed.
