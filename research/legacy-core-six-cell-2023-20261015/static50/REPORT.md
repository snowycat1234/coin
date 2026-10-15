# 2023 STATIC50_OLD_NO_REEXPANSION: frozen no-top-up baseline

Role: FROZEN_NO_TOPUP_BASELINE_COMPARISON. This is the unchanged common-execution variant of the legacy intrinsic signal, not a literal replication of a legacy account. The separate bounded cash-top-up or position-liquidation continuation version is excluded.

Three LOW/MID/HIGH cells are independently reviewed: 3 full-year paid-flat; 0 native economic HALTs with partial observation scope. Calendar: 365 days, 525600 required minutes. Annual APR is not separately defined or claimed.

## LOW
FULL_YEAR_PAID_FLAT; 525600 written minutes. Marked NAV 11114.37273035516188314330000000000000000 USDT. Marked return (FULL2023_PAID): 11.14372730%. Annual paid return: 11.14372730%.
Native all-observation MDD 4.31626670%; minute-close-derived MDD 4.31626670%. These observation scopes are separate.
Nominal forecast budget 5.0000%; maximum actually executed OPEN fresh forecast 4.97380578%; OPEN violations 0. Held-inventory minute-close forecast maximum 22.56342010%; minutes above budget 77649. Complete-day realized annualized volatility 6.06321239%.
True reduce-only CLOSE legs increased forecast risk 57 times; post-CLOSE maximum 24.16434238%. Removing a hedge or refreshing covariance can raise held-inventory forecast risk even when OPEN admission passes.
Fees 22.24623102121200; execution friction 32.358930640; signed funding -44.18980798362611685670; turnover 40447.692765840 USDT. Residual marked notional 0.0; unpaid liability 0; actual liquidation fills 0.

## MID
FULL_YEAR_PAID_FLAT; 525600 written minutes. Marked NAV 11451.44614306459604969090000000000000000 USDT. Marked return (FULL2023_PAID): 14.51446143%. Annual paid return: 14.51446143%.
Native all-observation MDD 7.30164553%; minute-close-derived MDD 7.30164553%. These observation scopes are separate.
Nominal forecast budget 10.0000%; maximum actually executed OPEN fresh forecast 9.92752246%; OPEN violations 0. Held-inventory minute-close forecast maximum 14.46564349%; minutes above budget 9087. Complete-day realized annualized volatility 7.21119366%.
True reduce-only CLOSE legs increased forecast risk 81 times; post-CLOSE maximum 14.38792450%. Removing a hedge or refreshing covariance can raise held-inventory forecast risk even when OPEN admission passes.
Fees 35.96688185173600; execution friction 52.316499680; signed funding -77.72107540366795030910; turnover 65394.330639520 USDT. Residual marked notional 0.0; unpaid liability 0; actual liquidation fills 0.

## HIGH
FULL_YEAR_PAID_FLAT; 525600 written minutes. Marked NAV 11725.44069662264527557279999999999999999 USDT. Marked return (FULL2023_PAID): 17.25440697%. Annual paid return: 17.25440697%.
Native all-observation MDD 4.51102382%; minute-close-derived MDD 4.51102382%. These observation scopes are separate.
Nominal forecast budget 15.0000%; maximum actually executed OPEN fresh forecast 10.46658704%; OPEN violations 0. Held-inventory minute-close forecast maximum 14.46564349%; minutes above budget 0. Complete-day realized annualized volatility 7.32494853%.
True reduce-only CLOSE legs increased forecast risk 94 times; post-CLOSE maximum 14.43442637%. Removing a hedge or refreshing covariance can raise held-inventory forecast risk even when OPEN admission passes.
Fees 36.85370756359600; execution friction 53.606605520; signed funding -78.94309029375872442720; turnover 67006.741024720 USDT. Residual marked notional 0.0; unpaid liability 0; actual liquidation fills 0.

Original MID is included once from the completed pilot. It was never rerun. LOW risk-spike context is retained in reviews/STATIC_LOW_RISK_SPIKE_CONTEXT.json: the July 14 covariance refresh and unchanged held quantities explain the forecast jump; the independent review found no fresh OPEN violation.

## Qualifications and recovery

Full unique actual trade and applied-funding objects preserve every Decimal string. The complete funding journal is losslessly factored and reconstructible as JSON objects in original event order; its original byte formatting is not reconstructed. Full original minute arrays, duplicate request snapshots, idempotency metadata and full guard/rejection journals are omitted and cannot be recovered from the compact packet. Every omitted full parent is hash-pinned. Daily rows and deterministic selected-minute evidence preserve saved values; the selection is a packaging rule, not strategy preregistration.

The offline verifier rechecks all included bytes, unique-economic-row/funding-journal hashes, Decimal cashflow/quantity/margin/debt reconciliation, daily projections, selected-minute clocks and covariance forecasts, review bindings and labels. Source-dependent OPEN admission remains a retained independent review; a compact packet does not reproduce every source or every omitted minute.

This uses native-account offline-proxy assumptions: BASE27 (5.5 bps taker fee per side plus 4 bps half-spread and 4 bps slippage per side), isolated 1x and coarse assumed quantity steps BTC 0.001, ETH 0.01, SOL 1, XRP 100, DOGE 1000. Exchange filters, native liquidation execution, raw-funding unit and provider publication/arrival/completeness are not certified. Raw funding is conditionally interpreted as a fraction. Free wallet cash does not cause an isolated-margin top-up in this frozen baseline.

2023 is seen-development evidence. Same nominal forecast budgets do not establish equal realized risk. Risk-matched excess is NOT_PREREGISTERED_NOT_CLAIMED. No average drops HALTs, no cross-tier average or alpha-family independence is claimed, and target aliases never permit account-execution reuse.

Packet work used only saved JSON/NumPy evidence: zero accounts constructed or replayed, zero financial reruns, zero source downloads and zero publishing actions. Original full outputs stay unchanged. Run python tools/verify_packet.py, then python tools/test_saved_packaging.py.
