# Saved-journal isolated-margin risk summaries

`../../native_margin_risk_summary.py` is a reusable, read-only diagnostic. It consumes only a completed account's `summary.json`, `trades.json`, `funding.json`, `liquidations.json` and `minute_nav_inventory.parquet`. It constructs no account or simulator, loads no market data and changes no policy. Four results retain the original separate accounts, PnL and full liquidation losses. `MANIFEST.json` binds result hashes; `PUBLIC_ACCOUNT_BINDINGS.json` checks all20 input hashes against the previously published archive members.

The unchanged engine is `native_daily_scheduler_v1`, SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`. The utility checks this and both account-source hashes before processing. It uses the original `liquidation_price` and `validated_tiers` functions; no financial source changed.

For signed quantity q, absolute quantity A, entry E, isolated collateral C, current mark P, leverage L, maintenance rate m, taker fee f and maintenance deduction d:

- Isolated equity = C + q(P−E); maintenance = APm−d; dollar headroom = equity−maintenance. Normalized headroom divides by AP. Account free cash remains separate and is never counted as isolated collateral.
- Extra collateral x = C−AE/L. Original long liquidation price = (AE−AE/L−x/(1−f)−d)/(A−Am); short price = (AE+AE/L+x/(1+f)+d)/(A+Am).
- Signed adverse distance = side×(P−liquidation price)/P, where side is +1 for long and −1 for short. Negative distance means the engine threshold was crossed. The engine trigger buffer is side×(P−liquidation price)×A×(1−side×m); it can differ from equity−maintenance when extra collateral is nonzero.

Each actual filled lifetime begins at flat-to-held and ends at a recorded normal close or takeover. Additions and partial reductions preserve the lifetime. A later reentry starts a new lifetime. Minima include held minute closes, recorded pre/post fills and funding, and the pre-takeover state. The ordinary takeover minute is already flat, so its earlier threshold crossing is retained separately. Near minute intervals count saved observations, not unobserved continuous exposure.

The default near label is **0 < signed adverse distance ≤5%**. This is an explicit diagnostic threshold, with crossed observations and actual liquidations counted separately; it introduces no order or risk limit. Each JSON provides per-lifetime and per-asset minima, timestamps, collateral, basis, mark, free cash, near intervals and original liquidation witnesses.

| Separate account | Lifetimes | Minimum dollar headroom, USDT | Minimum signed price distance | Near minute observations | Liquidations |
| --- | ---: | ---: | ---: | ---: | ---: |
| SELECTED_FULL773_256 |15|1.361430|9.583585%|0|0|
| FROZEN_VOL |5|17.877526|approximately100%¹|0|0|
| Static50 |16|−0.262837|−0.120194%|84|1|
| Cash50 |16|−0.279558|−0.271161%|84|1|

Dollar minima and distance minima can refer to different positions/times. The model's dollar minimum was a small DOGE position; its distance minimum was XRP on November16 at15:06UTC. Static50's XRP near observations span09:25–10:48UTC before its10:49 takeover; Cash50 spans09:24–10:47 before10:48. Each preserves its October7-to-November16 short lifetime and full109.207539/51.408545USDT collateral loss. Large available free cash did not top up isolated margin. Scaling quantity and collateral together leaves a fixed-leverage liquidation price unchanged.

¹Fully collateralized1x longs have liquidation price zero in exact algebra and no positive-price trigger. Zero/negative prices have distance NA. Tiny positive values from original Decimal rounding are preserved, with distance approximately100%; no clamp or collateral padding is applied. The price helper evaluates Decimal receipt state before the Float64 minute scan, avoiding spurious Float64 cancellation. Marks recovered from saved Float64 notional/quantity and scanned minima remain Float64 observations. Witnesses disclose precision; receipt-state reconciliation tolerance is1e−24USDT, minute tolerance1e−8. Observed maximum equity error was2.28e−13USDT; quantity, collateral and free-cash errors were zero. Historical native exchange rules and intraminute liquidation behavior remain uncertified.

Install the two pinned numerical dependencies in `requirements.txt` into an isolated Python3.11+ environment, or reuse the recovered runner environment. From the repository root, with `STATE` denoting an already recovered account directory and `OUTPUT` a separate destination:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 POLARS_MAX_THREADS=1 \
python research/recover-frozen-runner-20261009/native_margin_risk_summary.py \
  --account SELECTED_FULL773_256=STATE/q4-native92/SELECTED_FULL773_256/account \
  --account FROZEN_VOL=STATE/q4-native92/FROZEN_VOL/account \
  --account Static50=STATE/q4-native92/Static50/account \
  --account Cash50=STATE/q4-native92/Cash50/account \
  --output OUTPUT --near-distance .05
```

Fifteen fixtures in `tests/test_native_margin_risk_summary.py` cover long/short/flat formulas, fee-adjusted extra collateral, vector parity, Float64 cancellation, size invariance, both verified XRP events and the selected model's contemporaneous headroom, actual lifetime boundaries, pre-takeover capture, near counts, free-cash separation, funding depletion and rejection of inconsistent saved inventory. They use pure formulas and hand-written saved receipts, with no wallet instances. Run pytest with its basetemp outside the source and account directories. The four-account scan took4.525seconds, peak RSS185,708,544B, one CPU, numeric threads1 and a6GB address-space bound. No new wallet, fitting, downloads or original-journal changes occurred; no dependency blocker remains.
