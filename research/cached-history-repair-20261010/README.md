# Recover missing cached historical observations

The existing cached dataset had missing SOL/XRP trade days on 2022-02-26/27/28 and 2022-04-01/02. With a complete31-close covariance gate, those10 missing asset-days excluded many subsequent portfolio decisions. This is a verified coverage limitation, not proof that it caused the selector's losses.

Twenty-one targeted official daily minute ZIPs were retrieved and checked against official SHA256/CRC and exact1440-minute calendars. Ten trade asset-days were recovered, plus33 missing past-mark observations for funding on11 asset-days (BTC2022Jul31 and allfive2022Oct2/2023Feb24). All overlapping existing marks agree. All previously complete funding coefficients retain numerical parity. Original frozen files/models/results were not overwritten.

The2022Jan2–2024Apr29 interval now has849 dates satisfying complete CORE5 prior31close covariance, actual current/next execution prices and owned funding. That is76 more admissible dates than the previous773 active dates; it includes recovered observations, decisions previously blocked by lookback gaps, and previously paid-close boundaries. Joining wallets is a new economic experiment and old wallet profits must not simply be added.

Additional-date descriptive prior-price regimes:24uptrend,18sideways,16downtrend,11uptrendpullback,7downtrendrebound. These fixed causal bins are not universal labels, predictive evidence or a guarantee that all added history favors shorts.

RECOVERY.zip contains actual21 source ZIPs/checksums, repaired separate tables and scripts. Rolling features, expert targets, scaler and model need fresh reconstruction; do not splice repaired inputs into old frozen contexts or call old outcomes rerun. No training, APR/live-return forecast or Bybit-majority claim.

Prior cache source: https://github.com/snowycat1234/coin/commit/e0d3400b23842f11f167a63e7d80856d76501de8
Official source documentation: https://github.com/binance/binance-public-data
