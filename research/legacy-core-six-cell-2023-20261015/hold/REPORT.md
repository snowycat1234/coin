# 2023 HOLD_CORE5_VOL_MATCHED_NOREEXP: frozen no-top-up baseline

Role: FROZEN_NO_TOPUP_BASELINE_COMPARISON. This is the unchanged common-execution variant of the legacy intrinsic signal, not a literal replication of a legacy account. The separate bounded cash-top-up or position-liquidation continuation version is excluded.

Three LOW/MID/HIGH cells are independently reviewed: 3 full-year paid-flat; 0 native economic HALTs with partial observation scope. Calendar: 365 days, 525600 required minutes. Annual APR is not separately defined or claimed.

## LOW
FULL_YEAR_PAID_FLAT; 525600 written minutes. Marked NAV 11239.82397703392490377850000000000000000 USDT. Marked return (FULL2023_PAID): 12.39823977%. Annual paid return: 12.39823977%.
Native all-observation MDD 4.65817562%; minute-close-derived MDD 4.65817562%. These observation scopes are separate.
Nominal forecast budget 5.0000%; maximum actually executed OPEN fresh forecast 4.98838308%; OPEN violations 0. Held-inventory minute-close forecast maximum 13.96838962%; minutes above budget 295777. Complete-day realized annualized volatility 5.85127024%.
True reduce-only CLOSE legs increased forecast risk 0 times; post-CLOSE maximum 13.71907722%. Removing a hedge or refreshing covariance can raise held-inventory forecast risk even when OPEN admission passes.
Fees 5.51304839531600; execution friction 8.019829680; signed funding -75.07424489075909622150; turnover 10023.724355120 USDT. Residual marked notional 0.0; unpaid liability 0; actual liquidation fills 0.

## MID
FULL_YEAR_PAID_FLAT; 525600 written minutes. Marked NAV 12464.02437322464851945629999999999999999 USDT. Marked return (FULL2023_PAID): 24.64024373%. Annual paid return: 24.64024373%.
Native all-observation MDD 7.67032459%; minute-close-derived MDD 7.67032459%. These observation scopes are separate.
Nominal forecast budget 10.0000%; maximum actually executed OPEN fresh forecast 9.98132304%; OPEN violations 0. Held-inventory minute-close forecast maximum 26.45978062%; minutes above budget 207342. Complete-day realized annualized volatility 10.74628443%.
True reduce-only CLOSE legs increased forecast risk 0 times; post-CLOSE maximum 25.98938690%. Removing a hedge or refreshing covariance can raise held-inventory forecast risk even when OPEN admission passes.
Fees 13.01912469506000; execution friction 18.938603600; signed funding -152.38139848029148054370; turnover 23671.135809200 USDT. Residual marked notional 0.0; unpaid liability 0; actual liquidation fills 0.

## HIGH
FULL_YEAR_PAID_FLAT; 525600 written minutes. Marked NAV 12465.87484625057964062529999999999999999 USDT. Marked return (FULL2023_PAID): 24.65874846%. Annual paid return: 24.65874846%.
Native all-observation MDD 7.67693678%; minute-close-derived MDD 7.67693678%. These observation scopes are separate.
Nominal forecast budget 15.0000%; maximum actually executed OPEN fresh forecast 10.28638489%; OPEN violations 0. Held-inventory minute-close forecast maximum 26.45978062%; minutes above budget 1. Complete-day realized annualized volatility 10.74847967%.
True reduce-only CLOSE legs increased forecast risk 0 times; post-CLOSE maximum 25.98938690%. Removing a hedge or refreshing covariance can raise held-inventory forecast risk even when OPEN admission passes.
Fees 13.05357737437600; execution friction 18.988717920; signed funding -152.52745845504435937470; turnover 23733.777044320 USDT. Residual marked notional 0.0; unpaid liability 0; actual liquidation fills 0.

## Qualifications and recovery

Full unique actual trade and applied-funding objects preserve every Decimal string. The complete funding journal is losslessly factored and reconstructible as JSON objects in original event order; its original byte formatting is not reconstructed. Full original minute arrays, duplicate request snapshots, idempotency metadata and full guard/rejection journals are omitted and cannot be recovered from the compact packet. Every omitted full parent is hash-pinned. Daily rows and deterministic selected-minute evidence preserve saved values; the selection is a packaging rule, not strategy preregistration.

The offline verifier rechecks all included bytes, unique-economic-row/funding-journal hashes, Decimal cashflow/quantity/margin/debt reconciliation, daily projections, selected-minute clocks and covariance forecasts, review bindings and labels. Source-dependent OPEN admission remains a retained independent review; a compact packet does not reproduce every source or every omitted minute.

This uses native-account offline-proxy assumptions: BASE27 (5.5 bps taker fee per side plus 4 bps half-spread and 4 bps slippage per side), isolated 1x and coarse assumed quantity steps BTC 0.001, ETH 0.01, SOL 1, XRP 100, DOGE 1000. Exchange filters, native liquidation execution, raw-funding unit and provider publication/arrival/completeness are not certified. Raw funding is conditionally interpreted as a fraction. Free wallet cash does not cause an isolated-margin top-up in this frozen baseline.

2023 is seen-development evidence. Same nominal forecast budgets do not establish equal realized risk. Risk-matched excess is NOT_PREREGISTERED_NOT_CLAIMED. No average drops HALTs, no cross-tier average or alpha-family independence is claimed, and target aliases never permit account-execution reuse.

Packet work used only saved JSON/NumPy evidence: zero accounts constructed or replayed, zero financial reruns, zero source downloads and zero publishing actions. Original full outputs stay unchanged. Run python tools/verify_packet.py, then python tools/test_saved_packaging.py.
