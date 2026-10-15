# Corrected financial V2: saved full-2024 B/C results

This is the corrected V2 fixed2024 STATIC50_MID BASE27 saved-results packet. V1 remains superseded policy-mismatched diagnostic evidence. This packet does not run a financial model or recover omitted source data.

## Results

- B, continuation only: terminal NAV 10814.0378314267891803966 USDT; conditional-model return +8.1403783143%; all-observation MDD 6.1361587755%. Two conditional collateral-forfeiture settlements; no paid-market-flat return is asserted. Positive marked equity forfeited: 2.5688912 USDT; own remaining isolated collateral forfeited: 328.3426156 USDT; insurance support: zero.
- C, bounded margin-management package: terminal NAV 10587.7740661483466886176 USDT; actual paid-market-flat offline return +5.8777406615%; all-observation MDD 6.4438124795%. Eight internal transfers totaling 1639.37122176 USDT; zero conditional settlements, external cash added, or terminal debt.
- Both cases completed 527040 of 527040 minutes and ended with zero positions and unpaid liability. C minus B is −2.2626376528 percentage points for the whole management package under the declared model, not the pure effect of top-up transfers.
- Native A/B pre-first-settlement comparison: 269 exact trade rows, 4650 exact funding rows, and 446576 byte-equal financial minute rows. Full paths are omitted; this equality is an independently reviewed finding, not independently reproducible from the packet reductions.

## Descriptive asset attribution

Saved trade-log realized PnL minus fees plus funding gives B/C contributions (USDT): BTC 1126.7392/1103.8495; ETH 99.7125/107.0273; SOL −524.7737/−485.3899; XRP 807.7895/864.3390; DOGE −695.4297/−1002.0518. DOGE accounts for −306.6221 USDT of C−B, partly offset by other assets. This is path attribution, not pure transfer causal attribution. B includes conditional-clearing trade bookkeeping; execution friction is already in fill PnL. Exact100 aggregation leaves tiny native40 rounding residuals, explicitly retained in DESCRIPTIVE_ASSET_PNL_ATTRIBUTION.json.

## Controller and arithmetic qualification

The original serial controller exited with SAVED_PRIMARY_CASH_ISOLATED_DEBT_LEDGER_MISMATCH after terminal B and before starting C. It did not succeed. One XRPUSDT native40 margin-delta subtraction rounds the stored delta by +3E−38 at ledger sequence 4814. Exact100 summation of those stored rounded deltas therefore leaves a raw 3E−38 residual. Independent every-event frozen-native40 arithmetic verifies the actual cash, debt, quantities, basis, margin and totals exactly, without tolerance or changing finance. Original errors, proofs, raw residuals and saved outputs are preserved.

A separate root decision admitted the previously approved but never-started C once through the unchanged single-case entry and the same GO. B was not rerun. The C case's saved validator passed; that does not make the original pair controller successful.

## What is recoverable

Exact financial ledgers, trades, applied/non-applied funding receipts, internal transfers and conditional settlements are retained. Daily and monthly float64 NAV, exposure, cash and cost reductions are included. All-observation drawdown and exposure maxima are retained saved statistics. Full originals and parent identities are hash-pinned; hashes are not replacement data.

Full minute arrays, market/source arrays, full raw audit/native files, target/guard/rejection histories, all fill-request/no-op replay context, and original runtime state are omitted. No restart/resume, full minute-path reconstruction or cold historical reproduction is certified. Per-event price/rate values needed to verify the exact retained financial records are included; these are not a continuous market-data archive.

## Model limitations

The research model uses coarse uncertified quantity filters, fixed 0.005 maintenance and conditional collateral-forfeiture semantics. Native venue risk tiers, partial liquidation, insurance, ADL, intraminute prices and exchange execution remain uncertified. Funding RAW_AS_FRACTION scale=1, actual rate arrival and charge-mark semantics are unconfirmed; no funding-source or publication certification follows from this packet. The result is one fixed offline case, with no robustness or long-term APR claim.

Run python verify_saved_packet.py and python -m unittest -v test_saved_packet.py for standard-library saved-data-only checks. Rebuilding reductions from separately held originals needs NumPy; neither route constructs an account or executes a financial model.

See funding_semantics/V2_APPENDIX.md and V2_EVIDENCE.json for the independently saved-data-only check: both corrected paths have zero recorded same-symbol fills within ±15 seconds of funding. This does not certify raw archive units, arrival or charge-mark authority.

Corrected source is verified at commit c00c14b25b30a339195fe089acb6bd4d24a29f5f; SOURCE_PUBLICATION_REFERENCE.json gives its exact link and immutable archive/review pins. Source publication does not certify controller success or financial outcomes.

Publication status: unpublished candidate. Independent packaging review is required before results publication. The eventual results-parent commit remains pending root verification.
