# 2024 STATIC50: three reviewed terminal cells

Three risk cells are terminal: 0 full-year paid-flat, 3 unpaid native economic HALTs. Terminal does not mean three full annual results. Every HALT remains in the matrix; its annual paid return/APR is null. No mean excluding HALTs is calculated.

## STATIC50_LOW
BANKRUPT_HALT; 461363 of 527040 written minutes. Marked wallet NAV 11106.47263629105154012000000000000000000 USDT; marked partial return 11.0647263629%; all-observation drawdown 3.0691897778%.
At 2024-11-16T09:24:00+00:00, XRPUSDT quantity -200 had isolated equity -0.40060200 versus maintenance 1.00699837000 at mark 1.00699837. Isolated short-leg equity became negative and triggered the model stop. Whole-wallet NAV is reported separately above. No automatic margin top-up or simulated liquidation fill is introduced.
Fees 13.28631739300800; execution friction 19.326008960; signed funding -62.76196399594045988000; retained marked notional 1141.02187464; unpaid liability 0.

## STATIC50_MID
LIQUIDATION_REQUIRED_HALT; 446576 of 527040 written minutes. Marked wallet NAV 10160.83845940581749568050000000000000000 USDT; marked partial return 1.6083845941%; all-observation drawdown 6.1361587755%.
At 2024-11-06T02:57:00+00:00, DOGEUSDT quantity -2000 had isolated equity 1.3529320000000000000000000000000000000 versus maintenance 1.99618170000 at mark 0.19961817. Isolated equity fell below maintenance and triggered the model stop. Whole-wallet NAV is reported separately above. No automatic margin top-up or simulated liquidation fill is introduced.
Fees 24.07091301573200; execution friction 35.011806800; signed funding -108.72682453973050431950; retained marked notional 2210.24494716068; unpaid liability 0.

## STATIC50_HIGH
BANKRUPT_HALT; 446587 of 527040 written minutes. Marked wallet NAV 10202.08017682199767680369999999999999999 USDT; marked partial return 2.0208017682%; all-observation drawdown 12.0514242136%.
At 2024-11-06T03:08:00+00:00, DOGEUSDT quantity -1000 had isolated equity -3.4512280000000000000000000000000000000 versus maintenance 1.07833160000 at mark 0.21566632. Isolated short-leg equity became negative and triggered the model stop. Whole-wallet NAV is reported separately above. No automatic margin top-up or simulated liquidation fill is introduced.
Fees 22.76026441268800; execution friction 33.104961760; signed funding -130.54843501631432319630; retained marked notional 3398.844291949; unpaid liability 0.

## Scope and recovery

Frozen V3 finance, exact causal 2024 source adapter and control-only economic-terminal V2 remain unchanged. The original MID path was not rerun. STATIC50 MID evidence is referenced at its existing exact public commit rather than duplicated here. Other included cases retain complete unique actual trade/funding objects and Decimal strings, full losslessly factored funding journals, terminal positions/HALT witnesses, all guard/rejection rows, costs, risk and independent receipts. Duplicate request snapshots and full minute matrices are omitted and original complete saved files are hash-pinned.

Daily exports retain every complete UTC day plus the actual final partial day, explicitly labeled. Complete-day annualized volatility is a partial-path statistic when a HALT occurs. Deterministic rule-selected minute evidence preserves original row values, indices, causal-gap observations, trade neighborhoods, extrema and terminal neighborhoods. No fictional HALT minute or extension is added. The minute selection rule is an evidence-packaging rule, not strategy preregistration.

This is a native-account offline proxy with coarse assumed quantity steps BTC 0.001, ETH 0.01, SOL 1, XRP 100 and DOGE 1000, not verified exchange filters or venue liquidation execution. New-entry volatility admission does not guarantee ongoing held-inventory volatility or isolated solvency. Free whole-wallet cash does not imply automatic isolated-margin transfers. Historical years are seen development evidence; actual risk-matched excess is NOT_PREREGISTERED_NOT_CLAIMED. Annual excess is undefined unless both cells are full-year paid-flat, and is not claimed here.

All saved-input extraction is read-only JSON/NumPy logic: zero account construction, financial reruns, source downloads or publication. Public copies remove exact local workspace prefixes only where necessary and preserve original full file identities. Existing public base packets supply source/strategy/controller artifacts. Run python tools/verify_packet.py from any directory to verify this packet.
