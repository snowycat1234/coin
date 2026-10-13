# Fine SMA completion and existing fine controls

All three fixed SMA cases and all six existing fine controls are retained.
Paid cash needs a complete calendar and exact zero residual quantity. Halted or residual endpoints are marked; unequal horizons use completed-minute prefixes.

## 2023
- SMA200_10PCT: FULL_PAID_FLAT; 525600/525600 minutes; marked PnL -746.101720 USDT; paid PnL -746.101719722718; DD 16.943238%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"}
- STATIC50: FULL_PAID_FLAT; 525600/525600 minutes; marked PnL 1159.692494 USDT; paid PnL 1159.6924942943594; DD 11.993969%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"}
- EXACTHALF: FULL_PAID_FLAT; 525600/525600 minutes; marked PnL 254.982870 USDT; paid PnL 254.9828697053029; DD 9.975141%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"}
- SMA200_10PCT_minus_STATIC50: paid PnL delta -1905.7942140170776; same-calendar marked PnL delta -1905.7942140170776
- EXACTHALF_minus_STATIC50: paid PnL delta -904.7096245890566; same-calendar marked PnL delta -904.7096245890566
- EXACTHALF_minus_SMA200_10PCT: paid PnL delta 1001.084589428021; same-calendar marked PnL delta 1001.084589428021

## 2024
- SMA200_10PCT: FULL_PAID_FLAT; 527040/527040 minutes; marked PnL 766.120766 USDT; paid PnL 766.1207660942418; DD 16.210106%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"}
- STATIC50: PARTIAL_HALTED; 461448/527040 minutes; marked PnL 1512.479478 USDT; paid PnL None; DD 9.976521%; account LIQUIDATION_REQUIRED_HALT; exact quantities {"BTCUSDT": "0.00195815", "DOGEUSDT": "1488.70058163", "ETHUSDT": "-0.06828626", "SOLUSDT": "2.60073296", "XRPUSDT": "-236.58004288"}
- EXACTHALF: FULL_PAID_FLAT; 527040/527040 minutes; marked PnL 1386.553321 USDT; paid PnL 1386.5533207779022; DD 9.277422%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"}
- SMA200_10PCT_minus_STATIC50: 461448 common completed minutes; marked prefix PnL delta -874.9040556189957; annual/paid delta unavailable
- EXACTHALF_minus_STATIC50: 461448 common completed minutes; marked prefix PnL delta -358.17533525388535; annual/paid delta unavailable
- EXACTHALF_minus_SMA200_10PCT: paid PnL delta 620.4325546836603; same-calendar marked PnL delta 620.4325546836603

## 2025
- SMA200_10PCT: FULL_PAID_FLAT; 525600/525600 minutes; marked PnL -465.758203 USDT; paid PnL -465.7582026442363; DD 12.168597%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "0E-8", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "0E-8"}
- STATIC50: FULL_MARKED; 525600/525600 minutes; marked PnL 1612.841014 USDT; paid PnL None; DD 8.497864%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "-5165.64825394", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "-379.11600436"}
- EXACTHALF: FULL_MARKED; 525600/525600 minutes; marked PnL 597.573186 USDT; paid PnL None; DD 7.551317%; account ACTIVE; exact quantities {"BTCUSDT": "0E-8", "DOGEUSDT": "-796.07848250", "ETHUSDT": "0E-8", "SOLUSDT": "0E-8", "XRPUSDT": "-94.12643705"}
- SMA200_10PCT_minus_STATIC50: paid PnL delta None; same-calendar marked PnL delta -2078.599216876413
- EXACTHALF_minus_STATIC50: paid PnL delta None; same-calendar marked PnL delta -1015.2678284410833
- EXACTHALF_minus_SMA200_10PCT: paid PnL delta None; same-calendar marked PnL delta 1063.3313884353292

Conditional already-seen development simulation. Original frozen targets and fine-grid sensitivity remain unchanged. RAW_AS_FRACTION funding is conditional. No alpha, OOS, native-grid or venue-execution certification claim. No free terminal close; no annual return comparison across partial horizons.
