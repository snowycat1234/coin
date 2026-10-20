# Fixed settlement-window attribution: completed

Pre-outcome frozen commit: a2f698ff36715ee7ecef2b2daa9ead244dc89a6f. This is a retrospective conditional attribution study, not a shared-wallet backtest, executable one-USDT order, forecast, or investable return.

5,470 complete paired asset-events over all365 days were admitted. Exactly five January1 00:00 asset-events lacked the prior price window and were excluded as prespecified. All5,475 observed funding timestamps are retained alongside their scheduled slots;2,025 have1–29ms offsets. No price window was shifted, and no rate/sign/return/month filter was applied.

Calendar-day equal-weight primary summaries, basis points of each window's own one-USDT initial reference notional:
- Event-window SHORT net: −25.87490842bp. Fixed14-day circular block bootstrap95% interval: [−27.19031836, −24.22948420].
- Event minus paired control net: +1.48689506bp. Interval: [−0.11608860, +3.19794939], spanning zero.

Separately pooled across5,470 pairs, the event decomposition is:
- Trade-price contribution: +0.48202980bp.
- Conditional short funding receipt: +0.65200763bp.
- Spread/slippage cost: −15.99961438bp.
- Fill-notional commission: −10.99973467bp.
- Net: −25.86531163bp, versus control −27.36024372bp.
- Before costs, price plus funding leaves only1.13403742bp total round-trip cost allowance, versus approximately27bp charged under the frozen specification.

All12 calendar-month and all5 asset pooled event-net means are negative. These are full predeclared reporting partitions, not candidates for selecting profitable subperiods. Detailed values remain in RESULT.json; daily joint means and exact clock mapping are in DAILY.csv and EVENT_MAPPING.csv.

This single fixed-window hypothesis does not support a profitable short funding-capture implementation at the stated costs. The small event/control difference is not reliably separated from zero in this descriptive dependence-aware interval. No result rescues a different window, side, fee tier or funding-sign filter; none were tested.

Important limits: observed funding is used retrospectively, not as a pre-event forecast. Raw-rate-as-fraction and a fixed strictly-past mark CLOSE are conditional accounting assumptions, not verified venue charge-point/arrival authority. Minute trade OPENs are not executable BBO quotes. Nearby control windows do not identify a causal funding effect. Development-sample intervals are not pristine out-of-sample or selection-corrected evidence. No2026 values, model fitting, new provider downloads or wallet advances were used.

Attempt history: v1 prefreeze ca036045e82d4e39c1794a544abbe01506c012ab stopped before economic outcomes because its exact-clock admission did not accommodate observed millisecond offsets. V2 changed only source-clock admission to the existing source one-second tolerance, preserving actual timestamps, fixed windows and all economic settings. This was one economic hypothesis with a disclosed pre-calculation source-admission repair, not an outcome-driven parameter search.
